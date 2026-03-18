<h1 align="center">LITE SAVE BOT</h1>

<div align="center">

[![Python Version](https://img.shields.io/badge/Python-3.9+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Docker Support](https://img.shields.io/badge/Docker-Ready-2496ed?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Render Deploy](https://img.shields.io/badge/Deploy-Render-46e3b7?style=for-the-badge&logo=render&logoColor=white)](https://render.com/)

**A super simple Telegram bot that saves stuff from public and private post links.**  
Just paste a link, and let the bot do its thing. No fuss. 👍

</div>

---

## Why this bot? 🤔

Lite Save Bot was built with one goal in mind: saving Telegram media from message links, without any complicated setup. It's all about keeping things straightforward and reliable.

- **Public links**? Saved instantly -- no login required.
- **Private or restricted links**? No problem -- just a quick secure login and you're in.
- **Batch processing** is built right in.
- **Custom captions**? You can add or remove them easily.

---

## What it can do ✨

| Feature                 | Details                                                                           |
| :---------------------- | :-------------------------------------------------------------------------------- |
| **Public link saving**  | Save media from normal `t.me/channel/message_id` links.                           |
| **Private link saving** | Save from restricted `t.me/c/...` links after you log in.                         |
| **Batch support**       | Grab a range of messages, like `10-60`.                                           |
| **Batch limit control** | Set exactly how many messages to fetch per link.                                  |
| **Caption tools**       | Add your own custom caption or remove existing ones.                              |
| **Status check**        | See your session state, batch limit, caption settings, and how many you've saved. |
| **Login flow**          | Secure OTP keypad + 2FA password support -- just like Telegram.                   |
| **Render keep-alive**   | Built-in health server + auto-ping so it doesn't fall asleep on free hosts.       |

---

## Supported Links 🔗

### Single Message

Standard formatting for individual posts:

```text
https://t.me/channelname/123
https://t.me/c/1234567/123
```

### Batch Messages

Append a range to a normal message link to fetch multiple posts at once:

```text
https://t.me/channelname/10-60
https://t.me/c/1234567/10-60
```

So yeah, just add `-endID` to any message link and you're batch-saving.  
_Example:_

```text
https://t.me/somechannel/100-149
```

---

## Commands ⌨️

| Command              | What it does                                               |
| :------------------- | :--------------------------------------------------------- |
| `/start`             | Opens the main menu — your home base.                      |
| `/help`              | Shows usage instructions and examples.                     |
| `/login`             | Securely connects your Telegram account for private saves. |
| `/logout`            | Wipes your saved session.                                  |
| `/cancellogin`       | Aborts an ongoing login process.                           |
| `/status`            | Shows your session, caption, current task, and stats.      |
| `/ping`              | Checks the bot's response time (ping).                     |
| `/setcaption [text]` | Sets a custom caption to be added to downloaded media.     |
| `/delcaption`        | Removes your custom caption.                               |

---

## Quick Start 🏁

### 1. Install Dependencies

Make sure you have Python, then run:

```bash
pip install -r requirements.txt
```

### 2. Configure Credentials

You can put your environment variables in `config.py` or use a `.env` file.

**You'll need:**

- `API_ID`
- `API_HASH`
- `BOT_TOKEN`

_Example `.env` file:_

```env
API_ID=123456
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
```

### 3. Run the Bot

```bash
python bot.py
```

---

## Docker Deployment 🐳

### Build and Run Locally

```bash
docker build -t lite-save-bot .
docker run --env-file .env -v bot_data:/data lite-save-bot
```

### Run with Docker Compose

```bash
docker compose up --build -d
```

---

## Render Deployment Notes 🌐

This project comes with a built-in health server and a keep-alive ping loop -- perfect for free hosting platforms like Render.

It automatically checks these environment variables (in order) to build its ping URL:

1. `PING_URL`
2. `HEALTHCHECK_URL`
3. `RENDER_EXTERNAL_URL`
4. `APP_URL`
5. `RENDER_EXTERNAL_HOSTNAME`

If Render gives you `RENDER_EXTERNAL_HOSTNAME`, the bot can guess its public URL automatically.  
To force a specific ping target, just set:

```env
PING_URL=https://your-service.onrender.com
```

- pings every 5 minutes.\*

---

## Quick Q&A 💬

**How was this project made?**  
This bot was built in a short time with practicality in mind. Some parts were crafted and polished with the help of LLM tools — but the core idea was always: keep it clean, keep it simple, and make it work.

**Is it easy to deploy?**  
Totally. Just drop in your `API_ID`, `API_HASH`, and `BOT_TOKEN`, run it, and you're good to go.

**Do I need to login for every link?**  
Nope. Public links work right away without a session. For private or restricted links, you'll be prompted to run `/login` once.

**Is this meant for heavy, enterprise use?**  
Not really -- it's meant to stay lightweight. If your credentials are correct, it'll deploy smoothly locally, via Docker, or on cloud platforms like Render.

---

## Important Notes 📌

- The bot only works in **private chats** (for your safety).
- Only **one active save** runs at a time -- keeps things stable.
- Batch saves have a **7-second delay** between messages to avoid hitting API limits.
- Your session is stored **locally in SQLite** -- no external databases.
- There's a **built-in warning page** inside the bot UI so you always know what's up.

---

## Project Structure 📁

```text
.
|-- bot.py
|-- config.py
|-- requirements.txt
|-- Dockerfile
|-- docker-compose.yml
`-- LastPerson07/
    |-- __init__.py
    |-- db.py
    |-- keep_alive.py
    |-- runtime.py
    |-- save.py
    `-- session.py
```

---

## Last 💡

Lite Save Bot is all about being **lightweight, clear, and practical**. No extra noise, no confusing workflows -- just a clean Telegram saver with secure login, batch processing, custom captions, and a friendly UI.

LASTPERSON07! 😊
