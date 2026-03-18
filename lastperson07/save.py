"""
  public  → bot.copy_message
  private → userbot copies to bot (via @username) → bot relays to user DM → delete
  batch   → user-defined limit, 7s gap, 
  DONT f**ck the code , if u dont know then leave it ------
"""
import asyncio, html, logging, random, re, time

from pyrogram import Client, enums, filters, StopPropagation
from pyrogram.enums import ButtonStyle
from pyrogram.errors import AuthKeyUnregistered, ChatForwardsRestricted, FloodWait
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyParameters

from config import API_ID, API_HASH
from lastperson07.db import lastperson07_load_session, lastperson07_delete_session, lastperson07_load_caption, lastperson07_save_caption, lastperson07_delete_caption, lastperson07_load_batch_limit, lastperson07_increment_downloads, lastperson07_register_user
from lastperson07.runtime import (
    FLOOD_SLEEP_THRESHOLD, E_BATCH, E_CLOCK, E_CHECK, E_CROSS, E_STOP, E_ARROW, E_INFO,
    ICON_CANCEL, E_LOCK, REACTIONS, E_TIP, E_PENCIL
)

log = logging.getLogger(__name__)

SEND_INTERVAL = 7.0

_PUB  = re.compile(r"(?:https?://)?t\.me/([a-zA-Z][a-zA-Z0-9_]{3,})/(\d+)(?:-(\d+))?", re.I)
_PRIV = re.compile(r"(?:https?://)?t\.me/c/(\d+)/(\d+)(?:-(\d+))?", re.I)
_CANCEL = InlineKeyboardMarkup([[
    InlineKeyboardButton("Cancel", callback_data="lp7:cancel", icon_custom_emoji_id=ICON_CANCEL, style=ButtonStyle.DANGER)
]])

_lock    = asyncio.Lock()
_active: dict = {}
_clients: dict = {}
_relay: dict[int, asyncio.Queue] = {} 

_BOT_USERNAME: str = ""  


# ── helpers ───────────────────────────────────────────────────────────────────

def _esc(e): return html.escape(str(e), quote=False)

def _parse(text: str, limit: int = 50) -> dict | None:
    max_ids = limit if limit > 0 else 10_000   # 0 = unlimited (capped at 10k for safety)
    if m := _PRIV.search(text):
        s, e = int(m.group(2)), int(m.group(3)) if m.group(3) else int(m.group(2))
        return {"chat": int(f"-100{m.group(1)}"), "ids": list(range(s, min(e, s + max_ids - 1) + 1)), "pub": False}
    if m := _PUB.search(text):
        s, e = int(m.group(2)), int(m.group(3)) if m.group(3) else int(m.group(2))
        return {"chat": m.group(1), "ids": list(range(s, min(e, s + max_ids - 1) + 1)), "pub": True}
    return None

async def _flood(fn, key=""):
    while True:
        try: return await fn()
        except FloodWait as e:
            log.warning("FloodWait %s → %ss", key, e.value)
            await asyncio.sleep(e.value + 1)

async def _edit(msg, text, markup=None):
    while True:
        try:
            return await msg.edit_text(text, parse_mode=enums.ParseMode.HTML, reply_markup=markup)
        except FloodWait as e:
            log.warning("FloodWait in _edit → %ss", e.value)
            await asyncio.sleep(e.value + 1)
        except Exception:
            break

async def _typing(bot, chat_id, secs=2.5):
    try: await bot.send_chat_action(chat_id, enums.ChatAction.TYPING)
    except Exception: pass
    await asyncio.sleep(secs)


async def _react(bot: Client, chat_id: int, msg_id: int):
    """Sends a random reaction on the user's message."""
    try:
        emoji = random.choice(REACTIONS)
        await bot.send_reaction(chat_id, msg_id, emoji)
    except Exception:
        pass


# ── userbot cache ─────────────────────────────────────────────────────────────

async def _acc(uid: int, session: str) -> Client | None:
    if (c := _clients.get(uid)) and getattr(c, "is_connected", False):
        return c
    _clients.pop(uid, None)
    try:
        c = Client(f"u{uid}", session_string=session, api_id=API_ID, api_hash=API_HASH,
                   in_memory=True, no_updates=True, sleep_threshold=FLOOD_SLEEP_THRESHOLD)
        await _flood(c.connect, f"connect:{uid}")
        _clients[uid] = c
        return c
    except AuthKeyUnregistered:
        lastperson07_delete_session(uid); return None
    except Exception as e:
        log.error("acc uid=%s %s", uid, e); return None


# ── send one ──────────────────────────────────────────────────────────────────

