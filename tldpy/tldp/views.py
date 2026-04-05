import json
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views import View
from django.core.files.storage import default_storage
from django.conf import settings
import mimetypes
import re


def decode_content(content):
    if isinstance(content, bytes):
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1")
    return content


def get_ldplist(lang="en"):
    try:
        file = default_storage.open(f"{lang}/ldplist.json", "r")
        data = json.load(file)
        file.close()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_directory_keys(lang="en"):
    try:
        prefix = f"{lang}/"
        dirs = default_storage.listdir(prefix)[0]
        return sorted(
            [d for d in dirs if default_storage.exists(f"{prefix}{d}/index.html")]
        )
    except Exception:
        return []


def extract_title(html_content):
    match = re.search(r"<title>(.*?)</title>", html_content, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None


def extract_breadcrumbs(html_content):
    crumbs = []
    body_match = re.search(r"<body[^>]*>(.*)", html_content, re.DOTALL | re.IGNORECASE)
    if body_match:
        body = body_match.group(1)
        h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.IGNORECASE | re.DOTALL)
        if h1_match:
            text = re.sub(r"<[^>]+>", "", h1_match.group(1)).strip()
            if text:
                crumbs.append({"name": text, "url": ""})
    return crumbs


def get_category_for_key(lang, key):
    ldplist = get_ldplist(lang)
    for category, items in ldplist.items():
        if key in items:
            return category
    return None


_build_date = None


def get_build_date():
    global _build_date
    if _build_date is None:
        try:
            file = default_storage.open("build-date.txt", "r")
            content = file.read()
            if isinstance(content, bytes):
                try:
                    content = content.decode("utf-8")
                except UnicodeDecodeError:
                    content = content.decode("latin-1")
            _build_date = content.strip()
            file.close()
        except Exception:
            _build_date = None
    return _build_date


def render_document(request, lang, key, html, title, breadcrumbs=None):
    ldplist = get_ldplist(lang)
    category = get_category_for_key(lang, key)
    if breadcrumbs and category:
        breadcrumbs.insert(0, {"name": category, "url": f"/{lang}/"})
    return render(
        request,
        "tldp/base.html",
        {
            "lang": lang,
            "key": key,
            "title": title,
            "content": html,
            "breadcrumbs": breadcrumbs or [],
            "ldplist": ldplist,
            "build_date": get_build_date(),
        },
    )


class LDPIndexView(View):
    def get(self, request, lang="en", key=None):
        if key:
            return self.serve_document(request, lang, key, "index.html", key)
        return self.list_keys(request, lang)

    def serve_document(self, request, lang, key, filename, doc_title):
        path = f"{lang}/{key}/{filename}"
        try:
            file = default_storage.open(path, "rb")
            content = file.read()
            file.close()
        except Exception:
            raise Http404(f"Document not found: {path}")

        content_type, _ = mimetypes.guess_type(path)

        if content_type and content_type.startswith("text/html"):
            html = decode_content(content)
            title = extract_title(html) or doc_title
            breadcrumbs = extract_breadcrumbs(html)
            return render_document(request, lang, key, html, title, breadcrumbs)

        return FileResponse(
            content, content_type=content_type or "application/octet-stream"
        )

    def list_keys(self, request, lang):
        ldplist = get_ldplist(lang)
        filter_cat = request.GET.get("cat")

        if filter_cat and filter_cat in ldplist:
            items = ldplist[filter_cat]
            content = f'<div class="row"><div class="col-12"><h3>{filter_cat} ({len(items)} documents)</h3><a href="/{lang}/" class="btn btn-secondary btn-sm mb-3">← All Categories</a></div></div><div class="row">'
            for item in items:
                content += f'<div class="col-md-3 mb-3"><a href="/{lang}/{item}/" class="text-decoration-none"><div class="card h-100"><div class="card-body"><h6 class="card-title">{item}</h6></div></div></a></div>'
            content += "</div>"
            return render_document(request, lang, None, content, f"{filter_cat} - LDP")

        content = ""
        for category, items in ldplist.items():
            content += f'<div class="row mt-4"><div class="col-12"><h4>{category}</h4><div class="row">'
            for item in items[:12]:
                content += f'<div class="col-md-3 mb-3"><a href="/{lang}/{item}/" class="text-decoration-none"><div class="card h-100"><div class="card-body"><h6 class="card-title">{item}</h6></div></div></a></div>'
            if len(items) > 12:
                content += f'<div class="col-md-3 mb-3"><a href="/{lang}/?cat={category}" class="btn btn-outline-primary">View all {len(items)} {category}...</a></div>'
            content += "</div></div></div>"

        return render_document(request, lang, None, content, "LDP Documents")


