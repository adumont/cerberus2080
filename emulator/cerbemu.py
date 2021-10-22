#!/usr/bin/env python3

import os
import time
import curses
import threading
import signal
import locale
from disass import render_instr
from queue import Queue

import argparse

from py65.devices.mpu65c02 import MPU as CMOS65C02
from py65.utils.conversions import itoa
from py65.memory import ObservableMemory

# Argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('-r','--rom', help='binary rom file', default="forth.bin")
parser.add_argument('-a','--addr', help='address to load to', default=0xC000)
args = parser.parse_args()


locale.setlocale(locale.LC_ALL, '')
code = locale.getpreferredencoding()

exit_event = threading.Event()

addr_W    = 0x00FE
addr_IP	  = addr_W -2
addr_G2	  = addr_IP-2
addr_G1	  = addr_G2-2
addr_LINE = addr_G1-2
addr_ROW  = addr_LINE - 1
addr_COL  = addr_ROW - 1
addr_DTOP = addr_COL-2

addr_MAILFLAG   = 0x0200
addr_MAILBOX    = addr_MAILFLAG +1
addr_LATEST 	= addr_MAILBOX  +1
addr_MODE       = addr_LATEST +2
addr_BOOT       = addr_MODE +1
addr_BOOTP      = addr_BOOT +1
addr_ERROR      = addr_BOOTP +2
addr_INP_LEN    = addr_ERROR + 1
addr_INPUT      = addr_INP_LEN +1
addr_INP_IDX    = addr_INPUT + 128
addr_OK         = addr_INP_IDX + 1
addr_DP         = addr_OK +1

def cpuThreadFunction(ch,win,dbgwin, queue, queue_step):

    started=False

    hist_depth = 8

    instr = hist_depth*[""]

    def load(memory, start_address, bytes):
        memory[start_address:start_address + len(bytes)] = bytes

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


    def disass_pane(mode, instr):
            # if mode == 0:
            #     return

        dbgwin.addstr(0,0, "PC: %04X Cycles: %d" % ( mpu.pc, mpu.processorCycles ) )

        dbgwin.addstr(2,0, "A:%02X  X:%02X  Y:%02X  S:%02X  P:%s" % ( mpu.a, mpu.x, mpu.y, mpu.sp, ( itoa(mpu.p, 2).rjust(8, '0') ) ) )

        dbgwin.addstr(4,0, "LINE: %04X ROW: %02X COL: %02X " % ( getWord(addr_LINE), getByte(addr_ROW), getByte(addr_COL) ) )

        _w=getWord(addr_W)
        _ip=getWord(addr_IP)
        dbgwin.addstr(6,0, " W: %04X  IP: %04X" % ( _w, _ip ) )

        dbgwin.addstr(7,0, "G1: %04X  G2: %04X" % ( getWord(addr_G1), getWord(addr_G2) ) )

        dbgwin.addstr(8,0, "LATEST: %04X  DP: %04X" % ( getWord(addr_LATEST), getWord(addr_DP) ) )

        if mode == 1:
            instr.append( render_instr( [ "%04X" % mpu.pc, "%02X" % getByte(mpu.pc), "%02X" % getByte(mpu.pc+1), "%02X" % getByte(mpu.pc+2) ] ) )
            instr = instr[-hist_depth:] # keep last "hist_depth"
            for i in range(len(instr)):
                dbgwin.addstr(11+i,0, instr[i] )
        
        dbgwin.noutrefresh()


    def nmi():
        # triggers a NMI IRQ in the processor
        # this is very similar to the BRK instruction
        mpu.stPushWord(mpu.pc)
        mpu.p &= ~mpu.BREAK
        mpu.stPush(mpu.p | mpu.UNUSED)
        mpu.p |= mpu.INTERRUPT
        mpu.pc = mpu.WordAt(mpu.NMI)
        mpu.processorCycles += 7


    mpu = CMOS65C02()
    mpu.memory = 0x10000 * [0xEA]
    mpu.memory[0xF800:0xFCAF] =  (0xFCAF-0xF800+1)* [0x20]

    addrWidth = mpu.ADDR_WIDTH

    m = ObservableMemory(subject=mpu.memory, addrWidth=addrWidth)
    m.subscribe_to_write(range(0xF800,0xF800+30*40), vram_write)
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

    # as we have stripped the vectors out of the binary, we need to populate
    # the RESET vector, as CAT(BIOS) does.
    mpu.memory[0xFFFC] = (args.addr & 0xFF)
    mpu.memory[0xFFFD] = ( args.addr >> 8 ) & 0xFF

    # Reset: RESET vector => PC
    mpu.pc=getWord(mpu.RESET)

    started=True

    delay=0
    # delay=1

    dbgwin.addstr(1,26, "NV-BDIZC" )

    # mode_step = 0       # continuous execution
    mode_step = 1       # step by step execution

    disass_pane(mode_step, instr)
    curses.doupdate()

    run_next_step = 0

    while not exit_event.is_set():
        if not queue_step.empty():
            mode_step = queue_step.get()
            if mode_step == 0:  # back to continuous mode: we clear the disass part
                instr = hist_depth*[38*" "]
                for i in range(len(instr)):
                    dbgwin.addstr(11+i,0, instr[i] )                
            
            run_next_step = 1

        if mode_step == 1 and run_next_step == 0:
            continue

        if mode_step == 1:
            run_next_step = 0

        mpu.step()

        # any key pressed?
        if mpu.memory[0x0200] == 0 and not queue.empty():
            mpu.memory[0x0200]=1
            mpu.memory[0x0201]=queue.get()
            nmi()

        disass_pane(mode_step, instr)

        curses.doupdate()
        time.sleep(delay)

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
    queue_step = Queue()

    # create computer thread
    t=threading.Thread( target=cpuThreadFunction, args=("", cpuwin, dbgwin, queue, queue_step) )
    t.start()

    # main thread for getting keypress
    while True:
        # wait for a character; returns an int; does not raise an exception.
        key = stdscr.getch()

        if key == 0x152:    # Page DOWN
            # Enter step by step mode
            queue_step.put(1)
        elif key == 0x168:    # End key
            # Continuous execution
            queue_step.put(0)
        elif key == 0x1b:
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