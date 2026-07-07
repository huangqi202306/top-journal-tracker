#!/usr/bin/env python3
"""Collect recent top-journal papers and write Markdown/CSV digests.

The script intentionally uses only the Python standard library. It queries
PubMed and Crossref, then optionally parses RSS feeds configured in YAML.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = SKILL_DIR / "config" / "journals.yaml"
DEFAULT_STATE = SKILL_DIR / "state" / "seen_articles.json"


def today_utc() -> dt.date:
    return dt.datetime.utcnow().date()


def fetch_url(url: str, accept: str = "application/json", timeout: int = 30) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "top-journal-tracker/1.0 (mailto:research@example.com)",
            "Accept": accept,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def text_of(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def parse_simple_yaml(path: Path) -> dict:
    """Parse the small config shape used by this skill without PyYAML."""
    config: dict = {"journals": [], "topics": {"include": [], "exclude": []}, "rss_feeds": []}
    section = None
    subsection = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" ") and ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            subsection = None
            if value:
                if value == "[]":
                    config[key] = []
                elif value == "{}":
                    config[key] = {}
                elif value.isdigit():
                    config[key] = int(value)
                else:
                    config[key] = value.strip("\"'")
                section = None
            else:
                section = key
                config.setdefault(section, [] if section in {"journals", "rss_feeds"} else {})
            continue
        stripped = line.strip()
        if section in {"journals", "rss_feeds"} and stripped.startswith("- "):
            config.setdefault(section, []).append(stripped[2:].strip().strip("\"'"))
        elif section == "topics" and stripped.endswith(":"):
            subsection = stripped[:-1]
            config["topics"].setdefault(subsection, [])
        elif section == "topics" and stripped.startswith("- ") and subsection:
            config["topics"].setdefault(subsection, []).append(stripped[2:].strip().strip("\"'"))
    return config


def load_config(path: Path) -> dict:
    if not path.exists():
        return parse_simple_yaml(DEFAULT_CONFIG)
    return parse_simple_yaml(path)


def pubmed_search(journals: list[str], start: dt.date, end: dt.date) -> list[str]:
    journal_query = " OR ".join(f'"{journal}"[Journal]' for journal in journals)
    date_query = f'("{start.isoformat()}"[Date - Publication] : "{end.isoformat()}"[Date - Publication])'
    term = f"({journal_query}) AND {date_query}"
    params = urllib.parse.urlencode(
        {
            "db": "pubmed",
            "term": term,
            "retmode": "json",
            "retmax": "300",
            "sort": "pub+date",
        }
    )
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{params}"
    data = json.loads(fetch_url(url).decode("utf-8"))
    return data.get("esearchresult", {}).get("idlist", [])


def pubmed_fetch(pmids: list[str]) -> list[dict]:
    if not pmids:
        return []
    articles = []
    for i in range(0, len(pmids), 100):
        chunk = pmids[i : i + 100]
        params = urllib.parse.urlencode({"db": "pubmed", "id": ",".join(chunk), "retmode": "xml"})
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?{params}"
        root = ET.fromstring(fetch_url(url, accept="application/xml"))
        for article in root.findall(".//PubmedArticle"):
            medline = article.find("MedlineCitation")
            art = medline.find("Article") if medline is not None else None
            if art is None:
                continue
            journal = text_of(art.find("./Journal/Title")) or text_of(art.find("./Journal/ISOAbbreviation"))
            title = html.unescape(text_of(art.find("ArticleTitle")))
            abstract = " ".join(text_of(x) for x in art.findall("./Abstract/AbstractText")).strip()
            pubdate = extract_pubmed_date(art)
            doi = ""
            for aid in article.findall(".//ArticleId"):
                if aid.attrib.get("IdType") == "doi":
                    doi = text_of(aid)
            pmid = text_of(medline.find("PMID")) if medline is not None else ""
            pubtypes = [text_of(x) for x in art.findall("./PublicationTypeList/PublicationType")]
            articles.append(
                {
                    "date": pubdate,
                    "journal": journal,
                    "title": title,
                    "doi": doi,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else (f"https://doi.org/{doi}" if doi else ""),
                    "article_type": "; ".join(x for x in pubtypes if x),
                    "abstract": abstract,
                    "source": "PubMed",
                }
            )
        time.sleep(0.34)
    return articles


def extract_pubmed_date(article_node: ET.Element) -> str:
    pubdate = article_node.find("./Journal/JournalIssue/PubDate")
    if pubdate is None:
        return ""
    year = text_of(pubdate.find("Year"))
    month = text_of(pubdate.find("Month"))
    day = text_of(pubdate.find("Day")) or "01"
    if not year:
        medline = text_of(pubdate.find("MedlineDate"))
        match = re.search(r"\d{4}", medline)
        year = match.group(0) if match else ""
    month_map = {
        "jan": "01",
        "feb": "02",
        "mar": "03",
        "apr": "04",
        "may": "05",
        "jun": "06",
        "jul": "07",
        "aug": "08",
        "sep": "09",
        "oct": "10",
        "nov": "11",
        "dec": "12",
    }
    mm = month_map.get(month[:3].lower(), month.zfill(2) if month.isdigit() else "01")
    return f"{year}-{mm}-{day.zfill(2)}" if year else ""


def crossref_search(journals: list[str], start: dt.date, end: dt.date) -> list[dict]:
    rows = []
    for journal in journals:
        query = urllib.parse.urlencode(
            {
                "filter": f"from-pub-date:{start.isoformat()},until-pub-date:{end.isoformat()},type:journal-article",
                "query.container-title": journal,
                "rows": "50",
                "sort": "published",
                "order": "desc",
            }
        )
        url = f"https://api.crossref.org/works?{query}"
        try:
            data = json.loads(fetch_url(url).decode("utf-8"))
        except Exception as exc:
            print(f"[warn] Crossref failed for {journal}: {exc}", file=sys.stderr)
            continue
        for item in data.get("message", {}).get("items", []):
            container = (item.get("container-title") or [""])[0]
            if container and normalize_title(journal) not in normalize_title(container) and normalize_title(container) not in normalize_title(journal):
                continue
            title = html.unescape((item.get("title") or [""])[0])
            doi = item.get("DOI", "")
            abstract = re.sub("<[^>]+>", " ", item.get("abstract", "") or "")
            rows.append(
                {
                    "date": crossref_date(item),
                    "journal": container or journal,
                    "title": title,
                    "doi": doi,
                    "url": item.get("URL") or (f"https://doi.org/{doi}" if doi else ""),
                    "article_type": item.get("type", "journal-article"),
                    "abstract": " ".join(html.unescape(abstract).split()),
                    "source": "Crossref",
                }
            )
        time.sleep(1.0)
    return rows


def crossref_date(item: dict) -> str:
    for key in ("published-online", "published-print", "published"):
        parts = item.get(key, {}).get("date-parts", [])
        if parts and parts[0]:
            ymd = list(parts[0]) + [1, 1]
            return f"{ymd[0]:04d}-{ymd[1]:02d}-{ymd[2]:02d}"
    return ""


def rss_search(urls: list[str]) -> list[dict]:
    rows = []
    for feed in urls:
        try:
            root = ET.fromstring(fetch_url(feed, accept="application/rss+xml, application/xml"))
        except Exception as exc:
            print(f"[warn] RSS failed for {feed}: {exc}", file=sys.stderr)
            continue
        for item in root.findall(".//item") + root.findall(".//{http://www.w3.org/2005/Atom}entry"):
            title = html.unescape(text_of(item.find("title")) or text_of(item.find("{http://www.w3.org/2005/Atom}title")))
            link = text_of(item.find("link"))
            if not link:
                atom_link = item.find("{http://www.w3.org/2005/Atom}link")
                link = atom_link.attrib.get("href", "") if atom_link is not None else ""
            rows.append(
                {
                    "date": text_of(item.find("pubDate")) or text_of(item.find("{http://www.w3.org/2005/Atom}published")),
                    "journal": "",
                    "title": title,
                    "doi": "",
                    "url": link,
                    "article_type": "rss-item",
                    "abstract": html.unescape(text_of(item.find("description"))),
                    "source": "RSS",
                }
            )
    return rows


def deduplicate(rows: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for row in rows:
        key = row.get("doi", "").lower().strip() or normalize_title(row.get("title", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def score_rows(rows: list[dict], keywords: list[str], top_limit: int) -> list[dict]:
    novelty_terms = [
        "first",
        "novel",
        "new",
        "atlas",
        "trial",
        "phase",
        "single-cell",
        "spatial",
        "crispr",
        "ai",
        "foundation model",
        "mechanism",
        "therapy",
    ]
    kws = [k.lower() for k in keywords if k]
    scored = []
    for row in rows:
        haystack = f"{row.get('title','')} {row.get('abstract','')}".lower()
        relevance = sum(2 for k in kws if k in haystack)
        novelty = sum(1 for term in novelty_terms if term in haystack)
        if row.get("abstract"):
            relevance += 1
        row["relevance_score"] = relevance
        row["novelty_score"] = novelty
        scored.append(row)
    ranked = sorted(scored, key=lambda r: (r["relevance_score"] + r["novelty_score"], r.get("date", "")), reverse=True)
    top_keys = {r.get("doi", "").lower() or normalize_title(r.get("title", "")) for r in ranked[:top_limit]}
    for row in scored:
        key = row.get("doi", "").lower() or normalize_title(row.get("title", ""))
        row["top_pick"] = "yes" if key in top_keys else "no"
        row["reason"] = reason_for(row)
    return sorted(scored, key=lambda r: (r.get("journal", ""), r.get("date", ""), r.get("title", "")))


def reason_for(row: dict) -> str:
    reasons = []
    if row.get("relevance_score", 0) > 0:
        reasons.append("matches configured/user topic terms")
    if row.get("novelty_score", 0) > 1:
        reasons.append("contains novelty or high-impact signals")
    if row.get("abstract"):
        reasons.append("abstract available")
    return "; ".join(reasons) or "metadata-only inclusion"


def load_seen(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        return set(json.loads(path.read_text(encoding="utf-8")).get("seen", []))
    except Exception:
        return set()


def save_seen(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    seen = sorted({row.get("doi", "").lower() or normalize_title(row.get("title", "")) for row in rows if row.get("title")})
    path.write_text(json.dumps({"seen": seen}, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = ["date", "journal", "title", "doi", "url", "article_type", "abstract", "source", "relevance_score", "novelty_score", "top_pick", "reason"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_markdown(path: Path, rows: list[dict], start: dt.date, end: dt.date, source_notes: list[str]) -> None:
    top = sorted([r for r in rows if r.get("top_pick") == "yes"], key=lambda r: (r.get("relevance_score", 0) + r.get("novelty_score", 0)), reverse=True)
    lines = [
        f"# 顶刊前沿追踪 ({start.isoformat()} 至 {end.isoformat()})",
        "",
        "## 本期概览",
        "",
        f"- 收录文章：{len(rows)} 篇",
        f"- Top picks：{len(top)} 篇",
        "- 摘要依据：标题、摘要、DOI、期刊、发布日期和公共元数据；未默认读取付费全文。",
        "",
        "## Top picks",
        "",
    ]
    if not top:
        lines.append("本期没有足够元数据支持的 Top picks。")
    for i, row in enumerate(top, 1):
        lines.extend(render_card(row, index=i))
    lines.extend(["", "## 按期刊分组", ""])
    for journal in sorted({r.get("journal", "Unknown") or "Unknown" for r in rows}):
        lines.extend([f"### {journal}", ""])
        for row in [r for r in rows if (r.get("journal") or "Unknown") == journal]:
            lines.extend(render_card(row))
    lines.extend(["", "## 检索说明", ""])
    for note in source_notes:
        lines.append(f"- {note}")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def render_card(row: dict, index: int | None = None) -> list[str]:
    prefix = f"{index}. " if index is not None else "- "
    title = row.get("title") or "(untitled)"
    doi = row.get("doi")
    url = row.get("url")
    link = f"https://doi.org/{doi}" if doi else url
    abstract = row.get("abstract") or ""
    conclusion = abstract[:220] + ("..." if len(abstract) > 220 else "") if abstract else "公共元数据未提供摘要，需进一步查看期刊页面或全文。"
    return [
        f"{prefix}**{title}**",
        f"  - 期刊/日期：{row.get('journal','')}，{row.get('date','')}",
        f"  - DOI/链接：{doi or link or 'N/A'}",
        f"  - 一句话结论：{conclusion}",
        f"  - 创新/跟进价值：{row.get('reason','metadata-only inclusion')}",
        f"  - 局限：当前卡片基于公共摘要/元数据，未默认阅读全文。",
        "",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Track recent papers from top journals.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--journals", default="")
    parser.add_argument("--keywords", default="")
    parser.add_argument("--output", default=str(SKILL_DIR / "reports"))
    parser.add_argument("--weekly", action="store_true", help="Skip articles already stored in state/seen_articles.json")
    parser.add_argument("--include-seen", action="store_true")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    days = args.days or int(config.get("days", 7))
    end = today_utc()
    start = end - dt.timedelta(days=days)
    journals = [j.strip() for j in args.journals.split(",") if j.strip()] or config.get("journals", [])
    topics = config.get("topics", {})
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()] + topics.get("include", [])
    top_limit = int(config.get("top_pick_limit", 10))

    source_notes = []
    rows = []
    try:
        pmids = pubmed_search(journals, start, end)
        rows.extend(pubmed_fetch(pmids))
        source_notes.append(f"PubMed returned {len(pmids)} candidate records.")
    except Exception as exc:
        source_notes.append(f"PubMed failed: {exc}")

    crossref_rows = crossref_search(journals, start, end)
    rows.extend(crossref_rows)
    source_notes.append(f"Crossref returned {len(crossref_rows)} candidate records after journal filtering.")

    rss_rows = rss_search(config.get("rss_feeds", []))
    rows.extend(rss_rows)
    if config.get("rss_feeds"):
        source_notes.append(f"RSS returned {len(rss_rows)} candidate records.")

    rows = deduplicate(rows)
    if args.weekly and not args.include_seen:
        seen = load_seen(DEFAULT_STATE)
        rows = [r for r in rows if (r.get("doi", "").lower() or normalize_title(r.get("title", ""))) not in seen]
    rows = score_rows(rows, keywords, top_limit)

    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = end.isoformat()
    csv_path = outdir / f"{stamp}-journal-frontier-digest.csv"
    md_path = outdir / f"{stamp}-journal-frontier-digest.md"
    write_csv(csv_path, rows)
    write_markdown(md_path, rows, start, end, source_notes)
    if args.weekly:
        save_seen(DEFAULT_STATE, rows)

    print(f"Wrote {md_path}")
    print(f"Wrote {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
