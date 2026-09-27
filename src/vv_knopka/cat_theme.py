from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .manifest import build_manifest
from .settings import Settings, load_settings


_THEME_LIBRARY: tuple[dict[str, Any], ...] = (
    {
        "id": "cat_mischief",
        "keywords": (
            "trying to watch",
            "tv",
            "disrespect",
            "every single day",
            "won't stop",
            "wont stop",
            "interrupt",
            "annoy",
            "steal",
            "stole",
            "knock",
            "sabotage",
            "attack",
            "bite",
        ),
        "subreddits": ("catsareassholes",),
        "titles": {"en": "Zero Respect", "ru": "Ноль уважения"},
        "angles": {
            "en": "Cats confidently interrupting, blocking or overruling whatever the human was trying to do.",
            "ru": "Коты уверенно мешают, перекрывают и отменяют всё, что человек пытался спокойно сделать.",
        },
        "search_terms": (
            "cat interrupting owner",
            "cat blocking screen",
            "cat demanding attention",
            "cat knocking object",
            "cat stealing object",
            "cat meowing at owner",
            "cat bothering human",
            "cat playful mischief",
        ),
        "scene_prompts": {
            "en": ("blocks the human", "demands attention", "steals the moment", "knocks something over", "acts completely innocent", "argues back"),
            "ru": ("мешает человеку", "требует внимания", "крадёт момент", "что-то роняет", "делает невинный вид", "возмущённо отвечает"),
        },
    },
    {
        "id": "important_jobs",
        "keywords": (
            "assignment",
            "job",
            "hired",
            "work",
            "working",
            "cleaning lady",
            "supermodel",
            "employee",
            "manager",
            "helper",
            "delivery",
            "mission",
        ),
        "subreddits": ("catswithjobs",),
        "titles": {"en": "Important Cat Jobs", "ru": "Важные кошачьи дела"},
        "angles": {
            "en": "Cats treating ordinary household moments like extremely serious professional assignments.",
            "ru": "Коты воспринимают обычные домашние дела как крайне серьёзные профессиональные задания.",
        },
        "search_terms": (
            "cat helping human",
            "cat cleaning house",
            "cat carrying object",
            "cat sitting at desk",
            "cat interacting with human",
            "cat supervising owner",
            "cat working funny",
            "cat meowing at human",
        ),
        "scene_prompts": {
            "en": ("takes the assignment", "supervises the human", "inspects the work", "carries something important", "poses like a professional", "demands a promotion"),
            "ru": ("принимает задание", "контролирует человека", "проверяет работу", "несёт важный предмет", "позирует как профессионал", "требует повышение"),
        },
    },
    {
        "id": "weird_cat_logic",
        "keywords": (
            "nuts",
            "self-cleaning",
            "cleaning mode",
            "weird",
            "strange",
            "wrong",
            "bringing",
            "bring",
            "why does",
            "obsessed",
            "flip my cat",
        ),
        "subreddits": ("whatswrongwithyourcat",),
        "titles": {"en": "Cat Logic", "ru": "Кошачья логика"},
        "angles": {
            "en": "Tiny habits that make perfect sense to the cat and absolutely no sense to everyone else.",
            "ru": "Маленькие привычки, которые для кота совершенно логичны, а для всех остальных — вообще нет.",
        },
        "search_terms": (
            "cat weird behavior",
            "cat carrying object",
            "cat grooming funny",
            "cat curious reaction",
            "cat playing with household object",
            "cat strange habit",
            "cat investigating object",
            "cat meowing reaction",
        ),
        "scene_prompts": {
            "en": ("brings a strange object", "activates grooming mode", "investigates the impossible", "chooses the wrong object", "repeats a weird ritual", "looks proud of it"),
            "ru": ("приносит странный предмет", "включает режим умывания", "исследует невозможное", "выбирает не тот предмет", "повторяет странный ритуал", "очень собой доволен"),
        },
    },
    {
        "id": "orange_chaos",
        "keywords": ("orange", "braincell", "ginger"),
        "subreddits": ("oneorangebraincell",),
        "titles": {"en": "Orange Logic", "ru": "Рыжая логика"},
        "angles": {
            "en": "Orange cats confidently improvising solutions nobody asked for.",
            "ru": "Рыжие коты уверенно импровизируют решения, о которых их никто не просил.",
        },
        "search_terms": (
            "orange cat playing",
            "orange cat funny reaction",
            "orange cat jumping",
            "orange cat curious",
            "orange cat interacting with human",
            "orange cat meowing",
            "orange cat household",
            "orange cat chaos",
        ),
        "scene_prompts": {
            "en": ("chooses chaos", "tests gravity", "forgets the plan", "improvises anyway", "looks surprised", "walks away proudly"),
            "ru": ("выбирает хаос", "проверяет гравитацию", "забывает план", "всё равно импровизирует", "сам удивляется", "гордо уходит"),
        },
    },
    {
        "id": "cat_calculations",
        "keywords": ("hoop", "jump", "leap", "climb", "catch", "calculation", "calculated", "parkour"),
        "subreddits": ("catculations",),
        "titles": {"en": "Perfect Calculations", "ru": "Идеальный расчёт"},
        "angles": {
            "en": "Cats making suspiciously precise jumps, catches and tiny athletic calculations.",
            "ru": "Коты выполняют подозрительно точные прыжки, ловлю и маленькие спортивные расчёты.",
        },
        "search_terms": (
            "cat jumping",
            "cat climbing",
            "cat catching toy",
            "cat playing athletic",
            "cat jumping through hoop",
            "cat balancing",
            "cat chasing toy",
            "cat landing jump",
        ),
        "scene_prompts": {
            "en": ("measures the jump", "commits to the leap", "catches the target", "sticks the landing", "balances perfectly", "pretends it was easy"),
            "ru": ("оценивает прыжок", "решается на рывок", "ловит цель", "идеально приземляется", "держит баланс", "делает вид, что это легко"),
        },
    },
    {
        "id": "main_character_cats",
        "keywords": ("supermodel", "portrait", "potrait", "pose", "model", "dramatic", "stare", "beautiful"),
        "subreddits": (),
        "titles": {"en": "Main Character Cats", "ru": "Главные герои"},
        "angles": {
            "en": "Cats who somehow turn an ordinary room into their personal photo shoot or dramatic scene.",
            "ru": "Коты превращают обычную комнату в личную фотосессию или драматическую сцену.",
        },
        "search_terms": (
            "cat posing",
            "cat dramatic stare",
            "cat looking at camera",
            "cat portrait video",
            "cat sitting elegant",
            "cat funny expression",
            "cat walking toward camera",
            "cat meowing at camera",
        ),
        "scene_prompts": {
            "en": ("finds the camera", "holds the stare", "strikes a pose", "walks into frame", "adds unnecessary drama", "ends on the perfect look"),
            "ru": ("находит камеру", "держит взгляд", "принимает позу", "входит в кадр", "добавляет лишнюю драму", "заканчивает идеальным взглядом"),
        },
    },
)

