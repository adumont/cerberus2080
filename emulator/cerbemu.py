#!/usr/bin/env python3

# Cerbemu
#
# Copyright (C) 2021-2023 Alexandre Dumont <adumont@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-only

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
parser.add_argument('-r','--rom', help='binary rom file', default="forth-emu.bin")
parser.add_argument('-a','--addr', help='address to load to', default=0xC000)
parser.add_argument('-l','--logfile', help='filename of log', default=None)
parser.add_argument('-s','--symbols', help='symbols file', default="forth-emu.lbl")
parser.add_argument('-b','--breakpoint', help='set breakpoint (symbol)', default="do_BREAK")
args = parser.parse_args()

# stats = open("/tmp/stats", "w")  # a=append mode

locale.setlocale(locale.LC_ALL, '')
code = locale.getpreferredencoding()

exit_event = threading.Event()

symbols = None

def parseSymbolsFile(filename):
    # file content should look like this:
    # al 00C23D .do_PUSH1
    # al 00C239 .__word_12
    # al 00C239 .h_PUSH1
    # al 00C22E .__word_11
    symbols = {}
    with open(filename) as file:
        for line in file:
            _, a, s = line.split(" ")
            if s.startswith(".__word_") or s.startswith(".h_"):
                # we discard those symbols
                continue
            symbols[int(a,16)]=s.strip()[1:]
    return symbols

def getSymbol(addr):
    return symbols[max(k for k in symbols if k <= addr)]

def getLabelAddr(label):
    return [ k for k in symbols if symbols[k] == label ][0]

if args.symbols:
    symbols=parseSymbolsFile(args.symbols)

addr_W    = 0x00FE
addr_IP          = addr_W -2
addr_G2          = addr_IP-2
addr_G1          = addr_G2-2
addr_DP          = addr_G1-2
addr_LINE = addr_DP-2
addr_ROW  = addr_LINE - 1
addr_COL  = addr_ROW - 1
addr_DTOP = addr_COL-2

addr_MAILFLAG   = getLabelAddr("MAILFLAG")
addr_MAILBOX    = getLabelAddr("MAILBOX")
addr_LATEST 	= getLabelAddr("LATEST")
addr_MODE       = getLabelAddr("MODE")
addr_BOOT       = getLabelAddr("BOOT")
addr_BOOTP      = getLabelAddr("BOOTP")
addr_ERROR      = getLabelAddr("ERROR")
addr_INP_LEN    = getLabelAddr("INP_LEN")
addr_INPUT      = getLabelAddr("INPUT")
addr_INP_IDX    = getLabelAddr("INP_IDX")
addr_OK         = getLabelAddr("OK")

def cpuThreadFunction(ch,win,dbgwin, queue, queue_step, logfile):
    global symbols

    started=False

    hist_depth = 8

    instr = hist_depth*[""]

    symbol_depth=3
    syms = symbol_depth*[""]

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


    def disass_pane(mode, instr, syms):
        dbgwin.addstr(0,10, "Cycles: %d" % mpu.processorCycles )

        log_registers = "A:%02X  X:%02X  Y:%02X  S:%02X  P:%s" % ( mpu.a, mpu.x, mpu.y, mpu.sp, ( itoa(mpu.p, 2).rjust(8, '0') ) )

        _w=getWord(addr_W)
        _ip=getWord(addr_IP)
        log_forth_reg1 = " W: %04X  IP: %04X" % ( _w, _ip )

        _here = getWord(addr_DP)
        dbgwin.addstr(8,0, "LATEST: %04X  DP: %04X" % ( getWord(addr_LATEST), _here ) )

        curr_instr = render_instr( [ "%04X" % mpu.pc, "%02X" % getByte(mpu.pc), "%02X" % getByte(mpu.pc+1), "%02X" % getByte(mpu.pc+2) ] )
        if symbols:
            curr_instr += getSymbol(mpu.pc)

        if logfile:
            logfile.write(" | ".join([log_registers, log_forth_reg1, curr_instr]) + "\n")

        # stats.write("%10d %s\n" % ( mpu.processorCycles, curr_instr ) )

        if mode == 1: #step-by-step mode
            # these registers will only be updated in step-by-step mode
            dbgwin.addstr(0, 0, "PC: %04X" % mpu.pc )

            dbgwin.addstr(2,0, log_registers )

            dbgwin.addstr(4,0, "LINE: %04X ROW: %02X COL: %02X " % ( getWord(addr_LINE), getByte(addr_ROW), getByte(addr_COL) ) )

            log_forth_reg2 = "G1: %04X  G2: %04X" % ( getWord(addr_G1), getWord(addr_G2) )
            dbgwin.addstr(6,4, log_forth_reg1 )
            dbgwin.addstr(7,4, log_forth_reg2 )

            # Show disassembled code
            instr.append( curr_instr )
            instr = instr[-hist_depth:] # keep last "hist_depth"
            for i in range(len(instr)):
                dbgwin.addstr(12+i,0, (instr[i]+10*" ")[0:40] )

            # Show some bytes before HERE
            for j in [1,0]:
                a=_here-9-10*j
                dbgwin.addstr(10-j, 0, "%04X:" % (a) )
                for i in range(10):
                    dbgwin.addstr(10-j, 6+3*i, "%02X" % getByte( a+i ) )

            # Show Data Stack
            for i in range(5):
                a = mpu.x + 2*i
                v = getWord(a)
                if a<=addr_DTOP:
                    dbgwin.addstr(28-i, 0, "%d %04X: %04X" % (i, a, v) )
                else:
                    dbgwin.addstr(28-i, 0, "             " )

            # Show 6502 Stack
            for i in range(5):
                a = 0x100 + mpu.sp + i + 1
                v = getByte(a)
                if a<=0x1FF:
                    dbgwin.addstr(28-i, 20, "%02X: %02X" % (a & 0xFF, v) )
                else:
                    dbgwin.addstr(28-i, 20, "       " )

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

    disass_pane(mode_step, instr, syms)
    curses.doupdate()

    run_next_step = 0

    while not exit_event.is_set():
        if mpu.pc == getLabelAddr(args.breakpoint) or mpu.pc == getLabelAddr("do_BREAK"): # breakpoint
            queue_step.put(1)

        if not queue_step.empty():
            mode_step = queue_step.get()
            
            run_next_step = 1

        if mode_step == 1 and run_next_step == 0:
            continue

        if mode_step == 1:
            run_next_step = 0

        # stats.write("%d %04X" % ( mpu.pc, mpu.processorCycles ) )

        mpu.step()

        # any key pressed?
        if mpu.memory[0x0200] == 0 and not queue.empty():
            mpu.memory[0x0200]=1
            mpu.memory[0x0201]=queue.get()
            nmi()

        disass_pane(mode_step, instr, syms)

        curses.doupdate()
        time.sleep(delay)

def exit():
    exit_event.set()

    curses.nocbreak()
    curses.echo()
    curses.endwin()

    quit()

def main(stdscr):
    global symbols

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

    if args.logfile:
        logfile = open(args.logfile, "w")  # a=append mode
    else:
        logfile=None

    # create computer thread
    t=threading.Thread( target=cpuThreadFunction, args=("", cpuwin, dbgwin, queue, queue_step, logfile) )
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
