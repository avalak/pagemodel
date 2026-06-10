"""
Tests for Pydantic integration with pagemodel 2.0.
"""

import pytest
from lxml import html as lxml_html

from pagemodel import BasePage, Field, HtmlFragment

try:
    from pydantic import BaseModel as PydanticBaseModel

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

pytestmark = pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="pydantic not installed")

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


class TestPydanticIntegration:
    def test_to_model_explicit(self):
        class SimpleModel(PydanticBaseModel):
            title: str

        class Page(BasePage):
            title: str = "h1"

        page = Page(SIMPLE_HTML)
        result = page.to_model(SimpleModel)
        assert isinstance(result, SimpleModel)
        assert result.title == "Hello"

    def test_to_model_class_attr(self):
        class SimpleModel(PydanticBaseModel):
            heading: str

        class Page(BasePage):
            __pydantic_model__ = SimpleModel
            heading = Field("h1")

        page = Page(SIMPLE_HTML)
        result = page.to_model()
        assert result.heading == "Hello"

    def test_fragment_to_model(self):
        class ProductModel(PydanticBaseModel):
            name: str
            price: str

        class Product(HtmlFragment):
            __pydantic_model__ = ProductModel
            name = Field(".name")
            price = Field(".price", attr="data-value")

        frag = Product(lxml_html.fromstring(CATALOG_HTML).cssselect(".product")[0])
        prod = frag.to_model()
        assert prod.name == "Pen"
        assert prod.price == "1.5"

    def test_json_field_with_model_annotation(self):
        """Annotation with Pydantic model auto-creates Field(json=True, model=...)."""

        class ProductModel(PydanticBaseModel):
            name: str
            price: float

        html_data = '<script type="ld+json">{"name": "Pen", "price": 1.5}</script>'

        class Page(BasePage):
            product: ProductModel = "script[type='ld+json']"

        page = Page(html_data)
        assert isinstance(page.product, ProductModel)
        assert page.product.name == "Pen"
        assert page.product.price == 1.5

    def test_json_field_with_default(self):
        class Simple(PydanticBaseModel):
            x: int

        html_data = "<div></div>"

        class Page(BasePage):
            data: Simple = (".missing", None)

        page = Page(html_data)
        assert page.data is None

    def test_non_pydantic_class(self):
        class NotAModel:
            pass

        html_data = "<div class='x'>hello</div>"

        class Page(BasePage):
            x: NotAModel = ".x"

        page = Page(html_data)
        assert isinstance(page.x, str)
        assert page.x == "hello"
