from const import *
from game import Game
from move import Move
from piece import Piece
from typing import Tuple
import copy

import pygame
import time

class AI:
    # max_depth semantics: best_move() plays ply 1 itself and calls minimax() with depth=1;
    # recursion stops when depth > max_depth, so max_depth = N means the AI analyzes
    # N+1 plies in total (e.g. max_depth = 2 predicts 3 piece moves ahead)
    # pruning=False disables the alpha-beta cutoff (plain minimax), kept only so tests
    # can assert that pruning never changes the root score
    def __init__(self, max_depth = AI_MAX_DEPTH, pruning = True):
        self.max_depth = max_depth
        self.pruning = pruning
        self.moves_analyzed = 0
        self.best_score = None  # root score of the last best_move() search
        self.visual_mode = False

    # all legal moves of 'color' as (piece, move) pairs, captures first (highest
    # captured-piece value first) - good ordering is what makes alpha-beta cut
    def collect_ordered_moves(self, board, color: int) -> list:
        legal_moves = []
        for row in range(ROWS):
            for col in range(COLS):
                if board.squares[row][col].has_team_piece(color):
                    current_piece = board.squares[row][col].piece
                    current_piece.clear_moves()
                    board.calc_moves(current_piece, row, col)
                    for move in current_piece.moves:
                        legal_moves.append((current_piece, move))
        # piece.value is signed by color, so order by absolute value; non-captures
        # (empty destination) get key 0 and stay behind all captures
        legal_moves.sort(key = lambda pair:
                         -abs(pair[1].final.piece.value) if pair[1].final.piece else 0.0)
        return legal_moves

    # returns score of the current node in a minimax tree; [alpha, beta] is the
    # window of scores still relevant to the ancestors - branches proven outside
    # it are cut off (pure optimization, never changes the root result)
    def minimax(self, game_state: Game, screen, depth: int = 0, is_maximizing: bool = True,
                alpha: float = float('-inf'), beta: float = float('inf')) -> float:

        if self.visual_mode:
            game_state.show_bg(screen)
            game_state.show_last_move(screen)
            game_state.show_pieces_not_moved_yet(screen)                        
            game_state.show_moves(screen)
            game_state.show_pieces(screen)
            game_state.show_AI_moves_analyzed(screen, self.moves_analyzed)
            pygame.display.update()
            #time.sleep(1)

        board = game_state.board_states[game_state.move_count]  # creating board variable for better readibility!
        current_player = game_state.current_player

        # score of the side to move being checkmated at this node; finite and depth-adjusted
        # so that faster mates are preferred and the scores are never masked by the
        # best_score initial values (is_maximizing == True means white is to move)
        mated_score = float(-(MATE_SCORE - depth)) if is_maximizing else float(MATE_SCORE - depth)

        # draws detectable from counters alone (cheap, no move generation needed)
        if game_state.check_fifty_move_rule() or board.check_insufficient_mating_material():
            return 0

        # FIXED BUG: the module constant AI_MAX_DEPTH was read here instead of
        # self.max_depth, so the AI(max_depth=...) constructor argument was ignored
        if depth > self.max_depth:  # if max depth is reached stop recurrence
            # OPTIMIZATION (no per-node player_has_no_valid_moves scan): at the horizon
            # only look for a checkmate, and only when the king is actually in check
            if board.is_king_checked(current_player) and not board.has_any_valid_move(current_player):
                return mated_score
            return board.calculate_piece_score()

        # generate all legal moves of the side to move; an empty list means the game is
        # over at this node - checkmate if the king is in check, stalemate otherwise.
        # OPTIMIZATION: this replaces the player_has_no_valid_moves() scan formerly done
        # inside Board.move() for every single node of the search tree.
        legal_moves = self.collect_ordered_moves(board, current_player)

        if not legal_moves:
            if board.is_king_checked(current_player):
                return mated_score
            return 0  # stalemate

        best_score = float('-inf') if is_maximizing else float('inf')

        for current_piece, move in legal_moves:
            if depth == self.max_depth:
                self.moves_analyzed += 1

            board.move(current_piece, move, test_check = False, clear_moves = False, ai_minimax=True)
            game_state.prepare_board_state_for_next_move()

            # - recursively invoke minimax function for the move until 'max_depth' depth is reached
            score = self.minimax(game_state, screen, depth + 1, not is_maximizing, alpha, beta)

            # - revert to original player and board position
            game_state.undo_last_move()

            # - calculate current best score based on score received from minimax
            # and narrow the alpha-beta window with it
            if is_maximizing:
                best_score = max(best_score, score)
                alpha = max(alpha, best_score)
            else:
                best_score = min(best_score, score)
                beta = min(beta, best_score)

            if self.moves_analyzed % 1000 == 0:
                print(f"Analyzed {self.moves_analyzed} moves...")

            # alpha-beta cutoff: the opponent already has a better option earlier
            # in the tree, so no ancestor will ever let the game reach this node -
            # the remaining sibling moves cannot influence the root decision
            if self.pruning and beta <= alpha:
                break

        return best_score

    # function for debugging
    def show_all_possible_moves(self, game_state: Game) -> None:
        board = game_state.board_states[game_state.move_count]
        for row in range(ROWS):
            for col in range(COLS):
                if board.squares[row][col].has_team_piece(game_state.current_player):
                    current_piece = board.squares[row][col].piece
                    for i, move in enumerate(current_piece.moves):
                        comment = f"Move no {i} -> "                        
                        move.show(current_piece.name, comment)


    # Choosing best move for the AI
    # returns Piece and Move of the best move found
    # returns None, None Tuple if move not found
    # we as black are minimizing the score    
    def best_move(self, game_state: Game, screen) -> tuple[Piece, Move]:
        best_score: float
        best_piece: Piece = None
        best_move: Move = None
        self.moves_analyzed = 0

        # initialize best_score with the worst possible score for player
        if game_state.current_player == WHITE_PIECE_COLOR:
            best_score = -1000
        else:
            best_score = 1000

        board = game_state.board_states[game_state.move_count]
        maximizing = game_state.current_player == WHITE_PIECE_COLOR

        # test each valid move in current position, best captures first so that the
        # alpha-beta window narrows as early as possible
        for current_piece, move in self.collect_ordered_moves(board, game_state.current_player):
            moves_analyzed_so_far = self.moves_analyzed

            board.move(current_piece, move, test_check = False, clear_moves = False, ai_minimax=True)
            game_state.prepare_board_state_for_next_move()

            # - recursively invoke minimax function for the move until 'max_depth' depth is reached
            # invoke minimax method at depth=1 because best_move() method covers moves at depth=0.
            # best_score is the root alpha (white) / beta (black): a reply line proven
            # worse than the best move found so far is cut off, which can only affect
            # scores of moves that would not be chosen anyway
            if maximizing:
                score = self.minimax(game_state, screen, 1, is_maximizing = False,
                                     alpha = best_score, beta = float('inf'))
            else:
                score = self.minimax(game_state, screen, 1, is_maximizing = True,
                                     alpha = float('-inf'), beta = best_score)

            # - revert to original player and board position
            game_state.undo_last_move()
            comment = f"Calculated score {score} for move based on {self.moves_analyzed-moves_analyzed_so_far} moves."
            move.show(current_piece.name, comment)

            # if found score is better for the root player, set it as best_score
            if (score > best_score) if maximizing else (score < best_score):
                best_score = score
                best_move = move
                best_piece = current_piece
                comment = f"Found new best move: {best_score}"
                best_move.show(best_piece.name, comment)

        self.best_score = best_score

        if best_move is not None:
            board.move(best_piece, best_move)
            print(f"AI found a move after analyzing {self.moves_analyzed} moves (depth = {self.max_depth}). It's score is {best_score}.")
            return best_piece, best_move
        else: # this means AI didn't find any non-losing move so it should resing 
            return None, None
