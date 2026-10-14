# AIDA 客户端

来源：AIDA 指南中心；角色：工程师；提取日期：2026-10-14。

## 安装或更新 AIDA 客户端

根据 Windows、macOS 或 Linux 安装客户端，并使用自动检查或 aida update 保持最新版本。

### Windows PowerShell

在 PowerShell 中执行下面的命令。完成后关闭终端并重新打开。

Windows 安装命令

```powershell
Invoke-RestMethod http://113.100.143.91:9180/statics-live/aida/install.ps1 | Invoke-Expression
```

### macOS / Linux

在终端中执行安装脚本。脚本会自动选择当前系统支持的客户端文件。

macOS / Linux 安装命令

```bash
curl -fsSL http://113.100.143.91:9180/statics-live/aida/install.sh | bash
```

### 更新客户端

执行 login、upload 或 status 时，AIDA 会先检查最新版本；发现新版后会校验并安装，再继续当前命令。也可以随时手动检查更新。

立即检查并更新

```text
aida update
```

如果自动更新或 aida update 失败，请重新执行当前系统的安装命令，再用 aida version 核对版本。

### 确认安装结果

查看版本

```text
aida version
```

查看帮助

```text
aida help
```

如果提示找不到 aida 命令，先重新打开终端；仍无效时再检查安装输出中的 PATH 提示。

最后核对：2026-07-28

## 登录客户端并检查状态

使用个人令牌绑定 AIDA 服务，并确认当前终端登录身份正确。

### 登录

安装脚本已经自动配置当前 AIDA 服务环境。先在 AIDA 右上角打开个人菜单并选择“复制 Token”，然后执行下面的命令并按提示粘贴 Token。

登录命令

```text
aida login
```

不要把 Token 直接写在命令参数中，避免被终端命令历史保存；按交互提示粘贴即可。

### 核对身份

- Server 由安装脚本自动配置，普通用户无需填写或修改。
- User 应是你自己的姓名和角色。
- 如果身份不符，不要继续上传，重新登录正确账号。

查看登录状态

```text
aida status
```

最后核对：2026-07-28

## 个人设备上传 Session

在个人设备上交互选择或批量同步 Claude Code、Codex 工作记录。

### 开始前确认

- 已经安装 AIDA 客户端，并通过 aida status 确认当前登录身份正确。
- 本机已经使用 Claude Code 或 Codex 完成过工作，客户端会扫描对应的本地 Session。
- 本页介绍个人模式：上传结果归当前登录账号。多人共用同一系统账号的开发机请改用团队模式。
- 令牌只用于本人设备登录，不要粘贴到群聊、需求描述或截图中。

### 选择并上传

- 执行 aida upload 进入全屏选择器，并在其中确认待上传记录的项目、时间和摘要。
- 使用方向键或 j/k 移动，按 Space 勾选；需要缩小范围时按 / 搜索。
- 检查顶部已选择数量，确认后按 Enter 上传。

交互选择并上传

```text
aida upload
```

首次使用建议交互选择，不建议直接使用 --all；这样可以先排除无关项目或包含敏感上下文的 Session。命令 --all 仍是个人模式，不会按团队目录分发。

### 全屏选择器操作

- 使用 ↑/↓ 或 j/k 移动光标，按 Space 勾选或取消当前 Session；页面顶部持续显示已选择数量。
- 按 / 进入搜索，输入项目路径、Session ID、摘要或最新消息关键词；按 Enter 结束输入并保留筛选结果，按 Esc 退出搜索输入。
- 按 a 选择或取消当前搜索结果中的全部 Session；未搜索时等于选择全部本地可发现 Session，执行前必须确认没有无关或敏感记录。
- 确认范围后按 Enter 开始上传；按 q 或 Ctrl+C 取消且不上传。

当前选择器会显示项目、摘要、Session ID 和最新消息；方向键移动，Space 选择，/ 搜索，a 全选当前结果，Enter 上传。

### 怎么看上传结果

前往 Session 页面确认记录已出现。首次成功上传会形成一个可选切片；同一 Session 有新增内容后再次上传，会只上传新增内容并形成新的独立切片。没有新增内容时客户端会跳过，上传失败或重复操作不会产生可选的重复切片。一次上传即使包含跨天内容，也仍形成一个完整切片。

