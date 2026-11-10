# Color Under Pressure for Android: turn on the phone layer, then run the game exactly as on a computer.
import os, sys, runpy

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
os.chdir(here)

import android_shim
android_shim.install()

# the Android build ships compiled files: color_rush.pyc instead of color_rush.py
game = os.path.join(here, 'color_rush.py')
if not os.path.exists(game):
    game += 'c'
runpy.run_path(game, run_name='__main__')
