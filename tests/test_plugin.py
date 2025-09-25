import os
import sys
import threading
import time

from types import SimpleNamespace
from unittest import mock

from electrum import util
from electrum import plugin as plugin_module
from electrum.crypto import sha256
from electrum.plugin import (Plugins, IncorrectPluginHash, PluginMetadata, DeviceMgr, _hwd_comms_executor,
                             runs_in_hwd_thread)
from electrum.zip_importer import MemoryZipImporter
from electrum.simple_config import SimpleConfig

from electrum_ecc import ECPrivkey

from . import ElectrumTestCase
from .test_zip_importer import PLUGIN_NAME, make_plugin_zip


class PluginLoaderTestCase(ElectrumTestCase):
    """Tests that an authorized plugin is loaded from the bytes whose signature
    was verified, and not from whatever happens to be on disk at import time."""

    def setUp(self):
        super().setUp()
        self.config = SimpleConfig({'electrum_path': self.electrum_path})
        self.privkey = ECPrivkey(sha256(b'plugin zip unit test key'))
        self.plugins_dir = os.path.join(self.electrum_path, 'plugins')
        util.make_dir(self.plugins_dir)
        self.zip_path = os.path.join(self.plugins_dir, f'{PLUGIN_NAME}.zip')
        self._patcher = mock.patch.object(
            Plugins, 'get_pubkey_bytes',
            lambda _self: (self.privkey.get_public_key_bytes(), bytes(32)))
        self._patcher.start()
        self.plugins = None

    def tearDown(self):
        self._patcher.stop()
        self._stop_plugins()
        super().tearDown()

    def _stop_plugins(self) -> None:
        if self.plugins is not None:
            self.plugins.stop()
            self.plugins.stopped_event.wait()
            self.plugins = None
        # the import system is global state; undo what the test did to it
        for modname in [m for m in sys.modules if m.startswith('electrum_external_plugins')]:
            del sys.modules[modname]
        for finder in [f for f in sys.meta_path if isinstance(f, MemoryZipImporter)]:
            sys.meta_path.remove(finder)
        plugin_module._zip_importers.clear()

    def _start_plugins(self) -> Plugins:
        self.plugins = Plugins(self.config, gui_name='cmdline')
        return self.plugins

    def _authorize(self, plugins: Plugins) -> None:
        plugins.authorize_plugin(PLUGIN_NAME, self.privkey)

    def _replace_zip_on_disk(self, secret: str = 'evil') -> None:
        evil = os.path.join(self.electrum_path, 'evil.zip')
        make_plugin_zip(evil, secret=secret)
        os.replace(evil, self.zip_path)

    # --- the regression this guards against ---

    def test_import_raises_after_file_replaced(self):
        make_plugin_zip(self.zip_path, secret='benign')
        plugins = self._start_plugins()
        self._authorize(plugins)
        self.assertTrue(plugins.is_authorized(PLUGIN_NAME))
        self._replace_zip_on_disk('evil')
        with self.assertRaises(IncorrectPluginHash):
            plugin = plugins.load_plugin_by_name(PLUGIN_NAME)

    def test_read_file_raises_after_file_replaced(self):
        make_plugin_zip(self.zip_path, secret='benign')
        plugins = self._start_plugins()
        self._authorize(plugins)
        self._replace_zip_on_disk('evil')
        with self.assertRaises(IncorrectPluginHash):
            plugins.read_file(PLUGIN_NAME, 'icon.txt')

    def test_tampered_plugin_is_not_authorized(self):
        make_plugin_zip(self.zip_path, secret='benign')
        plugins = self._start_plugins()
        self._authorize(plugins)
        # replace on disk
        self._replace_zip_on_disk('evil')
        self.assertTrue(plugins.is_authorized(PLUGIN_NAME))
        # as if electrum had been restarted
        plugins.stop()
        plugins = self._start_plugins()
        self.assertFalse(plugins.is_authorized(PLUGIN_NAME))
        self.assertIsNone(plugins.load_plugin_by_name(PLUGIN_NAME))

    def test_unsigned_plugin_is_not_authorized(self):
        make_plugin_zip(self.zip_path, secret='benign')
        plugins = self._start_plugins()
        self.assertFalse(plugins.is_authorized(PLUGIN_NAME))
        self.assertIsNone(plugins.load_plugin_by_name(PLUGIN_NAME))

    def test_manifest_hash_describes_the_bytes_it_was_read_from(self):
        blob = make_plugin_zip(self.zip_path, secret='benign')
        plugins = self._start_plugins()
        manifest = plugins.read_manifest(self.zip_path)
        self.assertEqual(sha256(blob).hex(), manifest.zip_hash_sha256)

    # --- upgrade ---

    def _download_new_version(self, secret: str) -> PluginMetadata:
        path = os.path.join(self.electrum_path, f'{PLUGIN_NAME}-{secret}.zip')
        make_plugin_zip(path, secret=secret)
        return self.plugins.read_manifest(path)

    def test_upgrade_keeps_config(self):
        make_plugin_zip(self.zip_path, secret='v1')
        plugins = self._start_plugins()
        self._authorize(plugins)
        plugins.disable(PLUGIN_NAME)
        plugins.upgrade_external_plugin(self._download_new_version('v2'), self.privkey)
        # what WalletDB.prune_uninstalled_plugin_data() looks at
        self.assertIn(PLUGIN_NAME, self.config.get_installed_plugins())
        self.assertFalse(self.config.get(f'plugins.{PLUGIN_NAME}.enabled'))
        self.assertTrue(plugins.is_authorized(PLUGIN_NAME))
        # the new file keeps its name, the old one is removed
        self.assertEqual([f'{PLUGIN_NAME}-v2.zip'], os.listdir(self.plugins_dir))

    def test_upgrade_takes_effect_after_restart(self):
        make_plugin_zip(self.zip_path, secret='v1')
        plugins = self._start_plugins()
        self._authorize(plugins)
        p = plugins.load_plugin_by_name(PLUGIN_NAME)
        self.assertEqual('v1', sys.modules[p.__module__].SECRET)
        plugins.upgrade_external_plugin(self._download_new_version('v2'), self.privkey)
        # the old code keeps running from memory
        self.assertIs(p, plugins.load_plugin_by_name(PLUGIN_NAME))
        self.assertEqual(b'v1', plugins.read_file(PLUGIN_NAME, 'icon.txt'))
        # as if electrum had been restarted
        self._stop_plugins()
        plugins = self._start_plugins()
        self.assertTrue(plugins.is_authorized(PLUGIN_NAME))
        p = plugins.load_plugin_by_name(PLUGIN_NAME)
        self.assertEqual('v2', sys.modules[p.__module__].SECRET)

    def test_upgrade_refuses_bytes_other_than_those_shown(self):
        make_plugin_zip(self.zip_path, secret='v1')
        plugins = self._start_plugins()
        self._authorize(plugins)
        manifest = self._download_new_version('v2')
        make_plugin_zip(manifest.path, secret='evil')
        with self.assertRaises(IncorrectPluginHash):
            plugins.upgrade_external_plugin(manifest, self.privkey)
        self.assertTrue(plugins.is_authorized(PLUGIN_NAME))


