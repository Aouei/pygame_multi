import sys, os

if __name__ != '__main__':
    if getattr(sys, "frozen", False):
        BASE_DIR = sys._MEIPASS
    else:
        BASE_DIR = os.path.join(os.path.dirname(__file__), "..")

    ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
    PLAYER_DIR  = os.path.join(ASSETS_DIR, "player")
    TILES_DIR   = os.path.join(ASSETS_DIR, "tiles")
    MAP_PATH    = os.path.join(ASSETS_DIR, "map", "map.csv")
    SPRITE_PATH = os.path.join(ASSETS_DIR, "nave.png")