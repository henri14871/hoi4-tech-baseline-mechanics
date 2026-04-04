#!/usr/bin/env python3
"""
Tech Baseline Mechanics — Unified Compatibility Profile Tool
=========================================================

Single entrypoint for all compat profile operations:
  scan       — Read-only scan of a mod's tech tree
  generate   — Generate staging bundles for mod profiles
  build      — Compile staging bundles into runtime scripted effects
  rebuild    — Generate + build in one command
  list       — List known and generated profiles
  validate   — Validate generated profiles for correctness

Replaces the previous multi-file toolchain:
  tbm_tech_generator.py, generate_big_mod_compat.py,
  build_builtin_compat_profiles.py, manage_compat_profiles.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ============================================================================
# PATH CONSTANTS
# ============================================================================

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "Tools"
DEFAULT_HOI4_PATH = Path(r"E:\SteamLibrary\steamapps\common\Hearts of Iron IV")
DEFAULT_WORKSHOP_ROOT = Path(r"E:\SteamLibrary\steamapps\workshop\content\394360")
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "compat_generated"
CUSTOM_MAPPINGS_PATH = Path(__file__).resolve().parent / "custom_mappings.txt"
BASE_EVALUATION_PATH = REPO_ROOT / "common" / "scripted_effects" / "tbm_evaluation.txt"
SCRIPTED_EFFECTS_DIR = REPO_ROOT / "common" / "scripted_effects"
GAME_RULES_PATH = REPO_ROOT / "common" / "game_rules" / "tbm_game_rules.txt"
LOCALISATION_PATH = REPO_ROOT / "localisation" / "english" / "tbm_l_english.yml"


# ============================================================================
# CATEGORY TAG → BRANCH/CATEGORY MAPPING
# ============================================================================
# Priority order matters — first match wins. More specific tags before generic.

CATEGORY_MAP = {
    # ── Land / Tanks (most specific — BEFORE generic 'armor' and infantry) ──
    "cat_light_armor":          ("land", "light_tanks"),
    "cat_medium_armor":         ("land", "medium_tanks"),
    "cat_heavy_armor":          ("land", "heavy_tanks"),
    "cat_super_heavy_armor":    ("land", "heavy_tanks"),
    "cat_modern_armor":         ("land", "modern_tanks"),
    "armor":                    ("land", "tanks_generic"),

    # ── Land / Mechanised (BEFORE motorised) ──
    "cat_mechanized":           ("land", "mechanised"),
    "cat_mechanized_equipment": ("land", "mechanised"),
    "mechanized_equipment":     ("land", "mechanised"),

    # ── Land / Anti-Air & Anti-Tank (BEFORE artillery) ──
    "cat_anti_tank":            ("land", "anti_tank"),
    "cat_anti_air":             ("land", "anti_air"),
    "anti_air":                 ("land", "anti_air"),

    # ── Land / Artillery (after AA/AT) ──
    "artillery":                ("land", "artillery"),
    "cat_artillery":            ("land", "artillery"),
    "rocket_artillery":         ("land", "artillery"),

    # ── Land / Support (BEFORE motorised) ──
    "support_tech":             ("land", "support"),
    "hospital_tech":            ("land", "support"),
    "logistics_tech":           ("land", "support"),
    "signal_company_tech":      ("land", "support"),
    "recon_tech":               ("land", "support"),
    "engineer_tech":            ("land", "support"),
    "military_police_tech":     ("land", "support"),
    "maintenance_company_tech": ("land", "support"),
    "train_tech":               ("land", "support"),
    "night_vision":             ("land", "support"),

    # ── Land / Motorised (AFTER support) ──
    "motorized_equipment":      ("land", "motorised"),
    "motorized_tech":           ("land", "motorised"),

    # ── Land / Special Forces (mapped to infantry) ──
    "cat_special_forces_generic": ("land", "infantry"),
    "marine_tech":              ("land", "infantry"),
    "para_tech":                ("land", "infantry"),
    "mountaineers_tech":        ("land", "infantry"),

    # ── Land / Infantry (most generic land — LAST among land types) ──
    "infantry_weapons":         ("land", "infantry"),
    "infantry_tech":            ("land", "infantry"),

    # ── Air / Heavy Fighters (BEFORE generic fighter tags) ──
    "cat_heavy_fighter":        ("air", "heavy_fighters"),
    "heavy_fighter":            ("air", "heavy_fighters"),

    # ── Air / Fighters ──
    "light_fighter":            ("air", "fighters"),
    "cat_fighter":              ("air", "fighters"),

    # ── Air / Bombers (specific BEFORE generic) ──
    "cas_bomber":               ("air", "cas"),
    "cat_cas":                  ("air", "cas"),
    "cat_air_bombs":            ("air", "cas"),
    "cat_strategic_bomber":     ("air", "strategic_bombers"),
    "strategic_bomber":         ("air", "strategic_bombers"),
    "cat_tactical_bomber":      ("air", "tactical_bombers"),
    "tactical_bomber":          ("air", "tactical_bombers"),
    "naval_bomber":             ("air", "naval_bombers"),
    "cat_naval_bomber":         ("air", "naval_bombers"),
    "cat_maritime_patrol":      ("air", "naval_bombers"),
    "cat_scout_plane":          ("air", "fighters"),

    # ── Air / Transport ──
    "transport_planes_cat":     ("air", "transport"),
    "transport_plane_tech":     ("air", "transport"),

    # ── Air / Carrier variants (MIO tags from vanilla) ──
    "mio_cat_all_light_fighter_and_modules":  ("air", "fighters"),
    "mio_cat_all_naval_bomber_and_modules":   ("air", "naval_bombers"),
    "mio_cat_all_cas_and_modules":            ("air", "cas"),

    # ── Naval / Submarines (BEFORE destroyers) ──
    "sub_tech":                 ("naval", "submarines"),
    "ss_tech":                  ("naval", "submarines"),

    # ── Naval / Light ──
    "dd_tech":                  ("naval", "destroyers"),
    "cl_tech":                  ("naval", "light_cruisers"),

    # ── Naval / Heavy (specific BEFORE generic) ──
    "cv_tech":                  ("naval", "carriers"),
    "shbb_tech":                ("naval", "battleships"),
    "bb_tech":                  ("naval", "battleships"),
    "bc_tech":                  ("naval", "battleships"),
    "ca_tech":                  ("naval", "heavy_cruisers"),

    # ── Naval / Support ──
    "tp_tech":                  ("naval", "naval_support"),
    "naval_mines_tech":         ("naval", "naval_support"),
    "convoy_tech":              ("naval", "naval_support"),
    "mtg_transport":            ("naval", "naval_support"),

    # ── Industry / Radar (BEFORE generic electronics) ──
    "radar_tech":               ("industry_electronics", "radar"),

    # ── Industry / Electronics ──
    "electronics":              ("industry_electronics", "electronics"),
    "computing_tech":           ("industry_electronics", "electronics"),
    "encryption_tech":          ("industry_electronics", "electronics"),
    "decryption_tech":          ("industry_electronics", "electronics"),

    # ── Industry (generic — after radar/electronics) ──
    "industry":                 ("industry_electronics", "industry"),
    "construction_tech":        ("industry_electronics", "industry"),
    "concentrated_industry":    ("industry_electronics", "industry"),
    "dispersed_industry":       ("industry_electronics", "industry"),
    "synth_resources":          ("industry_electronics", "industry"),
    "cat_fortification":        ("industry_electronics", "industry"),

    # ── Nuclear / Rockets ──
    "nuclear":                  ("industry_electronics", "nuclear"),
    "nuclear_tech":             ("industry_electronics", "nuclear"),
    "rocketry":                 ("industry_electronics", "rockets"),
    "rocketry_tech":            ("industry_electronics", "rockets"),

    # ── Doctrines (specific path tags BEFORE generic doctrine tags) ──
    "cat_mobile_warfare":       ("doctrine", "land_doctrine"),
    "cat_superior_firepower":   ("doctrine", "land_doctrine"),
    "cat_grand_battle_plan":    ("doctrine", "land_doctrine"),
    "cat_mass_assault":         ("doctrine", "land_doctrine"),
    "cat_fleet_in_being":       ("doctrine", "naval_doctrine"),
    "cat_trade_interdiction":   ("doctrine", "naval_doctrine"),
    "cat_base_strike":          ("doctrine", "naval_doctrine"),
    "land_doctrine":            ("doctrine", "land_doctrine"),
    "naval_doctrine":           ("doctrine", "naval_doctrine"),
    "air_doctrine":             ("doctrine", "air_doctrine"),
}

CATEGORY_MIN_TIER = {
    "infantry":           "micro",
    "support":            "minor",
    "artillery":          "minor",
    "anti_air":           "minor",
    "anti_tank":          "minor",
    "industry":           "minor",
    "motorised":          "minor_industrial",
    "mechanised":         "regional_power",
    "light_tanks":        "regional_power",
    "medium_tanks":       "regional_power",
    "heavy_tanks":        "great_power",
    "modern_tanks":       "great_power",
    "tanks_generic":      "regional_power",
    "fighters":           "minor_industrial",
    "heavy_fighters":     "regional_power",
    "cas":                "minor_industrial",
    "tactical_bombers":   "regional_power",
    "strategic_bombers":  "great_power",
    "naval_bombers":      "regional_power",
    "transport":          "minor_industrial",
    "destroyers":         "minor_industrial",
    "submarines":         "minor_industrial",
    "light_cruisers":     "regional_power",
    "heavy_cruisers":     "regional_power",
    "battleships":        "great_power",
    "carriers":           "great_power",
    "naval_support":      "minor_industrial",
    "electronics":        "regional_power",
    "radar":              "regional_power",
    "nuclear":            "superpower",
    "rockets":            "superpower",
    "land_doctrine":      "minor_industrial",
    "naval_doctrine":     "minor_industrial",
    "air_doctrine":       "minor_industrial",
}

CATEGORY_MIN_BRANCH_SCORE = {
    "infantry":           0,
    "support":            15,
    "artillery":          15,
    "anti_air":           15,
    "anti_tank":          15,
    "industry":           15,
    "motorised":          25,
    "mechanised":         45,
    "light_tanks":        35,
    "medium_tanks":       45,
    "heavy_tanks":        70,
    "modern_tanks":       70,
    "tanks_generic":      35,
    "fighters":           25,
    "heavy_fighters":     45,
    "cas":                25,
    "tactical_bombers":   45,
    "strategic_bombers":  70,
    "naval_bombers":      35,
    "transport":          20,
    "destroyers":         25,
    "submarines":         25,
    "light_cruisers":     45,
    "heavy_cruisers":     45,
    "battleships":        70,
    "carriers":           70,
    "naval_support":      20,
    "electronics":        35,
    "radar":              35,
    "nuclear":            85,
    "rockets":            85,
    "land_doctrine":      25,
    "naval_doctrine":     25,
    "air_doctrine":       25,
}


# ============================================================================
# DLC FILE DETECTION
# ============================================================================

DLC_FILE_MAP = {
    "mtg_naval.txt":            "Man the Guns",
    "mtg_naval_support.txt":    "Man the Guns",
    "nsb_armor.txt":            "No Step Back",
    "bba_air_techs.txt":        "By Blood Alone",
}

DLC_TECH_OVERRIDES = {
    "sp_refined_pykrete": "Gotterdammerung",
    "sp_ice_composite_runawayas": "Gotterdammerung",
}

# Vanilla tech folders that are hidden when a specific DLC is active.
# Derived from common/technology_tags/00_technology.txt in the base game.
FOLDER_DLC_HIDDEN_MAP = {
    "armour_folder": "No Step Back",
    "air_techs_folder": "By Blood Alone",
    "naval_folder": "Man the Guns",
}


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class TechDef:
    """Parsed technology definition."""
    tech_id: str
    start_year: int = 1936
    categories: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)
    branch: str = "unknown"
    category: str = "unknown"
    min_tier: str = "micro"
    min_branch_score: int = 0
    is_doctrine: bool = False
    is_xp_gated: bool = False
    source_file: str = ""
    source_mod: str = "vanilla"
    dependency_depth: int = 0
    dlc_required: str = ""
    dlc_hidden_by: str = ""
    xor_techs: list = field(default_factory=list)


# ============================================================================
# OUTPUT MAPPING CONSTANTS
# ============================================================================

TIER_ORDER = ["micro", "minor", "minor_industrial", "regional_power", "great_power", "superpower"]

TARGET_YEAR_VAR_BY_BRANCH = {
    "land": "tbm_target_year_land",
    "air": "tbm_target_year_air",
    "naval": "tbm_target_year_naval",
    "industry_electronics": "tbm_target_year_industry",
}

COMPETENCE_VAR_BY_BRANCH = {
    "land": "tbm_land_competence",
    "air": "tbm_air_competence",
    "naval": "tbm_naval_competence",
    "industry_electronics": "tbm_industry_competence",
}

CATEGORY_FLAG_BY_CATEGORY = {
    "infantry": "tbm_cat_infantry",
    "support": "tbm_cat_support",
    "artillery": "tbm_cat_artillery",
    "anti_air": "tbm_cat_anti_air",
    "anti_tank": "tbm_cat_anti_tank",
    "industry": "tbm_cat_industry",
    "electronics": "tbm_cat_electronics",
    "radar": "tbm_cat_radar",
    "motorised": "tbm_cat_motorised",
    "mechanised": "tbm_cat_mechanised",
    "light_tanks": "tbm_cat_light_tanks",
    "medium_tanks": "tbm_cat_medium_tanks",
    "heavy_tanks": "tbm_cat_heavy_tanks",
    "modern_tanks": "tbm_cat_modern_tanks",
    "tanks_generic": "tbm_cat_tanks_generic",
    "fighters": "tbm_cat_fighters",
    "heavy_fighters": "tbm_cat_heavy_fighters",
    "cas": "tbm_cat_cas",
    "tactical_bombers": "tbm_cat_tactical_bombers",
    "strategic_bombers": "tbm_cat_strategic_bombers",
    "naval_bombers": "tbm_cat_naval_bombers",
    "transport": "tbm_cat_transport",
    "submarines": "tbm_cat_submarines",
    "destroyers": "tbm_cat_destroyers",
    "light_cruisers": "tbm_cat_light_cruisers",
    "heavy_cruisers": "tbm_cat_heavy_cruisers",
    "battleships": "tbm_cat_battleships",
    "carriers": "tbm_cat_carriers",
    "naval_support": "tbm_cat_naval_support",
    "nuclear": "tbm_cat_nuclear",
    "rockets": "tbm_cat_rockets",
}

KNOWN_XOR_PAIRS = [
    ("concentrated_industry", "dispersed_industry"),
    ("concentrated_industry2", "dispersed_industry2"),
    ("concentrated_industry3", "dispersed_industry3"),
    ("concentrated_industry4", "dispersed_industry4"),
    ("concentrated_industry5", "dispersed_industry5"),
]

ADVANCED_TECH_CATEGORIES = {"nuclear", "rockets"}


# ============================================================================
# PRESETS
# ============================================================================

PRESETS = {
    "kaiserreich": {
        "description": "Kaiserreich — adjusted for alternate WW1 aftermath economy",
        "tier_thresholds": {
            "superpower": 250,
            "great_power": 170,
            "regional_power": 100,
            "minor_industrial": 50,
            "minor": 22,
        },
    },
    "millennium_dawn": {
        "description": "Millennium Dawn — modern-era factory and resource scales",
        "tier_thresholds": {
            "superpower": 400,
            "great_power": 280,
            "regional_power": 160,
            "minor_industrial": 80,
            "minor": 35,
        },
    },
    "road_to_56": {
        "description": "Road to 56 — extended tech trees with more techs per branch",
        "tier_thresholds": {
            "superpower": 220,
            "great_power": 150,
            "regional_power": 90,
            "minor_industrial": 45,
            "minor": 20,
        },
    },
    "great_war": {
        "description": "The Great War — WW1 era with earlier start dates",
        "tier_thresholds": {
            "superpower": 180,
            "great_power": 120,
            "regional_power": 70,
            "minor_industrial": 35,
            "minor": 15,
        },
    },
}


# ============================================================================
# MAJOR MOD PROFILES
# ============================================================================

MAJOR_MOD_PROFILES = [
    {
        "workshop_id": "1137372539",
        "slug": "blackice",
        "display_name": "BlackICE Historical Immersion Mod",
        "mode": "overhaul",
        "preset": {
            "name": "blackice",
            "description": "BlackICE - denser WW2 industrial and doctrine scale",
            "tier_thresholds": {
                "superpower": 240, "great_power": 165,
                "regional_power": 95, "minor_industrial": 48, "minor": 21,
            },
        },
    },
    {
        "workshop_id": "1458561226",
        "slug": "cold_war_iron_curtain",
        "display_name": "Cold War Iron Curtain: A World Divided",
        "mode": "overhaul",
        "preset": {
            "name": "cold_war_iron_curtain",
            "description": "Cold War Iron Curtain - modern-era global economy scale",
            "tier_thresholds": {
                "superpower": 450, "great_power": 310,
                "regional_power": 180, "minor_industrial": 90, "minor": 40,
            },
        },
    },
    {
        "workshop_id": "1521695605",
        "slug": "kaiserreich",
        "display_name": "Kaiserreich",
        "mode": "overhaul",
        "preset_name": "kaiserreich",
    },
    {
        "workshop_id": "1532883122",
        "slug": "endsieg",
        "display_name": "EndsiegDEV",
        "mode": "overhaul",
        "preset": {
            "name": "endsieg",
            "description": "Endsieg - late-war scenario with roughly vanilla industrial scale",
            "tier_thresholds": {
                "superpower": 220, "great_power": 150,
                "regional_power": 90, "minor_industrial": 45, "minor": 20,
            },
        },
    },
    {
        "workshop_id": "1778255798",
        "slug": "extended_tech_tree_1960",
        "display_name": "Extended Tech Tree 1960",
        "mode": "expansion",
        "preset": {
            "name": "extended_tech_tree_1960",
            "description": "Extended Tech Tree 1960 - vanilla-scale economy with longer research tails",
            "tier_thresholds": {
                "superpower": 220, "great_power": 150,
                "regional_power": 90, "minor_industrial": 45, "minor": 20,
            },
        },
    },
    {
        "workshop_id": "1827273767",
        "slug": "novum_vexillum",
        "display_name": "Novum Vexillum",
        "mode": "overhaul",
        "preset": {
            "name": "novum_vexillum",
            "description": "Novum Vexillum - modern-era economy and force structure",
            "tier_thresholds": {
                "superpower": 380, "great_power": 260,
                "regional_power": 150, "minor_industrial": 75, "minor": 33,
            },
        },
    },
    {
        "workshop_id": "2026448968",
        "slug": "rise_of_nations",
        "display_name": "Rise of Nations",
        "mode": "overhaul",
        "preset": {
            "name": "rise_of_nations",
            "description": "Rise of Nations - modern-era economy with large branch breadth",
            "tier_thresholds": {
                "superpower": 400, "great_power": 280,
                "regional_power": 160, "minor_industrial": 80, "minor": 35,
            },
        },
    },
    {
        "workshop_id": "2076426030",
        "slug": "kaiserredux",
        "display_name": "KaiserreduX",
        "mode": "overhaul",
        "preset": {
            "name": "kaiserredux",
            "description": "Kaiserredux - Kaiserreich-scale economy with more content inflation",
            "tier_thresholds": {
                "superpower": 255, "great_power": 175,
                "regional_power": 102, "minor_industrial": 50, "minor": 22,
            },
        },
    },
    {
        "workshop_id": "2438003901",
        "slug": "the_new_order",
        "display_name": "The New Order: Last Days of Europe",
        "mode": "overhaul",
        "preset": {
            "name": "the_new_order",
            "description": "The New Order - 1960s start with larger baseline economies",
            "tier_thresholds": {
                "superpower": 300, "great_power": 205,
                "regional_power": 120, "minor_industrial": 60, "minor": 25,
            },
        },
    },
    {
        "workshop_id": "2777392649",
        "slug": "millennium_dawn",
        "display_name": "Millennium Dawn: A Modern Day Mod",
        "mode": "overhaul",
        "preset_name": "millennium_dawn",
    },
    {
        "workshop_id": "3350890356",
        "slug": "the_fire_rises",
        "display_name": "The Fire Rises",
        "mode": "overhaul",
        "preset": {
            "name": "the_fire_rises",
            "description": "The Fire Rises - near-modern economy and technology scale",
            "tier_thresholds": {
                "superpower": 420, "great_power": 290,
                "regional_power": 170, "minor_industrial": 85, "minor": 35,
            },
        },
    },
    {
        "workshop_id": "3365515312",
        "slug": "great_war_redux",
        "display_name": "The Great War Redux - 1.17.*",
        "mode": "overhaul",
        "preset": {
            "name": "great_war_redux",
            "description": "The Great War Redux - WW1 economy with expanded content",
            "tier_thresholds": {
                "superpower": 185, "great_power": 125,
                "regional_power": 72, "minor_industrial": 36, "minor": 15,
            },
        },
    },
    {
        "workshop_id": "699709023",
        "slug": "great_war",
        "display_name": "Hearts of Iron IV: The Great War",
        "mode": "overhaul",
        "preset_name": "great_war",
    },
    {
        "workshop_id": "820260968",
        "slug": "road_to_56",
        "display_name": "The Road to 56",
        "mode": "expansion",
        "preset_name": "road_to_56",
    },
]


# ============================================================================
# BUILD / COMPILE CONSTANTS
# ============================================================================

PROFILE_ORDER = [
    "blackice", "cold_war_iron_curtain", "kaiserreich", "endsieg",
    "extended_tech_tree_1960", "novum_vexillum", "rise_of_nations",
    "kaiserredux", "the_new_order", "millennium_dawn", "the_fire_rises",
    "great_war_redux", "great_war", "road_to_56",
]

PROFILE_OPTION_KEYS = {
    "blackice": "TBM_COMPAT_BLACKICE",
    "cold_war_iron_curtain": "TBM_COMPAT_CWIC",
    "kaiserreich": "TBM_COMPAT_KAISERREICH",
    "endsieg": "TBM_COMPAT_ENDSIEG",
    "extended_tech_tree_1960": "TBM_COMPAT_ETT1960",
    "novum_vexillum": "TBM_COMPAT_NOVUM_VEXILLUM",
    "rise_of_nations": "TBM_COMPAT_RISE_OF_NATIONS",
    "kaiserredux": "TBM_COMPAT_KAISERREDUX",
    "the_new_order": "TBM_COMPAT_TNO",
    "millennium_dawn": "TBM_COMPAT_MILLENNIUM_DAWN",
    "the_fire_rises": "TBM_COMPAT_TFR",
    "great_war_redux": "TBM_COMPAT_GREAT_WAR_REDUX",
    "great_war": "TBM_COMPAT_GREAT_WAR",
    "road_to_56": "TBM_COMPAT_ROAD_TO_56",
}

# Short display names for localization (derived from profile display_name or overridden)
PROFILE_SHORT_NAMES = {
    "blackice": "BlackICE",
    "cold_war_iron_curtain": "Cold War Iron Curtain",
    "kaiserreich": "Kaiserreich",
    "endsieg": "Endsieg",
    "extended_tech_tree_1960": "Extended Tech Tree 1960",
    "novum_vexillum": "Novum Vexillum",
    "rise_of_nations": "Rise of Nations",
    "kaiserredux": "Kaiserredux",
    "the_new_order": "The New Order",
    "millennium_dawn": "Millennium Dawn",
    "the_fire_rises": "The Fire Rises",
    "great_war_redux": "Great War Redux",
    "great_war": "The Great War",
    "road_to_56": "Road to 56",
}

AUTO_DETECT_LIMITS = {
    "blackice": [
        "country_exists = BMP", "country_exists = EHA", "country_exists = HAT",
        "country_exists = PGR", "country_exists = SCC", "country_exists = SDC",
        "country_exists = SKC", "country_exists = XIA", "country_exists = YUT",
        "country_exists = ZXL",
    ],
    "cold_war_iron_curtain": [
        "country_exists = BAD", "country_exists = BAV", "country_exists = BCP",
        "country_exists = BCR", "country_exists = BTG", "country_exists = CVD",
        "country_exists = DOC", "country_exists = DRY", "country_exists = FNL",
        "country_exists = FUL", "country_exists = HOK", "country_exists = INO",
        "country_exists = KAS", "country_exists = KAY", "country_exists = KMP",
        "country_exists = KPA", "country_exists = LOS", "country_exists = MLA",
        "country_exists = MNL", "country_exists = NLF", "country_exists = PDG",
        "country_exists = SGP", "country_exists = SMI", "country_exists = SMK",
        "country_exists = SVI", "country_exists = SWK", "country_exists = TNG",
        "country_exists = TOA", "country_exists = TRS", "country_exists = UNS",
    ],
    "kaiserreich": [
        "country_exists = HND", "country_exists = HNN", "country_exists = IMP",
        "country_exists = KUM", "country_exists = SHD", "country_exists = SPA",
        "country_exists = WIF",
    ],
    "endsieg": [
        "country_exists = ANA", "country_exists = CBU", "country_exists = CNT",
        "country_exists = EFR", "country_exists = EN3", "country_exists = FNN",
        "country_exists = FNR", "country_exists = HEJ", "country_exists = HEL",
        "country_exists = INU", "country_exists = KIT", "country_exists = LOK",
        "country_exists = NEJ", "country_exists = NOK", "country_exists = RCH",
        "country_exists = RKK", "country_exists = RKO", "country_exists = RKU",
        "country_exists = SOK", "country_exists = TSS", "country_exists = UBD",
        "country_exists = VIL", "country_exists = WUR", "country_exists = ZAP",
    ],
    # No safe core auto-detect probe. The standalone bundle overrides the
    # generic core effects directly when loaded after TBM.
    "extended_tech_tree_1960": [],
    "novum_vexillum": [
        "country_exists = AND", "country_exists = BAS", "country_exists = ETI",
        "country_exists = FAI", "country_exists = FSM", "country_exists = GRN",
        "country_exists = HKN", "country_exists = JVA", "country_exists = KRN",
        "country_exists = MCU", "country_exists = NAX", "country_exists = RCK",
        "country_exists = RRA", "country_exists = SKN", "country_exists = SPF",
        "country_exists = SWZ",
    ],
    "rise_of_nations": [
        "country_exists = ACR", "country_exists = ALK", "country_exists = ANH",
        "country_exists = ART", "country_exists = ARZ", "country_exists = BOX",
        "country_exists = CBV", "country_exists = CIN", "country_exists = CZR",
        "country_exists = DEL", "country_exists = DON", "country_exists = DPK",
        "country_exists = ETR", "country_exists = EUR", "country_exists = FEN",
        "country_exists = GRC", "country_exists = GUK", "country_exists = HAW",
        "country_exists = KNS", "country_exists = LNA", "country_exists = LON",
        "country_exists = MCR", "country_exists = MKH", "country_exists = MTA",
        "country_exists = NMX", "country_exists = OFR", "country_exists = OKL",
        "country_exists = OTT", "country_exists = PUE", "country_exists = ROK",
    ],
    "kaiserredux": [
        "country_exists = ALO", "country_exists = BHC", "country_exists = CAF",
        "country_exists = CIV", "country_exists = DEH", "country_exists = DKB",
        "country_exists = KIK", "country_exists = MTR", "country_exists = NSW",
        "country_exists = SKM", "country_exists = SQI", "country_exists = TRM",
    ],
    "the_new_order": [
        "country_exists = AAA", "country_exists = AAB", "country_exists = AAC",
        "country_exists = AAF", "country_exists = AAG", "country_exists = AAJ",
        "country_exists = AAN", "country_exists = AAO", "country_exists = ADN",
        "country_exists = AYR", "country_exists = AZH", "country_exists = AZW",
        "country_exists = BKF", "country_exists = BKR", "country_exists = BKU",
        "country_exists = BRG", "country_exists = BRY", "country_exists = CAO",
        "country_exists = CAU", "country_exists = CHT", "country_exists = CLC",
        "country_exists = CLL", "country_exists = CME", "country_exists = CYL",
        "country_exists = DRL", "country_exists = EWE", "country_exists = FAR",
        "country_exists = FAV", "country_exists = FFR", "country_exists = FRS",
    ],
    "millennium_dawn": [
        "country_exists = ACE", "country_exists = ADO", "country_exists = AGL",
        "country_exists = BEN", "country_exists = BFA", "country_exists = CBD",
        "country_exists = CDI", "country_exists = CNG", "country_exists = DMI",
        "country_exists = DRC", "country_exists = EGU", "country_exists = FYR",
        "country_exists = GAH", "country_exists = GRA", "country_exists = GUB",
        "country_exists = HAM", "country_exists = HKG", "country_exists = IEK",
        "country_exists = LUR", "country_exists = MAY", "country_exists = MIC",
        "country_exists = MLV", "country_exists = MOZ", "country_exists = NAM",
        "country_exists = NIG", "country_exists = NKO", "country_exists = NKR",
        "country_exists = NPM", "country_exists = PAU", "country_exists = PUK",
    ],
    "the_fire_rises": [
        "country_exists = AAS", "country_exists = BRS", "country_exists = CNF",
        "country_exists = CPC", "country_exists = DPR", "country_exists = HOU",
        "country_exists = HRL", "country_exists = HTS", "country_exists = KKP",
        "country_exists = KLA", "country_exists = KNU", "country_exists = MND",
        "country_exists = MOA", "country_exists = PLD", "country_exists = SHB",
        "country_exists = SSA", "country_exists = WAT", "country_exists = YAM",
    ],
    "great_war_redux": [
        "country_exists = ALM", "country_exists = ARB", "country_exists = BID",
        "country_exists = CAP", "country_exists = CER", "country_exists = DAR",
        "country_exists = EPR", "country_exists = FUJ", "country_exists = GLD",
        "country_exists = HBY", "country_exists = JOH", "country_exists = KED",
        "country_exists = KEL", "country_exists = KUT", "country_exists = MJT",
        "country_exists = MSC", "country_exists = NAJ", "country_exists = NAT",
        "country_exists = ORA", "country_exists = PLS", "country_exists = RIA",
        "country_exists = RWL", "country_exists = SMS", "country_exists = TRG",
        "country_exists = WTH", "country_exists = ZAN",
    ],
    "great_war": [
        "country_exists = ASR", "country_exists = BAY", "country_exists = CKK",
        "country_exists = CPM", "country_exists = FEC", "country_exists = TUK",
        "country_exists = ZHC",
    ],
    "road_to_56": [
        "country_exists = GDC", "country_exists = HBC", "country_exists = KHM",
        "country_exists = MPL", "country_exists = SND", "country_exists = XIC",
    ],
}

DOCTRINE_SAFE_PROFILES = {
    "kaiserreich", "kaiserredux", "endsieg",
    "extended_tech_tree_1960", "road_to_56",
}

GRANT_ORDER_BY_BRANCH = {
    "land": [
        "tbm_grant_land_infantry", "tbm_grant_land_support",
        "tbm_grant_land_artillery", "tbm_grant_land_anti_air",
        "tbm_grant_land_anti_tank", "tbm_grant_land_motorised",
        "tbm_grant_land_mechanised", "tbm_grant_land_light_tanks",
        "tbm_grant_land_medium_tanks", "tbm_grant_land_heavy_tanks",
        "tbm_grant_land_modern_tanks", "tbm_grant_land_tanks_generic",
    ],
    "air": [
        "tbm_grant_air_fighters", "tbm_grant_air_cas",
        "tbm_grant_air_heavy_fighters", "tbm_grant_air_tactical_bombers",
        "tbm_grant_air_strategic_bombers", "tbm_grant_air_naval_bombers",
        "tbm_grant_air_transport",
    ],
    "naval": [
        "tbm_grant_naval_submarines", "tbm_grant_naval_destroyers",
        "tbm_grant_naval_light_cruisers", "tbm_grant_naval_heavy_cruisers",
        "tbm_grant_naval_battleships", "tbm_grant_naval_carriers",
        "tbm_grant_naval_naval_support",
    ],
    "industry": [
        "tbm_grant_industry_electronics_industry",
        "tbm_grant_industry_electronics_electronics",
        "tbm_grant_industry_electronics_radar",
        "tbm_grant_industry_electronics_nuclear",
        "tbm_grant_industry_electronics_rockets",
    ],
}

BRANCH_ORDER = ["land", "air", "naval", "industry"]

CHECK_COMPARE_MAP = {
    ">": "greater_than",
    ">=": "greater_than_or_equals",
    "<": "less_than",
    "<=": "less_than_or_equals",
    "=": "equals",
}

EXPECTED_EFFECTS = [
    ("land", "infantry"), ("land", "support"), ("land", "artillery"),
    ("land", "anti_air"), ("land", "anti_tank"),
    ("land", "motorised"), ("land", "mechanised"),
    ("land", "light_tanks"), ("land", "medium_tanks"),
    ("land", "heavy_tanks"), ("land", "modern_tanks"),
    ("land", "tanks_generic"),
    ("air", "fighters"), ("air", "heavy_fighters"), ("air", "cas"),
    ("air", "tactical_bombers"), ("air", "strategic_bombers"),
    ("air", "naval_bombers"), ("air", "transport"),
    ("naval", "destroyers"), ("naval", "submarines"),
    ("naval", "light_cruisers"), ("naval", "heavy_cruisers"),
    ("naval", "battleships"), ("naval", "carriers"),
    ("naval", "naval_support"),
    ("industry_electronics", "industry"), ("industry_electronics", "electronics"),
    ("industry_electronics", "radar"),
    ("industry_electronics", "nuclear"), ("industry_electronics", "rockets"),
]


# ============================================================================
# CLAUSEWITZ PARSER
# ============================================================================

def strip_comments(text: str) -> str:
    """Remove # comments from Clausewitz text (but not inside quotes)."""
    result = []
    in_quote = False
    i = 0
    while i < len(text):
        c = text[i]
        if c == '"':
            in_quote = not in_quote
            result.append(c)
        elif c == '#' and not in_quote:
            while i < len(text) and text[i] != '\n':
                i += 1
            continue
        else:
            result.append(c)
        i += 1
    return ''.join(result)


