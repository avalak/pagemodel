"""
Tests for BasePage, caching, export, and StreamPage.
"""

import pytest
from lxml import html as lxml_html

from pagemodel import BaseFragment, BasePage, Field, export
from pagemodel.page import StreamPage

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


class TestBasePage:
    def test_source_str(self):
        page = BasePage("<p>text</p>")
        assert page.source == "<p>text</p>"

    def test_source_bytes(self):
        page = BasePage(b"<p>text</p>")
        assert page.source == "<p>text</p>"

    def test_doc(self):
        page = BasePage(SIMPLE_HTML)
        assert page.doc.tag == "html"

    def test_export_simple(self):
        class SimplePage(BasePage):
            title = Field("h1")

        page = SimplePage(SIMPLE_HTML)
        data = page.export()
        assert data == {"title": "Hello"}

    def test_export_deep(self):
        class ProductFragment(BaseFragment):
            name = Field(".name")
            price = Field(".price", attr="data-value")

        class CatalogPage(BasePage):
            title = Field("h1")
            products = Field(".product", fragment=ProductFragment, multiple=True)

        page = CatalogPage(CATALOG_HTML)
        data = page.export()
        assert data["title"] == "Catalog"
        assert len(data["products"]) == 2
        assert data["products"][0] == {"name": "Pen", "price": "1.5"}

    def test_export_shallow(self):
        class ProductPage(BasePage):
            name = Field(".name")

        page = ProductPage(CATALOG_HTML)
        data = page.export(deep=False)
        assert isinstance(data["name"], str)

    def test_url_makes_links_absolute(self):
        html = '<a href="/relative">link</a>'
        page = BasePage(html, url="http://example.com")
        link = page.doc.cssselect("a")[0].get("href")
        assert link == "http://example.com/relative"


class TestExportRecursion:
    def test_nested_fragments_export(self):
        class Address(BaseFragment):
            city = Field(".city")

        class User(BaseFragment):
            name = Field(".name")
            address = Field(".address", fragment=Address, index=0)

        html_user = """
        <div class="user">
            <span class="name">Alice</span>
            <div class="address">
                <span class="city">Moscow</span>
            </div>
        </div>
        """

        class UserPage(BasePage):
            user = Field(".user", fragment=User, index=0)

        page = UserPage(html_user)
        data = page.export()
        assert data["user"]["name"] == "Alice"
        assert data["user"]["address"]["city"] == "Moscow"


class TestExportDecorator:
    def test_export_method(self):
        class Page(BasePage):
            @export
            def title(self):
                return "Computed"

        page = Page("<html></html>")
        assert page.title == "Computed"
        assert "title" in page.export()

    def test_export_custom_name(self):
        class Page(BasePage):
            @export("heading")
            def title(self):
                return "Custom"

        page = Page("<html></html>")
        data = page.export()
        assert "heading" in data
        assert data["heading"] == "Custom"
        assert "title" not in data


class TestCaching:
    def test_cached_value(self):
        class Page(BasePage):
            heading = Field("h1")

        page = Page(SIMPLE_HTML)
        first = page.heading
        second = page.heading
        assert first == second

    def test_clear_cache(self):
        class Page(BasePage):
            heading = Field("h1")

        page = Page(SIMPLE_HTML)
        _ = page.heading
        page.clear_cache()
        assert page.heading == "Hello"

    def test_cache_instance_isolation(self):
        class Page(BasePage):
            heading = Field("h1")

        page1 = Page("<h1>First</h1>")
        page2 = Page("<h1>Second</h1>")
        assert page1.heading == "First"
        assert page2.heading == "Second"


class TestStreamPage:
    def test_iter_items_basic(self):

        class ItemFragment(BaseFragment):
            name = Field("name")

        xml_source = """<root><item><name>First</name></item><item><name>Second</name></item></root>"""
        stream = StreamPage(xml_source, tag_callback_map={"item": ItemFragment})
        results = list(stream.iter_items("item"))
        assert len(results) == 2
        assert results[0] == {"name": "First"}
        assert results[1] == {"name": "Second"}


class TestEdgeCases:
    def test_empty_selector(self):
        class Page(BasePage):
            nothing = Field(".nothing")

        page = Page(SIMPLE_HTML)
        assert page.nothing is None

    def test_attr_with_default(self):
        class Page(BasePage):
            currency = Field(".price", attr="data-currency", default="USD")

        page = Page(CATALOG_HTML)
        assert page.currency == "USD"

    def test_deep_export_with_none(self):
        class Product(BaseFragment):
            name = Field(".name")

        class Page(BasePage):
            single = Field(".nonexistent", fragment=Product, index=0)

        page = Page(CATALOG_HTML)
        data = page.export()
        assert data["single"] is None
