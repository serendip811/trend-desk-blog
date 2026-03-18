#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import textwrap
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urljoin
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
OUTPUT_DIR = ROOT / "outputs"
DRAFT_DIR = OUTPUT_DIR / "drafts"
USER_AGENT = "trend-content-pipeline/0.1"


@dataclass
class Entry:
    source: str
    title: str
    url: str
    published_at: str | None
    summary: str
    tags: list[str]
    score: float = 0.0
    score_breakdown: dict[str, float] | None = None


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def fetch_url(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=20) as response:
        return response.read()


def decode_payload(payload: bytes, encoding: str | None = None) -> str:
    candidates = [encoding, "utf-8", "cp949", "euc-kr"]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return payload.decode(candidate)
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="ignore")


def parse_rss(source: dict[str, Any]) -> list[Entry]:
    payload = fetch_url(source["url"])
    root = ET.fromstring(payload)
    items = root.findall(".//item")
    entries: list[Entry] = []
    for item in items:
        title = clean_text(item.findtext("title"))
        link = clean_text(item.findtext("link"))
        summary = clean_text(item.findtext("description"))
        published = clean_text(item.findtext("pubDate")) or None
        tags = source.get("topic_tags", [])
        if not title or not link:
            continue
        entries.append(
            Entry(
                source=source["name"],
                title=title,
                url=link,
                published_at=published,
                summary=summary,
                tags=tags,
            )
        )
    return entries


def parse_json_source(source: dict[str, Any]) -> list[Entry]:
    payload = fetch_url(source["url"])
    data = json.loads(decode_payload(payload, source.get("encoding")))
    items = data
    for part in source.get("items_path", []):
        items = items[part]

    entries: list[Entry] = []
    for item in items:
        title = clean_text(read_path(item, source.get("field_map", {}).get("title", "title")))
        link = clean_text(read_path(item, source.get("field_map", {}).get("url", "url")))
        summary = clean_text(read_path(item, source.get("field_map", {}).get("summary", "summary")))
        published = clean_text(read_path(item, source.get("field_map", {}).get("published_at", "published_at"))) or None
        tags = source.get("topic_tags", [])
        if not title or not link:
            continue
        entries.append(
            Entry(
                source=source["name"],
                title=title,
                url=link,
                published_at=published,
                summary=summary,
                tags=tags,
            )
        )
    return entries


def parse_html_source(source: dict[str, Any]) -> list[Entry]:
    payload = fetch_url(source["url"])
    text = decode_payload(payload, source.get("encoding"))

    start_marker = source.get("section_start_marker")
    if start_marker:
        start_index = text.find(start_marker)
        if start_index != -1:
            text = text[start_index:]

    section_char_limit = source.get("section_char_limit")
    if section_char_limit:
        text = text[: int(section_char_limit)]

    section_pattern = source.get("section_pattern")
    if section_pattern:
        section_match = re.search(section_pattern, text, re.S)
        if section_match:
            text = section_match.group(0)

    item_pattern = source.get("item_pattern")
    if not item_pattern:
        raise ValueError(f"HTML source {source['name']} is missing item_pattern")

    entries: list[Entry] = []
    seen: set[tuple[str, str]] = set()
    max_items = int(source.get("max_items", 0) or 0)
    for match in re.finditer(item_pattern, text, re.S):
        groups = match.groupdict()
        title = clean_text(groups.get("title"))
        url = clean_text(groups.get("url"))
        summary = clean_text(groups.get("summary"))
        published = clean_text(groups.get("published_at")) or None
        if not title or not url:
            continue
        url = urljoin(source.get("base_url", source["url"]), url)
        key = (title, url)
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            Entry(
                source=source["name"],
                title=title,
                url=url,
                published_at=published,
                summary=summary,
                tags=source.get("topic_tags", []),
            )
        )
        if max_items and len(entries) >= max_items:
            break
    return entries


def read_path(item: Any, path: str) -> Any:
    current = item
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(value))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_published_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return datetime.fromisoformat(value)
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None