def parse_tech_files(tech_dir: Path, mod_name: str = "vanilla", verbose: bool = False) -> list:
    """Parse all .txt files in a technologies directory. Returns list of TechDef."""
    techs = []
    if not tech_dir.exists():
        if verbose:
            print(f"  [SKIP] Directory not found: {tech_dir}")
        return techs

    for filepath in sorted(tech_dir.glob("*.txt")):
        if verbose:
            print(f"  [READ] {filepath.name}")
        try:
            raw = filepath.read_text(encoding='utf-8-sig', errors='replace')
        except Exception as e:
            print(f"  [ERROR] Could not read {filepath}: {e}")
            continue

        cleaned = strip_comments(raw)
        file_techs = extract_techs_from_text(cleaned, str(filepath), mod_name, verbose)

        dlc_name = DLC_FILE_MAP.get(filepath.name.lower(), "")
        if dlc_name:
            for t in file_techs:
                t.dlc_required = DLC_TECH_OVERRIDES.get(t.tech_id, dlc_name)

        techs.extend(file_techs)
    return techs


def extract_techs_from_text(text: str, source_file: str, mod_name: str, verbose: bool) -> list:
    """Extract tech definitions from cleaned Clausewitz text."""
    techs = []
    pos = 0
    length = len(text)

    while pos < length:
        while pos < length and text[pos] in ' \t\n\r':
            pos += 1
        if pos >= length:
            break

        id_start = pos
        while pos < length and text[pos] not in ' \t\n\r={}':
            pos += 1
        identifier = text[id_start:pos].strip()
        if not identifier:
            pos += 1
            continue

        while pos < length and text[pos] in ' \t\n\r':
            pos += 1
        if pos >= length:
            break
        if text[pos] != '=':
            pos += 1
            continue
        pos += 1

        while pos < length and text[pos] in ' \t\n\r':
            pos += 1
        if pos >= length:
            break
        if text[pos] != '{':
            while pos < length and text[pos] not in '\n\r':
                pos += 1
            continue

        brace_start = pos
        depth = 0
        while pos < length:
            if text[pos] == '{':
                depth += 1
            elif text[pos] == '}':
                depth -= 1
                if depth == 0:
                    pos += 1
                    break
            pos += 1

        block_content = text[brace_start:pos]

        if identifier in ('technologies', 'if', 'else', 'else_if'):
            inner_content = block_content[1:-1] if len(block_content) > 2 else ''
            inner_techs = extract_techs_from_text(inner_content, source_file, mod_name, verbose)
            techs.extend(inner_techs)
            continue

        if is_tech_block(block_content):
            tech = parse_single_tech(identifier, block_content, source_file, mod_name)
            if tech:
                techs.append(tech)
                if verbose:
                    print(f"    [TECH] {tech.tech_id} | year={tech.start_year} | "
                          f"branch={tech.branch} | cat={tech.category}")
    return techs


