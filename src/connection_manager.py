from __future__ import annotations

import socket
import threading
import time
import random

from src.peer_handler import PeerHandler


class ConnectionManager:
    def __init__(self, current_peer, peers, piece_manager, logger, common_config=None):
        self.current_peer = current_peer
        self.peers = list(peers)
        self.piece_manager = piece_manager
        self.logger = logger
        self.common_config = common_config

        self.server_socket = None
        self.running = False
        self.file_composed = False
        self.handlers = []
        self.handlers_lock = threading.Lock()
        self.completed_peer_ids = set()
        self.completed_peer_ids_lock = threading.Lock()
        self.accept_thread = None
        self.preferred_neighbors = set()
        self.optimistic_neighbor = None
        self.preferred_thread = None
        self.optimistic_thread = None

        self._peer_index = self._find_peer_index(self.current_peer.peer_id)
        self._lower_id_peers = self.peers[:self._peer_index]
        self._higher_id_peers = self.peers[self._peer_index + 1 :]
        self._expected_incoming = len(self._higher_id_peers)
        self._accepted_incoming = 0
        if self.piece_manager.check_completion():
            self.completed_peer_ids.add(self.current_peer.peer_id)

    def _find_peer_index(self, peer_id: int) -> int:
        for index, peer in enumerate(self.peers):
            if peer.peer_id == int(peer_id):
                return index
        raise ValueError(f"Peer ID not found in peer list: {peer_id}")

    def start(self) -> None:
        self.running = True
        self._start_server()
        self._start_accept_thread()
        self._start_unchoking_threads()
        self._connect_to_lower_id_peers()

    def _start_server(self) -> None:
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.current_peer.host_name, self.current_peer.port))
        self.server_socket.listen(len(self.peers))
        self.server_socket.settimeout(1.0)

    def _start_accept_thread(self) -> None:
        self.accept_thread = threading.Thread(target=self._accept_incoming_connections, daemon=True)
        self.accept_thread.start()

    def _start_unchoking_threads(self) -> None:
        if self.common_config is None:
            return

        self.preferred_thread = threading.Thread(target=self._preferred_neighbor_loop, daemon=True)
        self.preferred_thread.start()

        self.optimistic_thread = threading.Thread(target=self._optimistic_unchoke_loop, daemon=True)
        self.optimistic_thread.start()

    def _accept_incoming_connections(self) -> None:
        while self.running and self._accepted_incoming < self._expected_incoming:
            try:
                client_socket, _ = self.server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            self._accepted_incoming += 1
            self._register_handler(client_socket, incoming=True)

    def _connect_to_lower_id_peers(self) -> None:
        for peer in self._lower_id_peers:
            if not self.running:
                return

            while self.running:
                connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                connection.settimeout(2.0)
                try:
                    connection.connect((peer.host_name, peer.port))
                    connection.settimeout(None)
                    self.logger.log_tcp_connection_made(peer.peer_id)
                    self._register_handler(connection, neighbor_peer_id=peer.peer_id, incoming=False)
                    break
                except OSError:
                    connection.close()
                    time.sleep(1.0)

    def _register_handler(self, sock, neighbor_peer_id=None, incoming=False) -> PeerHandler:
        handler = PeerHandler(
            sock=sock,
            my_peer_id=self.current_peer.peer_id,
            neighbor_peer_id=neighbor_peer_id,
            piece_manager=self.piece_manager,
            logger=self.logger,
            peer_handlers=self.handlers,
            incoming=incoming,
        )
        with self.handlers_lock:
            self.handlers.append(handler)
        handler.start()
        return handler

    def _get_active_handlers(self) -> list[PeerHandler]:
        with self.handlers_lock:
            return [handler for handler in self.handlers if handler.is_alive() and handler.running]

    def _preferred_neighbor_loop(self) -> None:
        interval = self.common_config.unchoking_interval
        while self.running:
            time.sleep(interval)
            if not self.running:
                break
            self._reselect_preferred_neighbors()

    def _optimistic_unchoke_loop(self) -> None:
        interval = self.common_config.optimistic_unchoking_interval
        while self.running:
            time.sleep(interval)
            if not self.running:
                break
            self._reselect_optimistic_neighbor()

    def _reselect_preferred_neighbors(self) -> None:
        active_handlers = self._get_active_handlers()
        interested_handlers = [handler for handler in active_handlers if handler.is_interested()]
        preferred_count = self.common_config.number_of_preferred_neighbors
        previous_preferred = set(self.preferred_neighbors)

        if self.piece_manager.check_completion():
            random.shuffle(interested_handlers)
            selected_handlers = interested_handlers[:preferred_count]
            for handler in active_handlers:
                handler.consume_downloaded_bytes()
        else:
            scored_handlers = []
            for handler in interested_handlers:
                scored_handlers.append((handler.consume_downloaded_bytes(), random.random(), handler))
            scored_handlers.sort(key=lambda item: (-item[0], item[1]))
            selected_handlers = [handler for _, _, handler in scored_handlers[:preferred_count]]

        self.preferred_neighbors = {
            handler.neighbor_peer_id for handler in selected_handlers if handler.neighbor_peer_id is not None
        }
        self._apply_unchoke_policy(active_handlers)
        if self.logger is not None and self.preferred_neighbors != previous_preferred:
            self.logger.log_preferred_neighbors(sorted(self.preferred_neighbors))

    def _reselect_optimistic_neighbor(self) -> None:
        active_handlers = self._get_active_handlers()
        previous_optimistic = self.optimistic_neighbor
        candidates = [
            handler
            for handler in active_handlers
            if handler.is_interested()
            and handler.neighbor_peer_id is not None
            and handler.neighbor_peer_id not in self.preferred_neighbors
            and handler.is_peer_choked()
        ]

        chosen_handler = random.choice(candidates) if candidates else None
        self.optimistic_neighbor = (
            chosen_handler.neighbor_peer_id if chosen_handler is not None else None
        )
        self._apply_unchoke_policy(active_handlers)
        if (
            chosen_handler is not None
            and self.logger is not None
            and self.optimistic_neighbor != previous_optimistic
        ):
            self.logger.log_optimistic_unchoke(chosen_handler.neighbor_peer_id)

    def _apply_unchoke_policy(self, active_handlers: list[PeerHandler] | None = None) -> None:
        if active_handlers is None:
            active_handlers = self._get_active_handlers()

        allowed_neighbors = set(self.preferred_neighbors)
        optimistic_is_active = False
        if self.optimistic_neighbor is not None:
            for handler in active_handlers:
                if handler.neighbor_peer_id == self.optimistic_neighbor and handler.is_interested():
                    allowed_neighbors.add(self.optimistic_neighbor)
                    optimistic_is_active = True
                    break
            if not optimistic_is_active:
                self.optimistic_neighbor = None

        for handler in active_handlers:
            neighbor_peer_id = handler.neighbor_peer_id
            if neighbor_peer_id is None:
                continue
            should_choke = neighbor_peer_id not in allowed_neighbors
            try:
                handler.set_peer_choked(should_choke)
            except Exception:
                continue

    def wait_for_completion(self, poll_interval: float = 1.0) -> None:
        try:
            while self.running:
                if self.piece_manager.check_completion() and not self.file_composed:
                    if self.common_config is not None:
                        self.piece_manager.compose_file(self.common_config.file_name)
                    self.file_composed = True
                    self._mark_peer_complete(self.current_peer.peer_id)

                if self._all_peers_appear_complete():
                    break

                time.sleep(poll_interval)
        finally:
            self.stop()

    def _all_peers_appear_complete(self) -> bool:
        if not self.piece_manager.check_completion():
            return False

        self._mark_peer_complete(self.current_peer.peer_id)
        self._update_completed_neighbors()

        with self.completed_peer_ids_lock:
            return len(self.completed_peer_ids) == len(self.peers)

    def _update_completed_neighbors(self) -> None:
        with self.handlers_lock:
            handlers = list(self.handlers)

        for handler in handlers:
            neighbor_peer_id = getattr(handler, "neighbor_peer_id", None)
            neighbor_bitfield = getattr(handler, "neighbor_bitfield", None)
            if neighbor_peer_id is None or neighbor_bitfield is None:
                continue
            if neighbor_bitfield.check_completion():
                self._mark_peer_complete(neighbor_peer_id)

    def _mark_peer_complete(self, peer_id: int) -> None:
        with self.completed_peer_ids_lock:
            self.completed_peer_ids.add(int(peer_id))

    def stop(self) -> None:
        if not self.running:
            return

        self.running = False

        if self.server_socket is not None:
            try:
                self.server_socket.close()
            except OSError:
                pass

        if self.accept_thread is not None and self.accept_thread.is_alive():
            self.accept_thread.join(timeout=2.0)

        if self.preferred_thread is not None and self.preferred_thread.is_alive():
            self.preferred_thread.join(timeout=2.0)

        if self.optimistic_thread is not None and self.optimistic_thread.is_alive():
            self.optimistic_thread.join(timeout=2.0)

        with self.handlers_lock:
            handlers = list(self.handlers)

        for handler in handlers:
            handler.stop()

        for handler in handlers:
            handler.join(timeout=2.0)
