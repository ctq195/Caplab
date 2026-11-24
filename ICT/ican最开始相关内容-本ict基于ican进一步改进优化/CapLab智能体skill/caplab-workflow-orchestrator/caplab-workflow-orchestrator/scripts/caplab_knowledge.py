#!/usr/bin/env python3
"""Local, privacy-bounded knowledge maintenance for CapLab."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


REVIEW_STATUSES = {"machine_validated", "pending_human_review", "human_approved", "conflicting", "stale", "rejected"}
USABLE_STATUSES = {"machine_validated", "human_approved"}
CARD_TYPES = {"person_case": "people", "occupation": "occupations", "pathway": "pathways"}
POOLS = {"famous", "alumni", "ordinary_public", "setback_or_transition", "cross_major_bridge"}
MODES = {"background_similar", "goal_oriented", "direction_discovery"}
REQUEST_PURPOSES = {"direction_discovery", "path_validation"}
GRADE_STAGES = {"year_1", "year_2", "year_3", "other"}
CLAIM_TYPES = {"fact", "reported_practice", "transferable_hypothesis", "model_interpretation"}
PRIVATE_KEYS = {
    "raw_conversation", "full_profile", "health", "medical", "family", "finance", "financial_detail",
    "dialogic_self_understanding", "psychological_context", "psychological_observations", "psychological_hypotheses", "emotional_state", "support_preferences", "personal_facts",
    "contact", "phone", "email", "address", "identity_card", "identity_card_number", "bank_card",
    "bank_card_number", "user_name", "user_id", "private_note", "personal_story"
}
SOURCE_REQUIRED = {
    "source_id", "url", "title", "publisher", "source_type", "published_at", "checked_at",
    "location_scope", "applicable_period", "dynamic_type", "valid_until", "review_status",
    "snapshot_path", "notes"
}
CARD_REQUIRED = {
    "id", "card_type", "title", "created_at", "updated_at", "major_tags", "region_tags", "time_tags",
    "major_event_tags", "claims", "source_ids", "review_status", "supports", "cannot_prove"
}
ID_PATTERNS = {
    "source": re.compile(r"^KSRC-[0-9]{6}$"),
    "person_case": re.compile(r"^KPER-[0-9]{6}$"),
    "occupation": re.compile(r"^KOCC-[0-9]{6}$"),
    "pathway": re.compile(r"^KPATH-[0-9]{6}$"),
    "request": re.compile(r"^KREQ-[0-9]{6}$"),
    "snapshot": re.compile(r"^KSNP-[0-9]{6}$"),
}


class KnowledgeError(Exception):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def today() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise KnowledgeError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise KnowledgeError(f"invalid JSON {path}: {exc}") from exc


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def knowledge_root(workspace: Path) -> Path:
    return workspace.resolve() / "knowledge"


def iter_objects(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_objects(child)


def private_key_errors(value: Any, path: str = "$") -> list[str]:
    errors = []
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = key.lower()
            if lowered in PRIVATE_KEYS or lowered.startswith("private_"):
                errors.append(f"private field forbidden at {path}.{key}")
            errors.extend(private_key_errors(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(private_key_errors(child, f"{path}[{index}]"))
    return errors


def parse_date(value: Any, label: str, allow_null: bool = False) -> list[str]:
    if value is None and allow_null:
        return []
    if not isinstance(value, str):
        return [f"{label} must be an ISO date or datetime string"]
    try:
        dt.date.fromisoformat(value[:10])
        return []
    except ValueError:
        return [f"{label} is not a valid ISO date: {value!r}"]


def validate_request(data: Any) -> list[str]:
    errors = private_key_errors(data)
    if not isinstance(data, dict):
        return errors + ["knowledge request must be an object"]
    required = {
        "request_id", "major", "candidate_path_ids",
        "region", "time_window", "retrieval_modes", "evidence_gaps"
    }
    errors.extend(f"missing request field {key}" for key in sorted(required - set(data)))
    if not ID_PATTERNS["request"].match(str(data.get("request_id", ""))):
        errors.append("request_id must match KREQ-000001")
    major = data.get("major")
    if not isinstance(major, dict) or not major.get("name") or major.get("status") != "confirmed":
        errors.append("major must contain a name and status=confirmed")
    if not isinstance(data.get("candidate_path_ids"), list) or any(not re.match(r"^PTH-[0-9]{6}$", str(x)) for x in data.get("candidate_path_ids", [])):
        errors.append("candidate_path_ids must contain only PTH-* IDs")
    requested_modes = data.get("retrieval_modes")
    extended = any(key in data for key in ("request_purpose", "grade_stage")) or (isinstance(requested_modes, list) and "direction_discovery" in requested_modes)
    purpose = data.get("request_purpose", "path_validation")
    if extended:
        errors.extend(f"missing request field {key}" for key in ("request_purpose", "grade_stage") if key not in data)
    if purpose not in REQUEST_PURPOSES:
        errors.append("request_purpose must be direction_discovery or path_validation")
    if extended and purpose == "path_validation" and not data.get("candidate_path_ids"):
        errors.append("path_validation requires at least one candidate_path_id")
    if data.get("grade_stage", "other") not in GRADE_STAGES:
        errors.append("grade_stage must be year_1, year_2, year_3, or other")
    modes = data.get("retrieval_modes")
    if not isinstance(modes, list) or not modes or set(modes) - MODES:
        errors.append("retrieval_modes contains an unsupported mode")
    if purpose == "direction_discovery" and isinstance(modes, list) and "direction_discovery" not in modes:
        errors.append("direction_discovery purpose requires direction_discovery mode")
    if not isinstance(data.get("evidence_gaps"), list):
        errors.append("evidence_gaps must be an array")
    return errors


def normalized_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)))
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), query, ""))


def normalize_text(value: str) -> str:
    return re.sub(r"\W+", "", value, flags=re.UNICODE).lower()


def card_fingerprint(card: dict[str, Any]) -> str:
    material = "|".join([
        card.get("card_type", ""), normalize_text(str(card.get("title", ""))),
        ",".join(sorted(normalize_text(str(x)) for x in card.get("major_tags", []))),
        normalize_text(str(card.get("pool", ""))),
    ])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def validate_source(data: Any, label: str = "source") -> list[str]:
    errors = private_key_errors(data, label)
    if not isinstance(data, dict):
        return errors + [f"{label} must be an object"]
    errors.extend(f"{label}: missing {key}" for key in sorted(SOURCE_REQUIRED - set(data)))
    if not ID_PATTERNS["source"].match(str(data.get("source_id", ""))):
        errors.append(f"{label}: source_id must match KSRC-000001")
    url = data.get("url")
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        errors.append(f"{label}: URL must be http(s)")
    if data.get("review_status") not in REVIEW_STATUSES:
        errors.append(f"{label}: invalid review_status")
    if data.get("dynamic_type") not in {"job_or_salary", "use_time", "curriculum", "historical_person", "static"}:
        errors.append(f"{label}: invalid dynamic_type")
    errors.extend(parse_date(data.get("checked_at"), f"{label}.checked_at"))
    errors.extend(parse_date(data.get("published_at"), f"{label}.published_at", allow_null=True))
    if data.get("dynamic_type") != "static":
        errors.extend(parse_date(data.get("valid_until"), f"{label}.valid_until"))
    return errors


def validate_card(data: Any, source_ids: set[str], label: str = "card") -> list[str]:
    errors = private_key_errors(data, label)
    if not isinstance(data, dict):
        return errors + [f"{label} must be an object"]
    errors.extend(f"{label}: missing {key}" for key in sorted(CARD_REQUIRED - set(data)))
    card_type = data.get("card_type")
    if card_type not in CARD_TYPES:
        errors.append(f"{label}: invalid card_type")
    elif not ID_PATTERNS[card_type].match(str(data.get("id", ""))):
        errors.append(f"{label}: invalid id for {card_type}")
    if data.get("review_status") not in REVIEW_STATUSES:
        errors.append(f"{label}: invalid review_status")
    if card_type == "person_case" and data.get("pool") not in POOLS:
        errors.append(f"{label}: invalid person pool")
    linked = data.get("source_ids")
    if not isinstance(linked, list) or not linked:
        errors.append(f"{label}: source_ids must be a non-empty array")
        linked = []
    unknown = sorted(set(linked) - source_ids)
    if unknown:
        errors.append(f"{label}: unknown source_ids {unknown}")
    if not isinstance(data.get("supports"), list) or not isinstance(data.get("cannot_prove"), list) or not data.get("cannot_prove"):
        errors.append(f"{label}: supports and a non-empty cannot_prove list are required")
    for index, claim in enumerate(data.get("claims", [])):
        if not isinstance(claim, dict):
            errors.append(f"{label}: claim {index} must be an object")
            continue
        if not claim.get("statement") or not claim.get("source_ids") or claim.get("status") not in REVIEW_STATUSES or claim.get("claim_type") not in CLAIM_TYPES:
            errors.append(f"{label}: claim {index} missing or invalid statement/source_ids/status/claim_type")
        bad = sorted(set(claim.get("source_ids", [])) - source_ids)
        if bad:
            errors.append(f"{label}: claim {index} unknown source_ids {bad}")
    if card_type == "occupation" and data.get("valid_until") is not None:
        errors.extend(parse_date(data.get("valid_until"), f"{label}.valid_until"))
    return errors


def all_sources(root: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    result = {}
    for path in sorted((root / "sources").glob("*.json")):
        data = read_json(path)
        result[data.get("source_id")] = (path, data)
    return result


def all_cards(root: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    result = {}
    for path in sorted((root / "cards").glob("**/*.json")):
        data = read_json(path)
        result[data.get("id")] = (path, data)
    return result


def next_id(root: Path, kind: str) -> str:
    pattern = ID_PATTERNS[kind]
    prefix = {"snapshot": "KSNP", "request": "KREQ"}[kind]
    maximum = 0
    for path in root.glob("**/*.json"):
        match = pattern.match(path.stem)
        if match:
            maximum = max(maximum, int(path.stem.rsplit("-", 1)[1]))
    return f"{prefix}-{maximum + 1:06d}"


def queue_item(root: Path, reason: str, incoming: dict[str, Any], existing_id: str | None = None) -> Path:
    digest = hashlib.sha256(json.dumps(incoming, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    path = root / "review_queue" / f"queue-{utc_now()[:10]}-{digest}.json"
    atomic_json(path, {
        "queue_id": f"KQ-{digest}", "reason": reason, "incoming": incoming,
        "existing_id": existing_id, "created_at": utc_now(), "status": "open"
    })
    return path


def command_init(args: argparse.Namespace) -> None:
    if not getattr(args, "empty_for_test", False):
        from caplab_bootstrap import ensure_knowledge
        print(json.dumps(ensure_knowledge(args.root, getattr(args, "seed", None), getattr(args, "allow_temporary", False)), ensure_ascii=False))
        return
    root = knowledge_root(Path(args.root))
    for relative in ("sources", "cards/people", "cards/occupations", "cards/pathways", "snapshots", "review_queue", "audit"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    config = root / "config.json"
    if not config.exists():
        atomic_json(config, {
            "schema_version": "1.0.0", "created_by": "caplab-knowledge-maintainer",
            "contains_personal_user_data": False, "local_only": True,
            "review_statuses": sorted(REVIEW_STATUSES),
            "freshness_days": {"job_or_salary": 14, "use_time": 0, "curriculum": 365, "historical_person": 180}
        })
    print(f"INITIALIZED {root}")


def initialize_empty_for_test(args: argparse.Namespace) -> None:
    args = argparse.Namespace(**vars(args), empty_for_test=True)
    command_init(args)


def manifest_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def command_seed(args: argparse.Namespace) -> None:
    workspace = Path(args.root).resolve()
    target = knowledge_root(workspace)
    seed = Path(args.seed).resolve()
    manifest_path = seed / "seed-manifest.json"
    if not seed.is_dir() or not manifest_path.is_file():
        raise KnowledgeError("seed must contain seed-manifest.json")
    existing_files = [path for path in target.rglob("*") if path.is_file()] if target.exists() else []
    if existing_files:
        raise KnowledgeError("workspace knowledge is not empty; refusing to overwrite")
    from caplab_bootstrap import ensure_knowledge
    print(json.dumps(ensure_knowledge(workspace, seed, allow_temporary=True), ensure_ascii=False, indent=2))


def command_validate_request(args: argparse.Namespace) -> None:
    errors = validate_request(read_json(Path(args.request)))
    if errors:
        raise KnowledgeError("\n- ".join(errors))
    print(f"VALID_REQUEST {args.request}")


def command_validate(args: argparse.Namespace) -> None:
    root = knowledge_root(Path(args.root))
    config = read_json(root / "config.json")
    errors = private_key_errors(config, "config")
    if config.get("contains_personal_user_data") is not False:
        errors.append("config.contains_personal_user_data must be false")
    sources: dict[str, Path] = {}
    normalized_urls: dict[str, str] = {}
    for path in sorted((root / "sources").glob("*.json")):
        data = read_json(path)
        errors.extend(validate_source(data, str(path)))
        identifier = data.get("source_id")
        if identifier in sources:
            errors.append(f"duplicate source_id {identifier}: {sources[identifier]} and {path}")
        sources[identifier] = path
        url = normalized_url(str(data.get("url", "")))
        if url in normalized_urls:
            errors.append(f"duplicate normalized URL in {normalized_urls[url]} and {path}")
        normalized_urls[url] = str(path)
    cards: dict[str, Path] = {}
    fingerprints: dict[str, str] = {}
    for path in sorted((root / "cards").glob("**/*.json")):
        data = read_json(path)
        errors.extend(validate_card(data, set(sources), str(path)))
        identifier = data.get("id")
        if identifier in cards:
            errors.append(f"duplicate card id {identifier}: {cards[identifier]} and {path}")
        cards[identifier] = path
        fingerprint = card_fingerprint(data)
        if fingerprint in fingerprints:
            errors.append(f"duplicate card fingerprint in {fingerprints[fingerprint]} and {path}")
        fingerprints[fingerprint] = str(path)
    if errors:
        raise KnowledgeError("knowledge validation failed:\n- " + "\n- ".join(errors))
    print(f"VALID sources={len(sources)} cards={len(cards)}")


def command_add(args: argparse.Namespace) -> None:
    root = knowledge_root(Path(args.root))
    incoming = read_json(Path(args.file))
    sources = all_sources(root)
    cards = all_cards(root)
    if "source_id" in incoming and "card_type" not in incoming:
        errors = validate_source(incoming)
        if errors:
            raise KnowledgeError("invalid source:\n- " + "\n- ".join(errors))
        normalized = normalized_url(incoming["url"])
        for identifier, (_, existing) in sources.items():
            if normalized_url(existing["url"]) == normalized:
                queued = queue_item(root, "duplicate_source_url", incoming, identifier)
                print(f"QUEUED duplicate={identifier} at={queued}")
                return
        target = root / "sources" / f"{incoming['source_id']}.json"
    else:
        errors = validate_card(incoming, set(sources))
        if errors:
            raise KnowledgeError("invalid card:\n- " + "\n- ".join(errors))
        fingerprint = card_fingerprint(incoming)
        for identifier, (_, existing) in cards.items():
            if card_fingerprint(existing) == fingerprint:
                queued = queue_item(root, "duplicate_card_fingerprint", incoming, identifier)
                print(f"QUEUED duplicate={identifier} at={queued}")
                return
        target = root / "cards" / CARD_TYPES[incoming["card_type"]] / f"{incoming['id']}.json"
    if target.exists():
        queued = queue_item(root, "duplicate_id", incoming, target.stem)
        print(f"QUEUED duplicate={target.stem} at={queued}")
        return
    atomic_json(target, incoming)
    print(f"ADDED {target}")


def is_stale(record: dict[str, Any], as_of: dt.date) -> bool:
    if record.get("review_status") in {"stale", "rejected"}:
        return True
    valid_until = record.get("valid_until")
    if valid_until:
        try:
            return dt.date.fromisoformat(str(valid_until)[:10]) < as_of
        except ValueError:
            return True
    return record.get("dynamic_type") == "use_time"


def command_freshness(args: argparse.Namespace) -> None:
    root = knowledge_root(Path(args.root))
    as_of = dt.date.fromisoformat(args.as_of) if args.as_of else today()
    stale = []
    stale_source_ids = set()
    paths = list((root / "sources").glob("*.json")) + list((root / "cards" / "occupations").glob("*.json"))
    for path in sorted(paths):
        record = read_json(path)
        if is_stale(record, as_of):
            identifier = record.get("source_id") or record.get("id")
            stale.append(identifier)
            if record.get("source_id"):
                stale_source_ids.add(record["source_id"])
            if args.mark and record.get("review_status") != "rejected":
                record["review_status"] = "stale"
                record["updated_at"] = utc_now()
                atomic_json(path, record)
    if args.mark and stale_source_ids:
        for path in sorted((root / "cards").glob("**/*.json")):
            card = read_json(path)
            if stale_source_ids.intersection(card.get("source_ids", [])) and card.get("review_status") != "rejected":
                card["review_status"] = "stale"
                card["updated_at"] = utc_now()
                atomic_json(path, card)
                if card.get("id") not in stale:
                    stale.append(card.get("id"))
    print(json.dumps({"as_of": as_of.isoformat(), "stale_ids": stale, "marked": bool(args.mark)}, ensure_ascii=False, indent=2))


def text_tokens(value: str) -> list[str]:
    return [token for token in re.split(r"[\s,，。；;、:/]+", value.lower()) if len(token) >= 2]


def retrieval_result(card: dict[str, Any], request: dict[str, Any], mode: str) -> dict[str, Any] | None:
    major = request["major"]["name"]
    region = request["region"]
    reasons = []
    similarities = []
    differences = []
    if major in card.get("major_tags", []):
        reasons.append("major_exact")
        similarities.append(f"专业标签包含{major}")
    elif major in card.get("bridge_options", []):
        reasons.append("major_bridge")
        similarities.append(f"包含{major}的桥接路径")
    if region in card.get("region_tags", []):
        reasons.append("region_exact")
        similarities.append(f"地域适用范围包含{region}")
    elif card.get("region_tags"):
        differences.append(f"卡片地域为{card.get('region_tags')}，用户请求地域为{region}")
    if mode == "background_similar" and not any(reason in reasons for reason in ("major_exact", "major_bridge")):
        return None
    if mode in {"goal_oriented", "direction_discovery"}:
        query = " ".join(str(gap.get("claim_to_test", "")) for gap in request.get("evidence_gaps", []))
        haystack = json.dumps({
            "title": card.get("title"), "direction": card.get("direction"), "activities": card.get("core_activities"),
            "supports": card.get("supports"), "claims": card.get("claims")
        }, ensure_ascii=False).lower()
        matched = [token for token in text_tokens(query) if token in haystack]
        if matched:
            reasons.append("direction_keyword" if mode == "direction_discovery" else "goal_keyword")
            similarities.append("目标证据词重合：" + "、".join(matched[:5]))
        elif not reasons or mode == "direction_discovery":
            return None
    if mode == "direction_discovery" and card.get("card_type") not in {"occupation", "pathway"}:
        return None
    return {
        "id": card.get("id"), "title": card.get("title"), "card_type": card.get("card_type"),
        "retrieval_basis": reasons, "similarities": similarities,
        "important_differences": differences,
        "non_transferable_conditions": card.get("non_transferable_conditions", []),
        "supports": card.get("supports", []), "cannot_prove": card.get("cannot_prove", []),
        "source_ids": card.get("source_ids", []), "review_status": card.get("review_status")
    }


def command_retrieve(args: argparse.Namespace) -> None:
    root = knowledge_root(Path(args.root))
    if not (root / "config.json").is_file():
        raise KnowledgeError("knowledge unavailable: missing knowledge/config.json")
    request = read_json(Path(args.request))
    errors = validate_request(request)
    if errors:
        raise KnowledgeError("invalid request:\n- " + "\n- ".join(errors))
    request.setdefault("request_purpose", "path_validation")
    request.setdefault("grade_stage", "other")
    if args.mode not in request["retrieval_modes"]:
        raise KnowledgeError(f"mode {args.mode} was not authorized in the request")
    results = []
    sources = {identifier: data for identifier, (_, data) in all_sources(root).items()}
    excluded_counts = {"unapproved_or_stale_status": 0, "expired": 0, "unusable_source": 0}
    for _, (_, card) in all_cards(root).items():
        linked_sources = [sources.get(identifier) for identifier in card.get("source_ids", [])]
        source_unusable = any(
            source is None or source.get("review_status") not in USABLE_STATUSES or is_stale(source, today())
            for source in linked_sources
        )
        if card.get("review_status") not in USABLE_STATUSES:
            excluded_counts["unapproved_or_stale_status"] += 1
            continue
        if is_stale(card, today()):
            excluded_counts["expired"] += 1
            continue
        if source_unusable:
            excluded_counts["unusable_source"] += 1
            continue
        result = retrieval_result(card, request, args.mode)
        if result:
            result["sources"] = [
                {
                    "source_id": source_id, "title": sources[source_id].get("title"),
                    "publisher": sources[source_id].get("publisher"), "url": sources[source_id].get("url"),
                    "published_at": sources[source_id].get("published_at"), "checked_at": sources[source_id].get("checked_at"),
                    "valid_until": sources[source_id].get("valid_until"), "review_status": sources[source_id].get("review_status")
                }
                for source_id in card.get("source_ids", []) if source_id in sources
            ]
            results.append(result)
    snapshot_id = next_id(root / "snapshots", "snapshot")
    usable_count = len(results)
    coverage_status = "no_usable_match" if usable_count == 0 else "partial" if usable_count < 3 else "sufficient"
    payload = {
        "snapshot_id": snapshot_id, "request_id": request["request_id"], "generated_at": utc_now(),
        "request_purpose": request["request_purpose"], "mode": args.mode,
        "major": request["major"], "grade_stage": request["grade_stage"], "region": request["region"],
        "retrieval_mode": "seed_cards_fallback",
        "coverage_status": coverage_status, "usable_result_count": usable_count, "excluded_counts": excluded_counts,
        "results": results, "note": "Evidence candidates only; no suitability score or success probability."
    }
    atomic_json(root / "snapshots" / f"{snapshot_id}.json", payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def command_queue(args: argparse.Namespace) -> None:
    root = knowledge_root(Path(args.root))
    items = []
    for path in sorted((root / "review_queue").glob("*.json")):
        data = read_json(path)
        if data.get("status") == "open":
            items.append({"queue_id": data.get("queue_id"), "reason": data.get("reason"), "existing_id": data.get("existing_id"), "path": str(path)})
    print(json.dumps({"open_count": len(items), "items": items}, ensure_ascii=False, indent=2))


def command_review(args: argparse.Namespace) -> None:
    root = knowledge_root(Path(args.root))
    records = {**all_sources(root), **all_cards(root)}
    if args.id not in records:
        raise KnowledgeError(f"unknown knowledge id {args.id}")
    path, record = records[args.id]
    decision_status = {"approve": "human_approved", "reject": "rejected", "conflict": "conflicting"}[args.decision]
    updated = copy.deepcopy(record)
    updated["review_status"] = decision_status
    updated["updated_at"] = utc_now()
    audit = {
        "record_id": args.id, "decision": args.decision, "review_text": args.text.strip(),
        "recorded_at": utc_now(), "previous_status": record.get("review_status")
    }
    if not audit["review_text"]:
        raise KnowledgeError("review text cannot be empty")
    atomic_json(path, updated)
    digest = hashlib.sha256(json.dumps(audit, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    atomic_json(root / "audit" / f"review-{digest}.json", audit)
    print(f"REVIEWED {args.id} status={decision_status}")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="caplab_knowledge")
    sub = root.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init"); p.add_argument("--root", required=True); p.add_argument("--seed"); p.add_argument("--allow-temporary", action="store_true"); p.add_argument("--empty-for-test", action="store_true"); p.set_defaults(func=command_init)
    p = sub.add_parser("seed-knowledge"); p.add_argument("--root", required=True); p.add_argument("--seed", required=True); p.set_defaults(func=command_seed)
    p = sub.add_parser("validate-request"); p.add_argument("--request", required=True); p.set_defaults(func=command_validate_request)
    p = sub.add_parser("validate"); p.add_argument("--root", required=True); p.set_defaults(func=command_validate)
    p = sub.add_parser("add"); p.add_argument("--root", required=True); p.add_argument("--file", required=True); p.set_defaults(func=command_add)
    p = sub.add_parser("freshness"); p.add_argument("--root", required=True); p.add_argument("--as-of"); p.add_argument("--mark", action="store_true"); p.set_defaults(func=command_freshness)
    p = sub.add_parser("retrieve"); p.add_argument("--root", required=True); p.add_argument("--request", required=True); p.add_argument("--mode", choices=sorted(MODES), required=True); p.set_defaults(func=command_retrieve)
    p = sub.add_parser("queue"); p.add_argument("--root", required=True); p.set_defaults(func=command_queue)
    p = sub.add_parser("review"); p.add_argument("--root", required=True); p.add_argument("--id", required=True); p.add_argument("--decision", choices=("approve", "reject", "conflict"), required=True); p.add_argument("--text", required=True); p.set_defaults(func=command_review)
    return root


def main() -> int:
    from caplab_bootstrap import BootstrapError
    args = parser().parse_args()
    try:
        args.func(args)
        return 0
    except (KnowledgeError, BootstrapError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