def is_tech_block(block: str) -> bool:
    """Heuristic: does this block look like a technology definition?"""
    indicators = [
        'research_cost', 'categories', 'enable_equipments',
        'enable_equipment_modules', 'enable_subunits', 'start_year',
        'folder', 'path',
    ]
    block_lower = block.lower()
    return any(ind in block_lower for ind in indicators)


def parse_single_tech(tech_id: str, block: str, source_file: str, mod_name: str) -> Optional[TechDef]:
    """Parse a single technology block into a TechDef."""
    skip_ids = {'technologies', 'if', 'else', 'limit', 'OR', 'AND', 'NOT',
                'has_dlc', 'folder', 'doctrine', 'sub_technologies'}
    if tech_id in skip_ids:
        return None
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', tech_id):
        return None

    tech = TechDef(tech_id=tech_id, source_file=source_file, source_mod=mod_name)

    year_match = re.search(r'start_year\s*=\s*(\d{4})', block)
    if year_match:
        tech.start_year = int(year_match.group(1))

    cat_match = re.search(r'categories\s*=\s*\{([^}]*)\}', block)
    if cat_match:
        cats = cat_match.group(1).split()
        tech.categories = [c.strip() for c in cats if c.strip()]

    dep_match = re.search(r'dependencies\s*=\s*\{([^}]*)\}', block)
    if dep_match:
        deps = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\d+', dep_match.group(1))
        tech.dependencies = deps

    xor_match = re.search(r'XOR\s*=\s*\{([^}]*)\}', block)
    if xor_match:
        xor_ids = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', xor_match.group(1))
        tech.xor_techs = [x for x in xor_ids if x != tech_id]

    if 'xp_research_type' in block or 'xp_cost' in block:
        tech.is_xp_gated = True

    if any(cat in tech.categories for cat in
           ['land_doctrine', 'naval_doctrine', 'air_doctrine',
            'cat_mobile_warfare', 'cat_superior_firepower',
            'cat_grand_battle_plan', 'cat_mass_assault',
            'cat_fleet_in_being', 'cat_trade_interdiction',
            'cat_base_strike']):
        tech.is_doctrine = True

    # Parse allow_branch for DLC gating (per-tech level).
    # Negative: allow_branch = { NOT = { has_dlc = "X" } } → hidden when X active
    ab_neg = re.search(
        r'allow_branch\s*=\s*\{[^}]*NOT\s*=\s*\{[^}]*has_dlc\s*=\s*"([^"]+)"',
        block)
    if ab_neg:
        tech.dlc_hidden_by = ab_neg.group(1)
    else:
        # Positive: allow_branch = { has_dlc = "X" } → requires X
        ab_pos = re.search(
            r'allow_branch\s*=\s*\{[^}]*has_dlc\s*=\s*"([^"]+)"', block)
        if ab_pos and not tech.dlc_required:
            tech.dlc_required = ab_pos.group(1)

    # Parse folder assignments for folder-level DLC hiding.
    if not tech.dlc_hidden_by:
        folder_matches = re.findall(
            r'folder\s*=\s*\{[^}]*name\s*=\s*(\w+)', block)
        for folder_name in folder_matches:
            if folder_name in FOLDER_DLC_HIDDEN_MAP:
                tech.dlc_hidden_by = FOLDER_DLC_HIDDEN_MAP[folder_name]
                break

    map_tech_to_branch(tech)
    return tech


