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
# Modified by VibeDev (https://github.com/VibeDev-Si/vibedev-bot-plugins), November 2026: times are written in
# Chinese (format_time, format_absolute) and the time zone error is a Chinese message. See ../README.md.
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
import re

from attr import dataclass
from dateutil.relativedelta import relativedelta
import pytz

from maubot import MessageEvent
from maubot.handlers.command import Argument, ArgumentSyntaxError
from mautrix.types import EventID, RoomID, UserID
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper

from .locales import locales

if TYPE_CHECKING:
    from .bot import ReminderBot


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("default_timezone")
        helper.copy("base_command")


class DateArgument(Argument):
    def __init__(self, name: str, label: str = None, *, required: bool = False):
        super().__init__(name, label=label, required=required, pass_raw=True)

    def match(
        self, val: str, evt: MessageEvent = None, instance: "ReminderBot" = None
    ) -> Tuple[str, Optional[datetime]]:
        tz = pytz.UTC
        use_locales = [locales["en_iso"]]
        if instance:
            tz = instance.db.get_timezone(evt.sender, instance.default_timezone)
            locale_ids = instance.db.get_locales(evt.sender)
            use_locales = [locales[id] for id in locale_ids if id in locales]

        for locale in use_locales:
            match = locale.match(val)
            if match:
                date = (datetime.now(tz=tz) + relativedelta(**match.params)).astimezone(pytz.UTC)
                return match.unconsumed, date
        return val, None


def parse_timezone(val: str) -> Optional[pytz.timezone]:
    if not val:
        return None
    try:
        return pytz.timezone(val)
    except pytz.UnknownTimeZoneError as e:
        raise ArgumentSyntaxError(f"{val} 不是有效的时区，例如 Asia/Shanghai。", show_usage=False) from e


WEEKDAYS_ZH = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")


def format_absolute(time: datetime) -> str:
    """e.g. 2026-11-23 09:00（Asia/Shanghai，星期一）"""
    zone = getattr(time.tzinfo, "zone", None) or time.strftime("%Z")
    return f"{time.strftime('%Y-%m-%d %H:%M')}（{zone}，{WEEKDAYS_ZH[time.weekday()]}）"


def format_time(time: datetime) -> str:
    """Relative ("2 小时 30 分钟后") within 7 days, otherwise absolute local time ("在 2026-12-01 09:00（…）")."""
    now = datetime.now(tz=pytz.UTC).replace(microsecond=0)
    if time - now <= timedelta(days=7):
        delta = time - now
        parts = []
        if delta.days > 0:
            parts.append(f"{delta.days} 天")
        hours, seconds = divmod(delta.seconds, 60)
        hours, minutes = divmod(hours, 60)
        if hours > 0:
            parts.append(f"{hours} 小时")
        if minutes > 0:
            parts.append(f"{minutes} 分钟")
        if seconds > 0:
            parts.append(f"{seconds} 秒")
        return " ".join(parts) + "后" if parts else "马上"
    return "在 " + format_absolute(time)


@dataclass
class ReminderInfo:
    id: int = None
    date: datetime = None
    room_id: RoomID = None
    event_id: EventID = None
    message: str = None
    reply_to: EventID = None
    users: Union[Dict[UserID, EventID], List[UserID]] = None
