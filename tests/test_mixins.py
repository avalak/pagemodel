"""
Tests for pagemodel mixins used independently of BasePage/BaseFragment.
"""

import pytest
from lxml.cssselect import CSSSelector

from pagemodel.mixins import CacheMixin, CSSMixin, ExportMixin, PydanticMixin


class BarePage(ExportMixin, CacheMixin, PydanticMixin, CSSMixin):
    _cache_extra_keys = ["source", "doc"]

    def __init__(self):
        self._pagemodel_export = [("title", "title")]
        self.title = "Hello"
        self._css_cache = {}

    def doc(self):
        pass  # not needed for these tests


class TestExportMixin:
    def test_export(self):
        page = BarePage()
        assert page.export() == {"title": "Hello"}


class TestCacheMixin:
    def test_clear_cache_removes_fields(self):
        page = BarePage()
        assert page.title == "Hello"
        page.clear_cache()
        with pytest.raises(AttributeError):
            _ = page.title


class TestCSSMixin:
    def test_css_compiles_and_caches_selector(self):

        page = BarePage()
        sel = page.css("h1")
        assert isinstance(sel, CSSSelector)
        # Check caching
        assert page.css("h1") is sel
