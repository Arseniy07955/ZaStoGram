package org.telegram.messenger;

public final class ProxyPhasePolicy {
    public static final String EVIDENCE_NONE = "none";
    public static final String EVIDENCE_PRE_TCP_LOCAL_WAIT = "pre_tcp_local_wait";
    public static final String EVIDENCE_DNS_FAILURE = "dns_failure";
    public static final String EVIDENCE_TCP_FAILURE = "tcp_failure";
    public static final String EVIDENCE_NO_BYTES_AFTER_CLIENT_HELLO = "no_bytes_after_client_hello";
    public static final String EVIDENCE_SERVER_BYTES_PARSER_FAILURE = "server_bytes_parser_failure";
    public static final String EVIDENCE_SERVER_HELLO_HMAC_MISMATCH = "server_hello_hmac_mismatch";
    public static final String EVIDENCE_POST_HANDSHAKE_NO_APP_DATA = "post_handshake_no_app_data";
    public static final String EVIDENCE_CONFIG_INVALID_SECRET = "config_invalid_secret";
    public static final String EVIDENCE_CANCELLED_OR_SHADOWED = "cancelled_or_shadowed";

    public enum Kind {
        NEUTRAL,
        LIVE,
        SUCCESS,
        FAILURE
    }

    public enum KeyScope {
        NONE,
        EXACT,
        NETWORK
    }

    private static final PhaseInfo NEUTRAL_NONE = new PhaseInfo(Kind.NEUTRAL, KeyScope.NONE, false, false, true, false, false);

    private ProxyPhasePolicy() {
    }

    public static Kind kind(String phase) {
        return classify(phase).kind;
    }

    public static KeyScope keyScope(String phase) {
        return classify(phase).keyScope;
    }

    public static boolean canBackoff(String phase) {
        return classify(phase).canBackoff;
    }

    public static boolean canRotate(String phase) {
        return classify(phase).canRotate;
    }

    public static boolean isPunitiveFailure(String phase) {
        switch (ProxyCheckDiagnostics.normalize(phase)) {
            case ProxyCheckDiagnostics.TCP_NOT_CONNECTED:
            case ProxyCheckDiagnostics.HOST_RESOLVE_FAILED:
            case ProxyCheckDiagnostics.HOST_RESOLVE_TIMEOUT:
            case ProxyCheckDiagnostics.TCP_CONNECTED_NO_PONG:
            case ProxyCheckDiagnostics.SECRET_PARSE_INVALID_DOMAIN_CONTROL_CHAR:
            case ProxyCheckDiagnostics.SECRET_PARSE_INVALID_DOMAIN:
            case ProxyCheckDiagnostics.HANDSHAKE_PROFILES_EXHAUSTED:
            case ProxyCheckDiagnostics.MTPROXY_PACKET_SENT_NO_RESPONSE:
            case ProxyCheckDiagnostics.POST_HANDSHAKE_NO_APPDATA:
            case ProxyCheckDiagnostics.DROPPED_EARLY_AFTER_APPDATA:
                return true;
            default:
                return false;
        }
    }

    public static boolean isLocalOrLiveNonPunitive(String phase) {
        return isLivePhase(phase)
                || !canBackoff(phase)
                || (!canRotate(phase) && !terminalExactConfig(phase));
    }

    public static boolean canOverwriteVisible(String phase) {
        return classify(phase).canOverwriteVisible;
    }

    public static boolean usableSuccess(String phase) {
        return classify(phase).usableSuccess;
    }

    public static boolean terminalExactConfig(String phase) {
        return isTerminalExactConfigPhase(phase);
    }

    public static boolean isLivePhase(String phase) {
        Kind kind = kind(phase);
        return kind == Kind.LIVE || kind == Kind.SUCCESS;
    }

    public static boolean isFailure(String phase) {
        return kind(phase) == Kind.FAILURE;
    }

    public static boolean isOneShotTerminal(String phase) {
        switch (ProxyCheckDiagnostics.normalize(phase)) {
            case ProxyCheckDiagnostics.SECRET_PARSE_INVALID_DOMAIN_CONTROL_CHAR:
            case ProxyCheckDiagnostics.SECRET_PARSE_INVALID_DOMAIN:
                return true;
            default:
                return false;
        }
    }