def map_tech_to_branch(tech: TechDef):
    """Map a tech's category tags to a TBM branch and category."""
    cat_set = set(tech.categories)

    if "ca_tech" in cat_set:
        if "mio_cat_tech_all_screen_ship_and_modules" in cat_set:
            tech.branch, tech.category = "naval", "light_cruisers"
            tech.min_tier = CATEGORY_MIN_TIER.get(tech.category, "micro")
            tech.min_branch_score = CATEGORY_MIN_BRANCH_SCORE.get(tech.category, 0)
            return
        if "mio_cat_tech_all_capital_ship_and_modules" in cat_set:
            tech.branch, tech.category = "naval", "heavy_cruisers"
            tech.min_tier = CATEGORY_MIN_TIER.get(tech.category, "micro")
            tech.min_branch_score = CATEGORY_MIN_BRANCH_SCORE.get(tech.category, 0)
            return

    if tech.tech_id in {"main_battle_tank", "main_battle_tank_chassis"}:
        tech.branch, tech.category = "land", "modern_tanks"
        tech.min_tier = CATEGORY_MIN_TIER.get(tech.category, "micro")
        tech.min_branch_score = CATEGORY_MIN_BRANCH_SCORE.get(tech.category, 0)
        return

    for map_tag, (branch, category) in CATEGORY_MAP.items():
        if map_tag in cat_set:
            tech.branch = branch
            tech.category = category
            tech.min_tier = CATEGORY_MIN_TIER.get(category, "micro")
            tech.min_branch_score = CATEGORY_MIN_BRANCH_SCORE.get(category, 0)
            return

    SKIP_TAGS = {'naval_air', 'naval_equipment', 'air_equipment', 'light_air',
                 'medium_air', 'heavy_air', 'jet_technology', 'plane_modules_tech'}

    for cat_tag in tech.categories:
        if cat_tag.lower() in SKIP_TAGS:
            continue
        cat_lower = cat_tag.lower()

        if any(kw in cat_lower for kw in ['infantry', 'rifle', 'small_arms']):
            tech.branch, tech.category = "land", "infantry"
        elif any(kw in cat_lower for kw in ['support', 'engineer', 'recon', 'signal', 'logistics', 'hospital', 'maintenance', 'military_police']):
            tech.branch, tech.category = "land", "support"
        elif any(kw in cat_lower for kw in ['anti_air', 'antiair', 'aa_']):
            tech.branch, tech.category = "land", "anti_air"
        elif any(kw in cat_lower for kw in ['anti_tank', 'antitank', 'at_']):
            tech.branch, tech.category = "land", "anti_tank"
        elif any(kw in cat_lower for kw in ['mechanized', 'mechanised']):
            tech.branch, tech.category = "land", "mechanised"
        elif any(kw in cat_lower for kw in ['motorized', 'motorised']):
            tech.branch, tech.category = "land", "motorised"
        elif any(kw in cat_lower for kw in ['artillery', 'howitzer']):
            tech.branch, tech.category = "land", "artillery"
        elif any(kw in cat_lower for kw in ['armor', 'armour', 'tank']):
            tech.branch, tech.category = "land", "tanks_generic"
        elif any(kw in cat_lower for kw in ['fighter', 'interceptor']):
            tech.branch, tech.category = "air", "fighters"
        elif any(kw in cat_lower for kw in ['bomber']):
            tech.branch, tech.category = "air", "tactical_bombers"
        elif any(kw in cat_lower for kw in ['destroyer']):
            tech.branch, tech.category = "naval", "destroyers"
        elif any(kw in cat_lower for kw in ['cruiser']):
            tech.branch, tech.category = "naval", "heavy_cruisers"
        elif any(kw in cat_lower for kw in ['submarine', 'sub_tech']):
            tech.branch, tech.category = "naval", "submarines"
        elif any(kw in cat_lower for kw in ['battleship', 'capital_ship']):
            tech.branch, tech.category = "naval", "battleships"
        elif any(kw in cat_lower for kw in ['carrier']):
            tech.branch, tech.category = "naval", "carriers"
        elif any(kw in cat_lower for kw in ['ship', 'naval']):
            tech.branch, tech.category = "naval", "naval_support"
        elif any(kw in cat_lower for kw in ['industry', 'construction', 'production']):
            tech.branch, tech.category = "industry_electronics", "industry"
        elif any(kw in cat_lower for kw in ['electronic', 'radar', 'computing']):
            tech.branch, tech.category = "industry_electronics", "electronics"
        elif any(kw in cat_lower for kw in ['nuclear', 'atomic']):
            tech.branch, tech.category = "industry_electronics", "nuclear"
        elif any(kw in cat_lower for kw in ['rocket', 'missile']):
            tech.branch, tech.category = "industry_electronics", "rockets"
        elif any(kw in cat_lower for kw in ['doctrine']):
            tech.branch, tech.category = "doctrine", "land_doctrine"
            tech.is_doctrine = True
        else:
            continue

        tech.min_tier = CATEGORY_MIN_TIER.get(tech.category, "micro")
        tech.min_branch_score = CATEGORY_MIN_BRANCH_SCORE.get(tech.category, 0)
        return

    tech.branch = "unknown"
    tech.category = "unknown"


# ============================================================================
# DEPENDENCY DEPTH CALCULATION
# ============================================================================

def calculate_dependency_depths(techs: list):
    """Calculate the dependency chain depth for each tech."""
    tech_map = {t.tech_id: t for t in techs}

    def get_depth(tech_id: str, visited: set = None) -> int:
        if visited is None:
            visited = set()
        if tech_id in visited or tech_id not in tech_map:
            return 0
        visited.add(tech_id)
        tech = tech_map[tech_id]
        if not tech.dependencies:
            return 0
        max_dep_depth = 0
        for dep_id in tech.dependencies:
            d = get_depth(dep_id, visited.copy())
            max_dep_depth = max(max_dep_depth, d)
        return max_dep_depth + 1

    for tech in techs:
        tech.dependency_depth = get_depth(tech.tech_id)
        if tech.min_tier not in ("superpower",) and tech.dependency_depth >= 4:
            tech.min_tier = "great_power"
        elif tech.min_tier not in ("superpower", "great_power") and tech.dependency_depth >= 3:
            if tech.min_tier in ("micro", "minor", "minor_industrial"):
                tech.min_tier = "regional_power"


# ============================================================================
# CUSTOM MAPPING LOADER
# ============================================================================

def load_custom_mappings(filepath: Path) -> dict:
    """Load user-defined category tag mappings from a text file."""
    custom = {}
    if not filepath.exists():
        return custom
    print(f"[INFO] Loading custom mappings from {filepath}")
    for line in filepath.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        sep = '\u2192' if '\u2192' in line else '->'
        if sep not in line:
            continue
        tag_part, mapping_part = line.split(sep, 1)
        tag = tag_part.strip()
        parts = [p.strip() for p in mapping_part.split('/')]
        if len(parts) != 2:
            print(f"  [WARN] Bad mapping format: {line}")
            continue
        branch, category = parts
        custom[tag] = (branch, category)
        print(f"  [MAP] {tag} -> {branch} / {category}")
    return custom


# ============================================================================
# OUTPUT GENERATOR — HELPERS
# ============================================================================

def target_year_var_for_branch(branch: str) -> str:
    return TARGET_YEAR_VAR_BY_BRANCH.get(branch, f"tbm_target_year_{branch}")


def competence_var_for_branch(branch: str) -> str:
    return COMPETENCE_VAR_BY_BRANCH.get(branch, f"tbm_{branch}_competence")


def category_flag_for(category: str) -> str:
    return CATEGORY_FLAG_BY_CATEGORY.get(category, "")


def is_runtime_supported_tech(tech: TechDef) -> bool:
    return tech.branch != "unknown" and not tech.is_doctrine


def append_grant_limit_lines(lines: list, tech: TechDef, counter_var: str = "tbm_grant_counter",
                             cap_var: str = "tbm_quarterly_cap", indent: str = "            "):
    lines.append(
        f"{indent}check_variable = {{ var = {counter_var} value = {cap_var} compare = less_than }}"
    )
    lines.append(
        f"{indent}check_variable = {{ var = {target_year_var_for_branch(tech.branch)} "
        f"value = {tech.start_year} compare = greater_than_or_equals }}"
    )
    tier_index = TIER_ORDER.index(tech.min_tier) if tech.min_tier in TIER_ORDER else 0
    if tier_index > 0:
        lines.append(
            f"{indent}check_variable = {{ var = tbm_tier_index value = {tier_index} "
            f"compare = greater_than_or_equals }}"
        )
    if tech.min_branch_score > 0:
        lines.append(
            f"{indent}check_variable = {{ var = {competence_var_for_branch(tech.branch)} "
            f"value = {tech.min_branch_score} compare = greater_than_or_equals }}"
        )
    category_flag = category_flag_for(tech.category)
    if category_flag:
        lines.append(f"{indent}has_country_flag = {category_flag}")
    if tech.category in ADVANCED_TECH_CATEGORIES:
        lines.append(f"{indent}tbm_advanced_tech_allowed = yes")
    for dep in tech.dependencies:
        lines.append(f"{indent}has_tech = {dep}")
    if tech.dlc_required:
        lines.append(f'{indent}has_dlc = "{tech.dlc_required}"')
    if tech.dlc_hidden_by:
        lines.append(f'{indent}NOT = {{ has_dlc = "{tech.dlc_hidden_by}" }}')


def append_group_outer_limit_lines(lines: list, tech_list: list[TechDef],
                                   counter_var: str = "tbm_grant_counter",
                                   cap_var: str = "tbm_quarterly_cap",
                                   indent: str = "            "):
    if not tech_list:
        return
    first = tech_list[0]
    earliest_year = min(tech.start_year for tech in tech_list)
    lines.append(
        f"{indent}check_variable = {{ var = {counter_var} value = {cap_var} compare = less_than }}"
    )
    lines.append(
        f"{indent}check_variable = {{ var = {target_year_var_for_branch(first.branch)} "
        f"value = {earliest_year} compare = greater_than_or_equals }}"
    )
    category_flag = category_flag_for(first.category)
    if category_flag:
        lines.append(f"{indent}has_country_flag = {category_flag}")
    min_tier_index = min(
        (TIER_ORDER.index(tech.min_tier) if tech.min_tier in TIER_ORDER else 0)
        for tech in tech_list
    )
    if min_tier_index > 0:
        lines.append(
            f"{indent}check_variable = {{ var = tbm_tier_index value = {min_tier_index} "
            f"compare = greater_than_or_equals }}"
        )
    min_branch_score = min(tech.min_branch_score for tech in tech_list)
    if min_branch_score > 0:
        lines.append(
            f"{indent}check_variable = {{ var = {competence_var_for_branch(first.branch)} "
            f"value = {min_branch_score} compare = greater_than_or_equals }}"
        )
    if first.category in ADVANCED_TECH_CATEGORIES:
        lines.append(f"{indent}tbm_advanced_tech_allowed = yes")
    shared_dlc = tech_list[0].dlc_required
    if shared_dlc and all(tech.dlc_required == shared_dlc for tech in tech_list):
        lines.append(f'{indent}has_dlc = "{shared_dlc}"')
    shared_dlc_hidden = tech_list[0].dlc_hidden_by
    if shared_dlc_hidden and all(tech.dlc_hidden_by == shared_dlc_hidden for tech in tech_list):
        lines.append(f'{indent}NOT = {{ has_dlc = "{shared_dlc_hidden}" }}')


def split_techs_by_start_year(tech_list: list[TechDef]) -> list[tuple[int, list[TechDef]]]:
    grouped: list[tuple[int, list[TechDef]]] = []
    for tech in tech_list:
        if not grouped or grouped[-1][0] != tech.start_year:
            grouped.append((tech.start_year, [tech]))
        else:
            grouped[-1][1].append(tech)
    return grouped


def apply_known_xor_pairs(techs: list[TechDef]) -> None:
    """Inject known mutually exclusive tech guards when source data omits them."""
    tech_by_id = {tech.tech_id: tech for tech in techs}
    for left_id, right_id in KNOWN_XOR_PAIRS:
        left = tech_by_id.get(left_id)
        right = tech_by_id.get(right_id)
        if not left or not right:
            continue
        if right_id not in left.xor_techs:
            left.xor_techs.append(right_id)
        if left_id not in right.xor_techs:
            right.xor_techs.append(left_id)


def append_generated_grant_tech_blocks(lines: list, tech_list: list[TechDef], indent: str = "        "):
    child_indent = f"{indent}    "
    grandchild_indent = f"{child_indent}    "
    # Track XOR groups: once we emit the first tech of an XOR set, subsequent
    # members use else_if so the engine cannot grant both in the same pass.
    xor_emitted = set()
    for tech in tech_list:
        if tech.is_xp_gated:
            lines.append(f"{indent}# SKIPPED (XP-gated): {tech.tech_id}")
            continue
        # Determine if this tech is an XOR follower (its counterpart already emitted).
        is_xor_follower = False
        if tech.xor_techs:
            xor_key = frozenset([tech.tech_id] + tech.xor_techs)
            if xor_key in xor_emitted:
                is_xor_follower = True
            else:
                xor_emitted.add(xor_key)
        block_keyword = "else_if" if is_xor_follower else "if"
        lines.append(f"{indent}# {tech.tech_id} - {tech.start_year}")
        lines.append(f"{indent}{block_keyword} = {{")
        lines.append(f"{child_indent}limit = {{")
        lines.append(f"{grandchild_indent}NOT = {{ has_tech = {tech.tech_id} }}")
        for xor_id in tech.xor_techs:
            lines.append(f"{grandchild_indent}NOT = {{ has_tech = {xor_id} }}")
        append_grant_limit_lines(lines, tech, indent=grandchild_indent)
        lines.append(f"{child_indent}}}")
        lines.append(f"{child_indent}set_technology = {{ {tech.tech_id} = 1 popup = no }}")
        lines.append(f"{child_indent}add_to_variable = {{ tbm_grant_counter = 1 }}")
        lines.append(f"{child_indent}tbm_handle_tech_grant_notification = yes")
        lines.append(f"{indent}}}")


def append_generated_grant_effect(lines: list, effect_name: str, tech_list: list[TechDef]):
    year_groups = split_techs_by_start_year(tech_list)
    target_year_var = target_year_var_for_branch(tech_list[0].branch) if tech_list else ""

    lines.append(f"{effect_name} = {{")
    lines.append("    if = {")
    lines.append("        limit = {")
    append_group_outer_limit_lines(lines, tech_list)
    lines.append("        }")

    if len(year_groups) <= 1:
        append_generated_grant_tech_blocks(lines, tech_list)
    else:
        lines.append("        # Year-sliced dispatch avoids scanning future tech eras every pulse.")
        for start_year, year_techs in year_groups:
            subeffect_name = f"{effect_name}_y{start_year}"
            lines.append("        if = {")
            lines.append("            limit = {")
            lines.append("                check_variable = { var = tbm_grant_counter value = tbm_quarterly_cap compare = less_than }")
            lines.append(
                f"                check_variable = {{ var = {target_year_var} value = {start_year} compare = greater_than_or_equals }}"
            )
            lines.append("            }")
            lines.append(f"            {subeffect_name} = yes")
            lines.append("        }")

    lines.append("    }")
    lines.append("}")

    if len(year_groups) > 1:
        for start_year, year_techs in year_groups:
            subeffect_name = f"{effect_name}_y{start_year}"
            lines.append("")
            lines.append(f"{subeffect_name} = {{")
            lines.append("    if = {")
            lines.append("        limit = {")
            append_group_outer_limit_lines(lines, year_techs)
            lines.append("        }")
            append_generated_grant_tech_blocks(lines, year_techs)
            lines.append("    }")
            lines.append("}")


# ============================================================================
# OUTPUT GENERATOR — MAIN
# ============================================================================

