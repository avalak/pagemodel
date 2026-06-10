#!/usr/bin/env python3
"""
Advanced benchmark for pagemodel 0.2.0 – compares full‑DOM mode, raw lxml
(naive), optimized lxml (pre‑compiled CSS selectors), and BeautifulSoup.

Usage:
    python benchmark_advanced.py [--products N] [--repeat M] [--number K]
                                  [--no-bs] [--no-lxml]

Examples:
    python benchmark_advanced.py
    python benchmark_advanced.py --products 5000 --repeat 3 --number 50
    python benchmark_advanced.py --no-bs --no-lxml
"""

import argparse
import time
import timeit
import tracemalloc
from collections import namedtuple
from typing import Callable

# ---------------------------------------------------------------------------
# Page model (pagemodel 0.2.0)
# ---------------------------------------------------------------------------
from pagemodel import BasePage, Field, fragment


class CatalogPage(BasePage):
    title = Field("h1")

    @fragment(".product", multiple=True)
    class Product:
        name = Field(".name")
        price = Field(".price", attr="data-currency")
        link = Field("a.link", attr="href")


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------
PRODUCT_SINGLE = """
<div class="product">
    <h3 class="name">Product {i}</h3>
    <span class="price" data-currency="USD">{price}</span>
    <a class="link" href="/product/{i}">Details</a>
</div>
"""


def make_page_html(product_count: int) -> str:
    return f"""<html><body>
<h1>My Shop</h1>
<div class="catalog">
{"".join(PRODUCT_SINGLE.format(i=i, price=round(10 + i * 0.1, 2)) for i in range(product_count))}
</div>
</body></html>"""


# ---------------------------------------------------------------------------
# Extraction functions
# ---------------------------------------------------------------------------
def extract_pagemodel_full(source: str) -> dict:
    page = CatalogPage(source)
    # Access all fields to trigger lazy extraction
    _ = page.title
    for prod in page.Product:
        _ = prod.name
        _ = prod.price
        _ = prod.link
    return page.export()


def extract_lxml_raw(page_source: str) -> dict:
    from lxml import html

    doc = html.fromstring(page_source)
    title = doc.cssselect("h1")[0].text_content()
    products = []
    for elm in doc.cssselect(".product"):
        name = elm.cssselect(".name")[0].text_content()
        price = elm.cssselect(".price")[0].get("data-currency")
        link = elm.cssselect("a.link")[0].get("href")
        products.append({"name": name, "price": price, "link": link})
    return {"title": title, "products": products}


# Pre‑compiled CSS selectors for optimized lxml
from lxml.cssselect import CSSSelector

SEL_H1 = CSSSelector("h1")
SEL_PRODUCT = CSSSelector(".product")
SEL_NAME = CSSSelector(".name")
SEL_PRICE = CSSSelector(".price")
SEL_LINK = CSSSelector("a.link")


def extract_lxml_optimized(page_source: str) -> dict:
    from lxml import html

    doc = html.fromstring(page_source)
    title = SEL_H1(doc)[0].text_content()
    products = []
    for elm in SEL_PRODUCT(doc):
        name = SEL_NAME(elm)[0].text_content()
        price = SEL_PRICE(elm)[0].get("data-currency")
        link = SEL_LINK(elm)[0].get("href")
        products.append({"name": name, "price": price, "link": link})
    return {"title": title, "products": products}


def extract_bs(page_source: str) -> dict:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(page_source, "lxml")
    title = soup.select_one("h1").get_text()
    products = []
    for elm in soup.select(".product"):
        name = elm.select_one(".name").get_text()
        price = elm.select_one(".price").get("data-currency")
        link = elm.select_one("a.link").get("href")
        products.append({"name": name, "price": price, "link": link})
    return {"title": title, "products": products}


# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------
Result = namedtuple("Result", ["mean_ms", "stdev_ms"])
MemResult = namedtuple("MemResult", ["peak_kb"])


