# Cerberus2080

- [Cerberus2080](#cerberus2080)
- [Introduction](#introduction)
- [BIOS](#bios)
  - [Build and flash the BIOS](#build-and-flash-the-bios)
  - [Other available BIOS](#other-available-bios)
- [Emulator](#emulator)
  - [Build the kernel for the emulator](#build-the-kernel-for-the-emulator)
- [Kernel](#kernel)
  - [Build the kernel for Cerberus](#build-the-kernel-for-cerberus)
  - [Disassemble the kernel binary](#disassemble-the-kernel-binary)
  - [cl65 linker config files](#cl65-linker-config-files)
- [Credits](#credits)
- [References](#references)

# Introduction

This repo gathers my work on the Cerberus2080.

# BIOS

See files in bios/CERBERUS_2080_BIOS.

For now I've taken Andy Toone's 0xFE BIOS as code base, and I have made some minor changes:
- Reset vector set at `$C000`
- Boots in 6502 fast mode by default
- Write default values to pins *before* setting their mode (we don't want to output unknown/unexpected value in the board)
- Libs are included in the sketch folder, under libraries/
- Added a couple of build options (see in Makefile):
  - JINGLE_OFF: disable the boot Jingle
  - SOUND_FEEDBACK_OFF: disable the keys feedback sound

I have also added a couple of Makefiles for make the BIOS building from the repo.

You still need to have the Arduino IDE installed, but you won't need to open it.

TODO: detect the Arduino IDE path. For now, you can change the ARDUINO_DIR variable in your Makefile.

## Build and flash the BIOS

By using the Makefile, building and flashing the BIOS is a matter of running a couple of commands:

```
cd bios/CERBERUS_2080_BIOS
make build
make flash
```

## Other available BIOS

- [Andy Toone's 0xFE Bios](https://github.com/atoone/CERBERUS2080/tree/main/CAT)
- [Gordon Henderson's BIOS](https://project-downloads.drogon.net/cerberus2080/)
- [Dean Belfield BreakIntoProgram's BIOS](https://github.com/breakintoprogram/cerberus-bbc-basic/tree/main/cat)
- [The Byte Attic's original BIOS](https://github.com/TheByteAttic/CERBERUS2080/tree/main/CAT)

# Emulator

I've built a somewhat precarious emulator to develop a minimal [Kernel](#kernel). It's based on Py65 for the 6502 emulation, and Curses for the screen rendering.

On one hand, the emulator writes any key pressed to RAM using the MAILBOX/MAILFLAG mechanism.

On the other hand, the emulator intercepts writes to the Display RAM ($F800-$FCAF) and renders the written char on the emulated screen (left pane).

The right pane shows PC, some variables watches, and the bytes at PC.

## Build the kernel for the emulator

In order to build the kernel for the emulator we have to specify `EMULATOR=1`:

```
make clean
EMULATOR=1 make scr1.bin
emulator/cerbemu.py -r scr1.bin
```

At this early stage it looks like this:

![](asset/Emulator.gif)

# Kernel

At this early stage, I'm working on getting the input of the user (key pressed) rendered on the screen in a terminalish user-friendly way:
- handling line overflows
- scrolling up when reaching last line
- handling backspace and return
- display a cursor (static '_', not flashing at the moment)

That's mainly why I made the [Emulator](#emulator).

## Build the kernel for Cerberus

```
make clean
EMULATOR=1 make scr1.bin
emulator/cerbemu.py -r scr1.bin
```

## Disassemble the kernel binary

Useful to check that everything is where/how it should be:

```
da65 --cpu 65c02 --comments 3 --start-addr $(( 0xC000)) scr1.bin | less
```

## cl65 linker config files

There are two cl65 linker config files (layout of the binary by the lcl65 linker):
- lib/emulator.cfg: for the emulator, which include the whole $C000-$FFFF (so it does includes the interrupt vector table)
- lib/cerberus.cfg: for Cerberus2080, cl65 will not include the interrupt vector table.

# Credits

- [TheByteAttic/CERBERUS2080: CERBERUS 2080™, the amazing multi-processor 8-bit microcomputer](https://github.com/TheByteAttic/CERBERUS2080)

# References

- [CERBERUS 2080™ | The Byte Attic™](https://www.thebyteattic.com/p/cerberus-2080.html?view=magazine)