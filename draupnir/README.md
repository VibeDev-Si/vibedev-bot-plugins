# Draupnir：豁免指定发送者（防刷屏、防群发 @）

VibeDev 聊天的「VibeDev 安全助手」是 [Draupnir](https://github.com/the-draupnir-project/Draupnir) 3.2.0（官方镜像 `gnuxie/draupnir@sha256:97fbf71d7b477f27ca7805d975e198f426fda737b4bc405548aba639a10d473d`）。本目录是我们对它的唯一改动：让**防刷屏**（`BasicFloodingProtection`）和**防群发 @**（`MentionLimitProtection`）不处理指定的发送者。

*English: a two-file patch for Draupnir 3.2.0 that makes the flooding and mention-limit protections ignore the senders listed in `VIBEDEV_DRAUPNIR_EXEMPT_SENDERS` (comma-separated Matrix user IDs). With the variable empty or unset, behaviour is exactly upstream's. Apache-2.0, like the two files it changes.*

## 为什么

「VibeDev AI 助手」（`@vibedev-ai:matrix.vibedev.studio`）会在短时间内连续回答好几个人，一分钟内回复满 15 条、或者一条回答里提到 5 个以上的人，都很正常。Draupnir 3.2.0 没有按用户豁免的设置：除了它自己，这两项保护对所有发送者一视同仁，会封禁 AI 助手、删掉它的回答。

**违规词保护（`WordListProtection`）没有改**：它只管新成员进群后 20 分钟内的发言。如果有人诱导 AI 说出底线词，这时候照样处理是对的；万一 AI 助手因此被封禁，管理员可以在管理室解封。

## 改了什么

两个文件各加几行，见 [exempt-senders.patch](exempt-senders.patch)：

- 文件开头读取环境变量 `VIBEDEV_DRAUPNIR_EXEMPT_SENDERS`（逗号分隔的 Matrix 用户 ID），得到豁免名单；
- 保护处理消息时，紧跟在「是 Draupnir 自己就跳过」之后，加一条「在豁免名单里就跳过」：豁免的发送者既不计数，也不处理；
- 名单为空或没有设置时，和原版完全一样。
- 文件头加了修改说明，原有的版权和许可证声明保留。

| 文件（镜像里 `/apps/draupnir/dist/protections/`） | 原版 sha256 | 改后 sha256 |
|---|---|---|
| `BasicFlooding.js` | `306eab1bae964f758e20651c1d61bdcabf06d773d2d1334e7c397b063850d87e` | `d4d58ca95fd3e65c674ded3107490f50015b3173c82304ec407ffee30168ea6a` |
| `MentionLimitProtection.js` | `9c837d6ce282920bde07839bb1771513ab557e3f3438b6a6cdaf393af880dbbe` | `5e6c7a63f0b8968df1da2cfc398639c3fd41f04b5c179d62b7533c701fbf51f1` |

## 怎么用

不重建镜像：把 [patched/](patched/) 里的两个文件**只读挂载**到镜像里的同名文件上，再设环境变量。docker compose 的写法：

```yaml
    environment:
      VIBEDEV_DRAUPNIR_EXEMPT_SENDERS: '@vibedev-ai:matrix.vibedev.studio'
    volumes:
      - ./patch/BasicFlooding.js:/apps/draupnir/dist/protections/BasicFlooding.js:ro
      - ./patch/MentionLimitProtection.js:/apps/draupnir/dist/protections/MentionLimitProtection.js:ro
```

补丁只适用于上面这个镜像（原版文件的 sha256 必须一致）。换 Draupnir 版本时要重新核对、重新做补丁。

**撤销**：去掉这两个挂载和环境变量，重新创建容器；或者把名单设成空。

## 验证（2026-11-23，测试站和正式站各一次，都在临时受保护群里）

- AI 助手 2 秒内连发 22 条，再发一条 @ 了 6 个人的消息：一条都没被删，没被封，群里和管理室都没有警告；
- 普通账号一条消息 @ 6 个人：被删除，并收到警告；
- 普通账号连发 18 条：第 15 条时被封禁，18 条全部被删，管理室有通知。

## 许可证

这两个文件在上游的文件头里写明是 Apache License 2.0（`SPDX-License-Identifier: Apache-2.0`），我们的修改同样以 Apache-2.0 发布，见 [LICENSE](LICENSE)。Draupnir 上游的其他文件按各自的文件头声明（大多是 Apache-2.0，少数是 AFL-3.0），我们没有改动。