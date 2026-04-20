import threading

from src.message import (
    BITFIELD,
    CHOKE,
    HAVE,
    INTERESTED,
    NOT_INTERESTED,
    PIECE,
    REQUEST,
    UNCHOKE,
    build_bitfield,
    build_handshake,
    build_have,
    build_message,
    build_piece,
    build_request,
    parse_bitfield,
    parse_handshake,
    parse_have,
    parse_piece,
    parse_request,
    recv_exact,
    recv_message,
)


class PeerHandler(threading.Thread):
    def __init__(
        self,
        sock,
        my_peer_id,
        neighbor_peer_id=None,
        piece_manager=None,
        logger=None,
        peer_handlers=None,
        incoming=False,
    ):
        super().__init__()
        self.sock = sock
        self.my_peer_id = my_peer_id
        self.neighbor_peer_id = neighbor_peer_id
        self.piece_manager = piece_manager
        self.logger = logger
        self.peer_handlers = peer_handlers if peer_handlers is not None else []
        self.incoming = incoming

        self.running = True
        self.am_choked = True
        self.neighbor_interested = False
        self.neighbor_bitfield = None
        self._received_any_actual_message = False
        self.peer_choked = True
        self.downloaded_bytes_interval = 0
        self.pending_request_piece = None
        self.state_lock = threading.Lock()

    def run(self):
        try:
            self.do_handshake()
            self.send_bitfield()

            while self.running:
                msg_type, payload = self.receive_message()
                self.handle_message(msg_type, payload)
        except (ConnectionError, OSError):
            self.stop()
        except Exception as error:
            if self.running:
                print(f"Peer handler error: {error}")
            self.stop()

    def do_handshake(self):
        self.sock.sendall(build_handshake(self.my_peer_id))
        peer_id = parse_handshake(recv_exact(self.sock, 32))

        if self.neighbor_peer_id is None:
            self.neighbor_peer_id = peer_id
        elif self.neighbor_peer_id != peer_id:
            raise ValueError("Peer ID does not match handshake")

        if self.incoming and self.logger is not None:
            self.logger.log_tcp_connection_received(self.neighbor_peer_id)

    def send_bitfield(self):
        if self.piece_manager is None:
            return

        bitfield = self.piece_manager.get_bitfield()
        if not any(bitfield.to_bytes()):
            return

        self.send_message(build_bitfield(bitfield))

    def send_message(self, message):
        self.sock.sendall(message)

    def receive_message(self):
        return recv_message(self.sock)

    def handle_message(self, msg_type, payload):
        if self._received_any_actual_message:
            if msg_type == BITFIELD:
                raise ValueError("BITFIELD message is only allowed as the first message after handshake")
        else:
            self._received_any_actual_message = True

        if msg_type == CHOKE:
            self.handle_choke()
        elif msg_type == UNCHOKE:
            self.handle_unchoke()
        elif msg_type == INTERESTED:
            self.handle_interested()
        elif msg_type == NOT_INTERESTED:
            self.handle_not_interested()
        elif msg_type == HAVE:
            self.handle_have(payload)
        elif msg_type == BITFIELD:
            self.handle_bitfield(payload)
        elif msg_type == REQUEST:
            self.handle_request(payload)
        elif msg_type == PIECE:
            self.handle_piece(payload)
        else:
            raise ValueError(f"Unknown message type: {msg_type}")

    def handle_choke(self):
        self.am_choked = True
        pending_piece = None
        with self.state_lock:
            pending_piece = self.pending_request_piece
            self.pending_request_piece = None
        if pending_piece is not None and self.piece_manager is not None:
            self.piece_manager.mark_not_requested(pending_piece)
        if self.logger and self.neighbor_peer_id is not None:
            self.logger.log_choked(self.neighbor_peer_id)

    def handle_unchoke(self):
        self.am_choked = False
        if self.logger and self.neighbor_peer_id is not None:
            self.logger.log_unchoked(self.neighbor_peer_id)
        self.request_next_piece()

    def handle_interested(self):
        with self.state_lock:
            self.neighbor_interested = True
        if self.logger and self.neighbor_peer_id is not None:
            self.logger.log_interested(self.neighbor_peer_id)

    def handle_not_interested(self):
        with self.state_lock:
            self.neighbor_interested = False
        if self.logger and self.neighbor_peer_id is not None:
            self.logger.log_not_interested(self.neighbor_peer_id)

    def handle_have(self, payload):
        piece_index = parse_have(payload)
        if self.neighbor_bitfield is None and self.piece_manager is not None:
            empty_payload = b"\x00" * ((self.piece_manager.num_pieces + 7) // 8)
            self.neighbor_bitfield = parse_bitfield(empty_payload, self.piece_manager.num_pieces)

        self.update_neighbor_bitfield(piece_index)
        if self.logger and self.neighbor_peer_id is not None:
            self.logger.log_have(self.neighbor_peer_id, piece_index)
        self.evaluate_interest()

    def handle_bitfield(self, payload):
        if self.piece_manager is None:
            return
        self.neighbor_bitfield = parse_bitfield(payload, self.piece_manager.num_pieces)
        self.evaluate_interest()

    def handle_request(self, payload):
        piece_index = parse_request(payload)
        if self.piece_manager is None:
            return

        if self.is_peer_choked():
            return

        if self.piece_manager.has_piece(piece_index):
            self.send_message(build_piece(piece_index, self.piece_manager.get_piece(piece_index)))

    def handle_piece(self, payload):
        piece_index, piece_data = parse_piece(payload)
        if self.piece_manager is None:
            return

        with self.state_lock:
            self.downloaded_bytes_interval += len(piece_data)
            if self.pending_request_piece == piece_index:
                self.pending_request_piece = None

        self.piece_manager.save_piece(piece_index, piece_data)
        if self.logger and self.neighbor_peer_id is not None:
            self.logger.log_downloaded_piece(
                self.neighbor_peer_id,
                piece_index,
                self.piece_manager.count_owned_pieces(),
            )
            if self.piece_manager.mark_completion_logged():
                self.logger.log_complete_file()

        self.broadcast_have(piece_index)
        self.recheck_all_interest()
        self.request_next_piece()

    def evaluate_interest(self):
        if self.piece_manager is None or self.neighbor_bitfield is None:
            return

        if self.piece_manager.need_from_bitfield(self.neighbor_bitfield):
            self.send_message(build_message(INTERESTED))
        else:
            self.send_message(build_message(NOT_INTERESTED))

    def request_next_piece(self):
        if self.am_choked or self.piece_manager is None or self.neighbor_bitfield is None:
            return

        with self.state_lock:
            if self.pending_request_piece is not None:
                return

        piece_index = self.piece_manager.get_needed_piece_index(self.neighbor_bitfield)
        if piece_index is None:
            self.send_message(build_message(NOT_INTERESTED))
            return

        with self.state_lock:
            self.pending_request_piece = piece_index
        self.send_message(build_request(piece_index))

    def update_neighbor_bitfield(self, piece_index):
        if self.neighbor_bitfield is not None:
            self.neighbor_bitfield.set_piece(piece_index)

    def broadcast_have(self, piece_index):
        message = build_have(piece_index)
        for handler in list(self.peer_handlers):
            if handler is self or not getattr(handler, "running", False):
                continue
            try:
                handler.send_message(message)
            except Exception:
                continue

    def recheck_all_interest(self):
        for handler in list(self.peer_handlers):
            if handler is self or not getattr(handler, "running", False):
                continue
            try:
                handler.evaluate_interest()
            except Exception:
                continue

    def stop(self):
        self.running = False
        pending_piece = None
        with self.state_lock:
            pending_piece = self.pending_request_piece
            self.pending_request_piece = None
        if pending_piece is not None and self.piece_manager is not None:
            self.piece_manager.mark_not_requested(pending_piece)
        try:
            self.sock.close()
        except Exception:
            pass

    def is_interested(self) -> bool:
        with self.state_lock:
            return self.neighbor_interested

    def is_peer_choked(self) -> bool:
        with self.state_lock:
            return self.peer_choked

    def set_peer_choked(self, should_choke: bool) -> bool:
        message = build_message(CHOKE if should_choke else UNCHOKE)
        with self.state_lock:
            if self.peer_choked == bool(should_choke):
                return False
            self.peer_choked = bool(should_choke)

        self.send_message(message)
        return True

    def consume_downloaded_bytes(self) -> int:
        with self.state_lock:
            downloaded = self.downloaded_bytes_interval
            self.downloaded_bytes_interval = 0
            return downloaded
