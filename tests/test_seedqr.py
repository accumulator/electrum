from electrum import seedqr

from . import ElectrumTestCase


class TestSeedQR(ElectrumTestCase):
    def test_decode_standard_seedqr(self):
        seed = seedqr.seed_from_seedqr('192402220235174306311124037817700641198012901210')
        self.assertEqual('vacuum bridge buddy supreme exclude milk consider tail expand wasp pattern nuclear', seed)

        seed = seedqr.seed_from_seedqr('011513251154012711900771041507421289190620080870026613431420201617920614089619290300152408010643')
        self.assertEqual('attack pizza motion avocado network gather crop fresh patrol unusual wild holiday candy pony ranch winter theme error hybrid van cereal salon goddess expire', seed)

    def test_decode_compact_seedqr(self):
        seed = seedqr.seed_from_seedqr(b'[\xbd\x9dq\xa8\xecy\x90\x83\x1a\xff5\x9dBeE')
        self.assertEqual('forum undo fragile fade shy sign arrest garment culture tube off merit', seed)

        seed = seedqr.seed_from_seedqr(b'\x0et\xb6A\x07\xf9L\xc0\xcc\xfa\xe6\xa1=\xcb\xec6b\x15O\xecg\xe0\xe0\t\x99\xc0x\x92Y}\x19\n')
        self.assertEqual('attack pizza motion avocado network gather crop fresh patrol unusual wild holiday candy pony ranch winter theme error hybrid van cereal salon goddess expire', seed)

    def test_encode_standard_seedqr(self):
        standard_qr = seedqr.seed_to_seedqr('abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about', compact=False)
        self.assertEqual('0000'*11+'0003', standard_qr)

        standard_qr = seedqr.seed_to_seedqr('forum undo fragile fade shy sign arrest garment culture tube off merit', compact=False)
        self.assertEqual('073318950739065415961602009907670428187212261116', standard_qr)

        standard_qr = seedqr.seed_to_seedqr('attack pizza motion avocado network gather crop fresh patrol unusual wild holiday candy pony ranch winter theme error hybrid van cereal salon goddess expire', compact=False)
        self.assertEqual('011513251154012711900771041507421289190620080870026613431420201617920614089619290300152408010643', standard_qr)

        standard_qr = seedqr.seed_to_seedqr('atom solve joy ugly ankle message setup typical bean era cactus various odor refuse element afraid meadow quick medal plate wisdom swap noble shallow', compact=False)
        self.assertEqual('011416550964188800731119157218870156061002561932122514430573003611011405110613292018175411971576', standard_qr)

    def test_encode_compact_seedqr(self):
        standard_qr = seedqr.seed_to_seedqr('abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about', compact=True)
        self.assertEqual(bytes(16), standard_qr)

        standard_qr = seedqr.seed_to_seedqr('dignity utility vacant shiver thought canoe feel multiply item youth actor coyote', compact=True)
        self.assertEqual(b'>\x1e\x0b\xc1\xe3\x1e\x0eC\x154\x8bv\xdf\xec\n\x98', standard_qr)

        standard_qr = seedqr.seed_to_seedqr('attack pizza motion avocado network gather crop fresh patrol unusual wild holiday candy pony ranch winter theme error hybrid van cereal salon goddess expire', compact=True)
        self.assertEqual(b'\x0et\xb6A\x07\xf9L\xc0\xcc\xfa\xe6\xa1=\xcb\xec6b\x15O\xecg\xe0\xe0\t\x99\xc0x\x92Y}\x19\n', standard_qr)
