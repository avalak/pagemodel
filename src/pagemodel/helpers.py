"""
Convenience helpers for building field descriptors with a compact syntax.

- ``Q`` / ``Sel`` create a ``Field`` (CSS selector) with optional pipeline.
- ``X`` creates an ``XpathField`` with optional pipeline.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from .fields import Field, XpathField
from .pipeline import Pipe


class _Q:
    """Helper to build a ``Field`` (CSS selector) with optional pipeline.

    Usage::

        title = Q("h1")
        price = Q(".price @data-value") | float
        missing = (Q(".missing"), "N/A")
    """

    __slots__ = ("_selector", "_attr", "_default", "_pipe", "_name")

    def __init__(self, raw: str) -> None:
        parts = raw.split("@", 1)
        self._selector = parts[0].strip()
        self._attr = parts[1].strip() if len(parts) > 1 else None
        self._default: Any = None
        self._pipe: Pipe | None = None
        self._name: str | None = None

    def __or__(self, func: Callable[[Any], Any]) -> _Q:
        new = copy.copy(self)
        if new._pipe is None:
            new._pipe = Pipe(func)
        else:
            new._pipe = new._pipe | func
        return new

    def to_field(self, default: Any = None) -> Field:
        """Build the final ``Field`` instance."""
        default = default if default is not None else self._default
        return Field(
            self._selector,
            attr=self._attr,
            converter=self._pipe,
            default=default,
        )

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name
        if not hasattr(owner, "_pagemodel_export"):
            owner._pagemodel_export = []
        owner._pagemodel_export.append((name, name))

    def __get__(self, instance: Any, owner: type) -> Any:
        if instance is None:
            return self
        field = self.to_field()
        field.__set_name__(owner, self._name)
        setattr(owner, self._name, field)
        return field.__get__(instance, owner)


class _X:
    """Helper to build an ``XpathField`` with optional pipeline.

    Usage::

        heading = X("//h1/text()")
        price = X("//div/@data-value") | float
        missing = (X("//h2/text()"), "Default")
    """

    __slots__ = ("_selector", "_default", "_pipe", "_name")

    def __init__(self, raw: str) -> None:
        if raw.startswith("xpath:"):
            raw = raw[6:]
        self._selector = raw
        self._default: Any = None
        self._pipe: Pipe | None = None
        self._name: str | None = None

    def __or__(self, func: Callable[[Any], Any]) -> _X:
        new = copy.copy(self)
        if new._pipe is None:
            new._pipe = Pipe(func)
        else:
            new._pipe = new._pipe | func
        return new

    def to_field(self, default: Any = None) -> XpathField:
        """Build the final ``XpathField`` instance."""
        default = default if default is not None else self._default
        return XpathField(self._selector, converter=self._pipe, default=default)

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name
        if not hasattr(owner, "_pagemodel_export"):
            owner._pagemodel_export = []
        owner._pagemodel_export.append((name, name))

    def __get__(self, instance: Any, owner: type) -> Any:
        if instance is None:
            return self
        field = self.to_field()
        field.__set_name__(owner, self._name)
        setattr(owner, self._name, field)
        return field.__get__(instance, owner)


Q = _Q
Sel = _Q  # alias for CSS helper
X = _X
