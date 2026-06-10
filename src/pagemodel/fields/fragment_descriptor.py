from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from lxml.cssselect import CSSSelector

from ..log import logger

if TYPE_CHECKING:
    from ..page import HtmlFragment


def _to_snake_case(name: str) -> str:
    """Convert a CamelCase name to snake_case for use as a default export name."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


class FragmentDescriptor:
    """Descriptor for ``@fragment`` decorated classes. Caches the extracted
    fragment(s) on the page instance.

    Parameters
    ----------
    selector : str
        CSS selector (relative to the page document) that matches the elements
        to be wrapped.
    fragment_cls : type[HtmlFragment]
        The fragment class (a subclass of ``HtmlFragment``) to instantiate for
        each matched element.
    multiple : bool, optional
        If ``True``, return a list of fragments (one per matched element).
        Otherwise return a single fragment or ``default``.
    default : any, optional
        Value returned when no elements are matched (only relevant when
        ``multiple=False``).
    name : str or None, optional
        Explicit name to use in ``export()`` output. If ``None``, the export
        name is derived from the class attribute name by converting it to
        snake_case.
    """

    def __init__(
        self,
        selector: str,
        fragment_cls: type[HtmlFragment],
        multiple: bool = False,
        default: Any = None,
        name: str | None = None,
    ) -> None:
        self.selector = selector
        self._fragment_cls = fragment_cls
        self.multiple = multiple
        self.default = default
        self._name = name
        self._attr_name: str | None = None
        self._cached_selector = None

    @property
    def fragment_cls(self) -> type[HtmlFragment]:
        """The fragment class used to wrap matched elements."""
        return self._fragment_cls

    def __set_name__(self, owner: type, name: str) -> None:
        self._attr_name = name
        if not hasattr(owner, "_pagemodel_export"):
            owner._pagemodel_export = []
        export_name = self._name if self._name is not None else _to_snake_case(name)
        owner._pagemodel_export.append((name, export_name))

    def __get__(self, instance: Any, owner: type) -> Any:
        """Extract fragment(s) on first access and cache the result in the
        instance dictionary."""
        if instance is None:
            return self
        cache = instance.__dict__
        if self._attr_name not in cache:
            if self._cached_selector is None:
                self._cached_selector = CSSSelector(self.selector)
            sel = self._cached_selector
            elms = sel(instance.doc)
            if self.multiple:
                value = [self.fragment_cls(elm) for elm in elms]
                logger.debug("Created %d fragments for: %s", len(value), self._attr_name)
            else:
                if elms:
                    value = self.fragment_cls(elms[0])
                else:
                    value = self.default
            cache[self._attr_name] = value
        else:
            logger.debug("Cache hit for fragment descriptor: %s", self._attr_name)
        return cache[self._attr_name]


def fragment(
    selector: str,
    *,
    multiple: bool = False,
    default: Any = None,
    name: str | None = None,
) -> Callable[[type], FragmentDescriptor]:
    """Class decorator that turns a plain class into an ``HtmlFragment`` and
    returns a ``FragmentDescriptor`` for use on a ``BasePage``.

    Usage::

        class Page(BasePage):
            @fragment(".product", multiple=True)
            class Product:
                name: str = ".name"
                price: float = ".price @data-value"

    Parameters
    ----------
    selector : str
        CSS selector (relative to the page document) that matches the elements
        to be wrapped.
    multiple : bool, optional
        If ``True``, the descriptor will return a list of fragments (one per
        matched element). Otherwise it returns a single fragment or ``default``.
    default : any, optional
        Value returned when no elements are matched (only relevant when
        ``multiple=False``).
    name : str or None, optional
        Explicit name to use in ``export()`` output. If ``None``, the export
        name is derived from the class attribute name by converting it to
        snake_case.
    """

    def decorator(cls: type) -> FragmentDescriptor:
        from ..page import HtmlFragment as _HtmlFragment

        if not issubclass(cls, _HtmlFragment):
            new_cls_dict = {**cls.__dict__}
            if hasattr(cls, "__annotations__"):
                new_cls_dict["__annotations__"] = cls.__annotations__.copy()
            cls = type(cls.__name__, (cls, _HtmlFragment), new_cls_dict)
        return FragmentDescriptor(selector, cls, multiple=multiple, default=default, name=name)

    return decorator
