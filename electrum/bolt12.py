# -*- coding: utf-8 -*-
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2023 The Electrum developers
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
import asyncio
import copy
import io
import os
import time

from . import ecc
from .lnmsg import OnionWireSerializer
from .onion_message import Timeout
from .segwit_addr import bech32_decode, DecodedBech32, convertbits
from .util import OldTaskGroup


def is_offer(data: str):
    d = bech32_decode(data, ignore_long_length=True, with_checksum=False)
    if d == DecodedBech32(None, None, None):
        return False
    return d.hrp == 'lno'


def decode_offer(data):
    if isinstance(data, str):
        d = bech32_decode(data, ignore_long_length=True, with_checksum=False)
        d = bytes(convertbits(d.data, 5, 8))
        # we bomb on trailing 0, remove
        while d[-1] == 0:
            d = d[:-1]
    else:
        d = data
    with io.BytesIO(d) as f:
        return OnionWireSerializer.read_tlv_stream(fd=f, tlv_stream_name='offer')


def decode_invoice_request(data):
    if isinstance(data, str):
        d = bech32_decode(data, ignore_long_length=True, with_checksum=False)
        d = bytes(convertbits(d.data, 5, 8))
        # we bomb on trailing 0, remove
        while d[-1] == 0:
            d = d[:-1]
    else:
        d = data
    with io.BytesIO(d) as f:
        return OnionWireSerializer.read_tlv_stream(fd=f, tlv_stream_name='invoice_request', signing_key_path=['invreq_payer_id', 'key'])


def decode_invoice(data):
    if isinstance(data, str):
        d = bech32_decode(data, ignore_long_length=True, with_checksum=False)
        d = bytes(convertbits(d.data, 5, 8))
        # we bomb on trailing 0, remove
        while d[-1] == 0:
            d = d[:-1]
    else:
        d = data
    with io.BytesIO(d) as f:
        return OnionWireSerializer.read_tlv_stream(fd=f, tlv_stream_name='invoice', signing_key_path=['invoice_node_id', 'node_id'])


def encode_invoice_request(data, payer_key):
    with io.BytesIO() as fd:
        OnionWireSerializer.write_tlv_stream(fd=fd, tlv_stream_name='invoice_request', signing_key=payer_key, **data)
        return fd.getvalue()


def encode_invoice(data, signing_key):
    with io.BytesIO() as fd:
        OnionWireSerializer.write_tlv_stream(fd=fd, tlv_stream_name='invoice', signing_key=signing_key, **data)
        return fd.getvalue()


async def request_invoice(lnwallet: 'LNWallet', bolt12_offer, amount_msat: int, note: str):
    #   - if it chooses to sends an `invoice_request`, it sends an onion message:
    #     - if `offer_paths` is set:
    #       - MUST send the onion message via any path in `offer_paths` to the final `onion_msg_hop`.`blinded_node_id` in that path
    #     - otherwise:
    #       - MUST send the onion message to `offer_issuer_id`
    #     - MAY send more than one `invoice_request` onion message at once.
    # TODO: offer_paths
    node_id = bolt12_offer['offer_issuer_id']['id']

    session_key = os.urandom(32)
    blinding = ecc.ECPrivkey(session_key).get_public_key_bytes()

    # One is a response to an offer; this contains the `offer_issuer_id` or `offer_paths` and
    # all other offer details, and is generally received over an onion
    # message: if it's valid and refers to a known offer, the response is
    # generally to reply with an `invoice` using the `reply_path` field of
    # the onion message.
    data = copy.deepcopy(bolt12_offer)  # include all fields of the offer
    data.update({
        'invreq_payer_id': {'key': blinding},
        'invreq_metadata': {'blob': b'\x00'},  # TODO: fill invreq_metadata unique, and store for association
        'invreq_amount': {'msat': amount_msat}
    })

    invreq_tlv = encode_invoice_request(data, session_key)
    req_payload = {
        'invoice_request': {'invoice_request': invreq_tlv}
    }

    try:
        lnwallet.logger.info(f'requesting bolt12 invoice')
        rcpt_data, payload = await lnwallet.onion_message_manager.submit_reqrpy(payload=req_payload, node_id_or_blinded_path=node_id)
        lnwallet.logger.info(f'{rcpt_data=} {payload=}')
        invoice_tlv = payload['invoice']['invoice']
        with io.BytesIO(invoice_tlv) as fd:
            invoice_data = OnionWireSerializer.read_tlv_stream(fd=fd, tlv_stream_name='invoice',
                                                               signing_key_path=('invoice_node_id', 'node_id'))
        lnwallet.logger.warning(f'invoice_data: {invoice_data!r}')
    except Timeout:
        lnwallet.logger.info('timeout waiting for bolt12 invoice')
        raise
    except Exception as e:
        lnwallet.logger.error(f'error requesting bolt12 invoice: {e!r}')
        raise

    return invoice_data

    #
    # try:
    #     ids, complete = await util.wait_for2(self.get_channel_range(), LN_P2P_NETWORK_TIMEOUT)
    # except asyncio.TimeoutError as e:
    #     raise GracefulDisconnect("query_channel_range timed out") from e
