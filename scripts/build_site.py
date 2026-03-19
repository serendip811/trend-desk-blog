#!/usr/bin/env python3

from __future__ import annotations

import html
import json
import re
import textwrap
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content"
POST_SOURCE_DIR = CONTENT_DIR / "posts"
SITE_DIR = ROOT / "site"
POST_OUTPUT_DIR = SITE_DIR / "posts"
CATEGORY_OUTPUT_DIR = SITE_DIR / "categories"
CONFIG_PATH = CONTENT_DIR / "site.json"


@dataclass(frozen=True)
class Category:
    slug: str
    name: str
    feed_label: str
    description: str
    coming_soon: bool = False


@dataclass(frozen=True)
class Post:
    slug: str
    title: str
    page_title: str
    breadcrumb_title: str
    description: str
    summary: str
    deck: str
    date: str
    updated_at: str
    category_slug: str
    feature_badge: str | None
    image: str | None
    image_alt: str | None
    published: bool
    listed: bool
    rss: bool
    sitemap: bool
    body_html: str


def load_site_config() -> tuple[dict[str, object], list[Category], dict[str, Category]]:
    data = json.loads(CONFIG_PATH.read_text())
    categories = [Category(**item) for item in data["categories"]]
    category_map = {category.slug: category for category in categories}
    return data, categories, category_map


def parse_front_matter(raw: str) -> tuple[dict[str, object], str]:
    match = re.match(r"^---\n(.*?)\n---\n?(.*)$", raw, re.S)
    if not match:
        raise ValueError("Post source is missing front matter block")

    meta_block, body = match.groups()
    metadata: dict[str, object] = {}
    for line in meta_block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, value = stripped.split(":", 1)
        metadata[key.strip()] = parse_value(value.strip())
    return metadata, body.strip() + "\n"


def parse_value(raw: str) -> object:
    lowered = raw.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    if raw.startswith("[") or raw.startswith("{") or raw.startswith('"'):
        return json.loads(raw)
    return raw


def load_posts(category_map: dict[str, Category]) -> list[Post]:
    posts: list[Post] = []
    for path in sorted(POST_SOURCE_DIR.glob("*.html")):
        metadata, body_html = parse_front_matter(path.read_text())
        slug = str(metadata.get("slug", path.stem))
        category_slug = str(metadata["category"])
        if category_slug not in category_map:
            raise ValueError(f"Unknown category '{category_slug}' in {path.name}")

        published = bool(metadata.get("published", True))
        listed = bool(metadata.get("listed", published))
        rss = bool(metadata.get("rss", listed))
        sitemap = bool(metadata.get("sitemap", listed))

        posts.append(
            Post(
                slug=slug,
                title=str(metadata["title"]),
                page_title=str(metadata.get("page_title", metadata["title"])),
                breadcrumb_title=str(metadata.get("breadcrumb_title", metadata["title"])),
                description=str(metadata["description"]),
                summary=str(metadata["summary"]),
                deck=str(metadata["deck"]),
                date=str(metadata["date"]),
                updated_at=str(metadata.get("updated_at", metadata["date"])),
                category_slug=category_slug,
                feature_badge=metadata.get("feature_badge") and str(metadata["feature_badge"]),
                image=metadata.get("image") and str(metadata["image"]),
                image_alt=metadata.get("image_alt") and str(metadata["image_alt"]),
                published=published,
                listed=listed,
                rss=rss,
                sitemap=sitemap,
                body_html=body_html,
            )
        )
    return sorted(posts, key=lambda post: (post.date, post.slug), reverse=True)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def remove_managed_outputs() -> None:
    POST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CATEGORY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for path in POST_OUTPUT_DIR.glob("*.html"):
        path.unlink()
    for path in CATEGORY_OUTPUT_DIR.glob("*.html"):
        path.unlink()


def escape(value: str) -> str:
    return html.escape(value, quote=True)


def absolute_url(base_url: str, path: str | None) -> str:
    if not path:
        return base_url.rstrip("/")
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def format_title(site_title: str, page_title: str) -> str:
    if page_title == site_title:
        return site_title
    return f"{page_title} | {site_title}"


def iso_to_rss(value: str) -> str:
    dt = datetime.fromisoformat(value).replace(tzinfo=timezone.utc, hour=12)
    return format_datetime(dt)


def indent_html(raw: str, spaces: int = 8) -> str:
    return textwrap.indent(raw.rstrip(), " " * spaces)


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def strip_tags(value: str) -> str:
    return normalize_whitespace(re.sub(r"<[^>]+>", " ", value))


