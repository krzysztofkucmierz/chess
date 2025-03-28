# Screen dimensions
WIDTH = 800
HEIGHT = 800

# Board dimensions
ROWS = 8
COLS = 8
SQSIZE = WIDTH // COLS

# AI constants
AI_MAX_DEPTH = 2

from enum import Enum

# Play mode
class GameMode(Enum):
    PLAYER_VS_PLAYER_MODE = 1
    PLAYER_VS_AI_MODE = 2 # AI plays black pieces
    AI_VS_PLAYER_MODE = 3 # AI plays white pieces



# Piece coding on the board
PAWN_PIECE = 0x1
KNIGHT_PIECE = 0x2
BISHOP_PIECE = 0x4
ROOK_PIECE = 0x8
QUEEN_PIECE = 0x10
KING_PIECE = 0x20
ANY_PIECE = 0x3F
WHITE_PIECE_COLOR = 0x40 # bit indicating white color
BLACK_PIECE_COLOR = 0x0 # for clarity when the above bit is off
PIECE_MOVED = 0x80 # bit indicating whether the piece was already moved during the game
EN_PASSANT_PAWN = 0x100 # bit indicating whether the piece can be captured en passant (applies only to Pawns!)