    public static String evidenceForPhase(String phase) {
        switch (ProxyCheckDiagnostics.normalize(phase)) {
            case ProxyCheckDiagnostics.CONNECTION_NOT_STARTED:
            case ProxyCheckDiagnostics.ADMISSION_TIMEOUT:
            case ProxyCheckDiagnostics.ENDPOINT_COOLDOWN_TIMEOUT:
            case ProxyCheckDiagnostics.MTPROXY_PROBE_WAIT_TIMEOUT:
            case ProxyCheckDiagnostics.DNS_COALESCE_TIMEOUT:
            case ProxyCheckDiagnostics.TCP_CONNECT_GATE_TIMEOUT:
            case ProxyCheckDiagnostics.CONNECTING_TIMEOUT:
                return EVIDENCE_PRE_TCP_LOCAL_WAIT;

            case ProxyCheckDiagnostics.DNS_NEGATIVE_CACHE_HIT:
            case ProxyCheckDiagnostics.DNS_BLOCKED_ZERO_ADDRESS:
            case ProxyCheckDiagnostics.HOST_RESOLVE_FAILED:
            case ProxyCheckDiagnostics.HOST_RESOLVE_TIMEOUT:
                return EVIDENCE_DNS_FAILURE;

            case ProxyCheckDiagnostics.TCP_NOT_CONNECTED:
            case ProxyCheckDiagnostics.TCP_CONNECTED_NO_PONG:
            case ProxyCheckDiagnostics.NETWORK_BLOCK_SUSPECTED:
                return EVIDENCE_TCP_FAILURE;

            case ProxyCheckDiagnostics.TRUE_CLIENT_HELLO_TIMEOUT:
            case ProxyCheckDiagnostics.FAKETLS_SERVER_HELLO_WAIT_TIMEOUT:
            case ProxyCheckDiagnostics.SERVER_CLOSED_AFTER_CLIENT_HELLO:
            case ProxyCheckDiagnostics.CLIENT_HELLO_SENT_NO_SERVER_HELLO:
            case ProxyCheckDiagnostics.HANDSHAKE_PROFILES_EXHAUSTED:
                return EVIDENCE_NO_BYTES_AFTER_CLIENT_HELLO;

            case ProxyCheckDiagnostics.TLS_ALERT_AFTER_CLIENT_HELLO:
            case ProxyCheckDiagnostics.SHORT_TLS_RESPONSE_AFTER_CLIENT_HELLO:
            case ProxyCheckDiagnostics.UNRECOGNIZED_RESPONSE_AFTER_CLIENT_HELLO:
            case ProxyCheckDiagnostics.UNRECOGNIZED_TLS_RESPONSE_AFTER_CLIENT_HELLO:
                return EVIDENCE_SERVER_BYTES_PARSER_FAILURE;

            case ProxyCheckDiagnostics.SERVER_HELLO_HMAC_MISMATCH:
                return EVIDENCE_SERVER_HELLO_HMAC_MISMATCH;

            case ProxyCheckDiagnostics.MTPROXY_PACKET_SENT_NO_RESPONSE:
            case ProxyCheckDiagnostics.POST_HANDSHAKE_NO_APPDATA:
            case ProxyCheckDiagnostics.DROPPED_EARLY_AFTER_APPDATA:
            case ProxyCheckDiagnostics.DROPPED_AFTER_APPDATA:
                return EVIDENCE_POST_HANDSHAKE_NO_APP_DATA;

            case ProxyCheckDiagnostics.SECRET_PARSE_INVALID_DOMAIN_CONTROL_CHAR:
            case ProxyCheckDiagnostics.SECRET_PARSE_INVALID_DOMAIN:
                return EVIDENCE_CONFIG_INVALID_SECRET;

            case ProxyCheckDiagnostics.BACKGROUND_HANDSHAKE_ABORTED:
            case ProxyCheckDiagnostics.SHADOWED_SOCKET_FAILURE:
            case ProxyCheckDiagnostics.IGNORED_CANCELLED_GENERATION:
                return EVIDENCE_CANCELLED_OR_SHADOWED;

            default:
                return EVIDENCE_NONE;
        }
    }

    public static boolean shouldAccelerateProxyRotation(String phase) {
        return canRotate(phase);
    }

    public static boolean isProxyUsableSuccessPhase(String phase) {
        return usableSuccess(phase);
    }