def benchmark(func: Callable, number: int = 30, repeat: int = 3) -> Result:
    """Time a callable *number* times and repeat the trial *repeat* times."""
    timer = timeit.Timer(stmt=func)
    times = timer.repeat(repeat=repeat, number=number)
    mean = sum(times) / len(times) * 1000 / number
    stdev = (
        (sum((t * 1000 / number - mean) ** 2 for t in times) / (len(times) - 1)) ** 0.5
        if len(times) > 1
        else 0.0
    )
    return Result(mean, stdev)


def memory_benchmark(func: Callable) -> MemResult:
    """Return peak memory in KB during execution of *func*."""
    tracemalloc.start()
    func()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return MemResult(peak / 1024)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Benchmark pagemodel")
    parser.add_argument(
        "--products", type=int, default=1000, help="Number of product divs"
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=3,
        help="How many times to repeat the timing trial",
    )
    parser.add_argument(
        "--number", type=int, default=30, help="How many calls per trial"
    )
    parser.add_argument(
        "--no-bs", action="store_true", help="Skip BeautifulSoup benchmark"
    )
    parser.add_argument(
        "--no-lxml", action="store_true", help="Skip raw/optimized lxml benchmarks"
    )
    args = parser.parse_args()

    print(f"Products: {args.products}  Repeat: {args.repeat}  Number: {args.number}\n")

    html = make_page_html(args.products)

    # -----------------------------------------------------------------------
    # pagemodel 0.2.0
    # -----------------------------------------------------------------------
    print("--- pagemodel 0.2.0 ---")
    # Cold – full cycle including HTML parsing
    pagemodel_cold = lambda: extract_pagemodel_full(html)
    res_cold = benchmark(pagemodel_cold, number=args.number, repeat=args.repeat)
    print(
        f"  full-DOM, cold   : {res_cold.mean_ms:8.2f} ms ± {res_cold.stdev_ms:.2f} ms"
    )

    # Warm – re‑use the same page, only export
    page = CatalogPage(html)
    # Warm‑up
    _ = extract_pagemodel_full(html)
    pagemodel_warm = lambda: page.export()
    res_warm = benchmark(pagemodel_warm, number=args.number, repeat=args.repeat)
    print(
        f"  full-DOM, warm   : {res_warm.mean_ms:8.2f} ms ± {res_warm.stdev_ms:.2f} ms"
    )

    mem = memory_benchmark(lambda: extract_pagemodel_full(html))
    print(f"  peak memory      : {mem.peak_kb:8.0f} KB\n")

    # -----------------------------------------------------------------------
    # lxml
    # -----------------------------------------------------------------------
    if not args.no_lxml:
        print("--- lxml ---")
        lxml_raw = lambda: extract_lxml_raw(html)
        res = benchmark(lxml_raw, number=args.number, repeat=args.repeat)
        print(f"  raw              : {res.mean_ms:8.2f} ms ± {res.stdev_ms:.2f} ms")

        lxml_opt = lambda: extract_lxml_optimized(html)
        res = benchmark(lxml_opt, number=args.number, repeat=args.repeat)
        print(f"  compiled CSS     : {res.mean_ms:8.2f} ms ± {res.stdev_ms:.2f} ms")

        mem = memory_benchmark(lambda: extract_lxml_raw(html))
        print(f"  peak memory      : {mem.peak_kb:8.0f} KB\n")

    # -----------------------------------------------------------------------
    # BeautifulSoup
    # -----------------------------------------------------------------------
    if not args.no_bs:
        print("--- BeautifulSoup ---")
        try:
            bs_extract = lambda: extract_bs(html)
            res = benchmark(bs_extract, number=args.number, repeat=args.repeat)
            print(f"  lxml parser      : {res.mean_ms:8.2f} ms ± {res.stdev_ms:.2f} ms")

            mem = memory_benchmark(lambda: extract_bs(html))
            print(f"  peak memory      : {mem.peak_kb:8.0f} KB\n")
        except ImportError:
            print("  BeautifulSoup not installed, skipped.\n")
            print("  uv pip install bs4\n")

    print("Done.")


if __name__ == "__main__":
    main()
