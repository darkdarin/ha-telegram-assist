"""Constants for the Telegram Assist integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "telegram_assist"
TELEGRAM: Final = "telegram_bot"

CONF_BOT: Final = "bot_entry_id"  # the telegram_bot config entry whose messages we answer
CONF_PIPELINE: Final = "pipeline"  # the Assist assistant that answers (agent, speech-to-text)
CONF_USERS: Final = "users"  # {telegram user id: Home Assistant user id}
CONF_ONLY_KNOWN: Final = "only_known_users"
CONF_SHOW_HEARD: Final = "show_heard"  # quote the recognized text of a voice message

EVENT_TEXT: Final = "telegram_text"
EVENT_ATTACHMENT: Final = "telegram_attachment"
EVENT_COMMAND: Final = "telegram_command"

COMMAND_NEW: Final = "/new"  # start a new dialogue in this chat

TYPING_EVERY_S: Final = 4.0  # Telegram shows "typing…" for about 5 s per chat action
VOICE_MIME_TYPES: Final = ("audio/ogg", "audio/mpeg", "audio/mp4", "audio/x-m4a", "audio/wav")
MAX_VOICE_BYTES: Final = 20 * 1024 * 1024  # what Telegram lets bots download