def recency_score(published_at: str | None) -> float:
    dt = parse_published_at(published_at)
    if dt is None:
        return 0.25
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    age_hours = max((datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 3600, 0)
    return max(0.0, 1.0 - min(age_hours / 168, 1.0))


def keyword_score(text: str, keywords: list[str]) -> float:
    lower = text.lower()
    matches = 0
    for keyword in keywords:
        if keyword.lower() in lower:
            matches += 1
    if not keywords:
        return 0.0
    return min(matches / max(len(keywords), 1) * 3, 1.0)


def commercial_score(text: str, terms: list[str]) -> float:
    lower = text.lower()
    hits = sum(1 for term in terms if term.lower() in lower)
    return min(hits * 0.25, 1.0)


def score_entries(entries: list[Entry], config: dict[str, Any], source_map: dict[str, dict[str, Any]]) -> list[Entry]:
    boosts = config.get("keyword_boosts", [])
    global_commercial_terms = config.get("commercial_terms", [])
    for entry in entries:
        source = source_map[entry.source]
        text = f"{entry.title} {entry.summary} {' '.join(entry.tags)}"
        recency = recency_score(entry.published_at)
        keyword = keyword_score(text, boosts)
        commercial = commercial_score(text, global_commercial_terms + source.get("commercial_terms", []))
        source_weight = float(source.get("weight", 1.0))
        novelty = novelty_score(entry.title)
        score = (recency * 0.35) + (keyword * 0.25) + (commercial * 0.2) + (novelty * 0.2)
        entry.score = round(score * source_weight, 4)
        entry.score_breakdown = {
            "recency": round(recency, 4),
            "keyword_fit": round(keyword, 4),
            "commercial_intent": round(commercial, 4),
            "novelty": round(novelty, 4),
            "source_weight": source_weight,
        }
    return sorted(entries, key=lambda item: item.score, reverse=True)


def filter_entries(entries: list[Entry], config: dict[str, Any]) -> list[Entry]:
    filters = config.get("filters", {})
    must_match_any = [item.lower() for item in filters.get("must_match_any", [])]
    exclude_keywords = [item.lower() for item in filters.get("exclude_keywords", [])]
    min_score = float(filters.get("min_score", 0.0))
    min_keyword_or_commercial = float(filters.get("min_keyword_or_commercial", 0.0))

    filtered: list[Entry] = []
    for entry in entries:
        haystack = f"{entry.title} {entry.summary} {' '.join(entry.tags)}".lower()
        if exclude_keywords and any(keyword in haystack for keyword in exclude_keywords):
            continue
        if must_match_any and not any(keyword in haystack for keyword in must_match_any):
            continue
        if entry.score < min_score:
            continue
        breakdown = entry.score_breakdown or {}
        keyword_or_commercial = max(
            float(breakdown.get("keyword_fit", 0.0)),
            float(breakdown.get("commercial_intent", 0.0)),
        )
        if keyword_or_commercial < min_keyword_or_commercial:
            continue
        filtered.append(entry)
    return filtered


def novelty_score(title: str) -> float:
    tokens = tokenize(title)
    unique_ratio = len(set(tokens)) / max(len(tokens), 1)
    return min(max(unique_ratio, 0.2), 1.0)


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9가-힣]{2,}", text.lower())


def cluster_entries(entries: list[Entry]) -> list[list[Entry]]:
    clusters: list[list[Entry]] = []
    for entry in entries:
        placed = False
        entry_tokens = set(tokenize(entry.title))
        for cluster in clusters:
            cluster_tokens = set(tokenize(cluster[0].title))
            overlap = jaccard(entry_tokens, cluster_tokens)
            if overlap >= 0.35:
                cluster.append(entry)
                placed = True
                break
        if not placed:
            clusters.append([entry])
    return clusters


def jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    DRAFT_DIR.mkdir(parents=True, exist_ok=True)


def snapshot_entries(entries: list[Entry]) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = RAW_DIR / f"entries-{timestamp}.json"
    path.write_text(json.dumps([asdict(entry) for entry in entries], ensure_ascii=False, indent=2))
    return path


def slugify(text: str) -> str:
    text = "-".join(tokenize(text)[:8])
    return text[:80] or hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


