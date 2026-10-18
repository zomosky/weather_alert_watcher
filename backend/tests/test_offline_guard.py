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


@pytest.mark.skipif(not hasattr(socket.socket, "sendmsg"), reason="sendmsg is not available")
@pytest.mark.parametrize("family", [socket.AF_INET, socket.AF_INET6])
def test_destination_bearing_sendmsg_is_blocked(family):
    # 回归失败时仅可能发送到本机，不接触外部网络。
    address = ("127.0.0.1", 9) if family == socket.AF_INET else ("::1", 9)
    with socket.socket(family, socket.SOCK_DGRAM) as client:
        with pytest.raises(pytest.fail.Exception, match="Network access is disabled"):
            client.sendmsg([b"test"], [], 0, address)


def test_unix_socket_ipc_remains_available():
    sender, receiver = socket.socketpair()
    with sender, receiver:
        sender.sendall(b"test")
        assert receiver.recv(4) == b"test"


@pytest.mark.skipif(not hasattr(socket.socket, "sendmsg"), reason="sendmsg is not available")
def test_unix_sendmsg_remains_available():
    sender, receiver = socket.socketpair()
    with sender, receiver:
        assert sender.sendmsg([b"test"]) == 4
        assert receiver.recv(4) == b"test"