def json_ld_block(data: dict[str, object] | list[dict[str, object]] | None) -> str:
    if not data:
        return ""
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'\n  <script type="application/ld+json">{payload}</script>'


def publisher_schema(site: dict[str, object]) -> dict[str, object]:
    base_url = str(site["base_url"])
    return {
        "@type": "Organization",
        "name": str(site["site_title"]),
        "url": base_url.rstrip("/") + "/",
        "logo": {
            "@type": "ImageObject",
            "url": absolute_url(base_url, "assets/favicon.svg"),
        },
    }


def breadcrumb_schema(base_url: str, items: list[tuple[str, str]]) -> dict[str, object]:
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index,
                "name": name,
                "item": absolute_url(base_url, path),
            }
            for index, (name, path) in enumerate(items, start=1)
        ],
    }


def item_list_schema(base_url: str, name: str, items: list[tuple[str, str]]) -> dict[str, object]:
    return {
        "@type": "ItemList",
        "name": name,
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index,
                "url": absolute_url(base_url, path),
                "name": label,
            }
            for index, (label, path) in enumerate(items, start=1)
        ],
    }


def extract_faq_pairs(body_html: str) -> list[tuple[str, str]]:
    section_match = re.search(r"<h2>\s*자주 묻는 질문\s*</h2>(.*?)(?:<div class=\"article-bottom-links\">|$)", body_html, re.S)
    if not section_match:
        return []

    section = section_match.group(1)
    pairs: list[tuple[str, str]] = []
    for question, answer_html in re.findall(r"<h3>\s*Q\.?\s*(.*?)\s*</h3>\s*(<p>.*?</p>)", section, re.S):
        cleaned_question = strip_tags(question)
        cleaned_answer = strip_tags(answer_html)
        if cleaned_question and cleaned_answer:
            pairs.append((cleaned_question, cleaned_answer))
    return pairs


def faq_schema(faq_pairs: list[tuple[str, str]]) -> dict[str, object] | None:
    if not faq_pairs:
        return None

    return {
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": question,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": answer,
                },
            }
            for question, answer in faq_pairs
        ],
    }


def build_robots(site: dict[str, object]) -> str:
    return "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "",
            f"Sitemap: {absolute_url(str(site['base_url']), '/sitemap.xml')}",
            "",
        ]
    )


def build_head(
    *,
    site: dict[str, object],
    prefix: str,
    page_title: str,
    description: str,
    canonical_path: str,
    og_type: str = "website",
    og_image: str | None = None,
    og_image_alt: str | None = None,
    robots: str = "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1",
    extra_meta: str = "",
    structured_data: dict[str, object] | list[dict[str, object]] | None = None,
) -> str:
    site_title = str(site["site_title"])
    base_url = str(site["base_url"])
    resolved_title = format_title(site_title, page_title)
    canonical_url = absolute_url(base_url, canonical_path)
    image_url = absolute_url(base_url, og_image or str(site["default_og_image"]))
    image_alt = og_image_alt or resolved_title

    extra = f"\n{extra_meta.rstrip()}" if extra_meta else ""
    structured_data_block = json_ld_block(structured_data)
    return f"""<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(resolved_title)}</title>
  <meta name="description" content="{escape(description)}">
  <meta name="robots" content="{escape(robots)}">
  <link rel="canonical" href="{escape(canonical_url)}">
  <meta property="og:type" content="{escape(og_type)}">
  <meta property="og:title" content="{escape(resolved_title)}">
  <meta property="og:description" content="{escape(description)}">
  <meta property="og:url" content="{escape(canonical_url)}">
  <meta property="og:site_name" content="{escape(site_title)}">
  <meta property="og:locale" content="ko_KR">
  <meta property="og:image" content="{escape(image_url)}">
  <meta property="og:image:alt" content="{escape(image_alt)}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escape(resolved_title)}">
  <meta name="twitter:description" content="{escape(description)}">
  <meta name="twitter:image" content="{escape(image_url)}">
  <meta name="twitter:image:alt" content="{escape(image_alt)}">
  <link rel="icon" href="{prefix}assets/favicon.svg" type="image/svg+xml">
  <link rel="alternate" type="application/rss+xml" title="{escape(site_title)} RSS" href="{prefix}rss.xml">
  <link rel="stylesheet" href="{prefix}styles.css">{extra}{structured_data_block}
</head>"""


