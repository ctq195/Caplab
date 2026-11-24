"""Personal fact and timeline contract (schema 1.1.0; V1.0.0 port); Python standard library only."""
from __future__ import annotations

import copy
import datetime as dt
import re

STATUSES = ["unconfirmed", "confirmed", "conflicted", "declined"]
INTAKE_KEYS = {"decision_question", "problem_designability", "desired_output", "candidate_paths", "candidate_generation_needed", "deadline", "major", "personal_facts", "sources", "records", "constraints", "conflicts", "unknowns", "intake_ready", "confirmation_status", "decision_status", "psychological_context"}
SOURCE_IDS = {"type": "array", "items": {"type": "string", "pattern": r"^SRC-[0-9]{6}$"}, "uniqueItems": True}


def fact(value_type="string", **extra):
    value = {"type": [value_type, "null"]}
    if value_type == "string":
        value["minLength"] = 1
    props = {"value": value, "status": {"enum": STATUSES}, "source_ids": SOURCE_IDS, **extra}
    return {"type": "object", "additionalProperties": False, "required": list(props), "properties": props}


DATE = {"type": ["string", "null"], "pattern": r"^\d{4}-\d{2}-\d{2}$"}
EVENT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["name", "kind", "date", "precision", "status", "source_ids", "related_graduation_year", "eligibility_status", "rule_source_ids"],
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "kind": {"enum": ["preparation", "application", "exam", "program_entry", "internship", "employment", "other"]},
        "date": {"type": ["string", "null"]}, "precision": {"enum": ["year", "month", "day"]},
        "status": {"enum": STATUSES}, "source_ids": SOURCE_IDS,
        "related_graduation_year": {"type": ["integer", "null"], "minimum": 1900, "maximum": 2200},
        "eligibility_status": {"enum": ["unknown", "not_applicable", "verified"]}, "rule_source_ids": SOURCE_IDS,
    },
}
PERSONAL_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "gender": fact(),
        "age": fact("integer", as_of=DATE),
        "education_level": fact(),
        "institution_name": fact(),
        "institution_tier": fact(classification_basis={"type": ["string", "null"], "minLength": 1}),
        "enrollment_year": fact("integer"),
        "graduation_year": fact("integer", kind={"enum": ["expected", "actual"]}),
        "birth_date": fact(),
        "key_timepoints": {
            "type": "object", "additionalProperties": False,
            "required": ["status", "source_ids", "events"],
            "properties": {"status": {"enum": STATUSES}, "source_ids": SOURCE_IDS,
                           "events": {"type": "array", "items": EVENT_SCHEMA}},
        },
    },
}
PERSONAL_SCHEMA["required"] = [k for k in PERSONAL_SCHEMA["properties"] if k != "birth_date"]
PERSONAL_SCHEMA["properties"]["age"]["properties"]["value"].update(minimum=0, maximum=130)
for key in ("enrollment_year", "graduation_year"):
    PERSONAL_SCHEMA["properties"][key]["properties"]["value"].update(minimum=1900, maximum=2200)
MAJOR_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["name", "code", "status", "source_ids"],
                "properties": {"name": {"type": ["string", "null"], "minLength": 1}, "code": {"type": ["string", "null"]},
                               "status": {"enum": STATUSES}, "source_ids": SOURCE_IDS}}
PSYCH_SCHEMA = {"type": "object", "additionalProperties": False,
                "required": ["mode", "observation_ids", "hypothesis_ids", "revision_requests"],
                "properties": {"mode": {"enum": ["enabled", "skipped", "stop_saving"]},
                               "observation_ids": {"type": "array", "items": {"type": "string", "pattern": r"^(INT|PRO|OBS)-[0-9]{6}$"}},
                               "hypothesis_ids": {"type": "array", "items": {"type": "string", "pattern": r"^HYP-[0-9]{6}$"}},
                               "revision_requests": {"type": "array", "items": {"type": "string", "minLength": 1}}}}


def schema_errors(value, schema, path):
    """Validate the deliberately small JSON Schema vocabulary used above."""
    errors = []
    types = {"object": lambda v: isinstance(v, dict), "array": lambda v: isinstance(v, list),
             "string": lambda v: isinstance(v, str), "integer": lambda v: type(v) is int,
             "boolean": lambda v: type(v) is bool, "null": lambda v: v is None}
    expected = schema.get("type")
    if expected and not any(types[t](value) for t in ([expected] if isinstance(expected, str) else expected)):
        return [f"{path}: invalid type, expected {expected}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: invalid enum {value!r}")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        errors += [f"{path}: missing field {k}" for k in schema.get("required", []) if k not in value]
        if schema.get("additionalProperties") is False:
            errors += [f"{path}: unknown field {k}" for k in value if k not in props]
        for k in value.keys() & props.keys():
            errors += schema_errors(value[k], props[k], f"{path}.{k}")
    if isinstance(value, list):
        if schema.get("uniqueItems") and len({str(x) for x in value}) != len(value):
            errors.append(f"{path}: duplicate items")
        for i, item in enumerate(value):
            errors += schema_errors(item, schema.get("items", {}), f"{path}[{i}]")
    if isinstance(value, str):
        if len(value.strip()) < schema.get("minLength", 0):
            errors.append(f"{path}: empty value")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            errors.append(f"{path}: invalid format")
    if type(value) is int and not schema.get("minimum", value) <= value <= schema.get("maximum", value):
        errors.append(f"{path}: out of range")
    return errors


