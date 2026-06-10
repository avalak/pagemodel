#!/usr/bin/env python3
"""
Advanced profiling tool for pagemodel.

Usage:
    python profile_advanced.py [--mode cold|warm] [--export] [--snakeviz] [--products N]

Modes:
    cold  – creates a fresh page and accesses all fields (default)
    warm  – reuses a pre‑created page, measuring only field access & export
    --export  – runs page.export() at the end (both modes)
    --snakeviz – writes profile.prof and launches snakeviz

Examples:
    python profile_advanced.py
    python profile_advanced.py --mode warm --export
    python profile_advanced.py --products 5000 --snakeviz
"""

import argparse
import cProfile
import io
import pstats
import time

from pagemodel import BasePage, Field, fragment

# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------
PRODUCT_SINGLE = """
<div class="product">
    <h3 class="name">Product {i}</h3>
    <span class="price" data-currency="USD">{price}</span>
    <a class="link" href="/product/{i}">Details</a>
</div>
"""


def make_page_html(product_count: int) -> str:
    return f"""<html>
<head><title>My Shop - Catalog</title></head>
<body>
<h1>My Shop</h1>
<div class="catalog">
{"".join(PRODUCT_SINGLE.format(i=i, price=round(10 + i * 0.1, 2)) for i in range(product_count))}
</div>
</body></html>"""


# ---------------------------------------------------------------------------
# Page model
# ---------------------------------------------------------------------------
class CatalogPage(BasePage):
    title = Field("h1")

    @fragment(".product", multiple=True)
    class Product:
        name = Field(".name")
        price = Field(".price", attr="data-currency")
        link = Field("a.link", attr="href")


# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------
def cold_run(page_html: str, do_export: bool) -> None:
    page = CatalogPage(page_html)
    _ = page.title
    for prod in page.Product:
        _ = prod.name
        _ = prod.price
        _ = prod.link
    if do_export:
        _ = page.export()


def warm_run(page: CatalogPage, do_export: bool) -> None:
    _ = page.title
    for prod in page.Product:
        _ = prod.name
        _ = prod.price
        _ = prod.link
    if do_export:
        _ = page.export()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Profile pagemodel")
    parser.add_argument("--mode", choices=["cold", "warm"], default="cold")
    parser.add_argument("--export", action="store_true", help="Call page.export()")
    parser.add_argument(
        "--snakeviz", action="store_true", help="Dump profile.prof and open snakeviz"
    )
    parser.add_argument("--products", type=int, default=10000, help="Number of products")
    args = parser.parse_args()

    print(f"Products: {args.products}  Mode: {args.mode}  Export: {args.export}")
    page_html = make_page_html(args.products)

    # Pre-create page for warm mode
    page = CatalogPage(page_html) if args.mode == "warm" else None
    if page:
        # trigger lazy loading once so that subsequent access is warm
        _ = page.title
        _ = page.Product
        for p in page.Product:
            _ = p.name
            _ = p.price
            _ = p.link
        if args.export:
            _ = page.export()

    profiler = cProfile.Profile()
    profiler.enable()

    t0 = time.perf_counter()
    if args.mode == "cold":
        cold_run(page_html, args.export)
    else:
        warm_run(page, args.export)
    t1 = time.perf_counter()

    profiler.disable()

    print(f"Wall clock: {t1 - t0:.4f} s\n")

    # Print stats
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
    ps.print_stats(40)  # top 40 functions
    print(s.getvalue())

    # Optionally write profile for snakeviz
    if args.snakeviz:
        profiler.dump_stats("profile.prof")
        print("Profile written to profile.prof")
        try:
            from snakeviz.cli import main as snakeviz_main

            snakeviz_main(["profile.prof"])
        except ImportError:
            print("Install snakeviz to visualize: uv pip install snakeviz")
        except Exception:
            pass


if __name__ == "__main__":
    main()
