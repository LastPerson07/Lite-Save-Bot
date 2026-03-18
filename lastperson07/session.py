import asyncio
import html
import logging
import time

from pyrogram import Client, enums, filters
from pyrogram.enums import ButtonStyle
from pyrogram.errors import (
    FloodWait,
    PasswordHashInvalid,
    PhoneCodeExpired,
    PhoneCodeInvalid,
    PhoneNumberInvalid,
    SessionPasswordNeeded,
)
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from config import API_HASH, API_ID
from lastperson07.db import (
    lastperson07_delete_session,
    lastperson07_load_session,
    lastperson07_save_session,
)
from lastperson07.runtime import (
    FLOOD_SLEEP_THRESHOLD, LOGIN_STATE_TTL,
    E_LOCK, E_KEY, E_CLOCK, E_CHECK, E_CROSS, E_WARN, E_STOP, E_SHIELD, E_INFO,
    DIGIT_EMOJI, ICON_CANCEL, ICON_BACK, ICON_CHECK
)

log = logging.getLogger(__name__)

lastperson07_states: dict[int, dict] = {}

_LOGIN_CALLBACK_PREFIX = "lp7login"
_LOGIN_CALLBACK_RE = rf"^{_LOGIN_CALLBACK_PREFIX}:(?:\d|back|go|cancel)$"
_DIGITS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
_OTP_DIGITS = DIGIT_EMOJI
_LOGIN_DEVICE_MODEL = "Lite Bot Session"
_LOGIN_SYSTEM_VERSION = "Windows 11"
_LOGIN_APP_VERSION = "LiteBot/Stable"


def _fmt_exc(exc: Exception) -> str:
    return html.escape(str(exc), quote=False)


