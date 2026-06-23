#!/usr/bin/env python3
from pathlib import Path
import re
import sys

from mtproxy_phase_contract import (
    analyzer_failure_phases,
    analyzer_phase_names,
    endpoint_key_phases,
    java_phase_names,
    java_success_phases,
    java_visible_live_phases,
    native_phase_names,
    reconnect_backoff_phases,
    rotation_phases,
)


ROOT = Path(__file__).resolve().parents[1]

DIAGNOSTICS = ROOT / "TMessagesProj/src/main/java/org/telegram/messenger/ProxyCheckDiagnostics.java"
SCHEDULER = ROOT / "TMessagesProj/src/main/java/org/telegram/messenger/ProxyCheckScheduler.java"
SOCKET = ROOT / "TMessagesProj/jni/tgnet/ConnectionSocket.cpp"
SOCKET_H = ROOT / "TMessagesProj/jni/tgnet/ConnectionSocket.h"
CONNECTION = ROOT / "TMessagesProj/jni/tgnet/Connection.cpp"
ANALYZER = ROOT / "Tools/analyze_mtproxy_markers.py"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def require(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}", file=sys.stderr)
        sys.exit(1)


def java_constants(diagnostics: str) -> dict[str, str]:
    return dict(re.findall(r'public static final String ([A-Z0-9_]+)\s*=\s*"([a-z0-9_]+)"', diagnostics))


def method_body(source: str, start: str, end: str) -> str:
    start_index = source.find(start)
    if start_index < 0:
        return ""
    end_index = source.find(end, start_index + 1)
    return source[start_index:end_index if end_index >= 0 else len(source)]


def java_cases(source: str, constants: dict[str, str]) -> set[str]:
    return {
        constants[name]
        for name in re.findall(r'case (?:ProxyCheckDiagnostics\.)?([A-Z0-9_]+):', source)
        if name in constants
    }


def native_diagnostics(socket: str, socket_h: str) -> set[str]:
    phases = set(re.findall(r'publishProxyConnectionStage\("([a-z0-9_]+)"\)', socket))
    phases |= set(re.findall(r'proxyCheckDiagnostic\s*=\s*"([a-z0-9_]+)"', socket))
    phases |= set(re.findall(r'proxyCheckDiagnostic\s*=\s*"([a-z0-9_]+)"', socket_h))
    phases.discard("wss_tls_handshake")
    return phases


def string_set_in_block(source: str, start: str, end: str) -> set[str]:
    return set(re.findall(r'"([a-z0-9_]+)"', method_body(source, start, end)))


def analyzer_literal_set(analyzer: str, name: str) -> set[str]:
    match = re.search(rf"{name}\s*=\s*\{{(?P<body>.*?)\}}", analyzer, re.S)
    require(match is not None, f"analyzer must define {name}")
    return set(re.findall(r'"([a-z0-9_]+)"', match.group("body")))


def analyzer_verdict_returns(analyzer: str) -> set[str]:
    body = method_body(analyzer, "    def verdict(self) -> str:", "    def completed_tls_frames")
    return set(re.findall(r'return "([a-z0-9_]+)"', body))


def main() -> int:
    diagnostics = text(DIAGNOSTICS)
    scheduler = text(SCHEDULER)
    socket = text(SOCKET)
    socket_h = text(SOCKET_H)
    connection = text(CONNECTION)
    analyzer = text(ANALYZER)

    constants = java_constants(diagnostics)
    contract_java = java_phase_names()

    require(set(constants.values()) == contract_java, "ProxyCheckDiagnostics constants must match mtproxy_phase_contract")
    require(
        java_cases(method_body(diagnostics, "public static String normalize", "public static boolean isFailure"), constants) == contract_java,
        "ProxyCheckDiagnostics.normalize must accept exactly the contract Java phases",
    )
    require(
        java_cases(method_body(diagnostics, "public static boolean isLivePhase", "public static boolean isEarlyRetryPhase"), constants) == java_visible_live_phases(),
        "ProxyCheckDiagnostics.isLivePhase must match contract live/success phases",
    )
    require(
        java_cases(method_body(diagnostics, "public static boolean isProxyUsableSuccessPhase", "public static class HeaderStatusTitle"), constants) == java_success_phases(),
        "ProxyCheckDiagnostics.isProxyUsableSuccessPhase must match contract success phases",
    )
    require(
        java_cases(method_body(diagnostics, "public static boolean shouldAccelerateProxyRotation", "public static boolean shouldKeepFreshFailure"), constants) == rotation_phases(),
        "ProxyCheckDiagnostics.shouldAccelerateProxyRotation must match contract rotation phases",
    )
    require(
        java_cases(method_body(scheduler, "private static String endpointStateKeyForDiagnostic", "private static EndpointState latestEndpointState"), constants) == endpoint_key_phases("network"),
        "ProxyCheckScheduler.endpointStateKeyForDiagnostic must match contract network-key phases",
    )
    require(
        native_diagnostics(socket, socket_h) == native_phase_names(),
        "native MTProxy diagnostics must match contract native phases",
    )
    require(
        string_set_in_block(connection, "static bool mtProxyDiagnosticNeedsReconnectBackoff", "static uint32_t mtProxyReconnectBackoffBaseMs") == reconnect_backoff_phases(),
        "Connection.mtProxyDiagnosticNeedsReconnectBackoff must match contract reconnect phases",
    )
    require(
        analyzer_literal_set(analyzer, "FAKETLS_FAILURE_VERDICTS") == analyzer_failure_phases(),
        "analyzer FakeTLS failure verdicts must match contract analyzer failure phases",
    )
    require(
        analyzer_literal_set(analyzer, "NON_FAILURE_VERDICTS") <= analyzer_phase_names(),
        "analyzer non-failure verdicts must be declared in the contract",
    )
    require(
        analyzer_verdict_returns(analyzer) <= analyzer_phase_names(),
        "Attempt.verdict returns must be declared in the contract",
    )

    print("MTProxy phase contract guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
