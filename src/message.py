#This file handles message encoding and decoding

#Handshake: 18-byte header (string) + 10-byte zero bits + 4 byte peer ID (int)

#Actual messages : 4 byte msg length field + 1 byte message type field + Message payload of variable size
#type chart:
#message type  |value
#choke         | 0
#unchoke       | 1
#interested    | 2
#not interested| 3
#have          | 4
#bitfield      | 5
#request       | 6
#piece         | 7

#'choke’, ‘unchoke’, ‘interested’ and ‘not interested’ messages have no payload.

#‘have’ messages have a payload that contains a 4-byte piece index field.

#‘bitfield’ messages is only sent as the first message right after handshaking is done when
#a connection is established. ‘bitfield’ messages have a bitfield as its payload. 
# (see page 2 on project description for more info)

#read message on corresponding socket

import struct

# Handshake parts
HANDSHAKE_HEADER = b"P2PFILESHARINGPROJ"
HANDSHAKE_ZEROS = b"\x00" * 10
HANDSHAKE_LENGTH = 32

# Message types
CHOKE = 0
UNCHOKE = 1
INTERESTED = 2
NOT_INTERESTED = 3
HAVE = 4
BITFIELD = 5
REQUEST = 6
PIECE = 7


def build_handshake(peer_id: int) -> bytes:
    # Make handshake message
    return HANDSHAKE_HEADER + HANDSHAKE_ZEROS + struct.pack(">I", peer_id)


def parse_handshake(data: bytes) -> int:
    # Check handshake size
    if len(data) != HANDSHAKE_LENGTH:
        raise ValueError("Invalid handshake length")

    header = data[:18]
    zeros = data[18:28]
    peer_id_bytes = data[28:32]

    # Check header
    if header != HANDSHAKE_HEADER:
        raise ValueError("Invalid handshake header")

    # Check zero bits
    if zeros != HANDSHAKE_ZEROS:
        raise ValueError("Invalid handshake zero bits")

    return struct.unpack(">I", peer_id_bytes)[0]


def build_message(msg_type: int, payload: bytes = b"") -> bytes:
    # Make normal message
    msg_length = 1 + len(payload)
    return struct.pack(">I", msg_length) + struct.pack(">B", msg_type) + payload


def parse_message(data: bytes) -> tuple[int, bytes]:
    # Check smallest size
    if len(data) < 5:
        raise ValueError("Message too short")

    msg_length = struct.unpack(">I", data[:4])[0]

    # Check full size
    if len(data) != 4 + msg_length:
        raise ValueError("Message length mismatch")

    msg_type = struct.unpack(">B", data[4:5])[0]
    payload = data[5:]
    return msg_type, payload


def build_have(piece_index: int) -> bytes:
    payload = struct.pack(">I", piece_index)
    return build_message(HAVE, payload)


def parse_have(payload: bytes) -> int:
    if len(payload) != 4:
        raise ValueError("Invalid HAVE payload")
    return struct.unpack(">I", payload)[0]


def build_request(piece_index: int) -> bytes:
    payload = struct.pack(">I", piece_index)
    return build_message(REQUEST, payload)


def parse_request(payload: bytes) -> int:
    if len(payload) != 4:
        raise ValueError("Invalid REQUEST payload")
    return struct.unpack(">I", payload)[0]


def build_bitfield(bitfield_bytes: bytes) -> bytes:
    return build_message(BITFIELD, bitfield_bytes)


def parse_bitfield(payload: bytes) -> bytes:
    return payload


def build_piece(piece_index: int, piece_data: bytes) -> bytes:
    payload = struct.pack(">I", piece_index) + piece_data
    return build_message(PIECE, payload)


def parse_piece(payload: bytes) -> tuple[int, bytes]:
    if len(payload) < 4:
        raise ValueError("Invalid PIECE payload")
    piece_index = struct.unpack(">I", payload[:4])[0]
    piece_data = payload[4:]
    return piece_index, piece_data


def recv_exact(sock, num_bytes: int) -> bytes:
    # Read exact number of bytes
    data = b""
    while len(data) < num_bytes:
        chunk = sock.recv(num_bytes - len(data))
        if not chunk:
            raise ConnectionError("Socket closed early")
        data += chunk
    return data


def recv_handshake(sock) -> int:
    # Read handshake
    data = recv_exact(sock, HANDSHAKE_LENGTH)
    return parse_handshake(data)


def recv_message(sock) -> tuple[int, bytes]:
    # Read normal message
    length_bytes = recv_exact(sock, 4)
    msg_length = struct.unpack(">I", length_bytes)[0]
    body = recv_exact(sock, msg_length)
    return parse_message(length_bytes + body)