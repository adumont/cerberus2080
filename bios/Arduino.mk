INO_FILE ?= $(shell basename $(CURDIR)).ino

ARDUINO_IDE_VERSION ?= 1.8.13
ARDUINO_DIR ?= $(HOME)/opt/arduino-$(ARDUINO_IDE_VERSION)
AVR_DIR ?= $(ARDUINO_DIR)/hardware/tools/avr
BUILD_PATH ?= $(CURDIR)/.build
CACHE_PATH ?= $(CURDIR)/.cache

SOURCES := $(wildcard *.c *.cpp *.h *.ino *.pde)

USBP := $(wildcard /dev/ttyUSB? )

.DEFAULT_GOAL:=build

build: $(BUILD_PATH)/$(INO_FILE).elf

$(BUILD_PATH)/$(INO_FILE).elf: $(SOURCES)
	mkdir -p $(BUILD_PATH) $(CACHE_PATH)
	$(ARDUINO_DIR)/arduino-builder \
		-compile \
		$(ARDUINO_BUILDER_OPT) \
		-logger=human \
		-build-path $(BUILD_PATH) --prefs=build.path=$(BUILD_PATH) \
		-build-cache $(CACHE_PATH) \
		-hardware $(ARDUINO_DIR)/hardware \
		-hardware $(HOME)/.arduino15/packages \
		-tools $(ARDUINO_DIR)/tools-builder \
		-tools $(ARDUINO_DIR)/hardware/tools/avr \
		-tools $(HOME)/.arduino15/packages \
		-built-in-libraries $(ARDUINO_DIR)/libraries \
		-libraries $(LIBRARIES) \
		-fqbn=$(BOARD) \
		-ide-version=10806 \
		-prefs=build.warn_data_percentage=75 \
		$(INO_FILE)

$(BUILD_PATH)/$(INO_FILE).hex: $(BUILD_PATH)/$(INO_FILE).elf

flash: $(BUILD_PATH)/$(INO_FILE).hex
	$(ARDUINO_DIR)/hardware/tools/avr/bin/avrdude \
    -C$(ARDUINO_DIR)/hardware/tools/avr/etc/avrdude.conf \
    -v -patmega328p -carduino -P$(USBP) -b115200 -D -Uflash:w:$(<):i

clean:
	rm -rf $(BUILD_PATH) $(CACHE_PATH)

.PHONY: clean
