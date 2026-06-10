from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..pipeline import Pipe
from .base import BaseField


class XpathField(BaseField):
    """Extract data using an XPath expression.

    Returns the raw result of ``doc.xpath(selector)``, typically a list of
    strings or elements. Use ``index`` to pick a specific value.

    Parameters
    ----------
    selector : str
        XPath expression (e.g. ``//h1/text()``, ``//div/@data-value``).
    index : int or None, optional
        If None, return the whole list. If an integer, return the element at
        that index (default 0). If out of range, return ``default``.
    default : any, optional
        Value returned when the XPath matches nothing or index is out of range.
    namespaces : dict, optional
        Namespace prefix-to-URI mapping for the XPath expression.
    converter : callable or Pipe, optional
        Applied to the final value (before returning).
    is_exported : bool, optional
        Whether to include this field in ``export()`` output. Default True.
    """

    def __init__(
        self,
        selector: str,
        index: int | None = 0,
        default: Any = None,
        namespaces: dict[str, str] | None = None,
        converter: Pipe | list[Callable] | Callable | None = None,
        is_exported: bool = True,
    ) -> None:
        super().__init__(converter, is_exported)
        self.selector = selector
        self.index = index
        self._default = default
        self._namespaces = namespaces

    def _get(self, instance: Any, owner: type) -> Any:
        result = instance.doc.xpath(self.selector, namespaces=self._namespaces)
        try:
            if self.index is not None:
                return result[self.index]
            return result
        except IndexError:
            return self._default if self.index is not None else []
