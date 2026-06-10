"""
Tests for @fragment decorator.
"""

import pytest
from lxml import html as lxml_html

from pagemodel import BasePage, Field, HtmlFragment, fragment

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


class TestFragmentDecorator:
    def test_single(self):
        class Page(BasePage):
            @fragment(".product")
            class Product:
                name: str = ".name"

        page = Page(CATALOG_HTML)
        prod = page.Product
        assert isinstance(prod, HtmlFragment)
        assert prod.name == "Pen"

    def test_multiple(self):
        class Page(BasePage):
            @fragment(".product", multiple=True)
            class Product:
                name: str = ".name"

        page = Page(CATALOG_HTML)
        prods = page.Product
        assert len(prods) == 2
        assert prods[0].name == "Pen"
        data = page.export()
        assert "product" in data
        assert len(data["product"]) == 2

    def test_default(self):
        class Page(BasePage):
            @fragment(".nonexistent", default=None)
            class Widget:
                title: str = "h3"

        page = Page(CATALOG_HTML)
        assert page.Widget is None

    def test_export(self):
        class Page(BasePage):
            @fragment(".product")
            class Product:
                name: str = ".name"

        page = Page(CATALOG_HTML)
        data = page.export()
        assert data["product"]["name"] == "Pen"

    def test_explicit_name(self):
        class Page(BasePage):
            @fragment(".product", name="item")
            class Product:
                name: str = ".name"

        page = Page(CATALOG_HTML)
        data = page.export()
        assert "item" in data
        assert data["item"]["name"] == "Pen"
        assert page.Product.name == "Pen"
