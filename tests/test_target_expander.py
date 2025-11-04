# tests/test_target_expander.py
from tests.fakes import FakeTargetExpander


def test_expand_default_ports():
    e = FakeTargetExpander([80, 443])
    out = e.expand(["a.com"], None)
    assert ("a.com", 80) in out and ("a.com", 443) in out


def test_expand_custom_ports():
    e = FakeTargetExpander([80])
    out = e.expand(["a.com"], [8080])
    assert out == [("a.com", 8080)]
