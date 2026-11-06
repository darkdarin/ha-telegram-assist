"""Short replies of the bot itself, in the language of Home Assistant."""

from __future__ import annotations

TEXTS: dict[str, dict[str, str]] = {
    "new": {"en": "🆕 A new dialogue.", "ru": "🆕 Новый диалог."},
    "too_long": {"en": "⚠️ The voice message is too long.", "ru": "⚠️ Голосовое слишком длинное."},
    "not_heard": {"en": "🤷 Nothing was recognized.", "ru": "🤷 Ничего не распознано."},
    "failed": {
        "en": "⚠️ The assistant could not answer: {error}",
        "ru": "⚠️ Ассистент не смог ответить: {error}",
    },
}


def text(key: str, language: str | None, **values: str) -> str:
    base = (language or "en").replace("_", "-").split("-")[0].lower()
    texts = TEXTS[key]
    return texts.get(base, texts["en"]).format(**values)
