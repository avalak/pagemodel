# pagemodel

[![tests](https://github.com/avalak/pagemodel/actions/workflows/tests.yml/badge.svg)](https://github.com/avalak/pagemodel/actions/workflows/tests.yml)
[![publish](https://github.com/avalak/pagemodel/actions/workflows/publish.yml/badge.svg)](https://github.com/avalak/pagemodel/actions/workflows/publish.yml)
[![PyPI - Version](https://img.shields.io/pypi/v/pagemodel)](https://pypi.org/project/pagemodel/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pagemodel)

---

A declarative HTML/XML extraction framework built on lxml.

## Features

- **Unified `Field` descriptor** – handles text, attributes, JSON, fragments,
  and multiple values via a single class. CSS and XPath selectors are
  auto‑detected and pre‑compiled.
- **Type‑driven annotations** – write `title: str = "h1"` and the library
  automatically picks the right converter (`str`, `int`, `float`, `bool`,
  `dict`, `list`, Pydantic models).
- **`@fragment` decorator** – describe repeating blocks of HTML without
  leaving the page class.
- **`@keyvalue` decorator** – turn a list of fragments into a dictionary
  with one line.
- **Built‑in Pydantic integration** – validate JSON data and export directly
  to your models.
- **Streaming parser** (`StreamPage`) for large XML files that cannot fit in
  memory.
- **Compact helpers** `Q`, `Sel`, `X` for rapid field creation with pipeline
  support (`| float`, `| str.strip`).
- **Fast** – selectors are compiled once, results are cached, and lxml does
  the heavy lifting in C.

## Installation

```bash
pip install pagemodel
# or with extra dependencies
pip install pagemodel[all]
```

Python **>=3.10** is required.

## Quick Start

```python
from pagemodel import BasePage, fragment

html = """<html><body>
    <h1>Catalog</h1>
    <div class="product">
        <span class="name">Pen</span>
        <span class="price" data-value="1.5"></span>
    </div>
    <div class="product">
        <span class="name">Paper</span>
        <span class="price" data-value="2.0"></span>
    </div>
</body></html>"""

class Page(BasePage):
    title: str = "h1"

    @fragment(".product", multiple=True)
    class Product:
        name: str   = ".name"
        price: float = ".price @data-value"

page = Page(html)
print(page.title)          # Catalog
for prod in page.Product:
    print(prod.name, prod.price)
print(page.export())       # full dictionary
```

## Advanced usage

### Explicit `Field`, JSON and Pydantic models

```python
from pagemodel import BasePage, Field
from pydantic import BaseModel

class ProductModel(BaseModel):
    name: str
    price: float

class Page(BasePage):
    product: ProductModel = "script[type='application/json']"

page = Page('<script type="application/json">{"name":"Pen","price":1.5}</script>')
print(page.product.name)   # Pen
print(page.product.price)  # 1.5
```

### Key‑value aggregation with `@keyvalue`

```python
from pagemodel import BasePage, fragment, keyvalue

@keyvalue("Spec", key_field="label", value_field="val", export_name="specs")
class Page(BasePage):
    @fragment(".row", multiple=True)
    class Spec:
        label: str = ".key"
        val: str   = ".val"

page = Page("""<div class="row"><span class="key">Color</span><span class="val">Red</span></div>""")
print(page.export())   # {'specs': {'Color': 'Red'}}
```

### Streaming large XML

```python
from pagemodel import StreamPage, HtmlFragment, Field

class Item(HtmlFragment):
    name = Field("name")

xml = """<root><item><name>Alice</name></item><item><name>Bob</name></item></root>"""
stream = StreamPage(xml, tag_callback_map={"item": Item})
for entry in stream.iter_items("item"):
    print(entry)   # {'name': 'Alice'}   {'name': 'Bob'}
```

## Documentation

[Documentation](https://avalak.github.io/pagemodel "pagemodel - Documentation")

## Running tests

```bash
uv run pytest
```

## License

This project is licensed under the **MIT** License – see the [LICENSE](LICENSE) file for details.
