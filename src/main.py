# Original code by AlejoG10 avaiable at GitHub https://github.com/AlejoG10/python-chess-ai-yt
# Bug fixes/improvements/new features by KK-lerning-github

import pygame
import sys
from const import *
from game import Game
from square import Square
from move import Move
import copy
from minimax import *
from sound import Sound
import os

import cProfile
profiler = cProfile.Profile()

class Main:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode( (WIDTH, HEIGHT) )
        pygame.display.set_caption("Chess AI")
        self.game = Game()
        self.move_sound = Sound(os.path.join('assets/sounds/move.wav'))
        self.capture_sound = Sound(os.path.join('assets/sounds/capture.wav'))
        self.AI_engine = AI()
        
    def play_sound(self, captured=False):
        if captured:
            self.capture_sound.play()
        else:
            self.move_sound.play()
                
    def mainloop(self):
        game = self.game
        screen = self.screen
        board = self.game.board
        dragger = self.game.dragger
        show_popup_screen = False # controls whether to display end of game screen
        human_player_moved = False # set to True if human (white player) made a move, reset to False afte AI made a move

        
        while True:
            # show methods
            game.show_bg(screen)
            game.show_last_move(screen)
            #game.show_pieces_not_moved_yet(screen)             
            game.show_moves(screen)
            game.show_pieces(screen)
            game.show_hover(screen)

            # NEW LINES: if game ended show a popup window on screen
            if show_popup_screen:
                game.draw_popup(screen, game.game_message)


            if dragger.dragging:
                dragger.update_blit(screen)
                
            for event in pygame.event.get():

                # AI turn
                # if (human_player_moved and game.current_player == 'white') or board.first_move_made == False: # use this if clause to start AI as white
                if human_player_moved and game.current_player == 'black' and game.stopAI == False: # use this if statement to start human as white
                    print("Now it is AI turn...")
                    game.show_bg(screen)
                    game.show_last_move(screen)
                    #game.show_pieces_not_moved_yet(screen)
                    game.show_pieces(screen)
                    pygame.display.update()
                    
                    #profiler.enable()  # Start profiling
                    best_piece, best_move = self.AI_engine.best_move(game, screen)
                    #profiler.disable()  # Stop profiling
                    #profiler.print_stats()
                    if best_move:
                        board.first_move_made = True 
                        board.current_state.captured = board.squares[best_move.final.row][best_move.final.col].has_piece()                        
                        self.play_sound(board.current_state.captured)
                        #show methods
                        game.show_bg(screen)
                        game.show_last_move(screen)
                        game.show_pieces(screen)
                        pygame.display.update()
                        best_move.show(best_piece.name, "AI made a move! ")
                        # check if win or draw condition is on the board
                        if game.check_draw():
                            show_popup_screen = True                               
                        elif game.check_win(game.current_player):
                            show_popup_screen = True
                        else:
                            show_popup_screen = False                        
                        if show_popup_screen:
                            game.draw_popup(screen, game.game_message)
                    else:
                        game.game_message = f"You won! AI has resigned."
                        game.game_message += "Press 'r' to restart or close the app window to quit."
                        show_popup_screen = True                        
                        game.draw_popup(screen, game.game_message)

                    board.first_move_made = True # from now on current_state will be appended to previous_states list
                    
                    human_player_moved = False
                    game.current_player = 'white' if game.current_player == 'black' else 'black'


                # click event
                if event.type == pygame.MOUSEBUTTONDOWN:
                    # Operation on the board
                    dragger.update_mouse(event.pos)
                    clicked_row = dragger.mouseY // SQSIZE
                    clicked_col = dragger.mouseX // SQSIZE
                    # if clicked square has a piece and the piece is of the color of current player turn 
                    if board.squares[clicked_row][clicked_col].has_team_piece(game.current_player):
                        piece = board.squares[clicked_row][clicked_col].piece
                        board.calc_moves(piece, clicked_row, clicked_col)
                        dragger.save_initial(event.pos)
                        dragger.drag_piece(piece)
                        # show methods
                        game.show_bg(screen)
                        game.show_last_move(screen)
                        #game.show_pieces_not_moved_yet(screen)                        
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
                        #game.show_pieces_not_moved_yet(screen)                        
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
                            board.current_state.captured = board.squares[released_row][released_col].has_piece()

                            board.move(dragger.piece, move)
                            board.first_move_made = True # from now on current_state will be appended to previous_states list
                            self.play_sound(board.current_state.captured)
                            #show methods
                            game.show_bg(screen)
                            game.show_last_move(screen)
                            #game.show_pieces_not_moved_yet(screen)
                            game.show_pieces(screen)
                            pygame.display.update()
                            
                            # DEBUG INFO
                            board.show_pieces_count()
                            board.show_move_counters()
                            #board.show_moves_history()
                            print(f"Game score based on value of pieces is: {board.calculate_piece_score()}")
                            
                            # NEW CODE! check if win or draw condition is on the board
                            if game.check_draw():
                                show_popup_screen = True
                                game.stopAI = True

                            elif game.check_win(game.current_player):
                                show_popup_screen = True
                                game.stopAI = True

                            else:
                                show_popup_screen = False

                            if show_popup_screen:
                                game.draw_popup(screen, game.game_message)

                            if game.current_player == 'black':
                                board.current_state.move_count += 1
                                print(f"Game is advancing to move no {board.current_state.move_count}.")
                                
                            # Below line must be stay as the last one after the valid move. This linie limits the player move to only one move!
                            game.current_player = 'white' if game.current_player == 'black' else 'black'
                            board.current_state.player_color = game.current_player
                            print(f"{board.current_state.player_color} turn... ")
                            human_player_moved = True

                        else:
                            #print("Piece was dragged to invalid square")
                            dragger.piece.clear_moves()
                    dragger.undrag_piece()
                    game.show_pieces(screen)
                    pygame.display.update()
                    


                elif event.type == pygame.KEYDOWN:
                    # changing themes
                    if event.key == pygame.K_t: # on 't' key pressed
                        game.change_theme()

                    # resetting game
                    if event.key == pygame.K_r: # on 'r' key pressed
                        game.reset()
                        show_popup_screen = False
                        # we need to reset values of game, board and dragger as well as they were created based on previous game object
                        game = self.game
                        board = self.game.board
                        dragger = self.game.dragger

                    # undoing last move
                    if event.key == pygame.K_u: # on 'u' key pressed

                        show_popup_screen = False
                        # call undo_last_move() - this will also decrease move count and remove last move from history
                        board.undo_last_move()
                        # set new value of game.current_player 
                        game.current_player = board.current_state.player_color

                        print(f"Game is going back to player {game.current_player} move no {board.current_state.move_count} () board.player_color is {board.current_state.player_color} ).")                       
                        
                elif event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            pygame.display.update()


main = Main()
main.mainloop()
