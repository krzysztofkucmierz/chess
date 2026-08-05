"""Regression tests for IMPROVEMENTS.md items 1.7, 1.8, 1.9 and 1.11.

- 1.7: current_state.captured was set only by external callers (the GUI path and
  the minimax root), so deep search nodes read a stale flag in Board.move() and
  wrongly decremented the piece counters / stamped last_move_when_piece_captured
  for non-captures. Now move() inspects the destination square itself.
- 1.8: pawn-check detection guarded the wrong row: for the black king the row
  actually indexed is row-1, but the guard tested row+1, so at row 0 the index
  -1 silently wrapped around to row 7 and reported a phantom check.
- 1.9: auto-queen promotion executed even during legality probes
  (test_check=True), allocating a Queen object for every probe of a 7th-rank
  pawn move. Promotion now runs only for real moves.
- 1.11: Piece.is_black() returned bool(~(...)) which is True for every input
  (~0 == -1, ~0x40 == -65). Now it tests the color bit with 'not'.

Run standalone:  python .\tests\test_state_bugs.py
Or with pytest:  pytest tests
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
os.chdir(REPO_ROOT)  # asset paths inside src are relative to the repo root

import board as board_module
from board import Board
from const import WHITE_PIECE_COLOR, BLACK_PIECE_COLOR, PAWN_PIECE, ROWS, COLS
from game import Game
from move import Move
from piece import (King, Pawn, Queen, has_enemy_piece, has_team_piece,
                   is_black, is_white)
from square import Square


def empty_board():
    board = Board()
    for row in range(ROWS):
        for col in range(COLS):
            board.squares[row][col].piece = None
    return board


def play(board, from_sq, to_sq):
    piece = board.squares[from_sq[0]][from_sq[1]].piece
    piece.clear_moves()
    board.calc_moves(piece, from_sq[0], from_sq[1])
    for move in piece.moves:
        if (move.final.row, move.final.col) == to_sq:
            board.move(piece, move, clear_moves=False, ai_minimax=True)
            return piece
    raise AssertionError(f"move {from_sq} -> {to_sq} was not generated")


def game_play(game, from_sq, to_sq):
    """Make a move the way minimax does: move on the current board state, then
    prepare the next one."""
    board = game.board_states[game.move_count]
    piece = play(board, from_sq, to_sq)
    game.prepare_board_state_for_next_move()
    return piece


# ---------- item 1.7: 'captured' flag computed inside Board.move() ----------

def test_capture_sets_flag_and_decrements_counter_without_external_call():
    game = Game()
    game_play(game, (6, 4), (4, 4))   # 1. e4
    game_play(game, (1, 3), (3, 3))   # 1... d5
    game_play(game, (4, 4), (3, 3))   # 2. exd5 - no set_capturing_move_flag() call
    state = game.board_states[game.move_count].current_state
    assert state.captured, "a capture must set the captured flag inside move() itself"
    assert state.black_pieces_count == 15, "black must be one piece down after exd5"
    assert state.white_pieces_count == 16


def test_stale_captured_flag_is_not_reused_for_a_quiet_move():
    game = Game()
    # poison the flag the way stale search state used to: pretend the previous
    # node was a capture
    game.board_states[game.move_count].current_state.captured = True
    game_play(game, (7, 6), (5, 5))   # 1. Nf3 - a quiet move
    state = game.board_states[game.move_count].current_state
    assert not state.captured, "a quiet move must clear the captured flag"
    assert state.white_pieces_count == 16 and state.black_pieces_count == 16, \
        "a quiet move must not decrement any piece counter"
    assert state.last_move_when_piece_captured == 0, \
        "a quiet move must not stamp last_move_when_piece_captured"


# ---------- item 1.8: pawn-check negative-index wraparound ----------

def test_pawn_on_row_0_does_not_phantom_check_king_on_row_7():
    board = empty_board()
    # a white pawn on row 0 exists transiently during promotion legality probes;
    # with the old guard squares[-1][col+-1] wrapped around to row 7
    board.squares[0][2].piece = Pawn(WHITE_PIECE_COLOR)
    board.squares[0][2].piece.moved = True
    board.squares[7][1].piece = King(BLACK_PIECE_COLOR)
    board.squares[5][7].piece = King(WHITE_PIECE_COLOR)
    board.dump_to_squares_fast_method()
    assert not board.is_king_checked(BLACK_PIECE_COLOR), \
        "a pawn on row 0 must not check a king on row 7 (index wraparound)"


def test_real_pawn_check_still_detected():
    board = empty_board()
    board.squares[3][3].piece = Pawn(WHITE_PIECE_COLOR)   # attacks (2,2) and (2,4)
    board.squares[3][3].piece.moved = True
    board.squares[2][4].piece = King(BLACK_PIECE_COLOR)
    board.squares[7][7].piece = King(WHITE_PIECE_COLOR)
    board.dump_to_squares_fast_method()
    assert board.is_king_checked(BLACK_PIECE_COLOR), \
        "a genuine pawn check must still be detected"


# ---------- item 1.9: no promotion during legality probes ----------

class CountingQueen(Queen):
    instances = 0

    def __init__(self, color):
        CountingQueen.instances += 1
        super().__init__(color)


def test_promotion_skipped_in_probes_but_executed_for_real_moves():
    board = empty_board()
    pawn = Pawn(WHITE_PIECE_COLOR)
    pawn.moved = True
    board.squares[1][0].piece = pawn
    board.squares[7][4].piece = King(WHITE_PIECE_COLOR)
    board.squares[4][7].piece = King(BLACK_PIECE_COLOR)
    board.dump_to_squares_fast_method()

    original_queen = board_module.Queen
    board_module.Queen = CountingQueen
    try:
        CountingQueen.instances = 0
        # calc_moves() probes every candidate with in_check() (test_check=True)
        pawn.clear_moves()
        board.calc_moves(pawn, 1, 0)
        assert CountingQueen.instances == 0, \
            "legality probes must not allocate Queen objects"
        assert isinstance(board.squares[1][0].piece, Pawn), \
            "the probed pawn must stay a pawn on its original square"

        play(board, (1, 0), (0, 0))   # the real promotion move
        assert CountingQueen.instances == 1, \
            "a real promotion must create exactly one Queen"
        assert isinstance(board.squares[0][0].piece, Queen), \
            "the real move must leave a Queen on the promotion square"
    finally:
        board_module.Queen = original_queen


# ---------- item 1.11: int fast-path color helpers ----------

def test_int_color_helpers():
    white_pawn = PAWN_PIECE | WHITE_PIECE_COLOR
    black_pawn = PAWN_PIECE

    assert is_white(white_pawn) and not is_black(white_pawn), \
        "a white piece must not be reported as black"
    assert is_black(black_pawn) and not is_white(black_pawn)

    assert has_team_piece(black_pawn, BLACK_PIECE_COLOR)
    assert not has_team_piece(white_pawn, BLACK_PIECE_COLOR)
    assert has_enemy_piece(white_pawn, BLACK_PIECE_COLOR)
    assert not has_enemy_piece(black_pawn, BLACK_PIECE_COLOR)
    assert not has_enemy_piece(white_pawn, WHITE_PIECE_COLOR)


if __name__ == "__main__":
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_")]
    for name, fn in tests:
        fn()
        print(f"OK: {name}")
    print(f"All {len(tests)} state-bug regression tests passed.")
