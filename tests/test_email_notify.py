import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import smtplib
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('notify', Path(__file__).resolve().parents[1] / 'skills/general/email-notify/scripts/email_notify.py')
m = importlib.util.module_from_spec(spec)
previous_bytecode_setting = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    spec.loader.exec_module(m)
finally:
    sys.dont_write_bytecode = previous_bytecode_setting


class NotificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, EMAIL_NOTIFY_HOME=self.temp.name, EMAIL_NOTIFY_TEST_MODE='1')
        self.env.start()
        self.payload = Path(self.temp.name) / 'payload.json'
        self.payload.write_text(json.dumps({'subject': '测试', 'body': '结果摘要'}), encoding='utf-8')
        self.call('configure', '--email', 'self@example.com', '--host', 'smtp.example.com', '--port', '465', '--tls', 'ssl')
        c = m.config()
        c['checked'] = True  # isolated fixture; real SMTP prohibited
        m.save(c)
        token = self.call('preview', '--payload', str(self.payload))['preview_token']
        self.call('enable', '--preview-token', token)
        self.call('authorize', '--task', 'task1', '--run', 'run1')

    def tearDown(self):
        self.env.stop()
        # SQLite connection objects are collected before Windows temp removal.
        import gc
        gc.collect()
        self.temp.cleanup()

    def call(self, *args):
        return m.execute(m.parser().parse_args(args))

    def send(self, kind='completed', sequence='1', extra=()):
        return self.call('send', '--task', 'task1', '--run', 'run1', '--kind', kind,
                         '--sequence', sequence, '--payload', str(self.payload), *extra)

    def test_preview_and_auth_gate(self):
        self.assertEqual(self.call('status')['all']['business']['events'], 0)
        with self.assertRaises(ValueError):
            self.call('enable', '--preview-token', 'wrong')
        self.call('revoke', '--task', 'task1', '--run', 'run1')
        with self.assertRaises(ValueError):
            self.send()

    def test_concurrent_deduplication_and_terminal_slot(self):
        def delivery(*args):
            time.sleep(.05)
            return 'submitted', False, None
        with patch.object(m, 'deliver', side_effect=delivery) as transport:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
                results = list(pool.map(lambda _: self.send(), range(5)))
            self.assertEqual(transport.call_count, 1)
            self.assertEqual(sum(bool(r.get('duplicate')) for r in results), 4)
            self.assertTrue(self.send('failed')['duplicate'])
        stats = self.call('status')['all']['business']
        self.assertEqual((stats['events'], stats['submitted'], stats['attempts'], stats['duplicates']), (1, 1, 1, 5))

    def test_retries_and_test_separation(self):
        with patch.object(m, 'deliver', side_effect=[('failed', True, 'timeout'), ('failed', True, 'timeout'), ('submitted', False, None)]), patch.object(m.time, 'sleep'):
            result = self.send()
        self.assertEqual(result['attempts'], 3)
        with patch.object(m, 'deliver', return_value=('submitted', False, None)):
            self.send('test')
        stats = self.call('status')['all']
        self.assertEqual(stats['business']['attempts'], 3)
        self.assertEqual(stats['business']['submitted'], 1)
        self.assertEqual(stats['business']['failed'], 0)
        self.assertEqual(stats['tests']['submitted'], 1)

    def test_unknown_not_retried_and_explicit_resend(self):
        with patch.object(m, 'deliver', return_value=('unknown', False, 'disconnect')) as transport:
            result = self.send()
            self.assertEqual(transport.call_count, 1)
            self.assertTrue(self.send()['duplicate'])
        with patch.object(m, 'deliver', return_value=('submitted', False, None)):
            resent = self.send(sequence='2', extra=('--resend-of', result['event']))
        self.assertEqual(resent['status'], 'submitted')
        self.assertEqual(self.call('status')['all']['business']['unknown'], 1)

    def test_stale_send_recovery(self):
        with patch.object(m, 'deliver', return_value=('submitted', False, None)):
            result = self.send()
        conn = m.db()
        conn.execute("UPDATE events SET status='sending',updated=? WHERE id=?", (time.time()-700, result['event']))
        conn.close()
        self.assertEqual(self.send()['status'], 'unknown')

    def test_fixed_recipient_payload_and_disable(self):
        self.payload.write_text(json.dumps({'subject': 'x', 'body': 'y', 'to': 'other@example.com'}))
        with self.assertRaises(ValueError):
            self.send()
        self.call('disable')
        with self.assertRaises(ValueError):
            self.send()

    def test_smtp_phase_classification(self):
        class FakeSMTP:
            def mail(self, addr): return 250, b'OK'
            def rcpt(self, addr): return 250, b'OK'
            def data(self, data): raise smtplib.SMTPServerDisconnected('sensitive server detail')
            def close(self): pass
        msg = m.make_message(m.config(), {'subject': 'x', 'body': 'y'}, 't', 'r', 'e', time.time(), '<e@test>')
        self.assertNotIn(b'\n', msg.as_bytes().replace(b'\r\n', b''))
        with patch.object(m, 'connect', return_value=FakeSMTP()):
            outcome, retry, error = m.deliver(m.config(), msg)
        self.assertEqual((outcome, retry, error), ('unknown', False, 'SMTPServerDisconnected'))
        with patch.object(m, 'connect', side_effect=TimeoutError()):
            self.assertEqual(m.deliver(m.config(), msg)[:2], ('failed', True))
        with patch.object(m, 'connect', side_effect=smtplib.SMTPAuthenticationError(535, b'private')):
            self.assertEqual(m.deliver(m.config(), msg), ('failed', False, 'SMTPAuthenticationError:535'))

    def test_reconfigure_invalidates_authorizations(self):
        self.call('configure', '--email', 'self@example.com', '--host', 'smtp.example.com', '--port', '587', '--tls', 'starttls')
        self.assertFalse(m.config()['enabled'])
        conn = m.db()
        self.assertEqual(conn.execute('SELECT COUNT(*) FROM runs').fetchone()[0], 0)
        conn.close()

    def test_no_network_or_credentials_in_test_mode(self):
        with self.assertRaises(ValueError):
            m.connect(m.config())
        with self.assertRaises(ValueError):
            m.credential(m.config())


if __name__ == '__main__':
    unittest.main(verbosity=2)
