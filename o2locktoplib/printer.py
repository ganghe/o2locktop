#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import print_function
import multiprocessing
import os, sys
from o2locktoplib import util
from o2locktoplib import config
from o2locktoplib import keyboard
from o2locktoplib.retry import retry

SIMPLE_DISPLAY=0
DETAILED_DISPLAY=1

class Printer():
    def __init__(self, log):
        self.content = None
        self.display_mode = SIMPLE_DISPLAY
        self.should_stop = False
        self.log = None
        if log is not None:
            self.log = open(log, 'w')
        self.prelude = None
    @retry(10)
    def _refresh(self,rows):
        # if the stdout not point to the tty
        if util.LINUX and os.major(os.fstat(sys.stdout.fileno()).st_dev) != 0:
            print("unknow line in test case")
            print("unknow line in test case")
        if self.content:
            if(config.clear):
                util.clear_screen()
            if self.prelude:
                print(self.prelude)
            if rows == 0:
                print(self.content[self.display_mode])
            else:
                for i in self.content[self.display_mode].split('\n')[:rows+4]:
                    print(i)

                

    def activate(self, simple_content, detailed_content):
        #self.content = (copy.deepcopy(simple_content), copy.deepcopy(detailed_content))
        self.content = (simple_content, detailed_content)
    def toggle_display_mode(self):
        if self.display_mode == SIMPLE_DISPLAY:
            self.set_display_mode(DETAILED_DISPLAY)
        else:
            self.set_display_mode(SIMPLE_DISPLAY)

    def set_display_mode(self, mode):
        assert(mode in [SIMPLE_DISPLAY, DETAILED_DISPLAY])
        self.display_mode = mode

    @retry(10)
    def run(self, printer_queue, **kargs):
        self.prelude = "{0} {1} lockspace: {2}".format(config.VERSION, kargs['mount_info'], config.UUID)

        if self.log:
            self.log.write(self.prelude+"\n")
        while not self.should_stop:
            obj = printer_queue.get()
            msg_type = obj['msg_type']
            if msg_type == 'kb_hit':
                what = obj['what']
                if what == 'detial':
                    self.toggle_display_mode()
                    self._refresh(obj['rows'])
                # TODO
                if what == 'debug':
                    pass
                    
            elif msg_type == 'new_content':
                self.activate(obj['simple'], obj["detailed"])
                self._refresh(obj['rows'])
                if self.log:
                    self.log.write(self.content[self.display_mode])
                    self.log.write('\n\n\n')
                    self.log.flush()
            elif msg_type == 'quit':
                break

def worker(printer_queue, log, **kargs):
    printer = Printer(log)
    try:
        printer.run(printer_queue, **kargs)
    except KeyboardInterrupt:
        #keyboard.reset_terminal()
        pass
    except:
        import traceback
        print(traceback.format_exc())
        if log is not None:
            printer.log.close()
