"""Regression tests for castling legality rules (IMPROVEMENTS.md item 1.3).

Two castling rules were not enforced in king_moves():
- castling OUT of check was allowed (no "king not currently in check" test), and
- the square the King passes THROUGH (d1/d8 queenside, f1/f8 kingside) was never
  tested for attack — only the destination, plus a proxy test that moving the
  rook would not expose the own king (which does not detect an attacked transit
  square at all).

Now castling requires: king not in check, transit square not attacked,
destination square not attacked. Note that an attacked b-file square (crossed
only by the rook) legitimately does NOT prevent queenside castling.

Run standalone:  python .\tests\test_castling_legality.py
Or with pytest:  pytest tests
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
os.chdir(REPO_ROOT)  # asset paths inside src are relative to the repo root

from board import Board
from const import WHITE_PIECE_COLOR, BLACK_PIECE_COLOR, ROWS, COLS
from piece import King, Rook


def empty_board():
    board = Board()
    for row in range(ROWS):
        for col in range(COLS):
            board.squares[row][col].piece = None
    return board


def castling_setup(extra_pieces):
    """White king e1 + rooks a1/h1 with full castling rights, black king a8,
    plus extra (piece, row, col) attackers; returns the board."""
    board = empty_board()
    board.squares[7][4].piece = King(WHITE_PIECE_COLOR)
    board.squares[7][0].piece = Rook(WHITE_PIECE_COLOR)
    board.squares[7][7].piece = Rook(WHITE_PIECE_COLOR)
    board.squares[0][0].piece = King(BLACK_PIECE_COLOR)
    for piece, row, col in extra_pieces:
        board.squares[row][col].piece = piece
    board.dump_to_squares_fast_method()
    return board


def king_castle_targets(board):
    king = board.squares[7][4].piece
    king.clear_moves()
    board.calc_moves(king, 7, 4)
    return {m.final.col for m in king.moves if abs(m.final.col - m.initial.col) == 2}


def test_both_castles_allowed_without_threats():
    board = castling_setup([])
    assert king_castle_targets(board) == {2, 6}


def test_castling_out_of_check_refused():
    # black rook e5 gives check along the e-file
    board = castling_setup([(Rook(BLACK_PIECE_COLOR), 3, 4)])
    assert king_castle_targets(board) == set(), "castling out of check must be refused"


def test_queenside_castling_through_attacked_transit_square_refused():
    # black rook d5 attacks d1, which the king passes through (destination c1 is safe)
    board = castling_setup([(Rook(BLACK_PIECE_COLOR), 3, 3)])
    assert king_castle_targets(board) == {6}, "only kingside castling should remain legal"


def test_kingside_castling_through_attacked_transit_square_refused():
    # black rook f5 attacks f1, which the king passes through (destination g1 is safe)
    board = castling_setup([(Rook(BLACK_PIECE_COLOR), 3, 5)])
    assert king_castle_targets(board) == {2}, "only queenside castling should remain legal"


def test_castling_into_attacked_destination_refused():
    # black rook c5 attacks the queenside destination c1
    board = castling_setup([(Rook(BLACK_PIECE_COLOR), 3, 2)])
    assert king_castle_targets(board) == {6}, "only kingside castling should remain legal"


def test_attacked_rook_path_square_does_not_prevent_queenside_castling():
    # black rook b5 attacks b1, crossed only by the rook — queenside castling stays legal
    board = castling_setup([(Rook(BLACK_PIECE_COLOR), 3, 1)])
    assert king_castle_targets(board) == {2, 6}


if __name__ == "__main__":
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_")]
    for name, fn in tests:
        fn()
        print(f"OK: {name}")
    print(f"All {len(tests)} castling-legality regression tests passed.")