class FakeHandler:
    def __init__(self):
        self.statuses = []

    def update_status(self, paired):
        self.statuses.append(paired)


class FakeClient:
    def __init__(self, handler):
        self.handler = handler
        self.aborted = False
        self.closed_on = None  # name of the thread that closed the client
        self.usable = True

    def has_usable_connection_with_device(self):
        return self.usable

    def abort(self):
        self.aborted = True

    @runs_in_hwd_thread  # like the real clients
    def close(self):
        self.closed_on = threading.current_thread().name


class DeviceMgrTestCase(ElectrumTestCase):

    def setUp(self):
        super().setUp()
        self.devmgr = DeviceMgr(SimpleConfig({'electrum_path': self.electrum_path}))
        self.handler = FakeHandler()
        self.client = FakeClient(self.handler)
        self.devmgr.clients[self.client] = 'dev1'
        self.devmgr.pairing_code_to_id['bitbox02/abc'] = 'dev1'

    def _block_hwd_thread(self) -> threading.Event:
        """Keeps the hwd thread busy until the returned event is set, like an operation waiting on the device."""
        release = threading.Event()
        _hwd_comms_executor.submit(release.wait, 10)
        self.addCleanup(release.set)
        return release

    @staticmethod
    def _drain_hwd_thread():
        _hwd_comms_executor.submit(lambda: None).result(timeout=10)

    def test_on_device_removed_does_not_wait_for_the_hwd_thread(self):
        release = self._block_hwd_thread()
        t0 = time.monotonic()
        self.devmgr.on_device_removed('dev1')
        self.assertLess(time.monotonic() - t0, 1)
        # invalidated right away
        self.assertIsNone(self.devmgr._client_by_id('dev1'))
        self.assertIsNone(self.devmgr.id_by_pairing_code('bitbox02/abc'))
        self.assertTrue(self.client.aborted)
        self.assertEqual([False], self.handler.statuses)
        # closed on the hwd thread, once that is free
        self.assertIsNone(self.client.closed_on)
        release.set()
        self._drain_hwd_thread()
        self.assertTrue(self.client.closed_on.startswith('hwd_comms_thread'))

    def test_on_device_removed_unknown_id(self):
        self.devmgr.on_device_removed('dev2')
        self.assertIs(self.client, self.devmgr._client_by_id('dev1'))
        self.assertFalse(self.client.aborted)
        self.assertEqual([], self.handler.statuses)

    def test_on_device_removed_without_handler(self):
        self.client.handler = None
        self.devmgr.on_device_removed('dev1')
        self.assertIsNone(self.devmgr._client_by_id('dev1'))
        self.assertTrue(self.client.aborted)

    def test_on_device_removed_close_fails(self):
        def close():
            raise OSError('device gone')
        self.client.close = close
        with self.assertLogs(self.devmgr.logger, level='INFO') as logs:
            self.devmgr.on_device_removed('dev1')
            self._drain_hwd_thread()
        self.assertTrue(any('failed to close hardware client cleanly' in line for line in logs.output))

    def _scan(self, *device_ids):
        """Scans, and returns the thread that closed the client by the end of that hwd task, if any.
        Like client_for_keystore, which scans and then creates new clients in one hwd task."""
        devices = [SimpleNamespace(id_=id_) for id_ in device_ids]

        def scan():
            self.devmgr.scan_devices()
            return self.client.closed_on

        with mock.patch.object(self.devmgr, 'platform_scan_devices', return_value=devices):
            return _hwd_comms_executor.submit(scan).result(timeout=10)

    def test_scan_devices_removes_unplugged_client(self):
        closed_on = self._scan()
        self.assertTrue(closed_on.startswith('hwd_comms_thread'))
        self.assertIsNone(self.devmgr._client_by_id('dev1'))
        self.assertIsNone(self.devmgr.id_by_pairing_code('bitbox02/abc'))
        self.assertEqual([False], self.handler.statuses)
        self.assertFalse(self.client.aborted)  # not on the hwd thread

    def test_scan_devices_removes_unusable_client(self):
        # still plugged in: the client must have released the device before a new one is created for it
        self.client.usable = False
        self.assertIsNotNone(self._scan('dev1'))
        self.assertIsNone(self.devmgr._client_by_id('dev1'))
        self.assertEqual([False], self.handler.statuses)

    def test_scan_devices_keeps_connected_client(self):
        self.assertIsNone(self._scan('dev1'))
        self.assertIs(self.client, self.devmgr._client_by_id('dev1'))
        self.assertEqual([], self.handler.statuses)

    def test_unpair_id_closes_before_returning(self):
        self.devmgr.unpair_id('dev1')
        self.assertIsNotNone(self.client.closed_on)
        self.assertIsNone(self.devmgr._client_by_id('dev1'))
        self.assertIsNone(self.devmgr.id_by_pairing_code('bitbox02/abc'))
