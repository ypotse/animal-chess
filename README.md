# 鬥獸棋 — Animal Chess

A browser-based digital remake of **鬥獸棋** (Jungle Chess / Dou Shou Qi) — a childhood classic from Hong Kong, faithfully recreated with retro chessboard art and hand-drawn piece graphics.

## Play

Just open `index.html` in any modern browser. No installation needed.

## How to Play

Two players take turns moving one piece per turn. **Red moves first.**

| Rank | Piece |
|------|-------|
| 8 | Elephant 象 |
| 7 | Lion 獅 |
| 6 | Tiger 虎 |
| 5 | Leopard 豹 |
| 4 | Wolf 狼 |
| 3 | Dog 狗 |
| 2 | Cat 貓 |
| 1 | Rat 鼠 |

**Key rules:**
- Higher rank captures lower rank (except Rat captures Elephant)
- Lion and Tiger can jump over rivers; blocked if a Rat is in the river
- Rat can enter water; only Rat can capture Rat in water (from land)
- Pieces in an opponent's trap lose all rank (capturable by anything)
- **Win** by moving a piece into the opponent's den

## Assets

- `assets/chessboard.png` — retro-style game board
- `assets/piece_*.png` — 16 individual piece images (cut from original spritesheet via `cut_pieces.py`)
- `pieces.png` — original piece spritesheet

## Tech

Plain HTML + Canvas API, no dependencies.
