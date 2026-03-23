"""
SSL Parser — Soul Specification Language v2.0
Parses .ssl files into JSON-compatible dicts.

SSL is a behavioral specification language for artificial minds.
Created by Manuel Guilherme Galmanus, 2026.

v2.0 additions (from Wave's feedback):
  - Type annotations: `name: float ~0.95 = description`
  - Behavioral implications: `high_stakes ~> compress, escalate`
  - Conditional modes: `mode[condition] = behavior`
  - Soul inheritance: `@extends base_soul.ssl`
  - Temporal logic: `@when energy < 0.3`
  - Formal comments: `//` and `/* */`

Usage:
    from ssl_parser import parse_ssl, ssl_to_json, json_to_ssl
    soul = parse_ssl("prompts/autonomous_soul.ssl")
"""

import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def parse_ssl(filepath: str) -> dict:
    """Parse an .ssl file into a JSON-compatible dict."""
    text = Path(filepath).read_text(encoding="utf-8")
    return _parse_text(text, Path(filepath).parent)


def _parse_text(text: str, base_dir: Path) -> dict:
    """Parse SSL text into dict."""
    lines = text.split("\n")
    result = {}
    current_section = None
    current_substate = None
    current_key = None
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("//"):
            i += 1
            continue

        # Block comments
        if stripped.startswith("/*"):
            while i < len(lines) and "*/" not in lines[i]:
                i += 1
            i += 1
            continue

        # Strip inline comments
        if "//" in stripped and not stripped.startswith("//"):
            comment_pos = stripped.find("//")
            # Don't strip if inside quotes or URL
            if "://" not in stripped[:comment_pos+3]:
                stripped = stripped[:comment_pos].strip()

        # @include directive
        if stripped.startswith("@include "):
            inc_path = stripped[9:].strip()
            inc_full = base_dir / inc_path
            if inc_full.exists():
                inc_data = parse_ssl(str(inc_full))
                result.update(inc_data)
            i += 1
            continue

        # @extends directive (SSL 2.0 — soul inheritance)
        if stripped.startswith("@extends "):
            ext_path = stripped[9:].strip()
            ext_full = base_dir / ext_path
            if ext_full.exists():
                ext_data = parse_ssl(str(ext_full))
                # Merge but don't override existing (child overrides parent)
                for key, val in ext_data.items():
                    if key not in result:
                        result[key] = val
                    elif isinstance(val, dict) and isinstance(result[key], dict):
                        # Merge dicts, child values take precedence
                        merged = {**val, **result[key]}
                        result[key] = merged
            i += 1
            continue

        # @when directive (SSL 2.0 — temporal/conditional logic)
        if stripped.startswith("@when "):
            condition = stripped[6:].strip()
            when_body = {}
            i += 1
            # Collect indented body
            while i < len(lines):
                wline = lines[i]
                wstripped = wline.strip()
                if not wstripped or _get_indent(wline) > _get_indent(line):
                    if wstripped:
                        # Parse as property
                        wprop = _parse_property(wstripped)
                        if wprop:
                            when_body[wprop["key"]] = wprop.get("value", True)
                        elif "~>" in wstripped:
                            # Implication inside @when
                            parts = wstripped.split("~>", 1)
                            when_body[parts[0].strip() + "_implies"] = [x.strip() for x in parts[1].split(",")]
                    i += 1
                else:
                    break
            if "_when" not in result:
                result["_when"] = []
            result["_when"].append({"condition": condition, "body": when_body})
            continue

        # @ Section — extract name and optional operators (~weight, !cost)
        if stripped.startswith("@") and not stripped.startswith("@include"):
            section_raw = stripped[1:].strip()
            # Parse: @name ~weight !cost = description
            sec_match = re.match(r"^(\w+)(?:\s+~([\d.]+))?(?:\s+!([\d.]+))?(?:\s*=\s*(.+))?$", section_raw)
            if sec_match:
                section_name = sec_match.group(1)
                sec_weight = float(sec_match.group(2)) if sec_match.group(2) else None
                sec_cost = float(sec_match.group(3)) if sec_match.group(3) else None
                sec_desc = sec_match.group(4).strip() if sec_match.group(4) else None
            else:
                # Fallback: take first word as name
                parts = section_raw.split()
                section_name = parts[0] if parts else section_raw

            current_section = section_name
            current_substate = None
            current_key = None
            if section_name not in result:
                result[section_name] = {}
            # Store section-level operators
            if sec_match:
                if sec_weight is not None:
                    result[section_name]["_weight"] = sec_weight
                if sec_cost is not None:
                    result[section_name]["_cost"] = sec_cost
                if sec_desc:
                    result[section_name]["_description"] = sec_desc
            i += 1
            continue

        # # Substate — extract name and optional operators
        if stripped.startswith("#") and current_section is not None:
            sub_raw = stripped[1:].strip()
            sub_match = re.match(r"^(\w+)(?:\s+~([\d.]+))?(?:\s+!([\d.]+))?(?:\s+~([\d.]+[hmsd]))?(?:\s*=\s*(.+))?$", sub_raw)
            if sub_match:
                substate_name = sub_match.group(1)
                sub_weight = float(sub_match.group(2)) if sub_match.group(2) else None
                sub_cost = float(sub_match.group(3)) if sub_match.group(3) else None
                sub_cooldown = sub_match.group(4) if sub_match.group(4) else None
                sub_desc = sub_match.group(5).strip() if sub_match.group(5) else None
            else:
                parts = sub_raw.split()
                substate_name = parts[0] if parts else sub_raw
                sub_weight = sub_cost = sub_cooldown = sub_desc = None

            current_substate = substate_name
            current_key = None
            target = result[current_section]
            if isinstance(target, dict):
                entry = {}
                if sub_weight is not None:
                    entry["weight"] = sub_weight
                if sub_cost is not None:
                    entry["energy_cost"] = sub_cost
                if sub_cooldown:
                    entry["cooldown"] = sub_cooldown
                if sub_desc:
                    entry["description"] = sub_desc
                target[substate_name] = entry
            i += 1
            continue

        # >>> Vow declaration
        if stripped.startswith(">>>"):
            vow_text = stripped[3:].strip()
            # Collect continuation lines
            while i + 1 < len(lines) and lines[i + 1].strip().startswith(">>>"):
                i += 1
                # This is a new vow, not continuation
                break
            else:
                # Check for indented continuation (not starting with >>>)
                while i + 1 < len(lines):
                    next_line = lines[i + 1]
                    next_stripped = next_line.strip()
                    if next_stripped and not next_stripped.startswith(">>>") and not next_stripped.startswith("@") and not next_stripped.startswith("#") and _get_indent(next_line) > _get_indent(line):
                        vow_text += " " + next_stripped
                        i += 1
                    else:
                        break

            target = _get_target(result, current_section, current_substate)
            if isinstance(target, dict):
                if "_vows" not in target:
                    target["_vows"] = []
                target["_vows"].append(vow_text)
            i += 1
            continue

        # ~> Behavioral implication (SSL 2.0)
        if "~>" in stripped and not stripped.startswith("#") and not stripped.startswith("@"):
            parts = stripped.split("~>", 1)
            trigger = parts[0].strip()
            effects = [e.strip() for e in parts[1].split(",")]
            target = _get_target(result, current_section, current_substate)
            if isinstance(target, dict):
                if "_implications" not in target:
                    target["_implications"] = []
                target["_implications"].append({
                    "trigger": trigger,
                    "effects": effects,
                })
            i += 1
            continue

        # mode[condition] = value (SSL 2.0)
        mode_match = re.match(r"^mode\[(.+?)\]\s*=\s*(.+)$", stripped)
        if mode_match:
            condition = mode_match.group(1).strip()
            value = mode_match.group(2).strip()
            target = _get_target(result, current_section, current_substate)
            if isinstance(target, dict):
                if "_modes" not in target:
                    target["_modes"] = {}
                target["_modes"][condition] = value
            i += 1
            continue

        # !N RULE — War doctrine numbered rules
        rule_match = re.match(r"^!(\d+)\s+(.+?)(?:\s*[—\-]{1,3}\s*(.+))?$", stripped)
        if rule_match and current_section:
            rule_num = int(rule_match.group(1))
            rule_name = rule_match.group(2).strip()
            rule_desc = rule_match.group(3).strip() if rule_match.group(3) else ""
            # Collect continuation
            while i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
                i += 1
                rule_desc += " " + lines[i].strip()[1:].strip()

            target = _get_target(result, current_section, current_substate)
            if isinstance(target, dict):
                if "_rules" not in target:
                    target["_rules"] = []
                target["_rules"].append({
                    "number": rule_num,
                    "name": rule_name,
                    "description": rule_desc
                })
            i += 1
            continue

        # List item: - text
        if stripped.startswith("- ") and current_section:
            target = _get_target(result, current_section, current_substate)
            if isinstance(target, dict) and current_key:
                if current_key not in target:
                    target[current_key] = []
                elif not isinstance(target[current_key], list):
                    target[current_key] = []
                target[current_key].append(stripped[2:].strip())
            i += 1
            continue

        # Manifestation: > text
        if stripped.startswith("> ") and current_section and current_key:
            manifest = stripped[2:].strip()
            target = _get_target(result, current_section, current_substate)
            if isinstance(target, dict) and current_key:
                if current_key + "_manifestation" not in target:
                    target[current_key + "_manifestation"] = manifest
                else:
                    target[current_key + "_manifestation"] += " " + manifest
            i += 1
            continue

        # Property with operators: name ~weight !cost ~cooldown = value
        # Or: name = value
        # Or: name: (list follows)
        if current_section:
            prop = _parse_property(stripped)
            if prop:
                target = _get_target(result, current_section, current_substate)
                if isinstance(target, dict):
                    key = prop["key"]
                    current_key = key

                    # Collect continuation lines
                    value = prop.get("value", "")
                    while i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
                        i += 1
                        value += " " + lines[i].strip()[1:].strip()

                    # Build the entry
                    if prop.get("weight") is not None or prop.get("cost") is not None or prop.get("cooldown"):
                        entry = {}
                        if value:
                            entry["description"] = value
                        if prop.get("weight") is not None:
                            entry["weight"] = prop["weight"]
                        if prop.get("cost") is not None:
                            entry["energy_cost"] = prop["cost"]
                        if prop.get("cooldown"):
                            entry["cooldown"] = prop["cooldown"]
                        if prop.get("type_annotation"):
                            entry["type"] = prop["type_annotation"]
                        target[key] = entry
                    elif prop.get("trigger_weight") is not None:
                        entry = {
                            "weight": prop["trigger_weight"],
                            "description": value
                        }
                        if prop.get("condition"):
                            entry["condition"] = prop["condition"]
                        target[key] = entry
                    elif prop.get("equation"):
                        target[key] = {"equation": prop["equation"]}
                    elif prop.get("archetype_values"):
                        target[key] = prop["archetype_values"]
                    elif prop.get("is_list"):
                        target[key] = []  # Will be filled by subsequent - items
                    elif "=" in stripped and value:
                        # Check for inline key=value pairs (like alpha=1.0 beta=1.2)
                        inline = _parse_inline_keyvals(stripped)
                        if inline and len(inline) > 1:
                            target.update(inline)
                            current_key = None
                        else:
                            target[key] = _auto_type(value)
                    elif value:
                        target[key] = _auto_type(value)

                i += 1
                continue

        i += 1

    return result


