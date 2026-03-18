import time
import logging
from pyrogram import Client, enums, filters
from pyrogram.enums import ButtonStyle
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from config import API_ID, API_HASH, BOT_TOKEN
from lastperson07.db import lastperson07_db_init
from lastperson07.keep_alive import lastperson07_keep_alive
from lastperson07.runtime import (
    BOT_SESSION_NAME, BOT_WORKERS, ENABLE_HEALTHCHECK,
    FLOOD_SLEEP_THRESHOLD, lastperson07_assert_integrity,
    lastperson07_owner_name, lastperson07_dev2_name, lastperson07_dev3_name,
    lastperson07_all_devs,
    E_WARN, E_INFO, E_CROWN, E_SPARK, E_CHECK, E_BOLT, E_GEAR,
    E_STAR, E_STOP, E_GREEN, E_RED, E_LINK, E_BATCH, E_PENCIL, E_TIP,
    WARNING_TXT, ICON_INFO, ICON_WARN, ICON_HELP, ICON_DEV, ICON_BACK,
    ICON_GEAR, ICON_PENCIL, ICON_TRASH, ICON_REFRESH,
)
from lastperson07.db import (
    lastperson07_load_caption, lastperson07_delete_caption,
    lastperson07_load_session, lastperson07_register_user,
    lastperson07_get_user_downloads,
    lastperson07_save_batch_limit, lastperson07_load_batch_limit,
)
from lastperson07.save import lastperson07_register_save, _active
from lastperson07.session import lastperson07_register_session

log = logging.getLogger(__name__)

_BATCH_OPTIONS = [
    ("10",          10),
    ("25",          25),
    ("50",          50),
    ("100",        100),
    ("200",        200),
    ("∞ Unlimited",  0),
]
_HELP_MAX_PAGE = 2


