"""Telegram Assist: messages of a Telegram bot answered by an Assist assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .bridge import AssistBridge

type TelegramAssistEntry = ConfigEntry[AssistBridge]


async def async_setup_entry(hass: HomeAssistant, entry: TelegramAssistEntry) -> bool:
    bridge = AssistBridge(hass, entry)
    bridge.start()
    entry.runtime_data = bridge
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TelegramAssistEntry) -> bool:
    await entry.runtime_data.stop()
    return True