async def _send_one(bot: Client, dest: int, chat, mid: int, pub: bool,
                    acc: Client | None, uid: int) -> str:

    # public → bot copies directly (1 hop, no userbot needed)
    caption = lastperson07_load_caption(uid)

    if pub:
        try:
            await _flood(lambda: bot.copy_message(dest, chat, mid, caption=caption), "bot-copy")
            return "ok"
        except ChatForwardsRestricted:
            pass  # restricted public → fall through to userbot relay
        except Exception as e:
            err = str(e)
            return "skip" if ("INVALID" in err or "EMPTY" in err) else _esc(e)

    if not acc:
        return "no_session"

    # private/restricted ------
    q: asyncio.Queue = asyncio.Queue(maxsize=1)
    _relay[uid] = q
    relay_msg = None

    try:
        await _flood(
            lambda: acc.copy_message(_BOT_USERNAME, chat, mid),
            "acc→bot"
        )

        # wait for relay handler to deliver the message (timeout 30s)
        relay_msg = await asyncio.wait_for(q.get(), timeout=30)

        await _flood(
            lambda: bot.copy_message(dest, relay_msg.chat.id, relay_msg.id, caption=caption),
            "bot→user"
        )
        return "ok"

    except asyncio.TimeoutError:
        return "relay_timeout"
    except AuthKeyUnregistered:
        return "session_expired"
    except Exception as e:
        return _esc(e)
    finally:
        _relay.pop(uid, None)
        if relay_msg:
            try: await relay_msg.delete()
            except Exception: pass


# ── batch ──────────────────────────────────────────────────────────────

async def _run(bot: Client, msg: Message, parsed: dict, uid: int):
    dest, chat, ids, pub = msg.chat.id, parsed["chat"], parsed["ids"], parsed["pub"]
    total, batch = len(ids), len(ids) > 1
    start_time = time.monotonic()

    _active[uid] = job = {"cancel": False}
    await _typing(bot, dest, 1.5)

    status = await _flood(lambda: bot.send_message(dest,
        (
            f"<blockquote>{E_BATCH} <b>Starting your batch save</b>\n\n"
            f"{E_INFO} Messages queued: <b>{total}</b></blockquote>"
        ) if batch else
        f"<blockquote>{E_CLOCK} <b>Getting that message ready...</b></blockquote>",
        parse_mode=enums.ParseMode.HTML,
        reply_parameters=ReplyParameters(message_id=msg.id),
        reply_markup=_CANCEL,
    ), "bot-status")

    acc = None
    if not pub:
        session = lastperson07_load_session(uid)
        if not session:
            return await _edit(
                status,
                f"<blockquote>{E_LOCK} <b>Login required</b>\n\n"
                f"{E_INFO} Please use /login first, then send the link again.</blockquote>"
            )
        acc = await _acc(uid, session)
        if not acc:
            return await _edit(
                status,
                f"<blockquote>{E_CROSS} <b>Session problem</b>\n\n"
                f"{E_INFO} Please use /logout, then /login again.</blockquote>"
            )

    ok = skip = fail = 0

    for i, mid in enumerate(ids, 1):
        if job["cancel"]:
            return await _edit(status,
                f"<blockquote>{E_STOP} <b>Batch cancelled</b>\n\n"
                f"{E_CHECK} <b>Processed:</b> {i-1}/{total}\n"
                f"{E_ARROW} <b>Remaining:</b> {total - (i-1)}</blockquote>"
            )

        if batch:
            elapsed = time.monotonic() - start_time
            eta_val = (elapsed / max(1, i-1)) * (total - (i-1)) if i > 1 else 0
            eta = f"{int(eta_val // 60)}m {int(eta_val % 60)}s" if eta_val > 60 else f"{int(eta_val)}s"
            pct = int((i-1) * 100 / total)
            bar_len = 20
            filled = int((i-1) * bar_len / total)
            bar = "▰" * filled + "▱" * (bar_len - filled)
            await _edit(status,
                f"<blockquote>{E_BATCH} <b>Batch in progress</b>\n"
                f"<code>[{bar}]</code> {pct}%\n\n"
                f"{E_INFO} <b>Processing:</b> {i}/{total}\n"
                f"{E_CHECK} <b>Saved:</b> {ok}\n"
                f"{E_ARROW} <b>Skipped:</b> {skip}\n"
                f"{E_CROSS} <b>Failed:</b> {fail}\n"
                f"{E_CLOCK} <b>ETA:</b> {eta}</blockquote>",
                _CANCEL)

        result = await _send_one(bot, dest, chat, mid, pub, acc, uid)

        match result:
            case "ok":                        ok += 1
            case "skip":                      skip += 1
            case "no_session" | "session_expired":
                return await _edit(
                    status,
                    f"<blockquote>{E_LOCK} <b>Your session expired</b>\n\n"
                    f"{E_INFO} Please use /logout, then /login and try again.</blockquote>"
                )
            case "relay_timeout":
                return await _edit(
                    status,
                    f"<blockquote>{E_CLOCK} <b>Relay timed out</b>\n\n"
                    f"{E_TIP} Please try that link again in a moment.</blockquote>"
                )
            case _:
                fail += 1
                log.warning("mid=%s err=%s", mid, result)


        if i < total:
            await _typing(bot, dest, 2.5)
            await asyncio.sleep(SEND_INTERVAL - 2.5)  

    if batch:
        dur = time.monotonic() - start_time
        dur_str = f"{int(dur // 60)}m {int(dur % 60)}s" if dur > 60 else f"{int(dur)}s"
        await _edit(status,
            f"<blockquote>{E_CHECK} <b>Batch finished</b>\n\n"
            f"{E_CLOCK} <b>Total time:</b> {dur_str}\n"
            f"{E_CHECK} <b>Saved:</b> {ok}/{total}\n"
            f"{E_ARROW} <b>Skipped:</b> {skip}\n"
            f"{E_CROSS} <b>Failed:</b> {fail}</blockquote>"
        )
    else:
        try: await status.delete()
        except Exception: pass

    if ok:
        lastperson07_increment_downloads(uid, ok)
        await _react(bot, dest, msg.id)

    log.info("done uid=%s chat=%s ok=%s skip=%s fail=%s", uid, chat, ok, skip, fail)


