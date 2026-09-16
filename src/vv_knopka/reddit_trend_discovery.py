from __future__ import annotations

import argparse
import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .settings import load_settings


ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
DEFAULT_SUBREDDITS = (
    "cats",
    "WhatsWrongWithYourCat",
    "OneOrangeBraincell",
    "CatsAreAssholes",
    "Catculations",
    "Catswithjobs",
)


def _parse_datetime(value: str) -> datetime | None:
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _extract_links(content_html: str) -> list[str]:
    decoded = html.unescape(str(content_html or ""))
    links = re.findall(r'href=["\']([^"\']+)["\']', decoded, flags=re.IGNORECASE)
    deduped: list[str] = []
    seen: set[str] = set()
    for link in links:
        clean = html.unescape(link).strip()
        if not clean.startswith(("http://", "https://")) or clean in seen:
            continue
        seen.add(clean)
        deduped.append(clean)
    return deduped


def _media_hint(links: list[str]) -> tuple[str, list[str]]:
    media: list[str] = []
    hint = "unknown"
    for link in links:
        lower = link.casefold()
        if "v.redd.it" in lower or lower.endswith((".mp4", ".webm")):
            hint = "video"
            media.append(link)
        elif "youtube.com" in lower or "youtu.be" in lower:
            if hint == "unknown":
                hint = "youtube"
            media.append(link)
        elif "imgur.com" in lower or "i.redd.it" in lower or lower.endswith((".gif", ".gifv")):
            if hint == "unknown":
                hint = "visual"
            media.append(link)
    return hint, media[:5]


def _parse_atom_feed(
    xml_text: str,
    *,
    subreddit: str,
    feed_kind: str,
    now: datetime,
    max_age_days: int,
) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    results: list[dict[str, Any]] = []
    cutoff_seconds = max(int(max_age_days), 1) * 86400
    for rank, entry in enumerate(root.findall("atom:entry", ATOM_NS), 1):
        title = str(entry.findtext("atom:title", default="", namespaces=ATOM_NS) or "").strip()
        updated_raw = str(entry.findtext("atom:updated", default="", namespaces=ATOM_NS) or "").strip()
        published = _parse_datetime(updated_raw)
        if published is None:
            continue
        age_seconds = max((now - published).total_seconds(), 0.0)
        if age_seconds > cutoff_seconds:
            continue

        permalink = ""
        for link_node in entry.findall("atom:link", ATOM_NS):
            href = str(link_node.attrib.get("href") or "").strip()
            if href.startswith(("http://", "https://")):
                permalink = href
                break
        if not permalink:
            continue

        author = str(entry.findtext("atom:author/atom:name", default="", namespaces=ATOM_NS) or "").strip()
        content_node = entry.find("atom:content", ATOM_NS)
        content_html = content_node.text if content_node is not None and content_node.text else ""
        links = _extract_links(content_html)
        hint, media_links = _media_hint(links)
        age_days = max(age_seconds / 86400.0, 0.05)
        feed_weight = 1.0 if feed_kind == "top_week" else 0.7
        rank_signal = feed_weight / (rank ** 0.72)
        recency_signal = 1.0 / (1.0 + age_days / 7.0)

        results.append(
            {
                "provider": "reddit",
                "url": permalink,
                "title": title,
                "creator": author,
                "subreddit": subreddit,
                "published_at": published.isoformat(),
                "age_days": round(age_days, 2),
                "feed_kind": feed_kind,
                "feed_rank": rank,
                "community_signal": round(rank_signal * recency_signal, 6),
                "media_hint": hint,
                "media_links": media_links,
                "rights_status": "author_permission_required",
                "attribution_required": False,
                "import_status": "trend_reference_only_until_author_permission",
                "auto_download": False,
                "discovery_backend": "reddit_public_rss",
            }
        )
    return results


def _feed_urls(subreddit: str, feed_kind: str) -> list[str]:
    if feed_kind == "top_week":
        suffix = f"/r/{subreddit}/top/.rss?sort=top&t=week"
    elif feed_kind == "hot":
        suffix = f"/r/{subreddit}/hot/.rss"
    else:
        raise ValueError(f"unsupported Reddit feed kind: {feed_kind}")
    return [f"https://www.reddit.com{suffix}", f"https://old.reddit.com{suffix}"]


def _fetch_feed(client: httpx.Client, subreddit: str, feed_kind: str) -> tuple[str | None, str | None]:
    errors: list[str] = []
    for url in _feed_urls(subreddit, feed_kind):
        try:
            response = client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            errors.append(f"{url}: {type(exc).__name__}")
            continue
        body = response.text.strip()
        if body:
            return body, None
        errors.append(f"{url}: empty body")
    return None, "; ".join(errors) or "feed unavailable"