_GENERIC_THEME: dict[str, Any] = {
    "id": "current_cat_chaos",
    "keywords": (),
    "subreddits": (),
    "titles": {"en": "Tiny Cat Chaos", "ru": "Маленький кото-хаос"},
    "angles": {
        "en": "A coherent collection of small current cat moments: reactions, play, interruptions and odd habits.",
        "ru": "Связная подборка маленьких актуальных кошачьих моментов: реакции, игры, помехи и странные привычки.",
    },
    "search_terms": (
        "cat funny reaction",
        "cat playing",
        "cat interacting with human",
        "cat curious",
        "cat meowing",
        "cat household funny",
        "cat carrying object",
        "cat jumping",
    ),
    "scene_prompts": {
        "en": ("reacts", "plays", "interrupts", "investigates", "meows", "creates tiny chaos"),
        "ru": ("реагирует", "играет", "мешает", "исследует", "мяукает", "устраивает маленький хаос"),
    },
}


def _norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().replace("’", "'").split())


def _theme_definition(theme_id: str) -> dict[str, Any]:
    for theme in _THEME_LIBRARY:
        if theme["id"] == theme_id:
            return theme
    if theme_id == _GENERIC_THEME["id"]:
        return _GENERIC_THEME
    raise ValueError(f"unknown cat theme: {theme_id}")