def generate_output_files(techs: list, output_dir: Path, mode: str, mod_name: str,
                          report_dir: Optional[Path] = None):
    """Generate TBM-compatible scripted effect files from parsed techs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    if report_dir is None:
        report_dir = output_dir

    apply_known_xor_pairs(techs)

    known_techs = [t for t in techs if is_runtime_supported_tech(t)]
    unknown_techs = [t for t in techs if t.branch == "unknown"]

    if unknown_techs:
        print(f"\n[WARN] {len(unknown_techs)} techs could not be mapped to a branch:")
        for t in unknown_techs[:20]:
            print(f"  - {t.tech_id} (categories: {t.categories}) from {t.source_mod}")
        if len(unknown_techs) > 20:
            print(f"  ... and {len(unknown_techs) - 20} more")
        print(f"  Add mappings to custom_mappings.txt to include these.")

    grouped = {}
    for tech in known_techs:
        key = (tech.branch, tech.category)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(tech)

    for key in grouped:
        grouped[key].sort(key=lambda t: (t.start_year, t.dependency_depth))

    filename = "auto_research_techlist.txt"
    filepath = output_dir / filename

    lines = []
    lines.append(f"# {'=' * 67}")
    lines.append(f"# Tech Baseline Mechanics -- Auto-Generated Tech Lists")
    lines.append(f"# Source: {mod_name}")
    lines.append(f"# Mode: {mode}")
    lines.append(f"# Total techs mapped: {len(known_techs)}")
    lines.append(f"# Unmapped techs: {len(unknown_techs)}")
    lines.append(f"# {'=' * 67}")
    lines.append(f"# THIS FILE IS AUTO-GENERATED. Do not edit manually.")
    lines.append(f"# Re-run tbm_compat_tool.py to regenerate.")
    lines.append(f"# {'=' * 67}")
    lines.append("")

    for (branch, category), tech_list in sorted(grouped.items()):
        effect_name = f"tbm_grant_{branch}_{category}"
        lines.append(f"# -- {branch.upper()} / {category.upper()} ({len(tech_list)} techs) --")
        lines.append("")
        for tech in tech_list:
            flags = []
            if tech.is_doctrine:
                flags.append("DOCTRINE")
            if tech.is_xp_gated:
                flags.append("XP_GATED")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            dep_str = ""
            if tech.dependencies:
                dep_str = f" deps=[{', '.join(tech.dependencies)}]"
            xor_str = ""
            if tech.xor_techs:
                xor_str = f" XOR=[{', '.join(tech.xor_techs)}]"
            lines.append(f"# {tech.tech_id}")
            lines.append(f"#   year={tech.start_year} branch={tech.branch} "
                         f"category={tech.category}")
            lines.append(f"#   min_tier={tech.min_tier} "
                         f"min_branch_score={tech.min_branch_score}"
                         f"{dep_str}{xor_str}{flag_str}")
            lines.append("")
        append_generated_grant_effect(lines, effect_name, tech_list)

    for (branch, category) in EXPECTED_EFFECTS:
        if (branch, category) not in grouped:
            effect_name = f"tbm_grant_{branch}_{category}"
            lines.append(f"# -- {branch.upper()} / {category.upper()} (0 techs) --")
            lines.append(f"{effect_name} = {{")
            lines.append(f"    # No techs matched this category.")
            lines.append(f"}}")
            lines.append("")

    filepath.write_text('\n'.join(lines), encoding='utf-8')
    print(f"\n[OUTPUT] Written: {filepath}")
    print(f"         {len(known_techs)} techs in {len(grouped)} categories")

    report_path = report_dir / "tbm_tech_report.txt"
    generate_report(techs, known_techs, unknown_techs, grouped, report_path)
    return filepath


def generate_report(all_techs, known, unknown, grouped, filepath):
    """Generate a human-readable summary report."""
    lines = []
    lines.append("ARMS RACE MECHANICS -- TECH LIST GENERATION REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Total techs parsed:    {len(all_techs)}")
    lines.append(f"Successfully mapped:   {len(known)}")
    lines.append(f"Unmapped (unknown):    {len(unknown)}")
    lines.append("")

    lines.append("BRANCH SUMMARY")
    lines.append("-" * 40)
    branch_counts = {}
    for tech in known:
        branch_counts[tech.branch] = branch_counts.get(tech.branch, 0) + 1
    for branch in sorted(branch_counts.keys()):
        lines.append(f"  {branch:<30} {branch_counts[branch]:>4} techs")

    lines.append("")
    lines.append("CATEGORY DETAIL")
    lines.append("-" * 60)
    for (branch, category), tech_list in sorted(grouped.items()):
        lines.append(f"\n  [{branch} / {category}] -- {len(tech_list)} techs")
        for tech in tech_list:
            flags = []
            if tech.is_doctrine:
                flags.append("DOC")
            if tech.is_xp_gated:
                flags.append("XP")
            flag_str = f" ({', '.join(flags)})" if flags else ""
            lines.append(f"    {tech.start_year}  {tech.tech_id}{flag_str}")
            if tech.source_mod != "vanilla":
                lines.append(f"          [from: {tech.source_mod}]")

    if unknown:
        lines.append("")
        lines.append("UNMAPPED TECHS")
        lines.append("-" * 60)
        lines.append("These techs could not be assigned to a branch.")
        lines.append("Add entries to custom_mappings.txt to include them.")
        lines.append("")
        for tech in sorted(unknown, key=lambda t: t.tech_id):
            lines.append(f"  {tech.tech_id}")
            lines.append(f"    categories: {tech.categories}")
            lines.append(f"    source: {tech.source_mod} / {tech.source_file}")

    filepath.write_text('\n'.join(lines), encoding='utf-8')
    print(f"[OUTPUT] Report: {filepath}")


# ============================================================================
# CORE RUNTIME OUTPUTS
# ============================================================================

def refresh_core_runtime_outputs(hoi4_dir: Path,
                                 scripted_effects_dir: Path = SCRIPTED_EFFECTS_DIR,
                                 report_dir: Path = TOOLS_DIR) -> None:
    """Regenerate vanilla TBM runtime outputs checked into the main mod."""
    tech_root = hoi4_dir / "common" / "technologies"
    if not tech_root.exists():
        raise SystemExit(f"HOI4 tech directory not found: {tech_root}")

    custom_mappings = load_custom_mappings(CUSTOM_MAPPINGS_PATH)
    if custom_mappings:
        CATEGORY_MAP.update(custom_mappings)

    vanilla_techs = parse_tech_files(tech_root, "vanilla", False)
    generate_output_files(vanilla_techs, scripted_effects_dir, "expansion", "expansion", report_dir=report_dir)
    print("Core TBM runtime outputs written to common/scripted_effects")


# ============================================================================
# PRESET / EVALUATION PATCHING
# ============================================================================

def apply_thresholds_to_evaluation(text: str, thresholds: dict) -> str:
    promotions = {
        "minor": thresholds["minor"] + 5,
        "minor_industrial": thresholds["minor_industrial"] + 5,
        "regional_power": thresholds["regional_power"] + 5,
        "great_power": thresholds["great_power"] + 5,
        "superpower": thresholds["superpower"] + 5,
    }
    demotions = {
        "minor": thresholds["minor"] - 5,
        "minor_industrial": thresholds["minor_industrial"] - 5,
        "regional_power": thresholds["regional_power"] - 5,
        "great_power": thresholds["great_power"] - 5,
        "superpower": thresholds["superpower"] - 5,
    }

    section_re = re.compile(
        r"(\s*# Save old tier for change detection\s*\n\s*set_variable = \{ tbm_old_tier_index = tbm_tier_index \}\s*\n)"
        r"(.*?)"
        r"(\s*# ===================================================\s*\n\s*# Base lag by tier)",
        re.S,
    )
    match = section_re.search(text)
    if not match:
        raise RuntimeError("Failed to locate tbm_assign_power_tier movement section")

    movement = f"""    # ===================================================
    # Tier movement
    # Evaluate from the tier at the start of the pass so a
    # broken refresh cannot jump multiple tiers at once.
    # ===================================================
    if = {{
        limit = {{ check_variable = {{ var = tbm_old_tier_index value = 0 compare = equals }} }}
        if = {{
            limit = {{ check_variable = {{ var = tbm_global_power value = {promotions["minor"]} compare = greater_than }} }}
            set_variable = {{ tbm_tier_index = 1 }}
        }}
    }}
    else_if = {{
        limit = {{ check_variable = {{ var = tbm_old_tier_index value = 1 compare = equals }} }}
        if = {{
            limit = {{ check_variable = {{ var = tbm_global_power value = {promotions["minor_industrial"]} compare = greater_than }} }}
            set_variable = {{ tbm_tier_index = 2 }}
        }}
        else_if = {{
            limit = {{ check_variable = {{ var = tbm_global_power value = {demotions["minor"]} compare = less_than }} }}
            set_variable = {{ tbm_tier_index = 0 }}
        }}
    }}
    else_if = {{
        limit = {{ check_variable = {{ var = tbm_old_tier_index value = 2 compare = equals }} }}
        if = {{
            limit = {{ check_variable = {{ var = tbm_global_power value = {promotions["regional_power"]} compare = greater_than }} }}
            set_variable = {{ tbm_tier_index = 3 }}
        }}
        else_if = {{
            limit = {{ check_variable = {{ var = tbm_global_power value = {demotions["minor_industrial"]} compare = less_than }} }}
            set_variable = {{ tbm_tier_index = 1 }}
        }}
    }}
    else_if = {{
        limit = {{ check_variable = {{ var = tbm_old_tier_index value = 3 compare = equals }} }}
        if = {{
            limit = {{ check_variable = {{ var = tbm_global_power value = {promotions["great_power"]} compare = greater_than }} }}
            set_variable = {{ tbm_tier_index = 4 }}
        }}
        else_if = {{
            limit = {{ check_variable = {{ var = tbm_global_power value = {demotions["regional_power"]} compare = less_than }} }}
            set_variable = {{ tbm_tier_index = 2 }}
        }}
    }}
    else_if = {{
        limit = {{ check_variable = {{ var = tbm_old_tier_index value = 4 compare = equals }} }}
        if = {{
            limit = {{ check_variable = {{ var = tbm_global_power value = {promotions["superpower"]} compare = greater_than }} }}
            set_variable = {{ tbm_tier_index = 5 }}
        }}
        else_if = {{
            limit = {{ check_variable = {{ var = tbm_global_power value = {demotions["great_power"]} compare = less_than }} }}
            set_variable = {{ tbm_tier_index = 3 }}
        }}
    }}
    else_if = {{
        limit = {{ check_variable = {{ var = tbm_old_tier_index value = 5 compare = equals }} }}
        if = {{
            limit = {{ check_variable = {{ var = tbm_global_power value = {demotions["superpower"]} compare = less_than }} }}
            set_variable = {{ tbm_tier_index = 4 }}
        }}
    }}
