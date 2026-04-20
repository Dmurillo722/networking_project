from __future__ import annotations

import os
import random
import threading

from src.bitfield import Bitfield


class PieceManager:
    def __init__(self, peer_id, num_pieces, piece_size, file_size, has_file):
        self.peer_id = int(peer_id)
        self.num_pieces = int(num_pieces)
        self.piece_size = int(piece_size)
        self.file_size = int(file_size)
        self.has_file = bool(has_file)
        self.peer_dir = f"peer_{self.peer_id}"
        self.bitfield = Bitfield(self.num_pieces)
        self.requested = set()
        self.completion_logged = False
        self.lock = threading.Lock()

        os.makedirs(self.peer_dir, exist_ok=True)
        self._load_existing_pieces()

    def _piece_path(self, index: int) -> str:
        return os.path.join(self.peer_dir, f"piece_{int(index)}")

    def _load_existing_pieces(self) -> None:
        for piece_index in range(self.num_pieces):
            if os.path.exists(self._piece_path(piece_index)):
                self.bitfield.set_piece(piece_index)

    def initialize_from_complete_file(self, filename: str) -> None:
        source_path = os.path.join(self.peer_dir, filename)
        if not os.path.exists(source_path):
            if self.has_file:
                raise FileNotFoundError(f"Seed file not found: {source_path}")
            return

        with open(source_path, "rb") as source_file:
            for piece_index in range(self.num_pieces):
                piece_data = source_file.read(self.piece_size)
                if not piece_data:
                    break
                with open(self._piece_path(piece_index), "wb") as piece_file:
                    piece_file.write(piece_data)

        with self.lock:
            self.bitfield = Bitfield(self.num_pieces)
            self.requested.clear()
            self.completion_logged = self.bitfield.check_completion()
            self._load_existing_pieces()
            self.completion_logged = self.bitfield.check_completion()

    def get_bitfield(self) -> Bitfield:
        with self.lock:
            return Bitfield(self.num_pieces, data=self.bitfield.to_bytes())

    def has_piece(self, index: int) -> bool:
        with self.lock:
            return self.bitfield.has_piece(int(index))

    def count_owned_pieces(self) -> int:
        with self.lock:
            return sum(1 for piece_index in range(self.num_pieces) if self.bitfield.has_piece(piece_index))

    def need_from_bitfield(self, neighbor_bitfield: Bitfield) -> bool:
        return self.get_needed_piece_index(neighbor_bitfield, mark_requested=False) is not None

    def get_needed_piece_index(self, neighbor_bitfield: Bitfield, mark_requested: bool = True):
        with self.lock:
            needed_pieces = [
                piece_index
                for piece_index in range(self.num_pieces)
                if neighbor_bitfield.has_piece(piece_index)
                and not self.bitfield.has_piece(piece_index)
                and piece_index not in self.requested
            ]

            if not needed_pieces:
                return None

            chosen_piece = random.choice(needed_pieces)
            if mark_requested:
                self.requested.add(chosen_piece)
            return chosen_piece

    def select_piece(self, neighbor_bitfield: Bitfield):
        return self.get_needed_piece_index(neighbor_bitfield, mark_requested=True)

    def save_piece(self, index: int, data: bytes) -> None:
        piece_index = int(index)
        with open(self._piece_path(piece_index), "wb") as piece_file:
            piece_file.write(data)

        with self.lock:
            self.requested.discard(piece_index)
            self.bitfield.set_piece(piece_index)

    def write_piece(self, index, data):
        self.save_piece(index, data)

    def get_piece(self, index: int) -> bytes:
        piece_index = int(index)
        with open(self._piece_path(piece_index), "rb") as piece_file:
            return piece_file.read()

    def read_piece(self, index):
        return self.get_piece(index)

    def mark_not_requested(self, index: int) -> None:
        with self.lock:
            self.requested.discard(int(index))

    def check_completion(self):
        with self.lock:
            return self.bitfield.check_completion()

    def mark_completion_logged(self) -> bool:
        with self.lock:
            if not self.bitfield.check_completion() or self.completion_logged:
                return False
            self.completion_logged = True
            return True

    def compose_file(self, filename):
        output_path = os.path.join(self.peer_dir, filename)
        with open(output_path, "wb") as output_file:
            for piece_index in range(self.num_pieces):
                output_file.write(self.get_piece(piece_index))
