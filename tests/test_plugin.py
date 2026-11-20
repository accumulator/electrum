import gc
import os
import sys
import threading
import time
import weakref

from types import SimpleNamespace
from unittest import mock

from electrum import util
from electrum import plugin as plugin_module
from electrum.crypto import sha256
from electrum.plugin import (Plugins, IncorrectPluginHash, PluginMetadata, DeviceMgr, _hwd_comms_executor,
                             runs_in_hwd_thread, run_in_hwd_thread, DeviceUnpairableError)
from electrum.hw_wallet import HW_PluginBase, HardwareClientBase, constant_handler_delegate
from electrum.keystore import Hardware_KeyStore
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


# two wallets on one device, with different passphrases (the master xpubs of BIP-32 test vectors 1 and 2)
ROOT_A, XPUB_A = 'aaaaaaaa', 'xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8'
ROOT_B, XPUB_B = 'bbbbbbbb', 'xpub661MyMwAqRbcFW31YEwpkMuc5THy2PSt5bDMsktWQcFF8syAmRUapSCGu8ED9W6oDMSgv6Zz8idoc4a6mr8BDzTJY47LJhkJ8UB7WEGuduB'


class FakeHandler:
    def __init__(self):
        self.statuses = []

    def update_status(self, paired):
        self.statuses.append(paired)


class FakePlugin:
    name = 'fake'
    device = 'Fake'
    close_keystore = HW_PluginBase.close_keystore

    def __init__(self, devmgr: DeviceMgr):
        self._devmgr = devmgr

    def device_manager(self) -> DeviceMgr:
        return self._devmgr


class FakeThread:
    def __init__(self):
        self.stopped = False

    def stop(self):
        self.stopped = True


class FakeClient(HardwareClientBase):
    def __init__(self, plugin: FakePlugin, id_: str):
        HardwareClientBase.__init__(self, plugin=plugin, device_descriptor=SimpleNamespace(id_=id_))
        self.aborted = False
        self.closed_on = None  # name of the thread that closed the client
        self.usable = True
        self.xpub = None  # what get_xpub returns, e.g. depending on the passphrase of the session

    def is_pairable(self):
        return True

    def is_initialized(self):
        return True

    def get_xpub(self, bip32_path, xtype):
        return self.xpub

    def has_usable_connection_with_device(self):
        return self.usable

    def abort(self):
        self.aborted = True

    @runs_in_hwd_thread  # like the real clients
    def close(self):
        self.closed_on = threading.current_thread().name


class FakeKeystore(Hardware_KeyStore):
    hw_type = 'fake'
    device = 'Fake'

    def __init__(self, plugin: FakePlugin, soft_device_id: str, handler: FakeHandler = None, *,
                 root_fingerprint: str = None, xpub: str = None):
        Hardware_KeyStore.__init__(self, {
            'soft_device_id': soft_device_id, 'root_fingerprint': root_fingerprint, 'xpub': xpub, 'derivation': "m/0h",
        })
        self.plugin = plugin
        if handler is not None:
            self.set_handler_delegate(constant_handler_delegate(handler))

    def opportunistically_fill_in_missing_info_from_device(self, client):
        pass

    def decrypt_message(self, sequence, message, password):
        raise NotImplementedError()

    def sign_message(self, sequence, message, password, *, script_type=None):
        raise NotImplementedError()

    def sign_transaction(self, tx, password):
        raise NotImplementedError()


class HardwareKeystoreTestCase(ElectrumTestCase):

    def test_wallet_link_does_not_keep_the_wallet_alive(self):
        class FakeWallet:
            pass
        keystore = FakeKeystore(FakePlugin(DeviceMgr(SimpleConfig({'electrum_path': self.electrum_path}))), 'abc')
        wallet = FakeWallet()
        keystore.set_wallet(wallet)
        self.assertIs(wallet, keystore.get_wallet())
        del wallet
        gc.collect()
        self.assertIsNone(keystore.get_wallet())


