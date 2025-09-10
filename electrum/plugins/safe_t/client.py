from typing import TYPE_CHECKING

from safetlib.client import proto, BaseClient, ProtocolMixin
from .clientbase import SafeTClientBase

if TYPE_CHECKING:
    from electrum.plugin import Device


class SafeTClient(SafeTClientBase, ProtocolMixin, BaseClient):
    def __init__(self, device_descriptor: 'Device', transport, handler, plugin):
        BaseClient.__init__(self, transport=transport)
        ProtocolMixin.__init__(self, transport=transport)
        SafeTClientBase.__init__(self, device_descriptor, handler, plugin, proto)


SafeTClientBase.wrap_methods(SafeTClient)
