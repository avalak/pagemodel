"""
Tests for the unified Field descriptor in pagemodel 2.0.
"""

import pytest
from lxml import html as lxml_html

from pagemodel import BaseFragment, BasePage, Field

try:
    from pydantic import BaseModel

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

pydantic_mark = pytest.mark.skipif(
    not PYDANTIC_AVAILABLE, reason="pydantic not installed"
)

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


class TestFieldText:
    def test_basic(self):
        class Page(BasePage):
            heading = Field("h1")

        page = Page(SIMPLE_HTML)
        assert page.heading == "Hello"

    def test_index(self):
        class Page(BasePage):
            first = Field(".name", index=0)
            second = Field(".name", index=1)

        page = Page(CATALOG_HTML)
        assert page.first == "Pen"
        assert page.second == "Paper"

    def test_default(self):
        class Page(BasePage):
            missing = Field(".nonexistent", default="N/A")

        page = Page(CATALOG_HTML)
        assert page.missing == "N/A"

    def test_multiple(self):
        class Page(BasePage):
            names = Field(".name", multiple=True)

        page = Page(CATALOG_HTML)
        assert page.names == ["Pen", "Paper"]

    def test_multiple_missing(self):
        class Page(BasePage):
            missing = Field(".nonexistent", multiple=True)

        page = Page(CATALOG_HTML)
        assert page.missing == []

    def test_index_none_returns_list(self):
        class Page(BasePage):
            names = Field(".name", index=None)

        page = Page(CATALOG_HTML)
        assert page.names == ["Pen", "Paper"]

    def test_bare_string_field_works(self):
        """Field declared as a bare string without type annotation should extract text."""

        class Page(BasePage):
            heading = "h1"

        page = Page("<h1>Hello</h1>")
        assert page.heading == "Hello"

    def test_bare_string_field_with_attr_works(self):

        class Page(BasePage):
            price = ".price @data-value"

        page = Page('<div class="price" data-value="9.99"></div>')
        assert page.price == "9.99"


class TestFieldAttr:
    def test_attr(self):
        class Page(BasePage):
            price = Field(".price", attr="data-value")

        page = Page(CATALOG_HTML)
        assert page.price == "1.5"

    def test_attr_default(self):
        class Page(BasePage):
            currency = Field(".price", attr="data-currency", default="USD")

        page = Page(CATALOG_HTML)
        assert page.currency == "USD"

    def test_attr_multiple(self):
        class Page(BasePage):
            values = Field(".price", attr="data-value", multiple=True)

        page = Page(CATALOG_HTML)
        assert page.values == ["1.5", "2.0"]

    def test_attr_index_none(self):
        class Page(BasePage):
            values = Field(".price", attr="data-value", index=None)

        page = Page(CATALOG_HTML)
        assert page.values == ["1.5", "2.0"]

    def test_annotation_with_attr(self):
        class Page(BasePage):
            link: str = "a.link @href"

        page = Page("<a class='link' href='/product/1'>link</a>")
        assert page.link == "/product/1"

    def test_annotation_with_attr_and_converter(self):
        class Page(BasePage):
            price: float = ".price @data-value"

        page = Page('<div class="price" data-value="9.99"></div>')
        assert page.price == 9.99

    def test_annotation_json_with_attr(self):
        class Page(BasePage):
            config: dict = ".widget @data-config"

        page = Page('<div class="widget" data-config=\'{"theme":"dark"}\'></div>')
        assert page.config == {"theme": "dark"}


class TestFieldJson:
    JSON_HTML = '<div class="data">{"key": "value"}</div>'
    JSON_ATTR_HTML = '<div class="data" info=\'{"x": 1}\'></div>'
    JSON_ARRAY = '<div class="data">[1,2,3]</div>'
    JSON_MISSING = "<div></div>"

    def test_json_text(self):
        class Page(BasePage):
            info = Field(".data", json=True)

        page = Page(self.JSON_HTML)
        assert page.info == {"key": "value"}

    def test_json_attr(self):
        class Page(BasePage):
            info = Field(".data", attr="info", json=True)

        page = Page(self.JSON_ATTR_HTML)
        assert page.info == {"x": 1}

    def test_json_default(self):
        class Page(BasePage):
            info = Field(".missing", json=True, default={"fallback": True})

        page = Page(self.JSON_MISSING)
        assert page.info == {"fallback": True}

    def test_json_invalid(self):
        class Page(BasePage):
            info = Field(".data", json=True, default={"error": True})

        page = Page("<div class='data'>not json</div>")
        assert page.info == {"error": True}


class TestFieldFragment:
    def test_fragment_single(self):

        class Product(BaseFragment):
            name = Field(".name")

        class Page(BasePage):
            first = Field(".product", fragment=Product, index=0)

        page = Page(CATALOG_HTML)
        prod = page.first
        assert prod.name == "Pen"

    def test_fragment_multiple(self):

        class Product(BaseFragment):
            name = Field(".name")

        class Page(BasePage):
            products = Field(".product", fragment=Product, multiple=True)

        page = Page(CATALOG_HTML)
        prods = page.products
        assert len(prods) == 2
        assert prods[0].name == "Pen"


