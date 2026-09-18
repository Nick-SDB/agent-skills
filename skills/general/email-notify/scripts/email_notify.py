"""SMTP task notifications. Python 3.10+, stdlib on Windows."""
import argparse
import contextlib
import ctypes
import datetime as dt
import getpass
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import secrets
import smtplib
import socket
import sqlite3
import ssl
import sys
import tempfile
import time
from email.message import EmailMessage
from email.policy import SMTP as SMTP_POLICY
from email.utils import format_datetime
from zoneinfo import ZoneInfo


def roots():
    override = os.environ.get('EMAIL_NOTIFY_HOME')
    if override:
        return Path(override).resolve(), Path(override).resolve()
    home = Path.home()
    if sys.platform == 'win32':
        p = Path(os.environ.get('LOCALAPPDATA', home / 'AppData/Local')) / 'email-notify'
        return p, p
    if sys.platform == 'darwin':
        p = home / 'Library/Application Support/email-notify'
        return p, p
    return (Path(os.environ.get('XDG_CONFIG_HOME', home / '.config')) / 'email-notify',
            Path(os.environ.get('XDG_STATE_HOME', home / '.local/state')) / 'email-notify')


def private_dir(path):
    path.mkdir(parents=True, exist_ok=True)
    if os.name != 'nt':
        path.chmod(0o700)


def write_json(path, value):
    private_dir(path.parent)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.tmp-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(value, out, ensure_ascii=False, indent=2)
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def config():
    p = roots()[0] / 'config.json'
    if not p.exists():
        raise ValueError('Not configured; run doctor and configure first.')
    return json.loads(p.read_text(encoding='utf-8'))


def save(c):
    write_json(roots()[0] / 'config.json', c)


def db():
    p = roots()[1]
    private_dir(p)
    conn = sqlite3.connect(p / 'state.sqlite3', timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    if os.name != 'nt':
        (p / 'state.sqlite3').chmod(0o600)
    conn.executescript('''
      CREATE TABLE IF NOT EXISTS runs(task TEXT, run TEXT, revision TEXT,
        PRIMARY KEY(task,run));
      CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, task TEXT, run TEXT,
        kind TEXT, seq TEXT, slot TEXT UNIQUE, revision TEXT, content_hash TEXT,
        status TEXT, created REAL, updated REAL, duplicates INTEGER DEFAULT 0,
        resend_of TEXT, message_id TEXT);
      CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, event TEXT,
        started REAL, outcome TEXT, error TEXT);
    ''')
    conn.execute("UPDATE events SET status='unknown',updated=? WHERE status='sending' AND updated<?",
                 (time.time(), time.time() - 600))
    return conn


@contextlib.contextmanager
def transaction(conn):
    conn.execute('BEGIN IMMEDIATE')
    try:
        yield
        conn.execute('COMMIT')
    except BaseException:
        conn.execute('ROLLBACK')
        raise


def native_credential(target, username, password=None):
    from ctypes import wintypes as w
    class Credential(ctypes.Structure):
        _fields_ = [('Flags', w.DWORD), ('Type', w.DWORD), ('TargetName', w.LPWSTR),
                    ('Comment', w.LPWSTR), ('LastWritten', w.FILETIME),
                    ('CredentialBlobSize', w.DWORD), ('CredentialBlob', ctypes.POINTER(w.BYTE)),
                    ('Persist', w.DWORD), ('AttributeCount', w.DWORD),
                    ('Attributes', ctypes.c_void_p), ('TargetAlias', w.LPWSTR),
                    ('UserName', w.LPWSTR)]
    api = ctypes.WinDLL('Advapi32.dll', use_last_error=True)
    api.CredWriteW.argtypes = [ctypes.POINTER(Credential), w.DWORD]
    api.CredWriteW.restype = w.BOOL
    api.CredReadW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, ctypes.POINTER(ctypes.POINTER(Credential))]
    api.CredReadW.restype = w.BOOL
    api.CredFree.argtypes = [ctypes.c_void_p]
    api.CredFree.restype = None
    if password is not None:
        blob = password.encode('utf-16-le')
        buf = (w.BYTE * len(blob)).from_buffer_copy(blob)
        record = Credential(Type=1, TargetName=target, CredentialBlobSize=len(blob),
                            CredentialBlob=buf, Persist=2, UserName=username)
        if not api.CredWriteW(ctypes.byref(record), 0):
            raise ValueError('Windows credential write failed, code ' + str(ctypes.get_last_error()))
        return None
    ptr = ctypes.POINTER(Credential)()
    if not api.CredReadW(target, 1, 0, ctypes.byref(ptr)):
        raise ValueError('Windows credential missing or inaccessible, code ' + str(ctypes.get_last_error()))
    try:
        return ctypes.string_at(ptr.contents.CredentialBlob, ptr.contents.CredentialBlobSize).decode('utf-16-le')
    finally:
        api.CredFree(ptr)


