"""Path hack to make tests work."""
import sys
import os
sys.path.append('../locals/')
sys.path.append('../common/')
sys.path.append('../kahoot/')


def show_real_path():
    print(os.path.dirname(os.path.realpath('.')).split(os.sep))
# modpath = os.sep.join(bp + ['src'])
# sys.path.insert(0, modpath)
