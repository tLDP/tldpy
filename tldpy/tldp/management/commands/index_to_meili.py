import json
import re
from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage


class Command(BaseCommand):
    help = "Index documents from S3 storage to MeiliSearch"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear", action="store_true", help="Delete index and re-create"
        )
        parser.add_argument(
            "--skip-content", action="store_true", help="Skip fetching content (faster)"
        )

    def handle(self, *args, **options):
        from django.conf import settings
        import meilisearch

        host = settings.MEILISEARCH["HOST"].split(":")[0]
        port = settings.MEILISEARCH["PORT"]
        client = meilisearch.Client(
            f"http://{host}:{port}",
            settings.MEILISEARCH.get("MASTER_KEY"),
        )

        if options["clear"]:
            self.stdout.write("Deleting index...")
            try:
                client.delete_index("documents")
            except Exception:
                pass
            self.stdout.write("Creating index...")
            client.create_index("documents", {"primaryKey": "id"})

        self.stdout.write("Fetching ldplist...")
        ldplist = get_ldplist("en")

        documents = []
        errors = 0
        for idx, (category, keys) in enumerate(ldplist.items()):
            for key in keys:
                safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)
                doc = {
                    "id": safe_id,
                    "key": key,
                    "title": key,
                    "url": f"/en/{key}/",
                    "category": category,
                    "lang": "en",
                    "content": "",
                }

                if not options["skip_content"]:
                    content = fetch_index_content(key)
                    if content:
                        doc["title"] = extract_title(content) or key
                        doc["content"] = strip_html(content)[:50000]
                    else:
                        errors += 1

                documents.append(doc)

            if (idx + 1) % 50 == 0:
                self.stdout.write(f"  Processed {idx + 1}/{len(ldplist)} categories...")

        self.stdout.write(f"Indexing {len(documents)} documents (errors: {errors})...")

        index = client.index("documents")
        index.update_settings(
            {
                "searchableAttributes": ["title", "content", "key", "category"],
                "filterableAttributes": ["category", "lang"],
                "displayedAttributes": [
                    "key",
                    "title",
                    "url",
                    "category",
                    "lang",
                    "content",
                ],
            }
        )

        batch_size = 50
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            task = index.add_documents(batch, primary_key="id")
            client.wait_for_task(task.task_uid)

        stats = index.get_stats()
        self.stdout.write(
            self.style.SUCCESS(f"Indexed {stats.number_of_documents} documents")
        )


def get_ldplist(lang="en"):
    try:
        file = default_storage.open(f"{lang}/ldplist.json", "r")
        data = json.load(file)
        file.close()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def fetch_index_content(key):
    try:
        path = f"en/{key}/index.html"
        file = default_storage.open(path, "rb")
        content = file.read()
        file.close()
        return content.decode("utf-8", errors="replace")
    except Exception:
        return None


def extract_title(html):
    match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None


def strip_html(html):
    text = re.sub(
        r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE
    )
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
