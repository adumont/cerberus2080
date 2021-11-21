#!/usr/bin/env python3

import os
import time
import locale

import argparse

from py65.devices.mpu65c02 import MPU as CMOS65C02
from py65.utils.conversions import itoa
from py65.memory import ObservableMemory

from collections import defaultdict
from disass import decode

# Argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('-r','--rom', help='binary rom file', default="forth.bin")
parser.add_argument('-a','--addr', help='address to load to', default=0xC000)
parser.add_argument('-l','--logfile', help='filename of log', default=None)
parser.add_argument('-s','--symbols', help='symbols file', default="forth.lbl")
parser.add_argument('-t','--trace', help='trace file', default=None)
args = parser.parse_args()

locale.setlocale(locale.LC_ALL, '')
code = locale.getpreferredencoding()

def load(memory, start_address, bytes):
    memory[start_address:start_address + len(bytes)] = bytes

def getByte(address):
    return mpu.memory[address]

def getWord(address):
    return mpu.memory[address] + 256*mpu.memory[address+1]

symbols = None

def parseSymbolsFile(filename):
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
    l = symbols[max(k for k in symbols if (k <= addr and not symbols[k]. startswith("@")))]
    sl  = symbols[max(k for k in symbols if k <= addr)]
    if sl == l:
        sl=""
    return l,sl

def getLabelAddr(label):
    return [ k for k in symbols if symbols[k] == label ][0]

mpu = CMOS65C02()
mpu.memory = 0x10000 * [0xEA]
mpu.memory[0xF800:0xFCAF] =  (0xFCAF-0xF800+1)* [0x20]

addrWidth = mpu.ADDR_WIDTH

m = ObservableMemory(subject=mpu.memory, addrWidth=addrWidth)
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

if args.symbols:
    symbols=parseSymbolsFile(args.symbols)

load(mpu.memory, args.addr, program)

# as we have stripped the vectors out of the binary, we need to populate
# the RESET vector, as CAT(BIOS) does.
mpu.memory[0xFFFC] = (args.addr & 0xFF)
mpu.memory[0xFFFD] = ( args.addr >> 8 ) & 0xFF

# Reset: RESET vector => PC
mpu.pc=getWord(mpu.RESET)

stats=0x10000 * [0]

last_processorCycles = 0
last_pc=0

addr_BOOT = getLabelAddr("BOOT")

if args.trace:
    file = open("/tmp/stats", "w")

while True:
    # print("%04X %04X %d" % (mpu.pc, last_pc, mpu.processorCycles-last_processorCycles))
    # input("key")
    stats[last_pc] += mpu.processorCycles-last_processorCycles

    opcode, mode, _ = decode(getByte(last_pc))

    label, sublabel=getSymbol(last_pc)

    c = '.' if mpu.a < 32 or mpu.a > 126 else mpu.a

    if args.trace:
        file.write("%d %04X %s %02X %c %02X %02X %d %s %s\n" % ( mpu.processorCycles, last_pc, opcode, mpu.a, c, mpu.x, mpu.y, mpu.processorCycles-last_processorCycles, label, sublabel ) )

    last_processorCycles = mpu.processorCycles
    last_pc = mpu.pc

    mpu.step()

    if mpu.memory[addr_BOOT] == 0:
        break

if args.trace:
    file.close()

print("processorCycles:", mpu.processorCycles)

label_stats = defaultdict(int)

for a in range(0x10000):

    if stats[a]>0:
        label, sublabel=getSymbol(a)

        # print("%04X %d %s" % (a, stats[a], tmp_label))
        label_stats[label]+=stats[a]

for a in sorted(label_stats, key=label_stats.get, reverse=True):
    print("%s %d" % ( a, label_stats[a] ))