def discover_reddit_cat_trends(
    *,
    subreddits: tuple[str, ...] = DEFAULT_SUBREDDITS,
    days: int = 30,
    limit: int = 30,
    now: datetime | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    diagnostics: list[str] = []
    raw_items: list[dict[str, Any]] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; VV-knopka/0.1; public RSS trend discovery)",
        "Accept": "application/atom+xml,application/rss+xml,application/xml,text/xml;q=0.9,*/*;q=0.5",
    }
    with httpx.Client(timeout=20, follow_redirects=True, headers=headers) as client:
        for subreddit in subreddits:
            for feed_kind in ("top_week", "hot"):
                xml_text, error = _fetch_feed(client, subreddit, feed_kind)
                if xml_text is None:
                    diagnostics.append(f"r/{subreddit} {feed_kind}: {error}")
                    continue
                try:
                    raw_items.extend(
                        _parse_atom_feed(
                            xml_text,
                            subreddit=subreddit,
                            feed_kind=feed_kind,
                            now=current,
                            max_age_days=days,
                        )
                    )
                except ET.ParseError as exc:
                    diagnostics.append(f"r/{subreddit} {feed_kind}: invalid XML ({exc})")

    merged: dict[str, dict[str, Any]] = {}
    for item in raw_items:
        key = str(item.get("url") or "").strip()
        if not key:
            continue
        if key not in merged:
            copy = dict(item)
            copy["feed_hits"] = 1
            copy["community_score"] = float(item.get("community_signal") or 0.0)
            copy["signals"] = [
                {
                    "subreddit": item.get("subreddit"),
                    "feed_kind": item.get("feed_kind"),
                    "feed_rank": item.get("feed_rank"),
                }
            ]
            merged[key] = copy
            continue
        existing = merged[key]
        existing["feed_hits"] = int(existing.get("feed_hits") or 1) + 1
        existing["community_score"] = round(
            float(existing.get("community_score") or 0.0)
            + float(item.get("community_signal") or 0.0),
            6,
        )
        existing.setdefault("signals", []).append(
            {
                "subreddit": item.get("subreddit"),
                "feed_kind": item.get("feed_kind"),
                "feed_rank": item.get("feed_rank"),
            }
        )
        if existing.get("media_hint") == "unknown" and item.get("media_hint") != "unknown":
            existing["media_hint"] = item.get("media_hint")
            existing["media_links"] = item.get("media_links") or []

    candidates = list(merged.values())
    candidates.sort(
        key=lambda item: (
            -float(item.get("community_score") or 0.0),
            -int(item.get("feed_hits") or 0),
            float(item.get("age_days") or 9999),
        )
    )
    ranked = candidates[: max(int(limit), 1)]
    for rank, item in enumerate(ranked, 1):
        item["trend_rank"] = rank
        item["community_score"] = round(float(item.get("community_score") or 0.0), 6)
    return ranked, diagnostics


def write_reddit_report(
    output: Path,
    *,
    subreddits: tuple[str, ...],
    days: int,
    candidates: list[dict[str, Any]],
    diagnostics: list[str],
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "source": "reddit_cat_community_trends",
        "backend": "reddit_public_rss",
        "subreddits": list(subreddits),
        "lookback_days": int(days),
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(candidates),
        "policy": {
            "purpose": "trend/reference discovery only",
            "auto_download": False,
            "human_review_required": True,
            "rights_default": "author_permission_required",
            "note": (
                "Reddit RSS rank is used as a community-interest signal. A public Reddit post does not grant "
                "permission to reuse its media; candidates remain reference-only until rights are obtained."
            ),
        },
        "diagnostics": diagnostics,
        "candidates": candidates,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(prog="vv-cat-community")
    parser.add_argument("--config", default="config/pilot.toml")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument(
        "--subreddits",
        default=",".join(DEFAULT_SUBREDDITS),
        help="Comma-separated subreddit names",
    )
    args = parser.parse_args()

    settings = load_settings(args.config)
    subreddits = tuple(part.strip() for part in args.subreddits.split(",") if part.strip())
    if not subreddits:
        raise SystemExit("At least one subreddit is required")

    print("Community backend: Reddit public RSS (no API key, no account login)")
    candidates, diagnostics = discover_reddit_cat_trends(
        subreddits=subreddits,
        days=max(args.days, 1),
        limit=max(args.limit, 1),
    )
    output = settings.runtime_dir / "trends" / "reddit-cat-trends.json"
    write_reddit_report(
        output,
        subreddits=subreddits,
        days=max(args.days, 1),
        candidates=candidates,
        diagnostics=diagnostics,
    )
    print(f"Reddit cat community candidates: {len(candidates)}")
    print(output)
    if diagnostics:
        print(f"Feed warnings: {len(diagnostics)} (saved in report)")
    if candidates:
        print("Top community references:")
        for candidate in candidates[:10]:
            print(
                f"[{int(candidate['trend_rank']):02d}] [permission?] "
                f"score {float(candidate['community_score']):.3f} | "
                f"r/{candidate['subreddit']} | {candidate['age_days']:.1f}d | "
                f"{candidate['title']} | {candidate['url']}"
            )
        print(
            "These are trend references, not licensed media. Use them to identify current cat themes/scenes; "
            "do not import the media without creator permission or another verified license."
        )


if __name__ == "__main__":
    main()