"""
    return text[:match.start(2)] + movement + text[match.start(3):]


def write_preset_evaluation(output_path: Path, preset: dict):
    base_text = BASE_EVALUATION_PATH.read_text(encoding="utf-8-sig")
    patched = apply_thresholds_to_evaluation(base_text, preset["tier_thresholds"])
    header = (
        "##########################################################\n"
        f"# Generated preset override: {preset['description']}\n"
        "# This file is generated by Tools/tbm_compat_tool.py\n"
        "##########################################################\n\n"
    )
    output_path.write_text(header + patched, encoding="utf-8")


def resolve_preset(profile: dict) -> dict | None:
    if "preset" in profile:
        return profile["preset"]
    preset_name = profile.get("preset_name")
    if preset_name:
        preset = dict(PRESETS[preset_name])
        preset["name"] = preset_name
        return preset
    return None


def parse_descriptor_name(mod_dir: Path) -> str:
    descriptor = mod_dir / "descriptor.mod"
    if not descriptor.exists():
        return mod_dir.name
    text = descriptor.read_text(encoding="utf-8-sig", errors="replace")
    match = re.search(r'^name\s*=\s*"([^"]+)"', text, re.M)
    return match.group(1) if match else mod_dir.name


def handle_remove_readonly(func, path, exc_info):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        raise exc_info[1]


# ============================================================================
# BUNDLE WRITING
# ============================================================================

def build_final_techs(vanilla_techs: list, mod_techs: list) -> list:
    final_techs = [tech for tech in vanilla_techs if tech.tech_id not in {m.tech_id for m in mod_techs}]
    final_techs.extend(mod_techs)
    calculate_dependency_depths(final_techs)
    return final_techs


def write_bundle_readme(path: Path, profile: dict, actual_name: str, stats: dict, preset: dict | None):
    lines = [
        f"TBM compatibility bundle for {actual_name}",
        "",
        f"Workshop ID: {profile['workshop_id']}",
        f"Bundle slug: {profile['slug']}",
        f"Generation mode: {profile['mode']}",
        f"Parsed techs: {stats['techs_total']}",
        f"Unknown techs: {stats['unknown_total']}",
        f"Doctrines detected: {stats['doctrine_total']}",
    ]
    if preset:
        lines.append(f"Preset thresholds: {preset.get('name', 'custom')}")
    lines.extend([
        "",
        "Files in this bundle:",
        "- common/scripted_effects/auto_research_techlist.txt",
        "- Tools/tbm_tech_report.txt",
    ])
    if preset:
        lines.append("- common/scripted_effects/tbm_evaluation.txt")
    lines.extend([
        "",
        "Load after Tech Baseline Mechanics and the target mod.",
        "This bundle is generated output, not hand-authored logic.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_bundle(
    *,
    hoi4_dir: Path,
    mod_dir: Path,
    slug: str,
    display_name: str | None,
    mode: str,
    preset: dict | None,
    output_root: Path,
    workshop_id: str | None,
) -> dict:
    vanilla_techs = parse_tech_files(hoi4_dir / "common" / "technologies", "vanilla", False)
    mod_techs = parse_tech_files(mod_dir / "common" / "technologies", slug, False)
    final_techs = build_final_techs(vanilla_techs, mod_techs)

    bundle_root = output_root / slug
    if bundle_root.exists():
        shutil.rmtree(bundle_root, onexc=handle_remove_readonly)

    scripted_effects_dir = bundle_root / "common" / "scripted_effects"
    reports_dir = bundle_root / "Tools"
    scripted_effects_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    generate_output_files(final_techs, scripted_effects_dir, mode, slug, report_dir=reports_dir)

    if preset:
        write_preset_evaluation(scripted_effects_dir / "tbm_evaluation.txt", preset)

    actual_name = display_name or parse_descriptor_name(mod_dir)
    stats = {
        "techs_total": len(mod_techs),
        "unknown_total": sum(1 for tech in mod_techs if tech.branch == "unknown"),
        "doctrine_total": sum(1 for tech in mod_techs if tech.is_doctrine),
    }

    profile = {
        "workshop_id": workshop_id or "",
        "slug": slug,
        "display_name": actual_name,
        "mode": mode,
        "preset": preset["name"] if preset else None,
        "stats": stats,
    }

    write_bundle_readme(bundle_root / "README.txt", profile, actual_name, stats, preset)
    (bundle_root / "manifest.json").write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    return profile


# ============================================================================
# INDEX MANAGEMENT
# ============================================================================

def load_index(path: Path) -> dict:
    if not path.exists():
        return {"generated_bundles": []}
    return json.loads(path.read_text(encoding="utf-8"))


def write_index(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def upsert_index_entry(index: dict, entry: dict) -> None:
    bundles = index.setdefault("generated_bundles", [])
    for idx, existing in enumerate(bundles):
        if existing.get("slug") == entry["slug"]:
            bundles[idx] = entry
            break
    else:
        bundles.append(entry)
    bundles.sort(key=lambda item: item["slug"])


# ============================================================================
# BUILD / COMPILE — HELPERS
# ============================================================================

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
    suffix = f"_{slug}"

    def repl(match: re.Match[str]) -> str:
        token = match.group(1)
        if token.endswith(suffix):
            return token
        return f"{token}{suffix}"

    return re.sub(r"\b(tbm_grant_[A-Za-z0-9_]+)\b", repl, text)


def rename_tier_effect(block_text: str, slug: str) -> str:
    return re.sub(
        r"(?m)^tbm_assign_power_tier\s*=",
        f"tbm_assign_power_tier_{slug} =",
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


def normalize_generated_tier_block(text: str) -> str:
    text = text.replace(
        "        limit = {\n"
        "            has_game_rule = { rule = tbm_auto_research_intensity option = TBM_RELAXED }\n"
        "        }",
        "        limit = {\n"
        "            OR = {\n"
        "                has_game_rule = { rule = tbm_auto_research_intensity option = TBM_REALISTIC }\n"
        "                has_game_rule = { rule = tbm_auto_research_intensity option = TBM_HISTORICAL }\n"
        "            }\n"
        "        }",
    )
    replacements = {
        "set_variable = { tbm_base_lag = 0.5 }": "set_variable = { tbm_base_lag = __ARM_LAG_T5__ }",
        "set_variable = { tbm_base_lag = 1.0 }": "set_variable = { tbm_base_lag = __ARM_LAG_T4__ }",
        "set_variable = { tbm_base_lag = 1.5 }": "set_variable = { tbm_base_lag = __ARM_LAG_T3__ }",
        "set_variable = { tbm_base_lag = 3.0 }": "set_variable = { tbm_base_lag = __ARM_LAG_T2__ }",
        "set_variable = { tbm_base_lag = __ARM_LAG_T5__ }": "set_variable = { tbm_base_lag = 0.25 }",
        "set_variable = { tbm_base_lag = __ARM_LAG_T4__ }": "set_variable = { tbm_base_lag = 1.5 }",
        "set_variable = { tbm_base_lag = __ARM_LAG_T3__ }": "set_variable = { tbm_base_lag = 2.5 }",
        "set_variable = { tbm_base_lag = __ARM_LAG_T2__ }": "set_variable = { tbm_base_lag = 3.5 }",
        "subtract_from_variable = { tbm_base_lag = 0.5 }": "subtract_from_variable = { tbm_base_lag = 0.75 }",
        "has_game_rule = { rule = tbm_auto_research_intensity option = TBM_AGGRESSIVE }": "has_game_rule = { rule = tbm_auto_research_intensity option = TBM_ARCADE }",
        "set_variable = { tbm_quarterly_cap = 6 }": "set_variable = { tbm_quarterly_cap = 12 }",
        "set_variable = { tbm_quarterly_cap = 5 }": "set_variable = { tbm_quarterly_cap = 10 }",
        "set_variable = { tbm_quarterly_cap = 4 }": "set_variable = { tbm_quarterly_cap = 8 }",
        "set_variable = { tbm_quarterly_cap = 3 }": "set_variable = { tbm_quarterly_cap = 6 }",
        "set_variable = { tbm_quarterly_cap = 2 }": "set_variable = { tbm_quarterly_cap = 4 }",
        "set_variable = { tbm_quarterly_cap = 1 }": "set_variable = { tbm_quarterly_cap = 2 }",
        "# Superpower=6, Great=5, Regional=4, MinorInd=3, Minor=2, Micro=1": "# Superpower=12, Great=10, Regional=8, MinorInd=6, Minor=4, Micro=2",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


# ============================================================================
# BUILD / COMPILE — DISPATCH GENERATOR
# ============================================================================

def build_profile_limit_lines(slug: str, indent: str = "        ") -> list[str]:
    lines = [f"{indent}OR = {{"]
    lines.append(f"{indent}    has_game_rule = {{ rule = tbm_compat_profile option = {PROFILE_OPTION_KEYS[slug]} }}")
    lines.append(f"{indent}    AND = {{")
    lines.append(f"{indent}        has_game_rule = {{ rule = tbm_compat_profile option = TBM_COMPAT_AUTO }}")
    lines.append(f"{indent}        has_global_flag = tbm_compat_auto_{slug}")
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


def build_profile_dispatch(index: dict) -> str:
    profiles = [item["slug"] for item in index["generated_bundles"] if item["slug"] in PROFILE_OPTION_KEYS]

    lines = []
    lines.append("###############################################################################")
    lines.append("# tbm_compat_profiles_generated.txt")
    lines.append("# Generated by Tools/tbm_compat_tool.py")
    lines.append("###############################################################################")
    lines.append("")
    lines.append("tbm_clear_auto_compat_profile_flags = {")
    lines.append("    clr_global_flag = tbm_compat_auto_profile_detected")
    lines.append("    clr_global_flag = tbm_compat_auto_doctrine_safe")
    for slug in PROFILE_ORDER:
        if slug in profiles:
            lines.append(f"    clr_global_flag = tbm_compat_auto_{slug}")
    lines.append("}")
    lines.append("")
    lines.append("tbm_auto_detect_compat_profile = {")
    lines.append("    tbm_clear_auto_compat_profile_flags = yes")
    for slug in PROFILE_ORDER:
        if slug not in profiles:
            continue
        keyword = "if" if slug == PROFILE_ORDER[0] else "else_if"
        lines.append(f"    {keyword} = {{")
        lines.append("        limit = {")
        lines.extend(build_auto_detect_limit_lines(slug))
        lines.append("        }")
        lines.append("        set_global_flag = tbm_compat_auto_profile_detected")
        lines.append(f"        set_global_flag = tbm_compat_auto_{slug}")
        if slug in DOCTRINE_SAFE_PROFILES:
            lines.append("        set_global_flag = tbm_compat_auto_doctrine_safe")
        lines.append("    }")
    lines.append("}")
    lines.append("")
    lines.append("tbm_assign_power_tier_for_profile = {")
    for slug in PROFILE_ORDER:
        if slug not in profiles:
            continue
        keyword = "if" if slug == PROFILE_ORDER[0] else "else_if"
        lines.append(f"    {keyword} = {{")
        lines.append("        limit = {")
        lines.extend(build_profile_limit_lines(slug))
        lines.append("        }")
        lines.append(f"        tbm_assign_power_tier_{slug} = yes")
        lines.append("    }")
    lines.append("    else = {")
    lines.append("        tbm_assign_power_tier = yes")
    lines.append("    }")
    lines.append("}")
    lines.append("")
    lines.append("tbm_grant_techs_for_profile = {")
    for slug in PROFILE_ORDER:
        if slug not in profiles:
            continue
        keyword = "if" if slug == PROFILE_ORDER[0] else "else_if"
        lines.append(f"    {keyword} = {{")
        lines.append("        limit = {")
        lines.extend(build_profile_limit_lines(slug))
        lines.append("        }")
        counter_var = f"tbm_grant_counter_{slug}"
        for branch in BRANCH_ORDER:
            cap_var = f"tbm_cap_{branch}"
            lines.append(f"        # --- {branch.upper()} branch ---")
            lines.append(f"        set_variable = {{ {counter_var} = 0 }}")
            lines.append(f"        set_variable = {{ tbm_quarterly_cap = {cap_var} }}")
            for effect_name in GRANT_ORDER_BY_BRANCH[branch]:
                lines.append("        if = {")
                lines.append("            limit = {")
                lines.append(f"                check_variable = {{ var = {counter_var} value = tbm_quarterly_cap compare = less_than }}")
                lines.append("            }")
                lines.append(f"            {effect_name}_{slug} = yes")
                lines.append("        }")
        lines.append("    }")
    lines.append("    else = {")
    for branch in BRANCH_ORDER:
        cap_var = f"tbm_cap_{branch}"
        lines.append(f"        # --- {branch.upper()} branch ---")
        lines.append("        set_variable = { tbm_grant_counter = 0 }")
        lines.append(f"        set_variable = {{ tbm_quarterly_cap = {cap_var} }}")
        for effect_name in GRANT_ORDER_BY_BRANCH[branch]:
            lines.append("        if = {")
            lines.append("            limit = {")
            lines.append("                check_variable = { var = tbm_grant_counter value = tbm_quarterly_cap compare = less_than }")
            lines.append("            }")
            lines.append(f"            {effect_name} = yes")
            lines.append("        }")
    lines.append("    }")
    lines.append("}")
    lines.append("")
    lines.append("tbm_initialize_doctrine_paths_for_profile = {")
    lines.append("    if = {")
    lines.append("        limit = {")
    lines.append("            tbm_doctrine_allowed = yes")
    lines.append("            OR = {")
    lines.append("                has_game_rule = { rule = tbm_compat_profile option = TBM_COMPAT_VANILLA }")
    lines.append("                AND = {")
    lines.append("                    has_game_rule = { rule = tbm_compat_profile option = TBM_COMPAT_AUTO }")
    lines.append("                    OR = {")
    lines.append("                        NOT = { has_global_flag = tbm_compat_auto_profile_detected }")
    lines.append("                        has_global_flag = tbm_compat_auto_doctrine_safe")
    lines.append("                    }")
    lines.append("                }")
    for slug in PROFILE_ORDER:
        if slug in profiles and slug in DOCTRINE_SAFE_PROFILES:
            lines.append(f"                has_game_rule = {{ rule = tbm_compat_profile option = {PROFILE_OPTION_KEYS[slug]} }}")
    lines.append("            }")
    lines.append("        }")
    lines.append("        tbm_initialize_doctrine_paths = yes")
    lines.append("    }")
    lines.append("}")
    lines.append("")
    lines.append("tbm_grant_doctrines_for_profile = {")
    lines.append("    if = {")
    lines.append("        limit = {")
    lines.append("            tbm_doctrine_allowed = yes")
    lines.append("            OR = {")
    lines.append("                has_game_rule = { rule = tbm_compat_profile option = TBM_COMPAT_VANILLA }")
    lines.append("                AND = {")
    lines.append("                    has_game_rule = { rule = tbm_compat_profile option = TBM_COMPAT_AUTO }")
    lines.append("                    OR = {")
    lines.append("                        NOT = { has_global_flag = tbm_compat_auto_profile_detected }")
    lines.append("                        has_global_flag = tbm_compat_auto_doctrine_safe")
    lines.append("                    }")
    lines.append("                }")
    for slug in PROFILE_ORDER:
        if slug in profiles and slug in DOCTRINE_SAFE_PROFILES:
            lines.append(f"                has_game_rule = {{ rule = tbm_compat_profile option = {PROFILE_OPTION_KEYS[slug]} }}")
    lines.append("            }")
    lines.append("        }")
    lines.append("        tbm_grant_doctrines = yes")
    lines.append("    }")
    lines.append("}")
    lines.append("")
    return "\n".join(lines) + "\n"


# ============================================================================
# BUILD / COMPILE — MAIN
# ============================================================================

def compile_builtin_profiles(scripted_effects_dir: Path = SCRIPTED_EFFECTS_DIR):
    """Remove legacy baked compat runtime files from the core mod."""
    removed = []
    for old_file in sorted(scripted_effects_dir.glob("tbm_compat_generated*.txt")):
        old_file.unlink()
        removed.append(old_file.name)

    if removed:
        print("Removed legacy baked compatibility files from common/scripted_effects")
    else:
        print("No legacy baked compatibility files found in common/scripted_effects")


# ============================================================================
# GAME RULES AUTO-GENERATION
# ============================================================================

def update_game_rules(index: dict):
    """Regenerate the tbm_compat_profile block in tbm_game_rules.txt."""
    if not GAME_RULES_PATH.exists():
        print("[WARN] Game rules file not found, skipping game rules update")
        return

    text = GAME_RULES_PATH.read_text(encoding="utf-8-sig")

    # Find the tbm_compat_profile block boundaries
    block_start = text.find("tbm_compat_profile = {")
    if block_start == -1:
        print("[WARN] tbm_compat_profile block not found in game rules")
        return

    # Find the matching closing brace
    depth = 0
    pos = text.index("{", block_start)
    while pos < len(text):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                block_end = pos + 1
                break
        pos += 1
    else:
        print("[WARN] Unbalanced braces in tbm_compat_profile block")
        return

    # Build new block
    slugs_in_index = {item["slug"] for item in index.get("generated_bundles", [])}
    active_slugs = [s for s in PROFILE_ORDER if s in slugs_in_index and s in PROFILE_OPTION_KEYS]

    new_block_lines = [
        "tbm_compat_profile = {",
        '\tname = "TBM_RULE_compat_profile"',
        '\tgroup = "TBM_RULES_GROUP"',
        "",
        "\tdefault = {",
        "\t\tname = TBM_COMPAT_AUTO",
        '\t\ttext = "TBM_OPT_COMPAT_AUTO"',
        '\t\tdesc = "TBM_DESC_COMPAT_AUTO"',
        "\t}",
        "\toption = {",
        "\t\tname = TBM_COMPAT_VANILLA",
        '\t\ttext = "TBM_OPT_COMPAT_VANILLA"',
        '\t\tdesc = "TBM_DESC_COMPAT_VANILLA"',
        "\t}",
    ]
    for slug in active_slugs:
        key = PROFILE_OPTION_KEYS[slug]
        new_block_lines.extend([
            "\toption = {",
            f"\t\tname = {key}",
            f'\t\ttext = "TBM_OPT_{key.removeprefix("TBM_")}"',
            f'\t\tdesc = "TBM_DESC_{key.removeprefix("TBM_")}"',
            "\t\tallow_achievements = no",
            "\t}",
        ])
    new_block_lines.append("}")

    new_text = text[:block_start] + "\n".join(new_block_lines) + text[block_end:]
    GAME_RULES_PATH.write_text(new_text, encoding="utf-8")
    print(f"[OUTPUT] Updated game rules: {GAME_RULES_PATH}")


def update_localisation(index: dict):
    """Regenerate compat profile entries in tbm_l_english.yml."""
    if not LOCALISATION_PATH.exists():
        print("[WARN] Localisation file not found, skipping localisation update")
        return

    text = LOCALISATION_PATH.read_text(encoding="utf-8-sig")
    lines = text.split("\n")

    # Find boundaries of compat profile loc entries (after the header comment for rule 3)
    # We replace from the first TBM_OPT_COMPAT_ line (after Auto/Vanilla) to the last TBM_DESC_COMPAT_ line
    first_profile_line = None
    last_profile_line = None
    auto_vanilla_keys = {"TBM_OPT_COMPAT_AUTO", "TBM_DESC_COMPAT_AUTO",
                         "TBM_OPT_COMPAT_VANILLA", "TBM_DESC_COMPAT_VANILLA"}

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Check if this is a profile-specific compat line (not auto/vanilla)
        if (stripped.startswith("TBM_OPT_COMPAT_") or stripped.startswith("TBM_DESC_COMPAT_")):
            key = stripped.split(":")[0].strip()
            if key not in auto_vanilla_keys:
                if first_profile_line is None:
                    first_profile_line = i
                last_profile_line = i

    if first_profile_line is None:
        # No existing profile lines found — insert after vanilla desc
        for i, line in enumerate(lines):
            if "TBM_DESC_COMPAT_VANILLA" in line:
                first_profile_line = i + 1
                last_profile_line = i  # Will replace nothing, just insert
                break
        if first_profile_line is None:
            print("[WARN] Could not find insertion point for compat localisation")
            return

    # Build new profile lines
    slugs_in_index = {item["slug"] for item in index.get("generated_bundles", [])}
    active_slugs = [s for s in PROFILE_ORDER if s in slugs_in_index and s in PROFILE_OPTION_KEYS]

    # Look up display names from index
    display_names = {}
    for item in index.get("generated_bundles", []):
        display_names[item["slug"]] = item.get("display_name", item["slug"])

    new_lines = []
    for slug in active_slugs:
        key = PROFILE_OPTION_KEYS[slug]
        opt_key = f"TBM_OPT_{key.removeprefix('TBM_')}"
        desc_key = f"TBM_DESC_{key.removeprefix('TBM_')}"
        short_name = PROFILE_SHORT_NAMES.get(slug, display_names.get(slug, slug))
        full_name = display_names.get(slug, short_name)
        new_lines.append(f' {opt_key}:0 "{short_name}"')
        new_lines.append(f' {desc_key}:0 "Use the built-in {full_name} research profile."')

    # Replace the section
    result_lines = lines[:first_profile_line] + new_lines + lines[last_profile_line + 1:]
    LOCALISATION_PATH.write_text("\n".join(result_lines), encoding="utf-8-sig")
    print(f"[OUTPUT] Updated localisation: {LOCALISATION_PATH}")


# ============================================================================
# VALIDATION ENGINE
# ============================================================================

@dataclass
class ValidationIssue:
    severity: str  # "ERROR" or "WARN"
    check: str
    message: str


def validate_tech_ids(slug: str, bundle_root: Path, hoi4_dir: Path,
                      workshop_root: Path) -> list[ValidationIssue]:
    """Check that every tech ID in generated effects exists in the mod's tech tree."""
    issues = []

    # Find the mod's workshop ID from manifest
    manifest_path = bundle_root / "manifest.json"
    if not manifest_path.exists():
        issues.append(ValidationIssue("ERROR", "tech_ids", f"Missing manifest.json for {slug}"))
        return issues

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    workshop_id = manifest.get("workshop_id", "")
    if not workshop_id:
        issues.append(ValidationIssue("WARN", "tech_ids", f"No workshop_id in manifest for {slug}"))
        return issues

    mod_dir = workshop_root / workshop_id
    if not mod_dir.exists():
        issues.append(ValidationIssue("WARN", "tech_ids", f"Workshop mod not installed: {workshop_id}"))
        return issues

    # Parse all tech IDs from vanilla + mod
    vanilla_techs = parse_tech_files(hoi4_dir / "common" / "technologies", "vanilla", False)
    mod_techs = parse_tech_files(mod_dir / "common" / "technologies", slug, False)
    all_tech_ids = {t.tech_id for t in vanilla_techs} | {t.tech_id for t in mod_techs}

    # Extract tech IDs referenced in the compiled file
    compiled_path = SCRIPTED_EFFECTS_DIR / f"tbm_compat_generated_{slug}.txt"
    if not compiled_path.exists():
        issues.append(ValidationIssue("ERROR", "tech_ids", f"Compiled file missing: {compiled_path.name}"))
        return issues

    compiled_text = compiled_path.read_text(encoding="utf-8")

    # Find set_technology = { TECH_ID = 1 popup = no }
    granted_ids = set(re.findall(r"set_technology\s*=\s*\{\s*(\w+)\s*=\s*1", compiled_text))
    # Find has_tech = TECH_ID
    checked_ids = set(re.findall(r"has_tech\s*=\s*(\w+)", compiled_text))

    missing_grants = granted_ids - all_tech_ids
    missing_checks = checked_ids - all_tech_ids

    if missing_grants:
        for tid in sorted(missing_grants):
            issues.append(ValidationIssue("ERROR", "tech_ids", f"Granted tech does not exist: {tid}"))
    if missing_checks:
        for tid in sorted(missing_checks):
            issues.append(ValidationIssue("WARN", "tech_ids", f"Checked tech does not exist: {tid}"))

    return issues


