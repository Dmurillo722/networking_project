#parses Common.cfg and PeerInfo.cfg
# Computes total number of pieces by dividing filesize by piece size

import math


class CommonConfig:
    def __init__(self):
        self.number_of_preferred_neighbors = 0
        self.unchoking_interval = 0
        self.optimistic_unchoking_interval = 0
        self.file_name = ""
        self.file_size = 0
        self.piece_size = 0
        self.number_of_pieces = 0


class PeerInfo:
    def __init__(self, peer_id, host_name, port, has_file):
        self.peer_id = int(peer_id)
        self.host_name = host_name
        self.port = int(port)
        self.has_file = bool(int(has_file))


def load_common_config(file_path="Common.cfg"):
    # Make config object
    config = CommonConfig()

    with open(file_path, "r") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            parts = line.split()
            key = parts[0]
            value = parts[1]

            if key == "NumberOfPreferredNeighbors":
                config.number_of_preferred_neighbors = int(value)
            elif key == "UnchokingInterval":
                config.unchoking_interval = int(value)
            elif key == "OptimisticUnchokingInterval":
                config.optimistic_unchoking_interval = int(value)
            elif key == "FileName":
                config.file_name = value
            elif key == "FileSize":
                config.file_size = int(value)
            elif key == "PieceSize":
                config.piece_size = int(value)

    # Find total number of pieces
    if config.piece_size > 0:
        config.number_of_pieces = math.ceil(config.file_size / config.piece_size)

    return config


def load_peer_info(file_path="PeerInfo.cfg"):
    # Store all peers here
    peers = []

    with open(file_path, "r") as file:
        for line in file:
            line = line.strip()

            # Skip blank lines
            if not line:
                continue

            # Skip comment lines
            if line.startswith("#"):
                continue

            parts = line.split()

            peer_id = parts[0]
            host_name = parts[1]
            port = parts[2]
            has_file = parts[3]

            peer = PeerInfo(peer_id, host_name, port, has_file)
            peers.append(peer)

    return peers


def get_peer_by_id(peer_id, peers):
    # Find one peer by id
    for peer in peers:
        if peer.peer_id == int(peer_id):
            return peer
    return None