# ProMOC Assembly Documentation

This directory contains the complete documentation for the ProMOC Assembly system, built with **Sphinx** and hosted with **Read the Docs** theme.

## 📖 Documentation Structure

```
docs/
├── index.rst                    # Main documentation index
├── conf.py                      # Sphinx configuration
├── Makefile                     # Build automation
├── _static/                     # Custom CSS and assets
├── installation/                # Installation guides
├── quickstart/                  # Quick start tutorial
├── architecture/                # System architecture
├── api/                         # Auto-generated API docs
├── hardware/                    # Hardware documentation
├── simulation/                  # Simulation guides
├── tutorials/                   # Step-by-step tutorials
├── development/                 # Developer guides
└── appendix/                    # Troubleshooting, FAQ, etc.
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd docs/
make install
# or manually:
# pip install sphinx sphinx-rtd-theme myst-parser sphinx-autobuild
```

### 2. Build Documentation
```bash
# Quick development build
make dev

# Production build with checks
make prod

# Auto-rebuilding server (recommended for development)
make live
```

### 3. View Documentation
```bash
# Build and open in browser
make view

# Or manually open:
# firefox _build/html/index.html
```

## 🛠️ Development Workflow

### Live Preview (Recommended)
```bash
make live
```
- Starts server at http://localhost:8000
- Auto-rebuilds on file changes
- Watches Python source files for API changes

### Manual Building
```bash
# Quick build for development
make dev

# Full production build
make prod

# Generate API docs from source
make api

# Check for broken links
make linkcheck
```

## 📝 Writing Documentation

### File Formats

- **ReStructuredText (.rst)**: Main format for Sphinx
- **Markdown (.md)**: Supported via MyST parser
- **Python Docstrings**: Auto-extracted for API docs

### Style Guide

#### Headings
```markdown
# Main Title (H1)
## Section (H2)  
### Subsection (H3)
#### Sub-subsection (H4)
```

#### Code Blocks
```markdown
# Code with syntax highlighting
```python
def example_function():
    return "Hello, World!"
```

# Bash commands
```bash
ros2 launch promoc_bringup dual_lts300_gazebo.launch.py
```
```

#### Admonitions
```markdown
```{note}
This is an informational note.
```

```{warning}
This is a warning message.
```

```{important}
This is important information.
```
```

#### Cross-References
```markdown
# Link to other docs
{doc}`installation/index`

# Link to sections
{ref}`system-architecture`

# Link to API
{py:class}`linear_axis_nodes.LinearAxisDriver`
```

### Adding New Documentation

1. **Create new .md or .rst file** in appropriate directory
2. **Add to toctree** in parent index file
3. **Build and test** with `make dev`
4. **Check links** with `make linkcheck`

## 📚 Documentation Types

### User Documentation
- **Installation**: Step-by-step setup guides
- **Quick Start**: Get running in 5 minutes
- **Tutorials**: Task-oriented guides
- **Hardware**: Physical setup and configuration

### Developer Documentation  
- **API Reference**: Auto-generated from docstrings
- **Architecture**: System design and principles
- **Contributing**: Development workflow
- **Testing**: Test procedures and standards

### System Documentation
- **Configuration**: Parameter references
- **Troubleshooting**: Common problems and solutions
- **FAQ**: Frequently asked questions
- **Changelog**: Version history

## 🔧 Advanced Features

### API Documentation Generation
```bash
# Generate API docs from Python source
make api

# Include in main documentation
# (automatically included in build)
```

### Quality Checks
```bash
# Check for broken links
make linkcheck

# Spell checking (requires sphinxcontrib-spelling)
make spell

# Documentation coverage
make coverage

# All quality checks
make quality
```

### Deployment
```bash
# Deploy to GitHub Pages
make deploy

# Manual deployment
# 1. Build: make prod
# 2. Copy _build/html/* to web server
```

## 🎨 Customization

### Theme Configuration
Edit `conf.py`:
```python
html_theme_options = {
    'canonical_url': '',
    'analytics_id': '',
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'vcs_pageview_mode': '',
    'style_nav_header_background': '#2980B9',
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}
```

### Custom CSS
Add styles to `_static/custom.css`:
```css
/* Custom ProMOC styling */
.wy-nav-top {
    background: #2980B9 !important;
}
```

### Extensions
Add to `conf.py`:
```python
extensions = [
    'sphinx.ext.autodoc',      # Auto-generate docs
    'sphinx.ext.viewcode',     # Source code links
    'sphinx.ext.napoleon',     # Google/NumPy docstrings
    'sphinx.ext.intersphinx',  # Link to other projects
    'myst_parser',             # Markdown support
    'sphinx_rtd_theme',        # Theme
]
```

## 🔍 Troubleshooting

### Build Errors
```bash
# Clean and rebuild
make clean
make dev

# Check for syntax errors
make html 2>&1 | grep -i error
```

### Missing Dependencies
```bash
# Install all documentation dependencies
make install

# Or install specific packages
pip install sphinx sphinx-rtd-theme myst-parser
```

### API Generation Issues
```bash
# Manually regenerate API docs
sphinx-apidoc -f -o api/ ../linear_axis_nodes/
sphinx-apidoc -f -o api/ ../planar_motor_nodes/
```

## 📋 Makefile Commands

| Command | Description |
|---------|-------------|
| `make html` | Build HTML documentation |
| `make dev` | Quick development build |
| `make live` | Auto-rebuilding server |
| `make view` | Build and open in browser |
| `make api` | Generate API docs |
| `make linkcheck` | Check for broken links |
| `make clean` | Clean build files |
| `make install` | Install dependencies |
| `make deploy` | Deploy to GitHub Pages |
| `make quality` | Run all quality checks |

## 🌐 Hosting Options

### GitHub Pages
```bash
# Automatic deployment
make deploy

# Manual setup:
# 1. Enable GitHub Pages in repository settings
# 2. Set source to gh-pages branch
# 3. Run make deploy
```

### Read the Docs
1. Connect repository to readthedocs.org
2. Configure build settings
3. Automatic builds on push

### Local Server
```bash
# Simple HTTP server
cd _build/html
python -m http.server 8080

# Or use live server
make live
```

---

**For questions or issues with documentation, please check the troubleshooting section or create an issue in the project repository.**
