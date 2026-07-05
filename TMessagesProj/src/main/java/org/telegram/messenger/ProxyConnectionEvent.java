package org.telegram.messenger;

import android.os.SystemClock;

public final class ProxyConnectionEvent {

    public static final String SOURCE_NATIVE_STAGE = "native_stage";
    public static final String SOURCE_PROXY_CHECK = "proxy_check";
    public static final String SOURCE_CONNECTED = "connected";
    public static final String SOURCE_CONNECT_START = "connect_start";
    public static final String SOURCE_USABLE_SUCCESS = "usable_success";
    public static final String SOURCE_ROTATION_TIMEOUT = "rotation_timeout";

    public enum Origin {
        ACTIVE_SOCKET("active_socket"),
        PROXY_CHECK("proxy_check"),
        PROXY_LIST_ROW("proxy_list_row"),
        BACKGROUND_PRECHECK("background_precheck"),
        BACKGROUND_KEEPALIVE("background_keepalive"),
        SETTINGS_CHANGE("settings_change"),
        USER_SELECT("user_select"),
        STARTUP_RESTORE("startup_restore"),
        ROTATION_CANDIDATE("rotation_candidate");

        public final String wireName;

        Origin(String wireName) {
            this.wireName = wireName;
        }

        public static Origin fromNative(String origin) {
            if (origin == null) {
                return ACTIVE_SOCKET;
            }
            switch (origin) {
                case "active_socket":
                case "active_proxy":
                    return ACTIVE_SOCKET;
                case "proxy_check":
                    return PROXY_CHECK;
                case "proxy_list_row":
                    return PROXY_LIST_ROW;
                case "background_precheck":
                    return BACKGROUND_PRECHECK;
                case "background_keepalive":
                    return BACKGROUND_KEEPALIVE;
                case "settings_change":
                    return SETTINGS_CHANGE;
                case "user_select":
                    return USER_SELECT;
                case "startup_restore":
                    return STARTUP_RESTORE;
                case "rotation_candidate":
                    return ROTATION_CANDIDATE;
                default:
                    return ACTIVE_SOCKET;
            }
        }
    }

    public enum SocketRole {
        CONTROL_MAIN("control_main"),
        CONTROL_SECONDARY("control_secondary"),
        MEDIA_VISIBLE("media_visible"),
        MEDIA_PREFETCH("media_prefetch"),
        BACKGROUND_KEEPALIVE("background_keepalive"),
        STARTUP_RESTORE("startup_restore"),
        PROXY_CHECK("proxy_check");

        public final String wireName;

        SocketRole(String wireName) {
            this.wireName = wireName;
        }

        public static SocketRole fromNative(String role) {
            if (role == null) {
                return CONTROL_MAIN;
            }
            switch (role) {
                case "control_main":
                    return CONTROL_MAIN;
                case "control_secondary":
                    return CONTROL_SECONDARY;
                case "media_visible":
                    return MEDIA_VISIBLE;
                case "media_prefetch":
                    return MEDIA_PREFETCH;
                case "background_keepalive":
                    return BACKGROUND_KEEPALIVE;
                case "startup_restore":
                    return STARTUP_RESTORE;
                case "proxy_check":
                    return PROXY_CHECK;
                default:
                    return CONTROL_MAIN;
            }
        }
    }

    public final String source;
    public final Origin origin;
    public final int account;
    public final String phase;
    public final String endpointKey;
    public final String networkKey;
    public final String probeKey;
    public final SocketRole socketRole;
    public final int activationGeneration;
    // Native retry-authority hold (ms) that arrived with the event; 0 when the
    // event carries no native clock (Java-origin events, live phases).
    public final int suggestedHoldMs;
    public final long timestamp;

    private ProxyConnectionEvent(String source, Origin origin, int account, String phase, String endpointKey, String networkKey, String probeKey, int activationGeneration, long timestamp) {
        this(source, origin, account, phase, endpointKey, networkKey, probeKey, defaultRoleForOrigin(origin), activationGeneration, 0, timestamp);
    }

    private ProxyConnectionEvent(String source, Origin origin, int account, String phase, String endpointKey, String networkKey, String probeKey, int activationGeneration, int suggestedHoldMs, long timestamp) {
        this(source, origin, account, phase, endpointKey, networkKey, probeKey, defaultRoleForOrigin(origin), activationGeneration, suggestedHoldMs, timestamp);
    }

