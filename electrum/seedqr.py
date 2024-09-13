# Copyright (C) 2024 The Electrum developers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import textwrap
from typing import Union

from .crypto import sha256
from .mnemonic import Wordlist


def seed_from_seedqr(data: Union[str, bytes]) -> str:
    wordlist = Wordlist.from_file('english.txt')
    if isinstance(data, str):
        assert len(data) % 12 == 0
        return _seed_from_standard_seedqr(data, wordlist)
    elif isinstance(data, bytes):
        assert len(data) in [16, 32]
        return _seed_from_compact_seedqr(data, wordlist)
    else:
        raise ValueError('seedqr not a str or bytes')


def _seed_from_standard_seedqr(data: str, wordlist) -> str:
    seedwords = []
    for item in textwrap.wrap(data, 4):
        idx = int(item)
        seedwords.append(wordlist[idx])

    return ' '.join(seedwords)


def _seed_from_compact_seedqr(data: bytes, wordlist):
    seedqr = int.from_bytes(data, byteorder='big', signed=False)
    hashed = int.from_bytes(sha256(data), byteorder="big")
    n_seedwords = 12 if len(data) == 16 else 24
    checksum_length = 11 * n_seedwords // 33
    calculated_checksum = hashed >> (256 - checksum_length)
    seedqr = seedqr << checksum_length
    seedwords = []
    for i in range(0, n_seedwords):
        base = seedqr >> i*11
        idx = base & ((1 << 11) - 1)
        if i == 0:
            idx = idx | calculated_checksum
        seedwords.insert(0, wordlist[idx])

    return ' '.join(seedwords)


def seed_to_seedqr(seed: str, compact=True) -> Union[str, bytes]:
    wordlist = Wordlist.from_file('english.txt')
    if compact:
        return _seed_to_compact_seedqr(seed, wordlist)
    else:
        return _seed_to_standard_seedqr(seed, wordlist)


def _seed_to_compact_seedqr(seed: str, wordlist) -> bytes:
    seed_words = seed.split(' ')
    assert len(seed_words) in [12, 24]

    seedqr = 0
    for word in seed_words:
        idx = wordlist.index(word)
        seedqr = (seedqr << 11) | idx

    checksum_length = 11 * len(seed_words) // 33
    entropy_length = 32 * checksum_length
    seedqr = seedqr >> checksum_length
    seedqr = seedqr.to_bytes(length=entropy_length//8, byteorder='big', signed=False)

    return seedqr


def _seed_to_standard_seedqr(seed: str, wordlist) -> str:
    seedqr = ''
    seed_list = seed.split(' ')
    for word in seed_list:
        idx = wordlist.index(word)
        seedqr += '{:04d}'.format(idx)

    return seedqr
