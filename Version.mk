VERSION := $(shell git rev-parse --short HEAD)

ifneq ($(shell git status --porcelain),)
    VERSION := $(VERSION)-dirty
endif

DATE := $(shell git log -1 --format=%cd --date=format:"%Y%m%d")

VERSION := $(VERSION) ($(DATE))

REPO := $(shell git config --get remote.origin.url | cut -d: -f2 | sed -e 's/\.git//' )

$(info VERSION: $(REPO) $(VERSION))
