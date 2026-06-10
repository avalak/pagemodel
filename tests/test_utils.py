"""
Tests for pagemodel utility functions.
"""

import pytest
from lxml import html as lxml_html

from pagemodel import get_attr, get_elm, get_text, get_text_content, is_elm_exists

SIMPLE_HTML = "<html><body><h1>Hello</h1></body></html>"
CATALOG_HTML = """
<html><body>
    <h1>Catalog</h1>
    <div class="product">
        <span class="name">Pen</span>
        <span class="price" data-value="1.5"></span>
        <a href="/product/pen">link</a>
    </div>
    <div class="product">
        <span class="name">Paper</span>
        <span class="price" data-value="2.0"></span>
        <a href="/product/paper">link</a>
    </div>
</body></html>
"""


class TestUtils:
    def test_get_elm(self):
        doc = lxml_html.fromstring(SIMPLE_HTML)
        elm = get_elm(doc, "h1")
        assert elm is not None
        assert elm.tag == "h1"

    def test_get_elm_missing(self):
        doc = lxml_html.fromstring(SIMPLE_HTML)
        assert get_elm(doc, "h2") is None

    def test_get_text(self):
        doc = lxml_html.fromstring(CATALOG_HTML)
        assert get_text(doc, "h1") == "Catalog"

    def test_get_text_missing(self):
        doc = lxml_html.fromstring(CATALOG_HTML)
        assert get_text(doc, "h2") is None

    def test_get_text_with_default(self):
        doc = lxml_html.fromstring(CATALOG_HTML)
        assert get_text(doc, "h2", default="Missing") == "Missing"

    def test_get_attr(self):
        doc = lxml_html.fromstring(CATALOG_HTML)
        assert get_attr(doc, ".price", "data-value") == "1.5"

    def test_get_attr_missing(self):
        doc = lxml_html.fromstring(CATALOG_HTML)
        assert get_attr(doc, ".price", "data-currency") is None

    def test_is_elm_exists(self):
        doc = lxml_html.fromstring(CATALOG_HTML)
        assert is_elm_exists(doc, "h1") is True
        assert is_elm_exists(doc, "h2") is False

    def test_get_text_content_br(self):
        html_br = "<div>line1<br>line2<br>line3</div>"
        doc = lxml_html.fromstring(html_br)
        elm = doc.cssselect("div")[0]
        text = get_text_content(elm)
        assert text == "line1\nline2\nline3"
