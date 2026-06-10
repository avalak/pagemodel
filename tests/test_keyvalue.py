"""
Tests for @keyvalue decorator.
"""

from pagemodel import BasePage, fragment, keyvalue

HTML = """
<div class="specs">
    <div class="row"><span class="key">Color</span><span class="val">Red</span></div>
    <div class="row"><span class="key">Size</span><span class="val">XL</span></div>
</div>
"""


class TestKeyValue:
    def test_keyvalue_decorator(self):
        @keyvalue("Spec", key_field="k", value_field="v", export_name="specs")
        class Page(BasePage):
            @fragment(".row", multiple=True)
            class Spec:
                k: str = ".key"
                v: str = ".val"

        page = Page(HTML)
        data = page.export()
        assert data["specs"] == {"Color": "Red", "Size": "XL"}

    def test_keyvalue_default_export_name(self):
        # export_name must not clash with the fragment attribute name.
        @keyvalue("Spec", export_name="my_specs")
        class Page(BasePage):
            @fragment(".row", multiple=True)
            class Spec:
                key: str = ".key"
                value: str = ".val"

        page = Page(HTML)
        data = page.export()
        assert data["my_specs"] == {"Color": "Red", "Size": "XL"}
