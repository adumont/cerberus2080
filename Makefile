# build tools & options
CL65 = cl65
CLFLAGS  = -v -d -t none -O --cpu 65c02 -C $(LIB)/$(CFG)\
  -m  $(basename $@).map\
  -Ln $(basename $@).lbl

LIB=lib

.DEFAULT_GOAL := run

## For the Emulator

forth-emu.bin: forth.s
	$(eval CFG := emulator.cfg)
	$(CL65) $(CLFLAGS) --asm-define EMULATOR -o $@ $<

emu: forth-emu.bin

run: forth-emu.bin
	emulator/cerbemu.py

## For the HW (Cerberus2080)

forth-hw.bin: forth.s
	$(eval CFG := cerberus.cfg)
	$(CL65) $(CLFLAGS) -o $@ $<

hw: forth-hw.bin

send: forth-hw.bin
	./programmer.py send $<

## HELP

help:
	@echo "usage: make [run | send]"
	@echo ""
	@echo "  emu:   build the rom for the Cerberus2080 emulator"
	@echo "  run:   execute the rom in Cerberus2080 emulator"
	@echo "  hw:    build the rom for a Cerberus2080 computer"
	@echo "  send:  send the rom to a Cerberus computer"

clean:
	-rm -f lib/*.o *.o *.hex *.map *.bin *.h *.lbl
