"""
Higher-order decorators for pagemodel classes.

Currently provides ``@keyvalue``, which automatically creates an ``@export``
method that turns a list of fragments into a dictionary.
"""

from .fields import export


def keyvalue(fragments_attr, key_field="key", value_field="value", export_name=None):
    """Class decorator that adds an ``@export`` method converting a list of
    fragments to a dictionary.

    Usage::

        @keyvalue("Spec", key_field="k", value_field="v", export_name="specs")
        class Page(BasePage):
            @fragment(".row", multiple=True)
            class Spec:
                k: str = ".key"
                v: str = ".val"

    Parameters
    ----------
    fragments_attr : str
        Name of the attribute holding the list of fragments.
    key_field : str
        Field name on the fragment to use as dictionary key. Default ``"key"``.
    value_field : str
        Field name on the fragment to use as dictionary value. Default ``"value"``.
    export_name : str or None
        Name under which the dictionary appears in ``export()``. If ``None``,
        *fragments_attr* is used.
    """

    def decorator(cls):
        def _dict_export(self):
            frags = getattr(self, fragments_attr)
            return {getattr(f, key_field): getattr(f, value_field) for f in frags}

        _dict_export.__name__ = export_name or fragments_attr

        if not hasattr(cls, "_pagemodel_export"):
            cls._pagemodel_export = []
        attr = export_name or fragments_attr
        cls._pagemodel_export.append((attr, attr))
        setattr(cls, attr, export(_dict_export))
        return cls

    return decorator
