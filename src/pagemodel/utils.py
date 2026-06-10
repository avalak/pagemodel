"""
Low‑level extraction utilities that work directly with ``lxml`` elements.

These functions are independent of the page/fragment class system and can be
used for quick, one‑off extraction tasks.
"""

from __future__ import annotations

import copy
from typing import Any

from lxml import etree
from lxml.cssselect import CSSSelector
from lxml.html import HtmlElement

__all__ = (
    "get_attr",
    "get_elm",
    "get_text",
    "get_text_content",
    "is_elm_exists",
)

_Selector = str | CSSSelector


def _is_xpath_selector(sel: str) -> bool:
    return isinstance(sel, str) and (
        sel.startswith("/")
        or sel.startswith(".//")
        or sel.startswith("..")
        or sel.startswith("xpath:")
    )


def _execute_selector(ctx, selector: _Selector, namespaces: dict[str, str] | None = None) -> list:
    """Execute a CSS or XPath selector and return a list of elements."""
    if isinstance(selector, CSSSelector):
        return selector(ctx)
    # string selector
    if namespaces:
        return ctx.xpath(selector, namespaces=namespaces)
    if _is_xpath_selector(selector):
        sel = selector[6:] if selector.startswith("xpath:") else selector
        return ctx.xpath(sel)
    else:
        sel = CSSSelector(selector)
        return sel(ctx)


def _text_content(elm) -> str:
    """Get text content from an element, supporting both HtmlElement and etree._Element."""
    if hasattr(elm, "text_content"):
        return elm.text_content()
    # Fallback for plain lxml elements
    return etree.tounicode(elm, method="text").strip()


def get_elm(
    ctx: HtmlElement,
    selector: _Selector,
    index: int | None = 0,
    namespaces: dict[str, str] | None = None,
) -> HtmlElement | list[HtmlElement] | None:
    elms: list = _execute_selector(ctx, selector, namespaces)
    try:
        if index is not None:
            return elms[index]
        return elms
    except IndexError:
        return None if index is not None else elms


def get_text(
    ctx: HtmlElement,
    selector: _Selector,
    index: int | None = 0,
    default: Any = None,
    namespaces: dict[str, str] | None = None,
) -> str | list[str] | None:
    elms: list = _execute_selector(ctx, selector, namespaces)
    try:
        if index is not None:
            return _text_content(elms[index])
        return [_text_content(elm) for elm in elms]
    except IndexError:
        return default if index is not None else []


def get_attr(
    ctx: HtmlElement,
    selector: _Selector,
    attr: str,
    index: int | None = 0,
    default: Any = None,
    namespaces: dict[str, str] | None = None,
) -> str | list[str] | None:
    elms: list = _execute_selector(ctx, selector, namespaces)
    try:
        if index is not None:
            return elms[index].get(attr, default)
        return [elm.get(attr, default) for elm in elms]
    except IndexError:
        return default if index is not None else []


def get_text_content(elm: HtmlElement, glue: str = "\n") -> str:
    """
    Return the full text content of an element, replacing <br/> tags with `glue`.
    A deep copy is made to avoid mutating the original tree.
    """
    elm_copy = copy.deepcopy(elm)
    for br in elm_copy.xpath("//br"):
        br.tail = glue + (br.tail or "")
    return _text_content(elm_copy)


def is_elm_exists(
    ctx: HtmlElement,
    selector: _Selector,
    namespaces: dict[str, str] | None = None,
) -> bool:
    elms: list = _execute_selector(ctx, selector, namespaces)
    return len(elms) > 0
