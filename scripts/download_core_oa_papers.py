from __future__ import annotations

import csv
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = PROJECT_ROOT / "data" / "literature_corpus"
OUT_DIR = CORPUS_ROOT / "papers" / "core_downloaded"
MANIFEST_PATH = CORPUS_ROOT / "metadata" / "core_downloaded_manifest.csv"
FAILED_PATH = CORPUS_ROOT / "metadata" / "core_download_failed.csv"

TARGET_COUNT = 35
MIN_BYTES = 80_000
MIN_PAGES = 3
QUERY_DELAY_SECONDS = 1.25

OPENALEX_ENDPOINT = "https://api.openalex.org/works"

QUERIES = [
    "RDX ReaxFF molecular dynamics thermal decomposition",
    "RDX HTPB molecular dynamics thermal decomposition",
    "RDX aluminum reactive molecular dynamics energetic material",
    "CL-20 TNT molecular dynamics polymer bonded explosive",
    "CL-20 HMX molecular dynamics cocrystal explosive",
    "CL-20 polymer bonded explosive molecular dynamics",
    "CL-20 cocrystal molecular dynamics sensitivity mechanical properties",
    "HMX HTPB reactive molecular dynamics thermal decomposition",
    "HMX polymer bonded explosive molecular dynamics",
    "HMX ReaxFF molecular dynamics thermal decomposition",
    "NTO HTPB ReaxFF molecular dynamics plastic bonded explosive",
    "LLM-105 HTPB ReaxFF molecular dynamics plastic bonded explosive",
    "energetic cocrystal molecular dynamics CL-20 HMX FOX-7",
    "polymer bonded explosive molecular dynamics interface mechanical properties",
    "energetic materials ReaxFF molecular dynamics decomposition shock sensitivity",
    "nitramine energetic material molecular dynamics decomposition",
    "RDX nanoparticle molecular dynamics energetic response",
    "PBX molecular dynamics binder explosive interface",
]

MATERIAL_TERMS = [
    "rdx",
    "hmx",
    "cl-20",
    "cl20",
    "nto",
    "llm-105",
    "tatb",
    "fox-7",
    "nitramine",
    "energetic",
    "explosive",
    "propellant",
    "pbx",
    "polymer-bonded",
    "polymer bonded",
]

METHOD_TERMS = [
    "molecular dynamics",
    "reaxff",
    "reactive molecular dynamics",
    "quantum molecular dynamics",
    "first-principles molecular dynamics",
    "ab initio molecular dynamics",
]

EXCLUDE_TERMS = [
    "zeolite",
    "battery",
    "catalyst",
    "electrocatal",
    "photocatal",
    "co2 reduction",
    "gold nanocrystal",
    "large gold",
]


def request_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ai-app-engineer-roadmap/0.1 (mailto:openalex@example.com)"
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    return json.loads(data.decode("utf-8"))


def normalize_doi(doi: str | None) -> str:
    if not doi:
        return ""
    doi = doi.strip().lower()
    doi = doi.removeprefix("https://doi.org/")
    doi = doi.removeprefix("http://doi.org/")
    return doi


def slugify(text: str, max_len: int = 80) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:max_len].strip("-") or "paper"


def title_is_relevant(title: str) -> bool:
    t = title.lower()
    if any(term in t for term in EXCLUDE_TERMS):
        return False
    has_material = any(term in t for term in MATERIAL_TERMS)
    has_method = any(term in t for term in METHOD_TERMS)
    return has_material and has_method


def get_source_name(work: dict[str, Any]) -> str:
    loc = work.get("primary_location") or {}
    source = loc.get("source") or {}
    return source.get("display_name") or ""


def get_pdf_url(work: dict[str, Any]) -> str:
    content_urls = work.get("content_urls") or {}
    if content_urls.get("pdf"):
        return content_urls["pdf"]

    for loc_key in ("best_oa_location", "primary_location"):
        loc = work.get(loc_key) or {}
        pdf_url = loc.get("pdf_url")
        if pdf_url:
            return pdf_url

    oa = work.get("open_access") or {}
    oa_url = oa.get("oa_url") or ""
    if oa_url.lower().endswith(".pdf"):
        return oa_url
    return ""


