"""
Pipeline helpers – simple callable chains for field value conversion.

The core class is ``Pipe``, which wraps a sequence of callables and applies
them in order when called.  Pipes can be combined with the ``|`` operator.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ("Pipe",)


class Pipe:
    """A chain of callables that are applied sequentially.

    ``Pipe`` is used by field descriptors to implement the ``|`` syntax for
    inline converters.

    Usage::

        clean = Pipe(str.strip, str.lower)    # explicit Pipe
        field = Q(".price") | float           # built via __or__
        field = TextField(".price", converter=clean)
    """

    __slots__ = ("funcs",)

    def __init__(self, *funcs: Callable[[Any], Any]) -> None:
        self.funcs = funcs

    def __call__(self, value: Any) -> Any:
        """Apply the chain of callables to *value* and return the result.

        A fast path is taken when the pipe contains a single function.
        """
        if len(self.funcs) == 1:
            return self.funcs[0](value)
        for f in self.funcs:
            value = f(value)
        return value

    def __or__(self, other: Callable[[Any], Any]) -> Pipe:
        """Extend the pipeline with another callable (or Pipe)."""
        if isinstance(other, Pipe):
            return Pipe(*self.funcs, *other.funcs)
        return Pipe(*self.funcs, other)
