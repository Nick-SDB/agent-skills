"""Query the Codex weekly usage quota from the official ChatGPT wham/usage API.

Reads the stored authentication token and account id from ~/.codex/auth.json,
calls https://chatgpt.com/backend-api/wham/usage, and prints a readable report
of the plan, weekly window used/remaining percent, and the reset time.

The active HTTP(S)_PROXY environment is preserved on purpose: some networks
black-hole direct connections to chatgpt.com (e.g. IPv6 blocking), so the
proxy must be kept. Run this on the host shell, not inside the codex sandbox
(whose network is restricted).

Exit codes: 0 on success, 1 on failure (curl error, non-JSON body, missing auth).
"""

import datetime
import json
import os
import subprocess
import sys

USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"


def main() -> int:
    auth_path = os.path.expanduser("~/.codex/auth.json")
    try:
        with open(auth_path, encoding="utf-8") as fh:
            data = json.load(fh)
        token = data["tokens"]["access_token"]
        acct = data["tokens"]["account_id"]
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"读取 auth.json 失败: {exc}")
        return 1

    cmd = [
        "curl", "-sS", "-m", "25",
        "-H", f"Authorization: Bearer {token}",
        "-H", f"ChatGPT-Account-Id: {acct}",
        "-H", "Accept: application/json",
        "-H", "User-Agent: codex-cli/0.147.0",
        USAGE_URL,
    ]
    # Keep the inherited environment (HTTPS_PROXY / HTTP_PROXY etc.) unchanged.
    run = subprocess.run(cmd, capture_output=True, text=True)
    if run.returncode != 0:
        print("curl 失败:", run.stderr.strip())
        return 1
    try:
        payload = json.loads(run.stdout)
    except json.JSONDecodeError:
        print(f"响应非 JSON（HTTP 状态可能非 200）: {run.stdout[:200]}")
        return 1

    rate_limit = payload.get("rate_limit", {}) or {}
    primary = rate_limit.get("primary_window", {}) or {}
    secondary = rate_limit.get("secondary_window", {}) or {}
    used = primary.get("used_percent")
    remaining = (100 - used) if isinstance(used, (int, float)) else None
    reset_at = primary.get("reset_at")
    if reset_at:
        reset_str = (
            datetime.datetime.fromtimestamp(
                int(reset_at), datetime.timezone(datetime.timedelta(hours=8))
            ).strftime("%Y-%m-%d %H:%M")
            + " +08"
        )
    else:
        reset_str = "未知"
    reset_s = primary.get("reset_after_seconds")
    days = round(int(reset_s) / 86400, 1) if reset_s else None

    print("Codex 周额度汇报")
    print("  套餐        :", payload.get("plan_type"))
    print(f"  周窗口已用  : {used}%")
    if remaining is not None:
        print(f"  周窗口剩余  : {remaining}%")
    else:
        print("  周窗口剩余  : 未知")
    print(
        "  下次重置    :", reset_str, f"(约 {days} 天后)" if days is not None else ""
    )
    if secondary.get("used_percent") is not None:
        print("  次级窗口    : 已用", secondary.get("used_percent"), "%")
    else:
        print("  次级窗口    : 不适用")
    credits = payload.get("credits") or {}
    if credits.get("has_credits"):
        print(
            "  额外额度    :",
            f"balance={credits.get('balance')} unlimited={credits.get('unlimited')}",
        )
    else:
        print("  额外额度    : 无")
    return 0


if __name__ == "__main__":
    sys.exit(main())
