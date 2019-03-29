#!/usr/bin/env python
#-*- coding: utf-8 -*-

import sys, os
import termios, fcntl
import select
import signal
import threading
import time
from o2locktoplib.retry import retry
from o2locktoplib import config
from o2locktoplib import util

oldterm = None
oldflags = None
fd = sys.stdin.fileno()

def set_terminal():
    global oldterm,oldflags
    oldterm = termios.tcgetattr(fd)
    oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)

    newattr = termios.tcgetattr(fd)
    newattr[3] = newattr[3] & ~termios.ICANON
    newattr[3] = newattr[3] & ~termios.ECHO
    termios.tcsetattr(fd, termios.TCSANOW, newattr)

    fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)
    if util.cmd_is_exist("setterm")[0]:
        os.system('setterm -cursor off')

class Keyboard():
    def __init__(self):
        pass

    @retry(10,delay=False)
    def _getchar(self):    
        inp, outp, err = select.select([sys.stdin], [], [])
        c = sys.stdin.read()
        return c

    def run(self, printer_queue):
        set_terminal()
        while True:
            try:
                c = self._getchar()
            except Exception as e:
                printer_queue.put({'msg_type':'quit',
                                    'what':'1'})
                print(e)
                break

            if c == 'q':
                printer_queue.put({'msg_type':'quit',
                                    'what':'1'})
                break

            if c == 'd':
                rows, cols = os.popen('stty size', 'r').read().split()
                if int(cols) < config.COLUMNS:
                    rows = (int(rows)//2 - 4)
                else:
                    rows = (int(rows) - 6)
                printer_queue.put({'msg_type':'kb_hit',
                                   'what':'detial',
                                   'rows':rows})

            if c == '2':
                printer_queue.put({'msg_type':'kb_hit',
                                    'what':'debug'})
            time.sleep(0.1)

        # Reset the terminal:
        reset_terminal()

def reset_terminal():
    if oldterm:
        termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
    if oldflags:
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)
    if util.cmd_is_exist("setterm")[0]:
        os.system('setterm -cursor on')
    

def worker(printer_queue):
    kb = Keyboard()
    kb.run(printer_queue)


if __name__ == '__main__':
    worker(None)
