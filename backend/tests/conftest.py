"""Keep backend regression tests offline; use transports/fixtures for providers."""
import socket

import pytest


@pytest.fixture(autouse=True)
def disable_network(monkeypatch):
    # 保留 AnyIO/TestClient 使用的本地 Unix socket；禁止 IPv4/IPv6 外连。
    def block_method(name):
        original = getattr(socket.socket, name)

        def guarded(client, *args, **kwargs):
            if client.family in (socket.AF_INET, socket.AF_INET6):
                pytest.fail("Network access is disabled in backend tests", pytrace=False)
            return original(client, *args, **kwargs)

        monkeypatch.setattr(socket.socket, name, guarded)

    for name in ("connect", "connect_ex", "sendto"):
        block_method(name)

    def block_dns(*args, **kwargs):
        pytest.fail("Network access is disabled in backend tests", pytrace=False)

    monkeypatch.setattr(socket, "getaddrinfo", block_dns)
