from const import *
from piece import *
from typing import List, Tuple
from move import Move
from square import Square
from sound import Sound
import copy
import os

class Board:
    def __init__(self):
        self.squares: List[List[Square]]= [[0, 0, 0, 0, 0, 0, 0, 0] for col in range(COLS)]
        self.last_move: Move = None
        self._create()
        self._add_pieces('white')
        self._add_pieces('black')
        self.player_under_check = False # only one player can be under check at a given moment and it happens before his/her turn
        self.white_pieces_count = 16 # initial number of white pieces
        self.black_pieces_count = 16 # initial number of black pieces
        self.move_count = 1 # Counter for game moves. 1 is initial move number
        self.last_move_when_pawn_moved = 0 # Stores game move number when pawn was last moved. Will be set to move_count value when any Pawn will move.
        self.last_move_when_piece_captured = 0 # Stores game move number when a piece was last moved. Will be set to move_count when any piece will be captured.
        self.moves_history: List[Tuple[Piece, Move]] = [] # this list records all game moves (a single sequence of all white and black moves as they were played) 

    # This method actually makes a move 'move' for a piece 'piece' on the board
    # if testing == True then operation is performed on a temporary board to evaluate checks 
    # if testing == False then operation is performed on actual board. This is the default mode.
    
    def move(self, piece: Piece, move: Move, testing: bool = False):
        initial = move.initial
        final = move.final

        en_passant_empty = self.squares[final.row][final.col].isempty()
        
        # standard board update for the 'move'
        self.squares[initial.row][initial.col].piece = None
        self.squares[final.row][final.col].piece = piece

        # NEW CODE: increase 'last_move_when_pawn_moved' counter
        if isinstance(piece, Pawn):            
            self.last_move_when_pawn_moved = self.move_count
            
        # en passant capture
        if isinstance(piece, Pawn):
            diff = final.col - initial.col 
            if diff != 0 and en_passant_empty:
                self.squares[initial.row][initial.col + diff].piece = None
                self.squares[final.row][final.col].piece = piece
                self.update_pieces_count(piece.color) # NEW CODE: decrease piece counter in case of en passant capture
              
                if not testing:
                    sound = Sound(os.path.join('assets/sounds/capture.wav'))
                    sound.play()
                    # NEW CODE: increase 'last_move_when_piece_captured' counter
                    self.last_move_when_piece_captured = self.move_count


        # Pawn promotion to a Queen
        if (final.row == 7 or final.row == 0) and isinstance(piece, Pawn):  
            self.squares[final.row][final.col].piece = Queen(piece.color)


        # King castling - since King's move is coded above as standard move, now only move the Rook
        if isinstance(piece, King):
            if self.castling(initial, final) and not testing:
                diff = final.col - initial.col
                rook = piece.left_rook if (diff < 0) else piece.right_rook
                #rook.show_moves_debug("castling")
                self.move(rook, rook.moves[-1]) # recursion!


        # move
        piece.moved = True
        
        # clear valid moves
        piece.clear_moves()
        # set last move
        self.last_move = move
        
    # check if a piece move is a valid move on the board
    def valid_move(self, piece: Piece, move: Move):
        return move in piece.moves

    # check if king's move spans 2 columns as in castling 
    def castling(self, initial, final):
        return abs(initial.col - final.col) == 2

    # check for all pawns and set their en_passant state to False if they were not moved in the last move
    def set_true_en_passant(self, piece):
        if not isinstance(piece, Pawn):
            return
        
        for row in range(ROWS):
            for col in range(COLS):
                if isinstance(self.squares[row][col].piece, Pawn):
                    self.squares[row][col].piece.en_passant = False

        piece.en_passant = True
                    

    # verify if the move of the piece will trigger a check
    def in_check(self, piece: Piece, move: Move, testing = True):
        temp_piece = copy.deepcopy(piece)
        temp_board = copy.deepcopy(self)
        temp_board.move(temp_piece, move, testing = testing) # simulate the move
        # in the loop check if the above move will trigger the check condition!
        for row in range(ROWS):
            for col in range(COLS):
                if temp_board.squares[row][col].has_enemy_piece(piece.color):
                    p = temp_board.squares[row][col].piece # get object for each enemy piece 'p'
                    temp_board.calc_moves(p, row, col, move_the_piece = False)
                    for m in p.moves:
                        if isinstance(m.final.piece, King): # if enemy piece attacks King of opposite color -> signal a check
                            return True # check condition triggered

        return False


    # NEW METHOD!
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

    # NEW METHOD!
    def show_moves_history(self):
        for i, current_move in enumerate(self.moves_history):
            piece, move_coordinates = current_move 
            move_coordinates.show(piece.name, piece.color + " " + str((i // 2) + 1))
            
    # NEW METHOD!
    def show_move_counters(self):
        print(f"Game move no: {self.move_count}.")
        print(f"Pawn last moved on move no: {self.last_move_when_pawn_moved}.")
        print(f"Piece last captured on move no: {self.last_move_when_piece_captured}.")

    # NEW METHOD!
    # Returns True if game has reached 50 move rule which leads to game draw. 
    # NOTE. Using > comparison as move count is increased before checking this rule
    def check_fifty_move_rule(self, limit_moves_count: int = 50):
        if self.move_count - self.last_move_when_pawn_moved > limit_moves_count and self.move_count - self.last_move_when_piece_captured > limit_moves_count:
            return True
        else:
            return False
        
                
    # NEW METHOD!
    # Decreases one of piece counters after a move when a piece was captured.
    def update_pieces_count(self, current_player_color: str):
        if current_player_color == 'white':
            self.black_pieces_count = self.black_pieces_count - 1
        elif current_player_color == 'black':
            self.white_pieces_count = self.white_pieces_count - 1        

    # NEW METHOD!
    def show_pieces_count(self):
        print(f"White pieces count: {self.white_pieces_count}. Black pieces count {self.black_pieces_count}")


    # NEW METHOD!
    # Evaluates board to detect insufficient material. If this happens then the game ends with a draw.
    # returns True if there is insufficient mating material: K vs K, K vs K+B, K vs K+Kn
    # returns False if there is sufficient mating position (all other cases)
    # TODO: there is one more case of insufficient material: king and bishop versus king and bishop with the bishops on the same color.
    def check_insufficient_mating_material(self):
        if self.black_pieces_count == 1 and self.white_pieces_count == 1:
            print(f"Draw! Insufficient mating material (K vs K)!")            
            return True
        elif self.black_pieces_count == 1 and self.white_pieces_count == 2:
            for row in range(ROWS):
                for col in range(COLS):
                    if self.squares[row][col].has_team_piece('white'):
                        if isinstance(self.squares[row][col].piece, Bishop) or isinstance(self.squares[row][col].piece, Knight):
                            print(f"Draw! Insufficient mating material (K vs K+B or K vs K+Kn)!") 
                            return True
        elif self.black_pieces_count == 2 and self.white_pieces_count == 1:        
            for row in range(ROWS):
                for col in range(COLS):
                    if self.squares[row][col].has_team_piece('black'):                        
                        if isinstance(self.squares[row][col].piece, Bishop) or isinstance(self.squares[row][col].piece, Knight):
                            print(f"Draw! Insufficient mating material (K vs K+B or K vs K+Kn)!") 
                            return True
        else:
            return False

        return False
        
        
        
    # NEW METHOD!
    # Evaluates if there are no moves for all pieces of given color
    # Returns:
    # True if there is no valid moves for all pieces of 'color' color
    # False if any piece of 'color' color has a valid move
    def player_has_no_valid_moves(self, color: str):
        for row in range(ROWS):
            for col in range(COLS):
                if self.squares[row][col].has_team_piece(color):
                    self.squares[row][col].piece.clear_moves()
                    self.calc_moves(self.squares[row][col].piece, row, col, move_the_piece=True)
                    if self.squares[row][col].piece.moves != []:
                        #print(f"Piece on {Square.get_alphacol(col)}{ROWS - row} can move, player {color} has valid moves.")
                        return False
        print(f"Player {color} has no valid moves!")
        return True

    # NEW METHOD!
    # Evaluates if a piece on a sqare [row][col] is giving check in a straight line to the King of 'color' color 
    # Used for Bishop, Rook and Queen pieces in is_king_checked() method
    # Returns:
    # True if check detected
    # False if no check detected
    def straightline_checks(self, row: int, col: int, color: str, check_directions: List[Tuple]) -> bool:
        for check_direction in check_directions:
            row_incr, col_incr = check_direction
            possible_move_row = row + row_incr
            possible_move_col = col + col_incr
            while True:
                if Square.in_range(possible_move_row, possible_move_col):
                    # empty square -> continue checking squares in this direction
                    if self.squares[possible_move_row][possible_move_col].isempty():
                        pass
                    # square with King of other color found -> signal check                   
                    elif isinstance(self.squares[possible_move_row][possible_move_col].piece, King) and self.squares[possible_move_row][possible_move_col].has_team_piece(color):
                        print(f"{self.squares[row][col].piece.name} on {Square.get_alphacol(col)}{ROWS - row} is checking the {color} King!")
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



    
    # NEW METHOD!
    # Evaluates current board position for actual checks.
    # Returns:
    # True if King of color 'color' is being checked (as of current board position)
    # False otherwise
    def is_king_checked(self, color: str):
        for row in range(ROWS):
            for col in range(COLS):
                if self.squares[row][col].has_enemy_piece(color): # if piece of opposite color found then evaluate if this piece is checking the King
                    piece = self.squares[row][col].piece

                    # is checked by a Pawn?
                    if isinstance(piece, Pawn):
                        check_row = row + 1 if color == 'white' else row - 1
                        # check if King can be 'captured' by a pawn
                        if Square.in_range(row+1, col+1):
                            if isinstance(self.squares[check_row][col+1].piece, King) and self.squares[check_row][col+1].has_team_piece(color):
                                print(f"Pawn on {Square.get_alphacol(col)}{ROWS - row} is checking the {color} King!")
                                return True
                        if Square.in_range(row+1, col-1):
                            if isinstance(self.squares[check_row][col-1].piece, King) and self.squares[check_row][col-1].has_team_piece(color):
                                print(f"Pawn on {Square.get_alphacol(col)}{ROWS - row} is checking the {color} King!")
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
                                if isinstance(self.squares[check_row][check_col].piece, King) and self.squares[check_row][check_col].has_team_piece(color):
                                    print(f"Knight on {Square.get_alphacol(col)}{ROWS - row} is checking the {color} King!")
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

    # NEW METHOD!
    # Check if a King of oppostie color is in adjacent square.
    # This method is needed to prevent two Kings of opposite color to occupy adjacent squares. 
    # Returns:
    # True if King of opposite color is on adjacent square
    # False otherwise
    def opposite_king_on_adjacent_square(self, row: int, col: int, color: str):
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
                if self.squares[adjacent_square_row][adjacent_square_col].has_enemy_piece(color) and isinstance(self.squares[adjacent_square_row][adjacent_square_col].piece, King):
                    #print(f"Moving {color} King at {Square.get_alphacol(col)}{ROWS - row} close to a King of opposite color at {Square.get_alphacol(adjacent_square_col)}{ROWS - adjacent_square_row} is not allowed.")
                    return True
        return False

    def calc_moves(self, piece: Piece, row: int, col: int, move_the_piece: bool =True):
        ''' 
            Calculate all the possible (valid) moves of a specific piece on a specific position
            move_the_piece == True means we are also moving a piece
            move_the_piece == False means we will just calculate the piece bud don't move it
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
                    if self.squares[possible_move_row][col].isempty():
                        # create initial and finam move squares
                        initial = Square(row, col)
                        final = Square(possible_move_row, col)
                        # create a new move
                        move = Move(initial, final)
                        
                        #  see if there are potential checks
                        if move_the_piece: # with this line we avoid recursively invoking in_check() and calc_moves() method
                            if not self.in_check(piece, move):
                                piece.add_move(move)
                        else:
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
                        # create initial and finam move squares
                        initial = Square(row, col)
                        final_piece = self.squares[possible_move_row][possible_move_col].piece
                        final = Square(possible_move_row, possible_move_col, final_piece)
                        # create a new move
                        move = Move(initial, final)
                        
                        #  see if there are potential checks
                        if move_the_piece: # with this line we avoid recursively invoking in_check() and calc_moves() method
                            if not self.in_check(piece, move):
                                piece.add_move(move)
                        else:
                            piece.add_move(move)

            # en passant moves
            r = 3 if piece.color == 'white' else 4 # assign a row where this type of move may happen
            fr = 2 if piece.color == 'white' else 5  # final row
            # left en passant
            if Square.in_range(col-1) and row == r: 
                if self.squares[row][col-1].has_enemy_piece(piece.color): # check for enemy piece left to the pawn
                    p = self.squares[row][col-1].piece # p = enemy piece
                    if isinstance(p, Pawn): # if enemy piece is pawn
                            if p.en_passant: # if enemy piece is in en passant state
                                # create initial and finam move squares
                                initial = Square(row, col)
                                final = Square(fr, col-1, p)
                                # create a new move
                                move = Move(initial, final)
                                
                                #  see if there are potential checks
                                if move_the_piece: # with this line we avoid recursively invoking in_check() and calc_moves() method
                                    if not self.in_check(piece, move):
                                        piece.add_move(move)
                                else:
                                    piece.add_move(move)
            # right en passant
            if Square.in_range(col+1) and row == r: 
                if self.squares[row][col+1].has_enemy_piece(piece.color): # check for enemy piece left to the pawn
                    p = self.squares[row][col+1].piece # p = enemy piece
                    if isinstance(p, Pawn): # if enemy piece is pawn
                            if p.en_passant: # if enemy piece is in en passant state
                                # create initial and finam move squares
                                initial = Square(row, col)
                                final = Square(fr, col+1, p)
                                # create a new move
                                move = Move(initial, final)
                                
                                #  see if there are potential checks
                                if move_the_piece: # with this line we avoid recursively invoking in_check() and calc_moves() method
                                    if not self.in_check(piece, move):
                                        piece.add_move(move)
                                else:
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
                        # create squares of a new move
                        initial = Square(row, col)
                        final_piece = self.squares[possible_move_row][possible_move_col].piece
                        final = Square(possible_move_row, possible_move_col, final_piece)
                        # create a new move
                        move=Move(initial, final)
                        # append a new valid move
                        
                        #  see if there are potential checks
                        if move_the_piece: # with this line we avoid recursively invoking in_check() and calc_moves() method
                            if not self.in_check(piece, move):
                                piece.add_move(move)
                            #else: break # <- FIXED BUG: This line prevented the Knight piece to make valid moves
                        else:
                            piece.add_move(move)


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
                            # append new move
                            #  see if there are potential checks
                            if move_the_piece: # with this line we avoid recursively invoking in_check() and calc_moves() method
                                if not self.in_check(piece, move):
                                    piece.add_move(move)
                            else:
                                piece.add_move(move)
                            
                        # has enemy piece, so add a move but break (this is the furthest move in this direction)
                        elif self.squares[possible_move_row][possible_move_col].has_enemy_piece(piece.color):
                            # append new move
                            #  see if there are potential checks
                            if move_the_piece: # with this line we avoid recursively invoking in_check() and calc_moves() method
                                if not self.in_check(piece, move):
                                    piece.add_move(move)
                            else:
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
                            if move_the_piece: # with this line we avoid recursively invoking in_check() and calc_moves() method
                                if not self.in_check(piece, move):
                                    piece.add_move(move)
                                #else: break # <- FIXED BUG: This line prevented the King piece to make valid moves
                            else:
                                piece.add_move(move)


            # castling moves
            if not piece.moved: 
                # queenside castling
                left_rook = self.squares[row][0].piece
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
                                if move_the_piece: # with this line we avoid recursively invoking in_check() and calc_moves() method
                                    if not self.in_check(piece, moveKing) and not self.in_check(left_rook, moveRook):
                                        left_rook.add_move(moveRook)
                                        piece.add_move(moveKing)
                                else:
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
                                if move_the_piece: # with this line we avoid recursively invoking in_check() and calc_moves() method
                                    if not self.in_check(piece, moveKing) and not self.in_check(right_rook, moveRook):
                                        right_rook.add_move(moveRook)                                        
                                        piece.add_move(moveKing)
                                else:
                                    right_rook.add_move(moveRook)  
                                    piece.add_move(moveKing)        
        
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

    
    def _add_pieces(self, color: str):
        if color == 'white':
            row_pawn, row_other = (6, 7)
        else:
            row_pawn, row_other = (1, 0)            

        # putting Pawns on board
        for col in range(COLS):
            self.squares[row_pawn][col] = Square(row_pawn, col, Pawn(color))
            
        # Knights
        self.squares[row_other][1] = Square(row_other, 1, Knight(color))
        self.squares[row_other][6] = Square(row_other, 6, Knight(color))      
        
        # Bishop
        self.squares[row_other][2] = Square(row_other, 2, Bishop(color))
        self.squares[row_other][5] = Square(row_other, 5, Bishop(color))
        
        # Rook
        self.squares[row_other][0] = Square(row_other, 0, Rook(color))
        self.squares[row_other][7] = Square(row_other, 7, Rook(color))
        
        # Queen and King
        self.squares[row_other][3] = Square(row_other, 3, Queen(color))
        self.squares[row_other][4] = Square(row_other, 4, King(color))

