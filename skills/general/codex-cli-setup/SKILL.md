---
name: codex-cli-setup
description: 在 Linux 服务器或容器上安装、升级和排查 Codex CLI 及桌面客户端 SSH 远程运行环境，保留完整包树，检查后台服务与配套宿主的版本和路径，并验证登录与真实工具调用；避免为安装引入 node 运行时。
---

# Codex CLI 安装与登录

目标是在目标机器上得到一个能真正发请求的 `codex`，而不只是"装上了"。

## 先判断环境

确认系统与架构、是否已有 `codex` 及其版本、出网能力。如果机器由 ChatGPT/Codex 桌面客户端通过 SSH 连接，还要检查正在运行的 `app-server`：PATH 中的新 CLI 与桌面客户端使用的旧后台服务可能不是同一版本。**不要因为看到 npm 就先去装 node**：Codex 的平台压缩包里是静态二进制，不需要 node 运行时。

## 一、先测速，再决定渠道

同一台机器上不同源的差距可能是数量级。取 3 MB 片段实测，不要凭印象选：

```bash
curl -s -m 10 -L -o speedtest.bin -w '%{http_code} %{speed_download} B/s\n' -r 0-3000000 '<候选 URL>'
```

以 0.163.0 为例的候选：

| 渠道 | URL 形态 |
|---|---|
| npm 平台包 | `https://registry.npmjs.org/@openai/codex/-/codex-0.163.0-linux-x64.tgz` |
| GitHub release | `https://github.com/openai/codex/releases/download/rust-v0.163.0/codex-x86_64-unknown-linux-musl.tar.gz` |

实测参考：GitHub 约 170 KB/s，npm 约 0.4–4.5 MB/s（波动很大，所以每次都要重测），150 MB 量级的包相差数分钟到十几分钟。

容易踩错的一点：平台包**没有**独立的 `@openai/codex-linux-x64` 包（查它返回 404），真实包名仍是 `@openai/codex`，平台信息放在版本号后缀上（`0.163.0-linux-x64`）。要确认就用主包的元数据看 `optionalDependencies`，或用下面的方式直接拼出地址：

```bash
V=0.163.0
curl -fsSL https://registry.npmjs.org/@openai/codex \
  | python3 -c 'import json,sys;v=sys.argv[1];print(json.load(sys.stdin)["versions"][v]["dist"]["tarball"].replace(f"/codex-{v}.tgz", f"/codex-{v}-linux-x64.tgz"))' "$V"
```

## 二、安装：装完整包树，不要只拿二进制

```bash
V=0.163.0
PREFIX="${PREFIX:-$HOME/.local/opt/codex-$V}"   # 每个版本一个目录，便于回滚
mkdir -p "$PREFIX" && cd "$PREFIX"
curl -fL --retry 3 -o pkg.tgz '<最快渠道的 URL>'
tar xzf pkg.tgz
TARGET="$(ls package/vendor | grep -m1 "$(uname -m)" || ls package/vendor | head -1)"
find "package/vendor/$TARGET" -maxdepth 2 -type d
REAL="$PREFIX/package/vendor/$TARGET/bin/codex"
file "$REAL"
mkdir -p "$HOME/.local/bin"
WRAPPER="$HOME/.local/bin/codex"
printf '#!%s\n' "$(command -v sh)" > "$WRAPPER"
printf 'exec "%s" "$@"\n' "$REAL" >> "$WRAPPER"
chmod 0755 "$WRAPPER"
codex --version
```

升级时不要就地覆盖二进制：解包到新的版本目录，然后只改 wrapper 里的那一行路径，旧目录留着随时回滚。wrapper 里的路径是写死的，改完记得重新验证。

更换已有入口时，先在同目录写好临时 wrapper，设置执行权限并验证目标，再原子替换入口；不要直接重定向覆盖仍可能正在使用的 ELF 文件。切换入口不会升级已经运行的后台服务。在完成下文的后台进程核对前，不删除旧版包树。

