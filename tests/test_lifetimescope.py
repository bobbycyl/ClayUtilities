import pytest

from clayutil.putil import LifetimeError, LifetimeScope


def test_normal():
    with LifetimeScope("a", label="Lifetime_A", print_result=True) as lifetime:
        a = "a"
        b = a + "b"
        c = lifetime.track("c", b + "c")
        assert c == "abc"
        print(lifetime._unbind)
    with pytest.raises(LifetimeError, match="cannot access dead variable 'a'"):
        str(a)
    with pytest.raises(LifetimeError, match="cannot access dead variable 'c'"):
        _ = c.some_attribute
    assert b == "ab"


def test_func():
    test_normal()
