CXX ?= g++
CXXFLAGS ?= -O2 -Wall -Wextra -fPIC
CPPFLAGS ?= -I../lmic
LDFLAGS ?= -shared
LDLIBS ?= -lwiringPi

BUILD_DIR := build
LMIC_SRCS := ../lmic/aes.c ../lmic/hal.c ../lmic/lmic.c ../lmic/oslmic.c ../lmic/radio.c
NATIVE_SRC := native/lorawanpi_native.cpp
OBJS := $(patsubst ../lmic/%.c,$(BUILD_DIR)/%.o,$(LMIC_SRCS)) $(BUILD_DIR)/lorawanpi_native.o
LIB := lorawanpi/liblorawanpi.so

all: $(LIB)

$(LIB): $(OBJS)
	$(CXX) $(LDFLAGS) -o $@ $^ $(LDLIBS)

$(BUILD_DIR)/%.o: ../lmic/%.c ../lmic/config.h ../lmic/hal.h ../lmic/lmic.h ../lmic/local_hal.h ../lmic/lorabase.h ../lmic/oslmic.h
	mkdir -p $(BUILD_DIR)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c -o $@ $<

$(BUILD_DIR)/lorawanpi_native.o: $(NATIVE_SRC) ../lmic/lmic.h ../lmic/hal.h ../lmic/local_hal.h
	mkdir -p $(BUILD_DIR)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c -o $@ $<

clean:
	rm -rf $(BUILD_DIR) $(LIB)

.PHONY: all clean
