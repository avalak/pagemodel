"""
Page and fragment base classes.

- ``BasePage`` represents an entire HTML/XML document.
- ``BaseFragment`` / ``HtmlFragment`` represent a subtree within a document.
- ``StreamPage`` provides iterative XML processing without loading the whole tree.
"""

from __future__ import annotations

import copy
import io
from collections.abc import Iterator
from functools import cached_property
from typing import Any

from lxml import etree, html
from lxml.etree import tounicode

from .adapters import _process_annotations
from .log import logger
from .mixins import CacheMixin, CSSMixin, ExportMixin, PydanticMixin

__all__ = (
    "BaseFragment",
    "BasePage",
    "HtmlFragment",
)


class BasePage(ExportMixin, CacheMixin, PydanticMixin, CSSMixin):
    """Main entry point for extracting data from an HTML/XML document.

    Accepts a string, bytes, or pre‑parsed ``lxml.html.HtmlElement``.
    Fields declared on the class are automatically resolved via
    ``_process_annotations``.

    Parameters
    ----------
    source : str, bytes, or HtmlElement
        The HTML/XML content.
    url : str, optional
        Base URL used to resolve relative links.
    encoding : str, optional
        Encoding used when *source* is bytes. Default ``"utf-8"``.
    """

    _cache_extra_keys = ["source", "doc"]

    def __init__(
        self,
        source: str | bytes | html.HtmlElement | etree._Element,
        url: str | None = None,
        encoding: str = "utf-8",
    ) -> None:
        if isinstance(source, etree._Element):
            logger.debug("BasePage created with pre-parsed element")
            self._source = None
            self._doc = source
        else:
            logger.debug("BasePage created from source string/bytes")
            self._source = source
            self._doc = None
        self._encoding = encoding
        self._url = url

    @cached_property
    def source(self) -> str:
        """The original HTML/XML source as a string."""
        if self._source is None:
            return tounicode(self._doc)
        if isinstance(self._source, (bytes, bytearray, memoryview)):
            return bytes(self._source).decode(self._encoding)
        return self._source

    @cached_property
    def doc(self) -> html.HtmlElement:
        """The parsed lxml document tree."""
        if self._doc is not None:
            logger.debug("Using pre-parsed doc")
            return self._doc
        logger.debug("Parsing HTML to doc")
        doc = html.fromstring(
            self.source,
            base_url=self._url,
            parser=html.HTMLParser(encoding=self._encoding),
        )
        if self._url is not None:
            logger.debug("Making links absolute with base URL: %s", self._url)
            doc.make_links_absolute(self._url)
        return doc

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        _process_annotations(cls)


class BaseFragment(ExportMixin, CacheMixin, PydanticMixin, CSSMixin):
    """Represents a subtree of a document.

    Parameters
    ----------
    elm : HtmlElement
        The root element of the fragment.
    _copy : bool
        If ``True``, a deep copy of *elm* is made before use.
    """

    _cache_extra_keys = ["source"]

    def __init__(self, elm: html.HtmlElement, _copy: bool = False) -> None:
        self.doc = copy.deepcopy(elm) if _copy else elm

    @cached_property
    def source(self) -> str:
        """The serialised XML of this fragment's subtree."""
        return tounicode(self.doc)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        _process_annotations(cls)


class HtmlFragment(BaseFragment):
    """Alias for ``BaseFragment`` – kept for backward compatibility."""

    pass


class StreamPage:
    """Iterative XML processor that yields exported dictionaries.

    Useful for large XML files where building a full DOM is expensive.

    Parameters
    ----------
    source : str or bytes
        The XML content.
    encoding : str, optional
        Encoding used when *source* is bytes. Default ``"utf-8"``.
    tag_callback_map : dict, optional
        Mapping of XML tag names to fragment classes. Each time a matching
        element is parsed, the fragment is instantiated and exported.
    """

    def __init__(
        self,
        source: str | bytes,
        encoding: str = "utf-8",
        tag_callback_map: dict[str, type[BaseFragment]] | None = None,
    ) -> None:
        self.source_str = source if isinstance(source, str) else bytes(source).decode(encoding)
        self.tag_callback_map = tag_callback_map or {}

    def iter_items(self, tag: str) -> Iterator[dict[str, Any]]:
        """Yield exported dictionaries for each occurrence of *tag*."""
        fragment_cls = self.tag_callback_map.get(tag)
        if fragment_cls is None:
            raise ValueError(f"No fragment class registered for tag '{tag}'")
        events = etree.iterparse(io.BytesIO(self.source_str.encode()), events=("end",), tag=tag)
        for _, elem in events:
            html_elem = html.fragment_fromstring(etree.tounicode(elem))
            frag = fragment_cls(html_elem)
            yield frag.export()
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
