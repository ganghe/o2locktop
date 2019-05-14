'''
import sys
sys.path.append("../")
from tempfile import TemporaryFile
import pytest
from o2locktoplib import keyboard
import o2locktoplib.util as util
if util.PY2:
    from Queue import Queue
else:
    from queue import Queue
import config
import termios, fcntl
import sys
import os

#fd = TemporaryFile("w+t").fileno()
fd = 0

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
        keyboard.reset_terminal(fd=fd)

def test_reset_terminal():
    keyboard.set_terminal()
    oldterm = keyboard.oldterm
    oldflags = keyboard.oldflags
    keyboard.reset_terminal(fd=fd)
    assert oldterm == termios.tcgetattr(fd)
    assert oldflags == fcntl.fcntl(fd, fcntl.F_GETFL)
    assert keyboard.oldterm and keyboard.oldflags

def test_Keyboard():
    def worker(fd):
        fd.write('d')
        time.sleep(0.5)
        fd.write('q')
    sys.stdin = TemporaryFile("w+t")
    queue = Queue()
    keyboard = util.Keyboard()

    thread = threading.Thread(target=worker, args=(sys.stdin,))
    thread.daemon = true
    thread.start()
    keyboard.run(queue)
    print(queue.get())
    print(queue.get())
'''
