#!/usr/bin/env python
#-*- coding: utf-8 -*-

"""
The o2locktop library

It can set the terminal as o2locktop requird.
"""
import sys
import os
import termios
import fcntl
import select
import time
from o2locktoplib.retry import retry
from o2locktoplib import config
from o2locktoplib import util

OLDTERM = None
OLDFLAG = None

def set_terminal():
    """
    Set the terminal hid the input
    """
    global OLDTERM, OLDFLAG
    file_dec = sys.stdin.fileno()
    OLDTERM = termios.tcgetattr(file_dec)
    OLDFLAG = fcntl.fcntl(file_dec, fcntl.F_GETFL)

    newattr = termios.tcgetattr(file_dec)
    newattr[3] = newattr[3] & ~termios.ICANON
    newattr[3] = newattr[3] & ~termios.ECHO
    termios.tcsetattr(file_dec, termios.TCSANOW, newattr)

    fcntl.fcntl(file_dec, fcntl.F_SETFL, OLDFLAG | os.O_NONBLOCK)
    if util.cmd_is_exist("setterm")[0]:
        os.system('setterm -cursor off')

class Keyboard():
    """
    The main class of this file
    """
    def __init__(self):
        pass

    @retry(10, delay=False)
    def _getchar(self):
        """
        Get the input character from input by select
        """
        _, _, _ = select.select([sys.stdin], [], [])
        character = sys.stdin.read()
        return character

    def run(self, printer_queue):
        """
        The main method that will run in o2locktop and wait for the user's input
        """
        set_terminal()
        while True:
            try:
                character = self._getchar()
            except Exception as expt:
                printer_queue.put({'msg_type':'quit',
                                   'what':'1'})
                print(expt)
                break

            if character == 'q':
                printer_queue.put({'msg_type':'quit',
                                   'what':'1'})
                break

            if character == 'd':
                rows, cols = os.popen('stty size', 'r').read().split()
                if int(cols) < config.COLUMNS:
                    rows = (int(rows)//2 - 4)
                else:
                    rows = (int(rows) - 6)
                printer_queue.put({'msg_type':'kb_hit',
                                   'what':'detial',
                                   'rows':rows})

            if character == '2':
                printer_queue.put({'msg_type':'kb_hit',
                                   'what':'debug'})
            time.sleep(0.1)

        # Reset the terminal:
        reset_terminal()

def reset_terminal():
    """
    This function will recover the terminal
    """
    file_dec = sys.stdin.fileno()
    if OLDTERM:
        termios.tcsetattr(file_dec, termios.TCSAFLUSH, OLDTERM)
    if OLDFLAG:
        fcntl.fcntl(file_dec, fcntl.F_SETFL, OLDFLAG)
    if util.cmd_is_exist("setterm")[0]:
        os.system('setterm -cursor on')


def worker(printer_queue):
    """
    The method that will be called in o2locktop
    """
    keyboard = Keyboard()
    keyboard.run(printer_queue)


if __name__ == '__main__':
    worker(None)
