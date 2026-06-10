"""
Tests for XPath support: X helper (XpathField), auto-detection in old fields,
annotations, and low-level utilities.
"""

import pytest
from lxml import etree
from lxml import html as lxml_html

from pagemodel import (
    BasePage,
    Field,
    HtmlFragment,
    Q,
    X,
    XpathField,
    get_attr,
    get_elm,
    get_text,
    is_elm_exists,
)

XML_NS = """<root xmlns:ns="http://example.com/ns">
    <ns:title>Namespaced Title</ns:title>
    <ns:item price="10">First</ns:item>
    <ns:item price="20">Second</ns:item>
</root>
"""

HTML = """
<html><body>
    <h1>Hello</h1>
    <div class="price" data-value="9.99" data-currency="USD">9.99 USD</div>
    <ul>
        <li class="item"><span class="name">A</span></li>
        <li class="item"><span class="name">B</span></li>
    </ul>
    <script type="application/json">{"key": "value"}</script>
</body></html>
"""


class TestXHelper:
    """X creates XpathField – use /text() or @attr for strings."""

    def test_x_text(self):
        class Page(BasePage):
            heading = X("//h1/text()")

        page = Page(HTML)
        assert page.heading == "Hello"

    def test_x_attribute(self):
        class Page(BasePage):
            price = X("//div[@class='price']/@data-value") | float

        page = Page(HTML)
        assert page.price == 9.99

    def test_x_with_pipe(self):
        class Page(BasePage):
            heading = X("//h1/text()") | str.upper

        page = Page(HTML)
        assert page.heading == "HELLO"

    def test_x_with_default(self):
        class Page(BasePage):
            missing = (X("//h2/text()"), "Default")

        page = Page(HTML)
        assert page.missing == "Default"


class TestXpathField:
    """Explicit XpathField usage."""

    def test_extract_text(self):
        class Page(BasePage):
            heading = XpathField("//h1/text()")

        page = Page(HTML)
        assert page.heading == "Hello"

    def test_extract_attribute(self):
        class Page(BasePage):
            price = XpathField("//div[@class='price']/@data-value")

        page = Page(HTML)
        assert page.price == "9.99"

    def test_with_default(self):
        class Page(BasePage):
            missing = XpathField("//h2/text()", default="No heading")

        page = Page(HTML)
        assert page.missing == "No heading"

    def test_index_none_returns_list(self):
        class Page(BasePage):
            items = XpathField("//li[@class='item']/span/text()", index=None)

        page = Page(HTML)
        assert page.items == ["A", "B"]

    def test_with_converter(self):
        class Page(BasePage):
            price = XpathField("//div[@class='price']/@data-value") | float

        page = Page(HTML)
        assert page.price == 9.99

    def test_xpath_field_namespaces(self):

        doc = etree.fromstring(XML_NS)
        field = XpathField(
            "//ns:title/text()", namespaces={"ns": "http://example.com/ns"}
        )
        page = BasePage(doc)
        value = field.__get__(page, type(page))
        assert value == "Namespaced Title"


class TestOldFieldsXPath:
    """Old fields auto-detect XPath and work as before."""

    def test_textfield_xpath(self):
        class Page(BasePage):
            heading = Field("//h1")

        page = Page(HTML)
        assert page.heading == "Hello"

    def test_attrfield_xpath(self):
        class Page(BasePage):
            price = Field("//div[@class='price']", attr="data-value")

        page = Page(HTML)
        assert page.price == "9.99"

    def test_listfield_xpath(self):
        class Item(HtmlFragment):
            name = Field(".//span[@class='name']")

        class Page(BasePage):
            items = Field("//li[@class='item']", fragment=Item, multiple=True)

        page = Page(HTML)
        assert len(page.items) == 2
        assert page.items[0].name == "A"
        assert page.items[1].name == "B"

    def test_elementfield_xpath(self):
        class Item(HtmlFragment):
            name = Field(".//span[@class='name']")

        class Page(BasePage):
            first_item = Field("//li[@class='item']", fragment=Item, index=0)

        page = Page(HTML)
        assert page.first_item.name == "A"

    def test_jsonfield_xpath(self):
        class Page(BasePage):
            data = Field("//script[@type='application/json']", json=True)

        page = Page(HTML)
        assert page.data == {"key": "value"}


class TestQWithXPath:
    """Q helper auto-detects XPath."""

    def test_q_auto_xpath(self):
        class Page(BasePage):
            heading = Q("//h1")

        page = Page(HTML)
        assert page.heading == "Hello"

    def test_q_xpath_prefix(self):
        class Page(BasePage):
            heading = Q("xpath://h1")

        page = Page(HTML)
        assert page.heading == "Hello"

    def test_q_with_pipe_xpath(self):
        class Page(BasePage):
            heading = Q("//h1") | str.upper

        page = Page(HTML)
        assert page.heading == "HELLO"


class TestAnnotationXPath:
    """Annotations with XPath strings auto-create XpathField."""

    def test_string_annotation(self):
        class Page(BasePage):
            heading: str = "//h1/text()"

        page = Page(HTML)
        assert page.heading == "Hello"

    def test_tuple_annotation(self):
        class Page(BasePage):
            heading: str = ("//h2/text()", "None")

        page = Page(HTML)
        assert page.heading == "None"


class TestUtilitiesXPath:
    def test_get_text(self):
        doc = lxml_html.fromstring(HTML)
        assert get_text(doc, "//h1") == "Hello"

    def test_get_attr(self):
        doc = lxml_html.fromstring(HTML)
        assert get_attr(doc, "//div[@class='price']", "data-value") == "9.99"

    def test_get_elm(self):
        doc = lxml_html.fromstring(HTML)
        elm = get_elm(doc, "//h1")
        assert elm is not None and elm.tag == "h1"

    def test_is_elm_exists(self):
        doc = lxml_html.fromstring(HTML)
        assert is_elm_exists(doc, "//h1") is True
        assert is_elm_exists(doc, "//h2") is False


class TestXPathWithNamespaces:
    def test_textfield(self):
        doc = etree.fromstring(XML_NS)
        ns = {"ns": "http://example.com/ns"}
        assert get_text(doc, "//ns:title", namespaces=ns) == "Namespaced Title"

    def test_attr(self):
        doc = etree.fromstring(XML_NS)
        ns = {"ns": "http://example.com/ns"}
        assert get_attr(doc, "//ns:item", "price", namespaces=ns) == "10"


class TestBackwardCompatibility:
    def test_css_still_works(self):
        class Page(BasePage):
            heading = Field("h1")

        page = Page(HTML)
        assert page.heading == "Hello"

    def test_q_css_still_works(self):
        class Page(BasePage):
            heading = Q("h1")

        page = Page(HTML)
        assert page.heading == "Hello"
