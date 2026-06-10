"""
Tests for Q, Sel, and X helpers.
"""

from pagemodel import BasePage, Field, Q, Sel, X

HTML = """
<html><body>
    <h1>Hello</h1>
    <div class="price" data-value="9.99" data-currency="USD"></div>
</body></html>
"""


class TestQ:
    def test_q_creates_textfield(self):
        class Page(BasePage):
            title = Q("h1")

        page = Page(HTML)
        assert page.title == "Hello"
        assert isinstance(Page.__dict__["title"], Field)

    def test_q_creates_attrfield(self):
        class Page(BasePage):
            price = Q(".price @data-value")

        page = Page(HTML)
        assert page.price == "9.99"
        assert isinstance(Page.__dict__["price"], Field)

    def test_q_with_pipe(self):
        class Page(BasePage):
            price = Q(".price @data-value") | float

        page = Page(HTML)
        assert page.price == 9.99

    def test_q_with_default_tuple(self):
        class Page(BasePage):
            missing: str = (Q(".missing"), "default")

        page = Page(HTML)
        assert page.missing == "default"

    def test_q_with_default_tuple_no_type(self):
        class Page(BasePage):
            missing = (Q(".missing"), "default")

        page = Page(HTML)
        assert page.missing == "default"

    def test_q_with_default_attr(self):
        class Page(BasePage):
            currency: str = (Q(".price @data-currency"), "USD")

        page = Page(HTML)
        assert page.currency == "USD"

    def test_q_with_default_attr_no_type(self):
        class Page(BasePage):
            currency = (Q(".price @data-currency"), "USD")

        page = Page(HTML)
        assert page.currency == "USD"


class TestSel:
    """Sel is an alias for Q, so behaviour must be identical."""

    def test_sel_creates_textfield(self):
        class Page(BasePage):
            title = Sel("h1")

        page = Page(HTML)
        assert page.title == "Hello"


class TestX:
    """X creates XpathField, requiring explicit /text() or @attr for strings."""

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

    def test_x_without_annotation(self):
        """X should work even without a type annotation (second pass in _process_annotations)."""

        class Page(BasePage):
            heading = X("//h1/text()")

        page = Page(HTML)
        assert page.heading == "Hello"

    def test_x_tuple_without_annotation(self):
        class Page(BasePage):
            missing = (X("//h2/text()"), "Fallback")

        page = Page(HTML)
        assert page.missing == "Fallback"