    private ProxyConnectionEvent(String source, Origin origin, int account, String phase, String endpointKey, String networkKey, String probeKey, SocketRole socketRole, int activationGeneration, int suggestedHoldMs, long timestamp) {
        this.source = source;
        this.origin = origin == null ? Origin.ACTIVE_SOCKET : origin;
        this.account = account;
        this.phase = ProxyCheckDiagnostics.normalize(phase);
        this.endpointKey = endpointKey == null ? "" : endpointKey;
        this.networkKey = networkKey == null || networkKey.length() == 0 ? ProxyEndpointKey.networkFromLiveStage(this.endpointKey) : networkKey;
        this.probeKey = probeKey == null ? "" : probeKey;
        this.socketRole = socketRole == null ? defaultRoleForOrigin(this.origin) : socketRole;
        this.activationGeneration = activationGeneration;
        this.suggestedHoldMs = Math.max(0, suggestedHoldMs);
        this.timestamp = timestamp == 0 ? SystemClock.elapsedRealtime() : timestamp;
    }

    public static ProxyConnectionEvent nativeStage(int account, String phase, String endpointKey) {
        return nativeStage(account, phase, endpointKey, SystemClock.elapsedRealtime());
    }

    public static ProxyConnectionEvent nativeStage(int account, String phase, String endpointKey, long timestamp) {
        return new ProxyConnectionEvent(SOURCE_NATIVE_STAGE, Origin.ACTIVE_SOCKET, account, phase, endpointKey, "", "", 0, timestamp);
    }

    public static ProxyConnectionEvent nativeStage(int account, String phase, String endpointKey, String origin) {
        return nativeStage(account, phase, endpointKey, "", origin, SystemClock.elapsedRealtime());
    }

    public static ProxyConnectionEvent nativeStage(int account, String phase, String endpointKey, String origin, long timestamp) {
        return nativeStage(account, phase, endpointKey, "", origin, timestamp);
    }

    public static ProxyConnectionEvent nativeStage(int account, String phase, String endpointKey, String probeKey, String origin) {
        return nativeStage(account, phase, endpointKey, probeKey, origin, 0, SystemClock.elapsedRealtime());
    }

    public static ProxyConnectionEvent nativeStage(int account, String phase, String endpointKey, String probeKey, String origin, long timestamp) {
        return nativeStage(account, phase, endpointKey, probeKey, origin, 0, timestamp);
    }

    public static ProxyConnectionEvent nativeStage(int account, String phase, String endpointKey, String probeKey, String origin, int activationGeneration) {
        return nativeStage(account, phase, endpointKey, probeKey, origin, activationGeneration, SystemClock.elapsedRealtime());
    }

    public static ProxyConnectionEvent nativeStage(int account, String phase, String endpointKey, String probeKey, String origin, int activationGeneration, long timestamp) {
        return nativeStage(account, phase, endpointKey, probeKey, origin, activationGeneration, 0, timestamp);
    }

    public static ProxyConnectionEvent nativeStage(int account, String phase, String endpointKey, String probeKey, String origin, int activationGeneration, int suggestedHoldMs, long timestamp) {
        return nativeStage(account, phase, endpointKey, probeKey, origin, null, activationGeneration, suggestedHoldMs, timestamp);
    }

    public static ProxyConnectionEvent nativeStage(int account, String phase, String endpointKey, String probeKey, String origin, String socketRole, int activationGeneration, int suggestedHoldMs, long timestamp) {
        Origin parsedOrigin = Origin.fromNative(origin);
        SocketRole parsedRole = socketRole == null || socketRole.length() == 0 ? defaultRoleForOrigin(parsedOrigin) : SocketRole.fromNative(socketRole);
        return new ProxyConnectionEvent(SOURCE_NATIVE_STAGE, parsedOrigin, account, phase, endpointKey, "", probeKey, parsedRole, activationGeneration, suggestedHoldMs, timestamp);
    }

    public static ProxyConnectionEvent proxyCheck(int account, SharedConfig.ProxyInfo proxyInfo, String phase) {
        return new ProxyConnectionEvent(SOURCE_PROXY_CHECK, Origin.PROXY_CHECK, account, phase, ProxyEndpointKey.liveStage(proxyInfo), ProxyEndpointKey.networkLiveStage(proxyInfo), "", 0, SystemClock.elapsedRealtime());
    }

    public static ProxyConnectionEvent connected(int account, SharedConfig.ProxyInfo proxyInfo) {
        return connected(account, proxyInfo, Origin.ACTIVE_SOCKET, 0, SystemClock.elapsedRealtime());
    }

    public static ProxyConnectionEvent connected(int account, SharedConfig.ProxyInfo proxyInfo, Origin origin, int activationGeneration, long timestamp) {
        return new ProxyConnectionEvent(SOURCE_CONNECTED, origin, account, ProxyCheckDiagnostics.OK, ProxyEndpointKey.liveStage(proxyInfo), ProxyEndpointKey.networkLiveStage(proxyInfo), "", activationGeneration, timestamp);
    }

