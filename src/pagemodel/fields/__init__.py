"""Fields package for pagemodel.

This package provides the building blocks for declarative HTML/XML extraction.

Core descriptors
----------------
- ``BaseField`` – abstract base class for all field descriptors, implementing
  caching, pipeline support, and export registration.
- ``Field`` – unified field descriptor that replaces all specialised types from
  earlier versions (TextField, AttrField, etc.). Supports CSS and XPath
  selectors, text/attribute extraction, JSON parsing with optional Pydantic
  validation, fragment wrapping, and multiple-value modes.
- ``XpathField`` – specialised descriptor for raw XPath queries, returning the
  exact result of ``doc.xpath()`` without automatic text extraction.

Fragment support
----------------
- ``fragment`` – class decorator that turns a plain class into an
  ``HtmlFragment`` and wraps it in a ``FragmentDescriptor`` for use on a page.
- ``FragmentDescriptor`` – descriptor that extracts elements matching a CSS
  selector, instantiates the associated fragment class, and caches the result.

Utilities
---------
- ``export`` – decorator that marks a method for inclusion in ``export()``
  output.

All public symbols are re‑exported from the package root for convenience.
"""

from .base import BaseField, export
from .field import Field
from .fragment_descriptor import FragmentDescriptor, fragment
from .xpath_field import XpathField

__all__ = [
    "BaseField",
    "Field",
    "FragmentDescriptor",
    "XpathField",
    "export",
    "fragment",
]