def build_draft(entry: Entry, config: dict[str, Any], cluster: list[Entry]) -> str:
    sources = "\n".join(f"- {item.source}: {item.title} ({item.url})" for item in cluster[:5])
    related_keywords = ", ".join(extract_related_keywords(entry, cluster))
    audience = config.get("brand", {}).get("audience", "general readers")
    voice = config.get("brand", {}).get("voice", "clear and practical")
    title = entry.title
    return textwrap.dedent(
        f"""\
        # {title}

        - Primary angle: Turn this trend into a search-friendly post with practical value.
        - Suggested audience: {audience}
        - Suggested voice: {voice}
        - Related keywords: {related_keywords}
        - Score: {entry.score}

        ## Why this is worth publishing

        - The topic is recent and already appearing across one or more tracked feeds.
        - It has enough specificity to rewrite into a guide, roundup, comparison, or explainer.
        - It can be connected to search intent instead of pure news commentary.

        ## Suggested search angles

        - What happened and why it matters now
        - Who should care or act on it
        - Best options, comparisons, pricing, or next steps
        - Korea-specific usage, buying, or workflow implications

        ## Draft outline

        1. One-paragraph summary of the trend
        2. Why people are searching for it now
        3. Practical breakdown or comparison
        4. What to do next / checklist / recommendations
        5. FAQ

        ## Draft intro

        최근 `{title}` 관련 검색과 언급이 늘고 있습니다. 단순한 화제성 이슈로 끝나는지, 실제로 써볼 만한 정보인지 헷갈리는 분들이 많습니다. 이 글에서는 지금 왜 주목받는지, 어떤 사람에게 중요한지, 그리고 실제로 확인해야 할 포인트를 빠르게 정리합니다.

        ## Draft body points

        - 지금 뜨는 배경: 최근 발표, 업데이트, 출시, 이슈, 가격 변화, 사용자 반응
        - 실제 관심 포인트: 추천 여부, 가격/요금, 사용법, 비교 대상, 장단점
        - 검색형 정보로 바꾸기: "누가 써야 하나", "어떤 상황에 맞나", "대안은 뭔가"
        - 한국 독자 관점: 국내 사용 가능 여부, 결제/언어/지원/활용 방법

        ## FAQ ideas

        - 이 트렌드는 일시적인 이슈인가요?
        - 실제로 써보거나 구매할 가치가 있나요?
        - 한국 사용자 기준으로 주의할 점은 무엇인가요?
        - 대안이나 비교 대상은 무엇인가요?

        ## Source notes

        {sources}
        """
    ).strip() + "\n"


def extract_related_keywords(entry: Entry, cluster: list[Entry]) -> list[str]:
    counts: dict[str, int] = {}
    for item in [entry] + cluster:
        for token in tokenize(item.title):
            counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return [token for token, _count in ranked[:8]]


def write_outputs(entries: list[Entry], clusters: list[list[Entry]], config: dict[str, Any], limit: int) -> None:
    lines = ["# Trend Report", "", f"Generated at: {datetime.now().isoformat()}", ""]
    for index, cluster in enumerate(clusters[:limit], start=1):
        best = sorted(cluster, key=lambda item: item.score, reverse=True)[0]
        lines.append(f"## {index}. {best.title}")
        lines.append("")
        lines.append(f"- Score: {best.score}")
        lines.append(f"- Source: {best.source}")
        lines.append(f"- Published: {best.published_at or 'unknown'}")
        lines.append(f"- URL: {best.url}")
        if best.score_breakdown:
            breakdown = ", ".join(f"{key}={value}" for key, value in best.score_breakdown.items())
            lines.append(f"- Breakdown: {breakdown}")
        lines.append(f"- Related titles: {len(cluster)}")
        lines.append("")

        draft_path = DRAFT_DIR / f"{index:02d}-{slugify(best.title)}.md"
        draft_path.write_text(build_draft(best, config, cluster))
        lines.append(f"- Draft: `{draft_path.relative_to(ROOT)}`")
        lines.append("")

    (OUTPUT_DIR / "trend-report.md").write_text("\n".join(lines))


def collect_entries(config: dict[str, Any]) -> tuple[list[Entry], list[str]]:
    entries: list[Entry] = []
    errors: list[str] = []
    for source in config.get("sources", []):
        if not source.get("active", True):
            continue
        try:
            if source["type"] == "rss":
                entries.extend(parse_rss(source))
            elif source["type"] == "json":
                entries.extend(parse_json_source(source))
            elif source["type"] == "html":
                entries.extend(parse_html_source(source))
            else:
                errors.append(f"Unsupported source type for {source['name']}: {source['type']}")
        except (HTTPError, URLError, TimeoutError, ET.ParseError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{source['name']}: {exc}")
    return entries, errors


def run(config_path: Path, limit: int) -> int:
    ensure_dirs()
    config = load_config(config_path)
    entries, errors = collect_entries(config)
    if not entries:
        print("No entries collected.", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    source_map = {source["name"]: source for source in config.get("sources", [])}
    ranked = score_entries(entries, config, source_map)
    filtered = filter_entries(ranked, config)
    snapshot_path = snapshot_entries(ranked)
    if not filtered:
        filtered = ranked[:limit]
    clusters = cluster_entries(filtered)
    write_outputs(filtered, clusters, config, limit)

    print(f"Collected {len(entries)} entries")
    print(f"Filtered to {len(filtered)} entries")
    print(f"Saved snapshot to {snapshot_path.relative_to(ROOT)}")
    print(f"Wrote report to {(OUTPUT_DIR / 'trend-report.md').relative_to(ROOT)}")
    if errors:
        print("Completed with source warnings:")
        for error in errors:
            print(f"- {error}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Trend content pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Fetch sources and build outputs")
    run_parser.add_argument("--config", default="config/sources.json", help="Config path")
    run_parser.add_argument("--limit", type=int, default=8, help="How many top clusters to output")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "run":
        return run(ROOT / args.config, args.limit)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