class DeviceMgrTestCase(ElectrumTestCase):

    def setUp(self):
        super().setUp()
        self.devmgr = DeviceMgr(SimpleConfig({'electrum_path': self.electrum_path}))
        self.plugin = FakePlugin(self.devmgr)
        self.client = self._add_client('dev1')
        self.handler = FakeHandler()
        # a wallet's keystore, paired with dev1
        self.keystore = FakeKeystore(self.plugin, 'abc', self.handler, root_fingerprint=ROOT_A, xpub=XPUB_A)
        self.devmgr.pairing_code_to_id[self.keystore.pairing_code()] = 'dev1'
        self.devmgr._keystore_to_id[self.keystore] = 'dev1'

    def _add_client(self, id_: str) -> FakeClient:
        client = run_in_hwd_thread(lambda: FakeClient(self.plugin, id_))  # clients are created on the hwd thread
        self.devmgr._clients[client] = id_
        return client

    def _client_for(self, keystore: FakeKeystore):
        return self.devmgr.client_for_keystore(self.plugin, keystore, force_pair=False, devices=[])

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
        self.assertIsNone(self.devmgr.id_by_pairing_code(self.keystore.pairing_code()))
        self.assertIsNone(self.devmgr.get_bound_client(self.keystore))
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
        self.keystore.set_handler_delegate(None)
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
        self.assertIsNone(self.devmgr.id_by_pairing_code(self.keystore.pairing_code()))
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
        self.assertIsNone(self.devmgr.id_by_pairing_code(self.keystore.pairing_code()))
        self.assertEqual([False], self.handler.statuses)

    # --- routing ---

    def test_client_serves_the_last_requesting_keystore(self):
        handler2 = FakeHandler()
        keystore2 = FakeKeystore(self.plugin, 'abc', handler2, root_fingerprint=ROOT_A)  # another wallet using the same device
        self.assertIs(self.client, self._client_for(self.keystore))
        self.assertIs(self.handler, self.client.get_handler())
        self.assertIs(self.client, self._client_for(keystore2))
        self.assertIs(handler2, self.client.get_handler())
        # both are bound to the device, and were told so
        self.assertIs(self.client, self.devmgr.get_bound_client(self.keystore))
        self.assertIs(self.client, self.devmgr.get_bound_client(keystore2))
        self.assertEqual([True], self.handler.statuses)
        self.assertEqual([True], handler2.statuses)
        # the keystore's own handler does not follow the client
        self.assertIs(self.handler, self.keystore.get_handler())

    def test_delegate_gets_its_context(self):
        calls = []

        def delegate(*, keystore, client):
            calls.append((keystore, client))
            return self.handler
        keystore = FakeKeystore(self.plugin, 'xyz')
        keystore.set_handler_delegate(delegate)
        # from the keystore: itself, and the client of the device it is bound to, if any
        keystore.get_handler()
        self.devmgr._keystore_to_id[keystore] = 'dev1'
        keystore.get_handler()
        # from a client serving the keystore: both
        self.client.set_keystore(keystore)
        self.client.get_handler()
        # from a client serving a user without a keystore, e.g. a wizard: the client
        self.client.set_handler_delegate(delegate)
        self.client.get_handler()
        self.assertEqual(
            [(keystore, None), (keystore, self.client), (keystore, self.client), (None, self.client)],
            calls)

    def test_user_without_keystore(self):
        wizard_handler = FakeHandler()
        wizard_delegate = constant_handler_delegate(wizard_handler)
        self.client.set_keystore(self.keystore)
        self.client.set_handler_delegate(wizard_delegate)  # a wizard takes over the device
        self.assertIs(wizard_handler, self.client.get_handler())
        self.client.set_keystore(self.keystore)  # and a wallet takes it back
        self.assertIs(self.handler, self.client.get_handler())
        # releasing does not undo the route of another user
        self.client.release_handler_delegate(wizard_delegate)
        self.assertIs(self.handler, self.client.get_handler())
        self.client.set_handler_delegate(wizard_delegate)
        self.client.release_handler_delegate(wizard_delegate)
        self.assertIsNone(self.client.get_handler())

    def test_route_and_binding_do_not_keep_the_keystore_alive(self):
        keystore = FakeKeystore(self.plugin, 'xyz', FakeHandler())
        self.client.set_keystore(keystore)
        self.devmgr._keystore_to_id[keystore] = 'dev1'
        keystore_ref = weakref.ref(keystore)
        del keystore
        gc.collect()
        self.assertIsNone(keystore_ref())
        self.assertIsNone(self.client.get_handler())
        self.assertEqual([self.keystore], list(self.devmgr._keystore_to_id))

    def test_fixed_handler(self):
        handler2 = FakeHandler()
        keystore2 = FakeKeystore(self.plugin, 'abc', handler2)
        self.client.set_keystore(self.keystore)
        with self.client.fixed_handler():
            self.client.set_keystore(keystore2)  # another wallet takes over the device during the flow
            self.assertIs(self.handler, self.client.get_handler())
            with self.client.fixed_handler():  # nested: the outer flow keeps its handler
                self.assertIs(self.handler, self.client.get_handler())
            self.assertIs(self.handler, self.client.get_handler())
        self.assertIs(handler2, self.client.get_handler())

    # --- status ---

    def test_removal_informs_every_keystore_of_the_device(self):
        handler2, handler3 = FakeHandler(), FakeHandler()
        keystore2 = FakeKeystore(self.plugin, 'abc', handler2)  # another wallet using dev1
        keystore3 = FakeKeystore(self.plugin, 'def', handler3)  # a wallet using dev2
        client2 = self._add_client('dev2')
        self.devmgr._keystore_to_id[keystore2] = 'dev1'
        self.devmgr._keystore_to_id[keystore3] = 'dev2'
        self.devmgr.on_device_removed('dev1')
        self._drain_hwd_thread()
        self.assertEqual([False], self.handler.statuses)
        self.assertEqual([False], handler2.statuses)
        self.assertEqual([], handler3.statuses)
        self.assertIsNone(self.devmgr.get_bound_client(keystore2))
        self.assertIs(client2, self.devmgr.get_bound_client(keystore3))

    def test_unpair_informs_every_keystore_of_the_device(self):
        handler2 = FakeHandler()
        keystore2 = FakeKeystore(self.plugin, 'abc', handler2)
        self.devmgr._keystore_to_id[keystore2] = 'dev1'
        self.devmgr.unpair_pairing_code(self.keystore.pairing_code())
        self.assertEqual([False], self.handler.statuses)
        self.assertEqual([False], handler2.statuses)

    def test_shared_handler_is_informed_once(self):
        keystore2 = FakeKeystore(self.plugin, 'abc', self.handler)  # e.g. on QML, there is one handler per device
        self.devmgr._keystore_to_id[keystore2] = 'dev1'
        self.devmgr.unpair_id('dev1')
        self.assertEqual([False], self.handler.statuses)

    def test_failed_lookup_informs_only_the_requester(self):
        handler2 = FakeHandler()
        keystore2 = FakeKeystore(self.plugin, 'xyz', handler2)  # its device is not connected
        self.assertIsNone(self._client_for(keystore2))
        self.assertEqual([False], handler2.statuses)
        self.assertEqual([], self.handler.statuses)

    def test_lookup_without_handler_fails(self):
        keystore2 = FakeKeystore(self.plugin, 'abc')
        with self.assertRaises(Exception) as ctx:
            self._client_for(keystore2)
        self.assertIn('Handler not found', str(ctx.exception))

    # --- passphrases: one device, several roots ---

    def _force_pair(self, keystore: FakeKeystore, device_xpub: str):
        """Pairs keystore with dev1, whose session has the passphrase that gives device_xpub."""
        self.client.xpub = device_xpub
        info = SimpleNamespace(device=SimpleNamespace(id_='dev1'))
        return self.devmgr.force_pair_keystore(plugin=self.plugin, info=info, keystore=keystore)

    def test_pairing_another_root_unpairs_the_old_root(self):
        self._force_pair(self.keystore, XPUB_A)
        old_root_handler, unknown_root_handler = FakeHandler(), FakeHandler()
        old_root = FakeKeystore(self.plugin, 'abc', old_root_handler, root_fingerprint=ROOT_A)  # e.g. another account
        unknown_root = FakeKeystore(self.plugin, 'abc', unknown_root_handler)  # e.g. an old wallet file
        self.devmgr._keystore_to_id[old_root] = 'dev1'
        self.devmgr._keystore_to_id[unknown_root] = 'dev1'
        # e.g. after a reconnect, another wallet pairs the device with its own passphrase
        new_root = FakeKeystore(self.plugin, 'abc', FakeHandler(), root_fingerprint=ROOT_B, xpub=XPUB_B)
        self.assertIs(self.client, self._force_pair(new_root, XPUB_B))
        self.assertEqual('dev1', self.devmgr.id_by_pairing_code(new_root.pairing_code()))
        self.assertIsNone(self.devmgr.id_by_pairing_code(self.keystore.pairing_code()))
        self.assertEqual([False], self.handler.statuses)
        self.assertEqual([False], old_root_handler.statuses)
        self.assertIsNone(self.devmgr.get_bound_client(self.keystore))
        self.assertIsNone(self.devmgr.get_bound_client(old_root))
        # a keystore whose root is unknown has a code of its own: it pairs anew, which checks its xpub
        self.assertEqual([False], unknown_root_handler.statuses)
        self.assertIsNone(self.devmgr.get_bound_client(unknown_root))

    def test_client_with_concurrent_roots_keeps_the_other_roots(self):
        self.client.concurrent_roots = True  # e.g. a session per passphrase
        self._force_pair(self.keystore, XPUB_A)
        new_root = FakeKeystore(self.plugin, 'abc', FakeHandler(), root_fingerprint=ROOT_B, xpub=XPUB_B)
        self._force_pair(new_root, XPUB_B)
        self.assertEqual('dev1', self.devmgr.id_by_pairing_code(self.keystore.pairing_code()))
        self.assertEqual('dev1', self.devmgr.id_by_pairing_code(new_root.pairing_code()))
        self.assertIs(self.client, self.devmgr.get_bound_client(self.keystore))
        self.assertEqual([], self.handler.statuses)

    def test_lookup_of_another_root_does_not_reuse_the_client(self):
        self._force_pair(self.keystore, XPUB_A)
        other_root = FakeKeystore(self.plugin, 'abc', FakeHandler(), root_fingerprint=ROOT_B, xpub=XPUB_B)
        # same pairing code, but it must pair anew, which checks the xpub
        self.assertIsNone(self._client_for(other_root))
        self.assertIs(self.client, self._client_for(self.keystore))

    def test_pairing_fails_while_the_device_has_another_passphrase(self):
        self._force_pair(self.keystore, XPUB_A)
        other_root = FakeKeystore(self.plugin, 'abc', FakeHandler(), root_fingerprint=ROOT_B, xpub=XPUB_B)
        with self.assertRaises(DeviceUnpairableError):
            self._force_pair(other_root, XPUB_A)
        self.assertIs(self.client, self.devmgr.get_bound_client(self.keystore))
        self.assertEqual([], self.handler.statuses)

    def test_removal_drops_every_code_of_the_device(self):
        # e.g. a Ledger, whose code has the root anyway, paired with two passphrases in turn
        other_root = FakeKeystore(self.plugin, 'abc', FakeHandler(), root_fingerprint=ROOT_B)
        self.devmgr.pairing_code_to_id[other_root.pairing_code()] = 'dev1'
        self.devmgr.on_device_removed('dev1')
        self.assertEqual({}, self.devmgr.pairing_code_to_id)

    def test_no_leftover_code_reuses_a_reconnected_device(self):
        other_root = FakeKeystore(self.plugin, 'abc', FakeHandler(), root_fingerprint=ROOT_B, xpub=XPUB_B)
        self.devmgr.pairing_code_to_id[other_root.pairing_code()] = 'dev1'
        self.devmgr.unpair_id('dev1')
        # reconnected on the same port: same id_, a new client that nobody paired yet
        self._add_client('dev1')
        self.assertIsNone(self._client_for(self.keystore))
        self.assertIsNone(self._client_for(other_root))

    # --- closing ---

    def test_release_keeps_a_device_that_is_still_used(self):
        handler2 = FakeHandler()
        keystore2 = FakeKeystore(self.plugin, 'abc', handler2, root_fingerprint=ROOT_A)  # another wallet using dev1
        self.devmgr._keystore_to_id[keystore2] = 'dev1'
        self.devmgr.release_keystore(self.keystore)
        self.assertIsNone(self.client.closed_on)
        self.assertEqual('dev1', self.devmgr.id_by_pairing_code(self.keystore.pairing_code()))
        self.assertIsNone(self.devmgr.get_bound_client(self.keystore))
        self.assertIs(self.client, self.devmgr.get_bound_client(keystore2))
        self.assertEqual([], handler2.statuses)
        # the last one unpairs and closes it
        self.devmgr.release_keystore(keystore2)
        self.assertIsNotNone(self.client.closed_on)
        self.assertIsNone(self.devmgr.id_by_pairing_code(self.keystore.pairing_code()))
        self.assertIsNone(self.devmgr._client_by_id('dev1'))

    def test_release_of_an_unbound_keystore_keeps_a_device_that_is_still_used(self):
        keystore2 = FakeKeystore(self.plugin, 'abc', FakeHandler(), root_fingerprint=ROOT_A)  # e.g. its wallet did not pair yet
        self.devmgr.release_keystore(keystore2)
        self.assertIsNone(self.client.closed_on)
        self.assertEqual('dev1', self.devmgr.id_by_pairing_code(self.keystore.pairing_code()))

    def test_close_keystore(self):
        keystore2 = FakeKeystore(self.plugin, 'abc', FakeHandler(), root_fingerprint=ROOT_A)  # another wallet using dev1
        self.devmgr._keystore_to_id[keystore2] = 'dev1'
        self.keystore.thread = thread = FakeThread()
        self.client.set_keystore(self.keystore)
        handler_ref = weakref.ref(self.handler)
        self.plugin.close_keystore(self.keystore)
        self.assertTrue(thread.stopped)
        self.assertIsNone(self.keystore.thread)
        self.assertIsNone(self.keystore.get_handler())
        self.assertIsNone(self.client.get_handler())
        self.assertIsNone(self.client.closed_on)  # keystore2 still uses the device
        # nothing keeps the handler, and thus the closed window, alive
        del self.handler
        gc.collect()
        self.assertIsNone(handler_ref())
