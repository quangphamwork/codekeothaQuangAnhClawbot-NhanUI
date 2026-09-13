/*
 * Sim-to-Real ESP32-S3 WebSocket Client
 * ======================================
 * Connects to the bridge_server.py via WiFi WebSocket
 * and executes robot commands received from the simulation.
 *
 * This sketch extends the S4VRobot library with WiFi + WebSocket
 * capability for Sim-to-Real integration.
 *
 * Dependencies (install via Arduino Library Manager):
 *   - ArduinoJson (by Benoit Blanchon) >= 6.x
 *   - WebSockets (by Markus Sattler) >= 2.4.0
 *   - S4VRobot (your existing library)
 *
 * Hardware: ESP32-S3 Dev Module
 *
 * Protocol:
 *   Bridge → ESP32 (JSON):
 *     {"cmd":"go_forward","speed":50}
 *     {"cmd":"turn_left","speed":80}
 *     {"cmd":"arm_up","angle":0}
 *     {"cmd":"close_gripper","angle":30}
 *     {"cmd":"stop"}
 *
 *   ESP32 → Bridge (JSON):
 *     {"type":"hardware_hello","device":"S4VRobot-ESP32S3"}
 *     {"type":"ack","cmd":"go_forward","ok":true}
 *     {"type":"status","uptime":12345}
 */

#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include <S4VRobot.h>

// ============================================
// CONFIGURATION — Edit these for your network
// ============================================
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Bridge server address (your PC running bridge_server.py)
const char* BRIDGE_HOST = "192.168.1.100";  // Change to your PC's IP
const uint16_t BRIDGE_PORT = 8765;
const char* BRIDGE_PATH = "/hardware";

// Robot configuration
const char* DEVICE_NAME = "S4VRobot-ESP32S3";

// ============================================
// GLOBALS
// ============================================
S4VRobot Robot;
WebSocketsClient webSocket;

bool wsConnected = false;
unsigned long lastStatusTime = 0;
const unsigned long STATUS_INTERVAL = 5000;  // Send status every 5s

// ============================================
// COMMAND HANDLER
// ============================================
void handleCommand(const char* json) {
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, json);

    if (error) {
        Serial.printf("[WS] JSON parse error: %s\n", error.c_str());
        return;
    }

    const char* cmd = doc["cmd"];
    if (!cmd) return;

    Serial.printf("[CMD] %s\n", cmd);

    // Movement commands
    if (strcmp(cmd, "go_forward") == 0) {
        int speed = doc["speed"] | 50;
        Robot.go_forward(speed);
    }
    else if (strcmp(cmd, "go_backward") == 0) {
        int speed = doc["speed"] | 50;
        Robot.go_backward(speed);
    }
    else if (strcmp(cmd, "turn_left") == 0) {
        int speed = doc["speed"] | 50;
        Robot.turn_left(speed);
    }
    else if (strcmp(cmd, "turn_right") == 0) {
        int speed = doc["speed"] | 50;
        Robot.turn_right(speed);
    }
    else if (strcmp(cmd, "stop") == 0) {
        Robot.stop();
    }
    // Arm commands
    // Note: S4VRobot uses incremental arm_upward()/arm_downward()
    // Sim sends absolute angles. We approximate by stepping to target.
    else if (strcmp(cmd, "arm_up") == 0) {
        // Move arm upward for a few steps
        for (int i = 0; i < 20; i++) {
            Robot.arm_upward(2.0);
            delay(10);
        }
    }
    else if (strcmp(cmd, "arm_down") == 0) {
        for (int i = 0; i < 20; i++) {
            Robot.arm_downward(2.0);
            delay(10);
        }
    }
    // Gripper commands
    else if (strcmp(cmd, "close_gripper") == 0) {
        for (int i = 0; i < 20; i++) {
            Robot.grasp(2.0);
            delay(10);
        }
    }
    else if (strcmp(cmd, "open_gripper") == 0) {
        for (int i = 0; i < 20; i++) {
            Robot.release(2.0);
            delay(10);
        }
    }
    else {
        Serial.printf("[CMD] Unknown: %s\n", cmd);
    }

    // Send ACK
    sendAck(cmd, true);
}

void sendAck(const char* cmd, bool ok) {
    if (!wsConnected) return;

    StaticJsonDocument<128> doc;
    doc["type"] = "ack";
    doc["cmd"] = cmd;
    doc["ok"] = ok;

    char buffer[128];
    serializeJson(doc, buffer);
    webSocket.sendTXT(buffer);
}

void sendHello() {
    StaticJsonDocument<128> doc;
    doc["type"] = "hardware_hello";
    doc["device"] = DEVICE_NAME;

    char buffer[128];
    serializeJson(doc, buffer);
    webSocket.sendTXT(buffer);
    Serial.println("[WS] Sent hello");
}

void sendStatus() {
    if (!wsConnected) return;

    StaticJsonDocument<128> doc;
    doc["type"] = "status";
    doc["uptime"] = millis() / 1000;
    doc["device"] = DEVICE_NAME;

    char buffer[128];
    serializeJson(doc, buffer);
    webSocket.sendTXT(buffer);
}

// ============================================
// WEBSOCKET CALLBACKS
// ============================================
void webSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
    switch (type) {
        case WStype_DISCONNECTED:
            wsConnected = false;
            Serial.println("[WS] Disconnected");
            Robot.stop();  // Safety: stop on disconnect
            break;

        case WStype_CONNECTED:
            wsConnected = true;
            Serial.printf("[WS] Connected to %s:%d%s\n", BRIDGE_HOST, BRIDGE_PORT, BRIDGE_PATH);
            sendHello();
            break;

        case WStype_TEXT:
            Serial.printf("[WS] Received: %s\n", payload);
            handleCommand((const char*)payload);
            break;

        case WStype_PING:
            Serial.println("[WS] Ping");
            break;

        case WStype_PONG:
            break;

        default:
            break;
    }
}

// ============================================
// SETUP
// ============================================
void setup() {
    Serial.begin(115200);
    Serial.println("\n=== Sim-to-Real ESP32-S3 Client ===");

    // Initialize robot hardware
    Robot.begin();
    Serial.println("[ROBOT] Initialized");

    // Connect WiFi
    Serial.printf("[WIFI] Connecting to %s", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.printf("\n[WIFI] Connected! IP: %s\n", WiFi.localIP().toString().c_str());

    // Connect WebSocket
    webSocket.begin(BRIDGE_HOST, BRIDGE_PORT, BRIDGE_PATH);
    webSocket.onEvent(webSocketEvent);
    webSocket.setReconnectInterval(3000);  // Auto-reconnect every 3s

    Serial.printf("[WS] Connecting to ws://%s:%d%s\n", BRIDGE_HOST, BRIDGE_PORT, BRIDGE_PATH);
}

// ============================================
// MAIN LOOP
// ============================================
void loop() {
    webSocket.loop();

    // Also process Dabble BLE if connected (dual control)
    Robot.processInput();

    // Send periodic status
    if (wsConnected && millis() - lastStatusTime > STATUS_INTERVAL) {
        sendStatus();
        lastStatusTime = millis();
    }
}