def render_header(site: dict[str, object], *, prefix: str, current_section: str | None) -> str:
    nav_items = [
        ("home", f"{prefix}index.html", "홈"),
        ("archive", f"{prefix}archive.html", "글 목록"),
        ("categories", f"{prefix}categories/index.html", "카테고리"),
        ("rss", f"{prefix}rss.xml", "RSS"),
    ]
    nav_html = []
    for section, href, label in nav_items:
        current = ' aria-current="page"' if current_section == section else ""
        nav_html.append(f'<a href="{href}"{current}>{escape(label)}</a>')

    return f"""<header class="site-header">
      <div class="site-header-top">
        <a class="site-title" href="{prefix}index.html">{escape(str(site["site_title"]))}</a>
        <p class="site-tagline">{escape(str(site["tagline"]))}</p>
      </div>
      <nav class="site-nav" aria-label="주요 메뉴">
        {' '.join(nav_html)}
      </nav>
    </header>"""


def render_footer(site: dict[str, object], *, prefix: str) -> str:
    return f"""<footer class="site-footer-simple">
      <div>
        <strong>{escape(str(site["site_title"]))}</strong>
        <p>{escape(str(site["footer_text"]))}</p>
      </div>
      <div class="footer-links-simple">
        <a href="{prefix}archive.html">글 목록</a>
        <a href="{prefix}categories/index.html">카테고리</a>
        <a href="{prefix}rss.xml">RSS</a>
      </div>
    </footer>"""


def render_feed_item(post: Post, categories: dict[str, Category], *, prefix: str, show_category_link: bool) -> str:
    category = categories[post.category_slug]
    meta_bits = [
        f'<span class="feed-category">{escape(category.feed_label)}</span>',
        f"<span>{escape(post.date)}</span>",
    ]
    if show_category_link:
        meta_bits.append(f'<a href="{prefix}categories/{category.slug}.html">카테고리 보기</a>')

    return f"""<article class="feed-item">
        <div class="feed-main">
          <h2><a href="{prefix}posts/{post.slug}.html">{escape(post.title)}</a></h2>
          <p class="feed-summary">{escape(post.summary)}</p>
          <div class="feed-meta">
            {' '.join(meta_bits)}
          </div>
        </div>
      </article>"""


