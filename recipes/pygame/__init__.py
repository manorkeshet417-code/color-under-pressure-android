# python-for-android ships pygame 2.1.0, whose generated C code doesn't build with Python 3.11
# ("longintrepr.h not found"). pygame 2.1.3 fixed that; everything else about the recipe stays the same.
from pythonforandroid.recipes.pygame import Pygame2Recipe


class PygameRecipe213(Pygame2Recipe):
    version = '2.1.3'


recipe = PygameRecipe213()
