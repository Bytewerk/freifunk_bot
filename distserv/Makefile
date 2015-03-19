# --- START OF CONFIG ---------------------------------------------------
# Edit the following variables for your own needs

# toolchain configuration
CXX=gcc
LD=gcc

# default build configuration
# "make BUILD=release" does a release build
BUILD:=debug

# basic build flags configuration
CFLAGS+=-Wall -Wno-variadic-macros -std=c99 -pedantic -Wno-long-long -D_POSIX_C_SOURCE=20120607L -D_FILE_OFFSET_BITS=64 -pthread
LIBS+=-pthread

# local include directory
CFLAGS+=-I./include

# library specific flags
## libmicrohttpd
CFLAGS+=$(shell pkg-config --cflags libmicrohttpd)
LIBS+=$(shell pkg-config --libs libmicrohttpd)

## json-c
CFLAGS+=$(shell pkg-config --cflags json-c)
LIBS+=$(shell pkg-config --libs json-c)

# build type specific flags
CFLAGS_debug=-O0 -ggdb -DDEBUG
LIBS_debug=

CFLAGS_release=-O3
LIBS_release=

# target configuration
TARGET := multiclient_broadcast
VERSION := 0.0.1
VCSVERSION := $(shell git rev-parse --short HEAD)

# source files for the project
SOURCE := $(shell find src/ -name '*.c')
INCLUDES := $(shell find src/ -name '*.h')

# additional dependencies for build (proper targets must be specified by user)
DEPS :=

# default target
all: $(TARGET)

# user-specific targets

# --- END OF CONFIG -----------------------------------------------------

OBJ1=$(patsubst %.c, %.o, $(SOURCE))
OBJ=$(patsubst src/%, obj/$(BUILD)/%, $(OBJ1))

VERSIONSTR="\"$(VERSION)-$(VCSVERSION)\""

CFLAGS+=-DVERSION=$(VERSIONSTR)

TARGETFILE := bin/$(BUILD)/$(TARGET)

CFLAGS+=$(CFLAGS_$(BUILD))
LIBS+=$(LIBS_$(BUILD))

.PHONY show_cflags:
	@echo --- Build parameters:  ------------------------------------------
	@echo CFLAGS\=$(CFLAGS)
	@echo LIBS\=$(LIBS)
	@echo SOURCE\=$(SOURCE)
	@echo -----------------------------------------------------------------

$(TARGET): show_cflags $(TARGETFILE)
	@echo ">>> $(BUILD) build complete."

$(TARGETFILE): $(DEPS) $(OBJ) $(INCLUDES) Makefile
	@echo Linking $@ ...
	@mkdir -p $(shell dirname $@)
	@$(LD) -o $(TARGETFILE) $(OBJ) $(LIBS)

obj/$(BUILD)/%.o: src/%.c $(INCLUDES) Makefile
	@echo "Compiling $< ..."
	@mkdir -p $(shell dirname $@)
	@$(CXX) -c $(CFLAGS) -o $@ $<

doc:
	doxygen doxygen.conf

clean:
	rm -f $(TARGETFILE)
	rm -f $(OBJ)

