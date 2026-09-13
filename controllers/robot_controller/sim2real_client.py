"""
Sim-to-Real Hardware Bridge Client
===================================
Non-blocking WebSocket client that runs inside the Webots controller process.
Sends robot commands to the bridge server for forwarding to real hardware.

Usage in robot_controller.py:
    from sim2real_client import HardwareBridge

    bridge = HardwareBridge("ws://localhost:8765/controller")

    # In your robot API:
    def go_forward(speed):
        drive.go_forward(speed)          # Simulation
        bridge.send("go_forward", speed=speed)  # Hardware

Design principles:
    - Fire-and-forget: commands are queued, never block simulation
    - Fault-tolerant: hardware errors never crash simulation
    - Auto-reconnect: reconnects silently if connection drops
    - Thread-safe: uses a background thread for WebSocket I/O
"""

import json
import threading
import time
import logging
from collections import deque
from typing import Optional, Dict, Any

log = logging.getLogger("sim2real")

# Try to import websockets; if not available, bridge is disabled
try:
    import asyncio
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False


class HardwareBridge:
    """
    Non-blocking bridge client that sends commands to the Sim-to-Real bridge server.
    Runs a background thread with its own asyncio event loop.
    """

    def __init__(self, url: str = "ws://localhost:8765/controller",
                 enabled: bool = False,
                 reconnect_interval: float = 3.0,
                 max_queue: int = 100):
        """
        Args:
            url: WebSocket URL of the bridge server
            enabled: Whether to start the bridge (can be toggled later)
            reconnect_interval: Seconds between reconnect attempts
            max_queue: Maximum queued commands before dropping oldest
        """
        self.url = url
        self._enabled = enabled
        self.reconnect_interval = reconnect_interval
        self.max_queue = max_queue

        self._connected = False
        self._hw_connected = False  # Whether ESP32 is connected to bridge
        self._queue: deque = deque(maxlen=max_queue)
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_event = threading.Event()
        self._stats = {
            "sent": 0,
            "errors": 0,
            "dropped": 0,
            "last_cmd": None,
        }

        if not HAS_WEBSOCKETS:
            log.warning("websockets not installed — Sim-to-Real bridge disabled")
            return

        if enabled:
            self.start()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        if value and not self._enabled:
            self._enabled = True
            self.start()
        elif not value and self._enabled:
            self._enabled = False
            self.stop()

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def hardware_connected(self) -> bool:
        return self._hw_connected

    @property
    def stats(self) -> dict:
        return dict(self._stats)

    def send(self, cmd: str, **kwargs):
        """
        Queue a command to be sent to hardware.
        Non-blocking, fire-and-forget. Safe to call from any thread.
        """
        if not self._enabled or not HAS_WEBSOCKETS:
            return

        msg = {"cmd": cmd}
        if kwargs:
            msg["args"] = kwargs

        self._queue.append(json.dumps(msg))
        self._stats["last_cmd"] = cmd

    def get_status(self) -> dict:
        """Return current bridge status for UI display."""
        return {
            "enabled": self._enabled,
            "bridge_connected": self._connected,
            "hardware_connected": self._hw_connected,
            "commands_sent": self._stats["sent"],
            "errors": self._stats["errors"],
            "last_command": self._stats["last_cmd"],
        }

    def start(self):
        """Start the background WebSocket thread."""
        if not HAS_WEBSOCKETS:
            return
        if self._thread and self._thread.is_alive():
            return  # Already running

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        log.info(f"Sim-to-Real bridge started → {self.url}")

    def stop(self):
        """Stop the background WebSocket thread."""
        self._stop_event.set()
        self._connected = False
        self._hw_connected = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        log.info("Sim-to-Real bridge stopped")

    def _run_loop(self):
        """Background thread: runs asyncio event loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect_loop())
        except Exception as e:
            log.error(f"Bridge thread error: {e}")
        finally:
            self._loop.close()
            self._connected = False

    async def _connect_loop(self):
        """Reconnect loop — keeps trying to connect."""
        while not self._stop_event.is_set():
            try:
                async with websockets.connect(self.url) as ws:
                    self._connected = True
                    log.info("Bridge connected to server")
                    await self._message_loop(ws)
            except (ConnectionRefusedError, OSError) as e:
                self._connected = False
                self._hw_connected = False
                log.debug(f"Bridge connection failed: {e}")
            except Exception as e:
                self._connected = False
                log.warning(f"Bridge error: {e}")

            if not self._stop_event.is_set():
                await asyncio.sleep(self.reconnect_interval)

    async def _message_loop(self, ws):
        """Send queued commands and receive status from bridge server."""
        send_task = asyncio.create_task(self._sender(ws))
        recv_task = asyncio.create_task(self._receiver(ws))
        try:
            done, pending = await asyncio.wait(
                [send_task, recv_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
        except Exception:
            pass
        finally:
            self._connected = False

    async def _sender(self, ws):
        """Drain the command queue and send to bridge."""
        while not self._stop_event.is_set():
            while self._queue:
                msg = self._queue.popleft()
                try:
                    await ws.send(msg)
                    self._stats["sent"] += 1
                except Exception as e:
                    self._stats["errors"] += 1
                    raise  # Triggers reconnect
            await asyncio.sleep(0.01)  # 10ms poll

    async def _receiver(self, ws):
        """Receive status messages from bridge server."""
        async for message in ws:
            try:
                data = json.loads(message)
                if data.get("type") == "bridge_status":
                    self._hw_connected = data.get("hardware_connected", False)
                elif data.get("type") == "ack":
                    pass  # Could track per-command acks
            except json.JSONDecodeError:
                pass


# ==========================================
# SINGLETON INSTANCE
# ==========================================
# Global bridge instance — import and use from anywhere
_bridge: Optional[HardwareBridge] = None


def get_bridge(url: str = "ws://localhost:8765/controller") -> HardwareBridge:
    """Get or create the global HardwareBridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = HardwareBridge(url=url, enabled=False)
    return _bridge
