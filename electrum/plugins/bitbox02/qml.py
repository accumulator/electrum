from typing import TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal, QObject

from electrum.i18n import _
from electrum.gui.qml.qewizard import QENewWalletWizard
from electrum.hw_wallet.qml import QmlHandlerBase, QmlPluginBase

from .bitbox02 import BitBox02Plugin

if TYPE_CHECKING:
    from electrum.hw_wallet import HW_PluginBase


class BitBox02Handler(QmlHandlerBase):
    MESSAGE_DIALOG_TITLE = _("BitBox02 Status")

    password_available = pyqtSignal()

    def __init__(self, device_uid: str, parent=None):
        super(BitBox02Handler, self).__init__(device_uid, parent)


class Plugin(BitBox02Plugin, QmlPluginBase):
    handler_class = BitBox02Handler

    def create_handler(self, device_uid: str, parent: QObject = None) -> QmlHandlerBase:
        return QmlPluginBase.create_handler(self, device_uid, parent)

    # insert bitbox02 pages in new wallet wizard
    def extend_wizard(self, wizard: 'QENewWalletWizard'):
        super().extend_wizard(wizard)
        views = {
            # 'bitbox02_start': {'gui': WCBitbox02ScriptAndDerivation},
            # 'bitbox02_xpub': {'gui': WCHWXPub},
            # 'bitbox02_not_initialized': {'gui': WCHWUninitialized},
            'bitbox02_unlock': {'gui': 'WCHWUnlock'}
        }
        wizard.navmap_merge(views)

    # @hook
    # def init_qml(self, app):
    #     self.logger.debug(f'init_qml hook called, gui={str(type(app))}')
    #     self.logger.debug(f'app={self._app!r}, so={self.so!r}')
    #     self._app = app
    #     # important: QSignalObject needs to be parented, as keeping a ref
    #     # in the plugin is not enough to avoid gc
    #     self.so = Plugin.QSignalObject(self, self._app)
