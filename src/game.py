
import pygame
from const import *
from board import Board
from dragger import Dragger
from config import Config
from square import Square

class Game:
    def __init__(self):
        self.board = Board()
        self.dragger = Dragger()
        self.current_player = 'white'        
        self.hovered_sqr = None
        self.config = Config()
        
    # show methods
    def show_bg(self, surface: pygame.Surface):
        theme = self.config.theme
        for row in range(ROWS):
            for col in range (COLS):
                surface_color = theme.bg.light if (row + col) % 2 == 0 else theme.bg.dark
                rect = (col * SQSIZE, row * SQSIZE, SQSIZE, SQSIZE)
                pygame.draw.rect(surface, surface_color, rect)
                
                # show row coordinates
                if col == 0:
                    color = theme.bg.dark if row % 2 == 0 else theme.bg.light
                    col_label = self.config.font.render(str(ROWS-row), 1, color)
                    col_label_pos = (5, 5 + row * SQSIZE)
                    surface.blit(col_label, col_label_pos)
                    
                # show col coordinates
                if row == 7:
                    color = theme.bg.dark if (row + col) % 2 == 0 else theme.bg.light
                    row_label = self.config.font.render(Square.get_alphacol(col), 1, color)
                    row_label_pos = (col* SQSIZE + SQSIZE - 20, HEIGHT - 20)
                    surface.blit(row_label, row_label_pos)                
                
                
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
        if self.board.last_move:
            initial = self.board.last_move.initial
            final = self.board.last_move.final
            
            for pos in [initial, final]:
                # set color
                surface_color = theme.trace.light if (pos.row + pos.col) % 2 == 0 else theme.trace.dark                
                # create rectangle
                rect = (pos.col * SQSIZE, pos.row * SQSIZE, SQSIZE, SQSIZE)
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
        
    def play_sound(self, captured=False):
        if captured:
            self.config.capture_sound.play()
        else:
            self.config.move_sound.play()
            
    def reset(self):
        self.__init__()
        
    # NEW METHOD!    
    def draw_popup(self, surface: pygame.Surface, msg: str = "Default message"):
        WHITE = (255, 255, 255)
        GRAY = (200, 200, 200)
        BLACK = (0, 0, 0)
        BLUE = (0, 102, 204)
        font = pygame.font.Font(None, 20)
        xSize = 600
        ySize = 100
        pygame.draw.rect(surface, WHITE, ((WIDTH-xSize)/2, (HEIGHT-ySize)/2, xSize, ySize), border_radius=10)
        pygame.draw.rect(surface, BLACK, ((WIDTH-xSize)/2, (HEIGHT-ySize)/2, xSize, ySize), 3, border_radius=10)

        text = font.render(msg, True, BLACK)
        surface.blit(text, (150, HEIGHT/2))
