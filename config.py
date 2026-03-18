import logging
import os
import sys

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return False


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# Hardcoded values are set here. If left empty, the system will automatically use environment variables instead.

API_ID = 0
API_HASH = ""
BOT_TOKEN = ""


def _pick_str(current: str, env_name: str) -> str:
    return (current or os.environ.get(env_name, "")).strip()


def _pick_int(current: int, env_name: str) -> int:
    if current:
        return current

    raw = os.environ.get(env_name, "").strip()
    if not raw:
        return 0

    try:
        return int(raw)
    except ValueError:
        logging.critical("%s must be an integer", env_name)
        sys.exit(1)


API_ID = _pick_int(API_ID, "API_ID")
API_HASH = _pick_str(API_HASH, "API_HASH")
BOT_TOKEN = _pick_str(BOT_TOKEN, "BOT_TOKEN")


if not API_ID:
    logging.critical("Set API_ID in config.py or environment")
    sys.exit(1)

if not API_HASH:
    logging.critical("Set API_HASH in config.py or environment")
    sys.exit(1)

if not BOT_TOKEN:
    logging.critical("Set BOT_TOKEN in config.py or environment")
    sys.exit(1)
