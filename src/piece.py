import os
from move import Move
from typing import List

class Piece:
    def __init__(self, name: str, color: str, value: float, texture=None, texture_rect=None):
        self.name = name
        self.color = color
        
        # this is a value of a piece (not a direction)
        value_sign = 1 if color == 'white' else -1
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
        self.texture = os.path.join(f'assets/images/imgs-{size}px/{self.color}_{self.name}.png')

    def show_moves(self):
        print(f"valid moves for piece: ")
        for i, move in enumerate(self.moves):
            move.show(self.name, f"{i} : {self.color}")

    def add_move(self, move: Move):
        self.moves.append(move)

    def clear_moves(self):
        self.moves = []

class Pawn(Piece):
    def __init__(self, color: str):
        self.dir = -1 if color == 'white' else 1
        self.en_passant = False # can the Pawn be captured en passant?
        super().__init__("pawn", color, 1.0)
        
class Knight(Piece):
    def __init__(self, color: str):
        super().__init__("knight", color, 3.0)

class Bishop(Piece):
    def __init__(self, color: str):
        super().__init__("bishop", color, 3.0)


class Rook(Piece):
    def __init__(self, color: str):
        super().__init__("rook", color, 5.0)


class Queen(Piece):
    def __init__(self, color: str):
        super().__init__("queen", color, 9.0)


class King(Piece):
    def __init__(self, color: str):
        self.left_rook = None
        self.right_rook = None
        super().__init__("king", color, 10000.0)