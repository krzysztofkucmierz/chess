

class Square:

    ALPHACOLS = { 0: 'a', 1: 'b', 2: 'c', 3: 'd', 4: 'e', 5: 'f', 6: 'g', 7: 'h' }
    
    def __init__(self, row: int, col: int, piece = None):
        self.row = row
        self.col = col
        self.piece = piece
        #self.alphacol = self.ALPHACOLS[col]

    def __eq__(self, other):
        return self.row == other.row and self.col == other.col
    
    def has_piece(self) -> bool:
        return self.piece != None

    def isempty(self):
        return not self.has_piece()

    def has_team_piece(self, color: str):
        return self.has_piece() and self.piece.color == color

    def has_enemy_piece(self, color: str):
        return self.has_piece() and self.piece.color != color

    def isempty_or_enemy(self, color: str):
        return self.isempty() or self.has_enemy_piece(color)

    # check if a square is on the board or outside of the board    
    @staticmethod
    def in_range(*args):
        for arg in args:
            if arg < 0 or arg > 7:
                return False

        return True
    
    @staticmethod
    def get_alphacol(col):
       ALPHACOLS = { 0: 'a', 1: 'b', 2: 'c', 3: 'd', 4: 'e', 5: 'f', 6: 'g', 7: 'h' }
       return ALPHACOLS[col]