from typing import TYPE_CHECKING

from jnius import java_method, PythonJavaClass

from electrum.logging import get_logger

if TYPE_CHECKING:
    from typing import Callable


class PythonUsbListenerImpl(PythonJavaClass):
    __javainterfaces__ = ['org/kivy/android/PythonUsbListener']
    __javacontext__ = "app"

    def __init__(self):
        get_logger(__name__).info('CONSTRUCTOR')
        self.on_usb_open: 'Callable[[int, int], None]' = None
        self.on_usb_not_open: 'Callable[[int], None]' = None

    @java_method('(II)V', name='onUsbOpened')
    def onUsbOpened(self, android_usb_id: int, fd: int):
        get_logger(__name__).info('ON USB OPENEND')
        self.on_usb_open(android_usb_id, fd)

    @java_method('(I)V', name='onUsbNotOpened')
    def onUsbNotOpened(self, android_usb_id: int):
        get_logger(__name__).info('ON USB NOT OPENEND')
        self.on_usb_not_open(android_usb_id)