class TestFieldXPath:
    HTML = """
    <html><body>
        <h1>Title</h1>
        <div class="price" data-value="9.99"></div>
    </body></html>
    """

    def test_xpath_text(self):
        class Page(BasePage):
            heading = Field("//h1/text()")

        page = Page(self.HTML)
        assert page.heading == "Title"

    def test_xpath_attr(self):
        class Page(BasePage):
            price = Field("//div[@class='price']/@data-value")

        page = Page(self.HTML)
        assert page.price == "9.99"

    def test_xpath_multiple(self):
        class Page(BasePage):
            items = Field("//div/span/text()", multiple=True)

        page = Page("<div><span>A</span><span>B</span></div>")
        assert page.items == ["A", "B"]


class TestFieldConverter:
    def test_converter(self):
        class Page(BasePage):
            number = Field(".num", converter=int)

        page = Page("<div class='num'>123</div>")
        assert page.number == 123

    def test_pipe(self):
        class Page(BasePage):
            text = Field("h1") | str.strip | str.upper

        page = Page("<h1> hello </h1>")
        assert page.text == "HELLO"

    def test_pipe_with_attr(self):
        class Page(BasePage):
            price = Field(".price", attr="data-value") | float

        page = Page('<div class="price" data-value="9.99"></div>')
        assert page.price == 9.99


class TestFieldNamespaces:
    XML = """<root xmlns:ns="http://example.com/ns">
        <ns:title>Namespaced Title</ns:title>
    </root>"""

    def test_xpath_with_namespaces(self):
        from lxml import etree

        doc = etree.fromstring(self.XML)

        class Page(BasePage):
            heading = Field(
                "//ns:title/text()", namespaces={"ns": "http://example.com/ns"}
            )

        page = Page(doc)
        assert page.heading == "Namespaced Title"

    def test_xpath_attr_with_namespaces(self):
        from lxml import etree

        XML = """<root xmlns:ns="http://example.com/ns">
            <ns:item ns:attr="value">text</ns:item>
        </root>"""
        doc = etree.fromstring(XML)

        class Page(BasePage):
            val = Field(
                "//ns:item/@ns:attr", namespaces={"ns": "http://example.com/ns"}
            )

        page = Page(doc)
        assert page.val == "value"


class TestFieldJsonModel:
    JSON_HTML = '<script type="json">{"name": "Pen", "price": 1.5}</script>'

    @pydantic_mark
    def test_json_with_pydantic_model(self):
        from pydantic import BaseModel

        class Product(BaseModel):
            name: str
            price: float

        class Page(BasePage):
            product: Product = "script[type='json']"

        page = Page(self.JSON_HTML)
        assert isinstance(page.product, Product)
        assert page.product.name == "Pen"
        assert page.product.price == 1.5

    @pydantic_mark
    def test_json_model_default(self):
        from pydantic import BaseModel

        class Product(BaseModel):
            name: str
            price: float

        class Page(BasePage):
            product: Product = (".missing", None)

        page = Page("<html></html>")
        assert page.product is None

    @pydantic_mark
    def test_json_model_invalid(self):
        from pydantic import BaseModel

        class Product(BaseModel):
            name: str
            price: float

        class Page(BasePage):
            product: Product = ("script[type='json']", None)

        page = Page('<script type="json">invalid json</script>')
        assert page.product is None  # default returned on parse error


class TestFieldFragmentMultiple:
    HTML = """
    <div class="product">
        <span class="name">Pen</span>
        <span class="price" data-value="1.5"></span>
    </div>
    <div class="product">
        <span class="name">Paper</span>
        <span class="price" data-value="2.0"></span>
    </div>
    """

    def test_fragment_multiple(self):

        class Product(BaseFragment):
            name = Field(".name")
            price = Field(".price", attr="data-value") | float

        class Page(BasePage):
            products = Field(".product", fragment=Product, multiple=True)

        page = Page(self.HTML)
        prods = page.products
        assert len(prods) == 2
        assert prods[0].name == "Pen"
        assert prods[0].price == 1.5
        assert prods[1].name == "Paper"
        assert prods[1].price == 2.0

    def test_fragment_single_index_none(self):

        class Product(BaseFragment):
            name = Field(".name")

        class Page(BasePage):
            all_products = Field(".product", fragment=Product, index=None)

        page = Page(self.HTML)
        prods = page.all_products
        assert len(prods) == 2
        assert prods[0].name == "Pen"
        assert prods[1].name == "Paper"


class TestFieldEdgeCases:
    def test_empty_result_returns_default(self):
        class Page(BasePage):
            nothing = Field(".missing", default="N/A")

        page = Page("<html></html>")
        assert page.nothing == "N/A"

    def test_multiple_on_empty_returns_empty_list(self):
        class Page(BasePage):
            items = Field(".missing", multiple=True)

        page = Page("<html></html>")
        assert page.items == []

    def test_index_out_of_range_returns_default(self):
        class Page(BasePage):
            first = Field(".item", index=3, default="N/A")

        page = Page("<div class='item'>A</div>")
        assert page.first == "N/A"

    def test_xpath_empty_result_returns_default(self):
        class Page(BasePage):
            heading = Field("//h2/text()", default="No heading")

        page = Page("<html><h1>Title</h1></html>")
        assert page.heading == "No heading"
