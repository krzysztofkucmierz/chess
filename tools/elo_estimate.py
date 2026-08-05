r"""Automated Elo estimation - IMPROVEMENTS.md section 4.

Plays rated games against Stockfish limited to calibrated strength levels
(UCI_LimitStrength / UCI_Elo, floor ~1320) through the python-chess library,
then computes a maximum-likelihood performance rating over all games combined.
Appends every run to tools/elo_history.csv so strength progress can be tracked
across engine improvements.

A python-chess chess.Board mirrors every game and is the source of truth for
legality and game termination (the app's own draw detection has known gaps).
The app's board is driven through the same move()/prepare/undo path the GUI
and the tests use; positions are compared after every ply, so any divergence
between the two implementations aborts the game loudly instead of corrupting
the rating.

Requirements:
    pip install python-chess
    Stockfish binary: --stockfish PATH, or STOCKFISH_PATH env var, or
    'stockfish' on PATH (e.g. winget install Stockfish.Stockfish)

Usage:
    python .\tools\elo_estimate.py                  # 100 games, depth 2, ~1 h
    python .\tools\elo_estimate.py --quick          # 20 games, rough estimate
    python .\tools\elo_estimate.py --games 40 --depth 3 --levels 1320 1500
    python .\tools\elo_estimate.py --selftest       # verify the Elo math only
"""
import argparse
import contextlib
import io
import math
import os
import random
import shutil
import subprocess
import sys
import time
from datetime import date

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
os.chdir(REPO_ROOT)  # asset paths inside src are relative to the repo root

try:
    import chess
    import chess.engine
except ImportError:
    sys.exit("python-chess is required:  pip install python-chess")

import board as board_module
from game import Game
from minimax import AI
from piece import Pawn

# headless run - replace the sound played inside Board.move() with a no-op
class _SilentSound:
    def __init__(self, *args, **kwargs):
        pass

    def play(self):
        pass

board_module.Sound = _SilentSound

PIECE_LETTER = {"pawn": "p", "knight": "n", "bishop": "b",
                "rook": "r", "queen": "q", "king": "k"}

# short, quiet openings (UCI, 4 plies) to diversify games - the app is deterministic
OPENINGS = [
    ["e2e4", "e7e5", "g1f3", "b8c6"],   # Open game
    ["e2e4", "c7c5", "g1f3", "d7d6"],   # Sicilian
    ["d2d4", "d7d5", "c2c4", "e7e6"],   # Queen's Gambit Declined
    ["d2d4", "g8f6", "c2c4", "e7e6"],   # Indian defence
    ["e2e4", "e7e6", "d2d4", "d7d5"],   # French
    ["e2e4", "c7c6", "d2d4", "d7d5"],   # Caro-Kann
    ["d2d4", "d7d5", "g1f3", "g8f6"],   # Queen's pawn game
    ["c2c4", "e7e5", "b1c3", "g8f6"],   # English
    ["g1f3", "d7d5", "g2g3", "c7c5"],   # Reti
    ["e2e4", "e7e5", "f1c4", "f8c5"],   # Italian bishops
]

MAX_PLIES = 240  # the app preallocates 300 board states - stay well below
ADJUDICATION_CP = 500  # centipawn threshold when a capped game is adjudicated


class GameDiscarded(Exception):
    """Game cannot be finished/represented faithfully - excluded from rating."""


# ---------------------------------------------------------------------------
# adapter: drive the app's engine the way the GUI and the tests do
# ---------------------------------------------------------------------------

def uci_to_squares(uci):
    """'e2e4' -> ((row, col), (row, col)) in the app's coordinates."""
    from_sq = (8 - int(uci[1]), ord(uci[0]) - ord("a"))
    to_sq = (8 - int(uci[3]), ord(uci[2]) - ord("a"))
    return from_sq, to_sq


