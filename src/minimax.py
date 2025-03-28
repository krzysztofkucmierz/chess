from const import *
from game import Game
from move import Move
from piece import Piece
from typing import Tuple
import copy

import pygame
import time

class AI:
    def __init__(self, max_depth = AI_MAX_DEPTH):
        self.max_depth = max_depth
        self.moves_analyzed = 0
        self.visual_mode = False

    # returns score of the current node in a minimax tree
    def minimax(self, game_state: Game, screen, depth: int = 0, is_maximizing: bool = True) -> float:

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
        
        if game_state.check_win(BLACK_PIECE_COLOR):
            return float('-inf')
        elif game_state.check_win(WHITE_PIECE_COLOR):
            return float('inf')
        elif game_state.check_draw():
            return 0
        if depth > AI_MAX_DEPTH:  # if max depth is reached stop recurrence
            return board.calculate_piece_score()
       
        if is_maximizing:
            best_score = -1000

            for row in range(ROWS):
                for col in range(COLS):
                    if board.squares[row][col].has_team_piece(game_state.current_player):
                        current_piece = board.squares[row][col].piece
                        current_piece.clear_moves()
                        board.calc_moves(current_piece, row, col)
                        for move in current_piece.moves:

                            if depth == AI_MAX_DEPTH:
                                self.moves_analyzed += 1

                            board.move(current_piece, move, test_check = False, clear_moves = False, ai_minimax=True)
                            game_state.prepare_board_state_for_next_move()

                            # - recursively invoke minimax function for the move until 'max_depth' depth is reached
                            score = self.minimax(game_state, screen, depth + 1, is_maximizing = False)
                            
                            # - revert to original player and board position
                            game_state.undo_last_move()

                            # - calculate current best score based on score received from minimax
                            best_score = max(best_score, score)

                            if self.moves_analyzed % 1000 == 0:
                                print(f"Analyzed {self.moves_analyzed} moves...")

            return best_score
        
        else: # if is minimizing
            best_score = 1000

            for row in range(ROWS):
                for col in range(COLS):
                    if board.squares[row][col].has_team_piece(game_state.current_player):
                        current_piece = board.squares[row][col].piece
                        current_piece.clear_moves()
                        board.calc_moves(current_piece, row, col)
                        for move in current_piece.moves:

                            if depth == AI_MAX_DEPTH:
                                self.moves_analyzed += 1
                                
                            board.move(current_piece, move, test_check = False, clear_moves = False, ai_minimax=True)
                            game_state.prepare_board_state_for_next_move()

                            # - recursively invoke minimax function for the move until 'max_depth' depth is reached
                            score = self.minimax(game_state, screen, depth + 1, is_maximizing = True)

                            # - revert to original player and board position
                            game_state.undo_last_move()

                            # - calculate current best score based on score received from minimax
                            best_score = min(best_score, score)

                            if self.moves_analyzed % 1000 == 0:
                                print(f"Analyzed {self.moves_analyzed} moves...")

            return best_score

    # function for debugging
    def show_all_possible_moves(self, game_state: Game) -> bool:
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
    def best_move(self, game_state: Game, screen) -> Tuple[Piece, Move]:
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
        
        # test each valid move in current position            
        for row in range(ROWS):
            for col in range(COLS):

                if board.squares[row][col].has_team_piece(game_state.current_player):
                    current_piece = board.squares[row][col].piece
                    current_piece.clear_moves()
                    board.calc_moves(current_piece, row, col)
                    for move in current_piece.moves:
                        moves_analyzed_so_far = self.moves_analyzed

                        board.move(current_piece, move, test_check = False, clear_moves = False, ai_minimax=True)

                        # - recursively invoke minimax function for the move until 'max_depth' depth is reached
                        # invoke minimax method at depth=1 because best_move() method covers moves at depth=0
                        if game_state.current_player == WHITE_PIECE_COLOR:
                            game_state.prepare_board_state_for_next_move()
                            score = self.minimax(game_state, screen, 1, is_maximizing = False) 
                        else:
                            game_state.prepare_board_state_for_next_move()
                            score = self.minimax(game_state, screen, 1, is_maximizing = True)

                        game_state.undo_last_move()
                        comment = f"Calculated score {score} for move based on {self.moves_analyzed-moves_analyzed_so_far} moves."
                        move.show(current_piece.name, comment)
                                              
                        # if found score is lower, set it as best_score
                        if game_state.current_player == WHITE_PIECE_COLOR:
                            if score > best_score:
                                best_score = score
                                best_move = move
                                best_piece = current_piece
                                comment = f"Found new best move: {best_score}"
                                best_move.show(best_piece.name, comment)
                        else:
                            if score < best_score:
                                best_score = score
                                best_move = move
                                best_piece = current_piece
                                comment = f"Found new best move: {best_score}"
                                best_move.show(best_piece.name, comment)

                        # - revert to original player and board position


        if best_move is not None:
            # determine if the move was with capture and play appropriate sound
            board.set_capturing_move_flag(best_move)

            board.move(best_piece, best_move)
            print(f"AI found a move after analyzing {self.moves_analyzed} moves (depth = {self.max_depth}). It's score is {best_score}.")
            return best_piece, best_move
        else: # this means AI didn't find any non-losing move so it should resing 
            return None, None
