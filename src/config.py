from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path


@dataclass
class CommonConfig:
    number_of_preferred_neighbors: int = 0
    unchoking_interval: int = 0
    optimistic_unchoking_interval: int = 0
    file_name: str = ""
    file_size: int = 0
    piece_size: int = 0
    number_of_pieces: int = 0


@dataclass
class PeerInfo:
    peer_id: int
    host_name: str
    port: int
    has_file: bool


def _iter_config_lines(file_path: str | Path):
    with Path(file_path).open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.split("#", 1)[0].strip()
            if line:
                yield line_number, line


def load_common_config(file_path: str | Path = "Common.cfg") -> CommonConfig:
    config = CommonConfig()
    expected_keys = {
        "NumberOfPreferredNeighbors": "number_of_preferred_neighbors",
        "UnchokingInterval": "unchoking_interval",
        "OptimisticUnchokingInterval": "optimistic_unchoking_interval",
        "FileName": "file_name",
        "FileSize": "file_size",
        "PieceSize": "piece_size",
    }
    seen_keys = set()

    for line_number, line in _iter_config_lines(file_path):
        parts = line.split(None, 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid Common.cfg entry on line {line_number}: {line}")

        key, value = parts
        if key not in expected_keys:
            raise ValueError(f"Unknown Common.cfg key on line {line_number}: {key}")

        attribute = expected_keys[key]
        if attribute == "file_name":
            setattr(config, attribute, value.strip())
        else:
            setattr(config, attribute, int(value))
        seen_keys.add(key)

    missing_keys = [key for key in expected_keys if key not in seen_keys]
    if missing_keys:
        raise ValueError(f"Missing Common.cfg entries: {', '.join(missing_keys)}")

    if config.file_size < 0:
        raise ValueError("FileSize must be non-negative")
    if config.piece_size <= 0:
        raise ValueError("PieceSize must be positive")
    if config.number_of_preferred_neighbors < 0:
        raise ValueError("NumberOfPreferredNeighbors must be non-negative")
    if config.unchoking_interval <= 0:
        raise ValueError("UnchokingInterval must be positive")
    if config.optimistic_unchoking_interval <= 0:
        raise ValueError("OptimisticUnchokingInterval must be positive")

    config.number_of_pieces = math.ceil(config.file_size / config.piece_size) if config.file_size else 0
    return config


def load_peer_info(file_path: str | Path = "PeerInfo.cfg") -> list[PeerInfo]:
    peers = []
    seen_peer_ids = set()

    for line_number, line in _iter_config_lines(file_path):
        parts = line.split()
        if len(parts) != 4:
            raise ValueError(f"Invalid PeerInfo.cfg entry on line {line_number}: {line}")

        peer_id_text, host_name, port_text, has_file_text = parts
        peer = PeerInfo(
            peer_id=int(peer_id_text),
            host_name=host_name,
            port=int(port_text),
            has_file=bool(int(has_file_text)),
        )

        if peer.peer_id <= 0:
            raise ValueError(f"Peer ID must be positive: {peer.peer_id}")
        if peer.peer_id in seen_peer_ids:
            raise ValueError(f"Duplicate peer ID in PeerInfo.cfg: {peer.peer_id}")
        if peer.port <= 0:
            raise ValueError(f"Invalid port for peer {peer.peer_id}: {peer.port}")
        if has_file_text not in {"0", "1"}:
            raise ValueError(f"has_file must be 0 or 1 for peer {peer.peer_id}")

        seen_peer_ids.add(peer.peer_id)
        peers.append(peer)

    return peers


def get_peer_by_id(peer_id, peers):
    for peer in peers:
        if peer.peer_id == int(peer_id):
            return peer
    return None
