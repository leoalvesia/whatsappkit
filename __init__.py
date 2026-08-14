"""WhatsApp Manager Plugin Package Entry Point."""

import sys
from pathlib import Path

# Add current directory to path to ensure whatsapp_manager can be imported
plugin_dir = str(Path(__file__).parent)
if plugin_dir not in sys.path:
    sys.path.append(plugin_dir)

from whatsapp_manager import register
from adapter import WhatsAppPlatformAdapter

try:
    # Try registering with Hermes Gateway platform registry if available
    from gateway.platforms import register_platform_adapter
    register_platform_adapter("whatsapp", WhatsAppPlatformAdapter)
except ImportError:
    try:
        from hermes.gateway.platforms import register_platform_adapter
        register_platform_adapter("whatsapp", WhatsAppPlatformAdapter)
    except ImportError:
        pass


