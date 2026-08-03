"""Regression tests for sliding-piece move generation (IMPROVEMENTS.md item 1.2).

In straightline_moves() the ray-terminating `break` was nested inside the
"blocker is not a King" guard. When the blocking enemy piece WAS the king, the
loop kept going and generated moves on the squares BEHIND the king (e.g. rook a1
vs king a5 made a6/a7/a8 "legal"), and those moves were accepted by valid_move().
Any enemy piece must terminate the ray; the King check only suppresses the
capture move itself.

Run standalone:  python .\tests\test_sliding_moves.py
Or with pytest:  pytest tests
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
os.chdir(REPO_ROOT)  # asset paths inside src are relative to the repo root

from board import Board
from const import WHITE_PIECE_COLOR, BLACK_PIECE_COLOR, ROWS, COLS
from piece import Bishop, King, Queen, Rook


def empty_board():
    board = Board()
    for row in range(ROWS):
        for col in range(COLS):
            board.squares[row][col].piece = None
    return board


def place(board, piece, row, col):
    board.squares[row][col].piece = piece
    return piece


def moves_of(board, row, col):
    piece = board.squares[row][col].piece
    piece.clear_moves()
    board.calc_moves(piece, row, col)
    return {(m.final.row, m.final.col) for m in piece.moves}


def test_rook_ray_stops_at_enemy_king():
    board = empty_board()
    place(board, Rook(WHITE_PIECE_COLOR), 4, 4)
    place(board, King(BLACK_PIECE_COLOR), 2, 4)
    place(board, King(WHITE_PIECE_COLOR), 7, 7)
    board.dump_to_squares_fast_method()

    moves = moves_of(board, 4, 4)
    assert (3, 4) in moves, "square in front of the enemy king should be reachable"
    assert (2, 4) not in moves, "capturing the enemy king must not be a move"
    assert (1, 4) not in moves, "square behind the enemy king must not be a move"
    assert (0, 4) not in moves, "square behind the enemy king must not be a move"


def test_bishop_ray_stops_at_enemy_king():
    board = empty_board()
    place(board, Bishop(WHITE_PIECE_COLOR), 7, 0)
    place(board, King(BLACK_PIECE_COLOR), 4, 3)
    place(board, King(WHITE_PIECE_COLOR), 7, 7)
    board.dump_to_squares_fast_method()

    moves = moves_of(board, 7, 0)
    assert (5, 2) in moves, "square in front of the enemy king should be reachable"
    assert (4, 3) not in moves, "capturing the enemy king must not be a move"
    assert (3, 4) not in moves, "square behind the enemy king must not be a move"
    assert (2, 5) not in moves, "square behind the enemy king must not be a move"


def test_queen_ray_stops_at_enemy_king():
    board = empty_board()
    place(board, Queen(BLACK_PIECE_COLOR), 0, 0)
    place(board, King(WHITE_PIECE_COLOR), 0, 5)
    place(board, King(BLACK_PIECE_COLOR), 7, 7)
    board.dump_to_squares_fast_method()

    moves = moves_of(board, 0, 0)
    assert (0, 4) in moves, "square in front of the enemy king should be reachable"
    assert (0, 5) not in moves, "capturing the enemy king must not be a move"
    assert (0, 6) not in moves, "square behind the enemy king must not be a move"
    assert (0, 7) not in moves, "square behind the enemy king must not be a move"


def test_rook_ray_still_stops_at_ordinary_enemy_piece():
    # make sure the fix didn't change normal blocking behavior
    board = empty_board()
    place(board, Rook(WHITE_PIECE_COLOR), 4, 4)
    place(board, Rook(BLACK_PIECE_COLOR), 2, 4)
    place(board, King(BLACK_PIECE_COLOR), 0, 0)
    place(board, King(WHITE_PIECE_COLOR), 7, 7)
    board.dump_to_squares_fast_method()

    moves = moves_of(board, 4, 4)
    assert (2, 4) in moves, "capturing an ordinary enemy piece must be a move"
    assert (1, 4) not in moves, "square behind a blocking enemy piece must not be a move"
    assert (0, 4) not in moves, "square behind a blocking enemy piece must not be a move"


if __name__ == "__main__":
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_")]
    for name, fn in tests:
        fn()
        print(f"OK: {name}")
    print(f"All {len(tests)} sliding-move regression tests passed.")
