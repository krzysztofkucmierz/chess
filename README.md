# Overview

This project is a chessboard with AI mode written in Python. It uses a pygame library.  
It is an improved version of the chessboard project created by AlejoG10.  
Alejo's original code is available on GH at https://github.com/AlejoG10/python-chess-ai-yt  
AlejoG10 has also created 5 hours long hands-on tutorial on Youtube https://www.youtube.com/watch?v=OpL0Gcfn4B4 (watch it if you'd like to implement a chessboard "from scratch").  
However I've found several bugs and missing functionalities in his implementation so I've decided to work on it.  

## About the most recent version of the project:  
- It implements the simplest minimax algorithm for AI.  
- Performance has improved 5 times comparing to previous version just by optimizing original data structures and code flow.  
- You can select 3 game modes: player vs. player, player vs. AI and AI vs. player.  

Unfortunately AI is still very slow.  
It runs fast only on AI_MAX_DEPTH = 2 where it predicts only 3 piece moves ahead (depth=0 is no recurrence).  
On AI_MAX_DEPTH = 3 you need to wait ~30 seconds for AI to make a move.  
No reason to play at higher depths.  
To further improve performance I will implement alpha-beta pruning for minimax.  

# Game Snapshots

## Snapshot 1 - Checkmate detected
![snapshot1](snapshots/checkmate.png)

## Snapshot 2 - Draw - stalemate detected
![snapshot2](snapshots/stalemate.png)

## Snapshot 3 - Draw - insufficient material
![snapshot3](snapshots/draw-insufficient-material.png)

## Snapshot 4 - Select game mode
![snapshot4](snapshots/select-game-mode.png)

## How to run?
1. Clone, fork or download the project, then go to the project's main directory  
2. pip install -r requirements.txt  
3. python .\src\main.py # on Windows OS  
  
## How to run tests?

Regression tests live in the tests directory (currently castling execution; a perft test comparing move counts against known reference values is planned next, see IMPROVEMENTS.md section 4).  

1. python .\tests\test_castling.py # standalone, no extra dependencies  
2. pytest tests # alternatively, if you have pytest installed  

## You can choose which version of the code to run and work on.  
Available tags:  
- baseline_no_AI  - minimal changes to original AlejoG10 code  
- minimax_slow_AI - above + introduced player vs AI mode
- minimax_v2_AI - above + performance improved ~5 times

# List of game improvements

NOTE: A detailed, prioritized list of further correctness fixes and performance improvements (with exact file/line references) is maintained in [IMPROVEMENTS.md](IMPROVEMENTS.md).  

## Features not present in the original code:
 IMPLEMENTED:   Feature 1. Detect when a King is actually in check.  
 IMPLEMENTED:   Feature 2. Detect checkmate position.  
 IMPLEMENTED:   Feature 3. Detect stalemate position.  
 IMPLEMENTED:   Feature 4. Detect draw position in case of: position on the board repeated 3 times OR both players don't have enough material to win OR 50 moves made without capturing a piece and no pawn move. See details on: https://en.wikipedia.org/wiki/Draw_%28chess%29#Draws_in_all_games 
 NOTE: Currently 3 fold repetition is turned off.  
 IMPLEMENTED:   Feature 5. Storing and displaying list of all moves made from the start of the game. (press 'd' key)  
 IMPLEMENTED:   Feature 6. Undo move. Implemented ONLY for player vs player mode. (press 'u' key)  
 IMPLEMENTED:   Feature 7. Implement simplest Player vs Computer AI using simple minimax algorithm.  
 IMPLEMENTED:   Feature 8. User can select 3 game modes: player vs. player, player vs. AI and AI vs. player.  
 TODO:          Feature 9. Implement optimized minimax algorithm (with alpha-beta pruning) for Player vs Computer AI.  
 TODO:          Feature 10. Implement Player vs Computer AI using better method (hopefully reinforcement learning).  

## Bugs:
 FIXED:     Bug 1. There was a bug in calculating list of valid moves for King if he is in check or some fields around King is "in check".  
            It prevented King under check to make a valid move so it couldn't move.  
 FIXED:     Bug 2. Sometimes a Knight couldn't capture an enemy piece if that enemy piece was giving a check.  
 FIXED:     Bug 3. King was allowed to move to a square adjacent to an enemy King and as a result it could capture enemy King.  
 FIXED:     Bug 4. Queen, Rook, Bishop and Knight were allowed to capture enemy King when starting a game from other position than initial.  
 FIXED:     Bug 5. Sometimes when playing with AI, a user is not allowed to perform valid queenside Castling.  
            Root cause: castling in Board.move() executed the last move from the Rook's own move list, which goes stale during minimax (moves are recalculated with clear_moves=False), corrupting castling state.  
            Now the Rook relocation is derived directly from the King's destination square. Covered by regression tests in tests/test_castling.py.  
 FIXED:     Bug 6. Queen, Rook and Bishop could "see through" the enemy King: squares behind the King on the attack ray were generated as valid moves.  
            Root cause: the ray-terminating break in straightline_moves() was nested inside the "blocker is not a King" guard, so the enemy King did not stop the ray.  
            Covered by regression tests in tests/test_sliding_moves.py.  
 FIXED:     Bug 7. Castling was allowed through a square attacked by an enemy piece (and castling out of check was only prevented by accident).  
            Root cause: only the King's destination square was validated; the transit square (d1/d8 or f1/f8) was never tested for attack.  
            Now castling requires: King not in check, transit square not attacked, destination not attacked. Covered by regression tests in tests/test_castling_legality.py.  

## Performance improvements:
 IMPLEMENTED:   Improvement 1. Increase performance by redesigning program data structures. Mainly to avoid very costly deepcopy() operations.  This will also simplify overall program logic.  
 
 TODO:          Improvement 2. Efficient method of avoiding putting the King in check suggested by 'Wave Treader':  
 "This method does not need any copy or simulating all possible moves, it does not need to check for all opponent's possible moves.  
 It works like this.... you must have tracked the kings position every move and save it.  
 Make the move even if it puts the king in check, from there check from the king's position if any piece attacks it by looking at capture moves from the king's position.  
 If it results in a capture, just undo the move. it happens really fast you wont see the invalid move being executed.  
 The idea is that you make a function that assumes the king can move like a queen, bishop, rook, knight or pawn capture."  
