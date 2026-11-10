# Color Under Pressure for Android: turn on the phone layer, then run the game exactly as on a computer.
import os, sys, runpy

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
os.chdir(here)

import android_shim
android_shim.install()

runpy.run_path(os.path.join(here, 'color_rush.py'), run_name='__main__')
