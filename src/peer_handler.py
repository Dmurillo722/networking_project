#Handles one neighbor per connection thread in its lifetime

#Handshake Phase:
#Sends and receives handshake, then validates header and peer ID
#Sends bitfield and receives bitfield if neighbor has pieces
#Declares interest based on bitfield diff
#choke-> stop sending requests
#unchoke->pick a random needed piece and send request
#interested-> mark neighbor as interested
#not interested-> mark neighbor as not interested
#if has piece -> update neighbor's bitfield and re-evaluate interest
#bitfield->store neighbor's bitfield and evaluate interest
#request-> if neighbor is unchoked by us, respond with piece
#piece -> write to piece manager, update rate, and send next request
#broadcast "have" to all other neighbors
#re-evaluate interest for all other neighbors

import threading

from src.message import (
    CHOKE,
    UNCHOKE,
    INTERESTED,
    NOT_INTERESTED,
    HAVE,
    BITFIELD,
    REQUEST,
    PIECE,
    build_handshake,
    parse_handshake,
    build_message,
    build_request,
    build_have,
    build_bitfield,
    parse_have,
    parse_bitfield,
    parse_request,
    parse_piece,
    recv_exact,
    recv_message
)


class PeerHandler(threading.Thread):
    def __init__(self, sock, my_peer_id, neighbor_peer_id=None, piece_manager=None):
        super().__init__()
        self.sock = sock
        self.my_peer_id = my_peer_id
        self.neighbor_peer_id = neighbor_peer_id
        self.piece_manager = piece_manager

        self.running = True
        self.am_choked = True
        self.neighbor_interested = False
        self.neighbor_bitfield = None

    def run(self):
        # Do handshake first
        try:
            self.do_handshake()
            self.send_bitfield()

            while self.running:
                msg_type, payload = self.receive_message()
                self.handle_message(msg_type, payload)

        except Exception as e:
            print(f"Peer handler error: {e}")
            self.stop()

    def do_handshake(self):
        # Send my handshake
        handshake = build_handshake(self.my_peer_id)
        self.sock.sendall(handshake)

        # Read neighbor handshake
        data = recv_exact(self.sock, 32)
        peer_id = parse_handshake(data)

        # Save neighbor id if needed
        if self.neighbor_peer_id is None:
            self.neighbor_peer_id = peer_id

        # Make sure peer id matches
        elif self.neighbor_peer_id != peer_id:
            raise ValueError("Peer ID does not match handshake")

    def send_bitfield(self):
        # Send bitfield if I have one
        if self.piece_manager is None:
            return

        bitfield = self.piece_manager.get_bitfield()
        message = build_bitfield(bitfield)
        self.send_message(message)

    def send_message(self, message):
        # Send bytes on socket
        self.sock.sendall(message)

    def receive_message(self):
        # Read one normal message
        return recv_message(self.sock)

    def handle_message(self, msg_type, payload):
        # Stop requests if choked
        if msg_type == CHOKE:
            self.handle_choke()

        # Request piece if unchoked
        elif msg_type == UNCHOKE:
            self.handle_unchoke()

        # Mark neighbor interested
        elif msg_type == INTERESTED:
            self.handle_interested()

        # Mark neighbor not interested
        elif msg_type == NOT_INTERESTED:
            self.handle_not_interested()

        # Update one piece in neighbor bitfield
        elif msg_type == HAVE:
            self.handle_have(payload)

        # Save full neighbor bitfield
        elif msg_type == BITFIELD:
            self.handle_bitfield(payload)

        # Send piece if allowed
        elif msg_type == REQUEST:
            self.handle_request(payload)

        # Save piece and ask for next one
        elif msg_type == PIECE:
            self.handle_piece(payload)

    def handle_choke(self):
        self.am_choked = True

    def handle_unchoke(self):
        self.am_choked = False
        self.request_next_piece()

    def handle_interested(self):
        self.neighbor_interested = True

    def handle_not_interested(self):
        self.neighbor_interested = False

    def handle_have(self, payload):
        piece_index = parse_have(payload)

        if self.neighbor_bitfield is None:
            return

        self.update_neighbor_bitfield(piece_index)
        self.evaluate_interest()

    def handle_bitfield(self, payload):
        self.neighbor_bitfield = parse_bitfield(payload)
        self.evaluate_interest()

    def handle_request(self, payload):
        piece_index = parse_request(payload)

        if self.piece_manager is None:
            return

        # Real choke check can go here later
        if self.piece_manager.has_piece(piece_index):
            piece_data = self.piece_manager.get_piece(piece_index)
            message = self.build_piece_message(piece_index, piece_data)
            self.send_message(message)

    def handle_piece(self, payload):
        piece_index, piece_data = parse_piece(payload)

        if self.piece_manager is None:
            return

        self.piece_manager.save_piece(piece_index, piece_data)
        self.broadcast_have(piece_index)
        self.recheck_all_interest()
        self.request_next_piece()

    def evaluate_interest(self):
        # Decide if I want anything from this neighbor
        if self.piece_manager is None or self.neighbor_bitfield is None:
            return

        if self.piece_manager.need_from_bitfield(self.neighbor_bitfield):
            self.send_message(build_message(INTERESTED))
        else:
            self.send_message(build_message(NOT_INTERESTED))

    def request_next_piece(self):
        # Pick one needed piece
        if self.am_choked:
            return

        if self.piece_manager is None or self.neighbor_bitfield is None:
            return

        piece_index = self.piece_manager.get_needed_piece_index(self.neighbor_bitfield)

        if piece_index is None:
            return

        message = build_request(piece_index)
        self.send_message(message)

    def update_neighbor_bitfield(self, piece_index):
        # Update one bit later
        pass

    def broadcast_have(self, piece_index):
        # Tell other neighbors later
        message = build_have(piece_index)
        print(f"Need to broadcast HAVE for piece {piece_index}")

    def recheck_all_interest(self):
        # Recheck interest later
        pass

    def build_piece_message(self, piece_index, piece_data):
        # Import helper later if you want
        from src.message import build_piece
        return build_piece(piece_index, piece_data)

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except:
            pass