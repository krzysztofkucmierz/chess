"""Regression tests for en passant state handling (IMPROVEMENTS.md items 1.4 + 1.5).

Two closely related bugs:
- 1.4: set_true_en_passant() flagged a pawn as capturable en passant after ANY
  pawn move, including single-square pushes, so illegal en passant captures were
  offered as valid moves.
- 1.5: Game.undo_en_passant() re-flagged whatever piece last moved with
  en_passant=True unconditionally — knights and rooks got the attribute, and a
  single-pushed pawn became "capturable" — on every undo, including the
  thousands performed inside minimax.

Now the flag is set only after a two-square pawn push, and undo re-flags only a
pawn whose recorded move was a double push.

Run standalone:  python .\tests\test_en_passant.py
Or with pytest:  pytest tests
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
os.chdir(REPO_ROOT)  # asset paths inside src are relative to the repo root

from board import Board
from const import WHITE_PIECE_COLOR, BLACK_PIECE_COLOR, ROWS, COLS
from game import Game
from move import Move
from piece import King, Pawn, Rook
from square import Square


# ---------- board-level tests (item 1.4) ----------

def en_passant_board():
    """White pawn on (3,4) ready to capture en passant, black pawn on (1,3) or
    (2,3) depending on the scenario, kings out of the way."""
    board = Board()
    for row in range(ROWS):
        for col in range(COLS):
            board.squares[row][col].piece = None
    board.squares[3][4].piece = Pawn(WHITE_PIECE_COLOR)
    board.squares[7][7].piece = King(WHITE_PIECE_COLOR)
    board.squares[0][0].piece = King(BLACK_PIECE_COLOR)
    return board


def moves_of(board, row, col):
    piece = board.squares[row][col].piece
    piece.clear_moves()
    board.calc_moves(piece, row, col)
    return {(m.final.row, m.final.col) for m in piece.moves}


def play(board, from_sq, to_sq):
    piece = board.squares[from_sq[0]][from_sq[1]].piece
    piece.clear_moves()
    board.calc_moves(piece, from_sq[0], from_sq[1])
    for move in piece.moves:
        if (move.final.row, move.final.col) == to_sq:
            board.move(piece, move, clear_moves=False, ai_minimax=True)
            return piece
    raise AssertionError(f"move {from_sq} -> {to_sq} was not generated")


def test_single_push_does_not_enable_en_passant():
    board = en_passant_board()
    board.squares[2][3].piece = Pawn(BLACK_PIECE_COLOR)
    board.squares[2][3].piece.moved = True
    board.dump_to_squares_fast_method()

    pawn = play(board, (2, 3), (3, 3))  # black single push, lands next to white pawn
    assert not pawn.en_passant, "single push must not set the en passant flag"
    assert (2, 3) not in moves_of(board, 3, 4), "en passant capture of a single-pushed pawn is illegal"


def test_double_push_enables_en_passant():
    board = en_passant_board()
    board.squares[1][3].piece = Pawn(BLACK_PIECE_COLOR)
    board.dump_to_squares_fast_method()

    pawn = play(board, (1, 3), (3, 3))  # black double push
    assert pawn.en_passant, "double push must set the en passant flag"
    assert (2, 3) in moves_of(board, 3, 4), "en passant capture must be offered"

    play(board, (3, 4), (2, 3))  # execute the en passant capture
    assert board.squares[3][3].piece is None, "captured pawn must be removed from the board"
    assert isinstance(board.squares[2][3].piece, Pawn), "capturing pawn must land behind it"


def test_en_passant_flag_lasts_only_one_move():
    board = en_passant_board()
    board.squares[1][3].piece = Pawn(BLACK_PIECE_COLOR)
    board.squares[5][1].piece = Rook(WHITE_PIECE_COLOR)
    board.dump_to_squares_fast_method()

    pawn = play(board, (1, 3), (3, 3))  # black double push
    play(board, (5, 1), (4, 1))         # white plays something else
    assert not pawn.en_passant, "the en passant flag must be cleared by the next move"
    assert (2, 3) not in moves_of(board, 3, 4), "the en passant capture opportunity is gone"


# ---------- Game-level undo tests (item 1.5) ----------

def game_play(game, from_sq, to_sq):
    """Make a move the way minimax does: move on the current board state, then
    prepare the next one."""
    board = game.board_states[game.move_count]
    piece = play(board, from_sq, to_sq)
    game.prepare_board_state_for_next_move()
    return piece


def flagged_pawn_squares(board):
    return {(row, col) for row in range(ROWS) for col in range(COLS)
            if isinstance(board.squares[row][col].piece, Pawn)
            and board.squares[row][col].piece.en_passant}


def test_undo_after_nonpawn_move_does_not_flag_it():
    game = Game()
    knight = game_play(game, (7, 6), (5, 5))   # 1. white knight
    game_play(game, (0, 1), (2, 2))            # 2. black knight
    game_play(game, (7, 1), (5, 2))            # 3. white knight
    game.undo_last_move()                      # last remaining move: black knight
    black_knight = game.board_states[game.move_count].squares[2][2].piece
    assert not getattr(black_knight, "en_passant", False), \
        "undo must not put an en_passant flag on a knight"
    assert not getattr(knight, "en_passant", False)
    assert flagged_pawn_squares(game.board_states[game.move_count]) == set()


def test_undo_after_single_push_does_not_flag_the_pawn():
    game = Game()
    game_play(game, (7, 6), (5, 5))            # 1. white knight
    pawn = game_play(game, (1, 3), (2, 3))     # 2. black pawn SINGLE push
    game_play(game, (7, 1), (5, 2))            # 3. white knight
    game.undo_last_move()                      # last remaining move: the single push
    assert not pawn.en_passant, \
        "undo must not make a single-pushed pawn capturable en passant"
    assert flagged_pawn_squares(game.board_states[game.move_count]) == set()


def test_undo_restores_en_passant_after_double_push():
    game = Game()
    game_play(game, (7, 6), (5, 5))            # 1. white knight
    pawn = game_play(game, (1, 3), (3, 3))     # 2. black pawn DOUBLE push
    game_play(game, (7, 1), (5, 2))            # 3. white knight (clears the flag)
    assert not pawn.en_passant
    game.undo_last_move()                      # last remaining move: the double push
    assert pawn.en_passant, \
        "undo must restore the en passant flag of a freshly double-pushed pawn"
    assert flagged_pawn_squares(game.board_states[game.move_count]) == {(3, 3)}


if __name__ == "__main__":
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_")]
    for name, fn in tests:
        fn()
        print(f"OK: {name}")
    print(f"All {len(tests)} en passant regression tests passed.")
