---
name: email-notify
description: Configure SMTP email notifications to the user's own mailbox, preview messages, and send authorized task completion, failure, or action-needed notifications with persistent deduplication and counters. Use when the user invokes email-notify or requests email notification setup or status.
---

# Email notifications

Use `scripts/email_notify.py` with Python 3.10+. Read [configuration.md](references/configuration.md) for commands and storage details.

## First use

1. Run `doctor`; inspect actual paths, runtime, existing configuration, and credential backend availability. Do not scan unrelated accounts or secrets.
2. Collect missing fields together: user's email, SMTP host/port/TLS mode, and login only when different. Recipient defaults to sender. For common providers, verify connection parameters in official provider documentation; custom servers require user input. Detect the environment without asking.
3. Explain defaults: Chinese summaries, no attachments; completion, final failure, and action-needed notifications; automatic sending in the current and future tasks where the user explicitly invokes this skill. Merely discovering or installing the skill does not authorize unrelated task notifications.
4. Run `configure`. Have the user enter the SMTP password/app password via the local interactive `credential-set` command (hidden input). Never ask for secrets in chat, pass them in command arguments, or echo them. If no OS credential backend exists, explain the permission-restricted plaintext fallback and use it only after the user chooses it.
5. Run `check` to check DNS, TCP, certificate-verified TLS, and SMTP login without sending a message. Explain errors concretely. Never disable TLS verification.
6. Create a sample payload, run `preview`, and show the user the actual sender/recipient, authorization defaults, absolute storage locations, and complete sample email. Mark sample data as illustrative. Offer **confirm and enable**, **send test and enable**, or **modify**. Do not enable or send a test until that choice arrives. On test choice: `enable`, send a `test` event, and report its actual status. If testing fails, explain that configuration is enabled but delivery is not verified.

## Each explicitly invoked task

- Run `status`, then `authorize --task TASK_ID --run RUN_ID`. Use a stable task ID supplied by the environment, or create and retain a UUID. Create a new run ID only for a new execution, never for retries. Briefly announce active notification rules and recipient.
- Register completion, final failure, and action-needed calls in the current task's workflow. The skill is not a background daemon and cannot notify after the process is forcibly terminated.
- Compose concise Chinese summaries: task, result, deliverables, required action. Label local paths as local to the execution machine, not clickable remote deliverables. Exclude secrets, full chat/logs, and attachments by default.
- Use a stable event sequence per actionable question. A repeated check of the same question uses the same sequence. Completion and final failure share one terminal slot per run.
- Call `send` with a JSON payload file. Immediately inspect the returned status. `submitted` means SMTP accepted; never claim delivered or read. `unknown` means submission may have happened: do not automatically resend or change IDs to bypass deduplication. Report mail failures in the current conversation without masking the original task result.
- Payload files may contain private summaries: use a task-private temporary file and delete it after the command finishes. Do not put secrets in payloads.

## Follow-up requests

- Configuration/status/counts: `status`; preview: `preview` (no send counters).
- Explicit test request: authorize its task/run and send a `test` payload. Tests are counted separately.
- This task should not send: `revoke --task ... --run ...`.
- Disable future mail: `disable`. Re-enabling requires a user request.
- Change mailbox/settings: `configure` disables sending and invalidates old run authorizations; repeat check and preview before enabling.
- Explicit resend of an unknown or submitted event: explain its prior state, retain the original record, and use a fresh event sequence with `--resend-of ORIGINAL_EVENT_ID`; the user must explicitly request the resend. Never use this automatically.
- Time-based summaries require a separately authorized scheduler. No scheduling is installed by this skill.

## Failure and persistence rules

The helper enforces fixed recipient, TLS, task authorization, one terminal notification per run, transaction-based event claiming, bounded retries for definitely unsubmitted temporary failures, and conservative unknown states. Never edit its database to clear deduplication. Counts are derived from events and attempts, not incremented loosely. An interrupted send is converted to unknown after its lease expires; SMTP cannot guarantee exactly-once delivery.