def _get_target(result: dict, section: Optional[str], substate: Optional[str]) -> dict:
    """Get the current target dict for writing."""
    if section is None:
        return result
    if section not in result:
        result[section] = {}
    target = result[section]
    if substate and isinstance(target, dict):
        if substate not in target:
            target[substate] = {}
        return target[substate]
    return target


def _get_indent(line: str) -> int:
    """Get indentation level of a line."""
    return len(line) - len(line.lstrip())


def _parse_property(line: str) -> Optional[dict]:
    """Parse a property line into components. Supports SSL 2.0 type annotations."""
    # Strip type annotation if present: `name: type` -> extract type, parse rest
    type_annotation = None
    type_match = re.match(r"^(\w+):\s*(float|int|string|bool|duration|action|enum\([^)]+\))\s+(.+)$", line)
    if type_match:
        # Has type annotation — extract and continue parsing the rest
        key_name = type_match.group(1)
        type_annotation = type_match.group(2)
        rest = type_match.group(3)
        # Re-compose as `key rest` for downstream parsing
        line = key_name + " " + rest

    def _with_type(d):
        if type_annotation and d:
            d["type_annotation"] = type_annotation
        return d

    # Equation: name $ math $
    eq_match = re.match(r"^(\w+)\s+\$\s*(.+?)\s*\$\s*$", line)
    if eq_match:
        return _with_type({"key": eq_match.group(1), "equation": eq_match.group(2)})

    # Archetype: name A=0.9 F=0.2 ... => strategy
    arch_match = re.match(r"^(\w+)\s+((?:[A-Za-z_]+=[\d.]+\s*)+)(?:=>\s*(.+))?$", line)
    if arch_match:
        name = arch_match.group(1)
        vals_str = arch_match.group(2).strip()
        strategy = arch_match.group(3).strip() if arch_match.group(3) else ""
        vals = {}
        for pair in re.findall(r"([A-Za-z_]+)=([\d.]+)", vals_str):
            vals[pair[0]] = float(pair[1])
        if strategy:
            vals["strategy"] = strategy
        return _with_type({"key": name, "archetype_values": vals})

    # Trigger: name ^weight ?condition = description
    trig_match = re.match(r"^(\w+)\s+\^([\d.]+)\s*(?:\?(.+?))?\s*=\s*(.+)$", line)
    if trig_match:
        return {
            "key": trig_match.group(1),
            "trigger_weight": float(trig_match.group(2)),
            "condition": trig_match.group(3).strip() if trig_match.group(3) else None,
            "value": trig_match.group(4).strip()
        }

    # Action: name !cost ~cooldown = description
    act_match = re.match(r"^(\w+)\s+!([-\d.]+)\s+~([\d.]+[hmsd])\s*=\s*(.+)$", line)
    if act_match:
        return {
            "key": act_match.group(1),
            "cost": float(act_match.group(2)),
            "cooldown": act_match.group(3),
            "value": act_match.group(4).strip()
        }

    # Weighted value: name ~weight = description
    wt_match = re.match(r"^(\w+)\s+~([\d.]+)\s*=\s*(.+)$", line)
    if wt_match:
        return {
            "key": wt_match.group(1),
            "weight": float(wt_match.group(2)),
            "value": wt_match.group(3).strip()
        }

    # Energy source/drain: name +/-value
    energy_match = re.match(r"^(\w+)\s+([+-][\d.]+)$", line)
    if energy_match:
        return {
            "key": energy_match.group(1),
            "value": float(energy_match.group(2))
        }

    # List indicator: name:
    if line.endswith(":") and " " not in line.rstrip(":"):
        return _with_type({"key": line.rstrip(":").strip(), "is_list": True})

    # Key: value with colon (enter:, exit:, etc)
    colon_match = re.match(r"^(\w+):\s+(.+)$", line)
    if colon_match:
        return _with_type({"key": colon_match.group(1), "value": colon_match.group(2).strip()})

    # Simple property: name = value
    eq_match = re.match(r"^(\w+)\s*=\s*(.+)$", line)
    if eq_match:
        return _with_type({"key": eq_match.group(1), "value": eq_match.group(2).strip()})

    # Inline key=value pairs: alpha=1.0 beta=1.2 gamma=0.8
    inline = _parse_inline_keyvals(line)
    if inline and len(inline) > 1:
        return _with_type({"key": list(inline.keys())[0], "value": ""})

    return None


