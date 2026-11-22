# 掷骰子（基于 maubot/dice 修改）

本目录**基于 [maubot/dice](https://github.com/maubot/dice) 修改**，原作者是 Tulir Asokan，许可证为 AGPL-3.0-or-later。

- **上游提交**：[`94ca4b0e`](https://github.com/maubot/dice/tree/94ca4b0e17bc2d968e31a55967dae5cecd0bdab1)（“Add Python 3.14 support”，上游版本号 1.1.0）。
- **许可和版权**：`LICENSE` 和源文件里的版权声明都保持上游原样。`dice.py` 在原有的许可声明后面加了「Modified by VibeDev」和修改时间。
- **插件**：插件 ID 不变，仍是 `xyz.maubot.dice`；版本号形如 `1.1.0+vibedev.N`。在 VibeDev 聊天里，这个插件由「VibeDev 工具箱」机器人运行。

## 改动

- **Python 3.14 修复**：Python 3.14 删除了 `ast.Str`、`.s` 和 `ast.Constant.n`。上游这个提交还有两处在用它们，所以在 Python 3.14 上（maubot 0.6.1 的官方镜像就是），`!roll 2d6` 这类带数字的算式会出错，`ord()` 也一样。现在这两处改用 `ast.Constant` 和 `.value`。
- **新增 `!roll help`**：用中文说明用法，末尾附本仓库的链接。这是 AGPL-3.0 第 13 条的要求：通过网络使用修改版的用户，要能拿到它的源码。
- **出错提示**：看不懂的写法，在原来的 “Bad pattern 3:<” 后面附中文提示，告诉用户可以发 `!roll help`。

**没有改的**：其他行为和配置项（`base-config.yaml`）与上游相同。

**完整差异**：
- [`upstream.patch`](upstream.patch)：相对上游提交的完整差异。
- 也可以在本仓库执行 `git diff 6519394 HEAD -- dice/`。

## 构建

在仓库根目录执行 `python build.py dice`，得到 `dist/xyz.maubot.dice.mbp`。

## 版本记录

| 版本 | 日期 | 内容 |
|---|---|---|
| 1.1.0+vibedev.2 | 2026-11-23 | 新增 `!roll help`（含源码链接）；出错时附中文提示；源文件加修改声明 |
| 1.1.0+vibedev.1 | 2026-11-22 | Python 3.14 修复。2026-11-23 之前运行的就是这个版本 |