def validate_counter_variables(slug: str) -> list[ValidationIssue]:
    """Verify counter variable names use the correct slug."""
    issues = []
    compiled_path = SCRIPTED_EFFECTS_DIR / f"tbm_compat_generated_{slug}.txt"
    if not compiled_path.exists():
        return issues

    text = compiled_path.read_text(encoding="utf-8")
    counters = re.findall(r"tbm_grant_counter_(\w+)", text)

    wrong = [c for c in counters if c != slug]
    if wrong:
        unique_wrong = sorted(set(wrong))
        for w in unique_wrong:
            issues.append(ValidationIssue("ERROR", "counter_vars",
                                          f"Wrong counter suffix: tbm_grant_counter_{w} (expected _{slug})"))
    return issues


def validate_dispatch_linkage(slug: str) -> list[ValidationIssue]:
    """Verify dispatcher effect calls match compiled effect definitions."""
    issues = []
    dispatch_path = SCRIPTED_EFFECTS_DIR / "tbm_compat_generated_dispatch.txt"
    compiled_path = SCRIPTED_EFFECTS_DIR / f"tbm_compat_generated_{slug}.txt"
    if not dispatch_path.exists() or not compiled_path.exists():
        return issues

    dispatch_text = dispatch_path.read_text(encoding="utf-8")
    compiled_text = compiled_path.read_text(encoding="utf-8")

    # Effects called from dispatcher for this slug
    called = set(re.findall(rf"(tbm_grant_\w+_{re.escape(slug)})\s*=\s*yes", dispatch_text))

    # Effects defined in compiled file (top-level definitions)
    defined = set(re.findall(rf"^(tbm_grant_\w+_{re.escape(slug)})\s*=\s*\{{", compiled_text, re.MULTILINE))

    # Filter defined to only category-level effects (not year-slices)
    category_defined = {d for d in defined if not re.search(r"_y\d{4}_", d)}

    missing_defs = called - category_defined
    orphaned = category_defined - called

    for m in sorted(missing_defs):
        issues.append(ValidationIssue("ERROR", "dispatch_linkage",
                                      f"Dispatcher calls {m} but no definition found"))
    for o in sorted(orphaned):
        issues.append(ValidationIssue("WARN", "dispatch_linkage",
                                      f"Effect {o} defined but never called from dispatcher"))
    return issues


def validate_year_slices(slug: str) -> list[ValidationIssue]:
    """Verify year-slice sub-effects are reachable from parent effects."""
    issues = []
    compiled_path = SCRIPTED_EFFECTS_DIR / f"tbm_compat_generated_{slug}.txt"
    if not compiled_path.exists():
        return issues

    text = compiled_path.read_text(encoding="utf-8")

    # Find year-slice definitions
    year_defs = set(re.findall(rf"^(tbm_grant_\w+_y\d{{4}}_{re.escape(slug)})\s*=\s*\{{", text, re.MULTILINE))

    # Find year-slice calls
    year_calls = set(re.findall(rf"(tbm_grant_\w+_y\d{{4}}_{re.escape(slug)})\s*=\s*yes", text))

    orphaned = year_defs - year_calls
    for o in sorted(orphaned):
        issues.append(ValidationIssue("WARN", "year_slices", f"Year-slice defined but never called: {o}"))
    return issues


def validate_category_flags(slug: str) -> list[ValidationIssue]:
    """Verify category flag references are valid."""
    issues = []
    compiled_path = SCRIPTED_EFFECTS_DIR / f"tbm_compat_generated_{slug}.txt"
    if not compiled_path.exists():
        return issues

    text = compiled_path.read_text(encoding="utf-8")
    flags_used = set(re.findall(r"has_country_flag\s*=\s*(tbm_cat_\w+)", text))
    valid_flags = set(CATEGORY_FLAG_BY_CATEGORY.values())

    invalid = flags_used - valid_flags
    for f in sorted(invalid):
        issues.append(ValidationIssue("ERROR", "category_flags", f"Unknown category flag: {f}"))
    return issues


def validate_tier_effect(slug: str) -> list[ValidationIssue]:
    """Verify tier effect exists in tiers file."""
    issues = []
    tiers_path = SCRIPTED_EFFECTS_DIR / "tbm_compat_generated_tiers.txt"
    if not tiers_path.exists():
        issues.append(ValidationIssue("ERROR", "tier_effect", "Tiers file missing"))
        return issues

    text = tiers_path.read_text(encoding="utf-8")
    expected = f"tbm_assign_power_tier_{slug}"
    if expected not in text:
        issues.append(ValidationIssue("ERROR", "tier_effect", f"Missing tier effect: {expected}"))
    return issues


def validate_known_xor_pairs(slug: str) -> list[ValidationIssue]:
    """Verify compiled output preserves known mutually exclusive tech pairs."""
    issues = []
    compiled_path = SCRIPTED_EFFECTS_DIR / f"tbm_compat_generated_{slug}.txt"
    if not compiled_path.exists():
        return issues

    text = compiled_path.read_text(encoding="utf-8")
    for tech_id, other_id in KNOWN_XOR_PAIRS:
        for current, counterpart in ((tech_id, other_id), (other_id, tech_id)):
            pattern = re.compile(
                rf"set_technology\s*=\s*\{{\s*{re.escape(current)}\s*=\s*1\s+popup\s*=\s*no\s*\}}"
            )
            for match in pattern.finditer(text):
                window_start = max(0, match.start() - 600)
                block_window = text[window_start:match.start()]
                if f"NOT = {{ has_tech = {counterpart} }}" not in block_window:
                    issues.append(
                        ValidationIssue(
                            "ERROR",
                            "xor_pairs",
                            f"Missing XOR guard for {current} against {counterpart}",
                        )
                    )
                    break
    return issues


def run_validation(slugs: list[str], hoi4_dir: Path, workshop_root: Path,
                   verbose: bool = False) -> int:
    """Run all validation checks. Returns count of errors."""
    total_errors = 0
    total_warnings = 0

    for slug in slugs:
        bundle_root = DEFAULT_OUTPUT_ROOT / slug
        manifest_path = bundle_root / "manifest.json"
        workshop_id = ""
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            workshop_id = manifest.get("workshop_id", "")

        print(f"\nValidating: {slug}" + (f" (workshop: {workshop_id})" if workshop_id else ""))

        all_issues: list[ValidationIssue] = []

        # 1. Tech IDs
        tech_issues = validate_tech_ids(slug, bundle_root, hoi4_dir, workshop_root)
        all_issues.extend(tech_issues)
        compiled_file = SCRIPTED_EFFECTS_DIR / f"tbm_compat_generated_{slug}.txt"
        tech_total = len(set(re.findall(r"set_technology\s*=\s*\{\s*(\w+)\s*=\s*1",
                                        compiled_file.read_text(encoding="utf-8")
                                        if compiled_file.exists() else "")))
        if not tech_issues:
            print(f"  [PASS] Tech IDs: {tech_total} verified, 0 missing")
        elif all(i.severity == "WARN" and "not installed" in i.message for i in tech_issues):
            print(f"  [SKIP] Tech IDs: mod not installed locally")
        else:
            for i in tech_issues:
                print(f"  [{i.severity}] Tech IDs: {i.message}")

        # 2. Counter variables
        counter_issues = validate_counter_variables(slug)
        all_issues.extend(counter_issues)
        if not counter_issues:
            print(f"  [PASS] Counter variables: all references correct")
        else:
            for i in counter_issues:
                print(f"  [{i.severity}] Counter vars: {i.message}")

        # 3. Dispatch linkage
        link_issues = validate_dispatch_linkage(slug)
        all_issues.extend(link_issues)
        if not link_issues:
            print(f"  [PASS] Dispatch linkage: all effects matched")
        else:
            for i in link_issues:
                print(f"  [{i.severity}] Dispatch: {i.message}")

        # 4. Year slices
        year_issues = validate_year_slices(slug)
        all_issues.extend(year_issues)
        if not year_issues:
            print(f"  [PASS] Year-slices: all reachable")
        else:
            for i in year_issues:
                print(f"  [{i.severity}] Year-slices: {i.message}")

        # 5. Category flags
        flag_issues = validate_category_flags(slug)
        all_issues.extend(flag_issues)
        if not flag_issues:
            print(f"  [PASS] Category flags: all valid")
        else:
            for i in flag_issues:
                print(f"  [{i.severity}] Flags: {i.message}")

        # 6. Tier effect
        tier_issues = validate_tier_effect(slug)
        all_issues.extend(tier_issues)
        if not tier_issues:
            print(f"  [PASS] Tier effect: defined")
        else:
            for i in tier_issues:
                print(f"  [{i.severity}] Tier: {i.message}")

        # 7. Known XOR pairs
        xor_issues = validate_known_xor_pairs(slug)
        all_issues.extend(xor_issues)
        if not xor_issues:
            print(f"  [PASS] XOR pairs: known exclusions preserved")
        else:
            for i in xor_issues:
                print(f"  [{i.severity}] XOR: {i.message}")

        errors = sum(1 for i in all_issues if i.severity == "ERROR")
        warnings = sum(1 for i in all_issues if i.severity == "WARN")
        total_errors += errors
        total_warnings += warnings

    print(f"\nSummary: {len(slugs)} profiles validated, {total_errors} errors, {total_warnings} warnings")
    return total_errors


