from square import Square
from const import *

class Move:
    def __init__(self, initial, final):
        # initial and final are squares
        self.initial = initial
        self.final = final
        
    def __eq__(self, other):
        return self.initial == other.initial and self.final == other.final
    
    def show(self, piece_name: str, comment: str):
        print(f" Piece {piece_name}: {Square.get_alphacol(self.initial.col)}{ROWS-self.initial.row} -> {Square.get_alphacol(self.final.col)}{ROWS-self.final.row} ({comment})")