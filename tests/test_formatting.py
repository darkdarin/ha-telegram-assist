"""Markdown of language models as Telegram HTML."""

from __future__ import annotations

from importlib import import_module

import pytest

# by its package name, as Home Assistant loads it (mypy sees the sources as ``telegram_assist``)
formatting = import_module("custom_components.telegram_assist.formatting")


@pytest.mark.parametrize(
    ("markdown", "expected"),
    [
        ("Просто текст.", "Просто текст."),
        ("a < b & c > d", "a &lt; b &amp; c &gt; d"),
        ("**жирный** и __тоже__", "<b>жирный</b> и <b>тоже</b>"),
        ("*курсив* и _тоже_", "<i>курсив</i> и <i>тоже</i>"),
        ("~~нет~~", "<s>нет</s>"),
        ("***оба***", "<b><i>оба</i></b>"),
        ("sensor.living_room_temp и 2 * 3 * 4", "sensor.living_room_temp и 2 * 3 * 4"),
        ("`light.kitchen_main`", "<code>light.kitchen_main</code>"),
        ("`**<x>**`", "<code>**&lt;x&gt;**</code>"),
        ("## Свет", "<b>Свет</b>"),
        ("- раз\n* два\n  + три", "• раз\n• два\n  • три"),
        ("1. раз\n2. два", "1. раз\n2. два"),
        ("до\n---\nпосле", "до\n———\nпосле"),
        ("> цитата\n> вторая\n\nтекст", "<blockquote>цитата\nвторая</blockquote>\n\nтекст"),
        (
            "[**HA**](https://example.com/a_b?x=1&y=2)",
            '<a href="https://example.com/a_b?x=1&amp;y=2"><b>HA</b></a>',
        ),
        ("https://example.com/_a_/b", "https://example.com/_a_/b"),
        (
            "```yaml\nkey: <v>\n**x**\n```",
            '<pre><code class="language-yaml">key: &lt;v&gt;\n**x**</code></pre>',
        ),
        ("```\nplain\n```", "<pre><code>plain</code></pre>"),
    ],
)
def test_markdown_becomes_telegram_html(markdown: str, expected: str) -> None:
    assert formatting.to_telegram_html(markdown) == expected
