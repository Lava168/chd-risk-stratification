# GitHub 建仓与推送

推荐将远程仓库设为 private。

如果本机安装并登录了 GitHub CLI，可在仓库目录执行：

```bash
gh repo create Lava168/chd-risk-stratification --private --source=. --remote=origin --push
```

当前机器未检测到 `gh` 命令。也可以在 Codex 中安装 GitHub 插件后，由 Codex 直接创建远程仓库、添加 remote 并 push。

手动方式：

1. 在 GitHub 新建 private 仓库 `chd-risk-stratification`。
2. 在本地执行：

```bash
git remote add origin https://github.com/Lava168/chd-risk-stratification.git
git push -u origin main
```