def iter_openalex_results() -> list[dict[str, Any]]:
    seen: set[str] = set()
    results: list[dict[str, Any]] = []

    fields = ",".join(
        [
            "id",
            "doi",
            "display_name",
            "publication_year",
            "primary_location",
            "best_oa_location",
            "open_access",
            "content_urls",
            "cited_by_count",
        ]
    )

    for query in QUERIES:
        params = {
            "search": query,
            "filter": "open_access.is_oa:true,type:article",
            "per-page": "50",
            "select": fields,
        }
        url = OPENALEX_ENDPOINT + "?" + urllib.parse.urlencode(params)
        try:
            payload = request_json(url)
        except Exception as exc:
            print(f"query failed: {query}: {exc}")
            continue

        for work in payload.get("results", []):
            title = (work.get("display_name") or "").strip()
            doi = normalize_doi(work.get("doi"))
            key = doi or title.lower()
            if not key or key in seen:
                continue
            seen.add(key)
            if not title_is_relevant(title):
                continue
            pdf_url = get_pdf_url(work)
            if not pdf_url:
                continue
            work["_source_query"] = query
            work["_pdf_url"] = pdf_url
            results.append(work)

        time.sleep(QUERY_DELAY_SECONDS)

    results.sort(
        key=lambda w: (
            int(w.get("cited_by_count") or 0),
            int(w.get("publication_year") or 0),
        ),
        reverse=True,
    )
    return results


def download_url(url: str, path: Path) -> tuple[bool, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
            ),
            "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = resp.read()
    except urllib.error.HTTPError as exc:
        return False, f"http {exc.code}"
    except Exception as exc:
        return False, str(exc)

    if len(data) < MIN_BYTES:
        return False, f"too small: {len(data)} bytes"
    if not data.startswith(b"%PDF"):
        return False, "not a PDF response"

    with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)

    try:
        reader = PdfReader(str(tmp_path))
        page_count = len(reader.pages)
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        return False, f"invalid PDF: {exc}"

    if page_count < MIN_PAGES:
        tmp_path.unlink(missing_ok=True)
        return False, f"too few pages: {page_count}"

    path.write_bytes(data)
    tmp_path.unlink(missing_ok=True)
    return True, f"{len(data)} bytes, {page_count} pages"


def load_existing_dois() -> set[str]:
    dois: set[str] = set()
    for csv_path in [
        CORPUS_ROOT / "metadata" / "paper_manifest.csv",
        MANIFEST_PATH,
    ]:
        if not csv_path.exists():
            continue
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                doi = normalize_doi(row.get("doi"))
                if doi:
                    dois.add(doi)
    return dois


def load_existing_rows() -> list[dict[str, str]]:
    if not MANIFEST_PATH.exists():
        return []
    with MANIFEST_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def next_download_index(rows: list[dict[str, str]]) -> int:
    max_index = 0
    for row in rows:
        match = re.search(r"CORE-DL-(\d+)", row.get("download_id", ""))
        if match:
            max_index = max(max_index, int(match.group(1)))
    return max_index + 1


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    existing_dois = load_existing_dois()
    candidates = iter_openalex_results()

    existing_rows = load_existing_rows()
    rows: list[dict[str, str]] = list(existing_rows)
    failures: list[dict[str, str]] = []
    downloaded = 0
    next_index = next_download_index(existing_rows)

    for work in candidates:
        title = (work.get("display_name") or "").strip()
        doi = normalize_doi(work.get("doi"))
        if doi and doi in existing_dois:
            continue

        download_id = f"CORE-DL-{next_index:03d}"
        filename = f"{download_id}-{slugify(title)}.pdf"
        out_path = OUT_DIR / filename
        ok, status = download_url(work["_pdf_url"], out_path)

        record = {
            "download_id": download_id,
            "title": title,
            "year": str(work.get("publication_year") or ""),
            "journal": get_source_name(work),
            "doi": doi,
            "openalex_id": work.get("id") or "",
            "pdf_url": work["_pdf_url"],
            "source_query": work["_source_query"],
            "file_path": str(out_path.relative_to(CORPUS_ROOT)).replace("\\", "/"),
            "topic_tags": "energetic_materials;MD;ReaxFF;PBX;thermal_decomposition",
            "status": status,
        }

        if ok:
            rows.append(record)
            downloaded += 1
            next_index += 1
            existing_dois.add(doi)
            print(f"downloaded {download_id}: {title}")
        else:
            failures.append(record)
            print(f"failed: {title}: {status}")

        if downloaded >= TARGET_COUNT:
            break
        time.sleep(0.35)

    fieldnames = [
        "download_id",
        "title",
        "year",
        "journal",
        "doi",
        "openalex_id",
        "pdf_url",
        "source_query",
        "file_path",
        "topic_tags",
        "status",
    ]

    with MANIFEST_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with FAILED_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(failures)

    print(f"candidates: {len(candidates)}")
    print(f"downloaded: {downloaded}")
    print(f"manifest: {MANIFEST_PATH}")
    print(f"failed: {FAILED_PATH}")


if __name__ == "__main__":
    main()
