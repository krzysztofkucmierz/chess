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

### 1.4. En passant flag set on any pawn move — `src/board.py:235-243` — ✅ FIXED

> **Status: fixed.** `Board.move()` now passes a `double_pawn_push` flag (`abs(final.row - initial.row) == 2`) to `set_true_en_passant()`, so single pushes never mark a pawn as capturable. Verified together with 1.5 by `tests/test_en_passant.py`; the old code reproducibly failed.

`set_true_en_passant()` sets `piece.en_passant = True` for **every** pawn move, including single-square pushes. Combined with the capture conditions in `pawn_moves()` (`src/board.py:547-585`), a pawn that advanced only one square can be illegally captured "en passant".

**Fix:** set the flag only when the pawn moved two squares: `abs(move.initial.row - move.final.row) == 2`. Pass the move (or a `double_push` boolean) instead of the current `pawn_moved` flag.

### 1.5. `undo_en_passant()` re-flags arbitrary pieces — `src/game.py:250-254` — ✅ FIXED

> **Status: fixed.** `Game.undo_en_passant()` now re-flags only when the recorded piece is a `Pawn` whose recorded move was a two-square push; after any other move all flags are simply cleared. Verified together with 1.4 by `tests/test_en_passant.py` (undo after knight moves and single pushes leaves no flags; undo after a double push correctly restores the flag).

```python
piece = self.board_states[self.move_count].current_state.piece
if piece:
    self.board_states[self.move_count].set_true_en_passant(piece, True)
```

The `True` is unconditional, so after every undo — including the thousands of undos performed **inside minimax** — whatever piece moved last (knight, rook, king…) gets `en_passant = True`, and a single-pushed pawn becomes en-passant-capturable. This silently corrupts en-passant state throughout the search and after the `u`-key undo.

**Fix:** only re-flag when the stored piece is a `Pawn` and its recorded move was a double push; otherwise just clear all en-passant flags.

### 1.6. `check_win()` ignores its `color` argument — `src/game.py:194-201` + `src/minimax.py:32-35` — ✅ FIXED

> **Status: fixed.** `check_win(color)` now attributes the win to the color of the piece that made the mating move (`current_state.piece`, valid both before and after `prepare_board_state_for_next_move()`). Minimax scores mates side-aware, finite and depth-adjusted (`±(MATE_SCORE - depth)`, `MATE_SCORE = 100000` in `const.py`), and the `best_score` loop initializers were changed from `±1000` to `±inf` so mate scores are never masked. **Additionally discovered and fixed:** `copy_board_content()` did not copy `opponent_king_checked` / `opponent_has_no_valid_moves`, so every minimax node read stale mate/stalemate flags left over from previously explored branches — mate detection inside the search was effectively random before this. Verified by `tests/test_checkmate_scoring.py`; the old code reproducibly failed.

`check_win(color)` never uses `color` in its condition — it only reads `opponent_king_checked and opponent_has_no_valid_moves`. In minimax:

```python
if game_state.check_win(BLACK_PIECE_COLOR):   return float('-inf')
elif game_state.check_win(WHITE_PIECE_COLOR): return float('inf')
```

both calls return the same boolean, so the first branch always wins and **every checkmate in the search tree is scored `-inf` regardless of who is mated**. A white AI avoids delivering mate; a black AI walks into being mated. This is a major playing-strength bug.

**Fix:** determine the mated side from `current_state.player_color` and score mates side-aware. Use finite, depth-adjusted mate scores (e.g. `±(100000 - ply)`) instead of `±inf` — this also makes the AI prefer faster mates and avoids clipping against the `-1000`/`1000` initial values of `best_score`.

### 1.7. Stale `captured` flag inside the search — `src/board.py:246`, `:202` — ✅ FIXED

> **Status: fixed.** `Board.move()` now inspects the destination square itself (before overwriting it) and sets `current_state.captured` for every real move; the `set_capturing_move_flag()` method and both external calls (GUI path and minimax root) were removed. En passant keeps its separate counting path (destination square is empty), unchanged. Verified by `tests/test_state_bugs.py` — a capture decrements the counters with no external call, and a deliberately poisoned stale flag no longer makes a quiet move decrement counters or stamp `last_move_when_piece_captured`; the old code reproducibly failed.

