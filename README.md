<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/darkdarin/ha-telegram-assist/main/custom_components/telegram_assist/brand/dark_logo.png">
    <img alt="Telegram Assist" src="https://raw.githubusercontent.com/darkdarin/ha-telegram-assist/main/custom_components/telegram_assist/brand/logo.png" width="420">
  </picture>
</p>

# Telegram Assist for Home Assistant

[![Release](https://img.shields.io/github/v/release/darkdarin/ha-telegram-assist?sort=semver)](https://github.com/darkdarin/ha-telegram-assist/releases)
[![CI](https://github.com/darkdarin/ha-telegram-assist/actions/workflows/ci.yml/badge.svg)](https://github.com/darkdarin/ha-telegram-assist/actions/workflows/ci.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.10%2B-18BCF2?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)
[![License](https://img.shields.io/github/license/darkdarin/ha-telegram-assist)](LICENSE)

Talk to your Home Assistant **Assist** from Telegram. Text and voice messages to your bot are
answered by an Assist assistant of your choice: its conversation agent and speech-to-text handle
them exactly as they handle a voice satellite, so the same assistant answers at home and on the go.

> Early version (0.1). Answers come as text; voice replies and streamed answers are on the way.

## What you get

- **No external address needed.** The bot is Home Assistant's own
  [Telegram bot](https://www.home-assistant.io/integrations/telegram_bot/) integration in
  **Polling** mode; its allowed chats decide who may write.
- **Voice messages.** Home Assistant's ffmpeg decodes them, the assistant's speech-to-text
  recognizes them, its agent answers; the reply quotes what was heard, so a misheard command is
  obvious.
- **A dialogue per chat.** Follow-up questions keep their context; `/new` starts a new dialogue.
- **Who is who.** Map Telegram users to Home Assistant users: their messages are asked as that
  user, so agents know who is asking (with [FlowPilot](https://github.com/darkdarin/flowpilot),
  graphs can act on it). Optionally answer mapped users only.
- **Feels like a chat.** "typing…" shows while the assistant thinks, and a failure is told in the
  chat instead of silence.
- **Any agent.** The built-in Assist agent, an LLM integration or FlowPilot: whatever the
  assistant you pick uses. English and Russian.

## What you need

- Home Assistant **2026.10 or newer**.
- A Telegram bot (create one with [@BotFather](https://t.me/BotFather)) set up in the
  **Telegram bot** integration.
- An Assist assistant; for voice messages, one with speech-to-text.

## Installation

### Step 1. Set up the Telegram bot

[![Add the Telegram bot integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=telegram_bot)

1. Press the button (or **Settings → Devices & services → Add integration → Telegram bot**).
2. Choose the **Polling** platform and paste the bot's token: Home Assistant fetches messages
   itself, no port forwarding or external address.
3. Send `/start` to your bot, find your chat id (for example with
   [@userinfobot](https://t.me/userinfobot)) and add it in the integration under
   **⋮ → Add allowed chat ID**. Messages from other chats are dropped.

### Step 2. Install Telegram Assist

[![Open in the Marketplace](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=darkdarin&repository=ha-telegram-assist&category=integration)

1. Press the button. By hand on Home Assistant 2026.11 and newer: **Settings → Marketplace → Add
   from link**, enter `darkdarin/ha-telegram-assist`. On 2026.10: **HACS → ⋮ → Custom
   repositories**, add `https://github.com/darkdarin/ha-telegram-assist` with type
   **Integration**.
2. Install **Telegram Assist** and **restart Home Assistant**.

### Step 3. Connect the bot to an assistant

[![Add Telegram Assist](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=telegram_assist)

Pick the bot and the assistant that answers it. Then write to the bot: text or a voice message.

### Step 4. Tell it who is who (optional)

In **Telegram Assist → Configure → Map a Telegram user to a Home Assistant user**, enter a
Telegram user id and pick the Home Assistant user it is. Their messages are then asked as that
user.

## Using it

| You send | What happens |
|---|---|
| A text message | The assistant's agent answers it as a typed Assist command |
| A voice message | Speech-to-text, then the agent; the reply starts with 🎤 and what was heard |
| `/new` | A new dialogue in this chat: the agent forgets the earlier messages |

## Configuration

In **Telegram Assist → Configure**:

| Setting | What for |
|---|---|
| Assistant | Which Assist assistant answers: its agent, and its speech-to-text for voice messages |
| Quote what was heard | Start voice replies with the recognized text (on by default) |
| Answer only mapped users | Ignore Telegram users not mapped to a Home Assistant user |
| Map / remove users | Which Telegram user is which Home Assistant user |

Changes apply at once, without a restart.

## If something does not work

- **The bot does not answer at all.** Check that the chat is among the **allowed chat IDs** of the
  Telegram bot integration (Home Assistant's log says `Unauthorized update` otherwise), and that
  nothing else reads the same bot: a bot has one reader, so do not also answer it with your own
  automations or another app.
- **"⚠️ The assistant could not answer: …".** The assistant's agent or speech-to-text failed; the
  message says why, and Home Assistant's log has the details. Try the same command in the Assist
  chat of Home Assistant.
- **Voice messages are not understood.** Make sure the chosen assistant has a speech-to-text
  engine for your language; the 🎤 line shows what it heard.

## How it works

```
Telegram ──> Telegram bot integration (polling, allowed chats)
                 │ text, voice, /new
                 ▼
             Telegram Assist ──> Assist assistant: speech-to-text (voice) ──> conversation agent
                 │                                                                  │
                 └──────────── reply, "typing…" (Telegram bot actions) <────────────┘
```

Telegram Assist listens to the Telegram bot integration's events and replies with its actions; it
never talks to Telegram itself. Text goes to the assistant's agent; voice messages are downloaded
into the Telegram bot's own folder, decoded with Home Assistant's ffmpeg, run through the
assistant like a satellite's command, and deleted right after.

## Development

| Path | What |
|---|---|
| `custom_components/telegram_assist` | The integration (installed via Marketplace/HACS) |
| `tests/` | Tests in a real Home Assistant (pinned to one release) |
| `scripts/brand.py` | Renders the icon and logos |

```sh
uv sync && uv run pytest -q -p no:logging   # plus ruff and mypy, see AGENTS.md
```

Planning and the roadmap live in Notion (see [AGENTS.md](AGENTS.md)).

## License

[Apache-2.0](LICENSE).
