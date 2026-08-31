---
name: skill-sync-cloud
description: Synchronize a local Agent Skills repository with its remote (cloud) origin — push new or updated skills/versions up, pull remote updates down and install them locally. Use when asked to sync a skill repo and its remote, add local skills to the repo and push, or fetch remote updates and install them.
---

# Skill Sync Cloud

双向同步一个 Agent Skills 仓库与其云端远端：把本地新增/更新的 skill 推上去，把远端的更新拉下来并安装到本地。**push 与安装都要先经过用户确认。**把仓库当作本地事实源，远端当作云端副本。

## 前置检查

1. 确认仓库根目录与远端配置存在：`git remote -v`（有 `origin` 等可 push/pull 的远端）。
2. 确认当前分支（一般 `master`/`main`），并核对 `git status`，先看清未提交改动。
3. 确认本机已安装 skill 的安装方式（`python3 tools/skillctl.py install --help`：`--target`、`--scope`、`--home`/`--project-root`、`--mode`）。
4. 不要因为仓库里装了某个可选的 skill 就去改宿主账号或安装新的 CLI；保持宿主配置决策留在用户手里。

## 方向一：把本地 skill 推送到云端（push）

把本地新增或更新的 skill 提交到仓库并推送到远端。**在 commit 与 push 前都要获取用户确认。**

1. **识别变更**：`git status --short` 找出新增/修改的 skill 源文件（`skills/<category>/<name>/...`）。
   - 新增 skill：确认对应目录文件齐全（`SKILL.md` 及必要资源），并在 `registry.json` 里登记（category/name/source/targets/version）。
   - 更新 skill：确认版本号与内容一致（需要时在 `registry.json` 里递增 `version`）。
2. **校验与渲染**：
   - `python3 tools/skillctl.py validate` 通过（frontmatter 只能 `name`+`description`，SKILL.md ≤500 行，资源链接合法）。
   - `python3 tools/skillctl.py render --target all --output dist` 重建各目标分发。
   - `python3 tools/skillctl.py render --target all --output dist --check` 校验分发一致。
   - `python3 -m unittest discover -s tests -v` 跑测试（如存在）。
3. **提交前确认**：展示 diff 摘要（`git diff --stat` / 关键内容），**获取用户批准后再 `git add` + `git commit`**。
4. **推送前确认**：确认目标分支与远端后，**获取用户明确批准**再 `git push origin <branch>`。绝不 force-push。

## 方向二：从云端拉取更新并安装（pull + install）

把远端的新 skill 或版本更新拉下来，并安装到本机。**拉取合并与安装都有风险时须先确认。**

1. **拉取前检查**：`git fetch origin` 看远端更新；核对本地是否有未提交/未推送的改动可能冲突。`git status --short` + `git log HEAD..origin/<branch> --oneline`。
2. **拉取前确认**：若有本地改动可能被覆盖，或合并会产生冲突，**先向用户确认**拉取/合并方式（rebase 或 merge），不要静默改写。
3. **拉取**：
   - `git pull --ff-only origin <branch>`（优先快进），或 `git pull --rebase`（用户确认后）。
   - 冲突时停下，向用户报告冲突文件与解决方案，不要强行解决。
4. **重构分发**：拉取后重新 `render --target all --output dist --check` 并 `validate`，保证本地分发与新版源码一致。
5. **安装前确认**：确定目标（`--target` 与 `--scope user/project`，精确路径用 `--home`/`--project-root`/`--destination`）。**获取用户确认安装目标后**再执行安装：
   - `python3 tools/skillctl.py install --target <target> [--scope user]`（copy 模式默认）。
   - 或用 `--dry-run` 先预览再装；`--check` 验证已装内容是否一致。
6. **安装后验证**：确认安装目录出现更新后的 skill（例如 `ls` 对应 `user_path` 下的 skill 目录），报告拉取到的更新、安装结果与版本。

## 报告

汇报：push 的提交 hash 与推送状态；pull 拉到的更新列表；安装的目标与目录；任何冲突或遗留未同步项。所有"写做出"操作（commit、push、install）都要标注是否已获用户确认。

## 反模式

- 未经确认就 commit / push / install。
- force-push 或改写远端历史。
- 在安装前跳过校验/渲染，导致装到不一致或损坏的 skill。
- 静默覆盖本机已有 skill 的本地编辑或未管理文件。
