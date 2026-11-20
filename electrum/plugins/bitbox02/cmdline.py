from electrum.plugin import hook
from .bitbox02 import BitBox02Plugin
from electrum.hw_wallet import CmdLineHandler, constant_handler_delegate


class Plugin(BitBox02Plugin):
    handler = CmdLineHandler()
    @hook
    def init_keystore(self, keystore):
        if not isinstance(keystore, self.keystore_class):
            return
        keystore.set_handler_delegate(constant_handler_delegate(self.handler))

    def create_handler(self, window):
        return self.handler
