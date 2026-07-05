#!/usr/bin/env python3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JNI = ROOT / "TMessagesProj/jni"
TGNET = JNI / "tgnet"
JAVA_TGNET = ROOT / "TMessagesProj/src/main/java/org/telegram/tgnet"
JAVA_MESSENGER = ROOT / "TMessagesProj/src/main/java/org/telegram/messenger"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def block(text: str, start_marker: str, end_marker: str | None = None) -> str:
    start = text.find(start_marker)
    if start < 0:
        return ""
    if end_marker is None:
        return text[start:]
    end = text.find(end_marker, start + len(start_marker))
    return text[start:end if end >= 0 else len(text)]


def method_body(text: str, signature: str) -> str:
    start = text.find(signature)
    if start < 0:
        return ""
    brace = text.find("{", start)
    if brace < 0:
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


def main() -> int:
    failures: list[str] = []

    wrapper = read(JNI / "TgNetWrapper.cpp")
    defines = read(TGNET / "Defines.h")
    manager_h = read(TGNET / "ConnectionsManager.h")
    manager_cpp = read(TGNET / "ConnectionsManager.cpp")
    java_connections = read(JAVA_TGNET / "ConnectionsManager.java")
    event = read(JAVA_MESSENGER / "ProxyConnectionEvent.java")

    native_settings_sig = "(ILjava/lang/String;ILjava/lang/String;Ljava/lang/String;Ljava/lang/String;Lorg/telegram/tgnet/MtProxyOptions;ILjava/lang/String;)V"
    native_activation_sig = "(IILjava/lang/String;)V"
    stage_callback_sig = "(ILjava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;II)V"

    require(
        "public static native void native_setProxySettings(int currentAccount, String address, int port, String username, String password, String secret, MtProxyOptions options, int activationGeneration, String activationOrigin);" in java_connections,
        "Java native_setProxySettings declaration must include MtProxyOptions, activationGeneration and activationOrigin",
        failures,
    )
    require(
        "public static native void native_setProxyActivationContext(int currentAccount, int activationGeneration, String activationOrigin);" in java_connections,
        "Java native_setProxyActivationContext declaration must include activationGeneration and activationOrigin",
        failures,
    )
    require(
        "public static void onProxyConnectionStageChanged(final int currentAccount, final String diagnostic, final String endpointKey, final String probeKey, final String origin, final String socketRole, final int activationGeneration, final int suggestedHoldMs)" in java_connections
        and "ProxyConnectionEvent.nativeStage(currentAccount, diagnostic, endpointKey, probeKey, origin, socketRole, activationGeneration, suggestedHoldMs" in java_connections,
        "Java onProxyConnectionStageChanged must accept origin, socketRole, activationGeneration and suggestedHoldMs and pass all of them into ProxyConnectionEvent",
        failures,
    )
    require(
        "public final SocketRole socketRole" in event
        and "public final int suggestedHoldMs" in event
        and "nativeStage(int account, String phase, String endpointKey, String probeKey, String origin, String socketRole, int activationGeneration, int suggestedHoldMs" in event,
        "ProxyConnectionEvent must carry socketRole and suggestedHoldMs from the JNI callback",
        failures,
    )

    require(
        "void setProxySettings(JNIEnv *env, jclass c, jint instanceNum, jstring address, jint port, jstring username, jstring password, jstring secret, jobject options, jint activationGeneration, jstring activationOrigin)" in wrapper,
        "TgNetWrapper setProxySettings JNI body must accept MtProxyOptions, activationGeneration and activationOrigin",
        failures,
    )
    settings_body = method_body(wrapper, "void setProxySettings")
    require(
        "MtProxyOptions nativeOptions = readMtProxyOptions(env, options)" in settings_body
        and "const char *activationOriginStr" in settings_body
        and "activationGeneration > 0 ? (uint32_t) activationGeneration : 0" in settings_body
        and 'activationOriginStr != nullptr ? activationOriginStr : "active_socket"' in settings_body
        and "ConnectionsManager::getInstance(instanceNum).setProxySettings" in settings_body
        and "env->ReleaseStringUTFChars(activationOrigin, activationOriginStr)" in settings_body,
        "TgNetWrapper setProxySettings must bridge MtProxyOptions, activationGeneration and activationOrigin into native and release the origin string",
        failures,
    )
    require(
        f'{{"native_setProxySettings", "{native_settings_sig}", (void *) setProxySettings}}' in wrapper,
        "JNI native_setProxySettings registration must match the Java declaration exactly",
        failures,
    )

    require(
        "void setProxyActivationContext(JNIEnv *env, jclass c, jint instanceNum, jint activationGeneration, jstring activationOrigin)" in wrapper,
        "TgNetWrapper setProxyActivationContext JNI body must accept activationGeneration and activationOrigin",
        failures,
    )
    activation_body = method_body(wrapper, "void setProxyActivationContext")
    require(
        "const char *activationOriginStr" in activation_body
        and "ConnectionsManager::getInstance(instanceNum).setProxyActivationContext" in activation_body
        and "activationGeneration > 0 ? (uint32_t) activationGeneration : 0" in activation_body
        and 'activationOriginStr != nullptr ? activationOriginStr : "active_socket"' in activation_body
        and "env->ReleaseStringUTFChars(activationOrigin, activationOriginStr)" in activation_body,
        "TgNetWrapper setProxyActivationContext must bridge activationGeneration and activationOrigin into native and release the origin string",
        failures,
    )
    require(
        f'{{"native_setProxyActivationContext", "{native_activation_sig}", (void *) setProxyActivationContext}}' in wrapper,
        "JNI native_setProxyActivationContext registration must match the Java declaration exactly",
        failures,
    )

    require(
        "void onProxyConnectionStageChanged(int32_t instanceNum, std::string diagnostic, std::string endpointKey, std::string probeKey, std::string origin, std::string socketRole, int32_t activationGeneration, int32_t suggestedReconnectHoldMs)" in defines
        and "void onProxyConnectionStageChanged(int32_t instanceNum, std::string diagnostic, std::string endpointKey, std::string probeKey, std::string origin, std::string socketRole, int32_t activationGeneration, int32_t suggestedReconnectHoldMs)" in wrapper,
        "native delegate and TgNetWrapper override must expose origin, socketRole, activationGeneration and suggestedReconnectHoldMs",
        failures,
    )
    callback_body = method_body(wrapper, "void onProxyConnectionStageChanged")
    require(
        "jstring originString = jniEnv[instanceNum]->NewStringUTF(origin.c_str())" in callback_body
        and "jstring socketRoleString = jniEnv[instanceNum]->NewStringUTF(socketRole.c_str())" in callback_body
        and "jclass_ConnectionsManager_onProxyConnectionStageChanged" in callback_body
        and "originString, socketRoleString, activationGeneration, suggestedReconnectHoldMs" in callback_body
        and "DeleteLocalRef(socketRoleString)" in callback_body,
        "TgNetWrapper stage callback must forward origin, socketRole, activationGeneration and suggestedReconnectHoldMs to Java and release socketRoleString",
        failures,
    )
    require(
        f'GetStaticMethodID(jclass_ConnectionsManager, "onProxyConnectionStageChanged", "{stage_callback_sig}")' in wrapper,
        "GetStaticMethodID for onProxyConnectionStageChanged must use the full origin/role/generation/hold signature",
        failures,
    )
    for old_sig in (
        "(ILjava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;I)V",
        "(ILjava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;II)V",
        "(ILjava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;I)V",
    ):
        require(
            f'GetStaticMethodID(jclass_ConnectionsManager, "onProxyConnectionStageChanged", "{old_sig}")' not in wrapper,
            f"JNI must not resolve old onProxyConnectionStageChanged signature {old_sig}",
            failures,
        )

    require(
        "void setProxySettings(std::string address, uint16_t port, std::string username, std::string password, std::string secret, const MtProxyOptions &options, uint32_t activationGeneration, std::string activationOrigin)" in manager_h
        and "void ConnectionsManager::setProxySettings(std::string address, uint16_t port, std::string username, std::string password, std::string secret, const MtProxyOptions &options, uint32_t activationGeneration, std::string activationOrigin)" in manager_cpp,
        "native ConnectionsManager::setProxySettings signature must match the JNI bridge",
        failures,
    )
    require(
        "void setProxyActivationContext(uint32_t activationGeneration, std::string activationOrigin)" in manager_h
        and "void ConnectionsManager::setProxyActivationContext(uint32_t activationGeneration, std::string activationOrigin)" in manager_cpp,
        "native ConnectionsManager::setProxyActivationContext signature must match the JNI bridge",
        failures,
    )

    if failures:
        print("MTProxy JNI bridge contract guard failed:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("MTProxy JNI bridge contract guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