    private static PhaseInfo classify(String phase) {
        // Coordinator-owned exact phases: mtproxy_probe_wait, mtproxy_probe_wait_timeout,
        // faketls_server_hello_wait_timeout, server_closed_after_client_hello,
        // unrecognized_response_after_client_hello.
        switch (ProxyCheckDiagnostics.normalize(phase)) {
            case ProxyCheckDiagnostics.OK:
            case ProxyCheckDiagnostics.CHECKING:
            case ProxyCheckDiagnostics.CANCELLED:
            case ProxyCheckDiagnostics.SHADOWED_SOCKET_FAILURE:
            case ProxyCheckDiagnostics.IGNORED_CANCELLED_GENERATION:
                return NEUTRAL_NONE;

            case ProxyCheckDiagnostics.ADMISSION_QUEUE:
            case ProxyCheckDiagnostics.ENDPOINT_COOLDOWN:
            case ProxyCheckDiagnostics.MTPROXY_PROBE_WAIT:
            case ProxyCheckDiagnostics.PHASE_ADAPTIVE_RECIPE:
            case ProxyCheckDiagnostics.SECRET_DOMAIN_SANITIZED:
            case ProxyCheckDiagnostics.CONNECT_START:
            case ProxyCheckDiagnostics.CLIENT_HELLO_SENT:
            case ProxyCheckDiagnostics.ADMISSION_HOLD_AFTER_CLIENT_HELLO_FAILURE:
            case ProxyCheckDiagnostics.SERVER_HELLO_HMAC_OK:
            case ProxyCheckDiagnostics.ON_CONNECTED:
            case ProxyCheckDiagnostics.FIRST_TLS_APP_SENT:
                return live(KeyScope.EXACT);

            case ProxyCheckDiagnostics.TCP_CONNECT_GATE:
            case ProxyCheckDiagnostics.DNS_COALESCE_WAIT:
            case ProxyCheckDiagnostics.DNS_CACHE_HIT:
            case ProxyCheckDiagnostics.DNS_CACHE_STORE:
            case ProxyCheckDiagnostics.HOST_RESOLVE_START:
            case ProxyCheckDiagnostics.SOCKET_CONNECT_START:
            case ProxyCheckDiagnostics.SOCKET_CONNECTED:
            case ProxyCheckDiagnostics.WAITING_TCP:
                return live(KeyScope.NETWORK);

            case ProxyCheckDiagnostics.FIRST_MTPROXY_PACKET_SENT:
                return live(KeyScope.EXACT);

            case ProxyCheckDiagnostics.FIRST_TLS_APP_RECV:
                return success(KeyScope.EXACT);

            case ProxyCheckDiagnostics.FIRST_MTPROXY_PACKET_RECV:
                return success(KeyScope.EXACT);

            case ProxyCheckDiagnostics.CONNECTION_NOT_STARTED:
                return failure(KeyScope.NONE, false, false);

            case ProxyCheckDiagnostics.ADMISSION_TIMEOUT:
            case ProxyCheckDiagnostics.ENDPOINT_COOLDOWN_TIMEOUT:
            case ProxyCheckDiagnostics.MTPROXY_PROBE_WAIT_TIMEOUT:
                return failure(KeyScope.EXACT, false, false);

            case ProxyCheckDiagnostics.TCP_CONNECT_GATE_TIMEOUT:
            case ProxyCheckDiagnostics.DNS_COALESCE_TIMEOUT:
            case ProxyCheckDiagnostics.DNS_NEGATIVE_CACHE_HIT:
            case ProxyCheckDiagnostics.DNS_BLOCKED_ZERO_ADDRESS:
                return failure(KeyScope.NETWORK, false, false);

            case ProxyCheckDiagnostics.SECRET_PARSE_INVALID_DOMAIN_CONTROL_CHAR:
            case ProxyCheckDiagnostics.SECRET_PARSE_INVALID_DOMAIN:
                return failure(KeyScope.EXACT, true, true);

            case ProxyCheckDiagnostics.HOST_RESOLVE_FAILED:
            case ProxyCheckDiagnostics.HOST_RESOLVE_TIMEOUT:
            case ProxyCheckDiagnostics.TCP_NOT_CONNECTED:
            case ProxyCheckDiagnostics.TCP_CONNECTED_NO_PONG:
            case ProxyCheckDiagnostics.NETWORK_BLOCK_SUSPECTED:
            case ProxyCheckDiagnostics.DROPPED_EARLY_AFTER_APPDATA:
                return failure(KeyScope.NETWORK, true, true);

            case ProxyCheckDiagnostics.TRUE_CLIENT_HELLO_TIMEOUT:
            case ProxyCheckDiagnostics.FAKETLS_SERVER_HELLO_WAIT_TIMEOUT:
            case ProxyCheckDiagnostics.SERVER_CLOSED_AFTER_CLIENT_HELLO:
            case ProxyCheckDiagnostics.CLIENT_HELLO_SENT_NO_SERVER_HELLO:
            case ProxyCheckDiagnostics.TLS_ALERT_AFTER_CLIENT_HELLO:
            case ProxyCheckDiagnostics.SHORT_TLS_RESPONSE_AFTER_CLIENT_HELLO:
            case ProxyCheckDiagnostics.UNRECOGNIZED_RESPONSE_AFTER_CLIENT_HELLO:
            case ProxyCheckDiagnostics.UNRECOGNIZED_TLS_RESPONSE_AFTER_CLIENT_HELLO:
            case ProxyCheckDiagnostics.SERVER_HELLO_HMAC_MISMATCH:
            case ProxyCheckDiagnostics.BACKGROUND_HANDSHAKE_ABORTED:
                return failure(KeyScope.EXACT, false, false);

            case ProxyCheckDiagnostics.HANDSHAKE_PROFILES_EXHAUSTED:
                return failure(KeyScope.EXACT, true, true);

            case ProxyCheckDiagnostics.MTPROXY_PACKET_SENT_NO_RESPONSE:
            case ProxyCheckDiagnostics.POST_HANDSHAKE_NO_APPDATA:
            case ProxyCheckDiagnostics.CONNECTING_TIMEOUT:
                return failure(KeyScope.EXACT, true, true);

            case ProxyCheckDiagnostics.UNKNOWN_FAIL:
                return failure(KeyScope.EXACT, true, false);

            case ProxyCheckDiagnostics.START_FAILED:
                return failure(KeyScope.NONE, false, false);

            case ProxyCheckDiagnostics.DROPPED_AFTER_APPDATA:
                return failure(KeyScope.EXACT, false, false);

            default:
                return failure(KeyScope.EXACT, true, false);
        }
    }

