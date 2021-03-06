VERSION := $(shell git rev-parse --short HEAD)
DATE := $(shell git log -1 --format=%cd --date=format:"%Y%m%d")
VERSION := $(VERSION)($(DATE))

ifneq ($(shell git status --porcelain),)
    VERSION := $(VERSION)*
endif

REPO := $(shell git config --get remote.origin.url | cut -d: -f2 | sed -e 's/\.git//' )

$(info VERSION: $(REPO) $(VERSION))
