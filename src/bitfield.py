#class to store bitfield data and use it easily in other parts of the project

class Bitfield:
    def __init__(self, num_pieces, data = None):
        self.num_pieces =num_pieces
        num_bytes = (num_pieces + 7)//8

        if data: 
            self.bits = bytearray(data)
        else:
            #zero out in accordance with number of bytes
            self.bits = bytearray(num_bytes)

    def has_piece(self, index):
        byte_index = index//8
        bit_offset = 7 - (index % 8)
        
        if self.bits[byte_index] & (1 << bit_offset):
            return True
        else:
            return False
        
    def set_piece(self, index):
        byte_index = index // 8 
        bit_offset = 7 -(index%8)
        self.bits[byte_index] |= (1<<bit_offset)
    
    def to_bytes(self):
        return bytes(self.bits)
    
    def get_wanted_pieces(self, other):
        """ Returns indices that other has but self doesn't"""
        return [i for i in range(self.num_pieces) if other.has_piece(i) and not self.has_piece(i)]


    def check_completion(self):
        for i in range(self.num_pieces):
            if not self.has_piece(i):
                return False   
        return True


    