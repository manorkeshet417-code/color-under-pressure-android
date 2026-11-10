"""Small, exact changes to color_rush.py for the Android build (the original on the computer stays as is).

1. The screen size comes from the phone (android_shim.game_size).
2. Saves and logs go to the app's private folder (kept across updates), not next to the code
   (the code folder is replaced on every update).
Every change must find its spot exactly once; otherwise the build stops, so a change in the game
can't silently break the phone version.
"""
import sys

path = sys.argv[1] if len(sys.argv) > 1 else 'app/color_rush.py'
src = open(path, encoding='utf-8').read()

CHANGES = [
    ('WIDTH, HEIGHT = 900, 700',
     "WIDTH, HEIGHT = __import__('android_shim').game_size(900, 700)"),
    ('def _data_dir():\n',
     'def _data_dir():\n    if os.environ.get("ANDROID_PRIVATE"): return os.environ["ANDROID_PRIVATE"]   # Android: survives updates\n'),
]
for old, new in CHANGES:
    n = src.count(old)
    if n != 1:
        sys.exit(f'patch_game: expected exactly 1 of {old!r}, found {n}')
    src = src.replace(old, new)

open(path, 'w', encoding='utf-8').write(src)
print('patched', path)
