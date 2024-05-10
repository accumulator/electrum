import io

from electrum import segwit_addr, ecc, lnmsg
from electrum import bolt12
from electrum.bolt12 import is_offer, decode_offer, encode_invoice_request, decode_invoice_request
from electrum.lnmsg import UnknownMandatoryTLVRecordType, decode_msg, _tlv_merkle_root
from electrum.lnonion import OnionHopsDataSingle, new_onion_packet2, OnionPacket, process_onion_packet, \
    get_bolt04_onion_key
from electrum.lnutil import get_ecdh
from electrum.segwit_addr import INVALID_BECH32
from electrum.util import bfh

from . import ElectrumTestCase


def bech32_decode(x):
    return segwit_addr.bech32_decode(x, ignore_long_length=True, with_checksum=False)


class TestBolt12(ElectrumTestCase):
    def test_decode(self):
        # https://bootstrap.bolt12.org/examples
        offer = 'lno1pg257enxv4ezqcneype82um50ynhxgrwdajx293pqglnyxw6q0hzngfdusg8umzuxe8kquuz7pjl90ldj8wadwgs0xlmc'
        d = bech32_decode(offer)
        self.assertNotEqual(d, INVALID_BECH32, "bech32 decode error")
        self.assertEqual(d.hrp, 'lno', "wrong hrp")
        self.assertTrue(is_offer(offer))
        od = decode_offer(offer)
        self.assertEqual(od, {'offer_description': {'description': b"Offer by rusty's node"},
                              'offer_node_id':
                                  {'node_id': b'\x02?2\x19\xda\x03\xee)\xa1-\xe4\x10~l\\6O`s\x82\xf0e\xf2\xbf\xed\x91\xdd\xd6\xb9\x10y\xbf\xbc'}
                              })

        offer = 'lno1pqqnyzsmx5cx6umpwssx6atvw35j6ut4v9h8g6t50ysx7enxv4epyrmjw4ehgcm0wfczucm0d5hxzag5qqtzzq3lxgva5qlw9xsjmeqs0ek9cdj0vpec9ur972l7mywa66u3q7dlhs'
        d = bech32_decode(offer)
        self.assertNotEqual(d, INVALID_BECH32, "bech32 decode error")
        self.assertEqual(d.hrp, 'lno', "wrong hrp")
        od = decode_offer(offer)
        self.assertEqual(od, {'offer_amount': {'amount': 50},
                              'offer_description': {'description': b'50msat multi-quantity offer'},
                              'offer_issuer': {'issuer': b'rustcorp.com.au'},
                              'offer_quantity_max': {'max': 0},
                              'offer_node_id':
                                  {'node_id': b'\x02?2\x19\xda\x03\xee)\xa1-\xe4\x10~l\\6O`s\x82\xf0e\xf2\xbf\xed\x91\xdd\xd6\xb9\x10y\xbf\xbc'}
                              })

        # TODO: tests below use recurrence (tlv record type 26) which is not supported/generated from wire specs
        # (c-lightning carries patches re-adding these, but for now we ignore them)

        offer = 'lno1pqqkgzs5xycrqmtnv96zqetkv4e8jgrdd9h82ar9zgg8yatnw3ujumm6d3skyuewdaexw93pqglnyxw6q0hzngfdusg8umzuxe8kquuz7pjl90ldj8wadwgs0xlmcxszqq7q'
        d = bech32_decode(offer)
        self.assertNotEqual(d, INVALID_BECH32, "bech32 decode error")
        self.assertEqual(d.hrp, 'lno', "wrong hrp")
        # contains TLV record type 26 which is not defined (yet) in 12-offer-encoding.md
        with self.assertRaises(UnknownMandatoryTLVRecordType):
            od = bolt12.decode_offer(offer)

        offer = 'lno1pqqkgz38xycrqmtnv96zqetkv4e8jgrdd9h82ar99ss82upqw3hjqargwfjk2gr5d9kk2ucjzpe82um50yhx77nvv938xtn0wfn3vggz8uepnksrac56zt0yzplxchpkfas88qhsvhetlmv3mhttjyreh77p5qsq8s0qzqs'
        d = bech32_decode(offer)
        self.assertNotEqual(d, INVALID_BECH32, "bech32 decode error")
        self.assertEqual(d.hrp, 'lno', "wrong hrp")
        # contains TLV record type 26 which is not defined (yet) in 12-offer-encoding.md
        with self.assertRaises(UnknownMandatoryTLVRecordType):
            od = bolt12.decode_offer(offer)

        offer = 'lno1pqqkgz3zxycrqmtnv96zqetkv4e8jgryv9ujcgrxwfhk6gp3949xzm3dxgcryvgjzpe82um50yhx77nvv938xtn0wfn3vggz8uepnksrac56zt0yzplxchpkfas88qhsvhetlmv3mhttjyreh77p5qspqysq2q2laenqq'
        d = bech32_decode(offer)
        self.assertNotEqual(d, INVALID_BECH32, "bech32 decode error")
        self.assertEqual(d.hrp, 'lno', "wrong hrp")
        # contains TLV record type 26 which is not defined (yet) in 12-offer-encoding.md
        with self.assertRaises(UnknownMandatoryTLVRecordType):
            od = bolt12.decode_offer(offer)

        offer = 'lno1pqpq86q2fgcnqvpsd4ekzapqv4mx2uneyqcnqgryv9uhxtpqveex7mfqxyk55ctw95erqv339ss8qcteyqcksu3qvfjkvmmjv5s8gmeqxcczqum9vdhkuernypkxzar9zgg8yatnw3ujumm6d3skyuewdaexw93pqglnyxw6q0hzngfdusg8umzuxe8kquuz7pjl90ldj8wadwgs0xlmcxszqy9pcpsqqq8pqqpuyqzszhlwvcqq'
        d = bech32_decode(offer)
        self.assertNotEqual(d, INVALID_BECH32, "bech32 decode error")
        self.assertEqual(d.hrp, 'lno', "wrong hrp")
        # contains TLV record type 26 which is not defined (yet) in 12-offer-encoding.md
        with self.assertRaises(UnknownMandatoryTLVRecordType):
            od = bolt12.decode_offer(offer)

        offer = 'lno1pqpq86q2xycnqvpsd4ekzapqv4mx2uneyqcnqgryv9uhxtpqveex7mfqxyk55ctw95erqv339ss8qun094exzarpzgg8yatnw3ujumm6d3skyuewdaexw93pqglnyxw6q0hzngfdusg8umzuxe8kquuz7pjl90ldj8wadwgs0xlmcxszqy9pczqqp5hsqqgd9uqzqpgptlhxvqq'
        d = bech32_decode(offer)
        self.assertNotEqual(d, INVALID_BECH32, "bech32 decode error")
        self.assertEqual(d.hrp, 'lno', "wrong hrp")
        # contains TLV record type 26 which is not defined (yet) in 12-offer-encoding.md
        with self.assertRaises(UnknownMandatoryTLVRecordType):
            od = bolt12.decode_offer(offer)

        offer = 'lno1qcp4256ypqpq86q2pucnq42ngssx2an9wfujqerp0yfpqun4wd68jtn00fkxzcnn9ehhyeckyypr7vsemgp7u2dp9hjpqlnvtsmy7crnstcxtu4lakgam44ezpuml0q6qgqsz'
        d = bech32_decode(offer)
        self.assertNotEqual(d, INVALID_BECH32, "bech32 decode error")
        self.assertEqual(d.hrp, 'lno', "wrong hrp")
        # contains TLV record type 26 which is not defined (yet) in 12-offer-encoding.md
        with self.assertRaises(UnknownMandatoryTLVRecordType):
            od = bolt12.decode_offer(offer)

    def test_path_pubkeys_blinded_path_appended(self):
        # test vectors https://github.com/lightning/bolts/pull/759/files
        payment_path_pubkeys = [
            (bfh('02eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f283686619'),   # Alice
             bfh('6363636363636363636363636363636363636363636363636363636363636363')),
            (bfh('0324653eac434488002cc06bbfb7f10fe18991e35f9fe4302dbea6d2353dc0ab1c'),  # Bob w blinding secret override
             bfh('0101010101010101010101010101010101010101010101010101010101010101')),
            bfh('027f31ebc5462c1fdce1b737ecff52d37d75dea43ce11c74d25aa297165faa2007'),   # Carol
            bfh('032c0b7cf95324a07d05398b240174dc0c2be444d96b159aa6c7f7b1e668680991')    # Dave
        ]
        session_key = bfh('0303030303030303030303030303030303030303030303030303030303030303')

        hops_data = [
            OnionHopsDataSingle(tlv_stream_name='onionmsg_tlv',
                                blind_fields={'next_node_id': {'node_id': bfh('0324653eac434488002cc06bbfb7f10fe18991e35f9fe4302dbea6d2353dc0ab1c')},
                                              'next_blinding_override': {'blinding': bfh('031b84c5567b126440995d3ed5aaba0565d71e1834604819ff9c17f5e9d5dd078f')},
                                              #'blinding_override_secret': {'data': bfh('0101010101010101010101010101010101010101010101010101010101010101')}}
                                              # blinding_override_secret is not a member of encrypted_data_tlv
                                              }
                                ),
            OnionHopsDataSingle(tlv_stream_name='onionmsg_tlv',
                                blind_fields={'next_node_id': {'node_id': bfh('027f31ebc5462c1fdce1b737ecff52d37d75dea43ce11c74d25aa297165faa2007')},
                                              'unknown_tag_561': {'data': bfh('123456')}
                                              }
                                ),
            OnionHopsDataSingle(tlv_stream_name='onionmsg_tlv',
                                blind_fields={'padding': {'padding': bfh('0000000000')},
                                              'next_node_id': {'node_id': bfh('032c0b7cf95324a07d05398b240174dc0c2be444d96b159aa6c7f7b1e668680991')}
                                              }
                                ),
            OnionHopsDataSingle(tlv_stream_name='onionmsg_tlv', payload={'message': {'text': b'hello'}},
                                blind_fields={'padding': {'padding': b''},
                                              'path_id': {'data': bfh('deadbeefbadc0ffeedeadbeefbadc0ffeedeadbeefbadc0ffeedeadbeefbadc0')},
                                              'unknown_tag_65535': {'data': b'\x06\xc1'}
                                              }
                                )
        ]
        packet = new_onion_packet2(payment_path_pubkeys, session_key, hops_data)

        expected = bfh('0002531fe6068134503d2723133227c867ac8fa6c83c537e9a44c3c5bdbdcb1fe33793b828776d70aabbd8cef1a5b52d5a397ae1a20f20435ff6057cd8be339d5aee226660ef73b64afa45dbf2e6e8e26eb96a259b2db5aeecda1ce2e768bbc35d389d7f320ca3d2bd14e2689bef2f5ac0307eaaabc1924eb972c1563d4646ae131accd39da766257ed35ea36e4222527d1db4fa7b2000aab9eafcceed45e28b5560312d4e2299bd8d1e7fe27d10925966c28d497aec400b4630485e82efbabc00550996bdad5d6a9a8c75952f126d14ad2cff91e16198691a7ef2937de83209285f1fb90944b4e46bca7c856a9ce3da10cdf2a7d00dc2bf4f114bc4d3ed67b91cbde558ce9af86dc81fbdc37f8e301b29e23c1466659c62bdbf8cff5d4c20f0fb0851ec72f5e9385dd40fdd2e3ed67ca4517117825665e50a3e26f73c66998daf18e418e8aef9ce2d20da33c3629db2933640e03e7b44c2edf49e9b482db7b475cfd4c617ae1d46d5c24d697846f9f08561eac2b065f9b382501f6eabf07343ed6c602f61eab99cdb52adf63fd44a8db2d3016387ea708fc1c08591e19b4d9984ebe31edbd684c2ea86526dd8c7732b1d8d9117511dc1b643976d356258fce8313b1cb92682f41ab72dedd766f06de375f9edacbcd0ca8c99b865ea2b7952318ea1fd20775a28028b5cf59dece5de14f615b8df254eee63493a5111ea987224bea006d8f1b60d565eef06ac0da194dba2a6d02e79b2f2f34e9ca6e1984a507319d86e9d4fcaeea41b4b9144e0b1826304d4cc1da61cfc5f8b9850697df8adc5e9d6f3acb3219b02764b4909f2b2b22e799fd66c383414a84a7d791b899d4aa663770009eb122f90282c8cb9cda16aba6897edcf9b32951d0080c0f52be3ca011fbec3fb16423deb47744645c3b05fdbd932edf54ba6efd26e65340a8e9b1d1216582e1b30d64524f8ca2d6c5ba63a38f7120a3ed71bed8960bcac2feee2dd41c90be48e3c11ec518eb3d872779e4765a6cc28c6b0fa71ab57ced73ae963cc630edae4258cba2bf25821a6ae049fec2fca28b5dd1bb004d92924b65701b06dcf37f0ccd147a13a03f9bc0f98b7d78fe9058089756931e2cd0e0ed92ec6759d07b248069526c67e9e6ce095118fd3501ba0f858ef030b76c6f6beb11a09317b5ad25343f4b31aef02bc555951bc7791c2c289ecf94d5544dcd6ad3021ed8e8e3db34b2a73e1eedb57b578b068a5401836d6e382110b73690a94328c404af25e85a8d6b808893d1b71af6a31fadd8a8cc6e31ecc0d9ff7e6b91fd03c274a5c1f1ccd25b61150220a3fddb04c91012f5f7a83a5c90deb2470089d6e38cd5914b9c946eca6e9d31bbf8667d36cf87effc3f3ff283c21dd4137bd569fe7cf758feac94053e4baf7338bb592c8b7c291667fadf4a9bf9a2a154a18f612cbc7f851b3f8f2070e0a9d180622ee4f8e81b0ab250d504cef24116a3ff188cc829fcd8610b56343569e8dc997629410d1967ca9dd1d27eec5e01e4375aad16c46faba268524b154850d0d6fe3a76af2c6aa3e97647c51036049ac565370028d6a439a2672b6face56e1b171496c0722cfa22d9da631be359661617c5d5a2d286c5e19db9452c1e21a0107b6400debda2decb0c838f342dd017cdb2dccdf1fe97e3df3f881856b546997a3fed9e279c720145101567dd56be21688fed66bf9759e432a9aa89cbbd225d13cdea4ca05f7a45cfb6a682a3d5b1e18f7e6cf934fae5098108bae9058d05c3387a01d8d02a656d2bfff67e9f46b2d8a6aac28129e52efddf6e552214c3f8a45bc7a912cca9a7fec1d7d06412c6972cb9e3dc518983f56530b8bffe7f92c4b6eb47d4aef59fb513c4653a42de61bc17ad7728e7fc7590ff05a9e991de03f023d0aaf8688ed6170def5091c66576a424ac1cb')
        self.assertEqual(packet.to_bytes(), expected)

    def test_decode_onion_message_packet(self):
        packet = '0002531fe6068134503d2723133227c867ac8fa6c83c537e9a44c3c5bdbdcb1fe33793b828776d70aabbd8cef1a5b52d5a397ae1a20f20435ff6057cd8be339d5aee226660ef73b64afa45dbf2e6e8e26eb96a259b2db5aeecda1ce2e768bbc35d389d7f320ca3d2bd14e2689bef2f5ac0307eaaabc1924eb972c1563d4646ae131accd39da766257ed35ea36e4222527d1db4fa7b2000aab9eafcceed45e28b5560312d4e2299bd8d1e7fe27d10925966c28d497aec400b4630485e82efbabc00550996bdad5d6a9a8c75952f126d14ad2cff91e16198691a7ef2937de83209285f1fb90944b4e46bca7c856a9ce3da10cdf2a7d00dc2bf4f114bc4d3ed67b91cbde558ce9af86dc81fbdc37f8e301b29e23c1466659c62bdbf8cff5d4c20f0fb0851ec72f5e9385dd40fdd2e3ed67ca4517117825665e50a3e26f73c66998daf18e418e8aef9ce2d20da33c3629db2933640e03e7b44c2edf49e9b482db7b475cfd4c617ae1d46d5c24d697846f9f08561eac2b065f9b382501f6eabf07343ed6c602f61eab99cdb52adf63fd44a8db2d3016387ea708fc1c08591e19b4d9984ebe31edbd684c2ea86526dd8c7732b1d8d9117511dc1b643976d356258fce8313b1cb92682f41ab72dedd766f06de375f9edacbcd0ca8c99b865ea2b7952318ea1fd20775a28028b5cf59dece5de14f615b8df254eee63493a5111ea987224bea006d8f1b60d565eef06ac0da194dba2a6d02e79b2f2f34e9ca6e1984a507319d86e9d4fcaeea41b4b9144e0b1826304d4cc1da61cfc5f8b9850697df8adc5e9d6f3acb3219b02764b4909f2b2b22e799fd66c383414a84a7d791b899d4aa663770009eb122f90282c8cb9cda16aba6897edcf9b32951d0080c0f52be3ca011fbec3fb16423deb47744645c3b05fdbd932edf54ba6efd26e65340a8e9b1d1216582e1b30d64524f8ca2d6c5ba63a38f7120a3ed71bed8960bcac2feee2dd41c90be48e3c11ec518eb3d872779e4765a6cc28c6b0fa71ab57ced73ae963cc630edae4258cba2bf25821a6ae049fec2fca28b5dd1bb004d92924b65701b06dcf37f0ccd147a13a03f9bc0f98b7d78fe9058089756931e2cd0e0ed92ec6759d07b248069526c67e9e6ce095118fd3501ba0f858ef030b76c6f6beb11a09317b5ad25343f4b31aef02bc555951bc7791c2c289ecf94d5544dcd6ad3021ed8e8e3db34b2a73e1eedb57b578b068a5401836d6e382110b73690a94328c404af25e85a8d6b808893d1b71af6a31fadd8a8cc6e31ecc0d9ff7e6b91fd03c274a5c1f1ccd25b61150220a3fddb04c91012f5f7a83a5c90deb2470089d6e38cd5914b9c946eca6e9d31bbf8667d36cf87effc3f3ff283c21dd4137bd569fe7cf758feac94053e4baf7338bb592c8b7c291667fadf4a9bf9a2a154a18f612cbc7f851b3f8f2070e0a9d180622ee4f8e81b0ab250d504cef24116a3ff188cc829fcd8610b56343569e8dc997629410d1967ca9dd1d27eec5e01e4375aad16c46faba268524b154850d0d6fe3a76af2c6aa3e97647c51036049ac565370028d6a439a2672b6face56e1b171496c0722cfa22d9da631be359661617c5d5a2d286c5e19db9452c1e21a0107b6400debda2decb0c838f342dd017cdb2dccdf1fe97e3df3f881856b546997a3fed9e279c720145101567dd56be21688fed66bf9759e432a9aa89cbbd225d13cdea4ca05f7a45cfb6a682a3d5b1e18f7e6cf934fae5098108bae9058d05c3387a01d8d02a656d2bfff67e9f46b2d8a6aac28129e52efddf6e552214c3f8a45bc7a912cca9a7fec1d7d06412c6972cb9e3dc518983f56530b8bffe7f92c4b6eb47d4aef59fb513c4653a42de61bc17ad7728e7fc7590ff05a9e991de03f023d0aaf8688ed6170def5091c66576a424ac1cb'
        op = OnionPacket.from_bytes(bfh(packet))
        pass

    def test_decode_onion_message(self):
        msg = '0201031195a8046dcbb8e17034bca630065e7a0982e4e36f6f7e5a8d4554e4846fcd9905560002531fe6068134503d2723133227c867ac8fa6c83c537e9a44c3c5bdbdcb1fe33793b828776d70aabbd8cef1a5b52d5a397ae1a20f20435ff6057cd8be339d5aee226660ef73b64afa45dbf2e6e8e26eb96a259b2db5aeecda1ce2e768bbc35d389d7f320ca3d2bd14e2689bef2f5ac0307eaaabc1924eb972c1563d4646ae131accd39da766257ed35ea36e4222527d1db4fa7b2000aab9eafcceed45e28b5560312d4e2299bd8d1e7fe27d10925966c28d497aec400b4630485e82efbabc00550996bdad5d6a9a8c75952f126d14ad2cff91e16198691a7ef2937de83209285f1fb90944b4e46bca7c856a9ce3da10cdf2a7d00dc2bf4f114bc4d3ed67b91cbde558ce9af86dc81fbdc37f8e301b29e23c1466659c62bdbf8cff5d4c20f0fb0851ec72f5e9385dd40fdd2e3ed67ca4517117825665e50a3e26f73c66998daf18e418e8aef9ce2d20da33c3629db2933640e03e7b44c2edf49e9b482db7b475cfd4c617ae1d46d5c24d697846f9f08561eac2b065f9b382501f6eabf07343ed6c602f61eab99cdb52adf63fd44a8db2d3016387ea708fc1c08591e19b4d9984ebe31edbd684c2ea86526dd8c7732b1d8d9117511dc1b643976d356258fce8313b1cb92682f41ab72dedd766f06de375f9edacbcd0ca8c99b865ea2b7952318ea1fd20775a28028b5cf59dece5de14f615b8df254eee63493a5111ea987224bea006d8f1b60d565eef06ac0da194dba2a6d02e79b2f2f34e9ca6e1984a507319d86e9d4fcaeea41b4b9144e0b1826304d4cc1da61cfc5f8b9850697df8adc5e9d6f3acb3219b02764b4909f2b2b22e799fd66c383414a84a7d791b899d4aa663770009eb122f90282c8cb9cda16aba6897edcf9b32951d0080c0f52be3ca011fbec3fb16423deb47744645c3b05fdbd932edf54ba6efd26e65340a8e9b1d1216582e1b30d64524f8ca2d6c5ba63a38f7120a3ed71bed8960bcac2feee2dd41c90be48e3c11ec518eb3d872779e4765a6cc28c6b0fa71ab57ced73ae963cc630edae4258cba2bf25821a6ae049fec2fca28b5dd1bb004d92924b65701b06dcf37f0ccd147a13a03f9bc0f98b7d78fe9058089756931e2cd0e0ed92ec6759d07b248069526c67e9e6ce095118fd3501ba0f858ef030b76c6f6beb11a09317b5ad25343f4b31aef02bc555951bc7791c2c289ecf94d5544dcd6ad3021ed8e8e3db34b2a73e1eedb57b578b068a5401836d6e382110b73690a94328c404af25e85a8d6b808893d1b71af6a31fadd8a8cc6e31ecc0d9ff7e6b91fd03c274a5c1f1ccd25b61150220a3fddb04c91012f5f7a83a5c90deb2470089d6e38cd5914b9c946eca6e9d31bbf8667d36cf87effc3f3ff283c21dd4137bd569fe7cf758feac94053e4baf7338bb592c8b7c291667fadf4a9bf9a2a154a18f612cbc7f851b3f8f2070e0a9d180622ee4f8e81b0ab250d504cef24116a3ff188cc829fcd8610b56343569e8dc997629410d1967ca9dd1d27eec5e01e4375aad16c46faba268524b154850d0d6fe3a76af2c6aa3e97647c51036049ac565370028d6a439a2672b6face56e1b171496c0722cfa22d9da631be359661617c5d5a2d286c5e19db9452c1e21a0107b6400debda2decb0c838f342dd017cdb2dccdf1fe97e3df3f881856b546997a3fed9e279c720145101567dd56be21688fed66bf9759e432a9aa89cbbd225d13cdea4ca05f7a45cfb6a682a3d5b1e18f7e6cf934fae5098108bae9058d05c3387a01d8d02a656d2bfff67e9f46b2d8a6aac28129e52efddf6e552214c3f8a45bc7a912cca9a7fec1d7d06412c6972cb9e3dc518983f56530b8bffe7f92c4b6eb47d4aef59fb513c4653a42de61bc17ad7728e7fc7590ff05a9e991de03f023d0aaf8688ed6170def5091c66576a424ac1cb'
        op = decode_msg(bfh(msg))
        pass

    def test_decode_offer(self):
        offer = 'lno1pggxv6tjwd6zqar9wd6zqmmxvejhy93pq02rpdcl6l20pakl2ad70k0n8v862jwp2twq8a8uz0hz5wfafg495'
        d = bech32_decode(offer)
        self.assertNotEqual(d, INVALID_BECH32, "bech32 decode error")
        self.assertEqual(d.hrp, 'lno', "wrong hrp")
        self.assertTrue(is_offer(offer))

        od = decode_offer(offer)
        self.assertEqual(od['offer_description']['description'], b'first test offer')
        self.assertEqual(od['offer_node_id']['node_id'], bfh('03d430b71fd7d4f0f6df575be7d9f33b0fa549c152dc03f4fc13ee2a393d4a2a5a'))

    def test_decode_invreq(self):
        invreq = 'lnr1pggxv6tjwd6zqar9wd6zqmmxvejhy93pq02rpdcl6l20pakl2ad70k0n8v862jwp2twq8a8uz0hz5wfafg495'
        d = bech32_decode(invreq)
        self.assertNotEqual(d, INVALID_BECH32, "bech32 decode error")
        self.assertEqual(d.hrp, 'lnr', "wrong hrp")

        od = decode_invoice_request(invreq)
        self.assertEqual(od['offer_description']['description'], b'first test offer')
        self.assertEqual(od['offer_node_id']['node_id'], bfh('03d430b71fd7d4f0f6df575be7d9f33b0fa549c152dc03f4fc13ee2a393d4a2a5a'))

    def test_subtype_encode_decode(self):
        offer = 'lno1pggxv6tjwd6zqar9wd6zqmmxvejhy93pq02rpdcl6l20pakl2ad70k0n8v862jwp2twq8a8uz0hz5wfafg495'
        od = decode_offer(offer)
        data = {'offer_node_id': od['offer_node_id']}
        invreq_pl_tlv = encode_invoice_request(data, payer_key=bfh('4141414141414141414141414141414141414141414141414141414141414141'))

        ohds = OnionHopsDataSingle(tlv_stream_name='onionmsg_tlv',
                            payload={'invoice_request': {'invoice_request': invreq_pl_tlv},
                                         'reply_path': {'path': {
                                             'first_node_id': bfh('0309d14e515e8ef4ea022787dcda8550edfbd7da6052208d2fc0cc4f7d949558e5'),
                                             'blinding': bfh('0309d14e515e8ef4ea022787dcda8550edfbd7da6052208d2fc0cc4f7d949558e5'),
                                             'num_hops': 2,
                                             'path': [
                                                 {'blinded_node_id': bfh('0309d14e515e8ef4ea022787dcda8550edfbd7da6052208d2fc0cc4f7d949558e5'),
                                                  'enclen': 5,
                                                  'encrypted_recipient_data': bfh('0000000000')},
                                                 {'blinded_node_id': bfh('0309d14e515e8ef4ea022787dcda8550edfbd7da6052208d2fc0cc4f7d949558e5'),
                                                  'enclen': 6,
                                                  'encrypted_recipient_data': bfh('001111222233')}
                                             ]
                                         }},
                                     },
                            blind_fields={'padding': {'padding': b''},
                                          #'path_id': {'data': bfh('deadbeefbadc0ffeedeadbeefbadc0ffeedeadbeefbadc0ffeedeadbeefbadc0')}
                                          }
                            )

        ohds_b = ohds.to_bytes()

        self.assertEqual(ohds_b, bfh('fd00fd02940309d14e515e8ef4ea022787dcda8550edfbd7da6052208d2fc0cc4f7d949558e50309d14e515e8ef4ea022787dcda8550edfbd7da6052208d2fc0cc4f7d949558e5020309d14e515e8ef4ea022787dcda8550edfbd7da6052208d2fc0cc4f7d949558e5000500000000000309d14e515e8ef4ea022787dcda8550edfbd7da6052208d2fc0cc4f7d949558e500060011112222334065162103d430b71fd7d4f0f6df575be7d9f33b0fa549c152dc03f4fc13ee2a393d4a2a5af04078205e3d9d3cf87b743bcad5bca89f12f868ce638fbb4051d9570bac1a79d90ae3650ebcf15603b9349697edf71bf78ecb802aafe146d9118fe387bdb36ed26e0000000000000000000000000000000000000000000000000000000000000000'))

        with io.BytesIO(ohds_b) as fd:
            ohds2 = OnionHopsDataSingle.from_fd(fd, tlv_stream_name='onionmsg_tlv')
            self.assertTrue('invoice_request' in ohds2.payload)  # TODO
            self.assertTrue('reply_path' in ohds2.payload)  # TODO

    def test_merkle_root(self):
        # test vectors in https://github.com/lightning/bolts/pull/798
        tlvs = [
            (bfh('010203e8'), 1),
            (bfh('02080000010000020003'), 2),
            (bfh('03310266e4598d1d3c415f572a8488830b60f7e744ed9235eb0b1ba93283b315c0351800000000000000010000000000000002'), 3)
        ]

        self.assertEqual(_tlv_merkle_root(tlvs[:1]), bfh('b013756c8fee86503a0b4abdab4cddeb1af5d344ca6fc2fa8b6c08938caa6f93'))
        self.assertEqual(_tlv_merkle_root(tlvs[:2]), bfh('c3774abbf4815aa54ccaa026bff6581f01f3be5fe814c620a252534f434bc0d1'))
        self.assertEqual(_tlv_merkle_root(tlvs[:3]), bfh('ab2e79b1283b0b31e0b035258de23782df6b89a38cfa7237bde69aed1a658c5d'))

    def test_invoice_request_schnorr_signature(self):
        # use invoice request in https://github.com/lightning/bolts/pull/798 to match test vectors
        invreq = 'lnr1qqyqqqqqqqqqqqqqqcp4256ypqqkgzshgysy6ct5dpjk6ct5d93kzmpq23ex2ct5d9ek293pqthvwfzadd7jejes8q9lhc4rvjxd022zv5l44g6qah82ru5rdpnpjkppqvjx204vgdzgsqpvcp4mldl3plscny0rt707gvpdh6ndydfacz43euzqhrurageg3n7kafgsek6gz3e9w52parv8gs2hlxzk95tzeswywffxlkeyhml0hh46kndmwf4m6xma3tkq2lu04qz3slje2rfthc89vss'
        data = decode_invoice_request(invreq)
        del data['signature']  # remove signature, we regenerate it

        payer_key = bfh('4242424242424242424242424242424242424242424242424242424242424242')
        invreq_pl_tlv = encode_invoice_request(data, payer_key)

        self.assertEqual(invreq_pl_tlv, bfh('0008000000000000000006035553440801640a1741204d617468656d61746963616c205472656174697365162102eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f28368661958210324653eac434488002cc06bbfb7f10fe18991e35f9fe4302dbea6d2353dc0ab1cf040b8f83ea3288cfd6ea510cdb481472575141e8d8744157f98562d162cc1c472526fdb24befefbdebab4dbb726bbd1b7d8aec057f8fa805187e5950d2bbe0e5642'))

    def test_serde_complex_fields(self):
        payer_key = bfh('4141414141414141414141414141414141414141414141414141414141414141')

        # test complex field cardinality without explicit count
        invreq = {
            'offer_paths': {'paths': [
                {'first_node_id': bfh('02eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f283686619'),
                 'blinding': bfh('02eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f283686619'),
                 'num_hops': 0,
                 'path': []},
                {'first_node_id': bfh('02eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f283686619'),
                 'blinding': bfh('02eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f283686619'),
                 'num_hops': 0,
                 'path': []},
                {'first_node_id': bfh('02eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f283686619'),
                 'blinding': bfh('02eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f283686619'),
                 'num_hops': 0,
                 'path': []}
            ]}
        }

        invreq_pl_tlv = encode_invoice_request(invreq, payer_key=payer_key)

        with io.BytesIO() as fd:
            f = io.BytesIO(invreq_pl_tlv)
            lns = lnmsg.LNSerializer()
            deser = lns.read_tlv_stream(fd=f, tlv_stream_name='invoice_request')
            self.assertEqual(len(deser['offer_paths']['paths']), 3)

        # test complex field all members required
        invreq = {
            'offer_paths': {'paths': [
                {'first_node_id': bfh('02eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f283686619'),
                 'blinding': bfh('02eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f283686619'),
                 'num_hops': 0}
            ]}
        }

        with self.assertRaises(Exception):
            invreq_pl_tlv = encode_invoice_request(invreq, payer_key=payer_key)

        # test complex field count matches parameters
        invreq = {
            'offer_paths': {'paths': [
                {'first_node_id': bfh('02eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f283686619'),
                 'blinding': bfh('02eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f283686619'),
                 'num_hops': 1,
                 'path': []}
            ]}
        }

        with self.assertRaises(AssertionError):
            invreq_pl_tlv = encode_invoice_request(invreq, payer_key=payer_key)