`set_capturing_move_flag()` is called only from the GUI path (`src/main.py:230`) and once at the minimax root (`src/minimax.py:180`). Deeper in the search, `Board.move()` reads the stale `current_state.captured` value at `src/board.py:202` and may wrongly decrement `white_pieces_count`/`black_pieces_count` and stamp `last_move_when_piece_captured` for non-captures — corrupting insufficient-material and 50-move draw detection inside the search.

**Fix:** set `current_state.captured` inside `Board.move()` itself by inspecting the destination square before mutating it, and remove the reliance on external callers.

### 1.8. Pawn-check detection: negative-index wraparound — `src/board.py:396-407` — ✅ FIXED

> **Status: fixed.** Both guards in `is_king_checked()` now test `check_row` — the row actually indexed — instead of `row + 1`. This became reachable with the 1.9 fix (a probing pawn now really sits on row 0 during legality tests instead of being replaced by a Queen). Verified by `tests/test_state_bugs.py`: a white pawn on row 0 no longer "checks" a black king on row 7, and a genuine pawn check is still detected; the old code reproducibly failed.

The bounds guard tests `Square.in_range(row + 1, col ± 1)` but the row actually indexed is `check_row = row - 1` for the black king. At `row == 0` the guard passes while `check_row == -1`, so `squares[-1]` silently wraps to row 7 and a pawn on the opposite edge of the board can be reported as giving check.

**Fix:** guard with the row that is actually indexed (`check_row`), per color.

### 1.9. Promotion runs during legality probes — `src/board.py:171-173` — ✅ FIXED

> **Status: fixed.** The promotion in `Board.move()` is now gated on `not test_check` — during a probe the pawn stays a pawn (it blocks enemy rays the same way a Queen would, so the check answer is identical). Verified by `tests/test_state_bugs.py` with a counting `Queen` subclass: `calc_moves()` on a 7th-rank pawn allocates zero Queens, a real promotion move allocates exactly one; the old code reproducibly failed. (The piece counters need no adjustment on promotion — they count pieces, and pawn→queen keeps the count unchanged.)

The auto-queen promotion executes even when `test_check=True`, allocating a new `Queen` object for every legality probe of a 7th-rank pawn move. Additionally, piece counters are not adjusted on promotion.

