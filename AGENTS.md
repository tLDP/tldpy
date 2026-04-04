# TLDP Website - Agent Documentation

## Project Overview

This is the Django-based website for the Linux Documentation Project (TLDP). It serves HTML documentation files stored in S3 storage, organized by language and document categories.

## Tech Stack

- **Framework**: Django 6.x
- **Storage**: AWS S3 (via django-storages)
- **Frontend**: Bootstrap 5 with Flatly Bootswatch theme
- **Database**: PostgreSQL (via pg8000)

## Project Structure

```
tldpy/
├── tldpy/
│   ├── tldp/
│   │   ├── views.py          # Core view logic
│   │   ├── urls.py           # URL routing
│   │   ├── settings.py       # Django settings
│   │   └── templates/
│   │       └── tldp/
│   │           └── base.html # Main template
│   └── manage.py
├── pyproject.toml            # Python dependencies
└── .env                      # Environment variables
```

## Key Files

### views.py
Contains all view logic:
- `get_ldplist(lang)` - Reads `en/ldplist.json` from S3, returns dict with keys: HOWTO, Guides, FAQs
- `get_build_date()` - Reads `build-date.txt` from S3 root
- `get_category_for_key(lang, key)` - Maps document name to category
- `LDPIndexView` - Serves `/<lang>/` and `/<lang>/<key>/`
- `serve_file()` - Serves files via regex route
- `render_document()` - Wraps HTML in base template with nav

### urls.py
Routes:
- `/` → Redirects to `/en/`
- `/<lang>/` → List categories
- `/<lang>/?cat=HOWTO` → Filter by category
- `/<lang>/<key>/` → Serve document index.html
- `/<lang>/<key>/<path>` → Serve document files
- `/api/<lang>/ldplist/` → JSON list of keys

### base.html
Uses:
- `{% load django_bootstrap5 %}` for JS and Bootstrap utilities
- CDN link for Flatly Bootswatch theme
- Context variables: `lang`, `key`, `title`, `content`, `breadcrumbs`, `ldplist`, `build_date`

## S3 Storage Structure

```
Bucket: ldp
├── build-date.txt                    # Build timestamp
├── en/
│   ├── ldplist.json                 # Document index by category
│   ├── HOWTO/                       # 464 documents
│   │   ├── 3-Button-Mouse/
│   │   │   ├── index.html
│   │   │   ├── 3-Button-Mouse-1.html
│   │   │   └── ...
│   │   └── ...
│   ├── Guides/                      # 22 documents
│   └── FAQs/                        # 4 documents
```

### ldplist.json Format
```json
{
  "HOWTO": ["3-Button-Mouse", "3D-Modelling", ...],
  "Guides": ["Bash-Beginners-Guide", ...],
  "FAQs": ["AfterStep-FAQ", ...]
}
```

## Environment Variables (.env)

```
DJANGO_SECRET_KEY=<secret>
DEBUG=True
DATABASE_URL=postgresql://...
AWS_S3_ACCESS_KEY_ID=<key>
AWS_S3_SECRET_ACCESS_KEY=<secret>
```

## Common Patterns

### Adding new storage files
S3 storage returns strings for text files and bytes for binary files. Always handle both:
```python
content = file.read()
if isinstance(content, bytes):
    content = content.decode()
```

### Adding template context
Update `render_document()` in views.py to add new context variables.

### Adding URL routes
Add to `urls.py` with appropriate view. Use `re_path` for complex patterns.

## Development Commands

```bash
cd tldpy
uv sync                    # Install dependencies
uv run python manage.py runserver  # Run dev server
DJANGO_SETTINGS_MODULE=tldp.settings uv run python -c "..."  # Test code
```

## Git Workflow

- Branch: `main` (not `master`)
- Remote: `upstream` → git@github.com:tLDP/tldpy.git
- Push: `git push upstream main`
