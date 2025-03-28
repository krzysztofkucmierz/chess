
from const import *
from piece import *
from typing import List, Tuple
from move import Move
from square import Square
from sound import Sound

import os
import copy

class BoardState:
    def __init__(self):
        self.move_count: int = 0
        self.player_color: int = WHITE_PIECE_COLOR
        self.move: Move = None # coordinates of he move - used only in Game.undo_moved()
        self.piece: Piece = None # piece which is moved
        self.en_passant_captured_piece: Piece = None # stored but NOT USED!
        self.captured: bool = False
        self.en_passant_move: bool = False # was it en passant move? # stored but NOT USED!
        self.castling_move: bool = False # was it castling move? # stored but NOT USED!
        self.opponent_king_checked: bool = False
        self.opponent_has_no_valid_moves: bool = False
        self.white_pieces_count = 16 # initial number of white pieces
        self.black_pieces_count = 16 # initial number of black pieces
        self.last_move_when_pawn_moved = 0 # Stores game move number when pawn was last moved. Will be set to move_count value when any Pawn will move.
        self.last_move_when_piece_captured = 0 # Stores game move number when a piece was last moved. Will be set to move_count when any piece will be captured.


'''
Contains full board information about specific moment of the game.
Method data structures:
squares - rich representation of the board (contains Square, Move and Piece objects). 
    Mainly to display the board board content including user interaction in real-time.
squares_fast_method - optimized representation of the board (pieces encoded as int types).
    Required for fast computation of AI moves.
current_state - additional board state information computed at each move
'''
class Board:
    def __init__(self):
        self.squares: List[List[Square]] = [[0, 0, 0, 0, 0, 0, 0, 0] for col in range(COLS)]
        self.squares_fast_method: List[List[int]] = [[0, 0, 0, 0, 0, 0, 0, 0] for col in range(COLS)] # piece info is stored as integers
        self.current_state: BoardState = BoardState()
        # self.previous_states: List[BoardState] = []
        self._create()
        self._add_pieces(WHITE_PIECE_COLOR)
        self._add_pieces(BLACK_PIECE_COLOR)

    # TODO: change it to squares_fast_method instead using squares?
    # Check if two boards are equal. This means there is identical position on both boards.
    # This method is needed to implement 3 fold repetition rule.
    # Returns:
    #   True if position on both boards is identical
    #   False otherwise
    def __eq__(self, other):
        if other == None:
            return False
        # check if content of all board squares are identical between self and other
        for row in range(ROWS):
            for col in range(COLS):
                if self.squares[row][col].piece != other.squares[row][col].piece:
                    return False
        return True

    # Fast copy board contents without referencing to previous board or it's inner objects 
    # currently it copies only squares_fast_method and current_state
    def copy_board_content(self, other):
        # copy squares_fast_method (int values are actually copied)
        for row in range(ROWS):
            for col in range(COLS):
                self.squares_fast_method[row][col] = other.squares_fast_method[row][col]

        # only references are assigned for squares structure, no copy is created!
        for row in range(ROWS):
            for col in range(COLS):
                self.squares[row][col].piece = other.squares[row][col].piece

        # copy current_state (only non-mutable variables are copied)
        self.current_state.black_pieces_count = other.current_state.black_pieces_count
        self.current_state.captured = other.current_state.captured   
        self.current_state.castling_move = other.current_state.castling_move
        self.current_state.en_passant_captured_piece = other.current_state.en_passant_captured_piece # piece object
        self.current_state.en_passant_move = other.current_state.en_passant_move
        self.current_state.last_move_when_pawn_moved = other.current_state.last_move_when_pawn_moved
        self.current_state.last_move_when_piece_captured = other.current_state.last_move_when_piece_captured
        self.current_state.move_count = other.current_state.move_count
        self.current_state.move = other.current_state.move # move object
        self.current_state.piece = other.current_state.piece # piece object
        self.current_state.player_color = other.current_state.player_color
        self.current_state.white_pieces_count = other.current_state.white_pieces_count

    # dumps board information from 'squares' structure into 'squares_fast_method' structure
    def dump_to_squares_fast_method(self):
        piece_code: int = 0
        for row in range(ROWS):
            for col in range(COLS):
                piece_code = 0
                if not self.squares[row][col].has_piece(): # if square is empty
                    self.squares_fast_method[row][col] = piece_code
                    continue

                if self.squares[row][col].piece.color == WHITE_PIECE_COLOR:
                    piece_code |= WHITE_PIECE_COLOR
                else:
                    piece_code |= BLACK_PIECE_COLOR

                if self.squares[row][col].piece.moved == True:
                    piece_code |= PIECE_MOVED


                if isinstance(self.squares[row][col].piece, Pawn):
                    piece_code |= PAWN_PIECE
                    if self.squares[row][col].piece.en_passant == True: # encode en passant state
                        piece_code |= EN_PASSANT_PAWN                       
                elif isinstance(self.squares[row][col].piece, Knight):
                    piece_code |= KNIGHT_PIECE
                elif isinstance(self.squares[row][col].piece, Bishop):
                    piece_code |= BISHOP_PIECE
                elif isinstance(self.squares[row][col].piece, Rook):
                    piece_code |= ROOK_PIECE
                elif isinstance(self.squares[row][col].piece, Queen):
                    piece_code |= QUEEN_PIECE
                elif isinstance(self.squares[row][col].piece, King):
                    piece_code |= KING_PIECE
                else:
                    print(f"dump_to_squares_fast_method(): Unexpected value of the piece: {self.squares[row][col].piece}")

                #print(f"Piece encoded as: {hex(piece_code)}")
                self.squares_fast_method[row][col] = piece_code




    # Idea of board.move() method:
    # - adjust 'square' structure based on the move
    # - dump content of 'square' structure into 'squares_fast_method'
    # - store additional info in 'current_state' structure
    # Note: right after move() method game.move_count must be increased by 1

    # This method actually makes a move 'move' for a piece 'piece' on the board
    # if testing == True then operation is performed to evaluate checks and not to make any move
    # if clear_moves == True then all possible moves for a given piece are cleared after the move is made. 
    #   Particularly in AI.minimax() methods moves can't be cleared!
    def move(self, piece: Piece, move: Move, test_check: bool = False, clear_moves: bool = True, ai_minimax = False):

        initial = move.initial
        final = move.final
        #en_passant_empty = self.squares[final.row][final.col].isempty()
        en_passant_empty = is_empty(self.squares_fast_method[final.row][final.col])  # optimization
        pawn_moved = isinstance(piece, Pawn)
        # 1. adjust 'square' structure based on the move

        # standard board update for the 'move'
        self.squares[initial.row][initial.col].piece = None
        self.squares[final.row][final.col].piece = piece

        # en passant capture
        if pawn_moved:
            diff = final.col - initial.col
            if diff != 0 and en_passant_empty:
                self.squares[initial.row][initial.col + diff].piece = None
                if not test_check:
                    self.current_state.en_passant_move = True
                    self.current_state.en_passant_captured_piece = self.squares[initial.row][initial.col + diff].piece
                    self.update_pieces_count(piece.color) # update piece counter after capture (eg. white player captures, so decrease black pieces count)
                    self.current_state.last_move_when_piece_captured = self.current_state.move_count # increase 'last_move_when_piece_captured' counter
                    if not ai_minimax: # don't play en-passant capture sound when performing minimax algorithm
                        sound = Sound(os.path.join('assets/sounds/capture.wav'))
                        sound.play()

            # Pawn promotion to a Queen
            if (final.row == 7 or final.row == 0):
                self.squares[final.row][final.col].piece = Queen(piece.color)
            
        # King castling - since King's move is coded above as standard move, now only move the Rook
        if not test_check:
            if isinstance(piece, King):
                if self.castling(initial, final): # check if castling move detected
                    self.current_state.castling_move = True
                    diff = final.col - initial.col
                    rook = piece.left_rook if (diff < 0) else piece.right_rook
                    rook_move = rook.moves[-1]
                    # changed from recursion to normal implementation! 
                    self.squares[rook_move.initial.row][rook_move.initial.col].piece = None
                    self.squares[rook_move.final.row][rook_move.final.col].piece = rook
                    rook.moved = True

        # make sure en passant state for pawns lasts only for 1 turn, so clear the en passant flag for all other pawns on the board
        if not test_check:
            self.set_true_en_passant(piece, pawn_moved)
            
        # 2. dump content of 'square' structure into 'squares_fast_method'
        if not test_check:
            self.dump_to_squares_fast_method()

        # 3. save additional info to 'current_state' structure        
        if not test_check:
            self.current_state.player_color = piece.color
            self.current_state.move = move
            self.current_state.piece = piece

            if self.current_state.captured:
                self.update_pieces_count(piece.color) # update piece counter after capture
                self.current_state.last_move_when_piece_captured = self.current_state.move_count # set this variable to 'move_count' after capture

            # increase 'last_move_when_pawn_moved' counter
            if pawn_moved:
                self.current_state.last_move_when_pawn_moved = self.current_state.move_count

            enemy_color = BLACK_PIECE_COLOR if piece.color == WHITE_PIECE_COLOR else WHITE_PIECE_COLOR
            self.current_state.opponent_king_checked = self.is_king_checked(enemy_color)
            self.current_state.opponent_has_no_valid_moves = self.player_has_no_valid_moves(enemy_color)

        # final processing of the move
        if not test_check:
            piece.moved = True
        else: # if just test for check restore value of 'moved' attribute from the previous move stored in squares_fast_method!
            piece.moved = piece_moved(self.squares_fast_method[initial.row][initial.col])

        if clear_moves:  # clear valid moves
            piece.clear_moves()


    # check if a piece move is a valid move on the board
    def valid_move(self, piece: Piece, move: Move):
        #move.show(piece.name, "")
        #piece.show_moves()
        return move in piece.moves

    # check if king's move spans 2 columns as in castling
    def castling(self, initial, final):
        return abs(initial.col - final.col) == 2

    # check for all pawns and set their en_passant state to False if they were not moved in the last move
    def set_true_en_passant(self, piece, pawn_moved: bool):
        
        for row in range(ROWS):
            for col in range(COLS):
                if isinstance(self.squares[row][col].piece, Pawn):
                    self.squares[row][col].piece.en_passant = False

        if pawn_moved:
            piece.en_passant = True

    # set 'captured' flag by checking if destination square contained a piece 
    def set_capturing_move_flag(self, move: Move):
        self.current_state.captured = self.squares[move.final.row][move.final.col].has_piece()
        
    
    # verify if the move of the piece will uncover a check of King of the same color as the moved piece
    def in_check(self, piece: Piece, move: Move):
        king_checked = False

        # temporarily set current player color to piece color
        player_color = self.current_state.player_color
        self.current_state.player_color = piece.color
        
        # store temporarily content of the moved piece and (if applicable) piece captured en-passant
        previous_final_square_content = self.squares[move.final.row][move.final.col].piece

        # en_passant_empty = self.squares[move.final.row][move.final.col].isempty()
        en_passant_empty = is_empty(self.squares_fast_method[move.final.row][move.final.col]) # OPTIMIZATION
        if isinstance(piece, Pawn):
            diff = move.final.col - move.initial.col
            if diff != 0:
                if en_passant_empty:
                    previous_en_passant_capture_square_content = self.squares[move.initial.row][move.initial.col + diff].piece

        self.move(piece, move, test_check = True, clear_moves = False) # simulate the move

        king_checked = self.is_king_checked(piece.color)

        # move(test_check = True) don't update square_fast_method struct so based on it we can revert attributes of moved piece

        # revert board from standard 'move'
        self.squares[move.initial.row][move.initial.col].piece = piece
        self.squares[move.final.row][move.final.col].piece = previous_final_square_content

        # additionally revert board state from en-passant capture 'move'
        if isinstance(piece, Pawn):
            diff = move.final.col - move.initial.col
            if diff != 0:
                if en_passant_empty:
                    self.squares[move.initial.row][move.initial.col + diff].piece = previous_en_passant_capture_square_content

        # revert player color to the old value
        self.current_state.player_color = player_color
        
        return king_checked

        
    # Decreases piece counter of the enemy player after a player 'current_player_color' made a move and enemy piece was captured.
    def update_pieces_count(self, current_player_color: int):
        if current_player_color == WHITE_PIECE_COLOR:
            self.current_state.black_pieces_count = self.current_state.black_pieces_count - 1
        elif current_player_color == BLACK_PIECE_COLOR:
            self.current_state.white_pieces_count = self.current_state.white_pieces_count - 1        


    # Evaluates board to detect insufficient material. If this happens then the game ends with a draw.
    # returns True if there is insufficient mating material: K vs K, K vs K+B, K vs K+Kn
    # returns False if there is sufficient mating position (all other cases)
    # TODO: there is one more case of insufficient material: king and bishop versus king and bishop with the bishops on the same color.
    def check_insufficient_mating_material(self):
        if self.current_state.black_pieces_count == 1 and self.current_state.white_pieces_count == 1:
            print(f"Draw! Insufficient mating material (K vs K)!")
            return True
        elif self.current_state.black_pieces_count == 1 and self.current_state.white_pieces_count == 2:
            for row in range(ROWS):
                for col in range(COLS):
                    if self.squares[row][col].has_team_piece(WHITE_PIECE_COLOR):
                        if isinstance(self.squares[row][col].piece, Bishop) or isinstance(self.squares[row][col].piece, Knight):
                            print(f"Draw! Insufficient mating material (K vs K+B or K vs K+Kn)!") 
                            return True
        elif self.current_state.black_pieces_count == 2 and self.current_state.white_pieces_count == 1:
            for row in range(ROWS):
                for col in range(COLS):
                    if self.squares[row][col].has_team_piece(BLACK_PIECE_COLOR):
                        if isinstance(self.squares[row][col].piece, Bishop) or isinstance(self.squares[row][col].piece, Knight):
                            print(f"Draw! Insufficient mating material (K vs K+B or K vs K+Kn)!") 
                            return True
        else:
            return False

        return False
        

    # Evaluates if there are no valid moves for all pieces of given color
    # Sets value of no_valid_moves member variable:
    # True if there is no valid moves for all pieces of 'color' color
    # False if any piece of 'color' color has a valid move
    def player_has_no_valid_moves(self, color: int):
        for row in range(ROWS):
            for col in range(COLS):
                if self.squares[row][col].has_team_piece(color):
                    
                    #piece=copy.deepcopy(self.squares[row][col].piece)
                    piece=self.squares[row][col].piece  
                    tmp_moves = copy.deepcopy(piece.moves)
                    piece.clear_moves()
                    self.calc_moves(piece, row, col)
                    if piece.moves != []:
                        #print(f"Piece on {Square.get_alphacol(col)}{ROWS - row} can move, player {color} has valid moves.")
                        piece.moves=tmp_moves  
                        return False
                    else:
                        piece.moves=tmp_moves
                        
        print(f"Player {color_name(color)} has no valid moves!")
        return True

    # Evaluates if a piece on a sqare [row][col] is giving check in a straight line to the King of 'color' color 
    # Used for Bishop, Rook and Queen pieces in is_king_checked() method
    # Returns:
    # True if check detected
    # False if no check detected
    def straightline_checks(self, row: int, col: int, color: int, check_directions: List[Tuple]) -> bool:
        for check_direction in check_directions:
            row_incr, col_incr = check_direction
            possible_move_row = row + row_incr
            possible_move_col = col + col_incr
            while True:
                if Square.in_range(possible_move_row, possible_move_col):
                    # empty square -> continue checking squares in this direction
                    if self.squares[possible_move_row][possible_move_col].isempty():
                    # if is_empty(self.squares_fast_method[possible_move_row][possible_move_col]): # OPTIMIZATION
                        pass
                    # square with King of other color found -> signal check                   
                    elif isinstance(self.squares[possible_move_row][possible_move_col].piece, King) and self.squares[possible_move_row][possible_move_col].has_team_piece(color):
                            # print(f"{self.squares[row][col].piece.name} on {Square.get_alphacol(col)}{ROWS - row} is checking the {color} King!")
                            return True
                    # any other piece found, stop checking next squares in this direction
                    else:
                        break
                # square not on board, break the loop
                else: 
                    break
                # incrementing incrs
                possible_move_row = possible_move_row + row_incr
                possible_move_col = possible_move_col + col_incr
        return False


    # Evaluates current board position for actual checks.
    # Returns:
    # True if King of color 'color' is being checked (as of current board position)
    # False otherwise
    def is_king_checked(self, color: int):
        for row in range(ROWS):
            for col in range(COLS):
                if self.squares[row][col].has_enemy_piece(color): # if piece of opposite color found then evaluate if this piece is checking the King
                    piece = self.squares[row][col].piece

                    # is checked by a Pawn?
                    if isinstance(piece, Pawn):
                        check_row = row + 1 if color == WHITE_PIECE_COLOR else row - 1
                        # check if King can be 'captured' by a pawn
                        if Square.in_range(row+1, col+1):
                            if isinstance(self.squares[check_row][col+1].piece, King):
                                if self.squares[check_row][col+1].has_team_piece(color):
                                    #print(f"Pawn on {Square.get_alphacol(col)}{ROWS - row} is checking the {color} King!")
                                    return True
                        if Square.in_range(row+1, col-1):
                            if isinstance(self.squares[check_row][col-1].piece, King): 
                                if self.squares[check_row][col-1].has_team_piece(color):  
                                    #print(f"Pawn on {Square.get_alphacol(col)}{ROWS - row} is checking the {color} King!")
                                    return True
                                
                    # is checked by Knight?
                    elif isinstance(piece, Knight):
                        possible_knight_checks = [
                            (row-2, col+1),
                            (row-1, col+2),
                            (row+1, col+2),
                            (row+2, col+1),
                            (row+2, col-1),
                            (row+1, col-2),
                            (row-1, col-2),
                            (row-2, col-1),
                        ]
                        for possible_knight_check in possible_knight_checks:
                            check_row, check_col = possible_knight_check
                            if Square.in_range(check_row, check_col):
                                if isinstance(self.squares[check_row][check_col].piece, King):
                                    if self.squares[check_row][check_col].has_team_piece(color):
                                        #print(f"Knight on {Square.get_alphacol(col)}{ROWS - row} is checking the {color} King!")
                                        return True

                                
                    # is checked by a Bishop?
                    elif isinstance(piece, Bishop):
                        possible_bishop_check_directions = [(-1, 1), (-1, -1), (1, -1), (1, 1)]
                        if self.straightline_checks(row, col, color, possible_bishop_check_directions) == True:
                            return True
                                    
                                    
                    # is checked by a Rook?
                    elif isinstance(piece, Rook):
                        possible_rook_check_directions = [(-1,0), (0, -1), (0, 1), (1, 0)]
                        if self.straightline_checks(row, col, color, possible_rook_check_directions) == True:
                            return True

                    # is checked by a Queen?
                    elif isinstance(piece, Queen):
                        possible_queen_check_directions = [(-1, 1), (-1, -1), (1, -1), (1, 1), (-1,0), (0, -1), (0, 1), (1, 0)]
                        if self.straightline_checks(row, col, color, possible_queen_check_directions) == True:
                            return True
                        
                    # King cannot be checked by King of opposite color
                    else:
                        pass

        # if no checks found, return False
        return False

    # Check if a King of oppostie color is in adjacent square.
    # This method is needed to prevent two Kings of opposite color to occupy adjacent squares. 
    # Returns:
    # True if King of opposite color is on adjacent square
    # False otherwise
    def opposite_king_on_adjacent_square(self, row: int, col: int, color: int):
        adjacent_squares = [
            (row-1, col-1),
            (row-1, col),
            (row-1, col+1),
            (row, col-1),
            (row, col+1),
            (row+1, col-1),
            (row+1, col),
            (row+1, col+1),
        ]
        for adjacent_square in adjacent_squares:
            adjacent_square_row, adjacent_square_col = adjacent_square
            if Square.in_range(adjacent_square_row, adjacent_square_col):        
                if self.squares[adjacent_square_row][adjacent_square_col].has_enemy_piece(color):
                    if isinstance(self.squares[adjacent_square_row][adjacent_square_col].piece, King):
                        #print(f"Moving {color_name(color)} King at {Square.get_alphacol(col)}{ROWS - row} close to a King of opposite color at {Square.get_alphacol(adjacent_square_col)}{ROWS - adjacent_square_row} is not allowed.")
                        return True
        return False

    # Returns score of the current board position
    def calculate_piece_score(self) -> float:
        score = 0
        for col in range(COLS):
            for row in range(ROWS):
                if is_piece(self.squares_fast_method[row][col]): # OPTIMIZATION
                #if self.squares[row][col].has_piece():
                    piece = self.squares[row][col].piece
                    score += piece.value
        return score


    def calc_moves(self, piece: Piece, row: int, col: int, move_the_piece: bool = False):
        ''' 
            Calculate all the possible (valid) moves of a specific piece on a specific position
            move_the_piece == True means we are also moving a piece
            move_the_piece == False means we will just calculate the piece but don't move it
        '''
        
        
        def pawn_moves():
            # get possible number of squares to move forward
            steps = 1 if piece.moved else 2

            # vertical moves - 'dir' is a member of only Pawn piece!
            start = row + piece.dir
            end = row + (piece.dir * (1 + steps)) # end is one more because for loop doesn't iterate for end value of range
            # this loop will iterate over from start to end-1 iteration
            for possible_move_row in range(start, end, piece.dir):
                if Square.in_range(possible_move_row):
                    # if self.squares[possible_move_row][col].isempty():
                    if is_empty(self.squares_fast_method[possible_move_row][col]): # OPTIMIZATION
                        # create initial and finam move squares
                        initial = Square(row, col)
                        final = Square(possible_move_row, col)
                        # create a new move
                        move = Move(initial, final)
                        
                        #  see if there are potential checks uncovered by the move
                        if not self.in_check(piece, move):
                            piece.add_move(move)
                          
                    else: # this means we are blocked
                        break
                else: # not in range
                    break
            
            # diagonal moves
            possible_move_row = row + piece.dir
            possible_move_cols = [col-1, col+1]
            for possible_move_col in possible_move_cols:
                if Square.in_range(possible_move_row, possible_move_col):
                    if self.squares[possible_move_row][possible_move_col].has_enemy_piece(piece.color):
                    # if has_enemy_piece(self.squares_fast_method[possible_move_row][possible_move_col], piece.color): # OPTIMIZATION
                        # create initial and finam move squares
                        initial = Square(row, col)
                        final_piece = self.squares[possible_move_row][possible_move_col].piece
                        final = Square(possible_move_row, possible_move_col, final_piece)
                        # create a new move
                        move = Move(initial, final)
                        
                        #  see if there are potential checks
                        if not self.in_check(piece, move):
                            piece.add_move(move)


            # en passant moves
            r = 3 if piece.color == WHITE_PIECE_COLOR else 4 # assign a row where this type of move may happen
            fr = 2 if piece.color == WHITE_PIECE_COLOR else 5  # final row
            # left en passant
            if Square.in_range(col-1) and row == r: 
                if self.squares[row][col-1].has_enemy_piece(piece.color): # check for enemy piece left to the pawn
                # if has_enemy_piece(self.squares_fast_method[row][col-1], piece.color): # OPTIMIZATION
                    p = self.squares[row][col-1].piece # p = enemy piece
                    if isinstance(p, Pawn): # if enemy piece is pawn
                        if p.en_passant: # if enemy piece is in en passant state

                            #print(f"Pawn on row {row}, col {col} is in en-passant state")
                            # create initial and finam move squares
                            initial = Square(row, col)
                            final = Square(fr, col-1, p)
                            # create a new move
                            move = Move(initial, final)
                            
                            #  see if there are potential checks
                            if not self.in_check(piece, move):
                                piece.add_move(move)

            # right en passant
            if Square.in_range(col+1) and row == r: 
                if self.squares[row][col+1].has_enemy_piece(piece.color): # check for enemy piece left to the pawn
                #if has_enemy_piece(self.squares_fast_method[row][col+1], piece.color): # OPTIMIZATION
                    p = self.squares[row][col+1].piece # p = enemy piece
                    if isinstance(p, Pawn): # if enemy piece is pawn
                        if p.en_passant: # if enemy piece is in en passant state
                            #print(f"Pawn on row {row}, col {col} is in en-passant state")                                
                            # create initial and finam move squares
                            initial = Square(row, col)
                            final = Square(fr, col+1, p)
                            # create a new move
                            move = Move(initial, final)
                            
                            #  see if there are potential checks
                            if not self.in_check(piece, move):
                                piece.add_move(move)



        def knight_moves():
            # 8 possible moves
            possible_moves = [
                (row-2, col+1),
                (row-1, col+2),
                (row+1, col+2),
                (row+2, col+1),
                (row+2, col-1),
                (row+1, col-2),
                (row-1, col-2),
                (row-2, col-1),
            ]
            for possible_move in possible_moves:
                possible_move_row, possible_move_col = possible_move
                if Square.in_range(possible_move_row, possible_move_col):
                    # check if it is empty or if it is of rival color
                    if self.squares[possible_move_row][possible_move_col].isempty_or_enemy(piece.color):
                        # FIXED BUG: Piece cannot 'capture' enemy King!
                        if not isinstance(self.squares[possible_move_row][possible_move_col].piece, King):
                            # create squares of a new move
                            initial = Square(row, col)
                            final_piece = self.squares[possible_move_row][possible_move_col].piece
                            final = Square(possible_move_row, possible_move_col, final_piece)
                            # create a new move
                            move=Move(initial, final)
                            # append a new valid move
                            
                            #  see if there are potential checks
                            if not self.in_check(piece, move):
                                piece.add_move(move)
                            #else: break # <- FIXED BUG: This line prevented the Knight piece to make valid moves

        def straightline_moves(incrs: List[Tuple]):
            for incr in incrs:
                row_incr, col_incr = incr
                possible_move_row = row + row_incr
                possible_move_col = col + col_incr
                
                while True:
                    if Square.in_range(possible_move_row, possible_move_col):
                        # create squares of the possible new move
                        initial = Square(row, col)
                        final_piece = self.squares[possible_move_row][possible_move_col].piece
                        final = Square(possible_move_row, possible_move_col, final_piece)
                        # create a possible new move
                        move = Move(initial, final)
        
                        # empty
                        if self.squares[possible_move_row][possible_move_col].isempty():
                        #if is_empty(self.squares_fast_method[possible_move_row][possible_move_col]): # OPTIMIZATION
                            # append new move
                            #  see if there are potential checks
                            if not self.in_check(piece, move):
                                piece.add_move(move)
                            
                        # has enemy piece, so add a move but break (this is the furthest move in this direction)
                        elif self.squares[possible_move_row][possible_move_col].has_enemy_piece(piece.color):
                        # elif has_enemy_piece(self.squares_fast_method[possible_move_row][possible_move_col], piece.color): # OPTIMIZATION
                            # append new move
                            #  see if there are potential checks
                            # FIXED BUG: Piece cannot 'capture' enemy King!
                            if not isinstance(self.squares[possible_move_row][possible_move_col].piece, King):
                                if not self.in_check(piece, move):
                                    piece.add_move(move)
                                break
                        
                        # has friendly piece
                        elif self.squares[possible_move_row][possible_move_col].has_team_piece(piece.color):
                            break
                    # not in range
                    else:
                        break            
                    # incrementing incrs
                    possible_move_row = possible_move_row + row_incr
                    possible_move_col = possible_move_col + col_incr

        def king_moves():
            # 8 possible moves
            possible_moves = [
                (row-1, col-1),
                (row-1, col),
                (row-1, col+1),
                (row, col-1),
                (row, col+1),
                (row+1, col-1),
                (row+1, col),
                (row+1, col+1),
            ]
            
            # normal moves
            for possible_move in possible_moves:
                possible_move_row, possible_move_col = possible_move
                if Square.in_range(possible_move_row, possible_move_col):
                    # check if it is empty or if it is of rival color
                    if self.squares[possible_move_row][possible_move_col].isempty_or_enemy(piece.color):
                        # FIXED BUG: Moving King next to opposite King is not allowed!
                        if not self.opposite_king_on_adjacent_square(possible_move_row, possible_move_col, piece.color):
                            # create squares of a new move
                            initial = Square(row, col)
                            final = Square(possible_move_row, possible_move_col) # piece = piece
                            # create a new move
                            move=Move(initial, final)
                            # append a new valid move
                            #  see if there are potential checks
                            if not self.in_check(piece, move):
                                piece.add_move(move)
                            #else: break # <- FIXED BUG: This line prevented the King piece to make valid moves



            # castling moves
            if not piece.moved:
                # queenside castling
                left_rook = self.squares[row][0].piece
                #print(f"! left_rook: {left_rook.name} {left_rook.color} moved? {left_rook.moved}") 
                if isinstance(left_rook, Rook):
                    if not left_rook.moved:
                        for c in range(1,4):
                            if self.squares[row][c].has_piece():
                                break
                            if c == 3:
                                piece.left_rook = left_rook
                                # rook move
                                initial = Square(row, 0)
                                final = Square(row, 3)
                                moveRook = Move(initial, final)

                                # king move
                                initial = Square(row, col)
                                final = Square(row, 2)
                                moveKing = Move(initial, final)
                                
                                #  see if there are potential checks
                                if not self.in_check(piece, moveKing):
                                    if not self.in_check(left_rook, moveRook):
                                        left_rook.add_move(moveRook)
                                        piece.add_move(moveKing)



                                                                
                # kingside castling
                right_rook = self.squares[row][7].piece
                if isinstance(right_rook, Rook):
                    if not right_rook.moved:
                        for c in range(5, 7):
                            if self.squares[row][c].has_piece():
                                break
                            if c == 6:
                                piece.right_rook = right_rook
                                # rook move
                                initial = Square(row, 7)
                                final = Square(row, 5)
                                moveRook = Move(initial, final)
                                # king move
                                initial = Square(row, col)
                                final = Square(row, 6)
                                moveKing = Move(initial, final)
                
                                #  see if there are potential checks
                                if not self.in_check(piece, moveKing):
                                    if not self.in_check(right_rook, moveRook):
                                        right_rook.add_move(moveRook)
                                        piece.add_move(moveKing)
      
        #print(f"performing calc_moves for {color_name(piece.color)} {piece.name}.")
        if isinstance(piece, Pawn): 
            pawn_moves()
        elif isinstance(piece, Knight): 
            knight_moves()
        elif isinstance(piece, Bishop): 
            straightline_moves([(-1, 1), (-1, -1), (1, -1), (1, 1)])
        elif isinstance(piece, Rook): 
            straightline_moves([(-1,0), (0, -1), (0, 1), (1, 0)])
        elif isinstance(piece, Queen): 
            straightline_moves([(-1, 1), (-1, -1), (1, -1), (1, 1), (-1,0), (0, -1), (0, 1), (1, 0)])
        elif isinstance(piece, King): 
            king_moves()
        
        
    def _create(self):
        for row in range(ROWS):
            for col in range(COLS):
                self.squares[row][col] = Square(row, col)


    def _add_pieces(self, color: int, board_position: str = 'standard'):
        if board_position == 'standard':
            self._add_pieces_standard(color)
        elif board_position == 'checkmate':
            self._add_pieces_checkmate(color)
        elif board_position == 'stalemate':
            self._add_pieces_stalemate(color)
        elif board_position == 'insufficient_material':
            self._add_pieces_insufficient_material(color)
            

    ########################################################################
    # Methods for placing pieces at initial positions (different scenarios)
            
    def _add_pieces_standard(self, color: int):
        if color == WHITE_PIECE_COLOR:
            row_pawn, row_other = (6, 7)
            color_encoding = WHITE_PIECE_COLOR
        else:
            row_pawn, row_other = (1, 0)
            color_encoding = BLACK_PIECE_COLOR

        # putting Pawns on board
        for col in range(COLS):
            self.squares[row_pawn][col] = Square(row_pawn, col, Pawn(color))
            self.squares_fast_method[row_pawn][col] = PAWN_PIECE | color_encoding
        # Knights
        self.squares[row_other][1] = Square(row_other, 1, Knight(color))
        self.squares[row_other][6] = Square(row_other, 6, Knight(color))
        self.squares_fast_method[row_other][1] = KNIGHT_PIECE | color_encoding
        self.squares_fast_method[row_other][6] = KNIGHT_PIECE | color_encoding

        # Bishop
        self.squares[row_other][2] = Square(row_other, 2, Bishop(color))
        self.squares[row_other][5] = Square(row_other, 5, Bishop(color))
        self.squares_fast_method[row_other][2] = BISHOP_PIECE | color_encoding
        self.squares_fast_method[row_other][5] = BISHOP_PIECE | color_encoding

        # Rook
        self.squares[row_other][0] = Square(row_other, 0, Rook(color))
        self.squares[row_other][7] = Square(row_other, 7, Rook(color))
        self.squares_fast_method[row_other][0] = ROOK_PIECE | color_encoding
        self.squares_fast_method[row_other][7] = ROOK_PIECE | color_encoding

        # Queen and King
        self.squares[row_other][3] = Square(row_other, 3, Queen(color))
        self.squares[row_other][4] = Square(row_other, 4, King(color))
        self.squares_fast_method[row_other][3] = QUEEN_PIECE | color_encoding
        self.squares_fast_method[row_other][4] = KING_PIECE | color_encoding


    def _add_pieces_checkmate(self, color: int):
        if color == WHITE_PIECE_COLOR:
            row_pawn, row_other = (6, 7)
            self.squares[0][0] = Square(0, 0, Queen(color))
            self.squares[1][0] = Square(1, 0, Queen(color))
            self.squares_fast_method[0][0] = QUEEN_PIECE | WHITE_PIECE_COLOR
            self.squares_fast_method[1][0] = KING_PIECE | WHITE_PIECE_COLOR
        else:
            row_pawn, row_other = (1, 0)
            self.squares[row_other][4] = Square(row_other, 4, King(color))
            self.squares_fast_method[row_other][4] = KING_PIECE | BLACK_PIECE_COLOR
        self.current_state.white_pieces_count = 2
        self.current_state.black_pieces_count = 1 

    def _add_pieces_stalemate(self, color: int):
        if color == WHITE_PIECE_COLOR:
            self.squares[2][3] = Square(2, 3, Queen(color))
            self.squares[2][0] = Square(2, 0, King(color))
            self.squares_fast_method[2][3] = QUEEN_PIECE | WHITE_PIECE_COLOR
            self.squares_fast_method[2][0] = KING_PIECE | WHITE_PIECE_COLOR
        else:
            self.squares[0][1] = Square(0, 1, King(color))
            self.squares_fast_method[0][1] = KING_PIECE | BLACK_PIECE_COLOR
        self.current_state.white_pieces_count = 2
        self.current_state.black_pieces_count = 1 

    def _add_pieces_insufficient_material(self, color: int): # King + Knight vs King
        if color == WHITE_PIECE_COLOR:
            row_pawn, row_other = (6, 7)
            self.squares[row_other][1] = Square(row_other, 1, Knight(color))
            self.squares[row_other][4] = Square(row_other, 4, King(color))            
            self.squares_fast_method[row_other][1] = KNIGHT_PIECE | WHITE_PIECE_COLOR
            self.squares_fast_method[row_other][4] = KING_PIECE | WHITE_PIECE_COLOR
        else:
            row_pawn, row_other = (1, 0)
            self.squares[row_other][4] = Square(row_other, 4, King(color))
            self.squares_fast_method[row_other][4] = KING_PIECE | BLACK_PIECE_COLOR
        self.current_state.white_pieces_count = 2
        self.current_state.black_pieces_count = 1      

    #########################
    # DEBUG METHODS

    # show list of all moves made so far on the board
    def show_moves_history(self):
        for i, current_move in enumerate(self.moves_history):
            piece, move_coordinates = current_move 
            move_coordinates.show(piece.name, piece.color + " " + str((i // 2) + 1))

    # show board-related counters
    def show_move_counters(self):
        print(f"Move no: {self.current_state.move_count}.")
        print(f"Pawn last moved on move no: {self.current_state.last_move_when_pawn_moved}.")
        print(f"Piece last captured on move no: {self.current_state.last_move_when_piece_captured}.")

    # show number of black and white pieces currently on the board
    def show_pieces_count(self):
        print(f"White pieces count: {self.current_state.white_pieces_count}. Black pieces count {self.current_state.black_pieces_count}")
    


    # get board position of a Pawn which can be captured en-passant in current move
    def get_en_passant_pawn_position(self):
        for row in range(ROWS):
            for col in range(COLS):
                if isinstance(self.squares[row][col].piece, Pawn):
                    if self.squares[row][col].piece.en_passant == True:
                        #print(f"En Passant pawn is on {Square.get_alphacol(col)}{ROWS-row}")
                        return row, col
        return 0, 0 # if not found
    
    def get_pieces_not_moved_yet(self):
        rows = []
        cols = []
        for row in range(ROWS):
            for col in range(COLS):
                if self.squares[row][col].piece:
                    if self.squares[row][col].piece.moved == False:
                        rows.append(row)
                        cols.append(col)
        return rows, cols