def os_keyring():
    import keyring
    backend = keyring.get_keyring()
    name = type(backend).__module__
    allowed = ('keyring.backends.macOS', 'keyring.backends.SecretService',
               'keyring.backends.kwallet', 'keyring.backends.Windows')
    if not name.startswith(allowed):
        raise ValueError('A supported OS keyring backend is required; plaintext/chained backends are not accepted.')
    return keyring


def credential(c, password=None):
    if os.environ.get('EMAIL_NOTIFY_TEST_MODE') == '1':
        raise ValueError('Credential access is blocked in test mode.')
    backend = c['backend']
    if backend == 'native':
        if sys.platform != 'win32':
            raise ValueError('Native backend is Windows only.')
        return native_credential(c['credential_ref'], c['login'], password)
    if backend == 'keyring':
        k = os_keyring()
        if password is not None:
            k.set_password(c['credential_ref'], c['login'], password)
            return None
        value = k.get_password(c['credential_ref'], c['login'])
    else:
        if os.name == 'nt':
            raise ValueError('File fallback is POSIX only; use Windows Credential Manager.')
        p = roots()[0] / 'credentials.json'
        if password is not None:
            write_json(p, {'ref': c['credential_ref'], 'password': password})
            return None
        if p.stat().st_mode & 0o077:
            raise ValueError('Credential file permissions must be 600.')
        data = json.loads(p.read_text(encoding='utf-8'))
        value = data['password'] if data['ref'] == c['credential_ref'] else None
    if not value:
        raise ValueError('Credential missing; run credential-set in an interactive terminal.')
    return value


def zone(c):
    value = c['timezone']
    if value.startswith('offset:'):
        return dt.timezone(dt.timedelta(seconds=int(value.split(':')[1])))
    return ZoneInfo(value)


def detect_zone():
    env = os.environ.get('TZ')
    if env:
        try:
            ZoneInfo(env)
            return env
        except (ValueError, KeyError):
            pass
    try:
        resolved = str((Path('/') / 'etc' / 'localtime').resolve())
        if '/zoneinfo/' in resolved:
            value = resolved.split('/zoneinfo/', 1)[1]
            ZoneInfo(value)
            return value
    except (OSError, ValueError, KeyError):
        pass
    seconds = int(dt.datetime.now().astimezone().utcoffset().total_seconds())
    return 'offset:' + str(seconds)


def load_payload(path):
    p = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if set(p) != {'subject', 'body'} or not all(isinstance(v, str) for v in p.values()):
        raise ValueError('Payload requires only string subject and body.')
    if not p['subject'].strip() or any(ch in p['subject'] for ch in '\r\n'):
        raise ValueError('Subject must be nonempty and must not contain line breaks.')
    if len(p['subject']) > 200 or len(p['body']) > 20000:
        raise ValueError('Notification too long: subject <=200, body <=20000 characters.')
    return p


def connect(c):
    if os.environ.get('EMAIL_NOTIFY_TEST_MODE') == '1':
        raise ValueError('Real SMTP is blocked in test mode.')
    password = credential(c)
    context = ssl.create_default_context()
    server = None
    try:
        if c['tls'] == 'ssl':
            server = smtplib.SMTP_SSL(c['host'], c['port'], timeout=20, context=context)
        else:
            server = smtplib.SMTP(c['host'], c['port'], timeout=20)
            server.ehlo()
            server.starttls(context=context)
        server.ehlo()
        server.login(c['login'], password)
        return server
    except BaseException:
        if server is not None:
            server.close()
        raise


