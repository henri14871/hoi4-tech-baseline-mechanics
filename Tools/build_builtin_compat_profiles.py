#!/usr/bin/env python3
"""
Build one-folder builtin compatibility profiles from compat_generated bundles.

This takes the staging bundles in compat_generated/<slug>/ and writes
namespaced scripted effects directly into common/scripted_effects so the main
ARM mod can switch profile via a game rule instead of shipping separate submods.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
COMPAT_ROOT = REPO_ROOT / "compat_generated"
SCRIPTED_EFFECTS_DIR = REPO_ROOT / "common" / "scripted_effects"
INDEX_PATH = COMPAT_ROOT / "index.json"

PROFILE_ORDER = [
    "blackice",
    "cold_war_iron_curtain",
    "kaiserreich",
    "endsieg",
    "extended_tech_tree_1960",
    "novum_vexillum",
    "rise_of_nations",
    "kaiserredux",
    "the_new_order",
    "millennium_dawn",
    "the_fire_rises",
    "great_war_redux",
    "great_war",
    "road_to_56",
]

PROFILE_OPTION_KEYS = {
    "blackice": "ARM_COMPAT_BLACKICE",
    "cold_war_iron_curtain": "ARM_COMPAT_CWIC",
    "kaiserreich": "ARM_COMPAT_KAISERREICH",
    "endsieg": "ARM_COMPAT_ENDSIEG",
    "extended_tech_tree_1960": "ARM_COMPAT_ETT1960",
    "novum_vexillum": "ARM_COMPAT_NOVUM_VEXILLUM",
    "rise_of_nations": "ARM_COMPAT_RISE_OF_NATIONS",
    "kaiserredux": "ARM_COMPAT_KAISERREDUX",
    "the_new_order": "ARM_COMPAT_TNO",
    "millennium_dawn": "ARM_COMPAT_MILLENNIUM_DAWN",
    "the_fire_rises": "ARM_COMPAT_TFR",
    "great_war_redux": "ARM_COMPAT_GREAT_WAR_REDUX",
    "great_war": "ARM_COMPAT_GREAT_WAR",
    "road_to_56": "ARM_COMPAT_ROAD_TO_56",
}

AUTO_DETECT_LIMITS = {
    "blackice": [
        "country_exists = BMP",
        "country_exists = EHA",
        "country_exists = HAT",
        "country_exists = PGR",
        "country_exists = SCC",
        "country_exists = SDC",
        "country_exists = SKC",
        "country_exists = XIA",
        "country_exists = YUT",
        "country_exists = ZXL",
    ],
    "cold_war_iron_curtain": [
        "country_exists = BAD",
        "country_exists = BAV",
        "country_exists = BCP",
        "country_exists = BCR",
        "country_exists = BTG",
        "country_exists = CVD",
        "country_exists = DOC",
        "country_exists = DRY",
        "country_exists = FNL",
        "country_exists = FUL",
        "country_exists = HOK",
        "country_exists = INO",
        "country_exists = KAS",
        "country_exists = KAY",
        "country_exists = KMP",
        "country_exists = KPA",
        "country_exists = LOS",
        "country_exists = MLA",
        "country_exists = MNL",
        "country_exists = NLF",
        "country_exists = PDG",
        "country_exists = SGP",
        "country_exists = SMI",
        "country_exists = SMK",
        "country_exists = SVI",
        "country_exists = SWK",
        "country_exists = TNG",
        "country_exists = TOA",
        "country_exists = TRS",
        "country_exists = UNS",
    ],
    "kaiserreich": [
        "country_exists = HND",
        "country_exists = HNN",
        "country_exists = IMP",
        "country_exists = KUM",
        "country_exists = SHD",
        "country_exists = SPA",
        "country_exists = WIF",
    ],
    "endsieg": [
        "country_exists = ANA",
        "country_exists = CBU",
        "country_exists = CNT",
        "country_exists = EFR",
        "country_exists = EN3",
        "country_exists = FNN",
        "country_exists = FNR",
        "country_exists = HEJ",
        "country_exists = HEL",
        "country_exists = INU",
        "country_exists = KIT",
        "country_exists = LOK",
        "country_exists = NEJ",
        "country_exists = NOK",
        "country_exists = RCH",
        "country_exists = RKK",
        "country_exists = RKO",
        "country_exists = RKU",
        "country_exists = SOK",
        "country_exists = TSS",
        "country_exists = UBD",
        "country_exists = VIL",
        "country_exists = WUR",
        "country_exists = ZAP",
    ],
    "extended_tech_tree_1960": [
        "ENG = { has_tech = tech_fleet_oiler_1 }",
        "GER = { has_tech = tech_fleet_oiler_1 }",
        "ITA = { has_tech = tech_fleet_oiler_1 }",
        "JAP = { has_tech = tech_fleet_oiler_1 }",
        "SOV = { has_tech = tech_fleet_oiler_1 }",
        "USA = { has_tech = tech_fleet_oiler_1 }",
    ],
    "novum_vexillum": [
        "country_exists = AND",
        "country_exists = BAS",
        "country_exists = ETI",
        "country_exists = FAI",
        "country_exists = FSM",
        "country_exists = GRN",
        "country_exists = HKN",
        "country_exists = JVA",
        "country_exists = KRN",
        "country_exists = MCU",
        "country_exists = NAX",
        "country_exists = RCK",
        "country_exists = RRA",
        "country_exists = SKN",
        "country_exists = SPF",
        "country_exists = SWZ",
    ],
    "rise_of_nations": [
        "country_exists = ACR",
        "country_exists = ALK",
        "country_exists = ANH",
        "country_exists = ART",
        "country_exists = ARZ",
        "country_exists = BOX",
        "country_exists = CBV",
        "country_exists = CIN",
        "country_exists = CZR",
        "country_exists = DEL",
        "country_exists = DON",
        "country_exists = DPK",
        "country_exists = ETR",
        "country_exists = EUR",
        "country_exists = FEN",
        "country_exists = GRC",
        "country_exists = GUK",
        "country_exists = HAW",
        "country_exists = KNS",
        "country_exists = LNA",
        "country_exists = LON",
        "country_exists = MCR",
        "country_exists = MKH",
        "country_exists = MTA",
        "country_exists = NMX",
        "country_exists = OFR",
        "country_exists = OKL",
        "country_exists = OTT",
        "country_exists = PUE",
        "country_exists = ROK",
    ],
    "kaiserredux": [
        "country_exists = ALO",
        "country_exists = BHC",
        "country_exists = CAF",
        "country_exists = CIV",
        "country_exists = DEH",
        "country_exists = DKB",
        "country_exists = KIK",
        "country_exists = MTR",
        "country_exists = NSW",
        "country_exists = SKM",
        "country_exists = SQI",
        "country_exists = TRM",
    ],
    "the_new_order": [
        "country_exists = AAA",
        "country_exists = AAB",
        "country_exists = AAC",
        "country_exists = AAF",
        "country_exists = AAG",
        "country_exists = AAJ",
        "country_exists = AAN",
        "country_exists = AAO",
        "country_exists = ADN",
        "country_exists = AYR",
        "country_exists = AZH",
        "country_exists = AZW",
        "country_exists = BKF",
        "country_exists = BKR",
        "country_exists = BKU",
        "country_exists = BRG",
        "country_exists = BRY",
        "country_exists = CAO",
        "country_exists = CAU",
        "country_exists = CHT",
        "country_exists = CLC",
        "country_exists = CLL",
        "country_exists = CME",
        "country_exists = CYL",
        "country_exists = DRL",
        "country_exists = EWE",
        "country_exists = FAR",
        "country_exists = FAV",
        "country_exists = FFR",
        "country_exists = FRS",
    ],
    "millennium_dawn": [
        "country_exists = ACE",
        "country_exists = ADO",
        "country_exists = AGL",
        "country_exists = BEN",
        "country_exists = BFA",
        "country_exists = CBD",
        "country_exists = CDI",
        "country_exists = CNG",
        "country_exists = DMI",
        "country_exists = DRC",
        "country_exists = EGU",
        "country_exists = FYR",
        "country_exists = GAH",
        "country_exists = GRA",
        "country_exists = GUB",
        "country_exists = HAM",
        "country_exists = HKG",
        "country_exists = IEK",
        "country_exists = LUR",
        "country_exists = MAY",
        "country_exists = MIC",
        "country_exists = MLV",
        "country_exists = MOZ",
        "country_exists = NAM",
        "country_exists = NIG",
        "country_exists = NKO",
        "country_exists = NKR",
        "country_exists = NPM",
        "country_exists = PAU",
        "country_exists = PUK",
    ],
    "the_fire_rises": [
        "country_exists = AAS",
        "country_exists = BRS",
        "country_exists = CNF",
        "country_exists = CPC",
        "country_exists = DPR",
        "country_exists = HOU",
        "country_exists = HRL",
        "country_exists = HTS",
        "country_exists = KKP",
        "country_exists = KLA",
        "country_exists = KNU",
        "country_exists = MND",
        "country_exists = MOA",
        "country_exists = PLD",
        "country_exists = SHB",
        "country_exists = SSA",
        "country_exists = WAT",
        "country_exists = YAM",
    ],
    "great_war_redux": [
        "country_exists = ALM",
        "country_exists = ARB",
        "country_exists = BID",
        "country_exists = CAP",
        "country_exists = CER",
        "country_exists = DAR",
        "country_exists = EPR",
        "country_exists = FUJ",
        "country_exists = GLD",
        "country_exists = HBY",
        "country_exists = JOH",
        "country_exists = KED",
        "country_exists = KEL",
        "country_exists = KUT",
        "country_exists = MJT",
        "country_exists = MSC",
        "country_exists = NAJ",
        "country_exists = NAT",
        "country_exists = ORA",
        "country_exists = PLS",
        "country_exists = RIA",
        "country_exists = RWL",
        "country_exists = SMS",
        "country_exists = TRG",
        "country_exists = WTH",
        "country_exists = ZAN",
    ],
    "great_war": [
        "country_exists = ASR",
        "country_exists = BAY",
        "country_exists = CKK",
        "country_exists = CPM",
        "country_exists = FEC",
        "country_exists = TUK",
        "country_exists = ZHC",
    ],
    "road_to_56": [
        "country_exists = GDC",
        "country_exists = HBC",
        "country_exists = KHM",
        "country_exists = MPL",
        "country_exists = SND",
        "country_exists = XIC",
    ],
}

DOCTRINE_SAFE_PROFILES = {
    "kaiserreich",
    "kaiserredux",
    "endsieg",
    "extended_tech_tree_1960",
    "road_to_56",
}

GRANT_ORDER = [
    "arm_grant_land_infantry",
    "arm_grant_industry_electronics_industry",
    "arm_grant_land_support",
    "arm_grant_land_artillery",
    "arm_grant_land_anti_air",
    "arm_grant_land_anti_tank",
    "arm_grant_land_motorised",
    "arm_grant_land_mechanised",
    "arm_grant_air_fighters",
    "arm_grant_air_cas",
    "arm_grant_land_light_tanks",
    "arm_grant_land_medium_tanks",
    "arm_grant_land_heavy_tanks",
    "arm_grant_land_tanks_generic",
    "arm_grant_naval_submarines",
    "arm_grant_naval_destroyers",
    "arm_grant_naval_light_cruisers",
    "arm_grant_naval_heavy_cruisers",
    "arm_grant_naval_battleships",
    "arm_grant_naval_carriers",
    "arm_grant_industry_electronics_electronics",
    "arm_grant_industry_electronics_radar",
    "arm_grant_air_heavy_fighters",
    "arm_grant_air_tactical_bombers",
    "arm_grant_air_strategic_bombers",
    "arm_grant_air_naval_bombers",
    "arm_grant_air_transport",
    "arm_grant_naval_naval_support",
    "arm_grant_industry_electronics_nuclear",
    "arm_grant_industry_electronics_rockets",
]

CHECK_COMPARE_MAP = {
    ">": "greater_than",
    ">=": "greater_than_or_equals",
    "<": "less_than",
    "<=": "less_than_or_equals",
    "=": "equals",
}


def extract_top_level_block(text: str, identifier: str) -> str:
    pattern = re.compile(rf"(?m)^{re.escape(identifier)}\s*=\s*\{{")
    match = pattern.search(text)
    if not match:
        raise RuntimeError(f"Could not find top-level block for {identifier}")

    start = match.start()
    pos = match.end() - 1
    depth = 0
    while pos < len(text):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[start:pos + 1]
        pos += 1
    raise RuntimeError(f"Unbalanced braces while extracting {identifier}")


def rename_grant_effects(text: str, slug: str) -> str:
    return re.sub(
        r"(?m)^(arm_grant_[A-Za-z0-9_]+)\s*=",
        lambda m: f"{m.group(1)}_{slug} =",
        text,
    )


def rename_tier_effect(block_text: str, slug: str) -> str:
    return re.sub(
        r"(?m)^arm_assign_power_tier\s*=",
        f"arm_assign_power_tier_{slug} =",
        block_text,
        count=1,
    )


def sanitize_runtime_effect_text(text: str) -> str:
    """Normalize generated scripted effects before shipping them in the mod."""
    lines = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        stripped = raw_line.lstrip()
        if stripped.startswith("#"):
            continue
        lines.append(raw_line)

    sanitized = "\n".join(lines)
    sanitized = sanitized.replace("has_technology =", "has_tech =")
    sanitized = sanitized.replace("has_technology=", "has_tech=")
    sanitized = re.sub(
        r"(?m)^(\s*)add_technology\s*=\s*([A-Za-z0-9_:.+-]+)\s*$",
        lambda m: f"{m.group(1)}set_technology = {{ {m.group(2)} = 1 popup = no }}",
        sanitized,
    )
    sanitized = re.sub(
        r"check_variable\s*=\s*\{\s*([A-Za-z0-9_:.]+)\s*(>=|<=|>|<|=)\s*([A-Za-z0-9_:.+-]+)\s*\}",
        lambda m: (
            "check_variable = { "
            f"var = {m.group(1)} value = {m.group(3)} compare = "
            f"{CHECK_COMPARE_MAP[m.group(2)]} }}"
        ),
        sanitized,
    )
    return sanitized


def build_profile_limit_lines(slug: str, indent: str = "        ") -> list[str]:
    lines = [f"{indent}OR = {{"]
    lines.append(f"{indent}    has_game_rule = {{ rule = arm_compat_profile option = {PROFILE_OPTION_KEYS[slug]} }}")
    lines.append(f"{indent}    AND = {{")
    lines.append(f"{indent}        has_game_rule = {{ rule = arm_compat_profile option = ARM_COMPAT_AUTO }}")
    lines.append(f"{indent}        has_global_flag = arm_compat_auto_{slug}")
    lines.append(f"{indent}    }}")
    lines.append(f"{indent}}}")
    return lines


def build_auto_detect_limit_lines(slug: str, indent: str = "        ") -> list[str]:
    markers = AUTO_DETECT_LIMITS.get(slug)
    if not markers:
        raise RuntimeError(f"Missing auto-detect markers for profile: {slug}")
    if len(markers) == 1:
        return [f"{indent}{markers[0]}"]

    lines = [f"{indent}OR = {{"]
    for marker in markers:
        lines.append(f"{indent}    {marker}")
    lines.append(f"{indent}}}")
    return lines


def normalize_generated_tier_block(text: str) -> str:
    text = text.replace(
        "        limit = {\n"
        "            has_game_rule = { rule = arm_auto_research_intensity option = ARM_RELAXED }\n"
        "        }",
        "        limit = {\n"
        "            OR = {\n"
        "                has_game_rule = { rule = arm_auto_research_intensity option = ARM_REALISTIC }\n"
        "                has_game_rule = { rule = arm_auto_research_intensity option = ARM_HISTORICAL }\n"
        "            }\n"
        "        }",
    )
    replacements = {
        "set_variable = { arm_base_lag = 0.5 }": "set_variable = { arm_base_lag = __ARM_LAG_T5__ }",
        "set_variable = { arm_base_lag = 1.0 }": "set_variable = { arm_base_lag = __ARM_LAG_T4__ }",
        "set_variable = { arm_base_lag = 1.5 }": "set_variable = { arm_base_lag = __ARM_LAG_T3__ }",
        "set_variable = { arm_base_lag = 3.0 }": "set_variable = { arm_base_lag = __ARM_LAG_T2__ }",
        "set_variable = { arm_base_lag = __ARM_LAG_T5__ }": "set_variable = { arm_base_lag = 0.25 }",
        "set_variable = { arm_base_lag = __ARM_LAG_T4__ }": "set_variable = { arm_base_lag = 1.5 }",
        "set_variable = { arm_base_lag = __ARM_LAG_T3__ }": "set_variable = { arm_base_lag = 2.5 }",
        "set_variable = { arm_base_lag = __ARM_LAG_T2__ }": "set_variable = { arm_base_lag = 3.5 }",
        "subtract_from_variable = { arm_base_lag = 0.5 }": "subtract_from_variable = { arm_base_lag = 0.75 }",
        "has_game_rule = { rule = arm_auto_research_intensity option = ARM_AGGRESSIVE }": "has_game_rule = { rule = arm_auto_research_intensity option = ARM_ARCADE }",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def build_profile_dispatch(index: dict) -> str:
    profiles = [item["slug"] for item in index["generated_bundles"] if item["slug"] in PROFILE_OPTION_KEYS]

    lines = []
    lines.append("###############################################################################")
    lines.append("# arm_compat_profiles_generated.txt")
    lines.append("# Generated by Tools/build_builtin_compat_profiles.py")
    lines.append("###############################################################################")
    lines.append("")
    lines.append("arm_clear_auto_compat_profile_flags = {")
    lines.append("    clr_global_flag = arm_compat_auto_profile_detected")
    lines.append("    clr_global_flag = arm_compat_auto_doctrine_safe")
    for slug in PROFILE_ORDER:
        if slug in profiles:
            lines.append(f"    clr_global_flag = arm_compat_auto_{slug}")
    lines.append("}")
    lines.append("")
    lines.append("arm_auto_detect_compat_profile = {")
    lines.append("    arm_clear_auto_compat_profile_flags = yes")
    for slug in PROFILE_ORDER:
        if slug not in profiles:
            continue
        keyword = "if" if slug == PROFILE_ORDER[0] else "else_if"
        lines.append(f"    {keyword} = {{")
        lines.append("        limit = {")
        lines.extend(build_auto_detect_limit_lines(slug))
        lines.append("        }")
        lines.append("        set_global_flag = arm_compat_auto_profile_detected")
        lines.append(f"        set_global_flag = arm_compat_auto_{slug}")
        if slug in DOCTRINE_SAFE_PROFILES:
            lines.append("        set_global_flag = arm_compat_auto_doctrine_safe")
        lines.append("    }")
    lines.append("}")
    lines.append("")
    lines.append("arm_assign_power_tier_for_profile = {")
    for slug in PROFILE_ORDER:
        if slug not in profiles:
            continue
        keyword = "if" if slug == PROFILE_ORDER[0] else "else_if"
        lines.append(f"    {keyword} = {{")
        lines.append("        limit = {")
        lines.extend(build_profile_limit_lines(slug))
        lines.append("        }")
        lines.append(f"        arm_assign_power_tier_{slug} = yes")
        lines.append("    }")
    lines.append("    else = {")
    lines.append("        arm_assign_power_tier = yes")
    lines.append("    }")
    lines.append("}")
    lines.append("")
    lines.append("arm_grant_techs_for_profile = {")
    for slug in PROFILE_ORDER:
        if slug not in profiles:
            continue
        keyword = "if" if slug == PROFILE_ORDER[0] else "else_if"
        lines.append(f"    {keyword} = {{")
        lines.append("        limit = {")
        lines.extend(build_profile_limit_lines(slug))
        lines.append("        }")
        for effect_name in GRANT_ORDER:
            lines.append("        if = {")
            lines.append("            limit = {")
            lines.append("                check_variable = { var = arm_grant_counter value = arm_quarterly_cap compare = less_than }")
            lines.append("            }")
            lines.append(f"            {effect_name}_{slug} = yes")
            lines.append("        }")
        lines.append("    }")
    lines.append("    else = {")
    for effect_name in GRANT_ORDER:
        lines.append("        if = {")
        lines.append("            limit = {")
        lines.append("                check_variable = { var = arm_grant_counter value = arm_quarterly_cap compare = less_than }")
        lines.append("            }")
        lines.append(f"            {effect_name} = yes")
        lines.append("        }")
    lines.append("    }")
    lines.append("}")
    lines.append("")
    lines.append("arm_initialize_doctrine_paths_for_profile = {")
    lines.append("    if = {")
    lines.append("        limit = {")
    lines.append("            arm_doctrine_allowed = yes")
    lines.append("            OR = {")
    lines.append("                has_game_rule = { rule = arm_compat_profile option = ARM_COMPAT_VANILLA }")
    lines.append("                AND = {")
    lines.append("                    has_game_rule = { rule = arm_compat_profile option = ARM_COMPAT_AUTO }")
    lines.append("                    OR = {")
    lines.append("                        NOT = { has_global_flag = arm_compat_auto_profile_detected }")
    lines.append("                        has_global_flag = arm_compat_auto_doctrine_safe")
    lines.append("                    }")
    lines.append("                }")
    for slug in PROFILE_ORDER:
        if slug in profiles and slug in DOCTRINE_SAFE_PROFILES:
            lines.append(f"                has_game_rule = {{ rule = arm_compat_profile option = {PROFILE_OPTION_KEYS[slug]} }}")
    lines.append("            }")
    lines.append("        }")
    lines.append("        arm_initialize_doctrine_paths = yes")
    lines.append("    }")
    lines.append("}")
    lines.append("")
    lines.append("arm_grant_doctrines_for_profile = {")
    lines.append("    if = {")
    lines.append("        limit = {")
    lines.append("            arm_doctrine_allowed = yes")
    lines.append("            OR = {")
    lines.append("                has_game_rule = { rule = arm_compat_profile option = ARM_COMPAT_VANILLA }")
    lines.append("                AND = {")
    lines.append("                    has_game_rule = { rule = arm_compat_profile option = ARM_COMPAT_AUTO }")
    lines.append("                    OR = {")
    lines.append("                        NOT = { has_global_flag = arm_compat_auto_profile_detected }")
    lines.append("                        has_global_flag = arm_compat_auto_doctrine_safe")
    lines.append("                    }")
    lines.append("                }")
    for slug in PROFILE_ORDER:
        if slug in profiles and slug in DOCTRINE_SAFE_PROFILES:
            lines.append(f"                has_game_rule = {{ rule = arm_compat_profile option = {PROFILE_OPTION_KEYS[slug]} }}")
    lines.append("            }")
    lines.append("        }")
    lines.append("        arm_grant_doctrines = yes")
    lines.append("    }")
    lines.append("}")
    lines.append("")
    return "\n".join(lines) + "\n"


def main():
    if not INDEX_PATH.exists():
        raise SystemExit(f"Missing compat index: {INDEX_PATH}")

    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))

    for old_file in SCRIPTED_EFFECTS_DIR.glob("arm_compat_generated_*.txt"):
        old_file.unlink()
    dispatch_path = SCRIPTED_EFFECTS_DIR / "arm_compat_generated_dispatch.txt"
    if dispatch_path.exists():
        dispatch_path.unlink()

    tier_lines = []
    tier_lines.append("###############################################################################")
    tier_lines.append("# arm_compat_generated_tiers.txt")
    tier_lines.append("# Generated by Tools/build_builtin_compat_profiles.py")
    tier_lines.append("###############################################################################")
    tier_lines.append("")

    for item in index["generated_bundles"]:
        slug = item["slug"]
        bundle_root = COMPAT_ROOT / slug / "common" / "scripted_effects"
        techlist_path = bundle_root / "auto_research_techlist.txt"
        if not techlist_path.exists():
            continue

        tech_text = techlist_path.read_text(encoding="utf-8-sig")
        renamed_tech_text = rename_grant_effects(
            sanitize_runtime_effect_text(tech_text),
            slug,
        )
        output_tech_path = SCRIPTED_EFFECTS_DIR / f"arm_compat_generated_{slug}.txt"
        header = (
            "###############################################################################\n"
            f"# Builtin compatibility profile: {slug}\n"
            "# Generated by Tools/build_builtin_compat_profiles.py\n"
            "###############################################################################\n\n"
        )
        output_tech_path.write_text(header + renamed_tech_text, encoding="utf-8")

        eval_path = bundle_root / "arm_evaluation.txt"
        if eval_path.exists():
            eval_text = eval_path.read_text(encoding="utf-8-sig")
            tier_block = extract_top_level_block(eval_text, "arm_assign_power_tier")
            tier_block = normalize_generated_tier_block(tier_block)
            tier_lines.append(rename_tier_effect(tier_block, slug))
            tier_lines.append("")

    (SCRIPTED_EFFECTS_DIR / "arm_compat_generated_tiers.txt").write_text(
        "\n".join(tier_lines) + "\n",
        encoding="utf-8",
    )
    dispatch_path.write_text(build_profile_dispatch(index), encoding="utf-8")

    print("Builtin compatibility profiles written to common/scripted_effects")


if __name__ == "__main__":
    main()