**Fix:** skip promotion when `test_check=True` (the occupying piece type doesn't change the "is my king in check" answer for that probe).

### 1.10. Undoing castling leaves the Rook's `moved` flag set — `src/game.py` (`undo_moved`) — ✅ FIXED

> **Found by the perft harness** (kiwipete perft(2) counted 1,995 instead of 2,039): `undo_moved()` restored only the King's `moved` flag, never the Rook's, and Piece objects are shared across board states. After any minimax line in which a castle was tried, that Rook kept `moved = True` forever — castling silently disappeared from the rest of the search **and from the real game** (the second root cause behind README Bug 5). Fixed by restoring the castling Rook's flag from the previous state's `squares_fast_method` in `undo_moved()`. Guarded by `tests/test_perft.py` (kiwipete).

### 1.11. Latent: `Piece.is_black()` always returns `True` — `src/piece.py:36` — ✅ FIXED

> **Status: fixed.** `is_black()` now returns `not bool(piece_data & WHITE_PIECE_COLOR)` (matching the correct version that existed in `piece_representation.py`), so `has_team_piece` / `has_enemy_piece` / `isempty_or_enemy` in the int fast path give correct answers if the `# OPTIMIZATION` call sites are ever re-enabled. Verified by `tests/test_state_bugs.py` (color helper truth table); the old code reproducibly failed.

```python
return bool(~(piece_data & WHITE_PIECE_COLOR))
```

`~0 == -1` and `~0x40 == -65` — both truthy, so the function returns `True` for every input, which also breaks `has_team_piece` / `has_enemy_piece` / `isempty_or_enemy` in the int-based fast path (`src/piece.py:39-58`). Currently harmless only because every call site is commented out (the `# OPTIMIZATION` comments in `src/board.py:534, 553, 572, 646`) — re-enabling those paths today would silently break move generation. The correct version already exists in `src/piece_representation.py:27` (`not bool(...)`).

**Fix:** correct the operator before ever enabling the fast-path comparisons.

---

## 2. Performance quick wins

Ranked by expected impact. Combined, these should take depth 3 from ~30 s to the low seconds without any architectural rewrite.

### 2.1. Alpha-beta pruning — `src/minimax.py:18-101` (est. 5-20× at depth 3) — ✅ IMPLEMENTED

> **Status: implemented.** `minimax()` takes `alpha`/`beta` parameters with the standard cutoff (`beta <= alpha` → break), and the duplicated maximizing/minimizing branches were merged into a single parameterized loop. Move ordering is in via the new `collect_ordered_moves()` helper (captures first, highest `abs(move.final.piece.value)` first), used both inside the search and at the `best_move()` root, where the running root best score narrows the window (`alpha` for white, `beta` for black). The `AI(pruning=False)` constructor flag preserves the plain-minimax path for the equivalence tests in `tests/test_alpha_beta.py` — same root score, same chosen move, never more nodes.
> **Measured gains:** depth 2 startpos 3.7→0.27 s (24,825→1,007 moves analyzed), middlegame 6.6→0.37 s; **depth 3 startpos 123→4.5 s (27×), middlegame 226→4.8 s (47×)** — above the 5-20× estimate thanks to root-level window narrowing.

The search is plain minimax with no pruning (alpha-beta is already listed as TODO in the README). Add `alpha`/`beta` parameters with the standard cutoff; while doing so, merge the maximizing and minimizing branches (currently ~30 lines duplicated at `:41-70` vs `:72-101`) into a single parameterized loop or negamax form.

**Multiplier:** collect the node's `(piece, move)` pairs into a list first and sort captures-first, highest captured-piece value first (the captured piece is available via `move.final.piece`). Move ordering is what makes alpha-beta cut effectively.

### 2.2. Stop calling `player_has_no_valid_moves()` on every search node — `src/board.py:212` (est. 3-10×; the single biggest cost) — ✅ IMPLEMENTED

> **Status: implemented.** `Board.move()` computes `opponent_king_checked` / `opponent_has_no_valid_moves` only for real moves (`not ai_minimax`); minimax now collects the node's legal moves up front and treats an empty list as mate (`±(MATE_SCORE - depth)` via `is_king_checked`) or stalemate (0). Mates at the search horizon are still detected: leaf nodes run a cheap `is_king_checked` scan and only when in check probe `Board.has_any_valid_move()` (new early-exit helper). Draw-by-counters checks (50-move, insufficient material) stay at node entry.
> **Measured gains** (same `moves_analyzed`, same chosen moves — identical search, cheaper nodes): depth 2 startpos 8.0→4.2 s (1.9×), middlegame 10.7→7.5 s (1.4×); **depth 3 startpos 311→138 s (2.3×), middlegame 823→239 s (3.4×)**; perft(4) 61→26 s. Gain is below the 3-10× estimate because the old scan early-exits on the first enemy piece with a move — remaining node cost is dominated by the per-candidate-move `in_check` simulation (see 2.1 alpha-beta and README "Improvement 2").

Every `Board.move()` — i.e. every node of the search tree — runs `player_has_no_valid_moves(enemy_color)` (`src/board.py:332`), which performs **full move generation for every enemy piece, with a per-move `in_check()` simulation**. Each node effectively costs an extra ply, making node cost ~O(moves²). The profiling notes in `src/brudnopis.txt` confirm legality checking consumes >50% of AI time.

**Fix:** detect terminal nodes in minimax itself, for free: if generating moves at a node yields **zero legal moves**, the node is checkmate when `is_king_checked(side_to_move)` is true, stalemate otherwise. (Generating all node moves up front is needed for move ordering in 2.1 anyway.) Keep computing `opponent_king_checked` / `opponent_has_no_valid_moves` only on the real-move GUI path (e.g. gate on `not ai_minimax`).

### 2.3. Replace `copy.deepcopy(piece.moves)` — `src/board.py:339` — ✅ IMPLEMENTED

> **Status: implemented.** `player_has_no_valid_moves()` now saves/restores the list with a shallow copy `piece.moves[:]` (the Move objects are never mutated; `deepcopy` recursed into whole Piece objects via `Move.final.piece`). After 2.2 this function only runs on the real-move GUI path, so the gain is snappier GUI moves rather than search time. The now-unused `import copy` was removed from `board.py`.

Because each `Move` holds `Square`s that reference `Piece` objects, `deepcopy` recursively copies whole pieces (texture paths, move lists) for every piece on every call. A shallow copy `piece.moves[:]` is sufficient here — the list is only saved and restored around the probe.

### 2.4. Remove `print` calls from the search hot path (est. 1.2-1.5×)

Console I/O executed inside the search loop:
- `src/board.py:349` (`player_has_no_valid_moves`) — disappears anyway with 2.2
- `src/board.py:306-320` (`check_insufficient_mating_material`)
- `src/minimax.py:67-68` and `:98-99` — the `moves_analyzed % 1000` progress print (the modulo test itself runs per move)
- `src/minimax.py:157` — `move.show(...)` per root move (keep if desired, it's root-level only)

### 2.5. Fix depth plumbing — `src/minimax.py:38, 52, 83` — ✅ FIXED

> **Status: fixed.** `minimax()` now reads `self.max_depth` instead of the module constant `AI_MAX_DEPTH`, so `AI(max_depth=...)` finally works (verified: depth 1 searches 835 root+reply moves instead of the full 3-ply tree). The off-by-one semantics are documented at the constructor: `max_depth = N` analyzes N+1 plies (root move + N replies). `tests/benchmark_ai.py` no longer needs to patch the module global.

`minimax()` compares against the module-level constant `AI_MAX_DEPTH` instead of `self.max_depth`, so the constructor parameter is silently ignored (used only in a printout at `:183`). Also note `depth > AI_MAX_DEPTH` with the root driver starting at `depth=1` means `AI_MAX_DEPTH = 2` actually searches 3 plies — worth renaming or documenting so future depth changes do what they say.

### 2.6. Cheaper leaf evaluation — `src/board.py:482` — ✅ IMPLEMENTED

> **Status: implemented** (minimal variant). `calculate_piece_score()` iterates `self.squares` directly instead of indexing through both board representations with an `is_piece` bitfield test per square. **Measured** (together with 2.3/2.5): depth 2 startpos 4.2→3.7 s, middlegame 7.5→6.6 s; depth 3 startpos 138→123 s, middlegame 239→226 s (identical `moves_analyzed` and chosen moves). The incremental-material variant (score maintained in `BoardState`, updated on capture/promotion) remains available as future work once alpha-beta changes the leaf/interior ratio.

`calculate_piece_score()` rescans all 64 squares with an `is_piece` test and attribute lookups on every leaf. Minimal fix: iterate only occupied squares without the dual-array indirection. Better fix: maintain the material score **incrementally** in `BoardState`, updated on capture/promotion inside `move()` — leaf evaluation then becomes a single field read.

---

## 3. Optional future work (out of current scope)

- **Make/unmake refactor** — a single `Board` plus a small per-move undo record (captured piece, previous `moved` flag, previous en-passant pawn, castling rook squares) instead of the 300 pre-allocated `Board` snapshots. Eliminates `copy_board_content()` and the full `dump_to_squares_fast_method()` rebuild from every node, removes the 300-move hard cap and the slow startup (~9600 `Piece` constructions), and fixes the root cause behind bugs 1.1/1.5: `Piece` objects shared by reference across snapshots with `undo_moved()`/`undo_en_passant()` patch-ups. Prerequisite for comfortable depth 4+.
- **Incremental per-move updates** for `set_true_en_passant()` (`src/board.py:235`, scans 64 squares — track the single flagged pawn in `BoardState` instead) and `dump_to_squares_fast_method()` (`src/board.py:93`, full rebuild — update only the 2-4 changed squares).
- **Transposition table and iterative deepening** once alpha-beta is in.
- **App-level cleanups:** cache piece textures at startup instead of `pygame.image.load()` per piece per frame (`src/game.py:62`, also `src/dragger.py:21`); preload the capture `Sound` instead of constructing it inside `Board.move()` (`src/board.py:168`); allocate board states lazily; delete dead `src/piece_representation.py` (never imported; its `decode_piece()` recurses infinitely); ~~re-enable or remove the disabled 3-fold repetition check~~ — ✅ DONE (2026-08-05): `Game.check_three_fold_repetition()` rewritten from scratch. It compares `Game.position_key()` tuples built from the per-state `squares_fast_method` snapshots (the only reliable history — `Piece` objects are shared between board states): placement with the `PIECE_MOVED` bit masked out + side to move + actual castling rights + en passant flags (FIDE 9.2). The initial position is snapshotted in `Game.__init__` (its board state gets overwritten by ply 1), the post-`prepare` duplicate state is skipped via placement equality of the top two states, and the scan starts at the last irreversible-move stamp. Wired into `check_draw()`; GUI-only, so no search-performance impact. Covered by `tests/test_three_fold_repetition.py` (knight shuffle detected on the 3rd occurrence incl. the initial position, both GUI/pre-`prepare` and post-`prepare` call timings, burned castling rights and en passant flags distinguishing otherwise-identical placements, no false positives in a normal opening).

---

## 4. Verification

- **Perft test harness** — ✅ IMPLEMENTED as `tests/test_perft.py`: start position (20 / 400 / 8,902, plus 197,281 at depth 4 behind `CHESS_PERFT_DEEP=1` or `--deep`), "Kiwipete" (48 / 2,039, castling/pin heavy) and CPW position 3 (14 / 191 / 2,812, en passant/pin heavy), all driven through the same `move()` / `prepare_board_state_for_next_move()` / `undo_last_move()` path minimax uses. Runs in a few seconds by default; part of `pytest tests`. It found and led to fixing item 1.10 on its very first run.
- **Timing benchmark** — ✅ IMPLEMENTED as `tests/benchmark_ai.py` (not a pytest test; run directly, optionally passing depths: `python .\tests\benchmark_ai.py 2 3`). Measures `best_move()` wall time and `moves_analyzed` at each depth from the start position and a Giuoco Piano middlegame. Baseline on this machine (2026-08-04, before performance work): startpos depth 2 = 8.0 s / 24,825 moves; middlegame depth 2 = 10.7 s / 37,139 moves; **startpos depth 3 = 311 s / 728,887 moves; middlegame depth 3 = 823 s / 1,272,509 moves**. These are the numbers the section 2 quick wins should be measured against.
  After item 2.2 (2026-08-04): startpos depth 2 = 4.2 s; middlegame depth 2 = 7.5 s; **startpos depth 3 = 138 s; middlegame depth 3 = 239 s** (identical `moves_analyzed` and chosen moves).
  After items 2.3/2.5/2.6 (2026-08-04): startpos depth 2 = 3.7 s; middlegame depth 2 = 6.6 s; **startpos depth 3 = 123 s; middlegame depth 3 = 226 s** (identical `moves_analyzed` and chosen moves).
  After item 2.1, alpha-beta (2026-08-04): startpos depth 2 = 0.27 s / 1,007 moves; middlegame depth 2 = 0.37 s / 1,380 moves; **startpos depth 3 = 4.5 s / 5,031 moves; middlegame depth 3 = 4.8 s / 4,140 moves** (chosen moves may differ from the pre-ordering runs only among equal-score ties, because move ordering changes which equal-best move is found first).
- **Alpha-beta equivalence** — ✅ IMPLEMENTED as `tests/test_alpha_beta.py`: runs `best_move()` twice from identical positions (`AI(pruning=False)` plain minimax vs `AI(pruning=True)`) and asserts identical root score and chosen move, with `moves_analyzed` never higher when pruning (pruning must never change the result, only the work). Covers startpos and the Giuoco Piano middlegame at depth 1, startpos at depth 2; the slow middlegame depth 2 comparison is gated behind `CHESS_AB_DEEP=1` / `--deep`. Part of `pytest tests`.
- **Elo estimation** — ✅ IMPLEMENTED as `tools/elo_estimate.py` (standalone; requires `pip install python-chess` and a Stockfish binary — `winget install Stockfish.Stockfish`, `--stockfish PATH`, or `STOCKFISH_PATH`). Plays rated games against Stockfish limited to calibrated strengths (`UCI_LimitStrength`/`UCI_Elo`, floor 1320) through `python-chess`, which also serves as the source of truth for legality and game termination; the app's board is mirrored ply-by-ply with a desync guard, so every rated game doubles as a movegen cross-check. The rating is a maximum-likelihood logistic fit over all games with a 95% CI (`--selftest` verifies the math). Runs append to `tools/elo_history.csv` (date, commit, depth, W/D/L per level, estimate) — the strength progress log. Usage: `python .\tools\elo_estimate.py` (100 games, ~30 min at depth 2), `--quick` for a rough 20-game run, `--depth/--levels/--games/--movetime/--seed` to customize. **First measurement (2026-08-05, depth 2, 19 games): ~1190 Elo (95% CI 952-1382)** — 40% vs SF1320, 0% vs SF1700.
- **Manual sanity** — play a full game vs AI checking specifically: queenside castling works for both colors; castling is refused while in check or through an attacked square; en passant is only available on the immediately following move; no sliding piece ever moves through the enemy king.