class LDPListView(View):
    def get(self, request, lang="en"):
        return JsonResponse({"lang": lang, "keys": get_directory_keys(lang)})


def serve_file(request, lang, key, path):
    if not path or path.endswith("/"):
        path = (path or "") + "index.html"
    full_path = f"{lang}/{key}/{path}"
    try:
        content_type, _ = mimetypes.guess_type(full_path)
        content_type = content_type or "application/octet-stream"
        file = default_storage.open(full_path, "rb")
        content = file.read()
        file.close()
    except Exception:
        raise Http404(f"File not found: {full_path}")

    if content_type and content_type.startswith("text/html"):
        html = decode_content(content)
        title = extract_title(html) or key
        page_name = path.replace("index.html", key).replace(".html", "")
        breadcrumbs = [
            {"name": key, "url": f"/{lang}/{key}/"},
            {"name": page_name if page_name != key else "Index", "url": ""},
        ]
        return render_document(request, lang, key, html, title, breadcrumbs)

    return FileResponse(content, content_type=content_type)


def search_api(request, lang="en"):
    query = request.GET.get("q", "")
    limit = int(request.GET.get("limit", 10))

    if len(query) < 2:
        return JsonResponse({"results": []})

    try:
        import meilisearch

        host = settings.MEILISEARCH["HOST"].split(":")[0]
        port = settings.MEILISEARCH["PORT"]
        client = meilisearch.Client(
            f"http://{host}:{port}",
            settings.MEILISEARCH.get("MASTER_KEY"),
        )
        index = client.index("documents")
        results = index.search(
            query,
            {
                "limit": limit,
                "attributesToRetrieve": ["key", "title", "url", "category", "content"],
                "attributesToHighlight": ["title", "content"],
                "highlightPreTag": "<mark>",
                "highlightPostTag": "</mark>",
            },
        )

        return HttpResponse(
            json.dumps({"results": results.get("hits", [])}).encode("utf-8"),
            content_type="application/json",
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def search_page(request, lang="en"):
    query = request.GET.get("q", "")
    results = []

    if query:
        try:
            import meilisearch

            host = settings.MEILISEARCH["HOST"].split(":")[0]
            port = settings.MEILISEARCH["PORT"]
            client = meilisearch.Client(
                f"http://{host}:{port}",
                settings.MEILISEARCH.get("MASTER_KEY"),
            )
            index = client.index("documents")
            search_results = index.search(query, {"limit": 50})
            results = search_results.get("hits", [])
        except Exception:
            results = []

    html = render_search_results(query, results)
    return render(
        request,
        "tldp/base.html",
        {
            "lang": lang,
            "title": f"Search: {query}" if query else "Search",
            "content": html,
            "breadcrumbs": [{"name": "Search", "url": ""}],
            "ldplist": get_ldplist(lang),
            "build_date": get_build_date(),
        },
    )


def render_search_results(query, results):
    if not results:
        return f'<div class="alert alert-warning">No results found for "{query}".</div>'

    html = (
        f'<div class="alert alert-info mb-3">{len(results)} results for "{query}"</div>'
    )
    html += '<div class="list-group">'
    for r in results:
        html += f'<a href="{r.get("url", "#")}" class="list-group-item list-group-item-action"><strong>{r.get("title", r.get("key", ""))}</strong>'
        if r.get("category"):
            html += f'<span class="badge bg-secondary ms-2">{r.get("category")}</span>'
        html += "</a>"
    html += "</div>"
    return html
