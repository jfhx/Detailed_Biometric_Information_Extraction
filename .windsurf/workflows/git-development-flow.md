---
description: Detailed Biometric Extraction 项目的 Git 开发提交流程
---
1. 确认你在项目根目录，并查看当前工作区状态。

```bash
git status --short --branch
```

2. 如果你准备开始一个新改动，先同步主分支。

```bash
git checkout main
git pull --ff-only origin main
```

3. 为本次任务创建功能分支。分支名建议包含任务主题。

```bash
git checkout -b feat/<short-topic>
```

4. 完成代码修改后，优先做一次本地快速验证。这个项目建议先跑小批量模式。

```bash
python main.py --limit 5
```

如果你只修改了很小的逻辑，也至少执行一次你改动相关的最小验证步骤。

5. 提交前检查变更内容，避免把缓存、日志或 IDE 文件带进仓库。

```bash
git status --short
git diff -- . ':(exclude)source_text_report.xlsx'
```

6. 暂存并提交本次改动。

```bash
git add .
git commit -m "feat: <summary>"
```

如果只是修复 bug，可改用：

```bash
git commit -m "fix: <summary>"
```

7. 将分支推送到 GitHub。当前仓库推荐使用 SSH 远程。

```bash
git push -u origin feat/<short-topic>
```

8. 合并前再次确认主分支是最新的；如有需要，先在功能分支上同步主分支。

```bash
git fetch origin
git rebase origin/main
```

如果你不熟悉 rebase，也可以使用：

```bash
git merge origin/main
```

9. 功能合并完成后，回到主分支并同步远程。

```bash
git checkout main
git pull --ff-only origin main
```

10. 如果功能分支已经不再需要，可以清理本地和远程分支。

```bash
git branch -d feat/<short-topic>
git push origin --delete feat/<short-topic>
```

补充说明：

- 本项目已经配置了 `.gitignore`，通常不应提交 `.idea/`、`__pycache__/`、`out/`、日志文件和虚拟环境目录。
- `source_text_report.xlsx` 当前是仓库中的已跟踪输入文件，不会因为 `.gitignore` 规则而自动消失；如需改成不跟踪，应单独处理。
- 如果 HTTPS 推送不稳定，优先继续使用 SSH 远程：`git@github.com:jfhx/Detailed_Biometric_Information_Extraction.git`
