# reminder - A maubot plugin to remind you about things.
# Copyright (C) 2020 Tulir Asokan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# Modified by VibeDev (https://github.com/VibeDev-Si/vibedev-bot-plugins), November 2026: Chinese replies and help,
# an optional time argument with a Chinese hint, and a link to this source code in the help. See ../README.md.
from typing import List, Tuple, Type
from datetime import datetime, timedelta
from html import escape
import asyncio

import pytz

from maubot import MessageEvent, Plugin
from maubot.handlers import command, event
from mautrix.types import (
    EventType,
    Format,
    MessageType,
    ReactionEvent,
    RedactionEvent,
    StateEvent,
    TextMessageEventContent,
    UserID,
)
from mautrix.util import background_task
from mautrix.util.config import BaseProxyConfig

from .db import ReminderDatabase
from .locales import locales
from .util import Config, DateArgument, ReminderInfo, format_absolute, format_time, parse_timezone


class ReminderBot(Plugin):
    db: ReminderDatabase
    reminder_loop_task: asyncio.Future
    base_command: str
    base_aliases: Tuple[str, ...]
    default_timezone: pytz.timezone

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config

    async def start(self) -> None:
        self.on_external_config_update()
        self.db = ReminderDatabase(self.database)
        self.reminder_loop_task = asyncio.create_task(self.reminder_loop())

    def on_external_config_update(self) -> None:
        self.config.load_and_update()
        bc = self.config["base_command"]
        self.base_command = bc[0] if isinstance(bc, list) else bc
        self.base_aliases = tuple(bc) if isinstance(bc, list) else (bc,)
        raw_timezone = self.config["default_timezone"]
        try:
            self.default_timezone = pytz.timezone(raw_timezone)
        except pytz.UnknownTimeZoneError:
            self.log.warning(f"Unknown default timezone {raw_timezone}")
            self.default_timezone = pytz.UTC

    async def stop(self) -> None:
        self.reminder_loop_task.cancel()

    async def reminder_loop(self) -> None:
        try:
            self.log.debug("Reminder loop started")
            while True:
                now = datetime.now(tz=pytz.UTC)
                next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
                await asyncio.sleep((next_minute - now).total_seconds())
                await self.schedule_nearby_reminders(next_minute)
        except asyncio.CancelledError:
            self.log.debug("Reminder loop stopped")
        except Exception:
            self.log.exception("Exception in reminder loop")

    async def schedule_nearby_reminders(self, now: datetime) -> None:
        until = now + timedelta(minutes=1)
        for reminder in self.db.all_in_range(now, until):
            background_task.create(self.send_reminder(reminder))

    async def send_reminder(self, reminder: ReminderInfo) -> None:
        try:
            await self._send_reminder(reminder)
        except Exception:
            self.log.exception("Failed to send reminder")

    async def _send_reminder(self, reminder: ReminderInfo) -> None:
        if len(reminder.users) == 0:
            self.log.debug(f"Cancelling reminder {reminder}, no users left to remind")
            return
        wait = (reminder.date - datetime.now(tz=pytz.UTC)).total_seconds()
        if wait > 0:
            self.log.debug(f"Waiting {wait} seconds to send {reminder}")
            await asyncio.sleep(wait)
        else:
            self.log.debug(f"Sending {reminder} immediately")
        users = " ".join(reminder.users)
        users_html = " ".join(
            f"<a href='https://matrix.to/#/{user_id}'>{user_id}</a>" for user_id in reminder.users
        )
        content = TextMessageEventContent(
            msgtype=MessageType.TEXT,
            body=f"{users}: {reminder.message}",
            format=Format.HTML,
            formatted_body=f"{users_html}: {escape(reminder.message)}",
        )
        content["xyz.maubot.reminder"] = {
            "id": reminder.id,
            "message": reminder.message,
            "targets": list(reminder.users),
            "reply_to": reminder.reply_to,
        }
        if reminder.reply_to:
            content.set_reply(await self.client.get_event(reminder.room_id, reminder.reply_to))
        await self.client.send_message(reminder.room_id, content)

    def _past_reply(self, sender: UserID, date: datetime) -> str:
        local = date.astimezone(self.db.get_timezone(sender, self.default_timezone))
        return f"抱歉，{format_absolute(local)} 已经过去了，没法提醒到过去 :("

    def _no_time_reply(self, text: str) -> str:
        # VibeDev: the time argument is optional so that an unreadable time gets this Chinese hint instead of maubot's
        # English usage text.
        c = self.base_command
        seen = f"没看懂「{text.strip()[:40]}」里的时间。" if text and text.strip() else "缺少时间。"
        return (
            f"{seen}时间要写在最前面，用这些写法：`30m`、`2h`、`1d 2h`、`tomorrow 09:00`、`friday 15:00`、"
            f"`2026-12-01 09:00`（小时写两位）。例如 `!{c} tomorrow 09:00 交周报`。"
            f"暂不支持中文时间（如「明天 9 点」）和每天、每周的循环提醒。发 `!{c} help` 查看完整用法。"
        )

    @command.new(
        name=lambda self: self.base_command,
        aliases=lambda self, alias: alias in self.base_aliases,
        help="设一个提醒（发 !remind help 查看用法）",
        require_subcommand=False,
        arg_fallthrough=False,
    )
    @DateArgument("date", required=False)
    @command.argument("message", pass_raw=True, required=False)
    async def remind(self, evt: MessageEvent, date: datetime, message: str) -> None:
        if date is None:
            await evt.reply(self._no_time_reply(message))
            return
        date = date.replace(microsecond=0)
        now = datetime.now(tz=pytz.UTC).replace(microsecond=0)
        if date < now:
            await evt.reply(self._past_reply(evt.sender, date))
            return
        rem = ReminderInfo(
            date=date,
            room_id=evt.room_id,
            message=message,
            reply_to=evt.content.get_reply_to(),
            users={evt.sender: evt.event_id},
        )
        await self._remind(evt, rem, now)

    @remind.subcommand("for", help="给别人设提醒")
    @command.argument("user_id", required=True, matches="@[^:]*:[a-zA-Z0-9.-]{1,255}(?::\d{1,5})?")
    @DateArgument("date", required=False)
    @command.argument("message", pass_raw=True, required=False)
    async def remind_for(
        self, evt: MessageEvent, user_id: UserID, date: datetime, message: str
    ) -> None:
        if date is None:
            await evt.reply(self._no_time_reply(message))
            return
        date = date.replace(microsecond=0)
        now = datetime.now(tz=pytz.UTC).replace(microsecond=0)
        if date < now:
            await evt.reply(self._past_reply(evt.sender, date))
            return
        rem = ReminderInfo(
            date=date,
            room_id=evt.room_id,
            message=message,
            reply_to=evt.event_id,
            users={user_id: evt.event_id},
        )
        await self._remind(evt, rem, now, recipient=user_id.split(":")[0].removeprefix("@"))

    @remind.subcommand("reschedule", help="把收到的提醒改到另一个时间", aliases=("again",))
    @DateArgument("date", required=False)
    async def reschedule(self, evt: MessageEvent, date: datetime) -> None:
        reply_to_id = evt.content.get_reply_to()
        if not reply_to_id:
            await evt.reply("要改期，请先回复那条提醒消息，再发这个命令。")
            return
        if date is None:
            await evt.reply(self._no_time_reply(""))
            return
        date = date.replace(microsecond=0)
        now = datetime.now(tz=pytz.UTC).replace(microsecond=0)
        if date < now:
            await evt.reply(self._past_reply(evt.sender, date))
            return
        reply_to = await self.client.get_event(evt.room_id, reply_to_id)
        try:
            reminder_info = reply_to.content["xyz.maubot.reminder"]
            rem = ReminderInfo(
                date=date,
                room_id=evt.room_id,
                message=reminder_info["message"],
                reply_to=reminder_info["reply_to"],
                users={evt.sender: evt.event_id},
            )
        except KeyError:
            await evt.reply("这看起来不是一条有效的提醒消息。")
            return
        await self._remind(evt, rem, now, again=True)

    async def _remind(
        self,
        evt: MessageEvent,
        rem: ReminderInfo,
        now: datetime,
        again: bool = False,
        recipient: str = "你",
    ) -> None:
        if rem.date == now:
            await self.send_reminder(rem)
            return
        if rem.date.year > now.year + 125:
            recipient = "你的后代" if recipient == "你" else f"{recipient} 的后代"
        what = f"提醒{recipient}" if recipient == "你" or recipient.endswith("后代") else f"提醒 {recipient} "
        if again:
            what = "再次" + what
        if rem.reply_to:
            evt_link = f"[那条消息](https://matrix.to/#/{rem.room_id}/{rem.reply_to})"
            if rem.message:
                what += f"「{rem.message}」（关于{evt_link}）"
            else:
                what += f"看{evt_link}"
        elif rem.message:
            what += f"「{rem.message}」"
        else:
            rem.message = "提醒"
        msg = (
            f"好的，{self.format_time(evt.sender, rem)}{what}。\n\n"
            f"（其他人给这条消息点 \U0001f44d 也会一起被提醒）"
        )
        rem.event_id = await evt.reply(msg)
        self.db.insert(rem)
        now = datetime.now(tz=pytz.UTC)
        if (rem.date - now).total_seconds() < 60 and now.minute == rem.date.minute:
            self.log.debug(f"Reminder {rem} is in less than a minute, scheduling now...")
            background_task.create(self.send_reminder(rem))

    @remind.subcommand("help", help="用法说明")
    async def help(self, evt: MessageEvent) -> None:
        c = self.base_command
        server = self.client.mxid.partition(":")[2]
        await evt.reply(
            "**VibeDev 提醒**用法（命令和时间写法用英文格式）：\n\n"
            f"* `!{c} <时间> <内容>`：设提醒，例如 `!{c} 30m 喝水`、`!{c} 2h 开会`、"
            f"`!{c} tomorrow 09:00 交周报`、`!{c} friday 15:00 例会`、`!{c} 2026-12-01 09:00 发版`\n"
            f"* `!{c} for @某人:{server} <时间> <内容>`：给别人设提醒\n"
            f"* 回复一条消息再发 `!{c} <时间>`：到时提醒你看那条消息\n"
            f"* 回复收到的提醒发 `!{c} again <时间>`：改期再提醒一次\n"
            f"* `!{c} list`：本群你的提醒；`!{c} list all`：所有群\n"
            f"* `!{c} tz Asia/Shanghai`：设置你的时区（默认就是北京时间）\n\n"
            "**时间写法**：`30m` / `2h` / `1d` / `1d 2h 30m`（多久之后），"
            "`today 18:00`、`tomorrow 09:00`、`monday 10:00`（某天某时，时间必须写成两位 `09:00`），"
            "`2026-12-01 09:00`（具体日期）。暂不认中文时间（例如「明天 9 点」），也不支持每天、每周的循环提醒。\n\n"
            "**取消**：删除你发的那条命令，或删除机器人的确认消息。"
            "想一起被提醒：给确认消息点 \U0001f44d；取消点赞即退出。\n\n"
            "源码：https://github.com/VibeDev-Si/vibedev-bot-plugins"
        )

    @remind.subcommand("list", help="列出你的提醒")
    @command.argument("all", required=False)
    async def list(self, evt: MessageEvent, all: str) -> None:
        room_id = evt.room_id
        if "all" in all:
            room_id = None

        def format_rem(rem: ReminderInfo) -> str:
            if rem.reply_to:
                evt_link = f"[那条消息](https://matrix.to/#/{rem.room_id}/{rem.reply_to})"
                if rem.message:
                    return f"「{rem.message}」（关于{evt_link}）"
                else:
                    return evt_link
            else:
                return f"「{rem.message}」"

        reminders_str = "\n".join(
            f"* {format_rem(reminder)}：{self.format_time(evt.sender, reminder)}"
            for reminder in self.db.all_for_user(evt.sender, room_id=room_id)
        )
        scope = "本群" if room_id else "所有群"
        if len(reminders_str) == 0:
            await evt.reply(f"你在{scope}没有待发的提醒。")
        else:
            await evt.reply(f"你在{scope}待发的提醒：\n\n{reminders_str}")

    def format_time(self, sender: UserID, reminder: ReminderInfo) -> str:
        return format_time(reminder.date.astimezone(self.db.get_timezone(sender)))

    @remind.subcommand("locales", help="列出可用的时间写法")
    async def locales(self, evt: MessageEvent) -> None:
        def _format_key(key: str) -> str:
            language, country = key.split("_")
            return f"{language.lower()}_{country.upper()}"

        await evt.reply(
            "可用的时间写法（用 `!remind locale <代号>` 选择，默认 en_ISO）：\n\n"
            + "\n".join(
                f"* `{_format_key(key)}` - {locale.name}" for key, locale in locales.items()
            )
        )

    @staticmethod
    def _fmt_locales(locale_ids: List[str]) -> str:
        locale_names = [locales[id].name for id in locale_ids]
        if len(locale_names) == 0:
            return "未设置"
        return "、".join(locale_names)

    @remind.subcommand("locale", help="设置你的时间写法")
    @command.argument("locale", required=False, pass_raw=True)
    async def locale(self, evt: MessageEvent, locale: str) -> None:
        if not locale:
            await evt.reply(f"你的时间写法是：{self._fmt_locales(self.db.get_locales(evt.sender))}")
            return
        locale_ids = [part.strip() for part in locale.lower().split(" ")]
        for locale_id in locale_ids:
            if locale_id not in locales:
                await evt.reply(f"不支持时间写法 `{locale_id}`，发 `!remind locales` 查看可用的。")
                return
        self.db.set_locales(evt.sender, locale_ids)
        await evt.reply(f"已把你的时间写法设为：{self._fmt_locales(locale_ids)}")

    @remind.subcommand("timezone", help="设置你的时区", aliases=("tz",))
    @command.argument("timezone", parser=parse_timezone, required=False)
    async def timezone(self, evt: MessageEvent, timezone: pytz.timezone) -> None:
        if not timezone:
            zone = self.db.get_timezone(evt.sender, self.default_timezone).zone
            await evt.reply(f"你的时区是 {zone}")
            return
        self.db.set_timezone(evt.sender, timezone)
        await evt.reply(f"已把你的时区设为 {timezone.zone}")

    @command.passive(
        regex=r"(?:\U0001F44D[\U0001F3FB-\U0001F3FF]?)",
        field=lambda evt: evt.content.relates_to.key,
        event_type=EventType.REACTION,
        msgtypes=None,
    )
    async def subscribe_react(self, evt: ReactionEvent, _: Tuple[str]) -> None:
        reminder = self.db.get_by_event_id(evt.content.relates_to.event_id)
        if reminder:
            self.db.add_user(reminder, evt.sender, evt.event_id)

    @event.on(EventType.ROOM_REDACTION)
    async def redact(self, evt: RedactionEvent) -> None:
        self.db.redact_event(evt.redacts)

    @event.on(EventType.ROOM_TOMBSTONE)
    async def tombstone(self, evt: StateEvent) -> None:
        if not evt.content.replacement_room:
            return
        self.db.update_room_id(evt.room_id, evt.content.replacement_room)
