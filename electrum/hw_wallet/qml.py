#!/usr/bin/env python3
# -*- mode: python -*-
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2025  The Electrum developers
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import os
import threading
from functools import partial
from typing import TYPE_CHECKING, Union, Optional, Sequence, Type, Dict, Callable

import hid
from PyQt6.QtCore import QObject, pyqtSignal, Qt, pyqtSlot, QThread

from electrum.i18n import _
from electrum.logging import Logger
from electrum.util import UserCancelled, UserFacingException, ChoiceItem
from electrum.plugin import hook, MissingLibrariesException, Device

from electrum.gui.common_qt.util import TaskThread

from .plugin import OutdatedHwFirmwareException, HW_PluginBase, HardwareHandlerBase

if TYPE_CHECKING:
    from electrum.wallet import Abstract_Wallet
    from electrum.keystore import Hardware_KeyStore
    from electrum.gui.qml import ElectrumQmlApplication


class QmlHandlerBase(HardwareHandlerBase, QObject, Logger):
    """An interface between the GUI (here, QML) and the device handling
    logic for handling I/O."""

    passphrase_signal = pyqtSignal(object, object)
    message_signal = pyqtSignal(str)

    error_signal = pyqtSignal(str)
    word_signal = pyqtSignal(object)
    clear_signal = pyqtSignal()
    query_signal = pyqtSignal(object, object)
    yes_no_signal = pyqtSignal(object)
    status_signal = pyqtSignal(object)

    def __init__(self, device: str, parent=None):
        QObject.__init__(self, parent)
        Logger.__init__(self)

        # assert parent.thread() == QThread.currentThread()  # init in same thread as where parent lives

        # self.message_signal.connect(self.message_dialog)
        self.passphrase_signal.connect(self.passphrase_dialog)
        self.word_signal.connect(self.word_dialog)
        self.query_signal.connect(self.win_query_choice)
        self.yes_no_signal.connect(self.win_yes_no_question)
        self.status_signal.connect(self._update_status)
        self.device = device
        self.dialog = None
        self.plugin = None
        self.done = threading.Event()

        self._on_cancel_message = None

        if 'ANDROID_DATA' in os.environ:
            from jnius import autoclass
            from electrum.gui.qml.android import PythonUsbListenerImpl

            self.jpythonActivity = autoclass('org.kivy.android.PythonActivity').mActivity
            self.usblistener = PythonUsbListenerImpl()
            self.usblistener.on_usb_open = self.on_android_usb_open
            self.usblistener.on_usb_not_open = self.on_android_usb_not_open
            self.jpythonActivity.registerPythonUsbListener(self.usblistener)
            # TODO unregister at destruction
            self.fd = None

    def open_hid_device(self, device: 'Device') -> hid.device:
        # special handling for android, potential user interaction.
        hid_device = hid.device()
        if 'ANDROID_DATA' in os.environ:
            event = threading.Event()
            event.clear()
            self.android_usb_cb_info = (int(device.id_), event)
            self.jpythonActivity.openUsbDevice(int(device.id_))
            event.wait()  # TODO: timeout
            if self.fd is None:
                raise Exception('no fd')
            hid_device.open_fd(self.fd, 0)
        else:
            hid_device.open_path(device.path)
        return hid_device

    def on_android_usb_open(self, usb_id: int, fd: int):
        _usb_id, event = self.android_usb_cb_info
        if usb_id != _usb_id:
            return
        self.logger.info(f'ANDROID USB OPENED: {usb_id=} {fd=}')
        self.fd = fd
        event.set()

    def on_android_usb_not_open(self, usb_id: int):
        _usb_id, event = self.android_usb_cb_info
        if usb_id != _usb_id:
            return
        self.logger.info(f'ANDROID USB NOT OPENED: {usb_id=}')
        self.fd = None
        event.set()

    def update_status(self, paired):
        self.status_signal.emit(paired)

    def _update_status(self, paired):
        pass
        # if hasattr(self, 'button'):
        #     button = self.button
        #     icon_bytes = button.icon_paired if paired else button.icon_unpaired
        #     icon = read_QIcon_from_bytes(icon_bytes)
        #     button.setIcon(icon)

    def query_choice(self, msg: str, choices: Sequence[ChoiceItem]):
        raise Exception('query_choice')
        # self.done.clear()
        # self.query_signal.emit(msg, choices)
        # self.done.wait()
        # return self.choice

    def yes_no_question(self, msg):
        raise Exception('yes_no_question')
        # self.done.clear()
        # self.yes_no_signal.emit(msg)
        # self.done.wait()
        # return self.ok

    def show_message(self, msg, on_cancel: Callable[[], None] = None):
        self._on_cancel_message = on_cancel
        self.message_signal.emit(msg)

    @pyqtSlot()
    def cancelShowMessage(self):
        if self._on_cancel_message:
            self._on_cancel_message()

    def show_error(self, msg, blocking=False):
        self.error_signal.emit(msg)
        # raise Exception('show_error')
        # self.done.clear()
        # self.error_signal.emit(msg, blocking)
        # if blocking:
        #     self.done.wait()

    def finished(self):
        self._on_cancel_message = None
        self.clear_signal.emit()

    def get_word(self, msg):
        raise Exception('get_word')
        # self.done.clear()
        # self.word_signal.emit(msg)
        # self.done.wait()
        # return self.word

    def get_passphrase(self, msg, confirm):
        raise Exception('get_passphrase')
        # self.done.clear()
        # self.passphrase_signal.emit(msg, confirm)
        # self.done.wait()
        # return self.passphrase

    def passphrase_dialog(self, msg, confirm):
        # If confirm is true, require the user to enter the passphrase twice
        raise Exception('passphrase_dialog')
        # parent = self.top_level_window()
        # d = WindowModalDialog(parent, _("Enter Passphrase"))
        # if confirm:
        #     OK_button = OkButton(d)
        #     playout = PasswordLayout(msg=msg, kind=PW_PASSPHRASE, OK_button=OK_button)
        #     vbox = QVBoxLayout()
        #     vbox.addLayout(playout.layout())
        #     vbox.addLayout(Buttons(CancelButton(d), OK_button))
        #     d.setLayout(vbox)
        #     passphrase = playout.new_password() if d.exec() else None
        # else:
        #     pw = PasswordLineEdit()
        #     pw.setMinimumWidth(200)
        #     vbox = QVBoxLayout()
        #     vbox.addWidget(WWLabel(msg))
        #     vbox.addWidget(pw)
        #     vbox.addLayout(Buttons(CancelButton(d), OkButton(d)))
        #     d.setLayout(vbox)
        #     passphrase = pw.text() if d.exec() else None
        # self.passphrase = passphrase
        # self.done.set()

    def word_dialog(self, msg):
        raise Exception('word_dialog')
        # dialog = WindowModalDialog(self.top_level_window(), "")
        # hbox = QHBoxLayout(dialog)
        # hbox.addWidget(QLabel(msg))
        # text = QLineEdit()
        # text.setMaximumWidth(12 * char_width_in_lineedit())
        # text.returnPressed.connect(dialog.accept)
        # hbox.addWidget(text)
        # hbox.addStretch(1)
        # dialog.exec()  # Firmware cannot handle cancellation
        # self.word = text.text()
        # self.done.set()

    MESSAGE_DIALOG_TITLE = None  # type: Optional[str]
    def message_dialog(self, msg, on_cancel=None):
        raise Exception('message_dialog')
        # self.clear_dialog()
        # title = self.MESSAGE_DIALOG_TITLE
        # if title is None:
        #     title = _('Please check your {} device').format(self.device)
        # self.dialog = dialog = WindowModalDialog(self.top_level_window(), title)
        # label = QLabel(msg)
        # label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        # vbox = QVBoxLayout(dialog)
        # vbox.addWidget(label)
        # if on_cancel:
        #     dialog.rejected.connect(on_cancel)
        #     vbox.addLayout(Buttons(CancelButton(dialog)))
        # dialog.show()

    def win_query_choice(self, msg: str, choices: Sequence[ChoiceItem]):
        raise Exception('win_query_dialog')
        # try:
        #     self.choice = self.win.query_choice(msg, choices)
        # except UserCancelled:
        #     self.choice = None
        # self.done.set()

    def win_yes_no_question(self, msg):
        raise Exception('win_yes_no_dialog')
        # self.ok = self.win.question(msg)
        # self.done.set()

    @pyqtSlot()
    def abort(self):
        self.logger.info('aborting operation..')
        # find client by device_uid
        from electrum.gui.qml.qedaemon import QEDaemon
        client = QEDaemon.instance.plugins.device_manager._client_by_id(self.device)
        client.abort()

    @pyqtSlot(str, result=str)
    def icon(self, id_):
        try:
            return {
                'paired': os.path.join(self.plugin.fs_root, self.plugin.icon_paired),
                'unpaired': os.path.join(self.plugin.fs_root, self.plugin.icon_unpaired),
            }[id_]
        except Exception as e:
            return ''


