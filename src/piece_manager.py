import threading
import os
from bitfield import Bitfield
import random

class PieceManager: 
    def __init__(self, peer_id, num_pieces, piece_size, file_size, has_file):
        self.peer_id =  peer_id
        self.num_pieces = num_pieces
        self.piece_size = piece_size
        self.file_size = file_size
        self.peer_dir = f"peer_{peer_id}"
        self.bitfield = Bitfield(num_pieces)
        self.requested = set() #pieces that are currently in flight
        self.lock = threading.Lock()
        
    
    def select_piece(self, neighbor_bitfield : Bitfield):
        #pick a random piece that is needed but has not been requested
        #with self.lock:
        self.lock.acquire()
        try:
            #check that the neighbor's bitfield has the a given piece,
            #the piece is not already in our bitfield
            #and the piece has not already been requested
            needed_pieces = [i for i in range(self.num_pieces) 
                             if neighbor_bitfield.has_piece(i)
                             and not self.bitfield.has_piece(i)
                             and i not in self.requested]
            
            if not needed_pieces:
                return None
            
            #randomly choose piece
            chosen = random.choice(needed_pieces)
            self.requested.add(chosen)
            return chosen
        
        finally: 
            self.lock.release()
    
    def write_piece(self, index, data):
        path = os.path.join(self.peer_dir, f"piece_{index}")
        #open the file for writing in binary format
        f = open(path, "wb")
        try:
            f.write(data)
        finally:
            f.close()
            
        
        self.lock.acquire()
        try:
            self.requested.discard(index)
            self.bitfield.set_piece(index)
        finally:
            self.lock.release()

        
        
    def read_piece(self, index):

        path = os.path.join(self.peer_dir, f"piece_{index}")

        f = open(path, "rb")
        try: 
            return f.read()
        finally:
            f.close()
            

    def check_completion(self):
        self.lock.acquire()
        try:
            return self.bitfield.check_completion()
        finally:
            self.lock.release()

    def compose_file(self, filename):
        output_path = os.path.join(self.peer_dir, filename)
        try:
            out = open(output_path, "wb")
            for i in range(self.num_pieces):
                out.write(self.read_piece(i))
        finally:
            out.close()


        
    