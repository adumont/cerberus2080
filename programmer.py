#!/usr/bin/env python3

import argparse
import serial
import time
import os.path
from time import sleep
import math

from glob import glob

def cmd_send(args):
  l = os.stat(args.file).st_size

  addr = int(args.addr, 16)

  batch = 10

  with open(args.file, "rb") as f:
    count = 0
    while True:
      data=f.read(batch)
      if not data:
        break
      
      print("0x%04X " % addr, end="")
      ser.write( str.encode( "0x%04X " % addr ) )

      chkA=1
      chkB=0

      for c in data:
        print("%02X " % c, end="")
        ser.write( str.encode( "%02X " % c ) )
        chkA = ( chkA +   c  ) % 256
        chkB = ( chkB + chkA ) % 256

      print("#%02X%02X\r" % (chkA, chkB) )
      ser.write( str.encode( "#%02X%02X\r" % (chkA, chkB) ) )

      count += len(data)
      addr  += len(data)



      print("  %3.2f %%" % (100.0*count/l), end="\r")

      sleep(0.05)

      get_response(show=False)

      if count >= l: break

  print()


def get_response(show=False):
  exit = False
  b = []

  while True:
    for c in ser.read():
      if c not in (0x0d, 0x0a):
        b.append(c)
      if show:
        print("%c %02X   " % (c,c), end='', flush=True)
      if c == 0x0A:
        exit = True
        break
    if exit:
      break

  return b


def cmd_run(args):

  print("run")
  ser.write( str.encode( "run\r") )

  print()

parser = argparse.ArgumentParser(
        description='Cerberus2080 Serial Programmer',
        epilog='Written by @adumont')

parser.add_argument('-p', '--port', help='USB port to use', default="/dev/ttyUSB0" )

subparsers = parser.add_subparsers()

parser_put = subparsers.add_parser('send', help='Flash a binary file to Cerberus')
parser_put.add_argument('file', help='File to send')
parser_put.add_argument('-a', '--addr', help='Address (hexadecimal), default: C000', default="C000" )
parser_put.set_defaults(func=cmd_send)

parser_put = subparsers.add_parser('run', help='Send the run command')
parser_put.set_defaults(func=cmd_run)

def wait_for_prompt(show=True, timeout=0):
  prompt = False
  t0=time.time()
  while not prompt:
    t1=time.time()
    if timeout !=0 and 1000*(t1-t0) > timeout:
      break
    for c in ser.read():
      if c == ord(">"):
        prompt = True
        break
      if show:
        print("%c" % c, end='', flush=True)

if __name__ == '__main__':
  args = parser.parse_args()
  print(vars(args))

  if args.port == None:
    port = glob("/dev/ttyACM*")
    assert( len(port) > 0 )
    port = port[0]
  else:
    port = args.port

  ser = serial.Serial(
      port=port,
      baudrate=9600,
      parity=serial.PARITY_NONE,
      stopbits=serial.STOPBITS_ONE,
      bytesize=serial.EIGHTBITS,
      timeout=0
  )
  print("Connected to Cerberus on port: " + ser.portstr)

  sleep(1)

  # wait_for_prompt(show=False, timeout=200)

  args.func(args)

  # wait_for_prompt()
  ser.close()
