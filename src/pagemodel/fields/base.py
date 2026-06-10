from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any, TypeVar

from lxml.cssselect import CSSSelector

from ..log import logger
from ..pipeline import Pipe

T = TypeVar("T")


class _export(property):
    """Descriptor that caches the result of a method on the instance's __dict__.

    Used by the ``@export`` decorator to turn a method into a lazily evaluated
    property whose value is included in ``export()``.
    """

    def __init__(self, func: Callable[..., Any]) -> None:
        super().__init__()
        self._export_name: str | None = None
        self._func = func
        self._attr_name: str | None = None

    def __set_name__(self, owner: type, name: str) -> None:
        self._attr_name = name
        if not hasattr(owner, "_pagemodel_export"):
            owner._pagemodel_export = []
        owner._pagemodel_export.append((name, self._export_name or name))

    def __get__(self, instance: Any, owner: type) -> Any:
        if instance is None:
            return self
        cache = instance.__dict__
        if self._attr_name not in cache:
            logger.debug("Computing @export field: %s", self._attr_name)
            cache[self._attr_name] = self._func(instance)
        else:
            logger.debug("Cache hit for @export field: %s", self._attr_name)
        return cache[self._attr_name]


def export(arg: Callable | str) -> Any:
    """Decorator that marks a method for inclusion in ``export()``.

    Can be used without arguments::

        @export
        def computed_value(self):
            return ...

    or with a custom export name::

        @export("custom_name")
        def some_method(self):
            return ...
    """
    if callable(arg):
        return _export(arg)

    def wrapper(func: Callable) -> _export:
        obj = _export(func)
        obj._export_name = arg
        return obj

    return wrapper


class BaseField:
    """Base descriptor for all field types.

    Provides caching, pipeline support, automatic registration for export,
    and low‑level CSS/XPath query execution.  Concrete field classes must
    implement ``_get(instance, owner)``.
    """

    def __init__(
        self,
        converter: (Pipe | list[Callable[[Any], Any]] | Callable[[Any], Any] | None) = None,
        is_exported: bool = True,
    ) -> None:
        self.is_exported = is_exported
        if isinstance(converter, Pipe):
            self._pipe = converter
        elif isinstance(converter, (list, tuple)):
            self._pipe = Pipe(*converter)
        else:
            self._pipe = Pipe(converter) if converter else None
        self._attr_name: str | None = None
        self._cached_selector = None
        self._is_xpath: bool | None = None  # cached flag

    def __set_name__(self, owner: type, name: str) -> None:
        self._attr_name = name
        if not self.is_exported or name.startswith("_"):
            return
        if not hasattr(owner, "_pagemodel_export"):
            owner._pagemodel_export = []
        owner._pagemodel_export.append((name, name))

    def __get__(self, instance: Any, owner: type) -> Any:
        """Extract the value on first access, apply the pipeline, and cache."""
        if instance is None:
            return self
        cache = instance.__dict__
        if self._attr_name not in cache:
            logger.debug("Extracting value for field: %s", self._attr_name)
            value = self._get(instance, owner)
            if self._pipe is not None:
                value = self._pipe(value)
            cache[self._attr_name] = value
        else:
            logger.debug("Cache hit for field: %s", self._attr_name)
        return cache[self._attr_name]

    def _get(self, instance: Any, owner: type) -> Any:
        """Override in subclasses to perform the actual extraction."""
        raise NotImplementedError()

    def __or__(self, other: Pipe | Callable[[Any], Any]) -> BaseField:
        """Add a pipeline step (or pipe) to the field."""
        new_field = copy.copy(self)
        if self._pipe is None:
            new_field._pipe = Pipe(other) if not isinstance(other, Pipe) else other
        else:
            new_field._pipe = self._pipe | other
        return new_field

    def _query(self, doc):
        """Execute a CSS or XPath selector on *doc*, returning a list of elements.

        The selector type is detected once and cached. XPath expressions may
        start with ``//``, ``.//``, ``..``, or the explicit ``xpath:`` prefix.
        """
        if self._is_xpath is None:
            sel = getattr(self, "selector", "")
            # Detect XPath: starts with /, ./, .., or has xpath: prefix
            self._is_xpath = isinstance(sel, str) and (
                sel.startswith("/")
                or sel.startswith(".//")
                or sel.startswith("..")
                or sel.startswith("xpath:")
            )

        if self._is_xpath:
            sel = getattr(self, "selector", "")
            if sel.startswith("xpath:"):
                sel = sel[6:]
            return doc.xpath(sel)
        else:
            if self._cached_selector is None:
                self._cached_selector = CSSSelector(self.selector)
            return self._cached_selector(doc)
