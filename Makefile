CC ?= gcc
CXX ?= g++

CFLAGS ?= -O2 -Wall -Wextra -fPIC
CXXFLAGS ?= -O2 -Wall -Wextra -fPIC

CPPFLAGS ?= -Ilmic
LDFLAGS ?= -shared
LDLIBS ?= -lwiringPi

BUILD_DIR := build

LMIC_SRCS := lmic/aes.c lmic/hal.c lmic/lmic.c lmic/oslmic.c lmic/radio.c
NATIVE_SRC := native/lorawanpi_native.cpp

LMIC_OBJS := $(patsubst lmic/%.c,$(BUILD_DIR)/%.o,$(LMIC_SRCS))
NATIVE_OBJ := $(BUILD_DIR)/lorawanpi_native.o

OBJS := $(LMIC_OBJS) $(NATIVE_OBJ)
LIB := lorawanpi/liblorawanpi.so

all: $(LIB)

$(LIB): $(OBJS)
	mkdir -p $(dir $@)
	$(CXX) $(LDFLAGS) -o $@ $^ $(LDLIBS)

# Compile C sources with gcc
$(BUILD_DIR)/%.o: lmic/%.c
	mkdir -p $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c -o $@ $<

# Compile C++ bridge with g++
$(BUILD_DIR)/lorawanpi_native.o: $(NATIVE_SRC)
	mkdir -p $(BUILD_DIR)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c -o $@ $<

clean:
	rm -rf $(BUILD_DIR) $(LIB)

.PHONY: all clean
