#logger writing to 'log_peer_[peerID].log’ at the working directory as per page 9 of the spec
import time
import threading


class PeerLogger:
    def __init__(self, peer_id):
        self.peer_id = peer_id
        self.file_name = f"log_peer_{peer_id}.log"
        self.lock = threading.Lock()

    def _time(self):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    def _write(self, message):
        line = f"[{self._time()}]: {message}\n"

        with self.lock:
            with open(self.file_name, "a") as f:
                f.write(line)

    # tcp connection logs
    def log_tcp_connection(self, other_peer_id):
        self._write(
            f"Peer {self.peer_id} makes a connection to Peer {other_peer_id}."
        )

    def log_tcp_connected_from(self, other_peer_id):
        self._write(
            f"Peer {self.peer_id} is connected from Peer {other_peer_id}."
        )

    # change of preferred neighbors/change of optimisticall unchoked neighbor
    def log_preferred_neighbors(self, neighbors):
        neighbor_list = ", ".join(str(n) for n in neighbors)

        self._write(
            f"Peer {self.peer_id} has the preferred neighbors {neighbor_list}."
        )

    def log_optimistic_neighbor(self, neighbor_id):
        self._write(
            f"Peer {self.peer_id} has the optimistically unchoked neighbor {neighbor_id}."
        )

    # unchoke/choke
    def log_unchoked(self, neighbor_id):
        self._write(
            f"Peer {self.peer_id} is unchoked by {neighbor_id}."
        )

    def log_choked(self, neighbor_id):
        self._write(
            f"Peer {self.peer_id} is choked by {neighbor_id}."
        )

    # receiving interest messages
    def log_interested(self, neighbor_id):
        self._write(
            f"Peer {self.peer_id} received the 'interested' message from {neighbor_id}."
        )

    def log_not_interested(self, neighbor_id):
        self._write(
            f"Peer {self.peer_id} received the 'not interested' message from {neighbor_id}."
        )

    # have message
    def log_have(self, neighbor_id, piece_index):
        self._write(
            f"Peer {self.peer_id} received the 'have' message from {neighbor_id} for the piece {piece_index}."
        )

    def log_downloaded_piece(self, neighbor_id, piece_index, num_pieces):
        self._write(
            f"Peer {self.peer_id} has downloaded the piece {piece_index} from {neighbor_id}. "
            f"Now the number of pieces it has is {num_pieces}."
        )

    # completion of download
    def log_complete(self):
        self._write(
            f"Peer {self.peer_id} has downloaded the complete file."
        )