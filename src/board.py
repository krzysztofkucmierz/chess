from asyncio import current_task
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
        self.move_count: int = 1 # Counter for game moves. 1 is initial move number        
        self.player_color: str = 'white'
        self.move: Move = None # coordinates of he move
        self.piece: Piece = None # piece which is moved
        self.piece_moved_before_move: bool = False # state of piece.moved before moving the piece
        self.en_passant_captured_piece: Piece = None
        self.captured: bool = False
        self.initial_square_prev_content: Piece = None # content of the initial square before the move (including the piece itself)
        self.final_square_prev_content: Piece = None # content of the final square before the move (including the piece itself)
        self.en_passant_move: bool = False # was it en passant move?
        self.castling_move: bool = False # was it castling move?

        self.white_pieces_count = 16 # initial number of white pieces
        self.black_pieces_count = 16 # initial number of black pieces
        self.last_move_when_pawn_moved = 0 # Stores game move number when pawn was last moved. Will be set to move_count value when any Pawn will move.
        self.last_move_when_piece_captured = 0 # Stores game move number when a piece was last moved. Will be set to move_count when any piece will be captured.

    # TODO: later show also remaining members
    def show(self):
        print(f"-> Board state for move {self.move_count} color {self.player_color}:")
        if self.move:
            self.move.show(self.piece.name, "")
        else:
            print("Move in board_state structure = None")
        print(f"  piece.moved before move was made? {self.piece_moved_before_move}")
        print(f"  was piece captured? {self.captured}")
        print(f"  was the move en passant? {self.en_passant_move} Captured piece: {self.en_passant_captured_piece.name if self.en_passant_captured_piece is not None else "n/a"}")
        print(f"  initial square content {self.initial_square_prev_content}")
        print(f"  final square content {self.final_square_prev_content}")
        print(f"  pieces count: white: {self.white_pieces_count} black: {self.black_pieces_count}")
        print(f"  last move when: pawn moved {self.last_move_when_pawn_moved} piece captured: {self.last_move_when_piece_captured}")

        
