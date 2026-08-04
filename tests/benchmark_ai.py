"""AI timing benchmark - IMPROVEMENTS.md section 4.

Measures wall time and moves_analyzed of AI.best_move() at several depths from
the start position and from a middlegame position (Giuoco Piano). Run it before
and after every performance change to quantify the improvement.

Not a pytest test (it asserts nothing and takes a while) - run it directly:

    python .\tests\benchmark_ai.py              # depths 2 and 3
    python .\tests\benchmark_ai.py 2            # only depth 2
    python .\tests\benchmark_ai.py 2 3 4        # custom list of depths

The engine's search output (per-move scores etc.) is captured and suppressed so
only the summary table is printed; the time spent producing that output is still
included in the measurement, exactly as in the real game.
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
import minimax
from minimax import AI

# Giuoco Piano: 1.e4 e5 2.Nf3 Nc6 3.Bc4 Bc5 - a quiet middlegame-ish position
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


def sq_name(row, col):
    return "abcdefgh"[col] + str(8 - row)


def benchmark(position_name, game_factory, depth):
    # NOTE: minimax() reads the module-level AI_MAX_DEPTH instead of AI.max_depth
    # (IMPROVEMENTS.md item 2.5), so the depth is patched at module level here
    minimax.AI_MAX_DEPTH = depth
    game = game_factory()
    ai = AI(max_depth=depth)
    started = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        best_piece, best_move = ai.best_move(game, None)
    elapsed = time.perf_counter() - started
    if best_move is None:
        move_name = "resigned"
    else:
        move_name = (sq_name(best_move.initial.row, best_move.initial.col)
                     + sq_name(best_move.final.row, best_move.final.col))
    print(f"{position_name:12} depth {depth}: {elapsed:8.2f}s   "
          f"{ai.moves_analyzed:>9} moves analyzed   best: {move_name}")
    return elapsed


if __name__ == "__main__":
    depths = [int(arg) for arg in sys.argv[1:]] or [2, 3]
    print(f"AI benchmark (depths: {', '.join(map(str, depths))})")
    print("-" * 78)
    total = 0.0
    for depth in depths:
        total += benchmark("startpos", game_at_start, depth)
        total += benchmark("middlegame", game_at_middlegame, depth)
    print("-" * 78)
    print(f"total: {total:.2f}s")
