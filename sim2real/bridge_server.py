"""
Sim-to-Real Bridge Server
=========================
WebSocket bridge that relays robot commands from the Webots simulation
controller to a real ESP32-S3 robot over WiFi.

Architecture:
    Webots Controller (Python) --[localhost WS]--> Bridge Server --[WiFi WS]--> ESP32-S3

The bridge runs as a standalone process on the same machine as Webots.
It accepts two types of WebSocket connections:
    1. Controller client (Webots robot_controller.py) — sends commands
    2. Hardware client (ESP32-S3) — receives commands and sends status

Protocol (JSON over WebSocket):
    Controller → Bridge:
        {"cmd": "go_forward", "args": {"speed": 50}}
        {"cmd": "arm_up", "args": {"angle": 0}}
        {"cmd": "stop"}
        {"cmd": "delay", "args": {"seconds": 2}}

    Bridge → ESP32:
        {"cmd": "go_forward", "speed": 50}
        {"cmd": "arm_up", "angle": 0}
        {"cmd": "stop"}

    ESP32 → Bridge → Controller:
        {"type": "status", "connected": true, "battery": 85}
        {"type": "ack", "cmd": "go_forward", "ok": true}

    Bridge → Controller (status):
        {"type": "bridge_status", "hardware_connected": true, "esp32_ip": "192.168.1.x"}

Usage:
    python bridge_server.py [--port 8765]
"""

import asyncio
import json
import logging
import argparse
import time
from typing import Optional, Set

try:
    import websockets
    from websockets.server import serve
except ImportError:
    print("=" * 60)
    print("ERROR: websockets library not installed.")
    print("Install with:  pip install websockets")
    print("=" * 60)
    raise SystemExit(1)

# ==========================================
# CONFIGURATION
# ==========================================
DEFAULT_PORT = 8765
LOG_FORMAT = "[%(asctime)s] %(levelname)-7s %(message)s"
LOG_DATEFMT = "%H:%M:%S"

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt=LOG_DATEFMT)
log = logging.getLogger("bridge")

# ==========================================
# CONNECTION REGISTRY
# ==========================================
controller_clients: Set = set()  # Webots controllers
hardware_clients: Set = set()    # ESP32 devices

# Stats
stats = {
    "commands_sent": 0,
    "commands_acked": 0,
    "hw_connected_since": None,
    "last_command": None,
    "last_command_time": None,
}


async def broadcast_to_hardware(message: str):
    """Send a message to all connected hardware clients."""
    if not hardware_clients:
        return False
    disconnected = set()
    for ws in hardware_clients:
        try:
            await ws.send(message)
        except websockets.exceptions.ConnectionClosed:
            disconnected.add(ws)
    hardware_clients.difference_update(disconnected)
    return len(hardware_clients) > 0


async def notify_controllers(message: str):
    """Send a status message to all connected controller clients."""
    disconnected = set()
    for ws in controller_clients:
        try:
            await ws.send(message)
        except websockets.exceptions.ConnectionClosed:
            disconnected.add(ws)
    controller_clients.difference_update(disconnected)


async def send_bridge_status():
    """Broadcast current bridge status to all controllers."""
    status = {
        "type": "bridge_status",
        "hardware_connected": len(hardware_clients) > 0,
        "hardware_count": len(hardware_clients),
        "commands_sent": stats["commands_sent"],
        "commands_acked": stats["commands_acked"],
        "last_command": stats["last_command"],
    }
    await notify_controllers(json.dumps(status))


# ==========================================
# COMMAND MAPPING
# ==========================================
# Maps simulation commands to hardware-friendly format.
# The ESP32 firmware expects simplified JSON commands.

VALID_COMMANDS = {
    "go_forward", "go_backward", "turn_left", "turn_right",
    "stop", "stop_all",
    "arm_up", "arm_down",
    "open_gripper", "close_gripper",
    "delay",  # handled differently — not sent to hardware
    "set_speed",
    "home",
}


