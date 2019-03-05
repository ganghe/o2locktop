import pytest
from o2locktoplib import keyboard
import o2locktoplib.util as util
import config
import termios, fcntl
import sys
import os

fd = sys.stdin.fileno()

def test_init():
    assert not keyboard.oldterm and not keyboard.oldflags

def test_set_terminal():
    keyboard.set_terminal()
    try:
        assert keyboard.oldterm and keyboard.oldflags
        assert not (termios.tcgetattr(fd)[3] & termios.ICANON)
        assert not (termios.tcgetattr(fd)[3] & termios.ECHO)
        assert (fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK)
    finally:
        keyboard.reset_terminal()

def test_reset_terminal():
    keyboard.set_terminal()
    oldterm = keyboard.oldterm
    oldflags = keyboard.oldflags
    keyboard.reset_terminal()
    assert oldterm == termios.tcgetattr(fd)
    assert oldflags == fcntl.fcntl(fd, fcntl.F_GETFL)
    assert keyboard.oldterm and keyboard.oldflags
