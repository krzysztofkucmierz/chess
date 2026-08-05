"""Alpha-beta equivalence test - IMPROVEMENTS.md sections 2.1 and 4.

Pruning is a pure optimization: it must never change the move chosen at the
root or its score, only the number of nodes visited. Each test runs the same
search twice - AI(pruning=False) (plain minimax) vs AI(pruning=True) - from an
identical position and asserts identical root score and chosen move, and that
pruning did not analyze more moves than the plain search.

The slow depth-2 middlegame comparison (plain minimax alone takes several
seconds) is skipped by default. Enable it with:
    set CHESS_AB_DEEP=1
or run standalone with the --deep flag:
    python .\tests\test_alpha_beta.py --deep

Run standalone:  python .\tests\test_alpha_beta.py
Or with pytest:  pytest tests
"""
import contextlib
import io
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
os.chdir(REPO_ROOT)  # asset paths inside src are relative to the repo root

from game import Game
from minimax import AI

DEEP = os.environ.get("CHESS_AB_DEEP") == "1" or "--deep" in sys.argv

# Giuoco Piano: 1.e4 e5 2.Nf3 Nc6 3.Bc4 Bc5 - same position as benchmark_ai.py
MIDDLEGAME_MOVES = [
    ((6, 4), (4, 4)),  # e4
    ((1, 4), (3, 4)),  # e5
    ((7, 6), (5, 5)),  # Nf3
    ((0, 1), (2, 2)),  # Nc6
    ((7, 5), (4, 2)),  # Bc4
    ((0, 5), (3, 2)),  # Bc5
]


def play(game, from_sq, to_sq):
    board = game.board_states[game.move_count]
    piece = board.squares[from_sq[0]][from_sq[1]].piece
    piece.clear_moves()
    board.calc_moves(piece, from_sq[0], from_sq[1])
    for move in piece.moves:
        if (move.final.row, move.final.col) == to_sq:
            board.move(piece, move, clear_moves=False, ai_minimax=True)
            game.prepare_board_state_for_next_move()
            return
    raise AssertionError(f"move {from_sq} -> {to_sq} was not generated")


def game_at_start():
    """Start position with one played move pair so that the search runs at
    move_count >= 1 (undo_last_move() is a no-op at move_count <= 1)."""
    game = Game()
    play(game, (6, 4), (4, 4))  # e4
    play(game, (1, 4), (3, 4))  # e5
    return game


def game_at_middlegame():
    game = Game()
    for from_sq, to_sq in MIDDLEGAME_MOVES:
        play(game, from_sq, to_sq)
    return game


def search(game_factory, depth, pruning):
    game = game_factory()
    ai = AI(max_depth=depth, pruning=pruning)
    started = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        piece, move = ai.best_move(game, None)
    elapsed = time.perf_counter() - started
    assert move is not None, "search unexpectedly found no move"
    chosen = (piece.name, move.initial.row, move.initial.col,
              move.final.row, move.final.col)
    return ai.best_score, chosen, ai.moves_analyzed, elapsed


def assert_equivalent(name, game_factory, depth):
    plain_score, plain_move, plain_nodes, plain_time = \
        search(game_factory, depth, pruning=False)
    ab_score, ab_move, ab_nodes, ab_time = \
        search(game_factory, depth, pruning=True)

    assert ab_score == plain_score, \
        (f"{name} depth {depth}: alpha-beta root score {ab_score} "
         f"!= plain minimax score {plain_score}")
    assert ab_move == plain_move, \
        (f"{name} depth {depth}: alpha-beta chose {ab_move}, "
         f"plain minimax chose {plain_move}")
    assert ab_nodes <= plain_nodes, \
        (f"{name} depth {depth}: alpha-beta analyzed {ab_nodes} moves, "
         f"more than plain minimax ({plain_nodes})")
    print(f"OK: {name} depth {depth}: score {plain_score}, move {plain_move}, "
          f"moves analyzed {plain_nodes} -> {ab_nodes} "
          f"({plain_time:.2f}s -> {ab_time:.2f}s)")


def test_alpha_beta_equivalence_startpos_depth1():
    assert_equivalent("startpos", game_at_start, 1)


def test_alpha_beta_equivalence_middlegame_depth1():
    assert_equivalent("middlegame", game_at_middlegame, 1)


def test_alpha_beta_equivalence_startpos_depth2():
    assert_equivalent("startpos", game_at_start, 2)


def test_alpha_beta_equivalence_middlegame_depth2():
    if not DEEP:
        print("SKIP: middlegame depth 2 (enable with CHESS_AB_DEEP=1 or --deep)")
        return
    assert_equivalent("middlegame", game_at_middlegame, 2)


if __name__ == "__main__":
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_")]
    for name, fn in tests:
        fn()
    print("All alpha-beta equivalence tests passed.")