压缩包里有四块东西，缺一不可：

| 位置 | 作用 |
|---|---|
| `vendor` 下目标三元组的 `bin` 目录里的 `codex` | 主程序（静态 ELF） |
| 同目录的 `codex-code-mode-host` | code mode 宿主 |
| 同级的 `codex-resources` 目录 | 自带的 bwrap、ripgrep、zsh 等运行时资源 |
| 包根的 `package.json` | 包标识，用于解析包根 |

### 陷阱一：只拷主二进制

把主程序那一个文件单独 `install` 到 PATH 里，`codex exec` 这类一次性调用**看起来完全正常**，但交互式入口会直接失败：

```
Error: this CLI has no complete local package; install a packaged Codex CLI or use the standalone installer
To work without the background server, rerun the same command with --no-daemon (including resume or fork and its arguments).
```

这条报错容易被误读成"登录/凭证有问题"或"要去装 npm 包"，实际原因是程序按**自身所在位置**推断包根，只搬走一个文件就找不到同级的 `codex-resources` 和 `package.json`。`--no-daemon` 只是绕过，不是修复。

### 陷阱二：用符号链接接进 PATH

装好完整包树后，若在 PATH 里放一个 `ln -s` 指向包内二进制，TUI 能正常起来，但模型一开始调用工具就失败：

```
工具运行环境缺少 <PATH 目录>/codex-code-mode-host
```

或启动时提示 `Code Mode is unavailable because failed to spawn code-mode host ...`。

原因：`code-mode-host` 的路径是按**被调用路径的目录**拼接的，不跟随符号链接还原。链接放在 `~/.local/bin`，它就去 `~/.local/bin` 里找宿主程序，而那里没有。

因此要用**包装脚本 `exec` 真实路径**（如上），让 `argv[0]` 落在包内 `bin` 目录；或干脆把包内 `bin` 目录本身加入 `PATH`。不要用 `cp` 挪走二进制，也不要用符号链接。

### 陷阱三：入口已修复，桌面客户端仍使用旧后台服务

出现缺失宿主错误时，不要只检查 `codex --version` 或重新打开聊天。先核对实际服务：

```bash
command -v codex
codex --version
ps -eo pid,args | grep '[c]odex.*app-server'
# 从上面的输出确认实际服务 PID，不要误选 app-server proxy
PID=<实际服务PID>
readlink "/proc/$PID/exe"
"/proc/$PID/exe" --version
```

结合该聊天的错误日志，确认它实际尝试启动的 `codex-code-mode-host` 路径。`/proc/<PID>/exe` 显示 `(deleted)`，说明正在运行的是已被替换的旧文件；进程仍能工作，但不会自动切换到新 wrapper。已观察到旧后台服务为 0.162.1、PATH 入口为 0.163.0，服务仍查找 `/usr/local/bin/codex-code-mode-host` 的情况。

处理方式按会话状态选择：

- 正常升级：在当前任务可中断时，通过客户端断开并重新连接该 SSH 主机，使其重建远程后台服务。随后再次检查实际服务的 PID、可执行路径和版本。关闭一个聊天或重开 TUI 不代表后台服务已经重启；不要无差别 `pkill codex`。
- 保留现有会话的兼容修复：若报错路径缺失，且旧版完整包树还在，可在报错的精确位置创建一个指向**正在运行的旧服务同版本**宿主的软链接。例如下例仅适用于已确认 `/opt/codex` 与旧服务版本相同的情况：

  ```bash
  HOST=/opt/codex/package/vendor/x86_64-unknown-linux-musl/bin/codex-code-mode-host
  test -x "$HOST" && "$HOST" --help
  # 只在目标既不存在也不是悬空链接时创建；不覆盖已有文件
  if [ ! -e /usr/local/bin/codex-code-mode-host ] && [ ! -L /usr/local/bin/codex-code-mode-host ]; then
    ln -s "$HOST" /usr/local/bin/codex-code-mode-host
  fi
  /usr/local/bin/codex-code-mode-host --help
  ```

  这是旧服务的配套宿主兼容链接，不是把主程序用软链接装进 PATH。不要将旧服务的宿主链接到最新版，也不要把它当作正常安装的替代。记录链接目标，在旧服务退出前保留对应包树；后续重连并验证新服务后再清理这项兼容链接。