def rank_themes(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for theme in _THEME_LIBRARY:
        evidence: list[dict[str, Any]] = []
        subtotal = 0.0
        keyword_set = tuple(_norm(value) for value in theme.get("keywords", ()))
        subreddit_set = {_norm(value) for value in theme.get("subreddits", ())}
        for candidate in candidates:
            title = _norm(candidate.get("title"))
            subreddit = _norm(candidate.get("subreddit"))
            keyword_hits = [keyword for keyword in keyword_set if keyword and keyword in title]
            subreddit_match = subreddit in subreddit_set if subreddit_set else False
            if not keyword_hits and not subreddit_match:
                continue
            community_score = max(float(candidate.get("community_score") or 0.0), 0.0)
            weight = 1.0 + 0.55 * min(len(keyword_hits), 3) + (0.75 if subreddit_match else 0.0)
            contribution = community_score * weight
            subtotal += contribution
            evidence.append(
                {
                    "trend_rank": int(candidate.get("trend_rank") or 0),
                    "title": str(candidate.get("title") or ""),
                    "subreddit": str(candidate.get("subreddit") or ""),
                    "url": str(candidate.get("url") or ""),
                    "community_score": round(community_score, 6),
                    "keyword_hits": keyword_hits,
                    "subreddit_match": subreddit_match,
                    "contribution": round(contribution, 6),
                }
            )
        if not evidence:
            continue
        evidence.sort(key=lambda item: (-float(item["contribution"]), int(item.get("trend_rank") or 9999)))
        repeat_bonus = 1.0 + 0.12 * max(len(evidence) - 1, 0)
        score = subtotal * repeat_bonus
        ranked.append(
            {
                "theme_id": theme["id"],
                "score": round(score, 6),
                "evidence_count": len(evidence),
                "evidence": evidence[:6],
            }
        )
    ranked.sort(key=lambda item: (-float(item["score"]), -int(item["evidence_count"]), str(item["theme_id"])))
    return ranked


def _theme_signature(theme_id: str, search_terms: list[str]) -> str:
    payload = json.dumps(
        {"theme_id": theme_id, "search_terms": search_terms},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_theme_payload(
    report: dict[str, Any],
    *,
    slot: int,
    language: str,
    selected_theme_id: str | None = None,
) -> dict[str, Any]:
    language = "ru" if str(language).lower() == "ru" else "en"
    candidates = [dict(item) for item in report.get("candidates", []) if isinstance(item, dict)]
    if not candidates:
        raise ValueError("community trend report has no candidates")

    ranked = rank_themes(candidates)
    if selected_theme_id:
        selected_def = _theme_definition(selected_theme_id)
        selected_rank = next((item for item in ranked if item["theme_id"] == selected_theme_id), None)
        if selected_rank is None:
            selected_rank = {
                "theme_id": selected_theme_id,
                "score": 0.0,
                "evidence_count": 0,
                "evidence": [],
            }
    elif ranked:
        selected_rank = ranked[0]
        selected_def = _theme_definition(str(selected_rank["theme_id"]))
    else:
        selected_rank = {
            "theme_id": _GENERIC_THEME["id"],
            "score": 0.0,
            "evidence_count": min(len(candidates), 6),
            "evidence": [
                {
                    "trend_rank": int(item.get("trend_rank") or 0),
                    "title": str(item.get("title") or ""),
                    "subreddit": str(item.get("subreddit") or ""),
                    "url": str(item.get("url") or ""),
                    "community_score": round(float(item.get("community_score") or 0.0), 6),
                    "keyword_hits": [],
                    "subreddit_match": False,
                    "contribution": round(float(item.get("community_score") or 0.0), 6),
                }
                for item in candidates[:6]
            ],
        }
        selected_def = _GENERIC_THEME

    search_terms = list(dict.fromkeys(str(value).strip() for value in selected_def["search_terms"] if str(value).strip()))
    theme_id = str(selected_def["id"])
    signature = _theme_signature(theme_id, search_terms)
    return {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "slot": int(slot),
        "language": language,
        "source": "reddit_community_trend_theme",
        "source_report_discovered_at": report.get("discovered_at"),
        "source_candidate_count": len(candidates),
        "theme_id": theme_id,
        "theme_signature": signature,
        "episode_title": selected_def["titles"][language],
        "editorial_angle": selected_def["angles"][language],
        "search_terms": search_terms,
        "scene_prompts": list(selected_def["scene_prompts"][language]),
        "selected_theme": selected_rank,
        "ranked_themes": ranked[:6],
        "rights_policy": {
            "reddit_references_only": True,
            "reddit_media_auto_import": False,
            "usable_footage_must_pass_existing_license_and_audio_gates": True,
        },
    }


def build_theme_only_plan(theme_payload: dict[str, Any]) -> dict[str, Any]:
    language = "ru" if str(theme_payload.get("language") or "").lower() == "ru" else "en"
    title = str(theme_payload.get("episode_title") or ("Кошачья тема" if language == "ru" else "Cat Theme"))
    angle = str(theme_payload.get("editorial_angle") or "")
    scene_prompts = [str(value) for value in theme_payload.get("scene_prompts", []) if str(value).strip()]
    return {
        "title": title,
        "hook": angle,
        "script": "; ".join(scene_prompts),
        "visual_anchor": "cat",
        "search_terms": list(theme_payload.get("search_terms") or []),
        "caption": title,
        "hashtags": ["#cats", "#funnycats", "#catshorts"],
        "editorial_value": "Community-informed thematic curation with licensed footage and original edit structure.",
        "fact_check_items": [],
        "ai_disclosure_recommended": False,
    }


def apply_theme_to_plan(plan: dict[str, Any], theme_payload: dict[str, Any]) -> dict[str, Any]:
    effective = dict(plan or build_theme_only_plan(theme_payload))
    language = "ru" if str(theme_payload.get("language") or "").lower() == "ru" else "en"
    effective["title"] = str(theme_payload.get("episode_title") or effective.get("title") or "Cat Theme")
    effective["hook"] = str(theme_payload.get("editorial_angle") or effective.get("hook") or "")
    effective["visual_anchor"] = "cat"
    effective["search_terms"] = list(theme_payload.get("search_terms") or effective.get("search_terms") or [])
    scene_prompts = [str(value) for value in theme_payload.get("scene_prompts", []) if str(value).strip()]
    if scene_prompts:
        effective["script"] = "; ".join(scene_prompts)
    effective["caption"] = effective["title"]
    effective.setdefault("hashtags", ["#cats", "#funnycats", "#catshorts"])
    effective.setdefault("fact_check_items", [])
    effective["ai_disclosure_recommended"] = bool(effective.get("ai_disclosure_recommended", False))
    effective["editorial_value"] = (
        "Community-informed thematic curation; Reddit supplied trend references only, while final footage must pass "
        "the project's existing license, provenance, visual and audible-source gates."
    )
    effective["trend_theme"] = {
        "theme_id": theme_payload.get("theme_id"),
        "theme_signature": theme_payload.get("theme_signature"),
        "source": theme_payload.get("source"),
        "selected_theme": theme_payload.get("selected_theme"),
        "scene_prompts": scene_prompts,
        "language": language,
    }
    return effective


def prepare_theme_source_refresh(source_manifest: Path, slot_dir: Path, theme_payload: dict[str, Any]) -> bool:
    """Invalidate active stock when a newly selected trend theme differs from the cached source theme.

    Existing runtime media files are never deleted. The active source manifest and old generic material audit are
    archived so a themed render cannot silently reuse unrelated stock.
    """
    current_id = str(theme_payload.get("theme_id") or "").strip()
    current_signature = str(theme_payload.get("theme_signature") or "").strip()
    if not current_id or not current_signature:
        return False

    existing: dict[str, Any] = {}
    if source_manifest.exists():
        try:
            existing = json.loads(source_manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
    if (
        str(existing.get("trend_theme_id") or "") == current_id
        and str(existing.get("trend_theme_signature") or "") == current_signature
    ):
        return False

    if source_manifest.exists() and source_manifest.stat().st_size > 0:
        archive_hash = hashlib.sha256(source_manifest.read_bytes()).hexdigest()[:10]
        archive = slot_dir / f"sources-before-theme-{archive_hash}.json"
        if not archive.exists():
            shutil.copy2(source_manifest, archive)

    old_audit = slot_dir / "ai_materials.json"
    if old_audit.exists() and old_audit.stat().st_size > 0:
        audit_hash = hashlib.sha256(old_audit.read_bytes()).hexdigest()[:10]
        archive = slot_dir / f"ai_materials-before-theme-{audit_hash}.json"
        if not archive.exists():
            shutil.copy2(old_audit, archive)
        old_audit.unlink()

    source_manifest.parent.mkdir(parents=True, exist_ok=True)
    source_manifest.write_text(
        json.dumps(
            {
                "source_policy": "trend-theme refresh pending; usable clips must be reacquired through source gates",
                "trend_theme_id": current_id,
                "trend_theme_signature": current_signature,
                "clips": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return True


def stamp_source_manifest_theme(source_manifest: Path, theme_payload: dict[str, Any]) -> None:
    if not source_manifest.exists():
        return
    try:
        payload = json.loads(source_manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    payload["trend_theme_id"] = theme_payload.get("theme_id")
    payload["trend_theme_signature"] = theme_payload.get("theme_signature")
    payload["trend_theme_search_terms"] = list(theme_payload.get("search_terms") or [])
    source_manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _slot_language(settings: Settings, slot_number: int) -> str:
    for slot in build_manifest(settings):
        if int(slot.slot) == int(slot_number):
            if slot.pipeline != "animal_compilation":
                raise ValueError(f"slot {slot_number} is not an animal_compilation slot")
            return str(slot.language)
    raise ValueError(f"slot must be 1..{len(build_manifest(settings))}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="vv-cat-theme")
    parser.add_argument("slot", type=int)
    parser.add_argument("--config", default="config/pilot.toml")
    parser.add_argument("--report", default="runtime/trends/reddit-cat-trends.json")
    parser.add_argument("--theme", default=None, help="Optional explicit theme id instead of automatic ranking")
    args = parser.parse_args()

    settings = load_settings(args.config)
    language = _slot_language(settings, args.slot)
    report_path = Path(args.report).resolve()
    if not report_path.exists():
        raise SystemExit(f"missing {report_path}; run `vv-cat-community --days 30 --limit 30` first")
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        payload = build_theme_payload(
            report,
            slot=args.slot,
            language=language,
            selected_theme_id=args.theme,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    slot_dir = settings.runtime_dir / "slots" / f"{int(args.slot):02d}"
    slot_dir.mkdir(parents=True, exist_ok=True)
    output = slot_dir / "trend-theme.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    selected = payload["selected_theme"]
    print(f"Trend-to-theme slot {args.slot} ({language})")
    print(f"Selected theme: {payload['theme_id']} | score {float(selected.get('score') or 0.0):.3f}")
    print(f"Episode title: {payload['episode_title']}")
    print(f"Theme file: {output}")
    if selected.get("evidence"):
        print("Evidence:")
        for item in selected["evidence"][:5]:
            print(
                f"- r/{item['subreddit']} | score {float(item['community_score']):.3f} | "
                f"{item['title']}"
            )
    print("Licensed-footage search terms:")
    for term in payload["search_terms"]:
        print(f"- {term}")
    print("Next: run `vv render-animal %d`. A changed theme forces fresh stock search; Reddit media itself is not imported." % args.slot)


if __name__ == "__main__":
    main()