    public static ProxyConnectionEvent connectStart(int account, SharedConfig.ProxyInfo proxyInfo) {
        return connectStart(account, proxyInfo, Origin.ACTIVE_SOCKET, 0, SystemClock.elapsedRealtime());
    }

    public static ProxyConnectionEvent connectStart(int account, SharedConfig.ProxyInfo proxyInfo, Origin origin, int activationGeneration, long timestamp) {
        return new ProxyConnectionEvent(SOURCE_CONNECT_START, origin, account, ProxyCheckDiagnostics.CONNECT_START, ProxyEndpointKey.liveStage(proxyInfo), ProxyEndpointKey.networkLiveStage(proxyInfo), "", activationGeneration, timestamp);
    }

    public static ProxyConnectionEvent usableSuccess(int account, SharedConfig.ProxyInfo proxyInfo, String diagnostic, Origin origin, int activationGeneration, long timestamp) {
        return new ProxyConnectionEvent(SOURCE_USABLE_SUCCESS, origin, account, diagnostic, ProxyEndpointKey.liveStage(proxyInfo), ProxyEndpointKey.networkLiveStage(proxyInfo), "", activationGeneration, timestamp);
    }

    public static ProxyConnectionEvent rotationTimeout(int account, SharedConfig.ProxyInfo proxyInfo, String diagnostic, long timestamp) {
        return rotationTimeout(account, proxyInfo, diagnostic, 0, timestamp);
    }

    public static ProxyConnectionEvent rotationTimeout(int account, SharedConfig.ProxyInfo proxyInfo, String diagnostic, int activationGeneration, long timestamp) {
        return new ProxyConnectionEvent(SOURCE_ROTATION_TIMEOUT, Origin.ACTIVE_SOCKET, account, diagnostic, ProxyEndpointKey.liveStage(proxyInfo), ProxyEndpointKey.networkLiveStage(proxyInfo), "", SocketRole.CONTROL_MAIN, activationGeneration, 0, timestamp);
    }

    public static boolean isActiveProxyOrigin(Origin origin) {
        if (origin == null) {
            return true;
        }
        switch (origin) {
            case ACTIVE_SOCKET:
            case SETTINGS_CHANGE:
            case USER_SELECT:
            case ROTATION_CANDIDATE:
                return true;
            default:
                return false;
        }
    }

    public static boolean isHealthOrigin(Origin origin) {
        if (origin == null) {
            return true;
        }
        switch (origin) {
            case ACTIVE_SOCKET:
            case BACKGROUND_KEEPALIVE:
            case SETTINGS_CHANGE:
            case USER_SELECT:
            case STARTUP_RESTORE:
            case ROTATION_CANDIDATE:
                return true;
            default:
                return false;
        }
    }

    public static boolean isVisibleOwnerOrigin(Origin origin) {
        return origin == Origin.ACTIVE_SOCKET
                || origin == Origin.SETTINGS_CHANGE
                || origin == Origin.USER_SELECT
                || origin == Origin.ROTATION_CANDIDATE;
    }

    public static boolean isRotationOwnerOrigin(Origin origin) {
        return isVisibleOwnerOrigin(origin);
    }

    public static boolean canDriveVisible(ProxyConnectionEvent event) {
        if (event == null
                || event.account != UserConfig.selectedAccount
                || !isControlMainRole(event)) {
            return false;
        }
        switch (event.origin) {
            case USER_SELECT:
            case SETTINGS_CHANGE:
            case ROTATION_CANDIDATE:
                return true;
            case ACTIVE_SOCKET:
                return !ApplicationLoader.mainInterfacePaused;
            default:
                return false;
        }
    }

    public static boolean canDriveRotation(ProxyConnectionEvent event, ProxyEndpointVerdict verdict) {
        return canDriveVisible(event)
                && isRotationOwnerOrigin(event.origin)
                && verdict != null
                && verdict.canRotate;
    }

    public static boolean isLifecycleHealthOnly(ProxyConnectionEvent event) {
        return event != null
                && isHealthOrigin(event.origin)
                && !canDriveVisible(event);
    }

    private static boolean isControlMainRole(ProxyConnectionEvent event) {
        return event != null && event.socketRole == SocketRole.CONTROL_MAIN;
    }

    private static SocketRole defaultRoleForOrigin(Origin origin) {
        if (origin == null) {
            return SocketRole.CONTROL_MAIN;
        }
        switch (origin) {
            case PROXY_CHECK:
            case PROXY_LIST_ROW:
            case BACKGROUND_PRECHECK:
                return SocketRole.PROXY_CHECK;
            case BACKGROUND_KEEPALIVE:
                return SocketRole.BACKGROUND_KEEPALIVE;
            case STARTUP_RESTORE:
                return SocketRole.STARTUP_RESTORE;
            default:
                return SocketRole.CONTROL_MAIN;
        }
    }
}
