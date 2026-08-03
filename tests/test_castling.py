"""Regression tests for castling execution (Bug 5 / IMPROVEMENTS.md item 1.1).

Board.move() used to execute `rook.moves[-1]` to relocate the rook during castling.
That list goes stale whenever the rook's moves are recalculated after the king's
castle move was generated — exactly what happens inside AI.minimax(), which iterates
pieces with clear_moves=False. Result: rook teleported to a wrong square, or an
IndexError on an empty list, leaving corrupted state that later blocked legitimate
(mostly queenside) castling in the real game.

These tests drive castling through the same calc_moves()/valid_move()/move() path
minimax uses and assert the rook always lands on its proper square.

This file is the seed of the test harness described in IMPROVEMENTS.md section 4;
a perft test (perft(3) = 8,902 / perft(4) = 197,281 from the start position) should
be added next to catch move-generation regressions.

Run standalone:  python .\tests\test_castling.py
Or with pytest:  pytest tests
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
os.chdir(REPO_ROOT)  # asset paths inside src are relative to the repo root

from board import Board
from piece import King, Rook


def clear_squares(board, coords):
    for row, col in coords:
        board.squares[row][col].piece = None
    board.dump_to_squares_fast_method()


def find_castle_move(king, target_col):
    for move in king.moves:
        if abs(move.final.col - move.initial.col) == 2 and move.final.col == target_col:
            return move
    return None


def run_castling_case(name, king_pos, rook_pos, cleared, king_target_col, rook_target_col):
    board = Board()
    clear_squares(board, cleared)
    king_row, king_col = king_pos
    rook_row, rook_col = rook_pos
    king = board.squares[king_row][king_col].piece
    rook = board.squares[rook_row][rook_col].piece
    assert isinstance(king, King) and isinstance(rook, Rook), f"{name}: board setup wrong"

    # 1. generate the king's moves, including the castle move
    king.clear_moves()
    board.calc_moves(king, king_row, king_col)
    castle = find_castle_move(king, king_target_col)
    assert castle is not None, f"{name}: castle move not generated"

    # 2. recalculate the rook's own moves AFTER the king's — the minimax
    #    piece-iteration order that made rook.moves stale in the old code
    rook.clear_moves()
    board.calc_moves(rook, rook_row, rook_col)
    assert len(rook.moves) > 0, f"{name}: rook should have ordinary moves"

    # 3. execute the castle the way minimax does (clear_moves=False)
    assert board.valid_move(king, castle), f"{name}: castle not in king.moves"
    board.move(king, castle, clear_moves=False, ai_minimax=True)

    assert board.squares[king_row][king_target_col].piece is king, f"{name}: king not on target square"
    assert board.squares[rook_row][rook_target_col].piece is rook, f"{name}: rook not on target square"
    assert board.squares[rook_row][rook_col].piece is None, f"{name}: rook origin square not emptied"
    assert rook.moved, f"{name}: rook.moved flag not set"


def test_white_queenside_castling():
    run_castling_case("white queenside", (7, 4), (7, 0), [(7, 1), (7, 2), (7, 3)], 2, 3)


def test_white_kingside_castling():
    run_castling_case("white kingside", (7, 4), (7, 7), [(7, 5), (7, 6)], 6, 5)


def test_black_queenside_castling():
    run_castling_case("black queenside", (0, 4), (0, 0), [(0, 1), (0, 2), (0, 3)], 2, 3)


def test_black_kingside_castling():
    run_castling_case("black kingside", (0, 4), (0, 7), [(0, 5), (0, 6)], 6, 5)


def test_castling_with_empty_rook_move_list():
    # the old code crashed here with IndexError on rook.moves[-1]
    board = Board()
    clear_squares(board, [(7, 5), (7, 6)])
    king = board.squares[7][4].piece
    rook = board.squares[7][7].piece
    king.clear_moves()
    board.calc_moves(king, 7, 4)
    castle = find_castle_move(king, 6)
    assert castle is not None
    rook.clear_moves()
    board.move(king, castle, clear_moves=False, ai_minimax=True)
    assert board.squares[7][5].piece is rook


if __name__ == "__main__":
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_")]
    for name, fn in tests:
        fn()
        print(f"OK: {name}")
    print(f"All {len(tests)} castling regression tests passed.")
