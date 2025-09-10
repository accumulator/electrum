from PyQt6.QtCore import pyqtSignal, QObject

from electrum.i18n import _
from electrum.gui.qml.qewizard import QENewWalletWizard
from electrum.hw_wallet.qml import QmlHandlerBase, QmlPluginBase
from electrum.plugins.trezor.trezor import TrezorPlugin


class TrezorHandler(QmlHandlerBase):
    MESSAGE_DIALOG_TITLE = _("Trezor Status")

    password_available = pyqtSignal()

    def __init__(self, device_uid: str, parent=None):
        super(TrezorHandler, self).__init__(device_uid, parent)


class Plugin(TrezorPlugin, QmlPluginBase):
    handler_class = TrezorHandler

    def create_handler(self, device_uid: str, parent: QObject = None) -> QmlHandlerBase:
        return QmlPluginBase.create_handler(self, device_uid, parent)

    # insert trezor pages in new wallet wizard
    def extend_wizard(self, wizard: 'QENewWalletWizard'):
        super().extend_wizard(wizard)
        views = {
            # 'trezor_start': {'gui': WCScriptAndDerivation},
            # 'trezor_xpub': {'gui': WCTrezorXPub},
            # 'trezor_not_initialized': {'gui': WCTrezorInitMethod},
            # 'trezor_choose_new_recover': {'gui': WCTrezorInitParams},
            # 'trezor_do_init': {'gui': WCTrezorInit},
            'trezor_unlock': {'gui': 'WCHWUnlock'},
        }
        wizard.navmap_merge(views)
