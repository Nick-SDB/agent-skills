# Commands and configuration

All commands emit JSON and never print credentials. Run with Python 3.10+:

```text
python scripts/email_notify.py doctor
python scripts/email_notify.py configure --email USER@EXAMPLE.COM --host SMTP_HOST --port 465 --tls ssl
python scripts/email_notify.py credential-set
python scripts/email_notify.py check
python scripts/email_notify.py preview --payload PAYLOAD.json
python scripts/email_notify.py enable --preview-token TOKEN_FROM_PREVIEW
python scripts/email_notify.py authorize --task TASK_ID --run RUN_ID
python scripts/email_notify.py send --task TASK_ID --run RUN_ID --kind completed --sequence 1 --payload PAYLOAD.json
python scripts/email_notify.py status --task TASK_ID
python scripts/email_notify.py revoke --task TASK_ID --run RUN_ID
python scripts/email_notify.py disable
```

`configure` accepts `--login`, `--tls starttls --port 587`, `--timezone Asia/Shanghai`, and `--backend native|keyring|file`. Windows defaults to native Credential Manager; macOS/Linux default to the optional `keyring` package. Non-Windows OS backends require `python -m pip install keyring` and a working OS credential service. On Windows the native backend needs no extra dependencies. A missing backend is an actionable error, not an automatic switch to plaintext. User-selected file fallback is available only on POSIX, with directory 700 and file 600. Configure always resets enablement and run authorization. Timezone defaults to the detected local timezone (IANA zone if available, otherwise the current fixed offset).

The user runs `credential-set` directly in an interactive local terminal; input uses `getpass`. Do not submit passwords through agent tools. `credential-set` invalidates prior connection validation and disables sending. `check` must succeed after connection or credential changes before `enable`. Preview output includes an acknowledgment token; use `enable --preview-token TOKEN` only after the user has reviewed that preview. Preview must be generated after a successful check.

Payload JSON (UTF-8, optional BOM):

```json
{"subject":"[Agent][已完成] 整理项目文档","body":"任务：整理项目文档\n状态：已完成\n\n结果摘要：已生成文档索引。\n需要你处理：无。"}
```

`kind`: `completed`, `failed`, `action-needed`, or `test`. There are no recipient or attachment fields in payloads. `preview` adds illustrative metadata; actual `send` adds task/run/event ID and timestamp. `send --resend-of ID` creates a linked resend record; only use following the user's explicit resend instruction. Resends require a fresh sequence. All send commands require an enabled config and an authorized task/run.

## Storage

- Windows: `%LOCALAPPDATA%\email-notify\config.json` and `state.sqlite3`; native generic credential target `email-notify/smtp/<email>`.
- macOS: `~/Library/Application Support/email-notify/` for config/state; OS keyring service `email-notify/smtp/<email>`.
- Linux: `$XDG_CONFIG_HOME/email-notify/config.json` (default `~/.config`) and `$XDG_STATE_HOME/email-notify/state.sqlite3` (default `~/.local/state`); Secret Service through keyring.
- POSIX file fallback: `credentials.json` beside config, plaintext with restricted permissions.

`doctor` reports actual resolved paths and tests write access. Database stores subject/body hashes rather than full message bodies; records still contain task IDs, timestamps, and outcome categories. Do not expose raw SMTP server error strings: they can contain private message content. Config stores credential references, not passwords. OS-user access to credential storage is not a security boundary against other code running as that same user.

`EMAIL_NOTIFY_HOME` overrides config/state roots for isolated testing; `EMAIL_NOTIFY_TEST_MODE=1` blocks credential access and real SMTP networking. Never use these overrides to bypass normal authorization or counters.

## Counters and recovery

`status` returns cumulative, today, and optional task scopes. Business events, submitted, failed, unknown, pending/sending, attempts and duplicate calls are separate; tests have independent event/status/attempt counts. Counts of event outcomes change with event state and are never double counted. Day boundaries use configured timezone and event creation time (attempts use attempt time). Preview/check do not create notification events. A failed event is not automatically reopened by repeated calls.

Each send claims the event using `BEGIN IMMEDIATE`, records each attempt before networking, and uses a 10-minute lease. Concurrent duplicate calls cannot send the same event. Expired in-flight events become unknown; completed/failed share the terminal slot. SMTP connection/auth/MAIL/RCPT failures occur before DATA and can be classified as unsubmitted. Disconnects/timeouts after DATA starts are unknown. Explicit SMTP rejection after DATA is a definite failure. Retry only temporary, definitely unsubmitted failures, at most three attempts with short backoff.
