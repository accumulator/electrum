import sys
import threading
from typing import TYPE_CHECKING, Tuple, List, Optional

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtCore import Qt, QAbstractListModel, QModelIndex

from electrum.logging import get_logger
from electrum.i18n import _
from electrum.plugin import HardwarePluginLibraryUnavailable

from .util import QtEventListener

if TYPE_CHECKING:
    from electrum.plugin import DeviceInfo


class QEHardwareListModel(QAbstractListModel, QtEventListener):
    _logger = get_logger(__name__)

    scanComplete = pyqtSignal()
    scanFailed = pyqtSignal([str, str], arguments=['code', 'message'])
    busyChanged = pyqtSignal()
    busyMsgChanged = pyqtSignal()

    # define listmodel rolemap
    _ROLE_NAMES=('device_uid', 'plugin', 'model_name', 'label')
    _ROLE_KEYS = range(Qt.ItemDataRole.UserRole, Qt.ItemDataRole.UserRole + len(_ROLE_NAMES))
    _ROLE_MAP  = dict(zip(_ROLE_KEYS, [bytearray(x.encode()) for x in _ROLE_NAMES]))
    _ROLE_RMAP = dict(zip(_ROLE_NAMES, _ROLE_KEYS))

    def __init__(self, parent=None, *, plugins):
        QAbstractListModel.__init__(self, parent)
        self.plugins = plugins
        self._busy = False
        self._busy_msg = ''
        self._devices = []
        self.devices_found = None
        self.scanComplete.connect(lambda: self.update_devices())
        self.initModel()

    def rowCount(self, index):
        return len(self._devices)

    # also expose rowCount as a property
    countChanged = pyqtSignal()
    @pyqtProperty(int, notify=countChanged)
    def count(self):
        return self.rowCount(0)

    def roleNames(self):
        return self._ROLE_MAP

    def data(self, index, role):
        device = self._devices[index.row()]
        role_index = role - Qt.ItemDataRole.UserRole

        try:
            value = device[self._ROLE_NAMES[role_index]]
        except KeyError as e:
            self._logger.error(f'non-existing key "{self._ROLE_NAMES[role_index]}" requested')
            value = None

        if isinstance(value, (bool, list, int, str)) or value is None:
            return value
        return str(value)

    @pyqtProperty(bool, notify=busyChanged)
    def busy(self):
        return self._busy

    @busy.setter
    def busy(self, is_busy):
        if self._busy != is_busy:
            self._busy = is_busy
            self.busyChanged.emit()

    @pyqtProperty(bool, notify=busyMsgChanged)
    def busyMsg(self):
        return self._busy_msg

    @busyMsg.setter
    def busyMsg(self, busy_msg):
        if self._busy_msg != busy_msg:
            self._busy_msg = busy_msg
            # self.on_updated()
            self.busyMsgChanged.emit()

    def clear(self):
        self.beginResetModel()
        self._devices = []
        self.endResetModel()
        self.countChanged.emit()

    def device_to_model(self, device: Tuple[str, 'DeviceInfo']):
        plugin, device_info = device
        return {
            'device_uid': device_info.device.id_,
            'label': device_info.label_for_device_select(),
            'model_name': device_info.model_name,
            'plugin': plugin,
            'device_info': device_info
        }

    @pyqtSlot()
    def initModel(self):
        self._logger.debug('retrieving hww list')
        self.scan_devices()

    def update_devices(self):
        self.clear()
        if self.devices_found:
            self.beginInsertRows(QModelIndex(), 0, len(self.devices_found) - 1)
            self._devices = []
            for device in self.devices_found:
                self._devices.append(self.device_to_model(device))
            self.endInsertRows()
        self.countChanged.emit()

    def get_device_info(self, device_uid: str) -> Optional['DeviceInfo']:
        for device in self._devices:
            if device['device_uid'] == device_uid:
                return device['device_info']

    def scan_devices(self):
        self.busyMsg = _('Scanning devices...')
        self.busy = True
        self.clear()

        def scan_task():
            # check available plugins
            supported_plugins = self.plugins.get_hardware_support()
            devices = []  # type: List[Tuple[str, DeviceInfo]]
            devmgr = self.plugins.device_manager
            debug_msg = ''

            def failed_getting_device_infos(name, e):
                nonlocal debug_msg
                err_str_oneline = ' // '.join(str(e).splitlines())
                self._logger.warning(f'error getting device infos for {name}: {err_str_oneline}')
                _indented_error_msg = '    '.join([''] + str(e).splitlines(keepends=True))
                debug_msg += f'  {name}: (error getting device infos)\n{_indented_error_msg}\n'

            # scan devices
            try:
                scanned_devices = devmgr.scan_devices()
            except BaseException as e:
                debug_msg = '  {}:\n    {}'.format(_('Error scanning devices'), e)
            else:
                for splugin in supported_plugins:
                    name, plugin = splugin.name, splugin.plugin
                    # plugin init errored?
                    if not plugin:
                        e = splugin.exception
                        indented_error_msg = '    '.join([''] + str(e).splitlines(keepends=True))
                        debug_msg += f'  {name}: (error during plugin init)\n'
                        debug_msg += '    {}\n'.format(_('You might have an incompatible library.'))
                        debug_msg += f'{indented_error_msg}\n'
                        continue
                    # see if plugin recognizes 'scanned_devices'
                    try:
                        # FIXME: side-effect: this sets client.handler
                        device_infos = devmgr.list_pairable_device_infos(
                            handler=None, plugin=plugin, devices=scanned_devices, include_failing_clients=True)
                    except HardwarePluginLibraryUnavailable as e:
                        failed_getting_device_infos(name, e)
                        continue
                    except BaseException as e:
                        self._logger.exception('')
                        failed_getting_device_infos(name, e)
                        continue
                    device_infos_failing = list(filter(lambda di: di.exception is not None, device_infos))
                    for di in device_infos_failing:
                        self._logger.info(f'failing {name} {repr(di.exception)}')
                        failed_getting_device_infos(name, di.exception)
                    device_infos_working = list(filter(lambda di: di.exception is None, device_infos))
                    devices += list(map(lambda x: (name, x), device_infos_working))
            if not debug_msg:
                debug_msg = '  {}'.format(_('No exceptions encountered.'))
            if not devices:
                msg = (_('No hardware device detected.') + '\n\n')
                if sys.platform == 'win32':
                    msg += _('If your device is not detected on Windows, go to "Settings", "Devices", "Connected devices", '
                             'and do "Remove device". Then, plug your device again.') + '\n'
                    msg += _('While this is less than ideal, it might help if you run Electrum as Administrator.') + '\n'
                else:
                    msg += _('On Linux, you might have to add a new permission to your udev rules.') + '\n'
                msg += '\n\n'
                msg += _('Debug message') + '\n' + debug_msg

                self.scanFailed.emit('no_devices', msg)
                self.busy = False
                return

            # select device
            self.devices_found = devices
            self.scanComplete.emit()
            self.busy = False

        t = threading.Thread(target=scan_task, daemon=True)
        t.start()