def empty_personal():
    result = {k: {"value": None, "status": "unconfirmed", "source_ids": []} for k in PERSONAL_SCHEMA["required"] if k != "key_timepoints"}
    result["age"]["as_of"] = None
    result["institution_tier"]["classification_basis"] = None
    result["graduation_year"]["kind"] = "expected"
    result["key_timepoints"] = {"status": "unconfirmed", "source_ids": [], "events": []}
    return result


def parse_date(value, precision="day"):
    patterns = {"year": (r"\d{4}", "%Y"), "month": (r"\d{4}-\d{2}", "%Y-%m"), "day": (r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d")}
    pattern, fmt = patterns[precision]
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise ValueError("date precision mismatch")
    return dt.datetime.strptime(value, fmt).date()


def source_map(intake):
    return {s.get("source_id"): s for s in intake.get("sources", []) if isinstance(s, dict)}


def sourced_errors(item, sources, path, value_key="value"):
    errors = []
    ids = item.get("source_ids", [])
    for sid in ids:
        if sid not in sources:
            errors.append(f"{path}: unknown source {sid}")
    if item.get("status") == "confirmed":
        if value_key and item.get(value_key) is None:
            errors.append(f"{path}: confirmed value cannot be null")
        if not ids:
            errors.append(f"{path}: confirmed fact requires source_ids")
        for sid in ids:
            src = sources.get(sid, {})
            if not src.get("title") or src.get("source_type") not in {"user_statement", "uploaded_file", "existing_state", "public_source"} or src.get("read_status") not in {"success", "read", "available"}:
                errors.append(f"{path}: confirmed fact needs a successfully read source {sid}")
    return errors


def timeline_errors(events, intake, ready=False):
    errors = schema_errors(events, {"type": "array", "items": EVENT_SCHEMA}, "decision_timeline")
    if errors:
        return errors
    sources = source_map(intake)
    grad = intake.get("personal_facts", {}).get("graduation_year", {}).get("value")
    for i, event in enumerate(events):
        label = f"decision_timeline[{i}]"
        errors += sourced_errors(event, sources, label, "date")
        if ready and event["status"] != "confirmed":
            errors.append(f"{label}: timepoint not confirmed")
        date = None
        if event["date"] is not None:
            try:
                date = parse_date(event["date"], event["precision"])
            except ValueError:
                errors.append(f"{label}: invalid date or precision")
        if event["related_graduation_year"] is not None and event["related_graduation_year"] != grad:
            errors.append(f"{label}: graduation anchor conflicts with confirmed personal facts")
        policy_event = event["kind"] in {"application", "exam", "program_entry"}
        if policy_event and event["status"] == "confirmed":
            if event["eligibility_status"] != "verified" or not event["rule_source_ids"]:
                errors.append(f"{label}: formal application/exam/entry needs verified eligibility and rule_source_ids; preparation is a separate kind")
            if event["related_graduation_year"] != grad or grad is None:
                errors.append(f"{label}: formal event must anchor current graduation year")
        if event["eligibility_status"] == "verified":
            if not event["rule_source_ids"]:
                errors.append(f"{label}: verified eligibility needs policy sources")
            for sid in event["rule_source_ids"]:
                src = sources.get(sid, {})
                if src.get("source_type") not in {"public_source", "uploaded_file"} or src.get("read_status") not in {"success", "read", "available"} or not src.get("applicable_period"):
                    errors.append(f"{label}: eligibility source must identify a read policy and applicable_period: {sid}")
        for sid in event["rule_source_ids"]:
            if sid not in sources:
                errors.append(f"{label}: unknown policy source {sid}")
    return errors


def intake_errors(intake, require_ready=False):
    if not isinstance(intake, dict):
        return ["intake must be an object"]
    ready = require_ready or intake.get("intake_ready") is True
    if require_ready and intake.get("intake_ready") is not True:
        return ["formal stages require intake_ready=true"]
    errors = [f"intake: unknown field {key}" for key in intake if key not in INTAKE_KEYS]
    if not isinstance(intake.get("sources", []), list) or any(not isinstance(s, dict) for s in intake.get("sources", [])):
        return errors + ["intake.sources must be an array of objects"]
    if "intake_ready" in intake and type(intake["intake_ready"]) is not bool:
        errors.append("intake_ready must be boolean")
    personal = intake.get("personal_facts")
    if personal is None:
        if ready:
            errors.append("personal_facts required for ready intake")
        return errors
    errors += schema_errors(personal, PERSONAL_SCHEMA, "personal_facts")
    major = intake.get("major")
    errors += schema_errors(major, MAJOR_SCHEMA, "major")
    if errors:
        return errors
    sources = source_map(intake)
    errors += sourced_errors(major, sources, "major", "name")
    for k, item in personal.items():
        errors += sourced_errors(item, sources, f"personal_facts.{k}", None if k == "key_timepoints" else "value")
        if ready and k in PERSONAL_SCHEMA["required"] and item["status"] != "confirmed":
            errors.append(f"personal_facts.{k}: not confirmed")
    if ready:
        if major["status"] != "confirmed" or intake.get("confirmation_status") != "confirmed":
            errors.append("ready intake requires confirmed major and intake summary")
        if not isinstance(intake.get("decision_question"), str) or not intake["decision_question"].strip():
            errors.append("ready intake requires decision_question")
        if intake.get("conflicts"):
            errors.append("ready intake cannot contain unresolved conflicts; move resolved evidence to records")
    age = personal["age"]
    if age["value"] is not None and age["as_of"] is None:
        errors.append("age requires as_of date")
    for item, value in (("age.as_of", age["as_of"]), ("birth_date", personal.get("birth_date", {}).get("value"))):
        if value is not None:
            try:
                parsed = parse_date(value)
                if parsed > dt.datetime.now(dt.timezone.utc).date():
                    errors.append(f"{item}: cannot be in the future")
            except ValueError:
                errors.append(f"{item}: invalid date")
    birth = personal.get("birth_date", {}).get("value")
    if birth and age["as_of"]:
        try:
            b, a = parse_date(birth), parse_date(age["as_of"])
            actual = a.year - b.year - ((a.month, a.day) < (b.month, b.day))
            if age["value"] is not None and age["value"] != actual:
                errors.append("age conflicts with birth_date at as_of")
        except ValueError:
            pass
    enrollment, graduation = personal["enrollment_year"]["value"], personal["graduation_year"]["value"]
    if enrollment is not None and graduation is not None and enrollment > graduation:
        errors.append("enrollment_year must not exceed graduation_year")
    if personal["institution_tier"]["value"] is not None and not personal["institution_tier"]["classification_basis"]:
        errors.append("institution_tier requires classification_basis")
    errors += timeline_errors(personal["key_timepoints"]["events"], intake, ready)
    return errors


def sections_errors(sections, metadata=None):
    intake = sections.get("intake", {})
    errors = intake_errors(intake)
    for name, section in sections.items():
        for item in (section if isinstance(section, list) else [section]):
            if isinstance(item, dict) and "psychological_context" in item:
                errors += schema_errors(item["psychological_context"], PSYCH_SCHEMA, f"{name}.psychological_context")
    for name in ("profile", "path_decision", "cycle_plan", "reviews"):
        if (metadata or {}).get(name, {}).get("status") == "stale":
            continue
        values = sections.get(name, []) if name == "reviews" else [sections.get(name, {})]
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, dict) and "decision_timeline" in value:
                ready = (value.get("profile_ready") is True or value.get("accepted") is True
                         or value.get("plan_status") in {"selected", "in_progress", "waiting"}
                         or (name == "reviews" and value.get("decision") is not None))
                errors += timeline_errors(value["decision_timeline"], intake, ready=ready)
    return errors


def downgrade_legacy(state):
    """New current snapshot only; original history is never rewritten."""
    state = copy.deepcopy(state)
    intake = state["sections"]["intake"]
    personal = intake.setdefault("personal_facts", {})
    for key, default in empty_personal().items():
        personal.setdefault(key, default)
        personal[key]["status"] = "unconfirmed"
    intake.setdefault("major", {"name": None, "code": None, "status": "unconfirmed"})
    intake["major"].setdefault("code", None)
    intake["major"].setdefault("source_ids", [])
    intake["major"]["status"] = "unconfirmed"
    intake["intake_ready"] = False
    intake["confirmation_status"] = "unconfirmed"
    state["section_meta"]["intake"]["status"] = "draft"
    for name in ("profile", "path_decision", "cycle_plan", "reviews"):
        if state["sections"][name]:
            state["section_meta"][name]["status"] = "stale"
    state["schema_version"] = "1.1.0"
    state["active_stage"] = "profile_intake"
    return state
