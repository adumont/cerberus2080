#!/usr/bin/env python3

import sys
import os
import time
import curses
import threading
import signal
import locale
from queue import Queue

import argparse

from py65.devices.mpu65c02 import MPU as CMOS65C02
from py65.memory import ObservableMemory
from py65.utils import console

# Argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('-r','--rom', help='binary rom file', default="forth.bin")
parser.add_argument('-a','--addr', help='address to load to', default=0x8000)
args = parser.parse_args()


locale.setlocale(locale.LC_ALL, '')
code = locale.getpreferredencoding()

exit_event = threading.Event()

def cpuThreadFunction(ch,win,dbgwin, queue):

    started=False

    def load(memory, start_address, bytes):
        memory[start_address:start_address + len(bytes)] = bytes

    def variable_write(address, value):
        dbgwin.addstr(0,0, "LINE: %04X ROW: %02X COL: %02X " % ( getWord(0x00FE), getByte(0x00FE-1), getByte(0x00FE-2) ) )
        dbgwin.noutrefresh()
        curses.doupdate()

    def vram_write(address, value):
        if not started:
            return

        address -= 0xF800
        x,y = divmod(address,40)
        if value == 0:
            value = 0x20
        try:
            win.addstr(x,y, chr(value))
            win.noutrefresh()
            curses.doupdate()
        except curses.error:
            pass

    def getByte(address):
        return mpu.memory[address]

    def getWord(address):
        return mpu.memory[address] + 256*mpu.memory[address+1]

    mpu = CMOS65C02()
    mpu.memory = 0x10000 * [0xEA]

    addrWidth = mpu.ADDR_WIDTH

    m = ObservableMemory(subject=mpu.memory, addrWidth=addrWidth)
    m.subscribe_to_write(range(0xF800,0xF800+30*40), vram_write)
    m.subscribe_to_write(range(0x00FF-4,0x00FF), variable_write)
    mpu.memory = m

    if args.addr and str(args.addr).startswith("0x"):
        args.addr = int(args.addr,16)

    if args.rom:
        f = open(args.rom, 'rb')
        program = f.read()
        f.close()
    else:
        # Dummy prog
        program = [ 0xA9, 97, 0x8D, 0x01, 0xF0 ]

    load(mpu.memory, args.addr, program)

    # Reset: RESET vector => PC
    mpu.pc=getWord(mpu.RESET)

    started=True

    while not exit_event.is_set():
        mpu.step()

        # any key pressed?
        if mpu.memory[0x0200] == 0 and not queue.empty():
            mpu.memory[0x0200]=1
            mpu.memory[0x0201]=queue.get()

        time.sleep(0.0001)
        # time.sleep(0.1)

def exit():
    exit_event.set()

    curses.nocbreak()
    curses.echo()
    curses.endwin()

    quit()

def main(stdscr):
    if curses.has_colors() == True:
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1,curses.COLOR_GREEN ,curses.COLOR_BLUE)
        curses.init_pair(2,curses.COLOR_WHITE ,curses.COLOR_RED)
        curses.init_pair(3,curses.COLOR_WHITE ,curses.COLOR_BLACK)
        stdscr.bkgd(' ',curses.color_pair(1))

    curses.curs_set(0)      # cursor off.
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)     # receive special messages.

    # instantiate a small window to hold responses to keyboard messages.
    msgwin = curses.newwin(1,40,30,0)
    msgwin.bkgd(' ',curses.color_pair(2))

    # instantiate a small window to hold computer screen
    cpuwin = curses.newwin(30,40,0,0)
    cpuwin.bkgd(' ',curses.color_pair(3))

    # instantiate a small window to hold computer screen
    dbgwin = curses.newwin(30,38,0,42)
    dbgwin.bkgd(' ',curses.color_pair(3))
    dbgwin.erase()

    stdscr.noutrefresh()
    msgwin.noutrefresh()
    cpuwin.noutrefresh()
    dbgwin.noutrefresh()
    curses.doupdate()

    queue = Queue()

    # create computer thread
    t=threading.Thread( target=cpuThreadFunction, args=("", cpuwin, dbgwin, queue) )
    t.start()

    # main thread for getting keypress
    while True:
        # wait for a character; returns an int; does not raise an exception.
        key = stdscr.getch()

        if key == 0x1b:
            # escape key exits
            msgwin.erase()
            msgwin.addstr(0,0, 'Exiting...')
            exit_event.set()
            msgwin.noutrefresh()
            curses.doupdate()
            time.sleep(0.2)
            break
        else:
            msgwin.erase()
            if key == 0x0A :
                msgwin.addstr(0,0, 'received [$%02X]' % (key) )
            else:
                msgwin.addstr(0,0, 'received [%s] [$%02X]' % (chr(key) , key) )

            if key in (0x7f, 0x107):
                key=8

            queue.put(key)
            
        msgwin.noutrefresh()
        curses.doupdate()


    msgwin.erase()
    msgwin.addstr(0, 0, 'Press any key to exit')
    msgwin.noutrefresh()

    curses.doupdate()

    stdscr.getkey()

    stdscr.keypad(False)
    exit()

def signal_handler(signum, frame):
    exit()

if __name__ == '__main__':
    # Must happen BEFORE calling the wrapper, else escape key has a 1 second delay after pressing:
    os.environ.setdefault('ESCDELAY','100') # in mS; default: 1000
    signal.signal(signal.SIGINT, signal_handler)
    curses.wrapper(main)