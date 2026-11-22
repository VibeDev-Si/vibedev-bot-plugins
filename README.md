# vibedev-bot-plugins

VibeDev 聊天里的机器人运行在 [maubot](https://github.com/maubot/maubot) 上。本仓库公开我们**修改过**的 maubot 插件的完整源码，许可证为 AGPL-3.0-or-later，另附把它们打成插件包（`.mbp`）的构建脚本。VibeDev 聊天正在运行的这些插件包，都由本仓库原样构建。

*English: complete source code of the maubot plugins that VibeDev modified (AGPL-3.0-or-later). Each directory is based on an upstream plugin and lists its changes; `python build.py` rebuilds, byte for byte, the packages VibeDev runs.*

| 目录 | 插件 ID 和版本 | 基于（上游） | 改动摘要 | VibeDev 聊天里的机器人 |
|---|---|---|---|---|
| [reminder/](reminder/) | `studio.vibedev.reminder` 0.2.2+vibedev.3 | [maubot/reminder](https://github.com/maubot/reminder)，提交 `06fc782c` | 中文回复和帮助、中文时间提示、默认北京时间、帮助里附源码链接 | VibeDev 提醒 |
| [dice/](dice/) | `xyz.maubot.dice` 1.1.0+vibedev.2 | [maubot/dice](https://github.com/maubot/dice)，提交 `94ca4b0e` | Python 3.14 修复、中文 `!roll help`（附源码链接） | VibeDev 工具箱 |

每个目录里有三份说明文件：
- `LICENSE`：上游原样；
- `README.md`：基于哪个上游、改了什么、版本记录；
- `upstream.patch`：相对上游提交的完整差异。

### 没有修改的插件

下面这些插件 VibeDev 聊天也在用，但**没有修改**，运行的是用上游源码原样构建的包。源码见上游，许可证都是 AGPL-3.0-or-later：

- choose（`coffee.maubot.choose` 0.1.0.3）：[coffeebank/coffee-maubot/choose](https://github.com/coffeebank/coffee-maubot/tree/87975b598701cb1a2f8fccb62103638a7b651cc5/choose)
- translate（`xyz.maubot.translate` 0.1.0）：[maubot/translate](https://github.com/maubot/translate/tree/6ea0b97dc97528ae9723787fdcc95b9207232ee4)
- reactbot（`xyz.maubot.reactbot` 2.2.0）：[maubot/reactbot](https://github.com/maubot/reactbot/tree/7fd6dd1a3c49cc338e036b3c894bd0e11559cd84)

maubot 本身（0.6.1）用的是官方镜像，原样使用：[maubot/maubot v0.6.1](https://github.com/maubot/maubot/tree/v0.6.1)。

## 构建

需要 Python 3.8 以上，只用标准库：

```sh
python build.py            # 构建所有插件，得到 dist/<插件 ID>.mbp 和 dist/SHA256SUMS
python build.py reminder   # 只构建一个
```

构建是可复现的：同一个提交在任何系统上构建，得到的包都逐字节相同。做法是：
- 包内文件按名字排序、不压缩；
- 时间戳固定为 1980-01-01，权限固定；
- `.gitattributes` 关闭了换行符转换。

本版本构建出的包如下，VibeDev 聊天里运行的就是这两个包：

| 包 | sha256 |
|---|---|
| `studio.vibedev.reminder.mbp` | `0c01a2944aa85bd71eabdd6d84c2282fdb1bd85b321989ecae9a4f6879650c5e` |
| `xyz.maubot.dice.mbp` | `a762b70cd5e187b4061a0bdfc564a5041703b404fe2970d16c964da9d76e51fb` |

## 历史

第一个提交（`6519394`）是原样导入的上游文件，之后的提交都是我们的改动。用 `git log -p` 或 `git diff 6519394 HEAD` 可以看到全部改动。

## 许可证

两个插件都沿用上游的 GNU Affero General Public License v3.0 or later，见 [LICENSE](LICENSE) 和各目录里的 `LICENSE`。

- 版权归原作者所有，我们的修改同样以 AGPL-3.0-or-later 发布。
- `build.py` 也以 AGPL-3.0-or-later 发布。

有问题或建议，欢迎提 issue。
