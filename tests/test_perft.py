"""Perft (performance test) harness - IMPROVEMENTS.md section 4.

perft(depth) counts all leaf nodes of the legal-move tree. The counts are
compared against independently verified reference values (Stockfish / the
Chess Programming Wiki), so any regression in move generation or in the
make/undo path shows up as a wrong number. The tree is driven through the very
same move() / prepare_board_state_for_next_move() / undo_last_move() path the
minimax AI uses.

Reference values:
- start position: 20 / 400 / 8,902 / 197,281
- "Kiwipete" (CPW position 2, castling/pin heavy): 48 / 2,039 / 97,862
- CPW position 3 (en passant / pin heavy): 14 / 191 / 2,812

NOTE: the engine promotes to a Queen only (no underpromotion), so reference
values are only valid for depths that contain no promotions - true for all
tested depths of these positions.

The deepest (slow) counts are skipped by default. Enable them with:
    set CHESS_PERFT_DEEP=1        (pytest and standalone)
or run standalone with the --deep flag:
    python .\tests\test_perft.py --deep

Run standalone:  python .\tests\test_perft.py
Or with pytest:  pytest tests
"""
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
os.chdir(REPO_ROOT)  # asset paths inside src are relative to the repo root

from const import WHITE_PIECE_COLOR, BLACK_PIECE_COLOR, ROWS, COLS
from game import Game
from piece import Bishop, King, Knight, Pawn, Queen, Rook

DEEP = os.environ.get("CHESS_PERFT_DEEP") == "1" or "--deep" in sys.argv

PAWN_HOME_ROW = {WHITE_PIECE_COLOR: 6, BLACK_PIECE_COLOR: 1}


def game_with_position(pieces, current_player):
    """Build a Game whose current position (at move_count 1, so that
    undo_last_move() works as in a real game) contains exactly 'pieces'.
    Pawns placed outside their home row are marked as moved (no double push)."""
    game = Game()
    board = game.board_states[0]
    for row in range(ROWS):
        for col in range(COLS):
            board.squares[row][col].piece = None
    for piece, row, col in pieces:
        if isinstance(piece, Pawn) and row != PAWN_HOME_ROW[piece.color]:
            piece.moved = True
        board.squares[row][col].piece = piece
    board.dump_to_squares_fast_method()
    board.current_state.player_color = current_player

    game.board_states[1].copy_board_content(board)
    game.move_count = 1
    game.board_states[1].current_state.move_count = 1
    game.current_player = current_player
    game.first_move_made = True
    return game


def game_from_start():
    return game_with_position(start_position_pieces(), WHITE_PIECE_COLOR)


def start_position_pieces():
    pieces = []
    for col in range(COLS):
        pieces.append((Pawn(BLACK_PIECE_COLOR), 1, col))
        pieces.append((Pawn(WHITE_PIECE_COLOR), 6, col))
    for color, row in ((BLACK_PIECE_COLOR, 0), (WHITE_PIECE_COLOR, 7)):
        for col, piece_class in enumerate(
                [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]):
            pieces.append((piece_class(color), row, col))
    return pieces


def kiwipete_pieces():
    # r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq -
    W, B = WHITE_PIECE_COLOR, BLACK_PIECE_COLOR
    return [
        (Rook(B), 0, 0), (King(B), 0, 4), (Rook(B), 0, 7),
        (Pawn(B), 1, 0), (Pawn(B), 1, 2), (Pawn(B), 1, 3), (Queen(B), 1, 4),
        (Pawn(B), 1, 5), (Bishop(B), 1, 6),
        (Bishop(B), 2, 0), (Knight(B), 2, 1), (Pawn(B), 2, 4), (Knight(B), 2, 5), (Pawn(B), 2, 6),
        (Pawn(W), 3, 3), (Knight(W), 3, 4),
        (Pawn(B), 4, 1), (Pawn(W), 4, 4),
        (Knight(W), 5, 2), (Queen(W), 5, 5), (Pawn(B), 5, 7),
        (Pawn(W), 6, 0), (Pawn(W), 6, 1), (Pawn(W), 6, 2), (Bishop(W), 6, 3),
        (Bishop(W), 6, 4), (Pawn(W), 6, 5), (Pawn(W), 6, 6), (Pawn(W), 6, 7),
        (Rook(W), 7, 0), (King(W), 7, 4), (Rook(W), 7, 7),
    ]


def cpw_position3_pieces():
    # 8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - -
    W, B = WHITE_PIECE_COLOR, BLACK_PIECE_COLOR
    return [
        (Pawn(B), 1, 2),
        (Pawn(B), 2, 3),
        (King(W), 3, 0), (Pawn(W), 3, 1), (Rook(B), 3, 7),
        (Rook(W), 4, 1), (Pawn(B), 4, 5), (King(B), 4, 7),
        (Pawn(W), 6, 4), (Pawn(W), 6, 6),
    ]


def perft(game, depth):
    """Count leaf nodes of the legal-move tree, driving the board through the
    same make/prepare/undo path AI.minimax() uses."""
    if depth == 0:
        return 1
    board = game.board_states[game.move_count]
    nodes = 0
    for row in range(ROWS):
        for col in range(COLS):
            if board.squares[row][col].has_team_piece(game.current_player):
                piece = board.squares[row][col].piece
                piece.clear_moves()
                board.calc_moves(piece, row, col)
                # snapshot: deeper recursion recalculates moves of the same
                # (shared) Piece objects
                for move in list(piece.moves):
                    board.move(piece, move, clear_moves=False, ai_minimax=True)
                    game.prepare_board_state_for_next_move()
                    nodes += perft(game, depth - 1)
                    game.undo_last_move()
    return nodes


def run_perft(name, pieces, current_player, expected_by_depth, deep_depths=()):
    for depth, expected in expected_by_depth.items():
        if depth in deep_depths and not DEEP:
            print(f"SKIP: {name} perft({depth}) (enable with CHESS_PERFT_DEEP=1 or --deep)")
            continue
        game = game_with_position(pieces_copy(pieces), current_player)
        started = time.perf_counter()
        nodes = perft(game, depth)
        elapsed = time.perf_counter() - started
        assert nodes == expected, \
            f"{name} perft({depth}) = {nodes}, expected {expected}"
        print(f"OK: {name} perft({depth}) = {nodes} in {elapsed:.2f}s")


def pieces_copy(pieces):
    # fresh Piece objects for every run - Piece state (moved/en_passant) is mutable
    return [(piece.__class__(piece.color), row, col) for piece, row, col in pieces]


def test_perft_start_position():
    run_perft("startpos", start_position_pieces(), WHITE_PIECE_COLOR,
              {1: 20, 2: 400, 3: 8902, 4: 197281}, deep_depths=(4,))


def test_perft_kiwipete():
    run_perft("kiwipete", kiwipete_pieces(), WHITE_PIECE_COLOR,
              {1: 48, 2: 2039, 3: 97862}, deep_depths=(3,))


def test_perft_cpw_position3():
    run_perft("cpw-pos3", cpw_position3_pieces(), WHITE_PIECE_COLOR,
              {1: 14, 2: 191, 3: 2812})


if __name__ == "__main__":
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_")]
    for name, fn in tests:
        fn()
    print(f"All perft tests passed.")
