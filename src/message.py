from __future__ import annotations

import struct

from src.bitfield import Bitfield


HANDSHAKE_HEADER = b"P2PFILESHARINGPROJ"
HANDSHAKE_ZEROS = b"\x00" * 10
HANDSHAKE_LENGTH = 32

CHOKE = 0
UNCHOKE = 1
INTERESTED = 2
NOT_INTERESTED = 3
HAVE = 4
BITFIELD = 5
REQUEST = 6
PIECE = 7

def build_handshake(peer_id: int) -> bytes:
    return HANDSHAKE_HEADER + HANDSHAKE_ZEROS + struct.pack(">I", int(peer_id))


def parse_handshake(data: bytes) -> int:
    if len(data) != HANDSHAKE_LENGTH:
        raise ValueError(f"Invalid handshake length: expected {HANDSHAKE_LENGTH}, got {len(data)}")

    if data[:18] != HANDSHAKE_HEADER:
        raise ValueError("Invalid handshake header")

    if data[18:28] != HANDSHAKE_ZEROS:
        raise ValueError("Invalid handshake zero bits")

    return struct.unpack(">I", data[28:32])[0]


def build_message(msg_type: int, payload: bytes = b"") -> bytes:
    if not 0 <= int(msg_type) <= 255:
        raise ValueError("Message type must fit in one byte")

    payload_bytes = bytes(payload)
    msg_length = 1 + len(payload_bytes)
    return struct.pack(">I", msg_length) + struct.pack(">B", int(msg_type)) + payload_bytes


def parse_message(data: bytes) -> tuple[int, bytes]:
    if len(data) < 5:
        raise ValueError("Message too short")

    msg_length = struct.unpack(">I", data[:4])[0]
    if msg_length < 1:
        raise ValueError("Message length must include the message type byte")

    if len(data) != 4 + msg_length:
        raise ValueError("Message length mismatch")

    msg_type = data[4]
    payload = data[5:]
    return msg_type, payload


def build_have(piece_index: int) -> bytes:
    return build_message(HAVE, struct.pack(">I", int(piece_index)))


def parse_have(payload: bytes) -> int:
    if len(payload) != 4:
        raise ValueError("Invalid HAVE payload length")
    return struct.unpack(">I", payload)[0]


def build_request(piece_index: int) -> bytes:
    return build_message(REQUEST, struct.pack(">I", int(piece_index)))


def parse_request(payload: bytes) -> int:
    if len(payload) != 4:
        raise ValueError("Invalid REQUEST payload length")
    return struct.unpack(">I", payload)[0]


def build_bitfield(bitfield_obj) -> bytes:
    if isinstance(bitfield_obj, Bitfield):
        payload = bitfield_obj.to_bytes()
    elif hasattr(bitfield_obj, "to_bytes") and callable(bitfield_obj.to_bytes):
        payload = bitfield_obj.to_bytes()
    else:
        payload = bytes(bitfield_obj)
    return build_message(BITFIELD, payload)


def parse_bitfield(payload: bytes, num_pieces: int | None = None) -> Bitfield:
    if num_pieces is None:
        num_pieces = len(payload) * 8
    expected_bytes = (int(num_pieces) + 7) // 8
    if len(payload) != expected_bytes:
        raise ValueError(
            f"Invalid BITFIELD payload length: expected {expected_bytes}, got {len(payload)}"
        )
    return Bitfield(int(num_pieces), data=payload)


def build_piece(piece_index: int, piece_data: bytes) -> bytes:
    payload = struct.pack(">I", int(piece_index)) + bytes(piece_data)
    return build_message(PIECE, payload)


def parse_piece(payload: bytes) -> tuple[int, bytes]:
    if len(payload) < 4:
        raise ValueError("Invalid PIECE payload length")
    piece_index = struct.unpack(">I", payload[:4])[0]
    return piece_index, payload[4:]


def recv_exact(sock, num_bytes: int) -> bytes:
    if num_bytes < 0:
        raise ValueError("num_bytes must be non-negative")

    data = bytearray()
    while len(data) < num_bytes:
        chunk = sock.recv(num_bytes - len(data))
        if not chunk:
            raise ConnectionError(
                f"Socket closed before receiving {num_bytes} bytes; received {len(data)} bytes"
            )
        data.extend(chunk)
    return bytes(data)


def recv_message(sock) -> tuple[int, bytes]:
    length_bytes = recv_exact(sock, 4)
    msg_length = struct.unpack(">I", length_bytes)[0]
    if msg_length < 1:
        raise ValueError("Invalid message length")
    body = recv_exact(sock, msg_length)
    return parse_message(length_bytes + body)
