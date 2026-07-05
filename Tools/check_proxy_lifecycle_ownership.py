#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
MESSENGER = ROOT / "TMessagesProj/src/main/java/org/telegram/messenger"
TGNET_JAVA = ROOT / "TMessagesProj/src/main/java/org/telegram/tgnet"
JNI = ROOT / "TMessagesProj/jni"
TGNET = JNI / "tgnet"
RUNTIME_LOG_VERIFIER = ROOT / "Tools/verify_mtproxy_runtime_logs.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def method_body(text: str, signature: str) -> str:
    start = text.find(signature)
    if start == -1:
        return ""
    brace = text.find("{", start)
    if brace == -1:
        return ""
    depth = 0
    for index in range(brace, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    return text[start:]


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def ordered(body: str, *needles: str) -> bool:
    cursor = -1
    for needle in needles:
        index = body.find(needle, cursor + 1)
        if index == -1:
            return False
        cursor = index
    return True


def runtime_lines(proxy_control_tail: str) -> str:
    return (
        "\n".join(
            [
                "logcat.txt:1: 06-25 20:31:30.000 connection(0x1) connecting via proxy sberbank.dns.army:45631 secret[34] secret_kind=ee",
                proxy_control_tail,
                "logcat.txt:10: 06-25 20:31:31.000 connection(0x1) mtproxy_disconnect transport_state=closed epoll_registered=0 admission_active=0 tcp_gate_active=0",
                "logcat.txt:11: 06-25 20:31:31.010 connection(0x1) mtproxy_startup server_hello_hmac_ok bytes=196 len1=122 len2=58 flight=58 extra=0",
                "logcat.txt:12: 06-25 20:31:31.020 connection(0x1) mtproxy_startup endpoint_handshake_ok reason=server_hello_hmac_ok",
                "logcat.txt:13: 06-25 20:31:31.030 connection(0x1) mtproxy_startup first_tls_app_recv payload=1015",
                "logcat.txt:14: 06-25 20:31:31.040 connection(0x1) mtproxy_startup endpoint_data_path_success network_key=sberbank.dns.army:45631 key=sberbank.dns.army:45631:ee:sberbank.dns.army reason=first_tls_app_recv",
            ]
        )
        + "\n"
    )


def run_runtime_log_checks(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        session = Path(tmp)
        media_visible_bad = session / "media_visible_bad_markers.txt"
        media_visible_good = session / "media_visible_good_markers.txt"
        startup_visible_bad = session / "startup_visible_bad_markers.txt"
        startup_visible_good = session / "startup_visible_good_markers.txt"
        background_rotation_bad = session / "background_rotation_bad_markers.txt"
        background_rotation_good = session / "background_rotation_good_markers.txt"
        control_secondary_bad = session / "control_secondary_bad_markers.txt"
        control_secondary_good = session / "control_secondary_good_markers.txt"
        media_visible_bad.write_text(
            runtime_lines(
                "logcat.txt:2: 06-25 20:31:30.010 proxy_control owner=ProxyEventReducer.reduce decision=visible_only source=native_stage origin=user_select role=media_visible account=0 phase=socket_connected endpoint=sberbank.dns.army:45631:ee:sberbank.dns.army activation_generation=71"
            ),
            encoding="utf-8",
        )
        media_visible_good.write_text(
            runtime_lines(
                "logcat.txt:2: 06-25 20:31:30.010 proxy_control owner=ProxyEventReducer.reduce decision=lifecycle_health_only source=native_stage origin=user_select role=media_visible account=0 phase=socket_connected endpoint=sberbank.dns.army:45631:ee:sberbank.dns.army visible_owner=0 rotation_owner=0 activation_generation=71"
            ),
            encoding="utf-8",
        )
        startup_visible_bad.write_text(
            runtime_lines(
                "logcat.txt:2: 06-25 20:31:30.010 proxy_control owner=ProxyEventReducer.reduce decision=visible_only source=native_stage origin=startup_restore role=startup_restore account=2 phase=mtproxy_probe_wait endpoint=sberbank.dns.army:45631:ee:sberbank.dns.army activation_generation=31"
            ),
            encoding="utf-8",
        )
        startup_visible_good.write_text(
            runtime_lines(
                "logcat.txt:2: 06-25 20:31:30.010 proxy_control owner=ProxyEventReducer.reduce decision=lifecycle_health_only source=native_stage origin=startup_restore role=startup_restore account=2 phase=mtproxy_probe_wait endpoint=sberbank.dns.army:45631:ee:sberbank.dns.army visible_owner=0 rotation_owner=0 activation_generation=31"
            ),
            encoding="utf-8",
        )
        background_rotation_bad.write_text(
            runtime_lines(
                "logcat.txt:2: 06-25 20:31:30.010 proxy_control owner=ProxyEventReducer.reduce decision=rotation_trigger source=native_stage origin=background_keepalive role=background_keepalive account=0 phase=post_handshake_no_appdata endpoint=sberbank.dns.army:45631:ee:sberbank.dns.army visible_owner=0 rotation_owner=0 activation_generation=88"
            ),
            encoding="utf-8",
        )
        background_rotation_good.write_text(
            runtime_lines(
                "logcat.txt:2: 06-25 20:31:30.010 proxy_control owner=ProxyEventReducer.reduce decision=lifecycle_data_path_timeout_telemetry_only source=native_stage origin=background_keepalive role=background_keepalive account=0 phase=post_handshake_no_appdata endpoint=sberbank.dns.army:45631:ee:sberbank.dns.army visible_owner=0 rotation_owner=0 activation_generation=88"
            ),
            encoding="utf-8",
        )
        control_secondary_bad.write_text(
            runtime_lines(
                "logcat.txt:2: 06-25 20:31:30.010 proxy_control owner=ProxyEventReducer.reduce decision=backoff source=native_stage origin=active_socket role=control_secondary account=0 phase=tcp_connect_timeout endpoint=sberbank.dns.army:45631:ee:sberbank.dns.army visible_owner=0 rotation_owner=0 activation_generation=89"
            ),
            encoding="utf-8",
        )
        control_secondary_good.write_text(
            runtime_lines(
                "logcat.txt:2: 06-25 20:31:30.010 proxy_control owner=ProxyEventReducer.reduce decision=lifecycle_health_only source=native_stage origin=active_socket role=control_secondary account=0 phase=tcp_connect_timeout endpoint=sberbank.dns.army:45631:ee:sberbank.dns.army visible_owner=0 rotation_owner=0 activation_generation=89"
            ),
            encoding="utf-8",
        )

        bad_result = subprocess.run(
            [sys.executable, str(RUNTIME_LOG_VERIFIER), str(media_visible_bad)],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        require(
            bad_result.returncode != 0
            and "non-control socket role mirrored as active visible status" in bad_result.stderr,
            "runtime log verifier must reject visible_only from USER_SELECT/SETTINGS_CHANGE/ROTATION_CANDIDATE when socket role is media/download",
            failures,
        )

        good_result = subprocess.run(
            [sys.executable, str(RUNTIME_LOG_VERIFIER), str(media_visible_good)],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        require(
            good_result.returncode == 0,
            good_result.stderr.strip() or "runtime log verifier must allow non-control visible-origin events only as lifecycle_health_only",
            failures,
        )
        for path, expected_messages in (
            (startup_visible_bad, ("non-visible origin mirrored as active visible status", "lifecycle health-only event reached visible/backoff/rotation path")),
            (background_rotation_bad, ("lifecycle health-only event reached visible/backoff/rotation path",)),
            (control_secondary_bad, ("lifecycle health-only event reached visible/backoff/rotation path",)),
        ):
            result = subprocess.run(
                [sys.executable, str(RUNTIME_LOG_VERIFIER), str(path)],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            require(
                result.returncode != 0 and any(expected in result.stderr for expected in expected_messages),
                f"runtime log verifier must reject lifecycle visible/backoff/rotation path in {path.name}",
                failures,
            )
        for path in (startup_visible_good, background_rotation_good, control_secondary_good):
            result = subprocess.run(
                [sys.executable, str(RUNTIME_LOG_VERIFIER), str(path)],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            require(
                result.returncode == 0,
                result.stderr.strip() or f"runtime log verifier must allow lifecycle health-only path in {path.name}",
                failures,
            )


def main() -> int:
    failures: list[str] = []

    event = read(MESSENGER / "ProxyConnectionEvent.java")
    reducer = read(MESSENGER / "ProxyEventReducer.java")
    runtime = read(MESSENGER / "ProxyRuntimeStateStore.java")
    visible = read(MESSENGER / "ProxyVisibleStateStore.java")
    health = read(MESSENGER / "ProxyHealthStore.java")
    rotation = read(MESSENGER / "ProxyRotationController.java")
    rotation_engine = read(MESSENGER / "ProxyRotationEngine.java")
    connections_java = read(TGNET_JAVA / "ConnectionsManager.java")
    defines = read(TGNET / "Defines.h")
    wrapper = read(JNI / "TgNetWrapper.cpp")
    connection = read(TGNET / "Connection.cpp")
    socket_h = read(TGNET / "ConnectionSocket.h")
    socket_cpp = read(TGNET / "ConnectionSocket.cpp")
    all_checks = read(ROOT / "Tools/check_mtproxy_all.py")
    verifier = read(ROOT / "Tools/verify_mtproxy_runtime_logs.py")
    strings = read(ROOT / "TMessagesProj/src/main/res/values/strings.xml")
    strings_ru = read(ROOT / "TMessagesProj/src/main/res/values-ru/strings.xml")

    require("enum SocketRole" in event, "ProxyConnectionEvent must expose SocketRole", failures)
    require("final SocketRole socketRole" in event, "ProxyConnectionEvent must carry socketRole on every event", failures)
    require("SocketRole.fromNative" in event, "ProxyConnectionEvent must parse native socketRole", failures)
    require("canDriveVisible(ProxyConnectionEvent event)" in event, "ProxyConnectionEvent must expose canDriveVisible(event)", failures)
    require("canDriveRotation(ProxyConnectionEvent event, ProxyEndpointVerdict verdict)" in event, "ProxyConnectionEvent must expose canDriveRotation(event, verdict)", failures)
    require("isLifecycleHealthOnly(ProxyConnectionEvent event)" in event, "ProxyConnectionEvent must expose isLifecycleHealthOnly(event)", failures)
    require("isHealthOrigin" in event and "isVisibleOwnerOrigin" in event and "isRotationOwnerOrigin" in event, "origin helpers must be split into health/visible/rotation roles", failures)

    active_body = method_body(event, "public static boolean isActiveProxyOrigin")
    can_visible_body = method_body(event, "public static boolean canDriveVisible")
    lifecycle_health_body = method_body(event, "public static boolean isLifecycleHealthOnly")
    require("case STARTUP_RESTORE:" not in active_body and "case BACKGROUND_KEEPALIVE:" not in active_body, "isActiveProxyOrigin must not classify startup/background as active visible owners", failures)
    require("ApplicationLoader.mainInterfacePaused" in event and "UserConfig.selectedAccount" in event, "ACTIVE_SOCKET visibility must require foreground selected account", failures)
    require("SocketRole.CONTROL_MAIN" in event, "visible ownership must require CONTROL_MAIN role", failures)
    require(
        "isHealthOrigin(event.origin)" in lifecycle_health_body
        and "!canDriveVisible(event)" in lifecycle_health_body,
        "lifecycle health-only classification must be split from visible ownership",
        failures,
    )
    role_gate_idx = can_visible_body.find("isControlMainRole(event)")
    origin_switch_idx = can_visible_body.find("switch (event.origin)")
    require(
        role_gate_idx >= 0 and origin_switch_idx >= 0 and role_gate_idx < origin_switch_idx,
        "visible ownership must require CONTROL_MAIN before any USER_SELECT/SETTINGS_CHANGE/ROTATION_CANDIDATE origin can drive UI",
        failures,
    )

    reduce_body = method_body(reducer, "static ProxyRuntimeStateStore.Decision reduce")
    require("boolean visibleOwner = ProxyConnectionEvent.canDriveVisible(event)" in reduce_body, "ProxyEventReducer must compute visibleOwner from event role/origin", failures)
    require("boolean rotationOwner = ProxyConnectionEvent.canDriveRotation(event, verdict)" in reduce_body, "ProxyEventReducer must compute rotationOwner from event role/origin", failures)
    require("boolean lifecycleHealthOnly = ProxyConnectionEvent.isLifecycleHealthOnly(event)" in reduce_body, "ProxyEventReducer must compute lifecycleHealthOnly from event role/origin", failures)
    require(
        ordered(
            reduce_body,
            "ProxyRuntimeStateStore.shouldIgnoreStaleActivationGeneration(event)",
            "if (ProxyConnectionEvent.SOURCE_CONNECTED.equals(event.source))",
            "if (ProxyConnectionEvent.SOURCE_CONNECT_START.equals(event.source))",
            "if (ProxyConnectionEvent.SOURCE_USABLE_SUCCESS.equals(event.source))",
        ),
        "ProxyEventReducer must run stale-generation guard before Java synthetic fast paths",
        failures,
    )
    require("decision=lifecycle_health_only" in reduce_body, "lifecycle events must return lifecycle_health_only before visible/backoff paths", failures)
    resume_grace_visible_idx = reduce_body.find("shouldKeepVisibleOwnerInResumeGraceTelemetryOnly(event, verdict)")
    visible_mirror_idx = reduce_body.find("ProxyVisibleStateStore.mirrorVisiblePhaseIfAllowed")
    require(
        resume_grace_visible_idx >= 0
        and visible_mirror_idx >= 0
        and resume_grace_visible_idx < visible_mirror_idx,
        "foreground ACTIVE_SOCKET phases inside resume grace must stay health-only until a control_main event confirms them after the grace window",
        failures,
    )
    require("ProxyHealthStore.rememberLifecycleTelemetry(currentProxy, event, verdict)" in reduce_body, "lifecycle events must record health telemetry without visible mutation", failures)
    require("rotation_suppressed_by_lifecycle_origin" in reduce_body, "reducer must log suppressed lifecycle rotation attempts", failures)
    require("rotationOwner && verdict.canRotate" in reduce_body, "rotation trigger must require rotationOwner", failures)

    usable_body = method_body(reducer, "private static ProxyRuntimeStateStore.Decision applyVisibleUsableSuccess")
    require("ProxyConnectionEvent.canDriveVisible(event)" in usable_body, "usable success must be visible only for visible owners", failures)
    connect_start_body = method_body(reducer, "private static ProxyRuntimeStateStore.Decision reduceConnectStart")
    require("ProxyConnectionEvent.canDriveVisible(event)" in connect_start_body, "connect_start must be visible only for visible owners", failures)
    connected_body = method_body(reducer, "private static ProxyRuntimeStateStore.Decision reduceConnected")
    require("ProxyConnectionEvent.canDriveVisible(event)" in connected_body, "connected state must be visible only for visible owners", failures)

    require("visibleActivationGenerationFloor" in runtime, "runtime store must maintain a global visible-owner generation floor", failures)
    mark_connected_body = method_body(runtime, "public static void markConnected")
    mark_starting_body = method_body(runtime, "public static void markConnectionStarting(SharedConfig.ProxyInfo proxyInfo, ProxyConnectionEvent.Origin origin)")
    mark_usable_default_body = method_body(runtime, "public static void markConnectionUsable(SharedConfig.ProxyInfo proxyInfo, String diagnostic, long now)")
    require("currentActivationGenerationForEvent" in runtime, "runtime store must expose current generation for Java synthetic events", failures)
    require("currentActivationGenerationForEvent(" in mark_connected_body, "Java connected synthetic event must carry current activation generation", failures)
    require("currentActivationGenerationForEvent(" in mark_starting_body, "Java connect_start synthetic event must carry current activation generation", failures)
    require("currentActivationGenerationForEvent(" in mark_usable_default_body, "Java usable_success synthetic event must carry current activation generation by default", failures)
    stale_body = method_body(runtime, "static boolean shouldIgnoreStaleActivationGeneration")
    require("visibleActivationGenerationFloor" in stale_body, "stale generation guard must include visible-owner floor", failures)
    require("ProxyConnectionEvent.canDriveVisible(event)" in stale_body or "ProxyConnectionEvent.canDriveRotation(event" in stale_body, "stale generation guard must account for visible/rotation owners", failures)
    require("noteResumeForeground" in runtime and "isResumeGrace" in runtime, "runtime store must expose foreground resume grace", failures)
    require("shouldShowResumeRestoringStatus" in runtime, "runtime store must expose resume-recovery UI masking for stale/lifecycle phases", failures)
    require("public static ProxyHealthStore.EndpointFailureResult markEndpointFailure" not in runtime, "ProxyRuntimeStateStore must not expose legacy public markEndpointFailure bypass", failures)
    require("public static boolean shouldScheduleFallback" not in runtime, "ProxyRuntimeStateStore must not expose legacy public shouldScheduleFallback bypass", failures)
    require("ProxyRuntimeStateStore.markEndpointFailure(" not in rotation_engine, "ProxyRotationEngine must not bypass reducer with legacy markEndpointFailure", failures)
    require("ProxyRuntimeStateStore.shouldScheduleFallback(" not in rotation, "ProxyRotationController must not bypass reducer with legacy shouldScheduleFallback", failures)
    require("ProxyRuntimeStateStore.onRuntimeEvent(event)" in rotation_engine, "ProxyRotationEngine must run connecting timeout through ProxyConnectionEvent reducer", failures)
    require("currentActivationGenerationForEvent" in rotation_engine, "ProxyRotationEngine connecting timeout event must carry current activation generation", failures)
    require("decision.decision" in connections_java and "decision.rotationTrigger" in connections_java, "ConnectionsManager must post reducer decision and rotationTrigger with proxy stage notifications", failures)
    require("proxy_diagnosis owner=ConnectionsManager.onProxyConnectionStageChanged" in connections_java, "ConnectionsManager must emit a compact proxy_diagnosis line for visible decisions", failures)
    require("role=\" + event.socketRole.wireName" in connections_java, "proxy_diagnosis must include socket role", failures)
    require("layer=\" + decision.verdict.layer" in connections_java, "proxy_diagnosis must include verdict layer", failures)
    require("failure_class=\" + decision.verdict.failureClass" in connections_java, "proxy_diagnosis must include failure class", failures)
    require("decision=\" + decision.decision" in connections_java, "proxy_diagnosis must include reducer decision", failures)
    require("last_success_age_ms=\" + lastSuccessAgeMs" in connections_java, "proxy_diagnosis must include last usable-success age", failures)
    require("reducerDecision" in rotation and "rotationTrigger" in rotation, "ProxyRotationController must consume reducer decision instead of re-deriving fallback policy", failures)

    require("rememberLifecycleTelemetry(SharedConfig.ProxyInfo proxyInfo, ProxyConnectionEvent event, ProxyEndpointVerdict verdict)" in health, "ProxyHealthStore must remember lifecycle telemetry separately", failures)
    require("rememberBackgroundUsableSuccess" in health, "ProxyHealthStore must remember background usable success without visible success", failures)

    mark_start = method_body(visible, "static boolean markConnectionStarting")
    require("origin == ProxyConnectionEvent.Origin.STARTUP_RESTORE" not in mark_start, "STARTUP_RESTORE must not be force-visible in markConnectionStarting", failures)
    schedule_dns = method_body(visible, "static void scheduleDnsVisiblePhase")
    promote_dns = method_body(visible, "private static void promotePendingDnsVisiblePhase")
    require("pendingDnsVisibleOrigin" in visible and "pendingDnsVisibleActivationGeneration" in visible and "pendingDnsVisibleSocketRole" in visible, "delayed DNS must store origin, generation and role", failures)
    require("ProxyConnectionEvent.canDriveVisible" in promote_dns, "delayed DNS promotion must re-check visible ownership", failures)
    stale_dns_idx = promote_dns.find("ProxyRuntimeStateStore.shouldIgnoreStaleActivationGeneration(event)")
    mirror_dns_idx = promote_dns.find("ProxyStatusMirror.mirrorVisiblePhase")
    require(
        stale_dns_idx >= 0 and mirror_dns_idx >= 0 and stale_dns_idx < mirror_dns_idx,
        "delayed DNS promotion must run stale-generation guard before mirroring visible state",
        failures,
    )
    require("event.activationGeneration" in promote_dns and "event.socketRole.wireName" in promote_dns, "delayed DNS notification must post generation and role", failures)

    rotation_stage = rotation[rotation.find("NotificationCenter.proxyConnectionStageChanged"):]
    require("SocketRole.fromNative" in rotation_stage or "event.socketRole" in rotation_stage, "ProxyRotationController must read socket role from notification", failures)
    require("ProxyConnectionEvent.canDriveRotation(event" in rotation_stage, "ProxyRotationController must suppress non-rotation-owner events", failures)

    require("std::string socketRole" in defines and "onProxyConnectionStageChanged" in defines, "native delegate must expose socket role", failures)
    require("proxyConnectionStageSocketRole" in socket_h and "proxyConnectionStageSocketRole" in socket_cpp, "ConnectionSocket must expose proxyConnectionStageSocketRole", failures)
    require("Connection::proxyConnectionStageSocketRole" in connection, "Connection must map ConnectionType to socket role", failures)
    require("\"control_main\"" in connection and "\"media_visible\"" in connection and "\"background_keepalive\"" in connection and "\"proxy_check\"" in connection, "native role mapping must cover control/media/background/proxy_check", failures)
    require("socketRoleString" in wrapper and "(ILjava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;II)V" in wrapper, "JNI proxy stage callback must forward socket role", failures)
    require("final String socketRole" in connections_java and "event.socketRole.wireName" in connections_java, "Java ConnectionsManager callback must receive and post socket role", failures)

    require("owner=" in runtime and "owner=" in reducer and "owner=" in health and "owner=" in visible and "owner=" in rotation and "owner=ConnectionsManager.onProxyConnectionStageChanged" in connections_java, "decision logs must include owner provenance", failures)
    require("role=" in reducer and "role=" in rotation and "role=" in connections_java, "decision/stage logs must include socket role", failures)
    require("owner" in verifier and "lifecycle_health_only" in verifier and "rotation_suppressed_by_lifecycle_origin" in verifier, "runtime verifier must understand owner and lifecycle decisions", failures)

    require("Восстанавливаем соединение через прокси" in strings_ru and "Restoring proxy connection" in strings, "UI strings must include resume/startup restoring text", failures)
    diagnostics = read(MESSENGER / "ProxyCheckDiagnostics.java")
    status_text = method_body(diagnostics, "public static String statusText")
    header_text = method_body(diagnostics, "public static String headerStatusText")
    for body, name in ((status_text, "statusText"), (header_text, "headerStatusText")):
        resume_idx = body.find("ProxyRuntimeStateStore.shouldShowResumeRestoringStatus(proxyInfo")
        failure_idx = body.find("hasFreshFailure(proxyInfo)")
        live_idx = body.find("hasFreshLivePhase(proxyInfo)")
        require(
            resume_idx >= 0
            and failure_idx >= 0
            and live_idx >= 0
            and resume_idx < failure_idx
            and resume_idx < live_idx,
            f"{name} must show restoring proxy before stale/lifecycle failure or live phase text during resume recovery",
            failures,
        )
    require("data-path" in strings and "data-path" in strings_ru and "Прокси доступен на TCP" in strings_ru, "data-path timeout copy must mention TCP reachability and data-path", failures)
    require('"check_proxy_lifecycle_ownership.py"' in all_checks, "full guard suite must include lifecycle ownership guard", failures)
    run_runtime_log_checks(failures)

    if failures:
        print("Proxy lifecycle ownership guard failed:")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("Proxy lifecycle ownership guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
