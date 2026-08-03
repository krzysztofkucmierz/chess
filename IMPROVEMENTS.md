# Improvements

A prioritized list of correctness fixes and performance improvements for the chess engine, based on a full code review. Each item includes exact file/line references (valid as of this commit), an explanation of the problem, and a suggested fix.

The two goals addressed:

1. **Correctness** — rare situations where the algorithm makes invalid moves or considers invalid moves as valid (including the known open bug: *"sometimes queenside castling is wrongly refused when playing vs AI"*).
2. **Performance** — the AI is very slow when analyzing 3+ moves ahead (depth 2 is fast, depth 3 takes ~30 s).

Recommended order of work: fix the correctness bugs first (they also corrupt the search tree, so performance measurements are unreliable until they're gone), then apply the performance quick wins, verifying with perft tests after every change (see [Verification](#4-verification)).

---

## 1. Correctness bugs (invalid moves)

Ordered by user-visible impact.

### 1.1. Castling executes `rook.moves[-1]` — `src/board.py:180-186` ⚠️ prime suspect for the queenside castling bug — ✅ FIXED

> **Status: fixed.** `Board.move()` now derives the rook relocation from the king's destination column; the `rook.add_move(moveRook)` appends in `king_moves()` and the `King.left_rook`/`right_rook` attributes were removed. Verified with a regression test covering all four castles plus the empty-move-list crash scenario (the old code reproducibly raised `IndexError` on it).

`king_moves()` appends the castling rook-move onto the **rook's own move list** (`src/board.py:724` and `:751`), and `Board.move()` later executes `rook.moves[-1]` to relocate the rook. During minimax the search runs with `clear_moves=False` and only the currently iterated piece gets cleared, so `rook.moves` accumulates stale entries — `moves[-1]` can be an ordinary rook move calculated earlier (rook teleported to a wrong square) or the list can be empty (`IndexError`; already worked around once by skipping castling when `test_check=True`). The corrupted state persists into the real game, which is why castling is sometimes refused after playing vs AI.

**Fix:** derive the rook move from the king's destination column instead of reading the rook's move list:
- king lands on col 2 (queenside) → rook moves (row, 0) → (row, 3)
- king lands on col 6 (kingside) → rook moves (row, 7) → (row, 5)

Then delete the `piece.left_rook` / `piece.right_rook` attributes and the `rook.add_move(moveRook)` appends in `king_moves()` entirely.

### 1.2. Sliding rays pass through the enemy king — `src/board.py:645-653` — ✅ FIXED

> **Status: fixed.** The `break` was moved out of the `King` guard so any enemy piece terminates the ray; the guard now only suppresses the king-capture move itself. Verified with regression tests in `tests/test_sliding_moves.py` (rook/bishop/queen rays blocked by the enemy king, plus normal enemy-piece blocking unchanged); the old code reproducibly failed them.

In `straightline_moves()` the `break` is nested **inside** the `not isinstance(..., King)` guard:

```python
elif self.squares[...].has_enemy_piece(piece.color):
    if not isinstance(self.squares[...].piece, King):
        if not self.in_check(piece, move):
            piece.add_move(move)
        break   # <-- only breaks when the blocker is NOT a king
```

When the blocking enemy piece **is** the king, the loop does not break and keeps generating moves on the squares *behind* the king (e.g. rook a1 vs king a5 ⇒ a6/a7/a8 become "legal"). These moves are accepted by `valid_move()`.

**Fix:** move the `break` one level out so any enemy piece terminates the ray; keep the `King` check only to suppress `add_move`.

### 1.3. Castling legality checks incomplete — `src/board.py:699-752` — ✅ FIXED

> **Status: fixed.** Castling is now offered only when the king is not currently in check (`is_king_checked` gate), and the king's transit square (d1/d8 queenside, f1/f8 kingside) is validated with a direct `in_check` king-move test; the rook-move proxy test was removed. Verified with regression tests in `tests/test_castling_legality.py` (out of check, through attacked transit, into attacked destination, and the b-file square legitimately not blocking queenside); the old code reproducibly failed the transit-square cases.

Two rules of castling are not enforced:
- **Castling out of check is allowed** — there is no test that the king is not currently in check before offering the castling move.
- **The transit square is not tested directly** — only the king's destination is validated via `in_check()`, plus a proxy test that moving the rook doesn't expose the king. The square the king passes *through* (d1/d8 for queenside, f1/f8 for kingside) is never checked for attack.

**Fix:** before adding the castling move, require `not self.is_king_checked(piece.color)`, and validate the king's transit square with a direct `in_check()` test. Remove the rook-move proxy test.

### 1.4. En passant flag set on any pawn move — `src/board.py:235-243`

`set_true_en_passant()` sets `piece.en_passant = True` for **every** pawn move, including single-square pushes. Combined with the capture conditions in `pawn_moves()` (`src/board.py:547-585`), a pawn that advanced only one square can be illegally captured "en passant".

**Fix:** set the flag only when the pawn moved two squares: `abs(move.initial.row - move.final.row) == 2`. Pass the move (or a `double_push` boolean) instead of the current `pawn_moved` flag.

### 1.5. `undo_en_passant()` re-flags arbitrary pieces — `src/game.py:250-254`

```python
piece = self.board_states[self.move_count].current_state.piece
if piece:
    self.board_states[self.move_count].set_true_en_passant(piece, True)
```

The `True` is unconditional, so after every undo — including the thousands of undos performed **inside minimax** — whatever piece moved last (knight, rook, king…) gets `en_passant = True`, and a single-pushed pawn becomes en-passant-capturable. This silently corrupts en-passant state throughout the search and after the `u`-key undo.

**Fix:** only re-flag when the stored piece is a `Pawn` and its recorded move was a double push; otherwise just clear all en-passant flags.

### 1.6. `check_win()` ignores its `color` argument — `src/game.py:194-201` + `src/minimax.py:32-35`

`check_win(color)` never uses `color` in its condition — it only reads `opponent_king_checked and opponent_has_no_valid_moves`. In minimax:

```python
if game_state.check_win(BLACK_PIECE_COLOR):   return float('-inf')
elif game_state.check_win(WHITE_PIECE_COLOR): return float('inf')
```

both calls return the same boolean, so the first branch always wins and **every checkmate in the search tree is scored `-inf` regardless of who is mated**. A white AI avoids delivering mate; a black AI walks into being mated. This is a major playing-strength bug.

**Fix:** determine the mated side from `current_state.player_color` and score mates side-aware. Use finite, depth-adjusted mate scores (e.g. `±(100000 - ply)`) instead of `±inf` — this also makes the AI prefer faster mates and avoids clipping against the `-1000`/`1000` initial values of `best_score`.

### 1.7. Stale `captured` flag inside the search — `src/board.py:246`, `:202`

`set_capturing_move_flag()` is called only from the GUI path (`src/main.py:230`) and once at the minimax root (`src/minimax.py:180`). Deeper in the search, `Board.move()` reads the stale `current_state.captured` value at `src/board.py:202` and may wrongly decrement `white_pieces_count`/`black_pieces_count` and stamp `last_move_when_piece_captured` for non-captures — corrupting insufficient-material and 50-move draw detection inside the search.

**Fix:** set `current_state.captured` inside `Board.move()` itself by inspecting the destination square before mutating it, and remove the reliance on external callers.

### 1.8. Pawn-check detection: negative-index wraparound — `src/board.py:396-407`

The bounds guard tests `Square.in_range(row + 1, col ± 1)` but the row actually indexed is `check_row = row - 1` for the black king. At `row == 0` the guard passes while `check_row == -1`, so `squares[-1]` silently wraps to row 7 and a pawn on the opposite edge of the board can be reported as giving check.

**Fix:** guard with the row that is actually indexed (`check_row`), per color.

### 1.9. Promotion runs during legality probes — `src/board.py:171-173`

The auto-queen promotion executes even when `test_check=True`, allocating a new `Queen` object for every legality probe of a 7th-rank pawn move. Additionally, piece counters are not adjusted on promotion.

**Fix:** skip promotion when `test_check=True` (the occupying piece type doesn't change the "is my king in check" answer for that probe).

### 1.10. Latent: `Piece.is_black()` always returns `True` — `src/piece.py:36`

```python
return bool(~(piece_data & WHITE_PIECE_COLOR))
```

`~0 == -1` and `~0x40 == -65` — both truthy, so the function returns `True` for every input, which also breaks `has_team_piece` / `has_enemy_piece` / `isempty_or_enemy` in the int-based fast path (`src/piece.py:39-58`). Currently harmless only because every call site is commented out (the `# OPTIMIZATION` comments in `src/board.py:534, 553, 572, 646`) — re-enabling those paths today would silently break move generation. The correct version already exists in `src/piece_representation.py:27` (`not bool(...)`).

**Fix:** correct the operator before ever enabling the fast-path comparisons.

---

## 2. Performance quick wins

Ranked by expected impact. Combined, these should take depth 3 from ~30 s to the low seconds without any architectural rewrite.

### 2.1. Alpha-beta pruning — `src/minimax.py:18-101` (est. 5-20× at depth 3)

The search is plain minimax with no pruning (alpha-beta is already listed as TODO in the README). Add `alpha`/`beta` parameters with the standard cutoff; while doing so, merge the maximizing and minimizing branches (currently ~30 lines duplicated at `:41-70` vs `:72-101`) into a single parameterized loop or negamax form.

**Multiplier:** collect the node's `(piece, move)` pairs into a list first and sort captures-first, highest captured-piece value first (the captured piece is available via `move.final.piece`). Move ordering is what makes alpha-beta cut effectively.

### 2.2. Stop calling `player_has_no_valid_moves()` on every search node — `src/board.py:212` (est. 3-10×; the single biggest cost)

Every `Board.move()` — i.e. every node of the search tree — runs `player_has_no_valid_moves(enemy_color)` (`src/board.py:332`), which performs **full move generation for every enemy piece, with a per-move `in_check()` simulation**. Each node effectively costs an extra ply, making node cost ~O(moves²). The profiling notes in `src/brudnopis.txt` confirm legality checking consumes >50% of AI time.

**Fix:** detect terminal nodes in minimax itself, for free: if generating moves at a node yields **zero legal moves**, the node is checkmate when `is_king_checked(side_to_move)` is true, stalemate otherwise. (Generating all node moves up front is needed for move ordering in 2.1 anyway.) Keep computing `opponent_king_checked` / `opponent_has_no_valid_moves` only on the real-move GUI path (e.g. gate on `not ai_minimax`).

### 2.3. Replace `copy.deepcopy(piece.moves)` — `src/board.py:339`

Because each `Move` holds `Square`s that reference `Piece` objects, `deepcopy` recursively copies whole pieces (texture paths, move lists) for every piece on every call. A shallow copy `piece.moves[:]` is sufficient here — the list is only saved and restored around the probe.

### 2.4. Remove `print` calls from the search hot path (est. 1.2-1.5×)

Console I/O executed inside the search loop:
- `src/board.py:349` (`player_has_no_valid_moves`) — disappears anyway with 2.2
- `src/board.py:306-320` (`check_insufficient_mating_material`)
- `src/minimax.py:67-68` and `:98-99` — the `moves_analyzed % 1000` progress print (the modulo test itself runs per move)
- `src/minimax.py:157` — `move.show(...)` per root move (keep if desired, it's root-level only)

### 2.5. Fix depth plumbing — `src/minimax.py:38, 52, 83`

`minimax()` compares against the module-level constant `AI_MAX_DEPTH` instead of `self.max_depth`, so the constructor parameter is silently ignored (used only in a printout at `:183`). Also note `depth > AI_MAX_DEPTH` with the root driver starting at `depth=1` means `AI_MAX_DEPTH = 2` actually searches 3 plies — worth renaming or documenting so future depth changes do what they say.

### 2.6. Cheaper leaf evaluation — `src/board.py:482`

`calculate_piece_score()` rescans all 64 squares with an `is_piece` test and attribute lookups on every leaf. Minimal fix: iterate only occupied squares without the dual-array indirection. Better fix: maintain the material score **incrementally** in `BoardState`, updated on capture/promotion inside `move()` — leaf evaluation then becomes a single field read.

---

## 3. Optional future work (out of current scope)

- **Make/unmake refactor** — a single `Board` plus a small per-move undo record (captured piece, previous `moved` flag, previous en-passant pawn, castling rook squares) instead of the 300 pre-allocated `Board` snapshots. Eliminates `copy_board_content()` and the full `dump_to_squares_fast_method()` rebuild from every node, removes the 300-move hard cap and the slow startup (~9600 `Piece` constructions), and fixes the root cause behind bugs 1.1/1.5: `Piece` objects shared by reference across snapshots with `undo_moved()`/`undo_en_passant()` patch-ups. Prerequisite for comfortable depth 4+.
- **Incremental per-move updates** for `set_true_en_passant()` (`src/board.py:235`, scans 64 squares — track the single flagged pawn in `BoardState` instead) and `dump_to_squares_fast_method()` (`src/board.py:93`, full rebuild — update only the 2-4 changed squares).
- **Transposition table and iterative deepening** once alpha-beta is in.
- **App-level cleanups:** cache piece textures at startup instead of `pygame.image.load()` per piece per frame (`src/game.py:62`, also `src/dragger.py:21`); preload the capture `Sound` instead of constructing it inside `Board.move()` (`src/board.py:168`); allocate board states lazily; delete dead `src/piece_representation.py` (never imported; its `decode_piece()` recurses infinitely); re-enable or remove the disabled 3-fold repetition check (`src/game.py:174` starts with `return False` and references a field that no longer exists).

---

## 4. Verification

- **Perft test harness** — automate the Stockfish comparison already done manually in `src/brudnopis.txt`: from the starting position assert **perft(3) = 8,902** and **perft(4) = 197,281**, driving the tree through the same `move()` / `prepare_board_state_for_next_move()` / `undo_last_move()` path minimax uses. Add one or two hand-set-up positions rich in castling/en-passant to exercise the fixed paths. Run after **every** correctness fix — perft catches move-generation regressions instantly.
- **Timing benchmark** — measure `best_move()` wall time and `moves_analyzed` at depth 2 and 3 (start position + one middlegame position) before and after each performance item.
- **Alpha-beta equivalence** — before deleting the plain-minimax path, assert the alpha-beta root score equals the plain minimax root score on several positions (pruning must never change the result, only the work).
- **Manual sanity** — play a full game vs AI checking specifically: queenside castling works for both colors; castling is refused while in check or through an attacked square; en passant is only available on the immediately following move; no sliding piece ever moves through the enemy king.
