"""Shared settings for the legacy flashcard maker and matching game."""
import os

from chinese_tools.paths import GB2312_FONT, OUTPUT_DIR

# --- cards ---
CARD_SIDE_LENGTH = 460
CARD_GRID_COLOR = (185, 185, 185, 200)
CARD_GRID_WIDTH = 3
CHARACTER_FONT = GB2312_FONT
PINYIN_FONT = "calibri"  # any installed font with tone-marked vowels
CARD_BACKGROUND_COLOR = "white"
PINYIN_FONT_SIZE = 120
CHARACTER_FONT_SIZE = 420
CHARACTER_POSITION = ((CARD_SIDE_LENGTH - CHARACTER_FONT_SIZE) // 2, 10)
CHARACTER_COLOR = "black"
CHARACTER_IMAGE_FILE_NAME_PREFIX = os.path.join(OUTPUT_DIR, "flashcards", "zi_")
PINYIN_IMAGE_FILE_NAME_PREFIX = os.path.join(OUTPUT_DIR, "flashcards", "pinyin_")
CHARACTER_PINYIN_FOLDER = os.path.join(OUTPUT_DIR, "practice") + os.sep

# --- matching game ---
CHARACTER_IMAGES_PATH = os.path.join(OUTPUT_DIR, "characters") + os.sep
FILE_NAME_PATTERN = r"""_(\d+)\.jpg"""
DISPLAY_SIZE = (1000, 900)
CARD_NUMBER = 30
CARD_COLUMN_COUNT = 5
CARD_ROW_COUNT = 6
CARD_WIDTH = DISPLAY_SIZE[0] // CARD_COLUMN_COUNT
CARD_HEIGHT = DISPLAY_SIZE[1] // CARD_ROW_COUNT
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (200, 200, 200)
