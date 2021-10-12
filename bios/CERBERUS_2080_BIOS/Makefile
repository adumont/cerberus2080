include ../../Version.mk

ARDUINO_BUILDER_OPT:= -prefs="build.extra_flags=-DJINGLE_OFF -DSOUND_FEEDBACK_OFF -DCAT_VERSION=\"$(VERSION)\"" -verbose

BOARD = arduino:avr:uno

LIBRARIES := ./libraries

include ../Arduino.mk
