import hashlib
import logging
import os
import sys
from pathlib import Path

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
# Respect DATA_DIR env var so Docker volume mounts (/data) persist the DB.
# Falls back to project root when running locally without the env var.
DATA_DIR = Path(os.environ.get("DATA_DIR", str(BASE_DIR)))
DOWNLOADS_DIR = BASE_DIR / "downloads"

BOT_SESSION_NAME = "lite_bot"
BOT_WORKERS = 4
BOT_UPLOAD_TRANSMISSIONS = 4
USER_DOWNLOAD_TRANSMISSIONS = 1
FLOOD_SLEEP_THRESHOLD = 60
STATUS_UPDATE_INTERVAL = 8.0
STATUS_UPDATE_STEP = 15
REQUEST_INTERVAL = 1.25
LOGIN_STATE_TTL = 900
ENABLE_HEALTHCHECK = True

_KEY = 0x37

# @DmOwner
_NAME_PARTS = ("7773", "5a78", "4059", "5245")
_HASH_PARTS = {
    "a": "eff2ff9cb9ffda35",
    "b": "6bf952a49644f154",
    "c": "3a8bafb41ff0424f",
    "d": "08da7c9c099986d2",
}

# @adityaabhinav
_DEV2_PARTS = ("7756", "535e", "434e", "5656", "555f", "5e59", "5641")
_DEV2_HASH = {
    "a": "9673e24f70de9ee3",
    "b": "cf44347f86fb6a93",
    "c": "9d961c0001c05994",
    "d": "ce4054b6ca86b745",
}

# @cantarella_wuwa
_DEV3_PARTS = ("7754", "5659", "4356", "4552", "5b5b", "5668", "4042", "4056")
_DEV3_HASH = {
    "a": "715d339e9033c1d0",
    "b": "c54654c4a6493199",
    "c": "367645f96aee340b",
    "d": "798840b07a687eed",
}


def _decode(parts: tuple[str, ...]) -> str:
    return "".join(
        "".join(chr(byte ^ _KEY) for byte in bytes.fromhex(part))
        for part in parts
    )


def lastperson07_owner_tag() -> str:
    return _decode(_NAME_PARTS)


def lastperson07_owner_name() -> str:
    return lastperson07_owner_tag().lstrip("@")


def lastperson07_dev2_tag() -> str:
    return _decode(_DEV2_PARTS)


def lastperson07_dev2_name() -> str:
    return lastperson07_dev2_tag().lstrip("@")


def lastperson07_dev3_tag() -> str:
    return _decode(_DEV3_PARTS)


def lastperson07_dev3_name() -> str:
    return lastperson07_dev3_tag().lstrip("@")


def lastperson07_all_devs() -> list[dict]:
    """Return all devs as a list of dicts with tag and name."""
    return [
        {"tag": lastperson07_owner_tag(),  "name": lastperson07_owner_name()},
        {"tag": lastperson07_dev2_tag(),   "name": lastperson07_dev2_name()},
        {"tag": lastperson07_dev3_tag(),   "name": lastperson07_dev3_name()},
    ]


def _verify_hash(tag: str, hash_parts: dict) -> bool:
    digest = "".join(hash_parts[k] for k in ("b", "d", "a", "c"))
    return hashlib.sha256(tag.encode()).hexdigest() == digest


def lastperson07_integrity_ok() -> bool:
    return (
        _verify_hash(lastperson07_owner_tag(), _HASH_PARTS)
        and _verify_hash(lastperson07_dev2_tag(), _DEV2_HASH)
        and _verify_hash(lastperson07_dev3_tag(), _DEV3_HASH)
    )


def lastperson07_assert_integrity():
    if lastperson07_integrity_ok():
        return

    log.critical("Integrity check failed.")
    sys.exit(1)


DATA_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

REACTIONS = [
    "👍","❤️","🔥","🥰","👏","😁","🤔","🤯","😱","🤬","😢","🎉","🤩","🤮",
    "💩","🙏","👌","🕊","🤡","🥱","🥴","😍","🐳","❤️‍🔥","🌚","🌭","💯","🤣",
    "⚡","🍌","🏆","💔","🤨","😐","🍓","🍾","💋","🖕","😈","😴","😭","🤓",
    "👻","👨‍💻","👀","🎃","🙈","😇","😨","🤝","✍","🤗","🫡","🎅","🎄","☃",
    "💅","🤪","🗿","🆒","💘","🙉","🦄","😘","💊","🙊","😎","👾","🤷‍♂️","🤷‍♀️","😡",
]

