"""
SSL Parser — Soul Specification Language
Parses .ssl files into JSON-compatible dicts.

SSL is an LLM-native language for specifying artificial minds.
Created by Manuel Guilherme Galmanus, 2026.

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

        # @include directive
        if stripped.startswith("@include "):
            inc_path = stripped[9:].strip()
            inc_full = base_dir / inc_path
            if inc_full.exists():
                inc_data = parse_ssl(str(inc_full))
                result.update(inc_data)
            i += 1
            continue

        # @ Section
        if stripped.startswith("@") and not stripped.startswith("@include"):
            section_name = stripped[1:].strip()
            current_section = section_name
            current_substate = None
            current_key = None
            if section_name not in result:
                result[section_name] = {}
            i += 1
            continue

        # # Substate
        if stripped.startswith("#") and current_section is not None:
            substate_name = stripped[1:].strip()
            current_substate = substate_name
            current_key = None
            target = result[current_section]
            if isinstance(target, dict):
                target[substate_name] = {}
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
    """Parse a property line into components."""
    # Equation: name $ math $
    eq_match = re.match(r"^(\w+)\s+\$\s*(.+?)\s*\$\s*$", line)
    if eq_match:
        return {"key": eq_match.group(1), "equation": eq_match.group(2)}

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
        return {"key": name, "archetype_values": vals}

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
        return {"key": line.rstrip(":").strip(), "is_list": True}

    # Key: value with colon (enter:, exit:, etc)
    colon_match = re.match(r"^(\w+):\s+(.+)$", line)
    if colon_match:
        return {"key": colon_match.group(1), "value": colon_match.group(2).strip()}

    # Simple property: name = value
    eq_match = re.match(r"^(\w+)\s*=\s*(.+)$", line)
    if eq_match:
        return {"key": eq_match.group(1), "value": eq_match.group(2).strip()}

    # Inline key=value pairs: alpha=1.0 beta=1.2 gamma=0.8
    inline = _parse_inline_keyvals(line)
    if inline and len(inline) > 1:
        return {"key": list(inline.keys())[0], "value": ""}

    return None


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
