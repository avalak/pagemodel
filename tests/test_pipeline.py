"""
Tests for the Pipe helper.
"""

from pagemodel.pipeline import Pipe


def add_one(x):
    return x + 1


def mul_two(x):
    return x * 2


class TestPipe:
    def test_single_function(self):
        p = Pipe(add_one)
        assert p(5) == 6

    def test_multiple_functions(self):
        p = Pipe(add_one, mul_two)
        assert p(5) == 12  # (5+1)*2

    def test_empty_pipe(self):
        p = Pipe()
        assert p(42) == 42

    def test_or_with_callable(self):
        p = Pipe(add_one) | mul_two
        assert p(5) == 12

    def test_or_with_pipe(self):
        p1 = Pipe(add_one)
        p2 = Pipe(mul_two)
        p = p1 | p2
        assert p(5) == 12
