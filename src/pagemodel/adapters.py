"""
Annotation processing for pagemodel.

Converts class annotations (e.g. ``title: str = "h1"``) into field descriptors
using a lightweight resolver. Types like ``int``, ``float``, ``bool``, ``dict``,
``list``, and Pydantic models are mapped to appropriate ``Field`` configurations
with converters or JSON parsing.
"""

from __future__ import annotations

import functools
from typing import Any

from .fields import Field, XpathField
from .helpers import _Q, _X
from .log import logger

__all__ = ("_process_annotations",)


# ---------------------------------------------------------------------------
# Annotation resolution (cached)
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=128)
def _resolve_annotation(annot: Any) -> Any:
    import typing

    if annot is typing.Any:
        return typing.Any

    if isinstance(annot, type):
        return annot

    if isinstance(annot, str):
        return {
            "int": int,
            "float": float,
            "str": str,
            "bool": bool,
            "NoneType": type(None),
            "list": list,
            "dict": dict,
            "Any": typing.Any,
        }.get(annot, None)

    origin = typing.get_origin(annot)
    if origin is not None:
        args = typing.get_args(annot)
        if origin is typing.Union:
            for arg in args:
                if arg is not type(None):
                    return _resolve_annotation(arg)
        elif origin in (list, list):
            if args:
                return _resolve_annotation(args[0])
            return origin
        else:
            return origin

    return annot


# ---------------------------------------------------------------------------
# Converter selection based on type
# ---------------------------------------------------------------------------
def _converter_for_type(python_type: Any) -> Any:
    """Return a converter callable appropriate for the given type, or None."""
    if python_type is bool:
        return _to_bool
    if python_type is int:
        return int
    if python_type is float:
        return float
    # str, list, dict, Any, Pydantic models are handled elsewhere
    return None


def _to_bool(value: str) -> bool:
    return (value or "").strip().lower() in ("true", "1", "yes", "on")


# ---------------------------------------------------------------------------
# Single annotation → Field
# ---------------------------------------------------------------------------
def _process_single_annotation(cls, name, annot, value):
    """Create a field from a single annotation entry. Returns a BaseField or None."""

    # Q() / X() helpers
    if isinstance(value, _Q):
        return value.to_field()
    if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], _Q):
        q_obj, default = value
        return q_obj.to_field(default=default)

    if isinstance(value, _X):
        return value.to_field()
    if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], _X):
        x_obj, default = value
        return x_obj.to_field(default=default)

    # String / tuple with string
    if isinstance(value, str):
        selector = value
        default = None
    elif isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], str):
        selector, default = value
    else:
        return None

    python_type = _resolve_annotation(annot)
    # Default to str if annotation is missing or unresolved
    if python_type is None:
        python_type = str
    logger.debug("  Annotation %s: %s -> %s", name, annot, python_type)

    # Determine if this is an XPath expression
    is_xpath = (
        selector.startswith("/")
        or selector.startswith(".//")
        or selector.startswith("..")
        or selector.startswith("xpath:")
    )
    if is_xpath:
        sel = selector[6:] if selector.startswith("xpath:") else selector
        return XpathField(sel, default=default)

    selector, attr_name = _extract_attr(selector)

    # JSON special cases
    if python_type in (dict, list, Any) or _is_pydantic_model(python_type):
        return Field(
            selector,
            json=True,
            default=default,
            model=python_type if _is_pydantic_model(python_type) else None,
            attr=attr_name,
        )

    # Other types: add a converter if applicable
    converter = _converter_for_type(python_type)
    return Field(selector, default=default, converter=converter, attr=attr_name)


# ---------------------------------------------------------------------------
# Pydantic model detection
# ---------------------------------------------------------------------------
def _is_pydantic_model(t: Any) -> bool:
    try:
        from pydantic import BaseModel

        return isinstance(t, type) and issubclass(t, BaseModel)
    except ImportError:
        return False


def _extract_attr(selector: str) -> tuple[str, str | None]:
    """Extract optional attribute (@attr) from selector"""
    attr_name = None
    if " @" in selector:
        selector, attr_name = selector.split(" @", 1)
        selector = selector.strip()
        attr_name = attr_name.strip()
    return (selector, attr_name)


# ---------------------------------------------------------------------------
# Core annotation processor
# ---------------------------------------------------------------------------
def _process_annotations(cls: type) -> None:
    logger.debug("Processing annotations for class %s", cls.__name__)

    # First pass: handle annotated fields
    for name, annot in cls.__annotations__.items():
        value = cls.__dict__.get(name)
        if value is None:
            continue

        field = _process_single_annotation(cls, name, annot, value)
        if field is not None:
            field.__set_name__(cls, name)
            setattr(cls, name, field)
            logger.debug("  Created %s for %s", type(field).__name__, name)

    # Second pass: handle Q() / X() tuples without type annotation,
    # and bare strings (e.g. name = ".name")
    for name, value in list(cls.__dict__.items()):
        if isinstance(value, tuple) and len(value) == 2 and hasattr(value[0], "to_field"):
            builder, default = value
            field = builder.to_field(default=default)
            field.__set_name__(cls, name)
            setattr(cls, name, field)
            logger.debug(
                "  Created %s for %s (via builder with default, no annotation)",
                type(field).__name__,
                name,
            )
        elif isinstance(value, str) and not name.startswith("_"):
            selector, attr_name = _extract_attr(value)
            field = Field(selector, attr=attr_name)
            field.__set_name__(cls, name)
            setattr(cls, name, field)
            logger.debug("  Created %s for %s (bare string)", type(field).__name__, name)