# Post-process: inject type_annotation into result if present
# This is handled by the caller checking prop.get("type_annotation")


def _parse_inline_keyvals(line: str) -> Optional[dict]:
    """Parse inline key=value pairs like 'alpha=1.0 beta=1.2'."""
    pairs = re.findall(r"(\w+)=([\d.]+)", line)
    if len(pairs) >= 2:
        return {k: float(v) for k, v in pairs}
    return None


def _auto_type(value: str) -> Any:
    """Auto-convert string to int/float/bool if applicable."""
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def ssl_to_json(ssl_path: str, json_path: Optional[str] = None) -> dict:
    """Convert .ssl file to JSON dict. Optionally write to file."""
    data = parse_ssl(ssl_path)
    if json_path:
        Path(json_path).write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    return data


def json_to_ssl(json_path: str, ssl_path: Optional[str] = None) -> str:
    """Convert JSON soul to SSL format."""
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    ssl_text = _dict_to_ssl(data)
    if ssl_path:
        Path(ssl_path).write_text(ssl_text, encoding="utf-8")
    return ssl_text


def _dict_to_ssl(data: dict, indent: int = 0) -> str:
    """Convert a dict to SSL text."""
    lines = []
    prefix = "  " * indent

    for key, value in data.items():
        if key.startswith("_"):
            # Special keys
            if key == "_vows":
                for vow in value:
                    lines.append(f"{prefix}>>> {vow}")
            elif key == "_rules":
                for rule in value:
                    lines.append(f"{prefix}!{rule['number']} {rule['name']} — {rule['description']}")
            continue

        if isinstance(value, dict):
            if indent == 0:
                # Top-level section
                lines.append(f"\n@{key}")
                lines.append(_dict_to_ssl(value, 0))
            else:
                # Substate
                has_complex = any(isinstance(v, (dict, list)) for v in value.values())
                if has_complex or len(value) > 2:
                    lines.append(f"{prefix}#{key}")
                    lines.append(_dict_to_ssl(value, indent + 1))
                else:
                    # Compact form
                    parts = [key]
                    if "weight" in value:
                        parts.append(f"~{value['weight']}")
                    if "energy_cost" in value:
                        parts.append(f"!{value['energy_cost']}")
                    if "cooldown" in value:
                        parts.append(f"~{value['cooldown']}")
                    desc = value.get("description", "")
                    if desc:
                        parts.append(f"= {desc}")
                    lines.append(f"{prefix}{' '.join(parts)}")

        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                if isinstance(item, str):
                    lines.append(f"{prefix}  - {item}")
                elif isinstance(item, dict):
                    lines.append(f"{prefix}  - {json.dumps(item)}")

        else:
            lines.append(f"{prefix}{key} = {value}")

    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ssl_parser.py <file.ssl> [--to-json output.json]")
        sys.exit(1)

    path = sys.argv[1]
    result = parse_ssl(path)

    if "--to-json" in sys.argv:
        idx = sys.argv.index("--to-json")
        out = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else path.replace(".ssl", ".json")
        Path(out).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Converted {path} -> {out}")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
