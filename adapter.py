"""Native Hermes Platform Adapter for WhatsApp Sidecar Bridge."""

import os
import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

logger = logging.getLogger("whatsapp_manager")

try:
    from gateway.platforms.base import BasePlatformAdapter
except ImportError:
    try:
        from hermes.gateway.platforms.base import BasePlatformAdapter
    except ImportError:
        class BasePlatformAdapter:
            """Fallback Base class for standalone testing or direct invocation."""
            def __init__(self, config: Optional[Dict[str, Any]] = None):
                self.config = config or {}


class WhatsAppPlatformAdapter(BasePlatformAdapter):
    """Platform Adapter connecting Hermes Gateway to WhatsApp Baileys sidecar bridge."""

    platform_name = "whatsapp"
    default_profile = "whatsapp"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.bridge_url = os.getenv("WHATSAPP_BRIDGE_URL", "http://127.0.0.1:3000").rstrip("/")
        self._connected = False

    def connect(self) -> bool:
        """Query connection status from whatsapp-bridge."""
        try:
            url = f"{self.bridge_url}/whatsapp/status"
            req = urllib.request.Request(url, headers={"User-Agent": "Hermes-WhatsApp-Adapter/1.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    self._connected = bool(data.get("connected", False))
                    return self._connected
        except Exception:
            self._connected = False
        return False

    def disconnect(self) -> None:
        """Disconnect adapter."""
        self._connected = False

    def get_status(self) -> Dict[str, Any]:
        """Return platform status dictionary for Gateway and Web UI Dashboard."""
        connected = self.connect()
        return {
            "name": "whatsapp",
            "connected": connected,
            "status": "connected" if connected else "disconnected",
            "bridge_url": self.bridge_url,
            "details": {
                "engine": "baileys-node",
                "endpoint": f"{self.bridge_url}/whatsapp/status"
            }
        }

    def send(self, chat_id: str, content: str, **kwargs: Any) -> bool:
        """Send a text message via whatsapp-bridge, passing through security firewall."""
        try:
            from whatsapp_manager import isSystemError
            if isSystemError(content):
                logger.warning(f"[whatsapp-adapter] Error firewall blocked message to {chat_id}")
                return False
        except ImportError:
            pass

        try:
            payload = json.dumps({"chatId": chat_id, "text": content}).encode("utf-8")
            req = urllib.request.Request(
                f"{self.bridge_url}/send",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"[whatsapp-adapter] Failed to send message to {chat_id}: {e}")
            return False

    def send_poll(self, chat_id: str, name: str, values: list, selectable_count: int = 1) -> bool:
        """Send a native tap-to-vote poll via whatsapp-bridge (up to 12 options)."""
        try:
            payload = json.dumps({
                "chatId": chat_id,
                "name": name,
                "values": values,
                "selectableCount": selectable_count,
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{self.bridge_url}/send-poll",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"[whatsapp-adapter] Failed to send poll to {chat_id}: {e}")
            return False

    def send_location(self, chat_id: str, latitude: float, longitude: float, name: str = "", address: str = "") -> bool:
        """Send a location pin via whatsapp-bridge."""
        try:
            payload = json.dumps({
                "chatId": chat_id,
                "latitude": latitude,
                "longitude": longitude,
                "name": name,
                "address": address,
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{self.bridge_url}/send-location",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"[whatsapp-adapter] Failed to send location to {chat_id}: {e}")
            return False

    def send_typing(self, chat_id: str) -> bool:
        """Send typing presence indicator to chat."""
        try:
            payload = json.dumps({"chatId": chat_id}).encode("utf-8")
            req = urllib.request.Request(
                f"{self.bridge_url}/typing",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False