def _register_core(app: Client):
    dev  = lastperson07_owner_name()
    dev2 = lastperson07_dev2_name()
    dev3 = lastperson07_dev3_name()
    devs = lastperson07_all_devs()

    # buttons

    def get_main_markup():
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(" ʜᴇʟᴘ ",  callback_data="lp7:help:1",  icon_custom_emoji_id=ICON_HELP,  style=ButtonStyle.PRIMARY),
                InlineKeyboardButton(" ᴀʙᴏᴜᴛ ", callback_data="about", icon_custom_emoji_id=ICON_INFO,  style=ButtonStyle.PRIMARY),
            ],
            [
                InlineKeyboardButton(" Settings ", callback_data="settings", icon_custom_emoji_id=ICON_GEAR, style=ButtonStyle.PRIMARY),
            ],
            [
                InlineKeyboardButton(" ᴡᴀʀɴɪɴɢ ", callback_data="lp7:warning", icon_custom_emoji_id=ICON_WARN, style=ButtonStyle.DANGER),
            ],
        ])

    def get_back_markup(dest: str = "start"):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⌫ Back", callback_data=dest, icon_custom_emoji_id=ICON_BACK, style=ButtonStyle.PRIMARY)]
        ])

    def get_help_markup(page: int):
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("◁ Prev", callback_data=f"lp7:help:{page - 1}", style=ButtonStyle.PRIMARY))
        if page < _HELP_MAX_PAGE:
            nav_row.append(InlineKeyboardButton("Next ▷", callback_data=f"lp7:help:{page + 1}", style=ButtonStyle.PRIMARY))

        rows = []
        if nav_row:
            rows.append(nav_row)
        rows.append([InlineKeyboardButton("⌫ Back", callback_data="start", icon_custom_emoji_id=ICON_BACK, style=ButtonStyle.DANGER)])
        return InlineKeyboardMarkup(rows)

    def get_settings_markup(has_caption: bool, batch_limit: int):
        label = "∞ Unlimited" if batch_limit == 0 else str(batch_limit)
        buttons = [
            [InlineKeyboardButton("Set Caption",            callback_data="set_caption_help", icon_custom_emoji_id=ICON_PENCIL,  style=ButtonStyle.PRIMARY)],
        ]
        if has_caption:
            buttons.append(
                [InlineKeyboardButton("Remove Caption",       callback_data="remove_caption",   icon_custom_emoji_id=ICON_TRASH,   style=ButtonStyle.DANGER)]
            )
        buttons.append(
            [InlineKeyboardButton(f"Batch Limit: {label}",  callback_data="lp7:batchlimit",   icon_custom_emoji_id=ICON_REFRESH, style=ButtonStyle.PRIMARY)]
        )
        buttons.append(
            [InlineKeyboardButton("⌫ Back",                    callback_data="start",            icon_custom_emoji_id=ICON_BACK,    style=ButtonStyle.DANGER)]
        )
        return InlineKeyboardMarkup(buttons)

    def get_batch_limit_markup(current: int):
        rows, row = [], []
        for label, val in _BATCH_OPTIONS:
            row.append(InlineKeyboardButton(
                label,
                callback_data=f"lp7:bl:{val}",
                style=ButtonStyle.SUCCESS if val == current else ButtonStyle.PRIMARY,
            ))
            if len(row) == 3:
                rows.append(row); row = []
        if row:
            rows.append(row)
        rows.append([InlineKeyboardButton("⌫ Back", callback_data="settings", icon_custom_emoji_id=ICON_BACK, style=ButtonStyle.PRIMARY)])
        return InlineKeyboardMarkup(rows)

    # Start 

    def get_start_text(name: str) -> str:
        return (
            f"<blockquote>{E_STAR} <b>Hi, {name}!</b>\n\n"
            f"{E_SPARK} <b>Welcome to Lite Save Bot.</b>\n\n"
            f"{E_LINK} Log in once with /login, then send any Telegram link you want to save.\n\n"
            f"{E_INFO} Need a hand? Open /help for commands and examples.</blockquote>"
        )

    def get_help_text(page: int = 1) -> str:
        if page == 2:
            return (
                f"<blockquote>{E_LINK} <b>How to use</b>\n\n"
                f"{E_LINK} <b>Single message</b>\n"
                "<code>https://t.me/channel/123</code>\n\n"
                f"{E_BATCH} <b>Batch messages</b>\n"
                "<code>https://t.me/channel/10-60</code>\n"
                "<code>https://t.me/c/1234567/10-60</code>\n\n"
                f"{E_BATCH} You can also save a range by adding <code>-endID</code> to the link:\n"
                "<code>https://t.me/somechannel/100-149</code>\n\n"
                f"{E_GEAR} You can change the batch size anytime in Settings -> Batch Limit\n"
                f"{E_CHECK} The bot waits 7 seconds between sends to help keep things safe.</blockquote>"
            )

        return (
            f"<blockquote>{E_INFO} <b>How to use</b>\n\n"
            f"{E_GEAR} <b>Commands</b>\n"
            f"{E_GREEN} /login — Connect your account\n"
            f"{E_RED} /logout — Sign out and remove your saved session\n"
            f"{E_STOP} /cancellogin — Stop the current login flow\n"
            f"{E_INFO} /status — See your session, caption, and current tasks\n"
            f"{E_BOLT} /ping — Check how fast the bot is responding\n\n"
            f"{E_SPARK} Tap Next to see link formats and batch examples.</blockquote>"
        )

    # ── /start ────────────────────────────────────────────────────────────────

    @app.on_message(filters.private & filters.command("start"))
    async def _start(_, msg: Message):
        uid  = msg.from_user.id if msg.from_user else None
        name = msg.from_user.first_name if msg.from_user else "there"
        if uid:
            lastperson07_register_user(uid)
        await msg.reply(get_start_text(name), parse_mode=enums.ParseMode.HTML, reply_markup=get_main_markup())

    @app.on_callback_query(filters.regex(r"^start$"))
    async def _start_cb(_, cq: CallbackQuery):
        name = cq.from_user.first_name if cq.from_user else "there"
        try:
            await cq.message.edit_text(get_start_text(name), parse_mode=enums.ParseMode.HTML, reply_markup=get_main_markup())
        except Exception:
            pass
        await cq.answer()

    # ── /help ─────────────────────────────────────────────────────────────────

    @app.on_message(filters.private & filters.command("help"))
    async def _help(_, msg: Message):
        await msg.reply(get_help_text(1), parse_mode=enums.ParseMode.HTML, reply_markup=get_help_markup(1))

    @app.on_callback_query(filters.regex(r"^help$"))
    async def _help_cb(_, cq: CallbackQuery):
        try:
            await cq.message.edit_text(get_help_text(1), parse_mode=enums.ParseMode.HTML, reply_markup=get_help_markup(1))
        except Exception:
            pass
        await cq.answer()

    @app.on_callback_query(filters.regex(r"^lp7:help:(1|2)$"))
    async def _help_page_cb(_, cq: CallbackQuery):
        page = int(cq.data.rsplit(":", 1)[1])
        try:
            await cq.message.edit_text(get_help_text(page), parse_mode=enums.ParseMode.HTML, reply_markup=get_help_markup(page))
        except Exception:
            pass
        await cq.answer()

    # ── about ─────────────────────────────────────────────────────────────────

    @app.on_callback_query(filters.regex(r"^about$"))
    async def _about_cb(_, cq: CallbackQuery):
        dev_lines = "\n".join(
            (
                f"{E_CROWN} <b>DEVS</b> -> <a href=\"https://t.me/{d['name']}\">{d['tag']}</a>"
                if i == 0 else
                f"{E_BOLT} <b>DEVS {i}</b> -> <a href=\"https://t.me/{d['name']}\">{d['tag']}</a>"
            )
            for i, d in enumerate(devs)
        )
        try:
            await cq.message.edit_text(
                f"<blockquote>{E_INFO} <b>About Lite Save Bot</b>\n\n"
                f"{E_SPARK} Save Telegram files in a simple, clean way.\n\n"
                f"{E_CROWN} <b>Team</b>\n"
                "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
                f"{dev_lines}\n"
                "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
                f"{E_CHECK} Built by <b>@cantarellabots</b>.</blockquote>",
                parse_mode=enums.ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"@{dev}",  url=f"https://t.me/{dev}",  icon_custom_emoji_id=ICON_DEV, style=ButtonStyle.PRIMARY)],
                    [InlineKeyboardButton(f"@{dev2}", url=f"https://t.me/{dev2}", icon_custom_emoji_id=ICON_DEV, style=ButtonStyle.PRIMARY)],
                    [InlineKeyboardButton(f"@{dev3}", url=f"https://t.me/{dev3}", icon_custom_emoji_id=ICON_DEV, style=ButtonStyle.PRIMARY)],
                    [InlineKeyboardButton("⌫ Back", callback_data="start", icon_custom_emoji_id=ICON_BACK, style=ButtonStyle.DANGER)],
                ])
            )
        except Exception:
            pass
        await cq.answer()

    # ── warning ───────────────────────────────────────────────────────────────

    @app.on_callback_query(filters.regex(r"^lp7:warning$"))
    async def _warning_cb(_, cq: CallbackQuery):
        try:
            await cq.message.edit_text(
                f"<blockquote>{WARNING_TXT}</blockquote>",
                parse_mode=enums.ParseMode.HTML,
                reply_markup=get_back_markup()
            )
        except Exception:
            pass
        await cq.answer()

    # ── settings ──────────────────────────────────────────────────────────────

    @app.on_callback_query(filters.regex(r"^settings$"))
    async def _settings_cb(_, cq: CallbackQuery):
        uid         = cq.from_user.id
        caption     = lastperson07_load_caption(uid)
        batch_limit = lastperson07_load_batch_limit(uid)
        limit_label = "∞ Unlimited" if batch_limit == 0 else str(batch_limit)
        caption_label = caption if caption else "Not set. Original captions will be kept."
        try:
            await cq.message.edit_text(
                f"<blockquote>{E_GEAR} <b>Settings</b>\n\n"
                f"{E_PENCIL} <b>Caption:</b> {caption_label}\n"
                f"{E_BATCH} <b>Batch limit:</b> {limit_label}\n\n"
                f"{E_INFO} You can update these anytime.</blockquote>",
                parse_mode=enums.ParseMode.HTML,
                reply_markup=get_settings_markup(bool(caption), batch_limit)
            )
        except Exception:
            pass
        await cq.answer()

    @app.on_callback_query(filters.regex(r"^set_caption_help$"))
    async def _set_caption_help_cb(_, cq: CallbackQuery):
        try:
            await cq.message.edit_text(
                f"<blockquote>{E_PENCIL} <b>Set a Caption</b>\n\n"
                f"{E_TIP} Send the command below with the text you want:\n\n"
                "<code>/setcaption Your caption here</code>\n\n"
                f"{E_CHECK} It will be added to every file you save.\n"
                f"{E_INFO} Use /delcaption anytime to remove it.</blockquote>",
                parse_mode=enums.ParseMode.HTML,
                reply_markup=get_back_markup(dest="settings")
            )
        except Exception:
            pass
        await cq.answer()

    @app.on_callback_query(filters.regex(r"^remove_caption$"))
    async def _remove_caption_cb(_, cq: CallbackQuery):
        uid         = cq.from_user.id
        batch_limit = lastperson07_load_batch_limit(uid)
        lastperson07_delete_caption(uid)
        try:
            await cq.message.edit_text(
                f"<blockquote>{E_CHECK} <b>Caption removed</b>\n\n"
                f"{E_INFO} Your saved files will keep their original captions from now on.</blockquote>",
                parse_mode=enums.ParseMode.HTML,
                reply_markup=get_settings_markup(False, batch_limit)
            )
        except Exception:
            pass
        await cq.answer("Your caption was removed.", show_alert=True)

    # ── batch limit ───────────────────────────────────────────────────────────

    @app.on_callback_query(filters.regex(r"^lp7:batchlimit$"))
    async def _batchlimit_cb(_, cq: CallbackQuery):
        uid     = cq.from_user.id
        current = lastperson07_load_batch_limit(uid)
        label   = "∞ Unlimited" if current == 0 else str(current)
        try:
            await cq.message.edit_text(
                f"<blockquote>{E_BATCH} <b>Batch Limit</b>\n\n"
                f"{E_INFO} Current limit: <b>{label}</b>\n\n"
                f"{E_TIP} Choose how many files to save from one link.\n"
                f"{E_BATCH} Pick <b>∞ Unlimited</b> if you want the full range.</blockquote>",
                parse_mode=enums.ParseMode.HTML,
                reply_markup=get_batch_limit_markup(current)
            )
        except Exception:
            pass
        await cq.answer()

    @app.on_callback_query(filters.regex(r"^lp7:bl:(\d+)$"))
    async def _set_batchlimit_cb(_, cq: CallbackQuery):
        uid   = cq.from_user.id
        val   = int(cq.data.split(":")[-1])
        label = "∞ Unlimited" if val == 0 else str(val)
        lastperson07_save_batch_limit(uid, val)
        try:
            await cq.message.edit_text(
                f"<blockquote>{E_CHECK} <b>Batch limit updated</b>\n\n"
                f"{E_BATCH} Your next save will use <b>{label}</b>.</blockquote>",
                parse_mode=enums.ParseMode.HTML,
                reply_markup=get_batch_limit_markup(val)
            )
        except Exception:
            pass
        await cq.answer(f"Batch limit set to {label}", show_alert=True)

    # ── /ping ─────────────────────────────────────────────────────────────────

    @app.on_message(filters.private & filters.command("ping"))
    async def _ping(_, msg: Message):
        t0   = time.monotonic()
        sent = await msg.reply(f"<blockquote>{E_BOLT} <b>Checking speed...</b></blockquote>", parse_mode=enums.ParseMode.HTML)
        ms   = int((time.monotonic() - t0) * 1000)
        qual = E_GREEN if ms < 300 else (E_WARN if ms < 800 else E_RED)
        await sent.edit_text(
            f"<blockquote>{E_BOLT} <b>Pong!</b>\n\n"
            f"{qual} <b>Response time:</b> <code>{ms} ms</code></blockquote>",
            parse_mode=enums.ParseMode.HTML
        )

    # ── /status ───────────────────────────────────────────────────────────────

    @app.on_message(filters.private & filters.command("status"))
    async def _status(_, msg: Message):
        uid = msg.from_user.id if msg.from_user else None
        if not uid:
            return
        logged_in   = bool(lastperson07_load_session(uid))
        caption     = lastperson07_load_caption(uid)
        batch_limit = lastperson07_load_batch_limit(uid)
        downloads   = lastperson07_get_user_downloads(uid)
        job_active  = uid in _active
        limit_label = "∞ Unlimited" if batch_limit == 0 else str(batch_limit)
        await msg.reply(
            f"<blockquote>{E_INFO} <b>Your Status</b>\n\n"
            f"{E_GREEN if logged_in else E_RED} <b>Session:</b> {'Connected and ready' if logged_in else 'Not connected'}\n"
            f"{E_PENCIL} <b>Caption:</b> {caption if caption else 'Not set'}\n"
            f"{E_BATCH} <b>Batch limit:</b> {limit_label}\n"
            f"{E_STAR} <b>Files saved:</b> {downloads}\n"
            f"{E_BOLT if job_active else E_STOP} <b>Active task:</b> {'Running now' if job_active else 'Nothing running right now'}</blockquote>",
            parse_mode=enums.ParseMode.HTML,
            reply_markup=get_back_markup()
        )


def create_app() -> Client:
    app = Client(
        BOT_SESSION_NAME, api_id=API_ID, api_hash=API_HASH,
        bot_token=BOT_TOKEN, workers=BOT_WORKERS,
        sleep_threshold=FLOOD_SLEEP_THRESHOLD,
    )
    _register_core(app)
    lastperson07_register_session(app)
    lastperson07_register_save(app)
    return app


def main():
    lastperson07_assert_integrity()
    lastperson07_db_init()
    if ENABLE_HEALTHCHECK:
        lastperson07_keep_alive()
    log.info("Starting bot")
    create_app().run()


if __name__ == "__main__":
    main()
