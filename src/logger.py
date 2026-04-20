from __future__ import annotations

from datetime import datetime
from pathlib import Path
import threading


class PeerLogger:
    def __init__(self, peer_id: int, log_dir: str | Path = "."):
        self.peer_id = int(peer_id)
        self.log_path = Path(log_dir) / f"log_peer_{self.peer_id}.log"
        self._lock = threading.Lock()

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _write(self, message: str) -> None:
        line = f"[{self._timestamp()}]: {message}\n"
        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(line)

    def log_tcp_connection_made(self, peer_id: int) -> None:
        self._write(f"Peer {self.peer_id} makes a connection to Peer {int(peer_id)}.")

    def log_tcp_connection_received(self, peer_id: int) -> None:
        self._write(f"Peer {self.peer_id} is connected from Peer {int(peer_id)}.")

    def log_choked(self, peer_id: int) -> None:
        self._write(f"Peer {self.peer_id} is choked by Peer {int(peer_id)}.")

    def log_unchoked(self, peer_id: int) -> None:
        self._write(f"Peer {self.peer_id} is unchoked by Peer {int(peer_id)}.")

    def log_interested(self, peer_id: int) -> None:
        self._write(f"Peer {self.peer_id} received the 'interested' message from Peer {int(peer_id)}.")

    def log_not_interested(self, peer_id: int) -> None:
        self._write(f"Peer {self.peer_id} received the 'not interested' message from Peer {int(peer_id)}.")

    def log_have(self, peer_id: int, piece_index: int) -> None:
        self._write(
            f"Peer {self.peer_id} received the 'have' message from Peer {int(peer_id)} for the piece {int(piece_index)}."
        )

    def log_downloaded_piece(self, peer_id: int, piece_index: int, number_of_pieces: int) -> None:
        self._write(
            f"Peer {self.peer_id} has downloaded the piece {int(piece_index)} from Peer {int(peer_id)}. "
            f"Now the number of pieces it has is {int(number_of_pieces)}."
        )

    def log_complete_file(self) -> None:
        self._write(f"Peer {self.peer_id} has downloaded the complete file.")

    def log_preferred_neighbors(self, neighbor_ids) -> None:
        neighbors = ", ".join(str(int(peer_id)) for peer_id in neighbor_ids)
        self._write(f"Peer {self.peer_id} has the preferred neighbors {neighbors}.")

    def log_optimistic_unchoke(self, peer_id: int) -> None:
        self._write(f"Peer {self.peer_id} has the optimistically unchoked neighbor {int(peer_id)}.")


class Logger(PeerLogger):
    pass