- READY：服务端已经处理完成，可以用于日报或周报。
- PROCESSING：上传已接收，服务端仍在处理；先等待，不要连续重复上传。
- CURRENT：本地 Session 仍在追加，本次已上传当前完整快照；后续有新内容时再次执行 upload。
- FAILED 或 BLOCKED：本次未达到可用状态，保留错误码和发生时间后重试或联系平台负责人。

最后核对：2026-07-28

## 共享开发机使用团队同步

多人共用一台开发机时，按工作目录把 Session 同步到对应团队成员。

### 什么时候使用团队模式

- 多人共用同一个系统账号，并共同使用这台机器上的 Claude Code 或 Codex 时，使用团队模式。
- 个人电脑或只需要上传本人 Session 时，继续使用 aida upload、aida upload --all 或个人自动同步。
- 团队模式仍使用普通个人 Token 登录，不需要创建或保管团队账号、团队 Token。共享机上登录的账号必须属于目标团队。

### 1. 每位成员配置自己的目录

- 每位成员分别登录自己的 AIDA 网页账号，进入“我的 Token”。
- 在日期选择器后点击文件夹图标，打开“团队同步目录”。
- 添加本人工作目录的绝对路径，例如 `<本人工作目录的绝对路径>`；该目录及其子目录都会归属本人。
- 不同成员不能配置相同或互相包含的目录；不能配置文件系统根目录 /。

目录由成员自行维护。修改目录只影响后续团队同步；已上传 Session 不会自动迁移。删除目录后，该目录下新旧 Session 都会停止后续团队同步。

团队同步目录入口位于日期范围选择器最右侧的文件夹按钮，图中已用红色描边标出。

### 2. 在共享机登录并立即同步

- 共享机上的任一团队成员执行 aida login，使用自己的个人 Token 登录。
- 执行 aida status，确认登录身份和服务地址正确。
- 执行 aida upload --team。团队模式会扫描全部本地 Session，不会打开逐条选择器。
- 命中成员目录的新 Session 会直接进入该成员的个人数据；既有 Session 继续沿用原归属。

团队模式立即同步

```text
aida login
aida status
aida upload --team
```

### 3. 开启团队自动同步

设置一次后，AIDA 会按选择的北京时间每天自动执行团队同步。

开启团队自动同步

```text
aida auto-sync enable --team
```

检查自动同步状态

```text
aida auto-sync status
```

普通 aida auto-sync enable 开启的是个人模式。团队模式不会由登录、升级或其他命令自动开启。

### 4. 处理待配置目录

- 如果上传结果显示“待配置”，执行 aida log 查看目录和受影响的 Session 数。
- 让对应成员在“我的 Token”的文件夹入口补充该绝对目录。
- 配置完成后再次执行 aida upload --team；未配置期间内容不会被上传，也不会自动归给登录者。

查看团队同步待配置目录

```text
aida log
```

### 归属规则

- 目录只决定新 Session 的个人归属；同一 Session 建立后不会因为登录账号或目录配置变化而换人。
- 团队模式上传的 Session 直接计入归属成员的个人 Token、成本、Session 和日报统计。
- 旧 Session 已经传错账号时不会由日常同步自动拆分，需要联系平台负责人按确认目录执行一次性历史归属迁移。
- 目录未配置、Session 身份重复或原归属已不在当前团队时，对应 Session 不会上传；保留终端错误信息交给平台负责人处理。

最后核对：2026-07-28

## 设置每天自动同步

选择个人或团队模式，设置每天的北京时间，并检查或关闭后台同步。

### 选择同步模式

个人设备：开启个人自动同步

```text
aida auto-sync enable
```

共享开发机：开启团队自动同步

```text
aida auto-sync enable --team
```

个人模式把 Session 上传到当前登录账号；团队模式按网页中配置的成员目录分发。两种模式需要显式选择，不会自动互相切换。

### 管理自动同步

- enable 和 set-time 会在终端中引导选择每天的同步时间，页面显示统一使用北京时间。
- 也可以执行 aida status，同时检查登录、连接和自动同步状态。
- 客户端更新后会自动恢复已开启的同步任务；需要改变个人/团队模式时，重新执行对应的 enable 命令。

查看自动同步状态

```text
aida auto-sync status
```

修改每天同步时间