    private static boolean isTerminalExactConfigPhase(String phase) {
        switch (ProxyCheckDiagnostics.normalize(phase)) {
            case ProxyCheckDiagnostics.SECRET_PARSE_INVALID_DOMAIN_CONTROL_CHAR:
            case ProxyCheckDiagnostics.SECRET_PARSE_INVALID_DOMAIN:
                return true;
            default:
                return false;
        }
    }

    private static PhaseInfo live(KeyScope keyScope) {
        return new PhaseInfo(Kind.LIVE, keyScope, false, false, true, false, false);
    }

    private static PhaseInfo success(KeyScope keyScope) {
        return new PhaseInfo(Kind.SUCCESS, keyScope, false, false, true, true, false);
    }

    private static PhaseInfo failure(KeyScope keyScope, boolean canBackoff, boolean canRotate) {
        return new PhaseInfo(Kind.FAILURE, keyScope, canBackoff, canRotate, true, false, false);
    }

    private static PhaseInfo terminalExactFailure() {
        return new PhaseInfo(Kind.FAILURE, KeyScope.EXACT, true, false, true, false, true);
    }

    private static final class PhaseInfo {
        final Kind kind;
        final KeyScope keyScope;
        final boolean canBackoff;
        final boolean canRotate;
        final boolean canOverwriteVisible;
        final boolean usableSuccess;
        final boolean terminalExactConfig;

        PhaseInfo(Kind kind, KeyScope keyScope, boolean canBackoff, boolean canRotate, boolean canOverwriteVisible, boolean usableSuccess, boolean terminalExactConfig) {
            this.kind = kind;
            this.keyScope = keyScope;
            this.canBackoff = canBackoff;
            this.canRotate = canRotate;
            this.canOverwriteVisible = canOverwriteVisible;
            this.usableSuccess = usableSuccess;
            this.terminalExactConfig = terminalExactConfig;
        }
    }
}
