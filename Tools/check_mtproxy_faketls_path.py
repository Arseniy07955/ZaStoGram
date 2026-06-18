#!/usr/bin/env python3
"""Static guard for the active MTProxy FakeTLS transport path.

The working reference is tsrman/tg commit 9fe18931 for the risky fingerprint
parts: direct Firefox ClientHello, whole ClientHello send, and the original
fixed TLS record cap for wrapped data. The Android transport adds nonblocking
startup pacing, startup diagnostics, and a TLS write queue so MTProto payload
bytes are not discarded until the full TLS record has been sent.
"""

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
CPP = ROOT / "TMessagesProj/jni/tgnet/ConnectionSocket.cpp"
HDR = ROOT / "TMessagesProj/jni/tgnet/ConnectionSocket.h"


def main() -> int:
    cpp = CPP.read_text(encoding="utf-8")
    header = HDR.read_text(encoding="utf-8")
    combined = cpp + "\n" + header
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    require(
        "TlsHello hello = TlsHello::getFirefoxDefault();" in cpp,
        "FakeTLS handshake must instantiate getFirefoxDefault() directly",
    )
    require(
        not re.search(r"\bTlsHello\s+TlsHello::pickProfile\s*\(", cpp),
        "FakeTLS profile wrapper must stay out of the active transport path",
    )
    require(
        "randomizeGrease" not in cpp and "randomizeGrease" not in header,
        "per-connection GREASE rewrite must stay disabled until server path is proven",
    )
    require(
        "send(socketFd, tempBuffer->bytes, size, 0)" in cpp,
        "ClientHello must be sent whole like the working tsrman path",
    )
    require(
        "remaining > 2878" in cpp,
        "wrapped data path must keep the original fixed TLS record cap",
    )
    require(
        "nextTlsRecordSize" not in combined
        and "tlsRecordRemaining" not in combined
        and "drs" not in combined.lower(),
        "dynamic record sizing must stay removed from the transport path",
    )
    require(
        "nanosleep(&ts, nullptr);" not in cpp,
        "proxy pacing must not block the network thread",
    )
    require(
        "scheduleProxyPacingIfNeeded" in combined
        and "cancelProxyPacing" in combined
        and "Timer *proxyPacingTimer" in header
        and '#include "Timer.h"' in cpp,
        "proxy pacing must use a cancellable nonblocking Timer",
    )
    require(
        "pacingDeferred" not in combined,
        "old deferred pacing path must stay out of MTProxy connect",
    )
    require(
        "mtproxy_startup connect_start" in cpp
        and "mtproxy_startup socket_connected" in cpp
        and "mtproxy_startup client_hello_sent" in cpp
        and "mtproxy_startup server_hello_hmac_ok" in cpp
        and "mtproxy_startup on_connected" in cpp
        and "mtproxy_disconnect" in cpp,
        "MTProxy startup diagnostics must cover connect, TLS handshake, connected, and disconnect",
    )
    require(
        "pendingTlsFrame" in combined
        and "sendPendingTlsFrame" in combined
        and "clearPendingTlsFrame" in combined,
        "TLS writes must keep a pending frame for partial-send handling",
    )

    if errors:
        print("MTProxy FakeTLS path check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("MTProxy FakeTLS path check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
