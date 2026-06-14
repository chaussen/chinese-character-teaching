"""Centralized filesystem paths, resolved relative to this package.

Importing anything from ``chinese_tools`` works regardless of the current
working directory, so tools can be launched with e.g.::

    python -m chinese_tools.cards.worksheet_maker --file worksheets/yr1_chars.txt
"""
import os

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(PACKAGE_DIR)

DATA_DIR = os.path.join(PACKAGE_DIR, "data")
FONTS_DIR = os.path.join(PACKAGE_DIR, "fonts")
GB2312_FONT = os.path.join(FONTS_DIR, "GB2312.ttf")

WORKSHEETS_DIR = os.path.join(ROOT, "worksheets")
OUTPUT_DIR = os.path.join(ROOT, "generated")  # scratch output (git-ignored)