def deliver(c, message):
    server = None
    phase = 'connect'
    try:
        server = connect(c)
        phase = 'envelope'
        for code, _ in (server.mail(c['email']),):
            if code != 250:
                raise smtplib.SMTPResponseException(code, b'')
        code, _ = server.rcpt(c['email'])
        if code not in (250, 251):
            raise smtplib.SMTPResponseException(code, b'')
        phase = 'data'
        code, _ = server.data(message.as_bytes())
        if code != 250:
            raise smtplib.SMTPDataError(code, b'')
        return 'submitted', False, None
    except smtplib.SMTPResponseException as e:
        retry = 400 <= e.smtp_code < 500 and not isinstance(e, smtplib.SMTPAuthenticationError)
        return 'failed', retry, f'{type(e).__name__}:{e.smtp_code}'
    except (OSError, smtplib.SMTPException) as e:
        outcome = 'unknown' if phase == 'data' else 'failed'
        retry = phase != 'data' and not isinstance(e, (ssl.SSLError, smtplib.SMTPNotSupportedError))
        return outcome, retry, type(e).__name__
    except Exception as e:
        return ('unknown' if phase == 'data' else 'failed'), False, type(e).__name__
    finally:
        if server is not None:
            with contextlib.suppress(Exception):
                server.close()


def make_message(c, payload, task, run, event_id, created, message_id):
    message = EmailMessage(policy=SMTP_POLICY)
    message['From'] = c['email']
    message['To'] = c['email']
    message['Subject'] = payload['subject']
    message['Date'] = format_datetime(dt.datetime.fromtimestamp(created, zone(c)))
    message['Message-ID'] = message_id
    stamp = dt.datetime.fromtimestamp(created, zone(c)).isoformat(timespec='seconds')
    message.set_content(payload['body'] + f'\n\n任务编号：{task}\n执行编号：{run}\n事件时间：{stamp}\n通知编号：{event_id}\n')
    return message


def send(c, a):
    with contextlib.closing(db()) as conn:
        return send_with_db(c, a, conn)


