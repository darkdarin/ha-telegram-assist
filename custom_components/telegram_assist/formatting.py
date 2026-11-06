"""Markdown of language models, as the HTML Telegram renders.

Agents answer in Markdown (``**bold**``, ``# headings``, lists, code). Telegram's own Markdown
modes do not read it (MarkdownV2 also rejects every unescaped ``.`` or ``-``), so the answer is
converted to the small HTML subset Telegram supports: ``b``, ``i``, ``s``, ``code``, ``pre``,
``a`` and ``blockquote``. What has no equivalent stays as text: headings become bold lines, list
markers become bullets, tables are left as they are.
"""

from __future__ import annotations

import html
import re

_FENCE = re.compile(r"^[ \t]*```[ \t]*([\w+#.-]*)[^\n]*\n(.*?)^[ \t]*```[ \t]*$", re.M | re.S)
_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_LINK = re.compile(r"\[([^\]\n]+)\]\((\S+?)(?:\s+\"[^\"]*\")?\)")
_URL = re.compile(r"https?://[^\s<>]+")
_HEADING = re.compile(r"^#{1,6}[ \t]+(.+?)[ \t#]*$")
_BULLET = re.compile(r"^([ \t]*)[-*+][ \t]+")
_RULE = re.compile(r"^[ \t]*([-*_])([ \t]*\1){2,}[ \t]*$")
_QUOTE = re.compile(r"^&gt;[ \t]?")
_BOLD_ITALIC = re.compile(r"\*\*\*(?=\S)(.+?)(?<=\S)\*\*\*")
_BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*|__(?=\S)(.+?)(?<=\S)__")
_ITALIC = re.compile(
    r"(?<![\w*])\*(?=[^\s*])([^*\n]+?)(?<=[^\s*])\*(?![\w*])"
    r"|(?<![\w_])_(?=[^\s_])([^_\n]+?)(?<=[^\s_])_(?![\w_])"
)
_STRIKE = re.compile(r"~~(?=\S)(.+?)(?<=\S)~~")
_SLOT = re.compile(r"\x00(\d+)\x00")


def to_telegram_html(markdown: str) -> str:
    """The answer as Telegram HTML; plain text comes out as escaped plain text."""
    slots: list[str] = []

    def keep(fragment: str) -> str:
        slots.append(fragment)
        return f"\x00{len(slots) - 1}\x00"

    def code_block(match: re.Match[str]) -> str:
        language, body = match.group(1), html.escape(match.group(2).rstrip("\n"), quote=False)
        attr = f' class="language-{html.escape(language)}"' if language else ""
        return keep(f"<pre><code{attr}>{body}</code></pre>")

    text = markdown.replace("\x00", "")
    text = _FENCE.sub(code_block, text)
    text = _INLINE_CODE.sub(lambda m: keep(f"<code>{html.escape(m[1], quote=False)}</code>"), text)
    text = _LINK.sub(lambda m: keep(_anchor(m[2], _inline(html.escape(m[1], quote=False)))), text)
    text = _URL.sub(lambda m: keep(html.escape(m[0], quote=False)), text)
    text = html.escape(text, quote=False)
    text = _blocks(text)
    while _SLOT.search(text):  # a link label may hold inline code
        text = _SLOT.sub(lambda m: slots[int(m[1])], text)
    return text.strip()


def _anchor(url: str, label: str) -> str:
    return f'<a href="{html.escape(url)}">{label}</a>'


def _inline(text: str) -> str:
    text = _BOLD_ITALIC.sub(lambda m: f"<b><i>{m[1]}</i></b>", text)
    text = _BOLD.sub(lambda m: f"<b>{m[1] or m[2]}</b>", text)
    text = _STRIKE.sub(lambda m: f"<s>{m[1]}</s>", text)
    return _ITALIC.sub(lambda m: f"<i>{m[1] or m[2]}</i>", text)


def _blocks(text: str) -> str:
    """Line by line: headings, bullets, rules and quotes; inline markup inside each line."""
    out: list[str] = []
    quote: list[str] = []

    def close_quote() -> None:
        if quote:
            out.append(f"<blockquote>{'\n'.join(quote)}</blockquote>")
            quote.clear()

    for line in text.split("\n"):
        if _QUOTE.match(line):
            quote.append(_inline(_QUOTE.sub("", line, count=1)))
            continue
        close_quote()
        if heading := _HEADING.match(line):
            out.append(f"<b>{_inline(heading[1])}</b>")
        elif _RULE.match(line):
            out.append("———")
        else:
            out.append(_inline(_BULLET.sub(lambda m: f"{m[1]}• ", line, count=1)))
    close_quote()
    return "\n".join(out)
