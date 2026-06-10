"""
Unified Field descriptor for pagemodel 0.2.0.

Provides a single ``Field`` class that replaces all previous specialised
descriptors (TextField, AttrField, JsonField, ListField, ElementField,
FragmentField). It automatically detects CSS vs XPath selectors, pre-compiles
them, and generates a branch‑free extractor for maximum speed.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from lxml import etree
from lxml.cssselect import CSSSelector

from ..pipeline import Pipe
from .base import BaseField

if TYPE_CHECKING:
    from ..page import BaseFragment

try:
    import orjson as json
except ImportError:
    import json  # type: ignore[no-redef]


def _parse_json(raw: str) -> Any:
    """Parse a JSON string using orjson if available, otherwise stdlib json."""
    return json.loads(raw)


class Field(BaseField):
    """Universal field descriptor.

    Automatically detects CSS vs XPath selectors, pre‑compiles them,
    and generates a branch‑free extractor for maximum speed.

    Parameters
    ----------
    selector : str
        CSS selector, XPath expression (``//h1``), or ``xpath://h1``.
    attr : str, optional
        If set, extract an attribute instead of text.
    json : bool, optional
        If True, parse text/attribute content as JSON.
    model : type, optional
        Pydantic model class to validate JSON data (only used with ``json=True``).
    multiple : bool, optional
        If True, return a list of values (text/attr/JSON) instead of a single one.
    fragment : type[BaseFragment], optional
        If set, wrap each selected element into the given fragment class.
    index : int or None, optional
        Index of the element to pick (0-based). ``None`` returns all matched elements
        (as a list of fragments if ``fragment`` is set, otherwise list of strings).
        Ignored when ``multiple=True``.
    default : any, optional
        Value returned when the selector matches nothing or index is out of range.
    namespaces : dict, optional
        Namespace prefix-to-URI mapping for XPath expressions.
    converter : callable, Pipe, or None
        Applied to the extracted value (or each value when ``multiple=True``).
    is_exported : bool, optional
        Whether to include this field in ``export()``. Default True.
    """

    def __init__(
        self,
        selector: str,
        *,
        attr: str | None = None,
        json: bool = False,
        model: type | None = None,
        multiple: bool = False,
        fragment: type[BaseFragment] | None = None,
        index: int | None = 0,
        default: Any = None,
        namespaces: dict[str, str] | None = None,
        converter: Pipe | list[Callable] | Callable | None = None,
        is_exported: bool = True,
    ) -> None:
        super().__init__(converter, is_exported)
        self.selector = selector
        self._attr = attr
        self._json = json
        self._model = model
        self._multiple = multiple
        self._fragment_cls = fragment
        self._index = index
        self._default = default
        self._namespaces = namespaces
        self._build_extractor()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _is_xpath_sel(sel: str) -> bool:
        return (
            sel.startswith("/")
            or sel.startswith(".//")
            or sel.startswith("..")
            or sel.startswith("xpath:")
        )

    # ------------------------------------------------------------------
    # Extractor builders
    # ------------------------------------------------------------------
    def _make_query(self, sel: str, is_xpath: bool):
        """Create the `query(doc)` closure that executes the selector.

        For CSS selectors, a ``CSSSelector`` object is compiled once and reused.
        For XPath expressions, an ``etree.XPath`` object is compiled once,
        including any namespace mappings.
        """
        if is_xpath:
            xpath_obj = (
                etree.XPath(sel, namespaces=self._namespaces)
                if self._namespaces
                else etree.XPath(sel)
            )

            def query(doc):
                return xpath_obj(doc)

        else:
            css = CSSSelector(sel)

            def query(doc):
                return css(doc)

        return query

    def _build_fragment_extractor(self, query):
        """Return an extractor that wraps matched elements into fragment instances.

        Used when ``fragment`` is set. Depending on ``multiple`` or ``index``,
        returns either a list of fragments or a single fragment.
        """
        if self._multiple or self._index is None:

            def extract(doc):
                elms = query(doc)
                return [self._fragment_cls(elm) for elm in elms]

        else:

            def extract(doc):
                elms = query(doc)
                try:
                    return self._fragment_cls(elms[self._index])
                except IndexError:
                    return self._default

        return extract

    def _build_json_extractor(self, query, raw_xpath: bool):
        """Return an extractor that parses matched text/attribute content as JSON.

        When ``json=True``, this builder is selected. It handles both single
        and multiple values, and optionally validates with a Pydantic model.
        The ``raw_xpath`` flag indicates whether XPath results are atomic
        (strings) rather than elements, so ``.text_content()`` is not called.
        """
        if self._multiple or self._index is None:

            def extract(doc):
                elms = query(doc)
                results = []
                for elm in elms:
                    raw = (
                        elm.get(self._attr)
                        if self._attr
                        else (elm if raw_xpath else elm.text_content())
                    )
                    if raw is None:
                        results.append(self._default)
                    else:
                        try:
                            value = _parse_json(raw)
                            if self._model is not None:
                                value = self._validate_model(value)
                            results.append(value)
                        except Exception:
                            results.append(self._default)
                return results

        else:

            def extract(doc):
                elms = query(doc)
                try:
                    elm = elms[self._index]
                except IndexError:
                    return self._default
                raw = (
                    elm.get(self._attr)
                    if self._attr
                    else (elm if raw_xpath else elm.text_content())
                )
                if raw is None:
                    return self._default
                try:
                    value = _parse_json(raw)
                    if self._model is not None:
                        value = self._validate_model(value)
                    return value
                except Exception:
                    return self._default

        return extract

    def _build_raw_xpath_extractor(self, query):
        """Return an extractor for XPath expressions that return atomic values.

        Such expressions end with ``/text()`` or ``/@attr``. The results are
        already strings, so no ``.text_content()`` or ``.get()`` is needed.
        """
        if self._multiple or self._index is None:

            def extract(doc):
                return query(doc)  # already list of strings

        else:

            def extract(doc):
                elms = query(doc)
                try:
                    return elms[self._index]
                except IndexError:
                    return self._default

        return extract

    def _build_plain_extractor(self, query):
        """Return an extractor for standard text or attribute extraction.

        Handles both single values and lists, with optional attribute
        extraction controlled by ``self._attr``.
        """
        if self._multiple or self._index is None:
            if self._attr:

                def extract(doc):
                    elms = query(doc)
                    return [elm.get(self._attr, self._default) for elm in elms]

            else:

                def extract(doc):
                    elms = query(doc)
                    return [elm.text_content() for elm in elms]

        else:
            if self._attr:

                def extract(doc):
                    elms = query(doc)
                    try:
                        return elms[self._index].get(self._attr, self._default)
                    except IndexError:
                        return self._default

            else:

                def extract(doc):
                    elms = query(doc)
                    try:
                        return elms[self._index].text_content()
                    except IndexError:
                        return self._default

        return extract

    # ------------------------------------------------------------------
    # Main build dispatcher
    # ------------------------------------------------------------------
    def _build_extractor(self) -> None:
        """Select and build the appropriate extractor based on field flags."""
        sel = self.selector
        is_xpath = self._is_xpath_sel(sel)
        if is_xpath and sel.startswith("xpath:"):
            sel = sel[6:]

        query = self._make_query(sel, is_xpath)
        raw_xpath = is_xpath and ("text()" in sel or "/@" in sel)

        if self._fragment_cls is not None:
            self._extractor = self._build_fragment_extractor(query)
        elif self._json:
            self._extractor = self._build_json_extractor(query, raw_xpath)
        elif raw_xpath:
            self._extractor = self._build_raw_xpath_extractor(query)
        else:
            self._extractor = self._build_plain_extractor(query)

    def _validate_model(self, value: Any) -> Any:
        """Validate and return a Pydantic model instance (if a model is set)."""
        if self._model is None:
            return value
        try:
            from pydantic import BaseModel

            if hasattr(BaseModel, "model_validate"):
                return self._model.model_validate(value)
            else:
                return self._model.parse_obj(value)
        except ImportError:
            raise ImportError("pydantic is required for model validation") from None
        except Exception:
            return self._default

    def _get(self, instance: Any, owner: type) -> Any:
        return self._extractor(instance.doc)
