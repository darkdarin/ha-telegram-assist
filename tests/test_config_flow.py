"""Choosing the bot and the assistant; mapping Telegram users to Home Assistant users."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import BOT, Setup


async def test_needs_a_telegram_bot_first(hass: HomeAssistant) -> None:
    assert await async_setup_component(hass, "homeassistant", {})
    result = await hass.config_entries.flow.async_init(
        "telegram_assist", context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "no_bot"


async def test_picks_a_bot(hass: HomeAssistant) -> None:
    assert await async_setup_component(hass, "homeassistant", {})
    MockConfigEntry(domain="telegram_bot", entry_id=BOT, title="@home_bot").add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        "telegram_assist", context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"bot_entry_id": BOT}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "@home_bot" and result["data"] == {"bot_entry_id": BOT}
    again = await hass.config_entries.flow.async_init(
        "telegram_assist", context={"source": config_entries.SOURCE_USER}
    )
    again = await hass.config_entries.flow.async_configure(again["flow_id"], {"bot_entry_id": BOT})
    assert again["type"] is FlowResultType.ABORT and again["reason"] == "already_configured"


async def test_maps_and_unmaps_users(setup: Setup) -> None:
    hass, entry = setup.hass, setup.entry
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    assert flow["type"] is FlowResultType.MENU
    flow = await hass.config_entries.options.async_configure(
        flow["flow_id"], {"next_step_id": "add_user"}
    )
    bad = await hass.config_entries.options.async_configure(
        flow["flow_id"], {"telegram_user": "pavel", "ha_user": setup.user}
    )
    assert bad["errors"] == {"telegram_user": "not_a_number"}
    done = await hass.config_entries.options.async_configure(
        flow["flow_id"], {"telegram_user": "7", "ha_user": setup.user}
    )
    assert done["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["users"] == {"42": setup.user, "7": setup.user}
    await setup.message("теперь я свой", user=7)
    assert setup.telegram.texts[-1].startswith(f"{setup.user}|")  # applies without a reload

    flow = await hass.config_entries.options.async_init(entry.entry_id)
    flow = await hass.config_entries.options.async_configure(
        flow["flow_id"], {"next_step_id": "remove_user"}
    )
    done = await hass.config_entries.options.async_configure(flow["flow_id"], {"users": ["7"]})
    assert done["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["users"] == {"42": setup.user}
