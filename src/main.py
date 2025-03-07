# Original code by AlejoG10 avaiable at GitHub https://github.com/AlejoG10/python-chess-ai-yt
# Bug fixes/improvements/new features by KK-lerning-github

import pygame
import sys
from const import *
from game import Game
from square import Square
from move import Move
import copy

class Main:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode( (WIDTH, HEIGHT) )
        pygame.display.set_caption("Chess AI")
        self.game = Game()
                
    def mainloop(self):
        game = self.game
        screen = self.screen
        board = self.game.board
        dragger = self.game.dragger
        show_popup_screen = False # controls whether to display end of game screen
        end_of_game_message = ""
        while True:
            # show methods
            game.show_bg(screen)
            game.show_last_move(screen)
            game.show_moves(screen)
            game.show_pieces(screen)
            game.show_hover(screen)

            # NEW LINES: if game ended show a popup window on screen
            if show_popup_screen:
                game.draw_popup(screen, end_of_game_message)


            if dragger.dragging:
                dragger.update_blit(screen)
                
            for event in pygame.event.get():

                # click event
                if event.type == pygame.MOUSEBUTTONDOWN:
                    board.player_under_check = False # always reset player_under_check variable on next turn
                    # Operation on the board
                    dragger.update_mouse(event.pos)
                    clicked_row = dragger.mouseY // SQSIZE
                    clicked_col = dragger.mouseX // SQSIZE
                    # if clicked square has a piece and the piece is of the color of current player turn 
                    if board.squares[clicked_row][clicked_col].has_team_piece(game.current_player):
                        piece = board.squares[clicked_row][clicked_col].piece
                        board.calc_moves(piece, clicked_row, clicked_col, move_the_piece=True)
                        #piece.show_moves_debug("normal")
                        dragger.save_initial(event.pos)
                        dragger.drag_piece(piece)
                        # show methods
                        game.show_bg(screen)
                        game.show_last_move(screen)
                        game.show_moves(screen)
                        game.show_pieces(screen)

                # mouse motion event
                elif event.type == pygame.MOUSEMOTION:
                    motion_row = event.pos[1] // SQSIZE
                    motion_col = event.pos[0] // SQSIZE
                    game.set_hover(motion_row, motion_col)
                    
                    if dragger.dragging:
                        dragger.update_mouse(event.pos)
                        #show methods
                        game.show_bg(screen)
                        game.show_last_move(screen)
                        game.show_moves(screen)
                        game.show_pieces(screen)
                        game.show_hover(screen)
                        
                        dragger.update_blit(screen)

                # click release event
                elif event.type == pygame.MOUSEBUTTONUP:
                    if dragger.dragging:
                        dragger.update_mouse(event.pos)
                        released_row = dragger.mouseY // SQSIZE
                        released_col = dragger.mouseX // SQSIZE
                        
                        # create possible move
                        initial = Square(dragger.initial_row, dragger.initial_col)
                        final = Square(released_row, released_col)
                        move = Move(initial, final)
                        
                        if board.valid_move(dragger.piece, move):
                            # normal capture
                            captured = board.squares[released_row][released_col].has_piece()
                            
                            # NEW CODE! Update counters after piece capture
                            if captured:
                                board.update_pieces_count(game.current_player) # update piece counter after capture
                                board.last_move_when_piece_captured = board.move_count # set this variable to 'move_count' after capture
                                
                            board.move(dragger.piece, move)
                            board.moves_history.append((dragger.piece, move)) # NEW CODE: add last move to the history of game moves
                            board.set_true_en_passant(dragger.piece) # make sure en passant state for pawns lasts only for 1 turn
                            game.play_sound(captured)
                            #show methods
                            game.show_bg(screen)
                            game.show_last_move(screen)
                            game.show_pieces(screen)
                            enemy_color = 'black' if game.current_player == 'white' else 'white'
                            
                            # NEW CODE: is king checked? 
                            if board.is_king_checked(enemy_color):
                                board.player_under_check = True

                            # NEW CODE: evaluating three fold repetition 
                            game.add_board_to_list_of_previous_positions(copy.deepcopy(board)) # add copy of current board, not the board itself
                            if board.move_count >= 5:
                                game.check_three_fold_repetition()
                            
                            # DEBUG INFO
                            # board.show_pieces_count()
                            board.show_move_counters()
                            board.show_moves_history()
                            
                            # NEW CODE: increase move counter after black moves
                            if game.current_player == 'black':
                                board.move_count += 1
                                #print(f"Game is advancing to move no {board.move_count}.")
                                
                            # this line limits the player move to only one move!
                            game.current_player = 'white' if game.current_player == 'black' else 'black'
                        else:
                            dragger.piece.clear_moves()
                    dragger.undrag_piece()


                    
                    # NEW CODE: After the move was made check if the position is draw or checkmate or stalemate.
                    if game.three_fold_repetition_detected == True:
                        end_of_game_message = f"Draw. Reason: three fold repetition of the position. "
                        end_of_game_message += "Press 'r' to restart or close the app window to quit."
                        show_popup_screen = True
                    elif board.check_insufficient_mating_material():
                        end_of_game_message = f"Draw. Reason: insufficient material. "
                        end_of_game_message += "Press 'r' to restart or close the app window to quit."
                        show_popup_screen = True
                    elif board.check_fifty_move_rule():
                        end_of_game_message = f"Draw. Reason: 50 moves without pawn move and capturing a piece. "
                        end_of_game_message += "Press 'r' to restart or close the app window to quit."
                        show_popup_screen = True
                    elif board.player_has_no_valid_moves(game.current_player):
                        if board.player_under_check:
                            #print(f"Player {game.current_player} is checkmated!")
                            end_of_game_message = f"Player {game.current_player} is checkmated! "
                            
                        else:
                            #print(f"Player {game.current_player} is under stalemate!")
                            end_of_game_message = f"Draw. Player {game.current_player} is under stalemate! "
                            
                        end_of_game_message += "Press 'r' to restart or close the app window to quit."
                        show_popup_screen = True


                elif event.type == pygame.KEYDOWN:
                    # changing themes
                    if event.key == pygame.K_t: # on 't' key pressed
                        game.change_theme()

                    # changing themes
                    if event.key == pygame.K_r: # on 'r' key pressed
                        game.reset()
                        show_popup_screen = False
                        # we need to reset values of game, board and dragger as well as they were created based on previous game object
                        game = self.game
                        board = self.game.board
                        dragger = self.game.dragger
                        
                elif event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            pygame.display.update()


main = Main()
main.mainloop()