# ============================================================================
# CLI — SUBCOMMAND HANDLERS
# ============================================================================

def cmd_scan(args) -> int:
    hoi4_dir = Path(args.hoi4)
    if not hoi4_dir.exists():
        raise SystemExit(f"HOI4 directory not found: {hoi4_dir}")

    if args.mod_path:
        mod_dir = Path(args.mod_path)
    elif args.workshop_id:
        mod_dir = Path(args.workshop_root) / args.workshop_id
    else:
        raise SystemExit("Provide --mod-path or --workshop-id")

    if not mod_dir.exists():
        raise SystemExit(f"Mod directory not found: {mod_dir}")

    custom_mappings = load_custom_mappings(CUSTOM_MAPPINGS_PATH)
    if custom_mappings:
        CATEGORY_MAP.update(custom_mappings)

    mod_name = parse_descriptor_name(mod_dir)
    print(f"\nScanning: {mod_name}")
    print(f"Path: {mod_dir}")
    print(f"{'=' * 60}")

    vanilla_techs = parse_tech_files(hoi4_dir / "common" / "technologies", "vanilla", args.verbose)
    mod_techs = parse_tech_files(mod_dir / "common" / "technologies", "mod", args.verbose)

    print(f"\nVanilla techs: {len(vanilla_techs)}")
    print(f"Mod techs: {len(mod_techs)}")

    vanilla_ids = {t.tech_id for t in vanilla_techs}
    mod_ids = {t.tech_id for t in mod_techs}
    overlap = vanilla_ids & mod_ids
    mod_only = mod_ids - vanilla_ids

    print(f"Overlap with vanilla: {len(overlap)}")
    print(f"Mod-exclusive: {len(mod_only)}")

    # Suggest mode
    if len(overlap) > len(vanilla_ids) * 0.5:
        print(f"\nSuggested mode: overhaul (mod replaces >50% of vanilla techs)")
    else:
        print(f"\nSuggested mode: expansion (mod adds techs alongside vanilla)")

    # Show branch breakdown
    all_techs = [t for t in vanilla_techs if t.tech_id not in mod_ids]
    all_techs.extend(mod_techs)
    calculate_dependency_depths(all_techs)

    known = [t for t in all_techs if t.branch != "unknown" and not t.is_doctrine]
    unknown = [t for t in all_techs if t.branch == "unknown"]
    doctrines = [t for t in all_techs if t.is_doctrine]

    print(f"\nMapped techs: {len(known)}")
    print(f"Doctrines: {len(doctrines)}")
    print(f"Unmapped: {len(unknown)}")

    branch_counts = {}
    for t in known:
        key = (t.branch, t.category)
        branch_counts[key] = branch_counts.get(key, 0) + 1

    print(f"\nBranch / Category breakdown:")
    for (branch, category), count in sorted(branch_counts.items()):
        print(f"  {branch:>25} / {category:<20} {count:>4}")

    if unknown and args.verbose:
        print(f"\nUnmapped techs:")
        for t in sorted(unknown, key=lambda x: x.tech_id):
            print(f"  {t.tech_id} (categories: {t.categories})")

    return 0


def cmd_generate(args) -> int:
    hoi4_dir = Path(args.hoi4)
    workshop_root = Path(args.workshop_root)
    output_root = Path(args.output_root)

    if not hoi4_dir.exists():
        raise SystemExit(f"HOI4 directory not found: {hoi4_dir}")

    custom_mappings = load_custom_mappings(CUSTOM_MAPPINGS_PATH)
    if custom_mappings:
        CATEGORY_MAP.update(custom_mappings)

    output_root.mkdir(parents=True, exist_ok=True)
    index = load_index(output_root / "index.json")

    # Custom mod path or workshop ID
    if getattr(args, 'mod_path', None) or getattr(args, 'workshop_id', None):
        if not args.slug:
            raise SystemExit("--slug is required when using --mod-path or --workshop-id")
        if args.mod_path:
            mod_dir = Path(args.mod_path)
            wid = args.workshop_id if hasattr(args, 'workshop_id') else None
        else:
            if not workshop_root.exists():
                raise SystemExit(f"Workshop root not found: {workshop_root}")
            mod_dir = workshop_root / args.workshop_id
            wid = args.workshop_id

        if not mod_dir.exists():
            raise SystemExit(f"Mod directory not found: {mod_dir}")

        preset = resolve_preset_from_args(args)
        entry = build_bundle(
            hoi4_dir=hoi4_dir, mod_dir=mod_dir, slug=args.slug,
            display_name=args.display_name, mode=args.mode,
            preset=preset, output_root=output_root, workshop_id=wid,
        )
        upsert_index_entry(index, entry)
        write_index(output_root / "index.json", index)
        print(f"\nWrote compat bundle: {entry['slug']}")
        return 0

    # Major profiles
    if not workshop_root.exists():
        raise SystemExit(f"Workshop root not found: {workshop_root}")

    profiles = list(MAJOR_MOD_PROFILES)
    if getattr(args, 'profile', None):
        wanted = set(args.profile)
        profiles = [p for p in profiles if p["slug"] in wanted]
        missing = sorted(wanted - {p["slug"] for p in profiles})
        if missing:
            raise SystemExit(f"Unknown profile slug(s): {', '.join(missing)}")

    written = []
    for profile in profiles:
        mod_dir = workshop_root / profile["workshop_id"]
        if not mod_dir.exists():
            if getattr(args, 'fail_missing', False):
                raise SystemExit(f"Workshop mod not found for {profile['slug']}: {mod_dir}")
            continue

        preset = resolve_preset(profile)
        entry = build_bundle(
            hoi4_dir=hoi4_dir, mod_dir=mod_dir, slug=profile["slug"],
            display_name=None, mode=profile["mode"],
            preset=preset, output_root=output_root,
            workshop_id=profile["workshop_id"],
        )
        upsert_index_entry(index, entry)
        written.append(entry)

    write_index(output_root / "index.json", index)
    print(f"\nGenerated {len(written)} compat bundle(s) in {output_root}")
    for item in written:
        print(f"  - {item['slug']}: techs={item['stats']['techs_total']} "
              f"unknown={item['stats']['unknown_total']} preset={item['preset']}")
    return 0


def cmd_build(args) -> int:
    hoi4_dir = Path(args.hoi4)
    if not hoi4_dir.exists():
        raise SystemExit(f"HOI4 directory not found: {hoi4_dir}")

    refresh_core_runtime_outputs(hoi4_dir)
    compile_builtin_profiles()
    index = load_index(DEFAULT_OUTPUT_ROOT / "index.json")
    update_game_rules(index)
    update_localisation(index)
    return 0


def cmd_rebuild(args) -> int:
    cmd_generate(args)
    cmd_build(args)
    print("\nRebuilt TBM compatibility bundles and cleaned legacy core runtime files.")
    return 0


def cmd_list(args) -> int:
    index = load_index(DEFAULT_OUTPUT_ROOT / "index.json")
    generated = {item["slug"]: item for item in index.get("generated_bundles", [])}

    print("Known builtin profiles:")
    for profile in MAJOR_MOD_PROFILES:
        gen = generated.get(profile["slug"])
        suffix = "generated" if gen else "missing"
        techs = f" techs={gen['stats']['techs_total']}" if gen else ""
        print(f"  - {profile['slug']}: {profile['display_name']} [{suffix}]{techs}")

    extra = sorted(slug for slug in generated
                   if slug not in {p["slug"] for p in MAJOR_MOD_PROFILES})
    if extra:
        print("\nCustom/generated-only bundles:")
        for slug in extra:
            item = generated[slug]
            print(f"  - {slug}: {item.get('display_name', slug)}")
    return 0


def cmd_validate(args) -> int:
    hoi4_dir = Path(args.hoi4)
    workshop_root = Path(args.workshop_root)

    if not hoi4_dir.exists():
        raise SystemExit(f"HOI4 directory not found: {hoi4_dir}")

    index = load_index(DEFAULT_OUTPUT_ROOT / "index.json")
    all_slugs = [item["slug"] for item in index.get("generated_bundles", [])]

    if args.slug:
        slugs = args.slug
        missing = [s for s in slugs if s not in all_slugs]
        if missing:
            raise SystemExit(f"Unknown slug(s) not in index: {', '.join(missing)}")
    else:
        slugs = all_slugs

    if not slugs:
        print("No profiles to validate. Run 'generate' first.")
        return 0

    errors = run_validation(slugs, hoi4_dir, workshop_root, args.verbose)
    return 1 if errors > 0 else 0


# ============================================================================
# CLI — PRESET RESOLUTION HELPER
# ============================================================================

def resolve_preset_from_args(args) -> dict | None:
    if hasattr(args, 'preset_name') and args.preset_name:
        if args.preset_name not in PRESETS:
            raise SystemExit(f"Unknown preset: {args.preset_name}")
        preset = dict(PRESETS[args.preset_name])
        preset["name"] = args.preset_name
        return preset

    threshold_values = [
        getattr(args, 'superpower', None),
        getattr(args, 'great_power', None),
        getattr(args, 'regional_power', None),
        getattr(args, 'minor_industrial', None),
        getattr(args, 'minor', None),
    ]
    if any(value is not None for value in threshold_values):
        if not all(value is not None for value in threshold_values):
            raise SystemExit(
                "Custom thresholds require all five values: "
                "--superpower, --great-power, --regional-power, --minor-industrial, --minor"
            )
        return {
            "name": getattr(args, 'preset_label', None) or args.slug,
            "description": getattr(args, 'preset_description', None) or f"Custom preset for {args.slug}",
            "tier_thresholds": {
                "superpower": args.superpower,
                "great_power": args.great_power,
                "regional_power": args.regional_power,
                "minor_industrial": args.minor_industrial,
                "minor": args.minor,
            },
        }
    return None


# ============================================================================
# CLI — ARGUMENT PARSER
# ============================================================================

def add_shared_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--hoi4", default=str(DEFAULT_HOI4_PATH),
                        help="Path to the HOI4 install directory")
    parser.add_argument("--workshop-root", default=str(DEFAULT_WORKSHOP_ROOT),
                        help="Path to workshop/content/394360")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT),
                        help="Bundle output directory")


def add_preset_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--preset-name", help="Use an existing preset")
    parser.add_argument("--preset-label", help="Name for a custom threshold preset")
    parser.add_argument("--preset-description", help="Description for a custom preset")
    parser.add_argument("--superpower", type=int, help="Custom superpower threshold")
    parser.add_argument("--great-power", dest="great_power", type=int)
    parser.add_argument("--regional-power", dest="regional_power", type=int)
    parser.add_argument("--minor-industrial", dest="minor_industrial", type=int)
    parser.add_argument("--minor", type=int)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Tech Baseline Mechanics — Unified Compatibility Profile Tool"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # scan
    scan_p = subparsers.add_parser("scan", help="Scan a mod's tech tree (read-only)")
    scan_p.add_argument("--hoi4", default=str(DEFAULT_HOI4_PATH))
    scan_p.add_argument("--workshop-root", default=str(DEFAULT_WORKSHOP_ROOT))
    scan_p.add_argument("--mod-path", help="Path to mod directory")
    scan_p.add_argument("--workshop-id", help="Workshop ID to scan")
    scan_p.add_argument("--verbose", action="store_true")
    scan_p.set_defaults(func=cmd_scan)

    # generate
    gen_p = subparsers.add_parser("generate", help="Generate compat staging bundles")
    add_shared_args(gen_p)
    gen_p.add_argument("--profile", action="append",
                       help="Only generate named builtin profile slug. Repeatable.")
    gen_p.add_argument("--all", action="store_true", dest="generate_all",
                       help="Generate all major profiles (default when no --mod-path/--workshop-id)")
    gen_p.add_argument("--mod-path", help="Path to an arbitrary mod directory")
    gen_p.add_argument("--workshop-id", help="Workshop ID for arbitrary mod")
    gen_p.add_argument("--slug", help="Output bundle slug (required for custom mods)")
    gen_p.add_argument("--display-name", help="Override display name")
    gen_p.add_argument("--mode", choices=["expansion", "overhaul"], default="overhaul")
    gen_p.add_argument("--fail-missing", action="store_true")
    gen_p.add_argument("--verbose", action="store_true")
    add_preset_args(gen_p)
    gen_p.set_defaults(func=cmd_generate)

    # build
    build_p = subparsers.add_parser(
        "build",
        help="Refresh core runtime outputs and clean legacy baked compat files",
    )
    build_p.add_argument("--hoi4", default=str(DEFAULT_HOI4_PATH))
    build_p.set_defaults(func=cmd_build)

    # rebuild
    rebuild_p = subparsers.add_parser(
        "rebuild",
        help="Generate bundles + refresh core runtime outputs",
    )
    add_shared_args(rebuild_p)
    rebuild_p.add_argument("--profile", action="append")
    rebuild_p.add_argument("--fail-missing", action="store_true")
    rebuild_p.add_argument("--verbose", action="store_true")
    rebuild_p.set_defaults(func=cmd_rebuild)

    # list
    list_p = subparsers.add_parser("list", help="List known and generated profiles")
    list_p.set_defaults(func=cmd_list)

    # validate
    val_p = subparsers.add_parser("validate", help="Validate generated profiles for correctness")
    val_p.add_argument("--hoi4", default=str(DEFAULT_HOI4_PATH))
    val_p.add_argument("--workshop-root", default=str(DEFAULT_WORKSHOP_ROOT))
    val_p.add_argument("--slug", action="append", help="Validate specific slug(s). Repeatable.")
    val_p.add_argument("--verbose", action="store_true")
    val_p.set_defaults(func=cmd_validate)

    return parser


# ============================================================================
# MAIN
# ============================================================================

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
