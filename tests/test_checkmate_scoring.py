"""Regression tests for checkmate detection and scoring (IMPROVEMENTS.md item 1.6).

Game.check_win(color) ignored its color argument: it returned True for BOTH colors
whenever the last move delivered mate. In minimax the BLACK branch was tested first,
so every checkmate in the search tree was scored as a black win regardless of who
was mated - a white AI avoided delivering mate and black walked into being mated.

Now check_win() attributes the win to the color of the piece that made the mating
move (current_state.piece), which is valid both before and after
prepare_board_state_for_next_move(), and minimax scores mates finitely and
depth-adjusted (+/-(MATE_SCORE - depth)) so faster mates are preferred and the
scores are never masked by the best_score initial values.

Run standalone:  python .\tests\test_checkmate_scoring.py
Or with pytest:  pytest tests
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
os.chdir(REPO_ROOT)  # asset paths inside src are relative to the repo root

from const import WHITE_PIECE_COLOR, BLACK_PIECE_COLOR, ROWS, COLS
from game import Game
from minimax import AI
from piece import King, Rook


def play(board, from_sq, to_sq):
    # ai_minimax=False: real-move semantics, so the opponent_king_checked /
    # opponent_has_no_valid_moves flags read by check_win() are computed
    # (during the AI search they intentionally are not - see IMPROVEMENTS.md 2.2)
    piece = board.squares[from_sq[0]][from_sq[1]].piece
    piece.clear_moves()
    board.calc_moves(piece, from_sq[0], from_sq[1])
    for move in piece.moves:
        if (move.final.row, move.final.col) == to_sq:
            board.move(piece, move, clear_moves=False, ai_minimax=False)
            return piece
    raise AssertionError(f"move {from_sq} -> {to_sq} was not generated")


def game_with_position(pieces, current_player):
    """Build a Game whose current position (at move_count 1, as in a real game
    after the first move) contains exactly 'pieces' with 'current_player' to move."""
    game = Game()
    board = game.board_states[0]
    for row in range(ROWS):
        for col in range(COLS):
            board.squares[row][col].piece = None
    for piece, row, col in pieces:
        board.squares[row][col].piece = piece
    board.dump_to_squares_fast_method()
    board.current_state.player_color = current_player

    game.board_states[1].copy_board_content(board)
    game.move_count = 1
    game.board_states[1].current_state.move_count = 1
    game.current_player = current_player
    game.first_move_made = True
    return game


def test_check_win_reports_only_the_mating_color():
    # Fool's mate: 1. f3 e5  2. g4 Qh4#
    game = Game()
    for from_sq, to_sq in [((6, 5), (5, 5)), ((1, 4), (3, 4)), ((6, 6), (4, 6))]:
        play(game.board_states[game.move_count], from_sq, to_sq)
        game.prepare_board_state_for_next_move()
    play(game.board_states[game.move_count], (0, 3), (4, 7))  # Qh4#

    # before prepare_board_state_for_next_move() - the GUI call sites
    assert game.check_win(BLACK_PIECE_COLOR), "black delivered the mate"
    assert not game.check_win(WHITE_PIECE_COLOR), "white must not be reported as the winner"

    # after prepare - the minimax node context
    game.prepare_board_state_for_next_move()
    assert game.check_win(BLACK_PIECE_COLOR)
    assert not game.check_win(WHITE_PIECE_COLOR)
    assert not game.check_draw()


def test_white_ai_delivers_mate_in_one():
    # ladder mate: rook a7 cuts rank 7, Rb5-b8# mates the black king on the back rank
    game = game_with_position([
        (King(WHITE_PIECE_COLOR), 7, 7),
        (Rook(WHITE_PIECE_COLOR), 1, 0),
        (Rook(WHITE_PIECE_COLOR), 3, 1),
        (King(BLACK_PIECE_COLOR), 0, 4),
    ], WHITE_PIECE_COLOR)

    best_piece, best_move = AI().best_move(game, None)
    assert best_move is not None, "AI must not resign in a winning position"
    move_played = ((best_move.initial.row, best_move.initial.col),
                   (best_move.final.row, best_move.final.col))
    assert move_played == ((3, 1), (0, 1)), \
        f"white AI must play the mate in one (Rb8#), played {move_played}"


def test_black_ai_delivers_mate_in_one():
    # mirrored ladder mate: rook a2 cuts rank 2, black mates with Rb4-b1#
    game = game_with_position([
        (King(BLACK_PIECE_COLOR), 0, 7),
        (Rook(BLACK_PIECE_COLOR), 6, 0),
        (Rook(BLACK_PIECE_COLOR), 4, 1),
        (King(WHITE_PIECE_COLOR), 7, 4),
    ], BLACK_PIECE_COLOR)

    best_piece, best_move = AI().best_move(game, None)
    assert best_move is not None, "AI must not resign in a winning position"
    move_played = ((best_move.initial.row, best_move.initial.col),
                   (best_move.final.row, best_move.final.col))
    assert move_played == ((4, 1), (7, 1)), \
        f"black AI must play the mate in one (Rb1#), played {move_played}"


if __name__ == "__main__":
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_")]
    for name, fn in tests:
        fn()
        print(f"OK: {name}")
    print(f"All {len(tests)} checkmate-scoring regression tests passed.")
