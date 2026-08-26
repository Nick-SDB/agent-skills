---
name: check-codex-quota
description: 查询 Codex 账号当前剩余的每周使用额度（weekly usage quota / limit）。通过官方 wham/usage API 读取已存储的认证 token 与账号 id，返回套餐、周窗口已用/剩余百分比与重置时间。Use when the user asks about codex 额度、配额、用量、剩余额度、周额度、quota、usage、limit，或想知道本周 Codex 还能用多少。
---

# Check Codex Weekly Quota

## 背景

Codex（ChatGPT 认证的 Pro 等套餐）在服务端按**周窗口（7 天 / 10080 分钟）**限额。额度信息不在本地，必须查询 ChatGPT 官方接口 `https://chatgpt.com/backend-api/wham/usage`。认证信息（access_token + account_id）存储在 `~/.codex/auth.json`。

## 完整查询命令（直接可用）

以下脚本读取 auth.json、带正确请求头调用 wham/usage，并打印可读结果。**保持当前环境的 HTTP(S)_PROXY 代理变量不变**：某些网络下直连 chatgpt.com 会超时（如 IPv6 被墙），走代理才可达；不要清除代理变量。

```python
python3 - <<'PYEOF'
import json, subprocess, os, datetime, sys

d = json.load(open(os.path.expanduser('~/.codex/auth.json')))
token = d['tokens']['access_token']
acct  = d['tokens']['account_id']

# 注意：保持当前环境（含 HTTPS_PROXY 等代理变量）不变，这是可用的网络路径
cmd = ['curl', '-sS', '-m', '25',
       '-H', f'Authorization: Bearer {token}',
       '-H', f'ChatGPT-Account-Id: {acct}',
       '-H', 'Accept: application/json',
       '-H', 'User-Agent: codex-cli/0.147.0',
       'https://chatgpt.com/backend-api/wham/usage']
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print('curl 失败:', r.stderr.strip()); sys.exit(1)
try:
    x = json.loads(r.stdout)
except json.JSONDecodeError:
    print('响应非 JSON（HTTP 状态可能非 200）:', r.stdout[:200]); sys.exit(1)

rl = x.get('rate_limit', {}) or {}
p  = rl.get('primary_window', {}) or {}
s  = rl.get('secondary_window', {}) or {}
used = p.get('used_percent')
remaining = (100 - used) if isinstance(used, (int, float)) else None
reset_at = p.get('reset_at')
reset_str = (datetime.datetime.fromtimestamp(int(reset_at), datetime.timezone(datetime.timedelta(hours=8)))
             .strftime('%Y-%m-%d %H:%M') + ' +08') if reset_at else '未知'
reset_s = p.get('reset_after_seconds')
days = round(int(reset_s) / 86400, 1) if reset_s else None

print('Codex 周额度汇报')
print('  套餐        :', x.get('plan_type'))
print(f'  周窗口已用  : {used}%')
print(f'  周窗口剩余  : {remaining}%' if remaining is not None else '  周窗口剩余  : 未知')
print('  下次重置    :', reset_str, f'(约 {days} 天后)' if days is not None else '')
print('  次级窗口    :', ('已用 ' + str(s.get('used_percent')) + '%') if s.get('used_percent') is not None else '不适用')
credits = x.get('credits') or {}
print('  额外额度    :', '无' if not credits.get('has_credits') else f"balance={credits.get('balance')} unlimited={credits.get('unlimited')}")
PYEOF
```

## 字段含义

| 字段 | 含义 |
| --- | --- |
| `plan_type` | 套餐（pro / plus / team ...） |
| `rate_limit.primary_window.used_percent` | **周窗口（10080 分钟 = 7 天）已用百分比**，剩余 = 100 - 该值 |
| `rate_limit.primary_window.reset_at` / `reset_after_seconds` | 窗口重置时间 / 距重置秒数 |
| `rate_limit.secondary_window` | 次级窗口（通常为 0 或不适用） |
| `credits` | 额外额度（has_credits / balance / unlimited），一般无 |

## 常见坑（实测经验）

1. **不要直连 chatgpt.com**：部分网络下直连会解析到 IPv6 导致连接超时；必须走代理（保留环境变量 `HTTPS_PROXY` / `HTTP_PROXY` 即可）。
2. **必须带 `ChatGPT-Account-Id` 头**：裸 curl 只有 `Authorization` 会 403（HTML 错误页），加上账号头 + `User-Agent: codex-cli/...` 才能 200。
3. **不要在 codex exec 沙箱里跑这个查询**：codex 沙箱网络受限（`codex doctor` 显示 network sandbox: restricted），其内部 curl 会 "Couldn't connect to server"。直接在宿主 shell 执行。
4. **token 过期**：auth.json 的 access_token 长期不刷新会失效（401/403）。此时先用 refresh_token 走 `POST https://chatgpt.com/backend-api/session`（body `{"refresh_token": ...}`）刷新，或让用户重新 `codex login`。

## 故障排查与兜底

- 若 `wham/usage` 非 200：优先检查（a）是否在沙箱内、（b）请求头是否完整、（c）token 是否过期。
- 兜底一：让 codex 自己查——`codex exec "报告你剩余的每周使用额度"`。codex 会尝试官方 API，失败时它会翻本地日志，但**日志是历史数据（可能过期数天）**，只能当参考。
- 兜底二：直接从本地日志读取最后一次已知用量（也是历史数据）：
  `strings ~/.codex/logs_2.sqlite | rg 'x-codex-primary-used-percent' | tail -n 1`，看响应头里的 `x-codex-primary-used-percent` / `x-codex-primary-reset-at` 等字段。
- 注意区分**实时值**（wham/usage 接口）与**历史值**（本地日志/响应头），汇报时说明数据时间。

## 验证

跑通后应输出类似：
```
Codex 周额度汇报
  套餐        : pro
  周窗口已用  : 24%
  周窗口剩余  : 76%
  下次重置    : 2026-09-01 22:15 +08 (约 6.2 天后)
```