修复后先在原报错聊天中重试工具调用。补回原路径可能使旧服务直接恢复，不要断言所有修复都必须重启；若仍失败，再根据新的日志处理或重建后台服务。

`file` 应报告 `static-pie linked` 或 `statically linked`；若显示动态链接且缺库，换 musl 构建。

装好后确认它在 `PATH` 里；非交互 shell 不读 `.bashrc`，需要时补 `~/.profile` 或使用绝对路径。

## 三、凭证

只拷 `~/.codex/auth.json`，权限设为 600。

**不要整份拷 `config.toml`**：里面有本机绝对路径、`notify` 里指向本机可执行文件的命令，以及其他平台的 trust 记录，在服务器上无意义甚至报错。只挑可移植项：

```toml
model_context_window = 256000
model_auto_compact_token_limit = 230000
model = "<本地使用的模型名>"
model_reasoning_effort = "low"
service_tier = "priority"
```

## 四、验证

按实际使用入口验收：

1. 离线态：`codex login status` 应输出 `Logged in using ChatGPT`。这只证明文件格式被识别，**不证明能用**。
2. 真实请求：让标准输入立即 EOF，否则会停在 `Reading additional input from stdin`：

```bash
true | codex exec --skip-git-repo-check 'Reply with exactly: CRED_OK'
```

成功标志是输出里出现 `CRED_OK` 并打印 token 用量。只看到 `login status` 正常就宣称可用，是最常见的误判。

3. 工具调用：前面两步不足以确认 `code-mode-host` 可用。宿主的 `--help` 也只证明组件可启动，不等于模型的工具链已通过。

```bash
true | codex exec --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox \
  'Run the shell command: echo TOOL_OK. Then reply exactly: DONE'
```

输出里应看到命令真正执行（`TOOL_OK`），且没有 `failed to spawn code-mode host` 之类的降级提示。

4. 桌面客户端 SSH 入口：如果用户从客户端连接远程主机，必须在原报错聊天或同一主机的新聊天中验证工具执行；新启动的 `codex exec` 成功不能证明旧 `app-server` 已恢复。使用临时目录做「执行命令 → 写入随机标记 → 读回校验」测试，要求看到实际工具结果及无宿主启动错误。只有用户已授权安装技能时，才继续真实安装任务；不要为了验证擅自安装示例技能。

无法直接操作原客户端聊天时，明确报告已验证的范围（例如组件启动、目录权限、CLI 工具调用），并提供一条供用户在原聊天执行的重试指令。没有该入口的真实工具结果，不宣称端到端恢复。升级验收同时记录 PATH CLI 和实际后台服务版本。

## 常见告警（通常无害）

| 告警 | 含义 |
|---|---|
| `disable_response_storage is ignored` | 该版本的配置项已废弃，删掉即可 |
| `Code Mode is unavailable ... code-mode-host` | 检查完整包树、主程序入口，以及仍运行的旧 app-server 的实际宿主路径（见安装一节的陷阱二、三） |
| `could not find bubblewrap on PATH` | 会用包内自带的 bwrap，不影响运行 |
| `failed to refresh available models: request timed out` | 模型目录拉取超时，回退到内置目录，不影响调用 |

## 边界

- 不在命令行参数、shell 历史、日志或提交记录里出现 token。
- 不为了装 codex 引入 node/npm 运行时；只有必须用 npm 安装方式时才付这个代价。
- 不把本机的完整 `config.toml` 或 `sessions/` 之类的状态目录搬到服务器。
- 凭证属于个人账号：只在用户明确要求的那台机器上落地。
