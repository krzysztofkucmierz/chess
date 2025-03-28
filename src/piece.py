import os
from const import *
from move import Move
from typing import List


'''
We use int variable for logical representation of pieces in the board state.
It means actual placement of the pieces on the board is encoded in int variables.
'''
        
def is_king(piece_data: int):
    return bool(piece_data & KING_PIECE)

def is_queen(piece_data: int):
    return bool(piece_data & QUEEN_PIECE)

def is_rook(piece_data: int):
    return bool(piece_data & ROOK_PIECE)

def is_bishop(piece_data: int):
    return bool(piece_data & BISHOP_PIECE)

def is_knight(piece_data: int):
    return bool(piece_data & KNIGHT_PIECE)

def is_pawn(piece_data: int):
    return bool(piece_data & PAWN_PIECE)

def piece_moved(piece_data: int):
    return bool(piece_data & PIECE_MOVED)

def is_white(piece_data: int):
    return bool(piece_data & WHITE_PIECE_COLOR)

def is_black(piece_data: int):
    return bool(~(piece_data & WHITE_PIECE_COLOR))

def has_team_piece(piece_data: int, color: int):
    if color == WHITE_PIECE_COLOR:
        return is_white(piece_data)
    else:
        return is_black(piece_data)      

def has_enemy_piece(piece_data: int, color: int):
    if color == WHITE_PIECE_COLOR:
        return is_black(piece_data)
    else:
        return is_white(piece_data) 

def is_piece(piece_data: int):
    return bool(piece_data & ANY_PIECE)

def is_empty(piece_data: int):
    return not bool(piece_data & ANY_PIECE)

def isempty_or_enemy(piece_data: int, color: int):
    return (is_empty(piece_data) or has_enemy_piece(piece_data, color))
    
def en_passant_pawn(piece_data: int):
    return bool(piece_data & EN_PASSANT_PAWN)

def color_name(color: int):
    color = 'white' if is_white(color) else 'black'    
    return color

def decode_piece(piece_data: int):
    # decode color
    color = color_name(piece_data)
    if is_king(piece_data):
        name = "King"
    elif is_queen(piece_data):
        name = "Queen"
    elif is_rook(piece_data):
        name = "Rook"
    elif is_bishop(piece_data):
        name = "Bishop"       
    elif is_knight(piece_data):
        name = "Knight"
    elif is_pawn(piece_data):
        name = "Pawn"
    else:
        name = None

    print(f"{color} {name}")



'''
The Piece class represents visual properties of the pieces.
For actual placement of pieces on the board a different representation is used 
'''
class Piece:
    def __init__(self, name: str, color: int, value: float, texture=None, texture_rect=None):
        self.name = name
        self.color = color
        
        # this is a value of a piece (not a direction)
        value_sign = 1 if color == WHITE_PIECE_COLOR else -1
        self.value = value * value_sign
        self.texture = texture # texture is an image URI for a given piece
        self.set_texture()
        self.texture_rect = texture_rect
        self.moves: List[Move] = []
        self.moved = False # was the piece moved at least 1 time during the game?

    # NEW METHOD!
    def __eq__(self, other):
        if other == None:
            return False
        else:
            return self.name == other.name and self.color == other.color

    def set_texture(self, size=80):
        self.texture = os.path.join(f'assets/images/imgs-{size}px/{color_name(self.color)}_{self.name}.png')

    def show_moves(self):
        print(f"valid moves for piece: ")
        for i, move in enumerate(self.moves):
            move.show(self.name, f"{i} : {self.color}")

    def add_move(self, move: Move):
        self.moves.append(move)

    def clear_moves(self):
        self.moves = []

class Pawn(Piece):
    def __init__(self, color: int):
        self.dir = -1 if color == WHITE_PIECE_COLOR else 1
        self.en_passant = False # can the Pawn be captured en passant?
        super().__init__("pawn", color, 1.0)
        
class Knight(Piece):
    def __init__(self, color: int):
        super().__init__("knight", color, 3.0)

class Bishop(Piece):
    def __init__(self, color: int):
        super().__init__("bishop", color, 3.0)


class Rook(Piece):
    def __init__(self, color: int):
        super().__init__("rook", color, 5.0)


class Queen(Piece):
    def __init__(self, color: int):
        super().__init__("queen", color, 9.0)


class King(Piece):
    def __init__(self, color: int):
        self.left_rook = None
        self.right_rook = None
        super().__init__("king", color, 10000.0)