class QmlPluginBase(Logger):
    handler_class: Type['QmlHandlerBase']

    # class scoped handler_map stores device_uid <-> handler_class instance associations
    handler_map: Dict[str, 'QmlHandlerBase'] = {}

    @hook
    def load_wallet(self: Union['QmlPluginBase', HW_PluginBase], wallet: 'Abstract_Wallet'):
        relevant_keystores = [keystore for keystore in wallet.get_keystores()
                              if isinstance(keystore, self.keystore_class)]
        if not relevant_keystores:
            return
        for keystore in relevant_keystores:
            if not self.libraries_available:
                message = keystore.plugin.get_library_not_available_message()
                raise MissingLibrariesException(message)

            # tooltip = self.device + '\n' + (keystore.label or 'unnamed')
            # cb = partial(self._on_status_bar_button_click, window=window, keystore=keystore)
            # sb = window.statusBar()
            # icon = read_QIcon_from_bytes(self.read_file(self.icon_unpaired))
            # button = StatusBarButton(icon, tooltip, cb, sb.height())
            # button.icon_paired = self.read_file(self.icon_paired)
            # button.icon_unpaired = self.read_file(self.icon_unpaired)
            # sb.addPermanentWidget(button)
            # handler = self.create_handler(window)
            # handler.button = button
            # keystore.handler = handler
            # keystore.thread = TaskThread(window, on_error=partial(self.on_task_thread_error, window, keystore))
            # self.add_show_address_on_hw_device_button_for_receive_addr(wallet, keystore, window)
        # Trigger pairings
        devmgr = self.device_manager()
        trigger_pairings = partial(devmgr.trigger_pairings, relevant_keystores, allow_user_interaction=True)
        some_keystore = relevant_keystores[0]
        some_keystore.thread.add(trigger_pairings)

    # def _on_status_bar_button_click(self, *, window: 'ElectrumQmlApplication', keystore: 'Hardware_KeyStore'):
    #     try:
    #         self.show_settings_dialog(window=window, keystore=keystore)
    #     except (UserFacingException, UserCancelled) as e:
    #         exc_info = (type(e), e, e.__traceback__)
    #         self.on_task_thread_error(window=window, keystore=keystore, exc_info=exc_info)

    def on_task_thread_error(self: Union['QmlPluginBase', HW_PluginBase], window: 'ElectrumQmlApplication',
                             keystore: 'Hardware_KeyStore', exc_info):
        e = exc_info[1]
        if isinstance(e, OutdatedHwFirmwareException):
            if window.question(e.text_ignore_old_fw_and_continue(), title=_("Outdated device firmware")):
                self.set_ignore_outdated_fw()
                # will need to re-pair
                devmgr = self.device_manager()

                def re_pair_device():
                    device_id = self.choose_device(window, keystore)
                    devmgr.unpair_id(device_id)
                    self.get_client(keystore)

                keystore.thread.add(re_pair_device)
            return
        else:
            window.on_error(exc_info)

    def choose_device(self: Union['QmlPluginBase', HW_PluginBase], window: 'ElectrumQmlApplication',
                      keystore: 'Hardware_KeyStore') -> Optional[str]:
        """This dialog box should be usable even if the user has
        forgotten their PIN or it is in bootloader mode."""
        assert window.gui_thread != threading.current_thread(), 'must not be called from GUI thread'
        device_id = self.device_manager().id_by_pairing_code(keystore.pairing_code())
        if not device_id:
            try:
                info = self.device_manager().select_device(self, keystore.handler, keystore)
            except UserCancelled:
                return
            device_id = info.device.id_
        return device_id

    # def show_settings_dialog(self, window: 'ElectrumQmlApplication', keystore: 'Hardware_KeyStore') -> None:
    #     # default implementation (if no dialog): just try to connect to device
    #     def connect():
    #         device_id = self.choose_device(window, keystore)
    #
    #     keystore.thread.add(connect)

    # def add_show_address_on_hw_device_button_for_receive_addr(
    #         self,
    #         wallet: 'Abstract_Wallet',
    #         keystore: 'Hardware_KeyStore',
    #         main_window: 'ElectrumQmlApplication'
    # ):
    #     plugin = keystore.plugin
    #     receive_tab = main_window.receive_tab
    #
    #     def show_address():
    #         addr = str(receive_tab.addr)
    #         keystore.thread.add(partial(plugin.show_address, wallet, addr, keystore))
    #
    #     dev_name = f"{plugin.device} ({keystore.label})"
    #     receive_tab.toolbar_menu.addAction(read_QIcon("eye1.png"), _("Show address on {}").format(dev_name), show_address)

    # def create_handler(self, device_uid: str, parent=None) -> 'QmlHandlerBase':
    #     raise NotImplementedError()

    def create_handler(self, device_uid: str, parent: QObject = None) -> QmlHandlerBase:
        if not self.handler_class:
            raise RuntimeError('HANDLER_CLASS undefined')
        if handler := self.handler_map.get(device_uid):
            # self.logger.debug(f'handler for {device_uid} exists')
            return handler
        else:
            # self.logger.debug(f'new handler for {device_uid}')
            handler = self.handler_class(device_uid, parent)
            handler.plugin = self
            self.handler_map[device_uid] = handler
            return handler


    # def _add_menu_action(self, menu: QMenu, address: str, wallet: 'Abstract_Wallet'):
    #     if not wallet.is_mine(address):
    #         return
    #     for keystore in wallet.get_keystores():
    #         if type(keystore) == self.keystore_class:
    #
    #             def show_address(keystore=keystore):
    #                 keystore.thread.add(partial(self.show_address, wallet, address, keystore=keystore))
    #
    #             device_name = "{} ({})".format(self.device, keystore.label)
    #             menu.addAction(read_QIcon("eye1.png"), _("Show address on {}").format(device_name), show_address)