E_0     = '<emoji id="5305749482170758709">0️⃣</emoji>'
E_1     = '<emoji id="5305763715692377402">1️⃣</emoji>'
E_2     = '<emoji id="5307907239380528763">2️⃣</emoji>'
E_3     = '<emoji id="5305783000095537258">3️⃣</emoji>'
E_4     = '<emoji id="5305255243104138538">4️⃣</emoji>'
E_5     = '<emoji id="5305288155438526869">5️⃣</emoji>'
E_6     = '<emoji id="5305642863902604489">6️⃣</emoji>'
E_7     = '<emoji id="5305603955793867793">7️⃣</emoji>'
E_8     = '<emoji id="5305371288825509083">8️⃣</emoji>'
E_9     = '<emoji id="5307703499016910744">9️⃣</emoji>'

DIGIT_EMOJI = [E_0, E_1, E_2, E_3, E_4, E_5, E_6, E_7, E_8, E_9]

E_LOCK    = '<emoji id=5296369303661067030>🔒</emoji>'
E_KEY     = '<emoji id=5296369303661067030>🔒</emoji>'
E_SHIELD  = '<emoji id=5251203410396458957>🛡</emoji>'
E_CLOCK   = '<emoji id=5386367538735104399>⌛</emoji>'
E_CHECK   = '<emoji id=5206607081334906820>✔️</emoji>'
E_CROSS   = '<emoji id=5210952531676504517>❌</emoji>'
E_WARN    = '<emoji id=5447644880824181073>⚠️</emoji>'
E_SPARK   = '<emoji id=5325547803936572038>✨</emoji>'
E_CROWN   = '<emoji id=5217822164362739968>👑</emoji>'
E_STAR    = '<emoji id=5438496463044752972>⭐️</emoji>'
E_GREEN   = '<emoji id=5416081784641168838>🟢</emoji>'
E_RED     = '<emoji id=5411225014148014586>🔴</emoji>'
E_ARROW   = '<emoji id=5416117059207572332>➡️</emoji>'
E_TIP     = '<emoji id=5422439311196834318>💡</emoji>'
E_STOP    = '<emoji id=5260293700088511294>⛔️</emoji>'
E_INFO    = '<emoji id=5334544901428229844>ℹ️</emoji>'
E_BOLT    = '<emoji id=5456140674028019486>⚡️</emoji>'
E_LINK    = '<emoji id=5271604874419647061>🔗</emoji>'
E_BATCH   = '<emoji id=5341498088408234504>💯</emoji>'
E_GEAR    = '<emoji id=5341715473882955310>⚙️</emoji>'
E_PENCIL  = '<emoji id=5395444784611480792>✏️</emoji>'

ICON_CANCEL   = 5210952531676504517
ICON_BACK     = 5447183459602669338
ICON_CHECK    = 5206607081334906820
ICON_WARN     = 5447644880824181073
ICON_REFRESH  = 5375338737028841420
ICON_INFO     = 5334544901428229844
ICON_HELP     = 5443038326535759644
ICON_DEV      = 5823268688874179761
ICON_GEAR     = 5341715473882955310
ICON_PENCIL   = 5395444784611480792
ICON_TRASH    = 5260293700088511294

WARNING_TXT = (
    f"<b>{E_WARN} Warning</b>\n\n"
    "This bot is provided for convenience, but <b>use it at your own risk</b>.\n\n"
    "If you send too many requests, spam links, or try to download content too quickly, "
    "<b>Telegram’s anti-flood system may temporarily or permanently restrict or ban your account</b>.\n\n"
    "<b>The developers of this bot are NOT responsible for any bans, restrictions, or issues with your Telegram account.</b>\n"
    "By using this bot, you agree that <b>you are fully responsible for how you use it.</b>\n\n"
    "Use the bot carefully and avoid spamming or excessive downloading."
)