# ── register ──────────────────────────────────────────────────────────────────

def lastperson07_register_save(app: Client):

    @app.on_message(filters.private & filters.incoming, group=2)
    async def _relay_receiver(_, msg: Message):
        """Catch files sent by userbots into bot DM — deliver to waiting _send_one."""
        uid = msg.from_user.id if msg.from_user else None
        if uid and (q := _relay.get(uid)) and not q.full():
            await q.put(msg)
            raise StopPropagation

    @app.on_callback_query(filters.regex(r"^lp7:cancel$"))
    async def _cancel(_, cq: CallbackQuery):
        uid = cq.from_user.id
        if job := _active.get(uid):
            job["cancel"] = True; await cq.answer("Cancelling your current save...")
        else:
            await cq.answer("There isn't an active save right now.", show_alert=True)

    @app.on_message(filters.private & filters.command("setcaption"))
    async def _setcaption(_, msg: Message):
        uid = msg.from_user.id if msg.from_user else None
        parts = msg.text.split(maxsplit=1)
        if len(parts) < 2:
            await msg.reply(
                f"<blockquote>{E_PENCIL} <b>Set a caption</b>\n\n"
                f"{E_TIP} Use <code>/setcaption Your text here</code>\n"
                f"{E_INFO} That text will be added to the files you save.</blockquote>",
                parse_mode=enums.ParseMode.HTML
            )
            return
        caption = parts[1].strip()
        lastperson07_save_caption(uid, caption)
        await msg.reply(f"<blockquote>{E_CHECK} <b>Caption saved</b>\n\n"
                        f"{E_PENCIL} Your saved files will now include:\n\n{_esc(caption)}</blockquote>",
                        parse_mode=enums.ParseMode.HTML)

    @app.on_message(filters.private & filters.command("delcaption"))
    async def _delcaption(_, msg: Message):
        uid = msg.from_user.id if msg.from_user else None
        lastperson07_delete_caption(uid)
        await msg.reply(
            f"<blockquote>{E_CHECK} <b>Caption removed</b>\n\n"
            f"{E_INFO} Saved files will keep their original captions when available.</blockquote>",
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_message(filters.private & filters.text & ~filters.regex(r"^/"), group=0)
    async def _handler(bot: Client, msg: Message):
        global _BOT_USERNAME
        from lastperson07.session import lastperson07_states

        if not _BOT_USERNAME:
            me = await bot.get_me()
            _BOT_USERNAME = me.username

        uid = msg.from_user.id if msg.from_user else None
        if not uid or not msg.text or uid in lastperson07_states:
            return
        lastperson07_register_user(uid)
        limit  = lastperson07_load_batch_limit(uid)
        parsed = _parse(msg.text.strip(), limit)
        if not parsed:
            return
        if _lock.locked():
            await _typing(bot, msg.chat.id, 1.0)
            if uid in _active:
                await msg.reply(
                    f"<blockquote>{E_CLOCK} <b>A save is already running</b>\n\n"
                    f"{E_INFO} Wait for it to finish, or tap Cancel below.</blockquote>",
                    parse_mode=enums.ParseMode.HTML,
                    reply_markup=_CANCEL
                )
            else:
                await msg.reply(
                    f"<blockquote>{E_CLOCK} <b>Another save is in progress</b>\n\n"
                    f"{E_INFO} Please wait a moment and send your link again.</blockquote>",
                    parse_mode=enums.ParseMode.HTML,
                )
            return
        async with _lock:
            try:
                await _run(bot, msg, parsed, uid)
            except Exception as e:
                log.error("handler uid=%s %s", uid, e)
                await bot.send_message(msg.chat.id,
                    f"<blockquote>{E_CROSS} <b>Something went wrong</b>\n\n"
                    f"<code>{_esc(e)}</code></blockquote>",
                    parse_mode=enums.ParseMode.HTML)
            finally:
                _active.pop(uid, None)

    # ── react to every private message ────────────────────────────────────────

    @app.on_message(filters.private & filters.incoming, group=99)
    async def _react_all(bot: Client, msg: Message):
        """React with a random emoji on every message the user sends."""
        await _react(bot, msg.chat.id, msg.id)
