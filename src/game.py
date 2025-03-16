
import pygame
from const import *
from board import Board
from dragger import Dragger
from config import Config
from square import Square
from typing import List

class Game:
    def __init__(self):
        self.board = Board()
        self.last_n_board_positions: List[Board] = [] # this data structure is needed to verify if 'threefold repetition' rule was reached during the game       
        self.three_fold_repetition_detected: bool = False # flag indicating three fold repetition on board
        self.game_message: str = ""
        self.stopAI = False
        
        self.dragger = Dragger()
        self.current_player = 'white'
        self.hovered_sqr = None
        self.config = Config()
        
    # show methods
    def show_bg(self, surface: pygame.Surface):
        font = pygame.font.SysFont('monospace', 18, bold=True)
        theme = self.config.theme
        for row in range(ROWS):
            for col in range (COLS):
                surface_color = theme.bg.light if (row + col) % 2 == 0 else theme.bg.dark
                rect = (col * SQSIZE, row * SQSIZE, SQSIZE, SQSIZE)
                pygame.draw.rect(surface, surface_color, rect)
                
                # show row coordinates
                if col == 0:
                    color = theme.bg.dark if row % 2 == 0 else theme.bg.light
                    col_label = font.render(str(ROWS-row), 1, color)
                    col_label_pos = (5, 5 + row * SQSIZE)
                    surface.blit(col_label, col_label_pos)
                    
                # show col coordinates
                if row == 7:
                    color = theme.bg.dark if (row + col) % 2 == 0 else theme.bg.light
                    row_label = font.render(Square.get_alphacol(col), 1, color)
                    row_label_pos = (col* SQSIZE + SQSIZE - 20, HEIGHT - 20)
                    surface.blit(row_label, row_label_pos)                
                
    def show_AI_moves_analyzed(self, surface: pygame.Surface, moves_count: int):
        font = pygame.font.SysFont('monospace', 36, bold=True)
        theme = self.config.theme
        color = theme.bg.dark
        col_label = font.render(str(moves_count), 1, color)
        col_label_pos = (5, 5 + 7 * SQSIZE)
        surface.blit(col_label, col_label_pos)
                        
    def show_pieces(self, surface: pygame.Surface):
        for row in range(ROWS):
            for col in range (COLS):
                # if there is a piece?
                if self.board.squares[row][col].has_piece():
                    piece = self.board.squares[row][col].piece
                    
                    # all pieces except dragger piece
                    if piece is not self.dragger.piece:
                        piece.set_texture(size=80)
                        img = pygame.image.load(piece.texture)
                        img_center = col * SQSIZE + SQSIZE // 2, row * SQSIZE + SQSIZE // 2
                        piece.texture_rect = img.get_rect(center=img_center)
                        surface.blit(img, piece.texture_rect)
                        
    def show_moves(self, surface: pygame.Surface):
        theme = self.config.theme        
        if self.dragger.dragging:
            piece = self.dragger.piece
            for move in piece.moves: # loop all valid moves
                # set color
                surface_color = theme.moves.light if (move.final.row + move.final.col) % 2 == 0 else theme.moves.dark                
                # create rectangle
                rect = (move.final.col * SQSIZE, move.final.row * SQSIZE, SQSIZE, SQSIZE)
                # blit
                pygame.draw.rect(surface, surface_color, rect)
                
    def show_last_move(self, surface: pygame.Surface):
        theme = self.config.theme
        last_move = self.board.current_state.move
        if last_move:
            initial = last_move.initial
            final = last_move.final
            
            for pos in [initial, final]:
                # set color
                surface_color = theme.trace.light if (pos.row + pos.col) % 2 == 0 else theme.trace.dark                
                # create rectangle
                rect = (pos.col * SQSIZE, pos.row * SQSIZE, SQSIZE, SQSIZE)
                # blit
                pygame.draw.rect(surface, surface_color, rect)

    def show_en_passant_pawn(self, surface: pygame.Surface):
        theme = self.config.theme
        row, col = self.board.get_en_passant_pawn_position()
        
        # set color
        surface_color = theme.trace.light if (row + col) % 2 == 0 else theme.trace.dark                
        # create rectangle
        rect = (col * SQSIZE, row * SQSIZE, SQSIZE, SQSIZE)
        # blit
        pygame.draw.rect(surface, surface_color, rect)



    def show_pieces_not_moved_yet(self, surface: pygame.Surface):
        theme = self.config.theme
        rows, cols = self.board.get_pieces_not_moved_yet()

        for row, col in zip(rows, cols):
            # set color
            surface_color = theme.trace.light if (row + col) % 2 == 0 else theme.trace.dark                
            # create rectangle
            rect = (col * SQSIZE, row * SQSIZE, SQSIZE+10, SQSIZE+10)
            # blit
            pygame.draw.rect(surface, surface_color, rect)


    def show_hover(self, surface: pygame.Surface):
        if self.hovered_sqr:
            # set color
            surface_color = (180, 180, 180)
            # create rectangle
            rect = (self.hovered_sqr.col * SQSIZE, self.hovered_sqr.row * SQSIZE, SQSIZE, SQSIZE)
            # blit
            pygame.draw.rect(surface, surface_color, rect, width=5)
    
    def set_hover(self, row, col):
        self.hovered_sqr = self.board.squares[row][col]
        
    def change_theme(self):
        self.config.change_theme()
        
            
    def reset(self):
        self.__init__()
        
    # NEW METHOD!
    # Display a pop-up window with message to the player when current game ends.
    def draw_popup(self, surface: pygame.Surface, msg: str = "Default message"):
        WHITE = (255, 255, 255)
        GRAY = (200, 200, 200)
        BLACK = (0, 0, 0)
        BLUE = (0, 102, 204)
        font = pygame.font.Font(None, 20)
        xSize = 750
        ySize = 60
        pygame.draw.rect(surface, WHITE, ((WIDTH-xSize)/2, (HEIGHT-ySize)/2, xSize, ySize), border_radius=10)
        pygame.draw.rect(surface, BLACK, ((WIDTH-xSize)/2, (HEIGHT-ySize)/2, xSize, ySize), 3, border_radius=10)

        text = font.render(msg, True, BLACK)
        surface.blit(text, (100, HEIGHT/2))

    # TODO: Commenting out these verifications to speed up program execution!!!!
    # NEW METHOD!
    # Detects three fold repetition of positions which results in a game draw
    # Sets three_fold_repetition_detected menber variable to True if detected
    def check_three_fold_repetition(self):
        return False
        if len(self.last_n_board_positions) < 9:
            print(f"Attempting to check three fold repetition rule but the list has only {len(self.last_n_board_positions)} boards! It should contain 9.")
        elif self.last_n_board_positions[8] == self.last_n_board_positions[4]:
            if self.last_n_board_positions[4] == self.last_n_board_positions[0]:
                print(f"Three fold repetition detected on moves number: {self.last_n_board_positions[0].move_count}, {self.last_n_board_positions[4].move_count}, {self.last_n_board_positions[8].move_count}")
                self.three_fold_repetition_detected = True
                return
        # print(f"Three fold repetition NOT detected on moves no =  {self.last_n_board_positions[0].move_count}, {self.last_n_board_positions[4].move_count},  {self.last_n_board_positions[8].move_count}")
        
    # NEW METHOD!
    # Used to control content of self.last_n_board_positions List. 
    # Maximum number of boards stored in this list is 9.
    # This is because players need to move pieces 8 times in total to reach three fold repetition.
    def add_board_to_list_of_previous_positions(self, board: Board, n: int = 9):
        if len(self.last_n_board_positions) >= n:
            self.last_n_board_positions.pop(0)  # Remove the first element (FIFO behavior)
        self.last_n_board_positions.append(board)  # Add the new element

    def check_win(self, color: str) -> bool:
        enemy_color = 'black' if color == 'white' else 'white'        
        if self.board.is_king_checked(enemy_color) and self.board.player_has_no_valid_moves(enemy_color):
            self.game_message = f"Player {enemy_color} is checkmated! "
            self.game_message += "Press 'r' to restart or close the app window to quit."            
            return True
        else:
            return False
    
    def check_draw(self) -> bool:
        enemy_color = 'black' if self.current_player == 'white' else 'white'
        if not self.board.is_king_checked(enemy_color) and self.board.player_has_no_valid_moves(enemy_color):
            self.game_message = f"Draw. Player {enemy_color} is under stalemate! "
            self.game_message += "Press 'r' to restart or close the app window to quit."            
            return True
        elif self.board.current_state.move_count >= 5:
            self.check_three_fold_repetition()
            if self.three_fold_repetition_detected:
                self.game_message = f"Draw. Reason: three fold repetition of the position. "
                self.game_message += "Press 'r' to restart or close the app window to quit."
                return True
        elif self.board.check_insufficient_mating_material():
            self.game_message = f"Draw. Reason: insufficient material. "
            self.game_message += "Press 'r' to restart or close the app window to quit."            
            return True
        elif self.board.check_fifty_move_rule():
            self.game_message = f"Draw. Reason: 50 moves without pawn move and capturing a piece. "
            self.game_message += "Press 'r' to restart or close the app window to quit."
            return True
        else: 
            return False