"""
Mixins providing reusable functionality for page/fragment classes.

- ``ExportMixin`` – deep export to dictionary with Pydantic/model support.
- ``CacheMixin`` – cache clearing for extracted fields.
- ``PydanticMixin`` – conversion to Pydantic models via ``to_model()``.
- ``CSSMixin`` – on‑instance CSS selector compilation and caching.
"""

from __future__ import annotations

from typing import Any

from lxml.cssselect import CSSSelector

from .log import logger


# ---------------------------------------------------------------------------
# Export mixin
# ---------------------------------------------------------------------------
class ExportMixin:
    """Adds export() and deep-export logic."""

    def export(self, deep: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for attr_name, export_name in getattr(self, "_pagemodel_export", []):
            value = getattr(self, attr_name)
            if deep:
                value = self._deep_export(value)
            result[export_name] = value
        return result

    def _deep_export(self, value: Any) -> Any:
        # Pydantic model -> dict (v2 then v1 fallback)
        if hasattr(value, "model_dump"):  # pydantic v2
            logger.debug("Converting Pydantic v2 model to dict")
            return value.model_dump()
        if hasattr(value, "dict"):  # pydantic v1
            logger.debug("Converting Pydantic v1 model to dict")
            return value.dict()
        # Quorra page/fragment -> export
        if hasattr(value, "export"):
            return value.export()
        if isinstance(value, list):
            return [self._deep_export(v) for v in value]
        return value


# ---------------------------------------------------------------------------
# Cache mixin
# ---------------------------------------------------------------------------
class CacheMixin:
    """Adds clear_cache() for resetting cached fields."""

    def clear_cache(self) -> None:
        """Remove all cached field values and optional cached properties."""
        logger.debug("Clearing cache for instance %s", self)
        for name, _ in getattr(self, "_pagemodel_export", []):
            self.__dict__.pop(name, None)
        # Also allow subclasses to define extra cache keys
        extra = getattr(self, "_cache_extra_keys", [])
        for key in extra:
            self.__dict__.pop(key, None)


# ---------------------------------------------------------------------------
# Pydantic mixin
# ---------------------------------------------------------------------------
class PydanticMixin:
    """Adds to_model() for Pydantic integration."""

    __pydantic_model__: type | None = None

    def to_model(self, model_cls=None):
        if model_cls is None:
            model_cls = self.__pydantic_model__
        if model_cls is None:
            raise ValueError(
                "No Pydantic model specified. "
                "Set __pydantic_model__ on the class or pass model_cls."
            )
        try:
            from pydantic import BaseModel
        except ImportError:
            raise ImportError("pydantic is required for to_model()") from None

        data = self.export()
        if hasattr(BaseModel, "model_validate"):
            return model_cls.model_validate(data)
        else:
            return model_cls.parse_obj(data)


# ---------------------------------------------------------------------------
# CSS selector mixin
# ---------------------------------------------------------------------------
class CSSMixin:
    """Adds css() for compiling and caching CSS selectors on the instance."""

    def css(self, selector: str) -> CSSSelector:
        """Return a compiled CSSSelector, caching it on the instance."""
        cache = self.__dict__.setdefault("_css_cache", {})
        if selector not in cache:
            cache[selector] = CSSSelector(selector)
        return cache[selector]
