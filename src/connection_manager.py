import socket
import threading
import time

from peer_handler import PeerHandler

# manages TCP connections for the peer
class ConnectionManager:
    def __init__(self, my_peer_id, peers, piece_manager):
        self.my_peer_id = int(my_peer_id)
        self.peers = peers
        self.piece_manager = piece_manager

        self.server_socket = None
        self.handlers = []
        self.running = True

        # find my peer info
        self.my_info = None
        for p in peers:
            if p.peer_id == self.my_peer_id:
                self.my_info = p
                break

# open server socket and listen for incoming connections
def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.server_socket.bind((self.my_info.host_name, self.my_info.port))
        self.server_socket.listen()

        print(f"Peer {self.my_peer_id} listening on port {self.my_info.port}")

        thread = threading.Thread(target=self.accept_connections)
        thread.start()
def accept_connections(self):
        while self.running:
            try:
                sock, addr = self.server_socket.accept()

                handler = PeerHandler(
                    sock,
                    self.my_peer_id,
                    None,
                    self.piece_manager
                )

                handler.start()
                self.handlers.append(handler)

            except:
                break

#on startup, connect outbound to all lower-ID peers in order
#spawns one peer_handler thread per connection in both directions
def connect_to_previous_peers(self):
        for peer in self.peers:
            if peer.peer_id >= self.my_peer_id:
                break

            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((peer.host_name, peer.port))

                print(f"Peer {self.my_peer_id} connected to {peer.peer_id}")

                handler = PeerHandler(
                    sock,
                    self.my_peer_id,
                    peer.peer_id,
                    self.piece_manager
                )

                handler.start()
                self.handlers.append(handler)

            except Exception as e:
                print(f"Failed to connect to peer {peer.peer_id}: {e}")

#tracks all active peer handler instances
def get_handlers(self):
        return self.handlers

#polls all peers completion status to know when to shut down
def monitor_completion(self):
        while self.running:
            time.sleep(5)

            if self.piece_manager.check_completion():
                print(f"Peer {self.my_peer_id} finished downloading")

                self.shutdown()
 #shutdown 
def shutdown(self):
        self.running = False

        for handler in self.handlers:
            handler.stop()

        try:
            self.server_socket.close()
        except:
            pass

        print(f"Peer {self.my_peer_id} shutting down")