def _numpad():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("1", callback_data=f"{_LOGIN_CALLBACK_PREFIX}:1", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton("2", callback_data=f"{_LOGIN_CALLBACK_PREFIX}:2", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton("3", callback_data=f"{_LOGIN_CALLBACK_PREFIX}:3", style=ButtonStyle.PRIMARY),
            ],
            [
                InlineKeyboardButton("4", callback_data=f"{_LOGIN_CALLBACK_PREFIX}:4", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton("5", callback_data=f"{_LOGIN_CALLBACK_PREFIX}:5", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton("6", callback_data=f"{_LOGIN_CALLBACK_PREFIX}:6", style=ButtonStyle.PRIMARY),
            ],
            [
                InlineKeyboardButton("7", callback_data=f"{_LOGIN_CALLBACK_PREFIX}:7", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton("8", callback_data=f"{_LOGIN_CALLBACK_PREFIX}:8", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton("9", callback_data=f"{_LOGIN_CALLBACK_PREFIX}:9", style=ButtonStyle.PRIMARY),
            ],
            [
                InlineKeyboardButton("⌫", callback_data=f"{_LOGIN_CALLBACK_PREFIX}:back", icon_custom_emoji_id=ICON_BACK, style=ButtonStyle.DANGER),
                InlineKeyboardButton("0", callback_data=f"{_LOGIN_CALLBACK_PREFIX}:0", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton("✅", callback_data=f"{_LOGIN_CALLBACK_PREFIX}:go", icon_custom_emoji_id=ICON_CHECK, style=ButtonStyle.SUCCESS),
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"{_LOGIN_CALLBACK_PREFIX}:cancel", icon_custom_emoji_id=ICON_CANCEL, style=ButtonStyle.DANGER)],
        ]
    )


def _otp_txt(digits: list[str], err: str = "") -> str:
    slots = "  ".join(
        _OTP_DIGITS[int(digits[i])] if i < len(digits) else "⬜"
        for i in range(6)
    )
    note = f"\n{E_WARN} {err}" if err else ""
    return (
        f"<blockquote>{E_LOCK} <b>Enter OTP</b>\n\n"
        f"{slots}{note}\n\n"
        f"<i>Tap digits, then press confirm.</i></blockquote>"
    )


async def _wait_flood(coro_factory):
    while True:
        try:
            return await coro_factory()
        except FloodWait as wait:
            pause = int(wait.value) + 1
            log.warning("Login flow hit FloodWait, sleeping %ss", pause)
            await asyncio.sleep(pause)


async def _disconnect_client(acc: Client | None):
    if not acc:
        return
    try:
        await acc.disconnect()
    except Exception:
        pass


def _touch_state(state: dict):
    state["updated_at"] = time.monotonic()


async def _drop_state(uid: int):
    state = lastperson07_states.pop(uid, None)
    if state:
        await _disconnect_client(state.get("acc"))


async def _active_state(uid: int):
    state = lastperson07_states.get(uid)
    if not state:
        return None

    if time.monotonic() - state.get("updated_at", 0.0) > LOGIN_STATE_TTL:
        await _drop_state(uid)
        return None

    _touch_state(state)
    return state


async def _finish(status_message: Message, acc: Client, uid: int):
    try:
        session = await _wait_flood(lambda: acc.export_session_string())
        lastperson07_save_session(uid, session)
        await _disconnect_client(acc)
        lastperson07_states.pop(uid, None)
        await status_message.edit_text(
            f"<blockquote>{E_CHECK} <b>Login successful.</b>\n\nPaste a Telegram link and I will save it for you.</blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )
    except Exception as exc:
        await _disconnect_client(acc)
        lastperson07_states.pop(uid, None)
        await status_message.edit_text(
            f"❌ Session export failed: <code>{_fmt_exc(exc)}</code>",
            parse_mode=enums.ParseMode.HTML,
        )


def _login_client(uid: int) -> Client:
    return Client(
        f"lp7_login_{uid}",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True,
        no_updates=True,
        device_model=_LOGIN_DEVICE_MODEL,
        system_version=_LOGIN_SYSTEM_VERSION,
        app_version=_LOGIN_APP_VERSION,
        sleep_threshold=FLOOD_SLEEP_THRESHOLD,
    )


def lastperson07_register_session(app: Client):
    @app.on_message(filters.private & filters.command("login"))
    async def _login(_, msg: Message):
        uid = msg.from_user.id if msg.from_user else None

        if lastperson07_load_session(uid):
            await msg.reply(f"<blockquote>{E_CHECK} Already logged in. Use /logout if you want to replace the session.</blockquote>")
            return

        await _drop_state(uid)
        lastperson07_states[uid] = {
            "step": "phone",
            "acc": None,
            "phone": "",
            "hash": "",
            "digits": [],
            "updated_at": time.monotonic(),
        }
        await msg.reply(
            f"<blockquote>{E_SHIELD} <b>Login</b>\n\n"
            "Send your phone number with country code.\n"
            "Example: <code>+919876543210</code>\n\n"
            "Use /cancellogin any time if you want to stop.</blockquote>",
            parse_mode=enums.ParseMode.HTML,
            reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True),
        )

    @app.on_message(filters.private & filters.command("logout"))
    async def _logout(_, msg: Message):
        uid = msg.from_user.id if msg.from_user else None

        await _drop_state(uid)
        session = lastperson07_load_session(uid)
        if not session:
            await msg.reply(f"<blockquote>{E_INFO} No saved login found.</blockquote>", reply_markup=ReplyKeyboardRemove())
            return

        try:
            tmp = Client(
                f"lp7_logout_{uid}",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=session,
                in_memory=True,
                no_updates=True,
                sleep_threshold=FLOOD_SLEEP_THRESHOLD,
            )
            await _wait_flood(lambda: tmp.connect())
            await _wait_flood(lambda: tmp.log_out())
            await _disconnect_client(tmp)
        except Exception:
            pass

        lastperson07_delete_session(uid)
        await msg.reply(f"<blockquote>{E_CHECK} Logged out.</blockquote>", reply_markup=ReplyKeyboardRemove())

    @app.on_message(filters.private & filters.command("cancellogin"))
    async def _cancellogin(_, msg: Message):
        uid = msg.from_user.id if msg.from_user else None

        state = await _active_state(uid)
        if not state:
            await msg.reply(f"<blockquote>{E_INFO} No login is in progress.</blockquote>", reply_markup=ReplyKeyboardRemove())
            return

        await _drop_state(uid)
        await msg.reply(f"<blockquote>{E_STOP} Login cancelled.</blockquote>", reply_markup=ReplyKeyboardRemove())

    @app.on_message(filters.private & filters.text, group=1)
    async def _login_text(_, msg: Message):
        uid = msg.from_user.id if msg.from_user else None

        if not msg.text or msg.text.startswith("/"):
            return

        state = await _active_state(uid)
        if not state:
            return

        text = msg.text.strip()
        step = state["step"]

        if text == "❌ Cancel":
            await _drop_state(uid)
            await msg.reply(f"<blockquote>{E_STOP} Cancelled.</blockquote>", reply_markup=ReplyKeyboardRemove())
            return

        if step == "phone":
            acc = _login_client(uid)
            status_message = await msg.reply(f"<blockquote>{E_CLOCK} <b>Sending login code...</b></blockquote>", reply_markup=ReplyKeyboardRemove())

            try:
                await _wait_flood(lambda: acc.connect())
                sent = await _wait_flood(lambda: acc.send_code(text))
            except PhoneNumberInvalid:
                await status_message.edit_text(f"<blockquote>{E_WARN} Invalid phone number. Use /login and try again.</blockquote>")
                await _disconnect_client(acc)
                lastperson07_states.pop(uid, None)
                return
            except Exception as exc:
                await _disconnect_client(acc)
                lastperson07_states.pop(uid, None)
                await status_message.edit_text(
                    f"<blockquote>{E_CROSS} Error: <code>{_fmt_exc(exc)}</code>\n\nUse /login and try again.</blockquote>",
                    parse_mode=enums.ParseMode.HTML,
                )
                return

            state.update(
                acc=acc,
                phone=text,
                hash=sent.phone_code_hash,
                digits=[],
                step="code",
            )
            _touch_state(state)
            try:
                await status_message.delete()
            except Exception:
                pass

            await msg.reply(
                _otp_txt([]),
                parse_mode=enums.ParseMode.HTML,
                reply_markup=_numpad(),
            )
            return

        if step == "password":
            acc = state.get("acc")
            status_message = await msg.reply(f"<blockquote>{E_LOCK} <b>Verifying password...</b></blockquote>")
            try:
                await _wait_flood(lambda: acc.check_password(text))
                await _finish(status_message, acc, uid)
            except PasswordHashInvalid:
                await status_message.edit_text(f"<blockquote>{E_CROSS} Wrong password. Please type it again.</blockquote>")
            except Exception as exc:
                await status_message.edit_text(
                    f"<blockquote>{E_CROSS} <code>{_fmt_exc(exc)}</code></blockquote>",
                    parse_mode=enums.ParseMode.HTML,
                )
                await _drop_state(uid)

    @app.on_callback_query(filters.regex(_LOGIN_CALLBACK_RE))
    async def _otp(_, cq: CallbackQuery):
        uid = cq.from_user.id if cq.from_user else None

        state = await _active_state(uid)
        if not state or state["step"] != "code":
            await cq.answer("No active OTP. Use /login.", show_alert=True)
            return

        action = cq.data.split(":", 1)[1]
        digits = state["digits"]

        if action == "cancel":
            await _drop_state(uid)
            await cq.message.edit_text(f"<blockquote>{E_STOP} Login cancelled.</blockquote>")
            await cq.answer()
            return

        if action == "back":
            if digits:
                digits.pop()
            await cq.message.edit_text(
                _otp_txt(digits),
                parse_mode=enums.ParseMode.HTML,
                reply_markup=_numpad(),
            )
            await cq.answer()
            return

        if action in _DIGITS:
            if len(digits) >= 6:
                await cq.answer("Max 6 digits.", show_alert=True)
                return

            digits.append(action)
            _touch_state(state)
            await cq.message.edit_text(
                _otp_txt(digits),
                parse_mode=enums.ParseMode.HTML,
                reply_markup=_numpad(),
            )
            await cq.answer()
            return

        if action == "go":
            if len(digits) < 5:
                await cq.answer("Enter at least 5 digits.", show_alert=True)
                return

            await cq.message.edit_text(f"<blockquote>{E_CLOCK} <b>Verifying...</b></blockquote>")
            await cq.answer()
            acc = state.get("acc")
            try:
                await _wait_flood(
                    lambda: acc.sign_in(
                        state["phone"],
                        state["hash"],
                        "".join(digits),
                    )
                )
                await _finish(cq.message, acc, uid)
            except PhoneCodeInvalid:
                state["digits"] = []
                _touch_state(state)
                await cq.message.edit_text(
                    _otp_txt([], "Wrong code, try again"),
                    parse_mode=enums.ParseMode.HTML,
                    reply_markup=_numpad(),
                )
            except PhoneCodeExpired:
                await cq.message.edit_text(f"<blockquote>{E_CLOCK} Code expired. Use /login again.</blockquote>")
                await _drop_state(uid)
            except SessionPasswordNeeded:
                state["step"] = "password"
                _touch_state(state)
                await cq.message.edit_text(
                    f"<blockquote>{E_KEY} <b>2FA required</b>\n\n"
                    "Type your cloud password below.</blockquote>",
                    parse_mode=enums.ParseMode.HTML,
                )
            except Exception as exc:
                await cq.message.edit_text(
                    f"<blockquote>{E_CROSS} <code>{_fmt_exc(exc)}</code></blockquote>",
                    parse_mode=enums.ParseMode.HTML,
                )
                await _drop_state(uid)