```text
aida auto-sync set-time
```

关闭自动同步

```text
aida auto-sync disable
```

最后核对：2026-07-28

## 同步其他 AI 编程客户端

检测 OpenCode、Kimi Code、OpenClaw 和 WorkBuddy，并显式选择可上传的 Session。

### 检测本机客户端

Claude Code 和 Codex 直接使用 aida upload；其他客户端先检测，再使用 upload-client。

检测支持的客户端

```text
aida clients
```

### 上传 OpenCode 或 Kimi Code

交互选择 Session

```text
aida upload-client opencode
aida upload-client kimi_code
```

上传全部 Session

```text
aida upload-client opencode --all
aida upload-client kimi_code --all
```

### 上传 OpenClaw

OpenClaw 可能包含私人或非编码对话，因此必须逐条选择，不支持 --all。

打开选择器

```text
aida upload-client openclaw
```

按 Session Ref 上传

```text
aida upload-client openclaw <session-ref>
```

WorkBuddy 当前只支持检测，不支持上传；以 aida clients 的检测结果为准。

最后核对：2026-07-28

## Session 切片如何形成

了解首次上传、后续增量上传、跨天内容与报告选择之间的关系。

### 什么是 Session 切片

Session 切片是一次成功上传的内容范围。首次上传某个本地 Session 时，当前已有内容形成第一个切片；以后再次上传同一 Session 时，只把上次成功上传之后的新增内容形成新切片。

切片不是“一个 Session 的全部内容”，也不是“每个自然日一个切片”。

### 固定形成规则

- 一次成功上传最多形成一个切片；同一 Session 多次成功增量上传，可以形成多个独立切片。
- 切片不按自然日拆分。一次上传的新增内容即使横跨多天，仍然只形成一个完整切片。
- 没有新增内容时会跳过，不会形成新切片。
- 上传失败不会形成可选切片；重复操作同一段内容也不会形成重复切片。
- 每个切片的摘要只描述该切片自身包含的内容。

### 切片如何用于个人报告

- 同一 Session 形成的多个切片，会在个人日报和个人周报的 Session 选择列表中显示为多条可独立选择的记录。
- 手动选择切片后，已选切片是本次报告的权威 Session 来源；未选切片不会混入。
- 候选列表的日期范围只用于筛选记录。跨天切片只要与筛选日期相交，就会作为完整切片使用，不会按日期裁剪。
- 不手动选择切片时，系统会按日报日期或周报周期冻结默认的 Session 来源快照。

### 与 Token 统计的区别

报告 Session 切片用于决定 AI 报告读取哪些工作内容；Token 页面则按实际使用时间统计 Token 和成本。两者用途和日期口径不同，不能用报告切片数量或列表中的 Token 直接代替 Token 统计结果。

最后核对：2026-07-28

## 选择、上传与问题排查

掌握交互搜索、批量上传和常见失败的处理方式。

### 常用命令

交互选择并上传

```text
aida upload
```

个人账号上传全部本地 Session

```text
aida upload --all
```

共享机按团队目录上传全部 Session

```text
aida upload --team
```

查看团队模式待配置目录

```text
aida log
```

### 交互模式与直接模式

- 直接执行 aida upload 会进入全屏交互选择，支持键盘移动、勾选和搜索，适合首次上传和需要核对范围的场景。
- aida upload --all 会按当前登录账号处理全部本地可发现 Session，不是最近一页；无变化的 Session 会跳过，但仍应先检查上传范围。
- aida upload --team 同样扫描全部本地 Session，但按当前团队成员配置的工作目录分发；它不会打开选择器。

### 选择器为空

- 确认本机确实运行过 Claude Code 或 Codex，并产生了 Session。
- aida upload 会直接扫描全部本地可发现 Session，不需要先执行单独的列表命令。
- 如果刚开始使用 Claude Code 或 Codex，请先完成一段真实工作并退出当前会话，再重新执行 aida upload。

### 上传失败或超时

- 先执行 aida status，确认安装配置存在且登录身份正确。
- 确认网络可以访问 AIDA，再重试单条 Session。
- 较大的 Session 解析时间更长；不要在上传过程中重复启动多次相同命令。
- 仍失败时保留终端中的错误摘要和发生时间，联系平台负责人排查。

最后核对：2026-07-28