class Board:
    def __init__(self):
        self.squares: List[List[Square]]= [[0, 0, 0, 0, 0, 0, 0, 0] for col in range(COLS)]
        self.moves_history: List[Tuple[Piece, Move]] = [] # this list records all game moves (a single sequence of all white and black moves as they were played) 
        self.current_state: BoardState = BoardState()
        self.previous_states: List[BoardState] = []
        self.first_move_made = False
        self._create()
        self._add_pieces('white')
        self._add_pieces('black')

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

    # This method actually makes a move 'move' for a piece 'piece' on the board
    # if testing == True then operation is performed to evaluate checks and not to make any move
    # if clear_moves == True then all possible moves for a given piece are cleared after the move is made. In AI.minimax moves can't be cleared!
    def move(self, piece: Piece, move: Move, test_check: bool = False, clear_moves: bool = True):

        initial = move.initial
        final = move.final

        # store current_state in list of previous_states (as current_state will be modified in next step)
        if self.first_move_made:
            self.previous_states.append(copy.deepcopy(self.current_state))
            #print("State appended.")

        # store current board state in current_state structure 
        self.current_state.player_color = piece.color
        self.current_state.move = move
        self.current_state.piece = piece
        self.current_state.piece_moved_before_move = piece.moved
        self.current_state.initial_square_prev_content = self.squares[initial.row][initial.col].piece
        self.current_state.final_square_prev_content = self.squares[final.row][final.col].piece
        self.current_state.castling_move = False
        self.current_state.en_passant_move = False
       
        # Update relevant counters if piece was captured
        if self.current_state.captured:
            self.update_pieces_count(piece.color) # update piece counter after capture
            self.current_state.last_move_when_piece_captured = self.current_state.move_count # set this variable to 'move_count' after capture

        en_passant_empty = self.squares[final.row][final.col].isempty()
        
        # standard board update for the 'move'
        self.squares[initial.row][initial.col].piece = None
        self.squares[final.row][final.col].piece = piece

        # increase 'last_move_when_pawn_moved' counter
        if isinstance(piece, Pawn):
            self.current_state.last_move_when_pawn_moved = self.current_state.move_count

        # en passant capture
        if isinstance(piece, Pawn):
            diff = final.col - initial.col
            if diff != 0 and en_passant_empty:
                self.current_state.en_passant_move = True
                self.current_state.en_passant_captured_piece = self.squares[initial.row][initial.col + diff].piece
                self.squares[initial.row][initial.col + diff].piece = None
                self.squares[final.row][final.col].piece = piece # this is not needed, piece was placed here in standard board update (see above) 
                self.update_pieces_count(piece.color) # update piece counter after capture
                self.current_state.last_move_when_piece_captured = self.current_state.move_count # increase 'last_move_when_piece_captured' counter
              
                if not test_check:
                    sound = Sound(os.path.join('assets/sounds/capture.wav'))
                    sound.play()



        # Pawn promotion to a Queen
        if (final.row == 7 or final.row == 0) and isinstance(piece, Pawn):
            self.squares[final.row][final.col].piece = Queen(piece.color)


        # King castling - since King's move is coded above as standard move, now only move the Rook
        if isinstance(piece, King):
            if self.castling(initial, final) and not test_check: # check if castling move detected
                self.current_state.castling_move = True
                diff = final.col - initial.col
                rook = piece.left_rook if (diff < 0) else piece.right_rook
                rook_move = rook.moves[-1]
                # changed from recursion to normal implementation! 
                self.squares[rook_move.initial.row][rook_move.initial.col].piece = None
                self.squares[rook_move.final.row][rook_move.final.col].piece = rook
                rook.moved = True



        # move
        piece.moved = True
        if test_check:
            piece.moved = self.current_state.piece_moved_before_move
        # clear valid moves
        if clear_moves:
            piece.clear_moves()
        
        #self.current_state.show()
        self.set_true_en_passant(piece) # make sure en passant state for pawns lasts only for 1 turn, so clear the en passant flag for all other pawns of current color

        # remember last move

        self.moves_history.append((copy.deepcopy(piece), copy.deepcopy(move))) # NEW CODE: add last move to the history of game moves

    # returns if piece was moved based on moves history
    def piece_moved(self, piece: Piece, row, col) -> bool:
        if len(self.moves_history) <= 0:
            return False
        for p, m in self.moves_history:
            if isinstance(piece, Piece) and piece.color == p.color:
                if m.final.row == row and m.final.col == col:
                    return True

        return False
    
    # This method reverts board state to the position before last move
    # Returns:
    #   True if last move undone successfully
    #   False if otherwise (first move was not made yet)
    def undo_last_move(self, test_check: bool = False) -> bool:
 
        #print(f"undo_last_move(): length of previos states list: {len(self.previous_states)}")
        # IMPORTANT! if the list of previous states is empty it means that only first move was played
        # in this situation we just reset the board initial state
        #print(f"len(self.previous_states) = {len(self.previous_states)}")
        if len(self.previous_states) == 0:
            self.__init__()
            return False
        
        # revert the board status (pieces on squares)
        # return piece to initial
        init_row = self.current_state.move.initial.row
        init_col = self.current_state.move.initial.col
        #self.squares[init_row][init_col].piece = self.current_state.piece
        self.squares[init_row][init_col].piece = self.current_state.initial_square_prev_content
        self.squares[init_row][init_col].piece.moved = self.current_state.piece_moved_before_move

        # clear piece on final if it was empty or place removed piece if it was captured - standard case
        final_row = self.current_state.move.final.row
        final_col = self.current_state.move.final.col
        self.squares[final_row][final_col].piece = self.current_state.final_square_prev_content

        
        # for en-passant case restore captured piece on square next to capturing pawn
        if self.current_state.en_passant_move:        
            self.squares[init_row][final_col].piece = self.current_state.en_passant_captured_piece
            
        # King castling - since King's move is undone above, now undo the Rook move
        if isinstance(self.current_state.initial_square_prev_content, King):
            if self.current_state.castling_move == True:            
                # black queenside castling (King e8->c8, Rook a8->d8)
                if init_row == 0 and init_col == 4 and final_row == 0 and final_col == 2:
                    self.squares[0][0].piece = Rook('black')
                    self.squares[0][3].piece = None

                # white queenside castling (King e1->c1, Rook a1->d1)
                elif init_row == 7 and init_col == 4 and final_row == 7 and final_col == 2:
                    self.squares[7][0].piece = Rook('white')
                    self.squares[7][3].piece = None
                    
                # black kingside castling (King e8->g8, Rook h8->f8)
                elif init_row == 0 and init_col == 4 and final_row == 0 and final_col == 6:
                    self.squares[0][7].piece = Rook('black')
                    self.squares[0][5].piece = None
                    
                # white kingside castling (King e1->g1, Rook h1->f1)
                elif init_row == 7 and init_col == 4 and final_row == 7 and final_col == 6:
                    self.squares[7][7].piece = Rook('white')
                    self.squares[7][5].piece = None
                else:
                    self.current_state.move.show("king","!!! Error. IN undo_move for castling, but the King move is unrecognized")


        # set last previous state as current_state
        self.current_state = self.previous_states.pop()

        
        # set en passant flag on previously moved piece
        en_passant_row = self.current_state.move.final.row
        en_passant_col = self.current_state.move.final.col
        self.set_true_en_passant(self.squares[en_passant_row][en_passant_col].piece)


        self.moves_history.pop()

        return True


    # check if a piece move is a valid move on the board
    def valid_move(self, piece: Piece, move: Move):
        #move.show(piece.name, "")
        #piece.show_moves()
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


    # verify if the move of the piece will uncover a check of King of the same color as the moved piece
    def in_check(self, piece: Piece, move: Move):
        king_checked = False

        # temporarily set current player color to piece color
        player_color = self.current_state.player_color
        self.current_state.player_color = piece.color
        
        self.move(piece, move, test_check = True, clear_moves = False) # simulate the move
        king_checked = self.is_king_checked(piece.color)

        self.undo_last_move(test_check = True)
        
        # revert player color to the old value
        self.current_state.player_color = player_color
        return king_checked


    # Returns True if game has reached 50 move rule which leads to game draw. 
    # NOTE. Using > comparison as move count is increased before checking this rule
    def check_fifty_move_rule(self, limit_moves_count: int = 50):
        if self.current_state.move_count - self.current_state.last_move_when_pawn_moved > limit_moves_count and self.current_state.move_count - self.current_state.last_move_when_piece_captured > limit_moves_count:
            return True
        else:
            return False
        
    # Decreases one of piece counters after a move when a piece was captured.
    def update_pieces_count(self, current_player_color: str):
        if current_player_color == 'white':
            self.current_state.black_pieces_count = self.current_state.black_pieces_count - 1
        elif current_player_color == 'black':
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
                    if self.squares[row][col].has_team_piece('white'):
                        if isinstance(self.squares[row][col].piece, Bishop) or isinstance(self.squares[row][col].piece, Knight):
                            print(f"Draw! Insufficient mating material (K vs K+B or K vs K+Kn)!") 
                            return True
        elif self.current_state.black_pieces_count == 2 and self.current_state.white_pieces_count == 1:
            for row in range(ROWS):
                for col in range(COLS):
                    if self.squares[row][col].has_team_piece('black'):
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
    def player_has_no_valid_moves(self, color: str):
        for row in range(ROWS):
            for col in range(COLS):
                if self.squares[row][col].has_team_piece(color):
                    piece=copy.deepcopy(self.squares[row][col].piece)
                    self.calc_moves(piece, row, col)
                    if piece.moves != []:
                        #print(f"Piece on {Square.get_alphacol(col)}{ROWS - row} can move, player {color} has valid moves.")
                        return False
                    
        print(f"Player {color} has no valid moves!")
        return True

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
                                #print(f"Pawn on {Square.get_alphacol(col)}{ROWS - row} is checking the {color} King!")
                                return True
                        if Square.in_range(row+1, col-1):
                            if isinstance(self.squares[check_row][col-1].piece, King) and self.squares[check_row][col-1].has_team_piece(color):
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
                                if isinstance(self.squares[check_row][check_col].piece, King) and self.squares[check_row][check_col].has_team_piece(color):
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

    # Returns score of the current board position
    def calculate_piece_score(self) -> float:
        score = 0
        for col in range(COLS):
            for row in range(ROWS):
                if self.squares[row][col].has_piece():
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
                    if self.squares[possible_move_row][col].isempty():
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
            r = 3 if piece.color == 'white' else 4 # assign a row where this type of move may happen
            fr = 2 if piece.color == 'white' else 5  # final row
            # left en passant
            if Square.in_range(col-1) and row == r: 
                if self.squares[row][col-1].has_enemy_piece(piece.color): # check for enemy piece left to the pawn
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
                            # append new move
                            #  see if there are potential checks
                            if not self.in_check(piece, move):
                                piece.add_move(move)
                            
                        # has enemy piece, so add a move but break (this is the furthest move in this direction)
                        elif self.squares[possible_move_row][possible_move_col].has_enemy_piece(piece.color):
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
                                if not self.in_check(piece, moveKing) and not self.in_check(left_rook, moveRook):
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
                                if not self.in_check(piece, moveKing) and not self.in_check(right_rook, moveRook):
                                    right_rook.add_move(moveRook)
                                    piece.add_move(moveKing)
      
        #print(f"performing calc_moves for {piece.color} {piece.name}.")
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


    def _add_pieces(self, color: str, board_position: str = 'standard'):
        if board_position == 'standard':
            self._add_pieces_standard(color)
        elif board_position == 'checkmate':
            self._add_pieces_checkmate(color)
        elif board_position == 'stalemate':
            self._add_pieces_stalemate(color)
        elif board_position == 'insufficient_material':
            self._add_pieces_insufficient_material(color)
            
            
    def _add_pieces_standard(self, color: str):
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
    


    def _add_pieces_checkmate(self, color: str):
        if color == 'white':
            row_pawn, row_other = (6, 7)
            self.squares[0][0] = Square(0, 0, Queen(color))
            self.squares[1][0] = Square(1, 0, Queen(color))
        else:
            row_pawn, row_other = (1, 0)

        self.squares[row_other][4] = Square(row_other, 4, King(color))
    
    def _add_pieces_stalemate(self, color: str):
        if color == 'white':
            self.squares[2][3] = Square(2, 3, Queen(color))
            self.squares[2][0] = Square(2, 0, King(color))

        else:
            self.squares[0][1] = Square(0, 1, King(color))

                
    def _add_pieces_insufficient_material(self, color: str): # King + Knight vs King
        if color == 'white':
            row_pawn, row_other = (6, 7)
            self.squares[row_other][1] = Square(row_other, 1, Knight(color))
        else:
            row_pawn, row_other = (1, 0)

        self.squares[row_other][4] = Square(row_other, 4, King(color))
        self.current_state.white_pieces_count = 2
        self.current_state.black_pieces_count = 1      
        
        
    ##################################################
    # AI helper methods
    
    # For given player fill piece.moves List for all his/her pieces with all moves valid on current board
    # returns True if there are at least one valid move
    # returns False if no valid moves found (player has ZERO moves) 
    def get_all_valid_moves_for_player(self, current_player_color: str):
        found_moves = False
        for col in range(COLS):
            for row in range(ROWS):
                if self.squares[row][col].has_team_piece(current_player_color):
                    piece = self.squares[row][col].piece
                    self.calc_moves(piece, row, col)
                    if piece.moves != []:
                        found_moves = True
        return found_moves

    # For given player clear piece.moves List for all his/her pieces
    def clear_all_valid_moves_for_player(self, current_player_color: str):
        for col in range(COLS):
            for row in range(ROWS):
                if self.squares[row][col].has_team_piece(current_player_color):
                    piece = self.squares[row][col].piece
                    piece.clear_moves()

    #########################
    # DEBUG METHODS

    # show list of all moves made so far on the board
    def show_moves_history(self):
        for i, current_move in enumerate(self.moves_history):
            piece, move_coordinates = current_move 
            move_coordinates.show(piece.name, piece.color + " " + str((i // 2) + 1))

    # show board-related counters
    def show_move_counters(self):
        print(f"Game move no: {self.current_state.move_count}.")
        print(f"Pawn last moved on move no: {self.current_state.last_move_when_pawn_moved}.")
        print(f"Piece last captured on move no: {self.current_state.last_move_when_piece_captured}.")

    # show number of black and white pieces currently on the board
    def show_pieces_count(self):
        print(f"White pieces count: {self.current_state.white_pieces_count}. Black pieces count {self.current_state.black_pieces_count}")
    
    # show history of previous board states
    def show_previous_states(self):
        if self.previous_states == []:
            print("HISTORY NOT PRESENT! ")                               
        for i, old_state in enumerate(self.previous_states):
            print(f"-> HISTORY STATE {i}: ")
            old_state.show()

    # get board position of a Pawn which can be captured en-passant in current move
    def get_en_passant_pawn_position(self):
        for row in range(ROWS):
            for col in range(COLS):
                if isinstance(self.squares[row][col].piece, Pawn):
                    if self.squares[row][col].piece.en_passant == True:
                        print(f"En Passant pawn is on {Square.get_alphacol(col)}{ROWS-row}")
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