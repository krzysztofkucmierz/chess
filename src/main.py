# Original code by AlejoG10 avaiable at GitHub https://github.com/AlejoG10/python-chess-ai-yt
# Bug fixes/improvements/new features by Krzysztof Kućmierz krzysztof.kucmierz@artificiuminformatica.pl

import pygame
import sys
from const import *
from game import Game
from square import Square
from move import Move
from piece import color_name
import copy
from minimax import *
from sound import Sound
import os
import tkinter as tk

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
        self.human_player_moved = False # set to True if human (white player) made a move, reset to False afte AI made a move
        self.show_popup_screen = False # controls whether to display end of game screen

    # Function to show the pop up with buttons and return user selection
    def get_game_mode(self):

        mode = []

        def select_mode(selected_mode):
            # Callback to store the selected mode and close the window.
            mode.append(selected_mode)
            root.destroy()  # Close the window

        # Create Tkinter window
        root = tk.Tk()
        root.title("Select Game Mode")

        #Centers the Tkinter window on the screen.
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        width = 300
        height = 200
        # Calculate position x, y
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        root.geometry(f"{width}x{height}+{x}+{y}")

        # Create label
        label = tk.Label(root, text="Choose Game Mode:", font=("Arial", 12))
        label.pack(pady=10)

        # Create buttons
        btn_pvp = tk.Button(root, text="Player vs. Player", command=lambda: select_mode(GameMode.PLAYER_VS_PLAYER_MODE))
        btn_pvp.pack(pady=5)

        btn_pvc = tk.Button(root, text="Player vs. Computer (black)", command=lambda: select_mode(GameMode.PLAYER_VS_AI_MODE))
        btn_pvc.pack(pady=5)

        btn_pvc = tk.Button(root, text="Computer (white) vs. Player", command=lambda: select_mode(GameMode.AI_VS_PLAYER_MODE))
        btn_pvc.pack(pady=5)

        # Run the Tkinter event loop
        root.mainloop()

        # Return selected mode
        return mode[0] if mode else None  # Return selected mode or None if window was closed

        
    def play_sound(self, captured=False):
        if captured:
            self.capture_sound.play()
        else:
            self.move_sound.play()

    def AI_turn(self):
        ai_turn_as_white = (self.human_player_moved and self.game.current_player == WHITE_PIECE_COLOR) or self.game.first_move_made == False # condition for move when AI plays as white
        ai_turn_as_black = self.human_player_moved and self.game.current_player == BLACK_PIECE_COLOR and self.game.stopAI == False # condition for move when AI plays as black
        if (self.game.mode == GameMode.AI_VS_PLAYER_MODE and ai_turn_as_white) or (self.game.mode == GameMode.PLAYER_VS_AI_MODE and ai_turn_as_black): 
            print("Now it is AI turn...")
            self.game.show_bg(self.screen)
            self.game.show_last_move(self.screen)
            #game.show_pieces_not_moved_yet(screen)
            self.game.show_pieces(self.screen)
            pygame.display.update()
            
            #profiler.enable()  # Start profiling
            best_piece, best_move = self.AI_engine.best_move(self.game, self.screen)
            #profiler.disable()  # Stop profiling


            #profiler.print_stats(sort=1)
            if best_move:
                if self.game.first_move_made == False:
                    self.game.first_move_made = True
                
                # remember last move - append to the moves history
                self.game.moves_history.append((copy.deepcopy(best_piece), copy.deepcopy(best_move)))
                
                self.play_sound(self.game.board_states[self.game.move_count].current_state.captured)

                #show methods
                self.game.show_bg(self.screen)
                self.game.show_last_move(self.screen)
                self.game.show_pieces(self.screen)
                pygame.display.update()
                best_move.show(best_piece.name, "AI made a move! ")

                # check if win or draw condition is on the board
                if self.game.check_draw():
                    self.show_popup_screen = True                               
                elif self.game.check_win(self.game.current_player):
                    self.show_popup_screen = True
                else:
                    self.show_popup_screen = False                        
                if self.show_popup_screen:
                    self.game.draw_popup(self.screen, self.game.game_message)
            else:
                self.game.game_message = f"You won! AI has resigned."
                self.game.game_message += "Press 'r' to restart or close the app window to quit."
                self.show_popup_screen = True                        
                self.game.draw_popup(self.screen, self.game.game_message)

            self.game.prepare_board_state_for_next_move()
            
            self.human_player_moved = False        
        
        
    def mainloop(self):
        game = self.game
        screen = self.screen
        dragger = self.game.dragger

        # Get gameplay mode (PvP, PvC, CvP)
        game.mode = self.get_game_mode()
        print("Selected mode:", game.mode)

        # At the very beginning set counters to first move
        # increment by 1 'game.move_count' and move_count counter in next board_state
        game.move_count += 1
        game.board_states[game.move_count].current_state.move_count = game.move_count # move count was already incresed in above line

        while True:
            # show methods
            game.show_bg(screen)
            game.show_last_move(screen)
            #game.show_pieces_not_moved_yet(screen)             
            game.show_moves(screen)
            game.show_pieces(screen)
            game.show_hover(screen)



            # NEW LINES: if game ended show a popup window on screen
            if self.show_popup_screen:
                game.draw_popup(screen, game.game_message)


            if dragger.dragging:
                dragger.update_blit(screen)
                
            for event in pygame.event.get():

                # AI turn
                if game.mode != GameMode.PLAYER_VS_PLAYER_MODE:
                    self.AI_turn()

                # click event
                if event.type == pygame.MOUSEBUTTONDOWN:
                    # Operation on the board
                    dragger.update_mouse(event.pos)
                    clicked_row = dragger.mouseY // SQSIZE
                    clicked_col = dragger.mouseX // SQSIZE
                    # if clicked square has a piece and the piece is of the color of current player turn 
                    if game.board_states[game.move_count].squares[clicked_row][clicked_col].has_team_piece(game.current_player):
                        piece = game.board_states[game.move_count].squares[clicked_row][clicked_col].piece
                        game.board_states[game.move_count].calc_moves(piece, clicked_row, clicked_col)
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
                        
                        if game.board_states[game.move_count].valid_move(dragger.piece, move):
                            if game.first_move_made == False:
                                game.first_move_made = True

                            # check if piece captured
                            game.board_states[game.move_count].set_capturing_move_flag(move)

                            # move the piece
                            game.board_states[game.move_count].move(dragger.piece, move)

                            # add a new move to game.moves_history
                            game.moves_history.append((copy.deepcopy(piece), copy.deepcopy(move)))

                            self.play_sound(game.board_states[game.move_count].current_state.captured)

                            #show methods
                            game.show_bg(screen)
                            game.show_last_move(screen)
                            #game.show_pieces_not_moved_yet(screen)
                            game.show_pieces(screen)
                            pygame.display.update()
                            # DEBUG INFO
                            #game.board_states[game.move_count].show_pieces_count()
                            #game.show_move_counters()
                            #game.board_states[game.move_count].show_move_counters()
                            print(f"Game score based on value of pieces is: {game.board_states[game.move_count].calculate_piece_score()}")
                            
                            # check if win or draw condition is on the board
                            if game.check_draw():
                                self.show_popup_screen = True
                                game.stopAI = True

                            elif game.check_win(game.current_player):
                                self.show_popup_screen = True
                                game.stopAI = True

                            else:
                                self.show_popup_screen = False

                            if self.show_popup_screen:
                                game.draw_popup(screen, game.game_message)
                            
                            game.prepare_board_state_for_next_move()
                            
                            print(f"{color_name(game.current_player)} turn... ")
                            self.human_player_moved = True
                        else:
                            #print("Piece was dragged to invalid square")
                            dragger.piece.clear_moves()
                    dragger.undrag_piece()
                    game.show_pieces(screen)
                    game.show_en_passant_pawn(screen)                    
                    pygame.display.update()
                    


                elif event.type == pygame.KEYDOWN:
                    # changing themes
                    if event.key == pygame.K_t: # on 't' key pressed
                        game.change_theme()

                    # resetting game
                    if event.key == pygame.K_r: # on 'r' key pressed
                        game.reset()
                        self.show_popup_screen = False
                        # we need to reset values of game, board and dragger as well as they were created based on previous game object
                        game = self.game
                        dragger = self.game.dragger

                    # undoing last move
                    if event.key == pygame.K_u: # on 'u' key pressed
                        self.show_popup_screen = False
                        # remove last move from history
                        if game.move_count == 0:
                            print("Can't undo. Game is in initial state!")
                        else:
                            if game.moves_history:
                                game.moves_history.pop()
                            # undo the move
                            game.undo_last_move()
                            print(f"Game is going back to player {color_name(game.current_player)} move no {game.move_count}.")
                            #show methods
                            game.show_bg(screen)
                            game.show_last_move(screen)
                            #game.show_pieces_not_moved_yet(screen)
                            game.show_pieces(screen)
                            pygame.display.update()

                elif event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            pygame.display.update()


main = Main()
main.mainloop()
