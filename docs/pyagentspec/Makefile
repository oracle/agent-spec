# Simplified Makefile for Sphinx documentation (single source with external tag)

SPHINXOPTS    ?= -W --keep-going # To error if the build ends with one or more warnings
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = build/html
EXTERNAL_TAG  = external

.PHONY: help html clean

help:
	@echo "Please use 'make <target>' where <target> is one of:"
	@echo "  html    - build the HTML documentation"
	@echo "  clean   - clean up build files"

html:
	@echo "Building HTML docs to $(BUILDDIR)..."
	@$(SPHINXBUILD) -t $(EXTERNAL_TAG) -b html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)
	@echo "Build finished. The HTML pages are in $(BUILDDIR)"

clean:
	- rm -rf $(BUILDDIR)

# Catch-all: forward other targets to Sphinx's Make mode
%:
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)
