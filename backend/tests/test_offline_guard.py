"""The offline suite must reject real network access before any I/O."""
import socket

import pytest


@pytest.mark.parametrize("family", [socket.AF_INET, socket.AF_INET6])
@pytest.mark.parametrize("method", ["connect", "connect_ex", "sendto"])
def test_network_io_is_blocked(family, method):
    address = ("192.0.2.1", 9) if family == socket.AF_INET else ("2001:db8::1", 9)
    kind = socket.SOCK_DGRAM if method == "sendto" else socket.SOCK_STREAM
    with socket.socket(family, kind) as client:
        args = (b"test", address) if method == "sendto" else (address,)
        with pytest.raises(pytest.fail.Exception, match="Network access is disabled"):
            getattr(client, method)(*args)


def test_dns_is_blocked():
    with pytest.raises(pytest.fail.Exception, match="Network access is disabled"):
        socket.getaddrinfo("offline.invalid", 443)
