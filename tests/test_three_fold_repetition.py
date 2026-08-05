"""Regression tests for the three fold repetition rule (Game.check_three_fold_repetition).

The old method was dead code: it returned False on its first line and referenced
a field (last_n_board_positions) that no longer exists. The new implementation
compares position keys built from the per-state squares_fast_method snapshots
(the only reliable history - Piece objects are shared between board states) and
follows FIDE article 9.2: same placement, same side to move, same castling
rights, same en passant flag. The moved-flag of pieces other than the castling
king/rooks must NOT distinguish positions, while lost castling rights MUST.

Run standalone:  python .\tests\test_three_fold_repetition.py
Or with pytest:  pytest tests
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
os.chdir(REPO_ROOT)  # asset paths inside src are relative to the repo root

from const import WHITE_PIECE_COLOR, BLACK_PIECE_COLOR
from game import Game
from piece import King, Pawn, Rook
from test_perft import game_with_position


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
    play(game.board_states[game.move_count], from_sq, to_sq)
    game.prepare_board_state_for_next_move()


# knight shuffle: Nf3 Nf6 Ng1 Ng8 repeated - the start position recurs every 4 plies
KNIGHT_SHUFFLE = [((7, 6), (5, 5)), ((0, 6), (2, 5)),
                  ((5, 5), (7, 6)), ((2, 5), (0, 6))]


def test_knight_shuffle_detected_on_third_occurrence():
    game = Game()
    for ply, (from_sq, to_sq) in enumerate(KNIGHT_SHUFFLE * 2, start=1):
        game_play(game, from_sq, to_sq)
        detected = game.check_three_fold_repetition()
        if ply < 8:
            assert not detected, f"false repetition report after ply {ply}"
        else:
            # start position occurred at ply 0, 4 and 8 (the initial occurrence
            # must count even though board_states[0] was overwritten by ply 1)
            assert detected, "third occurrence of the start position not detected"
    assert game.three_fold_repetition_detected
    assert game.check_draw(), "check_draw() must report the repetition draw"


def test_gui_timing_before_prepare_also_detected():
    """check_draw() runs after Board.move() but BEFORE prepare_board_state_for_next_move()
    in main.py - the detection must work at that timing too."""
    game = Game()
    moves = KNIGHT_SHUFFLE * 2
    for from_sq, to_sq in moves[:-1]:
        game_play(game, from_sq, to_sq)
    play(game.board_states[game.move_count], *moves[-1])  # last ply: no prepare
    assert game.check_three_fold_repetition(), \
        "repetition not detected at the GUI (pre-prepare) call timing"


def rooks_and_kings():
    return [(King(WHITE_PIECE_COLOR), 7, 4), (Rook(WHITE_PIECE_COLOR), 7, 7),
            (King(BLACK_PIECE_COLOR), 0, 4), (Rook(BLACK_PIECE_COLOR), 0, 7)]


def test_lost_castling_rights_distinguish_positions():
    """Rh1-h2 / Rh8-h7 and back recreates the home placement, but the shuffle burns
    the castling rights - the position keys must differ although the placement is
    identical. The moved-flags themselves must NOT leak into the placement component
    (they enter only through the rights)."""
    game = game_with_position(rooks_and_kings(), WHITE_PIECE_COLOR)
    key_with_rights = game.position_key(0)  # board_states[0] keeps the initial snapshot
    shuffle = [((7, 7), (6, 7)), ((0, 7), (1, 7)),
               ((6, 7), (7, 7)), ((1, 7), (0, 7))]
    for from_sq, to_sq in shuffle:
        game_play(game, from_sq, to_sq)
    key_after_shuffle = game.position_key(4)  # home placement again, rights burned
    assert key_after_shuffle[0] == key_with_rights[0], \
        "identical placement expected - moved flags must be masked out of it"
    assert key_after_shuffle[2] != key_with_rights[2], \
        "burned castling rights must make the position distinct"


def test_rook_shuffle_repetition_detected():
    """In the rook shuffle the first position to genuinely occur 3 times is the
    intermediate one (both rooks lifted, rights-less) at plies 2, 6 and 10 - the
    rights-bearing start of the sequence never contributes an occurrence."""
    game = game_with_position(rooks_and_kings(), WHITE_PIECE_COLOR)
    shuffle = [((7, 7), (6, 7)), ((0, 7), (1, 7)),
               ((6, 7), (7, 7)), ((1, 7), (0, 7))]
    for ply, (from_sq, to_sq) in enumerate(shuffle * 3, start=1):
        game_play(game, from_sq, to_sq)
        detected = game.check_three_fold_repetition()
        if ply < 10:
            assert not detected, f"false repetition report after ply {ply}"
        else:
            assert detected, f"repetition not detected at ply {ply}"
            break


def test_en_passant_flag_distinguishes_positions():
    game = game_with_position(
        rooks_and_kings() + [(Pawn(BLACK_PIECE_COLOR), 3, 3)], WHITE_PIECE_COLOR)
    board = game.board_states[game.move_count]
    key_without_flag = game.position_key(game.move_count)
    board.squares[3][3].piece.en_passant = True
    board.dump_to_squares_fast_method()
    key_with_flag = game.position_key(game.move_count)
    assert key_with_flag != key_without_flag, \
        "an en-passant-capturable pawn must make the position distinct"


def test_no_false_positive_in_normal_opening():
    game = Game()
    for from_sq, to_sq in [((6, 4), (4, 4)), ((1, 4), (3, 4)),
                           ((7, 6), (5, 5)), ((0, 1), (2, 2))]:
        game_play(game, from_sq, to_sq)
        assert not game.check_three_fold_repetition(), \
            "repetition reported during a normal non-repeating opening"


if __name__ == "__main__":
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_")]
    for name, fn in tests:
        fn()
        print(f"OK: {name}")
    print(f"All {len(tests)} three fold repetition tests passed.")