def map_sim_to_hardware(data: dict) -> Optional[dict]:
    """
    Convert a simulation command to a hardware command.
    Returns None if the command should not be forwarded to hardware.
    """
    cmd = data.get("cmd", "")
    args = data.get("args", {})

    if cmd not in VALID_COMMANDS:
        log.warning(f"Unknown command: {cmd}")
        return None

    # 'delay' is a simulation concept — don't send to hardware
    # The hardware receives discrete movement commands and keeps running
    # until a new command or stop is received.
    if cmd == "delay":
        return None

    # 'stop_all' maps to 'stop' on hardware
    if cmd == "stop_all":
        cmd = "stop"

    # Build hardware command — flatten args into top-level
    hw_cmd = {"cmd": cmd}
    hw_cmd.update(args)
    return hw_cmd


# ==========================================
# WEBSOCKET HANDLER
# ==========================================
async def handler(websocket):
    """Handle a new WebSocket connection."""
    # Determine client type from path or first message
    path = websocket.request.path if hasattr(websocket, 'request') else ""

    if "/hardware" in path:
        await handle_hardware(websocket)
    elif "/controller" in path:
        await handle_controller(websocket)
    else:
        # Auto-detect from first message
        try:
            first_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(first_msg)
            if data.get("type") == "hardware_hello":
                await handle_hardware(websocket, first_msg=data)
            else:
                await handle_controller(websocket, first_msg=first_msg)
        except asyncio.TimeoutError:
            await websocket.close(1008, "Timeout: identify yourself")
        except Exception as e:
            log.error(f"Connection error: {e}")
            await websocket.close(1011, str(e))


async def handle_controller(websocket, first_msg=None):
    """Handle a Webots controller connection."""
    controller_clients.add(websocket)
    remote = websocket.remote_address
    log.info(f"Controller connected from {remote}")
    await send_bridge_status()

    try:
        if first_msg:
            await process_controller_message(first_msg)

        async for message in websocket:
            await process_controller_message(message)
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        controller_clients.discard(websocket)
        log.info(f"Controller disconnected from {remote}")


async def process_controller_message(message: str):
    """Process a command from the Webots controller."""
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        log.warning(f"Invalid JSON from controller: {message[:100]}")
        return

    cmd = data.get("cmd", "?")
    stats["last_command"] = cmd
    stats["last_command_time"] = time.time()

    # Map to hardware command
    hw_cmd = map_sim_to_hardware(data)
    if hw_cmd is None:
        return  # Command not forwarded (e.g., delay)

    hw_json = json.dumps(hw_cmd)

    # Forward to hardware
    sent = await broadcast_to_hardware(hw_json)
    stats["commands_sent"] += 1

    if sent:
        log.info(f"→ HW: {hw_json}")
    else:
        log.debug(f"→ (no hardware) {hw_json}")


async def handle_hardware(websocket, first_msg=None):
    """Handle an ESP32 hardware connection."""
    hardware_clients.add(websocket)
    remote = websocket.remote_address
    log.info(f"★ Hardware connected from {remote}")
    stats["hw_connected_since"] = time.time()
    await send_bridge_status()

    try:
        if first_msg:
            await process_hardware_message(first_msg)

        async for message in websocket:
            try:
                data = json.loads(message)
                await process_hardware_message(data)
            except json.JSONDecodeError:
                log.warning(f"Invalid JSON from hardware: {message[:100]}")
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        hardware_clients.discard(websocket)
        stats["hw_connected_since"] = None
        log.info(f"★ Hardware disconnected from {remote}")
        await send_bridge_status()


async def process_hardware_message(data: dict):
    """Process a message from the ESP32."""
    msg_type = data.get("type", "")

    if msg_type == "ack":
        stats["commands_acked"] += 1
        log.info(f"← HW ACK: {data.get('cmd', '?')}")

    elif msg_type == "status":
        log.debug(f"← HW Status: {data}")

    elif msg_type == "hardware_hello":
        device = data.get("device", "unknown")
        log.info(f"★ Hardware identified: {device}")

    # Forward hardware messages to controllers
    await notify_controllers(json.dumps(data))


# ==========================================
# MAIN
# ==========================================
async def main(port: int):
    log.info("=" * 50)
    log.info(f"  Sim-to-Real Bridge Server")
    log.info(f"  Port: {port}")
    log.info(f"  Controller URL: ws://localhost:{port}/controller")
    log.info(f"  Hardware URL:   ws://localhost:{port}/hardware")
    log.info("=" * 50)

    async with serve(handler, "0.0.0.0", port):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sim-to-Real Bridge Server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="WebSocket port")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.port))
    except KeyboardInterrupt:
        log.info("Bridge server stopped.")
