# Examples

## Quick Start

The simplest way to extract data is to annotate your fields with Python types
and provide a CSS selector string.  No need to import `Field` or remember
field class names.

```python
from pagemodel import BasePage, fragment

html = """<html><body>
    <h1>Hello</h1>
    <div class="price" data-value="9.99" data-currency="USD"></div>
</body></html>"""

class Page(BasePage):
    title: str       = "h1"
    price: float     = ".price @data-value"
    currency: str    = ".price @data-currency"

page = Page(html)
print(page.title)     # Hello
print(page.price)     # 9.99
print(page.currency)  # USD
```

XPath expressions are recognised automatically when the string starts with
`//`, `.//`, `..` or `xpath:`.

```python
class Page(BasePage):
    heading: str = "//h1/text()"
```

The annotation type controls conversion – `int`, `float`, `bool`, `str`,
`dict`, `list` and `Any` all work out of the box.

```python
class Page(BasePage):
    count: int   = ".count"
    active: bool = ".status"
    data: dict   = "script[type='application/json']"
```

For extra inline processing use the `Q` / `Sel` / `X` helpers.

```python
from pagemodel import Q, X

class Page(BasePage):
    title   = Q("h1") | str.strip | str.upper
    price   = Q(".price @data-value") | float
    heading = X("//h1/text()") | str.lower
```

Repeating items are described with the `@fragment` decorator.

```python
class Page(BasePage):
    @fragment(".product", multiple=True)
    class Product:
        name: str   = ".name"
        price: float = ".price @data-value"
```

---

## Advanced Usage

### Explicit `Field` and `XpathField`

For full control over extraction options (JSON parsing, namespaces, fragment
wrapping, etc.) use the `Field` descriptor directly.

```python
from pagemodel import BasePage, Field

class Page(BasePage):
    heading  = Field("h1")
    price    = Field(".price", attr="data-value") | float
    currency = Field(".price", attr="data-currency", default="USD")
    items    = Field(".item", multiple=True)
```

`XpathField` gives you the raw result of `doc.xpath()` – useful for complex
XPath queries that mix text, attributes and elements.

```python
from pagemodel import XpathField

class Page(BasePage):
    mixed = XpathField("//div/* | //div/@*", index=None)
```

### JSON and Pydantic models

Add `json=True` to parse element content or an attribute as JSON.  Pass a
Pydantic model via `model` to validate the result automatically.

```python
from pydantic import BaseModel

class Product(BaseModel):
    name: str
    price: float

class Page(BasePage):
    product: Product = "script[type='application/json']"

page = Page('<script type="application/json">{"name":"Pen","price":1.5}</script>')
print(page.product.name)   # Pen
print(page.product.price)  # 1.5
```

### Key‑value aggregation with `@keyvalue`

Turn a list of fragments into a dictionary with one decorator.

```python
from pagemodel import keyvalue

@keyvalue("Spec", key_field="label", value_field="val", export_name="specs")
class Page(BasePage):
    @fragment(".row", multiple=True)
    class Spec:
        label: str = ".key"
        val: str = ".val"

page = Page("""
<div class="row"><span class="key">Color</span><span class="val">Red</span></div>
<div class="row"><span class="key">Size</span><span class="val">XL</span></div>
""")

print(page.export())
# {'specs': {'Color': 'Red', 'Size': 'XL'}}
```

### Streaming large XML

`StreamPage` processes one element at a time, yielding exported dictionaries
without loading the whole tree into memory.

```python
from pagemodel import StreamPage, HtmlFragment, Field

class Item(HtmlFragment):
    name = Field("name")

xml = """<root>
    <item><name>Alice</name></item>
    <item><name>Bob</name></item>
</root>"""

stream = StreamPage(xml, tag_callback_map={"item": Item})
for entry in stream.iter_items("item"):
    print(entry)   # {'name': 'Alice'}   {'name': 'Bob'}
```

### Export and model conversion

Call `export()` to get a plain dictionary, or `to_model()` to hydrate a
Pydantic model.

```python
from pydantic import BaseModel

class CatalogModel(BaseModel):
    title: str
    products: list[dict]

class Page(BasePage):
    title = Field("h1")
    @fragment(".product", multiple=True)
    class Product:
        name: str = ".name"
        price: float = ".price @data-value"

page = Page("...")
catalog = page.to_model(CatalogModel)
print(catalog.title)   # Catalog
```