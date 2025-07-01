# Makefile for ProMOC Assembly Documentation

# Minimal makefile for Sphinx documentation
SPHINXOPTS    ?= -W --keep-going
SPHINXBUILD  ?= sphinx-build
SOURCEDIR    = .
BUILDDIR     = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Environment setup
setup:
	@echo "Setting up documentation environment..."
	pip install -r ../setup/dependencies.txt
	@echo "Documentation dependencies installed!"

# Quick build for development
dev: html
	@echo "Development build complete!"
	@echo "Open file://$(PWD)/_build/html/index.html to view"

# Production build with all checks
prod: clean html linkcheck
	@echo "Production build complete with link checking!"

# Auto-rebuild on file changes (requires sphinx-autobuild)
live:
	@echo "Starting live documentation server..."
	@echo "Open http://localhost:8000 to view"
	sphinx-autobuild "$(SOURCEDIR)" "$(BUILDDIR)/html" \
		--host 0.0.0.0 --port 8000 \
		--ignore "**/.*" \
		--ignore "**/__pycache__" \
		--watch "../**/**.py" \
		--watch "../**/**.md" \
		--watch "../**/**.rst"

# Build HTML and open in browser
view: html
	@echo "Opening documentation in browser..."
	@if command -v xdg-open > /dev/null; then \
		xdg-open _build/html/index.html; \
	elif command -v open > /dev/null; then \
		open _build/html/index.html; \
	else \
		echo "Please open file://$(PWD)/_build/html/index.html manually"; \
	fi

# Install dependencies for live preview
install-live:
	pip install sphinx-autobuild
	@echo "Live preview dependencies installed!"
	@echo "Run 'make live' to start auto-rebuilding server"

# Generate API documentation from source code
api:
	@echo "Generating API documentation..."
	sphinx-apidoc -f -o api/ ../linear_axis_nodes/
	sphinx-apidoc -f -o api/ ../planar_motor_nodes/
	@echo "API documentation generated!"

# Check for broken links
linkcheck:
	@echo "Checking for broken links..."
	@$(SPHINXBUILD) -b linkcheck "$(SOURCEDIR)" "$(BUILDDIR)/linkcheck" $(SPHINXOPTS)

# Check spelling (requires sphinxcontrib-spelling)
spell:
	@echo "Checking spelling..."
	@$(SPHINXBUILD) -b spelling "$(SOURCEDIR)" "$(BUILDDIR)/spelling" $(SPHINXOPTS)

# Generate coverage report
coverage:
	@echo "Generating documentation coverage report..."
	@$(SPHINXBUILD) -b coverage "$(SOURCEDIR)" "$(BUILDDIR)/coverage" $(SPHINXOPTS)
	@echo "Coverage report: _build/coverage/python.txt"

# Deploy to GitHub Pages (if configured)
deploy: prod
	@echo "Deploying to GitHub Pages..."
	@if [ -d ".git" ]; then \
		if [ ! -d "_build/html/.git" ]; then \
			cd _build/html && git init && git remote add origin ../../.git; \
		fi; \
		cd _build/html && \
		git add -A && \
		git commit -m "Deploy documentation" && \
		git push -f origin HEAD:gh-pages; \
		echo "Documentation deployed to GitHub Pages!"; \
	else \
		echo "Not a git repository. Cannot deploy to GitHub Pages."; \
	fi

# Clean all generated files
clean:
	@echo "Cleaning documentation build..."
	rm -rf $(BUILDDIR)/*
	rm -rf api/linear_axis_nodes*
	rm -rf api/planar_motor_nodes*

# Install all documentation dependencies
install:
	@echo "Installing documentation dependencies..."
	pip install sphinx>=4.0.0
	pip install sphinx-rtd-theme>=1.0.0
	pip install myst-parser>=0.15.0
	pip install sphinx-autobuild
	pip install sphinxcontrib-spelling
	@echo "All documentation dependencies installed!"

# Development workflow
dev-setup: install setup api
	@echo "Development environment ready!"
	@echo "Run 'make live' for auto-rebuilding server"
	@echo "Run 'make dev' for quick builds"

# Quality checks
quality: linkcheck spell coverage
	@echo "Quality checks complete!"

# Show useful information
info:
	@echo "ProMOC Assembly Documentation"
	@echo "============================="
	@echo ""
	@echo "Available commands:"
	@echo "  make html        - Build HTML documentation"
	@echo "  make dev         - Quick development build"
	@echo "  make live        - Start auto-rebuilding server"
	@echo "  make view        - Build and open in browser"
	@echo "  make api         - Generate API docs from source"
	@echo "  make linkcheck   - Check for broken links"
	@echo "  make clean       - Clean build files"
	@echo "  make deploy      - Deploy to GitHub Pages"
	@echo ""
	@echo "Setup commands:"
	@echo "  make install     - Install documentation tools"
	@echo "  make dev-setup   - Complete development setup"
	@echo ""
	@echo "Quality commands:"
	@echo "  make quality     - Run all quality checks"
	@echo "  make spell       - Check spelling"
	@echo "  make coverage    - Generate coverage report"

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