class AppEngine:
    def __init__(self, depth):
        self.game = Game()
        self.ai = AI(max_depth=depth)

    def push_uci(self, uci):
        """Apply an external (opening or Stockfish) move to the app's board."""
        if len(uci) == 5 and uci[4] != "q":
            raise GameDiscarded(f"underpromotion {uci} not representable (app auto-queens)")
        (from_row, from_col), to_sq = uci_to_squares(uci)
        board = self.game.board_states[self.game.move_count]
        piece = board.squares[from_row][from_col].piece
        if piece is None:
            raise GameDiscarded(f"no piece on origin square of {uci} (desync)")
        piece.clear_moves()
        board.calc_moves(piece, from_row, from_col)
        for move in piece.moves:
            if (move.final.row, move.final.col) == to_sq:
                board.move(piece, move, clear_moves=False, ai_minimax=True)
                self.game.prepare_board_state_for_next_move()
                return
        raise GameDiscarded(f"app does not generate the legal move {uci} (movegen bug)")

    def play_ai_move(self):
        """Ask the app's AI for a move; returns its UCI string or None (resign)."""
        with contextlib.redirect_stdout(io.StringIO()):
            piece, move = self.ai.best_move(self.game, None)
        if move is None:
            return None
        self.game.prepare_board_state_for_next_move()
        uci = ("abcdefgh"[move.initial.col] + str(8 - move.initial.row)
               + "abcdefgh"[move.final.col] + str(8 - move.final.row))
        if isinstance(piece, Pawn) and move.final.row in (0, 7):
            uci += "q"  # the app auto-queens
        return uci

    def board_fen(self):
        """Piece placement in FEN form, for the desync check."""
        board = self.game.board_states[self.game.move_count]
        ranks = []
        for row in range(8):
            rank, empties = "", 0
            for col in range(8):
                piece = board.squares[row][col].piece
                if piece is None:
                    empties += 1
                    continue
                if empties:
                    rank, empties = rank + str(empties), 0
                letter = PIECE_LETTER[piece.name]
                rank += letter.upper() if piece.color else letter
            if empties:
                rank += str(empties)
            ranks.append(rank)
        return "/".join(ranks)


# ---------------------------------------------------------------------------
# match loop
# ---------------------------------------------------------------------------

def adjudicate(engine, chess_board, level):
    """Full-strength eval of a capped game -> score for white in {0, 0.5, 1}."""
    engine.configure({"UCI_LimitStrength": False})
    info = engine.analyse(chess_board, chess.engine.Limit(depth=12))
    engine.configure({"UCI_LimitStrength": True, "UCI_Elo": level})
    cp = info["score"].white().score(mate_score=100000)
    if cp > ADJUDICATION_CP:
        return 1.0, "adjudicated +%d cp" % cp
    if cp < -ADJUDICATION_CP:
        return 0.0, "adjudicated %d cp" % cp
    return 0.5, "adjudicated %d cp" % cp


def play_game(engine, level, depth, movetime, opening, app_is_white):
    """Play one game; returns (score for the app in {0, 0.5, 1}, reason)."""
    app = AppEngine(depth)
    chess_board = chess.Board()
    for uci in opening:
        app.push_uci(uci)
        chess_board.push(chess.Move.from_uci(uci))

    while True:
        if chess_board.is_game_over() or chess_board.can_claim_draw():
            result = chess_board.result(claim_draw=True)
            white_score = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}[result]
            reason = chess_board.outcome(claim_draw=True).termination.name.lower()
            return (white_score if app_is_white else 1.0 - white_score), \
                   f"{result} ({reason}, {len(chess_board.move_stack)} plies)"

        if len(chess_board.move_stack) >= MAX_PLIES:
            white_score, reason = adjudicate(engine, chess_board, level)
            return (white_score if app_is_white else 1.0 - white_score), \
                   f"{reason} at ply cap {MAX_PLIES}"

        if chess_board.turn == chess.WHITE and app_is_white \
                or chess_board.turn == chess.BLACK and not app_is_white:
            uci = app.play_ai_move()
            if uci is None:
                return 0.0, "app resigned (no non-losing move)"
            move = chess.Move.from_uci(uci)
            if move not in chess_board.legal_moves:
                raise GameDiscarded(f"app played illegal move {uci} in {chess_board.fen()}")
            chess_board.push(move)
        else:
            played = engine.play(chess_board, chess.engine.Limit(time=movetime))
            app.push_uci(played.move.uci())
            chess_board.push(played.move)

        if app.board_fen() != chess_board.board_fen():
            raise GameDiscarded(
                f"board desync after {len(chess_board.move_stack)} plies:\n"
                f"  app:          {app.board_fen()}\n"
                f"  python-chess: {chess_board.board_fen()}")