def send_with_db(c, a, conn):
    if not c['enabled']:
        raise ValueError('Notifications disabled; complete preview and enable first.')
    payload = load_payload(a.payload)
    terminal = a.kind in ('completed', 'failed')
    slot = json.dumps([a.task, a.run, 'terminal' if terminal else a.kind,
                       '' if terminal else a.sequence], separators=(',', ':'))
    if a.resend_of:
        slot = json.dumps([a.task, a.run, 'resend', a.resend_of, a.sequence])
    event_id = hashlib.sha256(slot.encode()).hexdigest()[:32]
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    now = time.time()
    with transaction(conn):
        run = conn.execute('SELECT revision FROM runs WHERE task=? AND run=?', (a.task, a.run)).fetchone()
        if not run or run['revision'] != c['revision']:
            raise ValueError('This task/run is not authorized for the current configuration.')
        if a.resend_of:
            original = conn.execute('SELECT * FROM events WHERE id=?', (a.resend_of,)).fetchone()
            if not original or original['task'] != a.task or original['run'] != a.run or original['kind'] != a.kind:
                raise ValueError('Resend reference must match this task/run and kind.')
        existing = conn.execute('SELECT * FROM events WHERE slot=?', (slot,)).fetchone()
        if existing:
            conn.execute('UPDATE events SET duplicates=duplicates+1 WHERE id=?', (existing['id'],))
            return {'event': existing['id'], 'status': existing['status'], 'duplicate': True,
                    'content_changed': existing['content_hash'] != digest}
        message_id = f'<{event_id}@email-notify.local>'
        message = make_message(c, payload, a.task, a.run, event_id, now, message_id)
        message.as_bytes()  # fail before event claim if serialization fails
        conn.execute('''INSERT INTO events(id,task,run,kind,seq,slot,revision,content_hash,status,
                     created,updated,resend_of,message_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                     (event_id, a.task, a.run, a.kind, a.sequence, slot, c['revision'], digest,
                      'sending', now, now, a.resend_of, message_id))
    for n in range(3):
        latest = config()
        authorized = conn.execute('SELECT revision FROM runs WHERE task=? AND run=?', (a.task, a.run)).fetchone()
        if not latest['enabled'] or latest['revision'] != c['revision'] or not authorized:
            conn.execute("UPDATE events SET status='failed',updated=? WHERE id=?", (time.time(), event_id))
            return {'event': event_id, 'status': 'failed', 'reason': 'authorization_revoked'}
        started = time.time()
        with transaction(conn):
            attempt = conn.execute('INSERT INTO attempts(event,started,outcome) VALUES(?,?,?)',
                                   (event_id, started, 'sending')).lastrowid
            conn.execute('UPDATE events SET updated=? WHERE id=?', (started, event_id))
        outcome, retry, error = deliver(c, message)
        again = outcome == 'failed' and retry and n < 2
        with transaction(conn):
            conn.execute('UPDATE attempts SET outcome=?,error=? WHERE id=?', (outcome, error, attempt))
            conn.execute('UPDATE events SET status=?,updated=? WHERE id=?',
                         ('sending' if again else outcome, time.time(), event_id))
        if not again:
            return {'event': event_id, 'status': outcome, 'attempts': n + 1, 'error': error,
                    'meaning': 'SMTP accepted; delivery is not verified.' if outcome == 'submitted' else outcome}
        time.sleep(2 ** n)


def stats(conn, since=0, task=None):
    where = 'created>=?'
    values = [since]
    if task:
        where += ' AND task=?'
        values.append(task)
    result = {}
    for name, comparison in [('business', "kind!='test'"), ('tests', "kind='test'")]:
        rows = conn.execute(f'SELECT status,duplicates FROM events WHERE {where} AND {comparison}', values).fetchall()
        counts = {key: 0 for key in ['events', 'submitted', 'failed', 'unknown', 'sending', 'duplicates', 'attempts']}
        counts['events'] = len(rows)
        for row in rows:
            counts[row['status']] += 1
            counts['duplicates'] += row['duplicates']
        sql = f'SELECT count(*) FROM attempts a JOIN events e ON a.event=e.id WHERE a.started>=? AND e.{comparison}'
        params = [since]
        if task:
            sql += ' AND e.task=?'
            params.append(task)
        counts['attempts'] = conn.execute(sql, params).fetchone()[0]
        result[name] = counts
    return result


def execute(a):
    confroot, stateroot = roots()
    if a.command == 'doctor':
        writes = {}
        for p in {confroot, stateroot}:
            try:
                private_dir(p)
                with tempfile.TemporaryFile(dir=p):
                    pass
                writes[str(p)] = True
            except OSError:
                writes[str(p)] = False
        backend = 'native' if sys.platform == 'win32' else 'keyring'
        available = sys.platform == 'win32'
        if not available:
            try:
                os_keyring()
                available = True
            except Exception:
                pass
        return {'os': platform.system(), 'python': platform.python_version(), 'executable': sys.executable,
                'config': str(confroot / 'config.json'), 'state': str(stateroot / 'state.sqlite3'),
                'configured': (confroot / 'config.json').exists(), 'write_access': writes,
                'backend': backend, 'backend_available': available, 'timezone': detect_zone()}
    if a.command == 'configure':
        if not re.fullmatch(r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', a.email):
            raise ValueError('A single ASCII mailbox address is required.')
        if not a.host or any(x.isspace() for x in a.host) or not 1 <= a.port <= 65535:
            raise ValueError('Invalid SMTP host or port.')
        if a.backend == 'native' and sys.platform != 'win32' or a.backend == 'file' and os.name == 'nt':
            raise ValueError('Unsupported credential backend for this OS.')
        c = {'email': a.email, 'host': a.host, 'port': a.port, 'tls': a.tls,
             'login': a.login or a.email, 'backend': a.backend,
             'credential_ref': 'email-notify/smtp/' + a.email, 'timezone': a.timezone or detect_zone(),
             'enabled': False, 'checked': False, 'revision': secrets.token_hex(16)}
        zone(c)
        save(c)
        with contextlib.closing(db()) as conn:
            conn.execute('DELETE FROM runs')
        return {'configured': True, 'enabled': False, 'config': str(confroot / 'config.json'),
                'credential_backend': c['backend'], 'credential_ref': c['credential_ref']}
    c = config()
    if a.command == 'credential-set':
        if not sys.stdin.isatty():
            raise ValueError('Run credential-set yourself in an interactive terminal; no piped secrets.')
        password = getpass.getpass('SMTP password/app password (hidden): ')
        if not password:
            raise ValueError('Credential cannot be empty.')
        credential(c, password)
        c.update(enabled=False, checked=False)
        c.pop('preview_token', None)
        save(c)
        return {'credential_saved': True, 'backend': c['backend'], 'ref': c['credential_ref']}
    if a.command == 'check':
        c.update(checked=False, enabled=False)
        c.pop('preview_token', None)
        save(c)
        server = connect(c)
        server.close()
        c['checked'] = True
        save(c)
        return {'dns_tcp_tls_auth': 'passed', 'email_sent': False}
    if a.command == 'preview':
        payload = load_payload(a.payload)
        token = secrets.token_hex(16) if c['checked'] else None
        c['preview_token'] = token
        save(c)
        sample = make_message(c, payload, 'sample-task', 'sample-run', 'sample-event', time.time(), '<sample@email-notify.local>')
        return {'preview_only': True, 'from': c['email'], 'to': c['email'], 'subject': payload['subject'],
                'body': sample.get_content(), 'preview_token': token,
                'authorization': 'Current/future explicitly invoked tasks; completion, failure, action-needed; no attachments.',
                'config': str(confroot / 'config.json'), 'state': str(stateroot / 'state.sqlite3'),
                'credential_backend': c['backend'], 'credential_ref': c['credential_ref']}
    if a.command == 'enable':
        if not c['checked'] or not a.preview_token or a.preview_token != c.get('preview_token'):
            raise ValueError('Successful check and user-reviewed preview token required.')
        c.update(enabled=True)
        c.pop('preview_token', None)
        save(c)
        return {'enabled': True}
    if a.command == 'disable':
        c.update(enabled=False)
        save(c)
        return {'enabled': False}
    if a.command in ('authorize', 'revoke'):
        with contextlib.closing(db()) as conn:
            if a.command == 'authorize':
                if not c['enabled']:
                    raise ValueError('Configuration is not enabled.')
                conn.execute('INSERT OR REPLACE INTO runs VALUES(?,?,?)', (a.task, a.run, c['revision']))
            else:
                conn.execute('DELETE FROM runs WHERE task=? AND run=?', (a.task, a.run))
        return {'task': a.task, 'run': a.run, 'authorized': a.command == 'authorize'}
    if a.command == 'send':
        return send(c, a)
    if a.command == 'status':
        midnight = dt.datetime.now(zone(c)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        with contextlib.closing(db()) as conn:
            result = {'config': c, 'all': stats(conn), 'today': stats(conn, midnight)}
            result['config'] = {k: v for k, v in c.items() if k != 'preview_token'}
            if a.task:
                result['task'] = stats(conn, task=a.task)
            return result


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    for command in ('doctor', 'credential-set', 'check', 'disable'):
        sub.add_parser(command)
    q = sub.add_parser('configure')
    for name in ('email', 'host'):
        q.add_argument('--' + name, required=True)
    q.add_argument('--port', required=True, type=int)
    q.add_argument('--tls', choices=['ssl', 'starttls'], required=True)
    q.add_argument('--login')
    q.add_argument('--timezone')
    q.add_argument('--backend', choices=['native', 'keyring', 'file'], default='native' if sys.platform == 'win32' else 'keyring')
    sub.add_parser('preview').add_argument('--payload', required=True)
    sub.add_parser('enable').add_argument('--preview-token', required=True)
    sub.add_parser('status').add_argument('--task')
    for command in ('authorize', 'revoke', 'send'):
        q = sub.add_parser(command)
        q.add_argument('--task', required=True)
        q.add_argument('--run', required=True)
        if command == 'send':
            q.add_argument('--kind', choices=['completed', 'failed', 'action-needed', 'test'], required=True)
            q.add_argument('--sequence', required=True)
            q.add_argument('--payload', required=True)
            q.add_argument('--resend-of')
    return p


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    a = parser().parse_args()
    try:
        result = execute(a)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get('status') in ('failed', 'unknown') else 0
    except Exception as e:
        # SMTP errors can contain private server content: show only type/code.
        if isinstance(e, smtplib.SMTPResponseException):
            detail = f'SMTP code {e.smtp_code}'
        elif isinstance(e, (ValueError, FileNotFoundError, ModuleNotFoundError)):
            detail = str(e)
        else:
            detail = 'Check configuration, network and credential backend.'
        print(json.dumps({'error': type(e).__name__, 'detail': detail}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
