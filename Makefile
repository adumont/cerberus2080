# build tools & options
CL65 = cl65
CLFLAGS  = -v -d -t none -O --cpu 65c02 -C $(LIB)/$(CFG)\
  -m  $(basename $@).map\
  -Ln $(basename $@).lbl

LIB=lib

.DEFAULT_GOAL := run

all: hw emu

# At the moment, LINKING <=> STAGE2
# TODO: replace with STAGE1 flag and invert logic (ifdef => ifndef)

# Minify the bootstrap code (remove \ comments and empty lines)
%.f.min: %.f
	sed -e 's/ \\ .*//; s/^\\ .*//; s/^\s*//' $< | grep -v '^\s*$$' > $@

### Version file ###

# we compare the output with the version saved.
# if not the same we update it
version.dat: version.sh .force
	./version.sh | cmp -s - $@ || ./version.sh > $@

###### For the Emulator ######

## STAGE 1

forth-emu-stage1.bin: forth.s version.dat
	$(eval CFG := emulator.cfg)
	$(CL65) $(CLFLAGS) --asm-define EMULATOR -o $@ $<

# Builds the 3 .dat files, cross-compiling the bootstrap.f code
%-emu.dat: forth-emu-stage1.bin bootstrap.f.min
	./xcompiler.py -r forth-emu-stage1.bin -l bootstrap.f.min -a 0xC000 -t emu -s forth-emu-stage1.lbl

## STAGE 2

# Builds the emulator image, using LINKING flag!
forth-emu.bin: forth.s rom-emu.dat ram-emu.dat last-emu.dat
	$(eval CFG := emulator.cfg)
	$(CL65) $(CLFLAGS) --asm-define LINKING --asm-define EMULATOR -o $@ $<

emu: forth-emu.bin

run: forth-emu.bin
	emulator/cerbemu.py -r $<


###### For the HW (Cerberus2080) ######

## STAGE 1

forth-hw-stage1.bin: forth.s version.dat
	$(eval CFG := emulator.cfg)
	$(CL65) $(CLFLAGS) -o $@ $<

# Builds the 3 .dat files, cross-compiling the bootstrap.f code
%-hw.dat: forth-hw-stage1.bin bootstrap.f.min
	./xcompiler.py -r forth-hw-stage1.bin -l bootstrap.f.min -a 0xC000 -t hw -s forth-hw-stage1.lbl

## STAGE 2

# Builds the emulator image, using LINKING flag!
forth-hw.bin: forth.s rom-hw.dat ram-hw.dat last-hw.dat
	$(eval CFG := emulator.cfg)
	$(CL65) $(CLFLAGS) --asm-define LINKING -o $@ $<

hw: forth-hw.bin

send: forth-hw.bin
	./programmer.py send $<

######


## HELP

help:
	@echo "usage: make [run | send]"
	@echo ""
	@echo "  emu:   build the rom for the Cerberus2080 emulator"
	@echo "  run:   execute the rom in Cerberus2080 emulator"
	@echo "  hw:    build the rom for a Cerberus2080 computer"
	@echo "  send:  send the rom to a Cerberus computer"

clean:
	-rm -f lib/*.o *.o *.hex *.map *.bin *.h *.lbl *.dat

.PHONY: .force
