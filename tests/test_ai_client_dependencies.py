"""AIClient dependency compatibility tests."""

import sys
from types import SimpleNamespace

from litrx.ai_client import AIClient


def test_httpx_proxy_shim_rewrites_proxies_keyword():
    """httpx>=0.28 removal of 'proxies' should be auto-adapted."""

    capture: dict = {}

    class DummyClient:
        def __init__(self, *args, **kwargs):
            capture["client_kwargs"] = dict(kwargs)

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs):
            capture["async_kwargs"] = dict(kwargs)

    fake_httpx = SimpleNamespace(
        __version__="0.28.0",
        Client=DummyClient,
        AsyncClient=DummyAsyncClient,
    )

    AIClient._ensure_httpx_proxy_shim(fake_httpx)

    fake_httpx.Client(proxies="http://proxy.example")
    fake_httpx.AsyncClient(proxies={"https": "http://proxy.example"})

    assert capture["client_kwargs"].get("proxy") == "http://proxy.example"
    assert "proxies" not in capture["client_kwargs"]
    assert capture["async_kwargs"].get("proxy") == "http://proxy.example"
    assert "proxies" not in capture["async_kwargs"]


def test_validate_dependencies_handles_openai_v2(monkeypatch):
    """openai>=2 with httpx>=0.28 should not trigger NameError during validation."""

    capture: dict = {}

    class DummyClient:
        def __init__(self, *args, **kwargs):
            capture["shim_applied"] = dict(kwargs)

    fake_openai = SimpleNamespace(__version__="2.8.1")
    fake_httpx = SimpleNamespace(
        __version__="0.28.1",
        Client=DummyClient,
        AsyncClient=DummyClient,
    )

    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)

    # Should complete without raising NameError and install the shim for future calls
    AIClient._validate_dependencies()

    assert getattr(fake_httpx, "_litrx_proxy_shim_installed", False)