# ---------------------------------------------------------------------------
# Elo math: maximum-likelihood performance rating (logistic model)
# ---------------------------------------------------------------------------

def expected_score(rating, opponent):
    return 1.0 / (1.0 + 10.0 ** ((opponent - rating) / 400.0))

def log_likelihood(rating, results):
    total = 0.0
    for opponent, score in results:
        e = min(max(expected_score(rating, opponent), 1e-12), 1.0 - 1e-12)
        total += score * math.log(e) + (1.0 - score) * math.log(1.0 - e)
    return total

def mle_elo(results, lo=200.0, hi=4200.0):
    """Rating maximizing the likelihood; None if the score saturates (0% or 100%)."""
    total = sum(score for _, score in results)
    if total == 0 or total == len(results):
        return None
    gradient = lambda r: sum(score - expected_score(r, opponent)
                             for opponent, score in results)  # decreasing in r
    for _ in range(80):
        mid = (lo + hi) / 2
        if gradient(mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2

def confidence_interval(results, best, drop=1.92):
    """95% CI: ratings where the log-likelihood falls 'drop' below the maximum."""
    peak = log_likelihood(best, results)
    def edge(lo, hi):
        for _ in range(80):
            mid = (lo + hi) / 2
            if log_likelihood(mid, results) < peak - drop:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2
    low = edge(best - 1500, best)
    def edge_high(lo, hi):
        for _ in range(80):
            mid = (lo + hi) / 2
            if log_likelihood(mid, results) < peak - drop:
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2
    high = edge_high(best, best + 1500)
    return low, high


def selftest():
    # 50% score vs a single level must reproduce that level exactly
    results = [(1400, 1.0)] * 10 + [(1400, 0.0)] * 10
    assert abs(mle_elo(results) - 1400) < 1, mle_elo(results)
    # 75% score vs 1400 -> 1400 + 400*log10(3) = ~1590.8
    results = [(1400, 1.0)] * 15 + [(1400, 0.0)] * 5
    assert abs(mle_elo(results) - 1590.8) < 1, mle_elo(results)
    # draws count as half points: all draws vs 1500 -> 1500
    results = [(1500, 0.5)] * 20
    assert abs(mle_elo(results) - 1500) < 1, mle_elo(results)
    # saturated scores have no point estimate
    assert mle_elo([(1320, 0.0)] * 10) is None
    # CI shrinks with more games and contains the point estimate
    results = [(1400, 1.0)] * 30 + [(1400, 0.0)] * 30
    low, high = confidence_interval(results, mle_elo(results))
    assert low < 1400 < high and (high - low) < 250, (low, high)
    print("selftest OK")


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------

def find_stockfish(cli_path):
    candidates = [
        cli_path,
        os.environ.get("STOCKFISH_PATH"),
        shutil.which("stockfish"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""),
                     "Microsoft", "WinGet", "Links", "stockfish.exe"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    sys.exit("Stockfish not found. Install it (winget install Stockfish.Stockfish\n"
             "or download from stockfishchess.org) and pass the binary with\n"
             "--stockfish PATH or the STOCKFISH_PATH environment variable.")


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, cwd=REPO_ROOT,
                              check=True).stdout.strip()
    except Exception:
        return "unknown"


def append_history(depth, games, per_level, elo_text):
    path = os.path.join(REPO_ROOT, "tools", "elo_history.csv")
    new_file = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as f:
        if new_file:
            f.write("date,commit,depth,games,per_level_w-d-l,estimate\n")
        levels_text = ";".join(f"{level}:{w}-{d}-{l}"
                               for level, (w, d, l) in sorted(per_level.items()))
        f.write(f"{date.today().isoformat()},{git_commit()},{depth},{games},"
                f"{levels_text},{elo_text}\n")
    print(f"result appended to {os.path.relpath(path, REPO_ROOT)}")


def main():
    parser = argparse.ArgumentParser(description="Estimate the app's Elo vs Stockfish")
    parser.add_argument("--games", type=int, default=100)
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--levels", type=int, nargs="+", default=[1320, 1400, 1500, 1700])
    parser.add_argument("--movetime", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--stockfish", default=None)
    parser.add_argument("--quick", action="store_true", help="20 games, rough estimate")
    parser.add_argument("--selftest", action="store_true", help="verify the Elo math only")
    args = parser.parse_args()

    if args.selftest:
        selftest()
        return

    games_total = 20 if args.quick else args.games
    rng = random.Random(args.seed)
    stockfish_path = find_stockfish(args.stockfish)
    engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
    try:
        elo_option = engine.options["UCI_Elo"]
        levels = []
        for level in args.levels:
            clamped = max(elo_option.min, min(elo_option.max, level))
            if clamped != level:
                print(f"note: UCI_Elo {level} clamped to {clamped} "
                      f"(engine range {elo_option.min}-{elo_option.max})")
            levels.append(clamped)

        games_per_level = max(1, games_total // len(levels))
        print(f"Rating run: {games_per_level * len(levels)} games, app depth {args.depth}, "
              f"Stockfish levels {levels}, movetime {args.movetime}s "
              f"({os.path.basename(stockfish_path)})")

        results = []            # (opponent_elo, score) per rated game
        per_level = {level: [0, 0, 0] for level in levels}  # W, D, L
        discarded = 0
        game_no = 0
        started = time.perf_counter()

        for level in levels:
            engine.configure({"UCI_LimitStrength": True, "UCI_Elo": level})
            for i in range(games_per_level):
                game_no += 1
                app_is_white = (i % 2 == 0)
                opening = OPENINGS[rng.randrange(len(OPENINGS))]
                try:
                    score, reason = play_game(engine, level, args.depth,
                                              args.movetime, opening, app_is_white)
                except GameDiscarded as exc:
                    discarded += 1
                    print(f"game {game_no}: DISCARDED - {exc}")
                    continue
                results.append((level, score))
                slot = 0 if score == 1.0 else (1 if score == 0.5 else 2)
                per_level[level][slot] += 1
                color = "white" if app_is_white else "black"
                verdict = {1.0: "WIN ", 0.5: "draw", 0.0: "loss"}[score]
                print(f"game {game_no}/{games_per_level * len(levels)} vs SF{level} "
                      f"as {color}: {verdict} {reason}")

        elapsed = time.perf_counter() - started
        print("-" * 78)
        for level in levels:
            w, d, l = per_level[level]
            n = w + d + l
            pct = 100.0 * (w + 0.5 * d) / n if n else 0.0
            print(f"vs SF{level}: +{w} ={d} -{l}  ({pct:.0f}%)")
        if discarded:
            print(f"discarded games: {discarded} (see log above; underpromotions are "
                  f"expected occasionally, desyncs and illegal moves are engine bugs)")

        best = mle_elo(results)
        if best is None:
            total = sum(score for _, score in results)
            if total == 0:
                elo_text = f"<= ~{min(levels) - 200} (scored 0 points; below Stockfish's calibrated floor)"
            else:
                elo_text = f">= ~{max(levels) + 200} (scored 100%; raise --levels)"
        else:
            low, high = confidence_interval(results, best)
            elo_text = f"{best:.0f} (95% CI {low:.0f}-{high:.0f})"
            if best < min(levels) - 400:
                elo_text += " [extrapolated below the calibrated floor - rough]"
        print(f"Estimated Elo: {elo_text}   [{len(results)} rated games in {elapsed/60:.1f} min]")
        append_history(args.depth, len(results),
                       {lvl: tuple(wdl) for lvl, wdl in per_level.items()}, elo_text)
    finally:
        engine.quit()


if __name__ == "__main__":
    main()
