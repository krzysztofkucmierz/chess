
import pygame
from const import *
from board import Board
from piece import Piece, Pawn, King, color_name, piece_moved
from move import Move
from dragger import Dragger
from config import Config
from square import Square
from typing import List, Tuple

class Game:
    def __init__(self):
        # nove_count Counts number of moves played so far. 1 is initial move number. It increases by 1 after each player moves.
        # It is not equal to move number used in chess notation!!! 
        self.mode: GameMode = GameMode.PLAYER_VS_PLAYER_MODE
        self.move_count: int = 0
        self.first_move_made = False
        self.current_player: int = WHITE_PIECE_COLOR
        self.board_states: List[Board] = [Board() for _ in range(300)]
        self.moves_history: List[Tuple[Piece, Move]] = [] # this list records all game moves (a single sequence of all white and black moves as they were played)
        self.three_fold_repetition_detected: bool = False # flag indicating three fold repetition on board
        # snapshot the starting position for the repetition rule - board_states[0] is
        # mutated in place by the first move, so its key must be taken now; BLACK as
        # pseudo-mover marks "white to move", consistent with finalized state keys
        self.board_states[0].dump_to_squares_fast_method()
        placement, _, rights = self.position_key(0)
        self.initial_position_key = (placement, BLACK_PIECE_COLOR, rights)

        self.stopAI = False
        self.game_message: str = ""
        self.dragger = Dragger()
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
                if self.board_states[self.move_count].squares[row][col].has_piece():
                    piece = self.board_states[self.move_count].squares[row][col].piece
                    
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
        last_move = self.board_states[self.move_count].current_state.move
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
        row, col = self.board_states[self.move_count].get_en_passant_pawn_position()
        
        # set color
        surface_color = theme.trace.light if (row + col) % 2 == 0 else theme.trace.dark                
        # create rectangle
        rect = (col * SQSIZE, row * SQSIZE, SQSIZE, SQSIZE)
        # blit
        pygame.draw.rect(surface, surface_color, rect)



    def show_pieces_not_moved_yet(self, surface: pygame.Surface):
        theme = self.config.theme
        rows, cols = self.board_states[self.move_count].get_pieces_not_moved_yet()

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
        self.hovered_sqr = self.board_states[self.move_count].squares[row][col]
        
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


    def show_move_counters(self):
        print(f"Game.move_count: {self.move_count}.")


    # Hashable identity of the position stored in board_states[index], for the
    # three fold repetition rule (FIDE article 9.2): piece placement (type + color +
    # en passant flag), the color recorded in the state, and the actual castling rights.
    # Built from squares_fast_method - the Piece objects in 'squares' are shared between
    # board states, so only the int encoding preserves historical moved/en-passant flags.
    # The PIECE_MOVED bit is masked out of the placement (a knight that returned to its
    # start square recreates the same position even though its flag changed) and re-enters
    # only through the castling rights of the four king/rook home squares.
    def position_key(self, index: int) -> tuple:
        fast = self.board_states[index].squares_fast_method

        def castling_right(king_row, rook_col):
            return (fast[king_row][4] & (KING_PIECE | PIECE_MOVED)) == KING_PIECE \
               and (fast[king_row][rook_col] & (ROOK_PIECE | PIECE_MOVED)) == ROOK_PIECE

        placement = tuple(square & (ANY_PIECE | WHITE_PIECE_COLOR | EN_PASSANT_PAWN)
                          for row in fast for square in row)
        rights = (castling_right(7, 0), castling_right(7, 7),
                  castling_right(0, 0), castling_right(0, 7))
        return (placement, self.board_states[index].current_state.player_color, rights)

    # Returns True if the current position has occurred at least 3 times in the game
    # (draw by three fold repetition, FIDE article 9.2). Sets three_fold_repetition_detected.
    #
    # How the history is stored: Board.move() mutates board_states[i] in place, so a
    # finalized state i holds the position AFTER ply i+1 with player_color = the color
    # that made that ply - a consistent "last mover" marking across all finalized states,
    # which position_key() can compare directly. Two consequences handled here:
    # - the initial position's snapshot is overwritten by ply 1, so it is kept separately
    #   as initial_position_key (with BLACK as pseudo-mover: white to move);
    # - right after prepare_board_state_for_next_move() the state at move_count is a
    #   fresh copy of move_count-1 (identical placement, toggled color); a real move
    #   always changes the placement, so equal neighbouring placements reliably identify
    #   that timing and the duplicate is skipped.
    def check_three_fold_repetition(self) -> bool:
        last = self.move_count
        if last >= 1 and (self.board_states[last].squares_fast_method
                          == self.board_states[last - 1].squares_fast_method):
            last -= 1  # called after prepare - board_states[move_count] is a duplicate

        current_key = self.position_key(last)
        repetitions = 1 if current_key == self.initial_position_key else 0

        # positions from before the last irreversible move (pawn move or capture) can
        # never recur - scanning from its stamp is a pure optimization, as a position
        # older than that can never equal the current placement anyway
        state = self.board_states[last].current_state
        first_possible = max(state.last_move_when_pawn_moved,
                             state.last_move_when_piece_captured)
        repetitions += sum(1 for i in range(first_possible, last + 1)
                           if self.position_key(i) == current_key)

        if repetitions >= 3:
            print(f"Three fold repetition detected: the current position "
                  f"has occurred {repetitions} times.")
            self.three_fold_repetition_detected = True
            return True
        return False

    # Returns True if game has reached 50 move rule which leads to game draw. 
    # NOTE. Using > comparison as move count is increased before checking this rule
    def check_fifty_move_rule(self, limit_moves_count: int = 50) -> bool:
        #print(f"Game.check_fifty_move_rule(): pawns: {(self.move_count - self.board_states[self.move_count].current_state.last_move_when_pawn_moved) // 2} captures: {(self.move_count - self.board_states[self.move_count].current_state.last_move_when_piece_captured) // 2}")
        return (self.move_count - self.board_states[self.move_count].current_state.last_move_when_pawn_moved) // 2 >= limit_moves_count and (self.move_count - self.board_states[self.move_count].current_state.last_move_when_piece_captured) // 2 >= limit_moves_count

    # Returns True if player 'color' has checkmated the opponent
    def check_win(self, color: int) -> bool:
        enemy_color = BLACK_PIECE_COLOR if color == WHITE_PIECE_COLOR else WHITE_PIECE_COLOR
        state = self.board_states[self.move_count].current_state
        # FIXED BUG: the 'color' argument was ignored, so a checkmate was reported as a win
        # for whichever color was asked about first. The winner is the color of the piece
        # that made the last (mating) move - state.piece is the only field holding it both
        # before and after prepare_board_state_for_next_move() (player_color gets switched).
        if state.opponent_king_checked and state.opponent_has_no_valid_moves \
                and state.piece is not None and state.piece.color == color:
            self.game_message = f"Player {color_name(enemy_color)} is checkmated! "
            self.game_message += "Press 'r' to restart or close the app window to quit."
            return True
        else:
            return False
    
    def check_draw(self) -> bool:
        enemy_color = BLACK_PIECE_COLOR if self.current_player == WHITE_PIECE_COLOR else WHITE_PIECE_COLOR
        if not self.board_states[self.move_count].current_state.opponent_king_checked and self.board_states[self.move_count].current_state.opponent_has_no_valid_moves:
            self.game_message = f"Draw. Player {color_name(enemy_color)} is under stalemate! "
            self.game_message += "Press 'r' to restart or close the app window to quit." 
            return True
        elif self.check_three_fold_repetition():
            self.game_message = "Draw. Reason: three fold repetition of the position. "
            self.game_message += "Press 'r' to restart or close the app window to quit."
            return True
        elif self.board_states[self.move_count].check_insufficient_mating_material():
            self.game_message = "Draw. Reason: insufficient material. "
            self.game_message += "Press 'r' to restart or close the app window to quit."            
            return True
        elif self.check_fifty_move_rule():
            self.game_message = "Draw. Reason: 50 moves without pawn move and capturing a piece. "
            self.game_message += "Press 'r' to restart or close the app window to quit."
            return True
        else: 
            return False
        return False
        
    # returns if piece was moved based on moves history
    def piece_moved(self, piece: Piece, row, col) -> bool:
        if len(self.moves_history) <= 0:
            return False
        for p, m in self.moves_history:
            if piece.color == p.color:
                if isinstance(piece, Piece):
                    if m.final.row == row and m.final.col == col:
                        return True

        return False

    # after the move was made, prepare board state for the next move
    def prepare_board_state_for_next_move(self):
        # copy content of the game.board_state[game.move_count] to next board state in the list as its initial value
        self.board_states[self.move_count + 1].copy_board_content(self.board_states[self.move_count])
        # increment by 1 'game.move_count' and move_count counter in next board_state
        self.move_count += 1
        self.board_states[self.move_count].current_state.move_count = self.move_count # move count was already incresed in above line
                                    
        # Below line must be the last one after the valid move. This linie limits the player move to only one move!
        self.current_player = WHITE_PIECE_COLOR if self.current_player == BLACK_PIECE_COLOR else BLACK_PIECE_COLOR
        self.board_states[self.move_count].current_state.player_color = self.current_player
        
    # Set en_passant flags for board state after move_count  (restoring correct Piece attributes required when undoing a move)
    def undo_en_passant(self):
        if self.move_count > 0:
            state = self.board_states[self.move_count].current_state
            piece = state.piece
            if piece:
                # FIXED BUG: re-flag only a Pawn whose recorded move was a two-square push;
                # after any other last move all en passant flags must simply be cleared
                double_pawn_push = (isinstance(piece, Pawn)
                                    and state.move is not None
                                    and abs(state.move.final.row - state.move.initial.row) == 2)
                self.board_states[self.move_count].set_true_en_passant(piece, double_pawn_push)
    
    # Set moved flag of Piece moved in move_count + 1 (restoring correct Piece attributes required when undoing a move)
    def undo_moved(self):
        # get initial square of the Move performed at move_count + 1
        move = self.board_states[self.move_count + 1].current_state.move
        initial = move.initial
        # set piece attribute moved according to its previous state (by decoding info from square_fast_method)
        piece = self.board_states[self.move_count + 1].current_state.piece
        previous_moved_state = piece_moved(self.board_states[self.move_count].squares_fast_method[initial.row][initial.col])
        piece.moved = previous_moved_state
        # FIXED BUG: undoing a castling move must also restore the moved flag of the Rook,
        # otherwise the (shared) Rook object keeps moved=True after lines explored by minimax
        # and castling with it is refused for the rest of the game
        if isinstance(piece, King) and abs(move.final.col - move.initial.col) == 2:
            rook_initial_col, rook_final_col = (0, 3) if move.final.col == 2 else (7, 5)
            rook = self.board_states[self.move_count + 1].squares[move.final.row][rook_final_col].piece
            if rook is not None:
                rook.moved = piece_moved(
                    self.board_states[self.move_count].squares_fast_method[move.final.row][rook_initial_col])
        
        
    # Procedure to undo the last move
    def undo_last_move(self):

        current_player = self.board_states[self.move_count -1].current_state.player_color

        # decrease game.move_count by 1
        if self.move_count <= 1: # at first move! Can't undo it.
            pass #self.first_move_made == False # TODO: is it needed?
        else:

            self.move_count -= 2 # decrease by 2 because the counter was already incresed by 1 inside prepare_board_state_for_next_move()
            self.undo_en_passant()
            self.undo_moved()

            self.board_states[self.move_count + 1].copy_board_content(self.board_states[self.move_count])

            # advance to next move
            self.move_count += 1
            self.board_states[self.move_count].current_state.move_count = self.move_count # move count was already incresed in above line
            # set new value of game.current_player
            self.current_player = current_player
            self.board_states[self.move_count].current_state.player_color = current_player