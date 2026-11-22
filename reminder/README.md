# VibeDev 提醒（基于 maubot/reminder 修改）

本目录**基于 [maubot/reminder](https://github.com/maubot/reminder) 修改**，原作者是 Tulir Asokan，许可证为 AGPL-3.0-or-later。

- **上游提交**：[`06fc782c`](https://github.com/maubot/reminder/tree/06fc782c1a5d3c24580cc5322f37b09e4bc03d36)（上游版本号 0.2.2）。
- **许可和版权**：`LICENSE` 和源文件里的版权声明都保持上游原样。改过的源文件，在原有的许可声明后面加了「Modified by VibeDev」和修改时间。
- **插件**：插件 ID 是 `studio.vibedev.reminder`，版本号形如 `0.2.2+vibedev.N`。在 VibeDev 聊天里，这个插件以「VibeDev 提醒」机器人的身份运行。

## 改动

- **插件 ID 和版本号**：ID 改为 `studio.vibedev.reminder`，避免和上游的 `xyz.maubot.reminder` 混淆；版本号用 `0.2.2+vibedev.N`。
- **中文回复**：所有回复和帮助都改成了中文。时间也用中文显示，例如「2 小时 30 分钟后」「在 2026-12-01 09:00（Asia/Shanghai，星期二）」。
- **默认时区**：没设置时区的用户默认用 `Asia/Shanghai`（`base-config.yaml`）。
- **时间参数可选**：时间参数改为可选。写的时间看不懂时，不再显示 maubot 的英文用法，而是用中文提示正确的写法。
- **错误提示中文化**：「时间已经过去」「不是有效的时区」「要回复提醒消息才能改期」等提示都改成了中文。
- **源码链接**：`!remind help` 的末尾附上本仓库的链接。这是 AGPL-3.0 第 13 条的要求：通过网络使用修改版的用户，要能拿到它的源码。
- **示例服务器名**：帮助里 `for @某人:<服务器>` 的示例，用机器人自己所在的服务器名，不再写死。

**没有改的**：
- 命令关键字：`remind`、`for`、`again`/`reschedule`、`list`、`tz`/`timezone`、`locale`、`locales`、`help`；
- 时间的解析方式；
- 数据库结构。

**完整差异**：
- [`upstream.patch`](upstream.patch)：相对上游提交的完整差异，可以在上游仓库里直接 `git apply`。
- 也可以在本仓库执行 `git diff 6519394 HEAD -- reminder/`，第一个提交是原样导入的上游文件。

## 构建

在仓库根目录执行 `python build.py reminder`，得到 `dist/studio.vibedev.reminder.mbp`。构建方法和校验值见[根目录说明](../README.md)。

## 版本记录

| 版本 | 日期 | 内容 |
|---|---|---|
| 0.2.2+vibedev.3 | 2026-11-23 | 帮助末尾加源码链接；`for` 示例的服务器名改为自动获取；源文件加修改声明 |
| 0.2.2+vibedev.2 | 2026-11-22 | 中文回复和帮助、中文时间提示、默认北京时间。2026-11-23 之前运行的就是这个版本，和 vibedev.3 的区别只有上一行列出的几点 |
