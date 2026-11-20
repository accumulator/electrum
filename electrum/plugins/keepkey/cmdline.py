from electrum.plugin import hook
from electrum.hw_wallet import CmdLineHandler, constant_handler_delegate
from .keepkey import KeepKeyPlugin

class Plugin(KeepKeyPlugin):
    handler = CmdLineHandler()
    @hook
    def init_keystore(self, keystore):
        if not isinstance(keystore, self.keystore_class):
            return
        keystore.set_handler_delegate(constant_handler_delegate(self.handler))

    def create_handler(self, window):
        return self.handler