def render_page(site: dict[str, object], head: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ko">
{head}
<body>
  <div class="layout-shell">
{body}
  </div>
</body>
</html>
"""


def build_home(site: dict[str, object], posts: list[Post], categories: dict[str, Category]) -> str:
    base_url = str(site["base_url"])
    listed_posts = [post for post in posts if post.listed]
    structured_data: list[dict[str, object]] = [
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": str(site["site_title"]),
            "url": base_url.rstrip("/") + "/",
            "description": str(site["default_description"]),
            "publisher": publisher_schema(site),
        },
        {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": str(site["home_title"]),
            "url": base_url.rstrip("/") + "/",
            "description": str(site["home_description"]),
            "inLanguage": "ko-KR",
            "publisher": publisher_schema(site),
            "image": absolute_url(base_url, str(site["default_og_image"])),
            "isPartOf": {"@type": "WebSite", "name": str(site["site_title"]), "url": base_url.rstrip("/") + "/"},
            "mainEntity": item_list_schema(
                base_url,
                "Trend Desk 최신 글",
                [(post.title, f"/posts/{post.slug}.html") for post in listed_posts],
            ),
        },
    ]
    head = build_head(
        site=site,
        prefix="",
        page_title=str(site["home_title"]),
        description=str(site["default_description"]),
        canonical_path="/",
        structured_data=structured_data,
    )
    feed_html = "\n\n".join(
        render_feed_item(post, categories, prefix="", show_category_link=True) for post in listed_posts
    )
    body = f"""    {render_header(site, prefix='', current_section='home')}

    <main class="content-wrap">
      <section class="page-head">
        <p class="page-kicker">{escape(str(site["home_kicker"]))}</p>
        <h1>{escape(str(site["home_title"]))}</h1>
        <p class="page-desc">{escape(str(site["home_description"]))}</p>
      </section>

      <section class="feed-section" id="latest">
{indent_html(feed_html, 8)}
      </section>
    </main>

    {render_footer(site, prefix='')}"""
    return render_page(site, head, body)


def build_archive(site: dict[str, object], posts: list[Post], categories: dict[str, Category]) -> str:
    base_url = str(site["base_url"])
    listed_posts = [post for post in posts if post.listed]
    structured_data: list[dict[str, object]] = [
        {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": "전체 글 목록",
            "url": absolute_url(base_url, "/archive.html"),
            "description": "Trend Desk에 올라온 전체 글 목록입니다.",
            "inLanguage": "ko-KR",
            "publisher": publisher_schema(site),
            "image": absolute_url(base_url, str(site["default_og_image"])),
            "isPartOf": {"@type": "WebSite", "name": str(site["site_title"]), "url": base_url.rstrip("/") + "/"},
            "mainEntity": item_list_schema(
                base_url,
                "Trend Desk 전체 글",
                [(post.title, f"/posts/{post.slug}.html") for post in listed_posts],
            ),
        },
        {
            "@context": "https://schema.org",
            **breadcrumb_schema(base_url, [("홈", "/"), ("글 목록", "/archive.html")]),
        },
    ]
    head = build_head(
        site=site,
        prefix="",
        page_title="글 목록",
        description="Trend Desk에 올라온 전체 글 목록입니다.",
        canonical_path="/archive.html",
        structured_data=structured_data,
    )
    feed_html = "\n\n".join(
        render_feed_item(post, categories, prefix="", show_category_link=False) for post in listed_posts
    )
    body = f"""    {render_header(site, prefix='', current_section='archive')}

    <main class="content-wrap">
      <section class="page-head compact-head">
        <p class="page-kicker">아카이브</p>
        <h1>전체 글 목록</h1>
      </section>

      <section class="feed-section">
{indent_html(feed_html, 8)}
      </section>
    </main>

    {render_footer(site, prefix='')}"""
    return render_page(site, head, body)


def build_category_index(site: dict[str, object], categories: list[Category], posts: list[Post]) -> str:
    base_url = str(site["base_url"])
    visible_categories = [category for category in categories if not category.coming_soon]
    head = build_head(
        site=site,
        prefix="../",
        page_title="카테고리",
        description="Trend Desk의 카테고리 목록입니다.",
        canonical_path="/categories/index.html",
        structured_data=[
            {
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": "Trend Desk 카테고리",
                "url": absolute_url(base_url, "/categories/index.html"),
                "description": "Trend Desk의 카테고리 목록입니다.",
                "inLanguage": "ko-KR",
                "publisher": publisher_schema(site),
                "image": absolute_url(base_url, str(site["default_og_image"])),
                "mainEntity": item_list_schema(
                    base_url,
                    "Trend Desk 카테고리 목록",
                    [(category.name, f"/categories/{category.slug}.html") for category in visible_categories],
                ),
            },
            {
                "@context": "https://schema.org",
                **breadcrumb_schema(base_url, [("홈", "/"), ("카테고리", "/categories/index.html")]),
            },
        ],
    )
    counts = defaultdict(int)
    for post in posts:
        if post.listed:
            counts[post.category_slug] += 1

    items: list[str] = []
    for category in categories:
        if category.coming_soon:
            items.append(
                f"""<article class="feed-item category-feed-item muted-item">
          <div class="feed-main">
            <div class="feed-meta"><span>준비 중</span></div>
            <h2>{escape(category.name)}</h2>
            <p class="feed-summary">{escape(category.description)}</p>
          </div>
        </article>"""
            )
            continue

        count_text = f"{counts[category.slug]}개 글"
        items.append(
            f"""<article class="feed-item category-feed-item">
          <div class="feed-main">
            <div class="feed-meta"><span class="feed-category">{escape(count_text)}</span></div>
            <h2><a href="{category.slug}.html">{escape(category.name)}</a></h2>
            <p class="feed-summary">{escape(category.description)}</p>
          </div>
        </article>"""
        )

    body = f"""    {render_header(site, prefix='../', current_section='categories')}

    <main class="content-wrap">
      <section class="page-head compact-head">
        <p class="page-kicker">카테고리</p>
        <h1>주제별 보기</h1>
      </section>

      <section class="feed-section">
{indent_html('\n\n'.join(items), 8)}
      </section>
    </main>

    {render_footer(site, prefix='../')}"""
    return render_page(site, head, body)


def build_category_page(site: dict[str, object], category: Category, posts: list[Post], categories: dict[str, Category]) -> str:
    base_url = str(site["base_url"])
    head = build_head(
        site=site,
        prefix="../",
        page_title=category.name,
        description=f"Trend Desk의 {category.name} 카테고리입니다.",
        canonical_path=f"/categories/{category.slug}.html",
        structured_data=[
            {
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": category.name,
                "url": absolute_url(base_url, f"/categories/{category.slug}.html"),
                "description": category.description,
                "inLanguage": "ko-KR",
                "publisher": publisher_schema(site),
                "image": absolute_url(base_url, str(site["default_og_image"])),
                "mainEntity": item_list_schema(
                    base_url,
                    f"{category.name} 글 목록",
                    [(post.title, f"/posts/{post.slug}.html") for post in posts],
                ),
            },
            {
                "@context": "https://schema.org",
                **breadcrumb_schema(base_url, [("홈", "/"), ("카테고리", "/categories/index.html"), (category.name, f"/categories/{category.slug}.html")]),
            },
        ],
    )
    feed_html = "\n\n".join(
        render_feed_item(post, categories, prefix="../", show_category_link=False) for post in posts
    )
    body = f"""    {render_header(site, prefix='../', current_section='categories')}

    <main class="content-wrap">
      <section class="page-head compact-head">
        <p class="page-kicker">카테고리</p>
        <h1>{escape(category.name)}</h1>
        <p class="page-desc">{escape(category.description)}</p>
      </section>

      <section class="feed-section">
{indent_html(feed_html, 8)}
      </section>
    </main>

    {render_footer(site, prefix='../')}"""
    return render_page(site, head, body)


def build_post_page(site: dict[str, object], post: Post, category: Category) -> str:
    base_url = str(site["base_url"])
    article_meta = "\n".join(
        [
            f'  <meta property="article:published_time" content="{escape(post.date)}">',
            f'  <meta property="article:modified_time" content="{escape(post.updated_at)}">',
            f'  <meta property="article:section" content="{escape(category.name)}">',
            '  <meta name="author" content="Trend Desk">',
        ]
    )
    robots = "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1" if post.listed else "noindex,follow"
    breadcrumb_data = {
        "@context": "https://schema.org",
        **breadcrumb_schema(
            base_url,
            [
                ("홈", "/"),
                ("카테고리", f"/categories/{category.slug}.html"),
                (post.breadcrumb_title, f"/posts/{post.slug}.html"),
            ],
        ),
    }
    article_data: dict[str, object] = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": post.title,
        "description": post.description,
        "datePublished": post.date,
        "dateModified": post.updated_at,
        "mainEntityOfPage": absolute_url(base_url, f"/posts/{post.slug}.html"),
        "url": absolute_url(base_url, f"/posts/{post.slug}.html"),
        "inLanguage": "ko-KR",
        "articleSection": category.name,
        "isPartOf": {"@type": "WebSite", "name": str(site["site_title"]), "url": base_url.rstrip("/") + "/"},
        "author": {
            "@type": "Organization",
            "name": str(site["site_title"]),
        },
        "publisher": publisher_schema(site),
        "image": [absolute_url(base_url, post.image)] if post.image else [absolute_url(base_url, str(site["default_og_image"]))],
    }
    faq_data = faq_schema(extract_faq_pairs(post.body_html))
    structured_data: list[dict[str, object]] = [breadcrumb_data, article_data]
    if faq_data:
        structured_data.append({"@context": "https://schema.org", **faq_data})
    head = build_head(
        site=site,
        prefix="../",
        page_title=post.page_title,
        description=post.description,
        canonical_path=f"/posts/{post.slug}.html",
        og_type="article",
        og_image=post.image or str(site["default_og_image"]),
        og_image_alt=post.image_alt or post.title,
        robots=robots,
        extra_meta=article_meta,
        structured_data=structured_data,
    )

    meta_bits = [f'<span class="feed-category">{escape(category.feed_label)}</span>', f"<span>{escape(post.date)}</span>"]
    if post.feature_badge:
        meta_bits.append(f"<span>{escape(post.feature_badge)}</span>")

    body = f"""    {render_header(site, prefix='../', current_section=None)}

    <main class="content-wrap article-wrap">
      <nav class="breadcrumbs" aria-label="breadcrumb">
        <a href="../index.html">홈</a>
        <span>/</span>
        <a href="../categories/{category.slug}.html">{escape(category.feed_label)}</a>
        <span>/</span>
        <span>{escape(post.breadcrumb_title)}</span>
      </nav>

      <header class="article-head-simple">
        <div class="feed-meta">
          {' '.join(meta_bits)}
        </div>
        <h1>{escape(post.title)}</h1>
        <p class="article-deck">{escape(post.deck)}</p>
      </header>

      <article class="article-body-simple">
{indent_html(post.body_html, 8)}
      </article>
    </main>

    {render_footer(site, prefix='../')}"""
    return render_page(site, head, body)


def build_rss(site: dict[str, object], posts: list[Post], categories: dict[str, Category]) -> str:
    base_url = str(site["base_url"])
    rss_posts = [post for post in posts if post.rss and post.listed]
    last_build = max((post.updated_at for post in rss_posts), default=datetime.now().date().isoformat())

    items = []
    for post in rss_posts:
        category = categories[post.category_slug]
        items.append(
            f"""    <item>
      <title>{escape(post.title)}</title>
      <link>{escape(absolute_url(base_url, f"/posts/{post.slug}.html"))}</link>
      <guid>{escape(absolute_url(base_url, f"/posts/{post.slug}.html"))}</guid>
      <pubDate>{escape(iso_to_rss(post.date))}</pubDate>
      <description>{escape(post.summary)}</description>
      <category>{escape(category.name)}</category>
    </item>"""
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{escape(str(site["site_title"]))}</title>
    <link>{escape(base_url.rstrip('/') + '/')}</link>
    <description>{escape(str(site["default_description"]))}</description>
    <language>ko-kr</language>
    <lastBuildDate>{escape(iso_to_rss(last_build))}</lastBuildDate>
    <atom:link href="{escape(absolute_url(base_url, '/rss.xml'))}" rel="self" type="application/rss+xml" xmlns:atom="http://www.w3.org/2005/Atom" />
{chr(10).join(items)}
  </channel>
</rss>
"""


def build_sitemap(site: dict[str, object], categories: list[Category], posts: list[Post]) -> str:
    base_url = str(site["base_url"])
    listed_posts = [post for post in posts if post.sitemap and post.listed]
    category_counts = defaultdict(int)
    for post in posts:
        if post.listed:
            category_counts[post.category_slug] += 1

    entries = [
        ("/", max((post.updated_at for post in listed_posts), default=datetime.now().date().isoformat()), "weekly", "1.0"),
        ("/archive.html", max((post.updated_at for post in listed_posts), default=datetime.now().date().isoformat()), "weekly", "0.8"),
        ("/categories/index.html", max((post.updated_at for post in listed_posts), default=datetime.now().date().isoformat()), "weekly", "0.7"),
    ]

    for category in categories:
        if category.coming_soon or category_counts[category.slug] == 0:
            continue
        latest = max(post.updated_at for post in listed_posts if post.category_slug == category.slug)
        entries.append((f"/categories/{category.slug}.html", latest, "weekly", "0.8"))

    for post in listed_posts:
        entries.append((f"/posts/{post.slug}.html", post.updated_at, "monthly", "0.9"))

    url_entries = [
        f"""  <url>
    <loc>{escape(absolute_url(base_url, path))}</loc>
    <lastmod>{escape(lastmod)}</lastmod>
    <changefreq>{escape(changefreq)}</changefreq>
    <priority>{escape(priority)}</priority>
  </url>"""
        for path, lastmod, changefreq, priority in entries
    ]

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(url_entries)}
</urlset>
"""


def main() -> None:
    site, categories, category_map = load_site_config()
    posts = load_posts(category_map)
    remove_managed_outputs()

    write_text(SITE_DIR / "index.html", build_home(site, posts, category_map))
    write_text(SITE_DIR / "archive.html", build_archive(site, posts, category_map))
    write_text(CATEGORY_OUTPUT_DIR / "index.html", build_category_index(site, categories, posts))

    listed_posts = [post for post in posts if post.listed]
    posts_by_category: dict[str, list[Post]] = defaultdict(list)
    for post in listed_posts:
        posts_by_category[post.category_slug].append(post)

    for category in categories:
        if category.coming_soon:
            continue
        write_text(
            CATEGORY_OUTPUT_DIR / f"{category.slug}.html",
            build_category_page(site, category, posts_by_category.get(category.slug, []), category_map),
        )

    for post in posts:
        if not post.published:
            continue
        write_text(POST_OUTPUT_DIR / f"{post.slug}.html", build_post_page(site, post, category_map[post.category_slug]))

    write_text(SITE_DIR / "rss.xml", build_rss(site, posts, category_map))
    write_text(SITE_DIR / "sitemap.xml", build_sitemap(site, categories, posts))
    write_text(SITE_DIR / "robots.txt", build_robots(site))


if __name__ == "__main__":
    main()
