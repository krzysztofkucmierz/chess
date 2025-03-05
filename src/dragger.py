
import pygame
from const import *
from piece import Piece

class Dragger:

    def __init__(self):
        self.piece: Piece = None # type of the piece
        self.dragging = False # if the piece is being dragged
        self.mouseX = 0
        self.mouseY = 0
        self.initial_row = 0
        self.initial_col = 0

    def update_blit(self, surface: pygame.Surface):
        # texture
        self.piece.set_texture(size=128)
        texture = self.piece.texture
        # image
        img = pygame.image.load(texture)
        # rectange
        img_center = (self.mouseX, self.mouseY)
        self.piece.texture_rect = img.get_rect(center=img_center)
        # blit
        surface.blit(img, self.piece.texture_rect)
        
    def update_mouse(self, pos):
        self.mouseX, self.mouseY = pos # (xcoor, ycoor)
        
    def save_initial(self, pos):
        self.initial_row = pos[1] // SQSIZE
        self.initial_col = pos[0] // SQSIZE
    
    def drag_piece(self, piece: Piece):
        self.piece = piece
        self.dragging = True
        
    def undrag_piece(self):
        self.piece = None
        self.dragging = False