"""Config flow: which bot, which assistant; options: settings and who is who."""

from __future__ import annotations

from typing import Any

import probatio
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_BOT,
    CONF_ONLY_KNOWN,
    CONF_PIPELINE,
    CONF_SHOW_HEARD,
    CONF_USERS,
    DOMAIN,
    TELEGRAM,
)

CONF_TELEGRAM_USER = "telegram_user"
CONF_HA_USER = "ha_user"
ALLOWED_CHATS = "allowed_chat_ids"  # telegram_bot's subentries: {chat_id}, titled with the name


class TelegramAssistConfigFlow(ConfigFlow, domain=DOMAIN):
    """Pick a Telegram bot (set up in Telegram bot) and the assistant that answers it."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> TelegramAssistOptionsFlow:
        return TelegramAssistOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        bots = self.hass.config_entries.async_entries(TELEGRAM)
        if not bots:
            return self.async_abort(reason="no_bot")
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_BOT])
            self._abort_if_unique_id_configured()
            bot = self.hass.config_entries.async_get_entry(user_input[CONF_BOT])
            return self.async_create_entry(
                title=bot.title if bot else "Telegram Assist",
                data={CONF_BOT: user_input[CONF_BOT]},
                options={CONF_PIPELINE: user_input.get(CONF_PIPELINE), CONF_USERS: {}},
            )
        schema = probatio.Schema(
            {
                probatio.Required(CONF_BOT): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=b.entry_id, label=b.title) for b in bots
                        ]
                    )
                ),
                probatio.Optional(CONF_PIPELINE): selector.AssistPipelineSelector(),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)


class TelegramAssistOptionsFlow(OptionsFlow):
    """The assistant, how answers look, and which Telegram user is which Home Assistant user."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="init", menu_options=["settings", "add_user", "remove_user"]
        )

    def _people(self) -> dict[str, str]:
        """Telegram users allowed to write to the bot, by id: its private allowed chats.

        A private chat's id is its user's id; group chats (negative ids) are not people.
        """
        bot = self.hass.config_entries.async_get_entry(str(self.config_entry.data[CONF_BOT]))
        people: dict[str, str] = {}
        for sub in bot.subentries.values() if bot else []:
            chat = sub.data.get("chat_id")
            if sub.subentry_type == ALLOWED_CHATS and isinstance(chat, int) and chat > 0:
                people[str(chat)] = sub.title or str(chat)
        return people

    def _options(self) -> dict[str, Any]:
        options = dict(self.config_entry.options)
        options[CONF_USERS] = dict(options.get(CONF_USERS) or {})
        return options

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        options = self._options()
        if user_input is not None:
            return self.async_create_entry(data=options | user_input)
        schema = probatio.Schema(
            {
                probatio.Optional(
                    CONF_PIPELINE, description={"suggested_value": options.get(CONF_PIPELINE)}
                ): selector.AssistPipelineSelector(),
                probatio.Optional(
                    CONF_SHOW_HEARD, default=options.get(CONF_SHOW_HEARD, True)
                ): selector.BooleanSelector(),
                probatio.Optional(
                    CONF_ONLY_KNOWN, default=options.get(CONF_ONLY_KNOWN, False)
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="settings", data_schema=schema)

    async def async_step_add_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        users = {
            u.id: u.name or u.id
            for u in await self.hass.auth.async_get_users()
            if not u.system_generated and u.is_active
        }
        if user_input is not None:
            telegram_user = str(user_input[CONF_TELEGRAM_USER]).strip()
            if not telegram_user.lstrip("-").isdigit():
                errors[CONF_TELEGRAM_USER] = "not_a_number"
            else:
                options = self._options()
                options[CONF_USERS][telegram_user] = user_input[CONF_HA_USER]
                return self.async_create_entry(data=options)
        people = self._people()
        mapped = self._options()[CONF_USERS]
        schema = probatio.Schema(
            {
                # the bot's allowed people first; any other id can be typed in
                probatio.Required(CONF_TELEGRAM_USER): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=tg, label=f"{name} ({tg})")
                            for tg, name in people.items()
                            if tg not in mapped
                        ],
                        custom_value=True,
                    )
                ),
                probatio.Required(CONF_HA_USER): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=uid, label=name)
                            for uid, name in users.items()
                        ]
                    )
                ),
            }
        )
        return self.async_show_form(step_id="add_user", data_schema=schema, errors=errors)

    async def async_step_remove_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        options = self._options()
        if not options[CONF_USERS]:
            return self.async_abort(reason="no_users")
        if user_input is not None:
            for telegram_user in user_input.get(CONF_USERS) or []:
                options[CONF_USERS].pop(telegram_user, None)
            return self.async_create_entry(data=options)
        names = {u.id: u.name or u.id for u in await self.hass.auth.async_get_users()}
        people = self._people()
        schema = probatio.Schema(
            {
                probatio.Required(CONF_USERS): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=tg, label=f"{people.get(tg, tg)} → {names.get(ha, ha)}"
                            )
                            for tg, ha in options[CONF_USERS].items()
                        ],
                        multiple=True,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="remove_user", data_schema=schema)
