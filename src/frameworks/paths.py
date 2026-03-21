import sys
import os

if __name__ != "__main__":
    if getattr(sys, "frozen", False):
        BASE_DIR = sys._MEIPASS
    else:
        # src/frameworks/ → src/ → project root
        BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")

    ASSETS_DIR = os.path.join(BASE_DIR, "assets")
    PLAYER_DIR = os.path.join(ASSETS_DIR, "player")
    SHIP_DIR = os.path.join(ASSETS_DIR, "enemies", "ship")
    ENEMY_DIR = os.path.join(ASSETS_DIR, "enemies", "dino")
    BULLET_DIR = os.path.join(ASSETS_DIR, "bullets")
    TILES_DIR = os.path.join(ASSETS_DIR, "tiles")
    MAP_PATH = os.path.join(ASSETS_DIR, "map", "shikoku.tmx")
    CASTLE_PATH = os.path.join(ASSETS_DIR, "castle.png")
    BACKGROND_MUSIC_PATH = os.path.join(
        ASSETS_DIR, "music", "Goblins_Den_(Regular).wav"
    )
    BATTLE_MUSIC_PATH = os.path.join(ASSETS_DIR, "music", "Goblins_Dance_(Battle).wav")
