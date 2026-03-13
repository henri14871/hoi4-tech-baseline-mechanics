#!/usr/bin/env python3
"""
Arms Race Mechanics — Tech List Generator
==========================================

Reads HOI4 technology files from vanilla and/or mods, parses every tech definition,
maps them to ARM branches and categories, and outputs curated tech list files that
drop directly into the Arms Race Mechanics mod folder.

Usage:
    python arm_tech_generator.py --hoi4 "C:/Program Files/Steam/steamapps/common/Hearts of Iron IV"
    python arm_tech_generator.py --hoi4 "/path/to/hoi4" --mods "/path/to/mod1" "/path/to/mod2"
    python arm_tech_generator.py --hoi4 "/path/to/hoi4" --mods "/path/to/kaiserreich" --mode overhaul
    python arm_tech_generator.py --hoi4 "/path/to/hoi4" --auto-detect

Options:
    --hoi4          Path to HOI4 installation directory (required)
    --mods          One or more paths to mod directories
    --auto-detect   Auto-detect active mods from HOI4 launcher settings
    --mode          'expansion' (default) or 'overhaul'
                    expansion: generates additional files alongside vanilla lists
                    overhaul: generates replacement files that override vanilla lists
    --output        Output directory (default: current directory)
    --preset        Load a tier threshold preset (e.g. 'kaiserreich', 'millennium_dawn')
    --dry-run       Parse and report without writing files
    --verbose       Print detailed parsing info
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# ============================================================================
# CATEGORY TAG → BRANCH/CATEGORY MAPPING
# ============================================================================
# This is the core mapping table. HOI4 techs have 'categories = { ... }' blocks
# containing tags like 'infantry_weapons', 'cat_fighter', 'armor', etc.
# We map these to ARM branches and categories.
#
# Priority order matters — if a tech has multiple category tags, the first match
# in this list wins. More specific tags should come before generic ones.
#
# Users can extend this via custom_mappings.txt (see below).

CATEGORY_MAP = {
    # ══════════════════════════════════════════════════════════════════
    # ORDERING IS PRIORITY — matching iterates this dict in insertion
    # order and picks the FIRST key that appears in a tech's categories.
    # More specific equipment/vehicle tags BEFORE generic unit-type tags.
    # ══════════════════════════════════════════════════════════════════

    # ── Land / Tanks (most specific — BEFORE generic 'armor' and infantry) ──
    "cat_light_armor":          ("land", "light_tanks"),
    "cat_medium_armor":         ("land", "medium_tanks"),
    "cat_heavy_armor":          ("land", "heavy_tanks"),
    "cat_super_heavy_armor":    ("land", "heavy_tanks"),
    "cat_modern_armor":         ("land", "modern_tanks"),
    "armor":                    ("land", "tanks_generic"),

    # ── Land / Mechanised (BEFORE motorised — mech techs also have motorized_equipment) ──
    "cat_mechanized":           ("land", "mechanised"),
    "cat_mechanized_equipment": ("land", "mechanised"),
    "mechanized_equipment":     ("land", "mechanised"),

    # ── Land / Anti-Air & Anti-Tank (BEFORE artillery — AA/AT techs also have cat_artillery) ──
    "cat_anti_tank":            ("land", "anti_tank"),
    "cat_anti_air":             ("land", "anti_air"),
    "anti_air":                 ("land", "anti_air"),

    # ── Land / Artillery (after AA/AT) ──
    "artillery":                ("land", "artillery"),
    "cat_artillery":            ("land", "artillery"),
    "rocket_artillery":         ("land", "artillery"),

    # ── Land / Support (BEFORE motorised — support techs also have motorized_equipment) ──
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

    # ── Land / Motorised (AFTER support — motorized_equipment is broad, many techs have it) ──
    "motorized_equipment":      ("land", "motorised"),
    "motorized_tech":           ("land", "motorised"),

    # ── Land / Special Forces (mapped to infantry) ──
    "cat_special_forces_generic": ("land", "infantry"),
    "marine_tech":              ("land", "infantry"),
    "para_tech":                ("land", "infantry"),
    "mountaineers_tech":        ("land", "infantry"),

    # ── Land / Infantry (most generic land tag — LAST among land types) ──
    "infantry_weapons":         ("land", "infantry"),
    "infantry_tech":            ("land", "infantry"),

    # ── Air / Heavy Fighters (BEFORE generic fighter tags) ──
    "cat_heavy_fighter":        ("air", "heavy_fighters"),
    "heavy_fighter":            ("air", "heavy_fighters"),

    # ── Air / Fighters ──
    "light_fighter":            ("air", "fighters"),
    "cat_fighter":              ("air", "fighters"),
    # NOTE: jet_technology intentionally NOT mapped — it is a capability
    # tag shared by jet fighters, jet bombers, and jet airframes.  The
    # specific class tags (cat_fighter, tactical_bomber, cat_strategic_bomber,
    # etc.) are the correct discriminators.

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

    # ── Naval / Submarines (BEFORE destroyers — some shared techs) ──
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

    # ── Industry / Radar (BEFORE generic electronics — radar techs also have 'electronics') ──
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

# Minimum tier assignment based on category
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

# Minimum branch score by category
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
# Map known DLC-specific filenames to their DLC requirement.
# Techs from these files get wrapped in has_dlc checks so the mod works
# regardless of which expansions the player owns.

DLC_FILE_MAP = {
    "mtg_naval.txt":            "Man the Guns",
    "mtg_naval_support.txt":    "Man the Guns",
    "nsb_armor.txt":            "No Step Back",
    "bba_air_techs.txt":        "By Blood Alone",
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
            # Skip to end of line
            while i < len(text) and text[i] != '\n':
                i += 1
            continue
        else:
            result.append(c)
        i += 1
    return ''.join(result)


def parse_tech_files(tech_dir: Path, mod_name: str = "vanilla", verbose: bool = False) -> list:
    """
    Parse all .txt files in a technologies directory.
    Returns a list of TechDef objects.
    """
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

        # Tag techs from DLC-specific files
        dlc_name = DLC_FILE_MAP.get(filepath.name.lower(), "")
        if dlc_name:
            for t in file_techs:
                t.dlc_required = dlc_name

        techs.extend(file_techs)

    return techs


def extract_techs_from_text(text: str, source_file: str, mod_name: str, verbose: bool) -> list:
    """
    Extract tech definitions from cleaned Clausewitz text.
    
    Looks for top-level blocks of the form:
        tech_id = { ... }
    
    and parses start_year, categories, and dependencies from within.
    """
    techs = []
    
    # Tokenize: find top-level key = { ... } blocks
    # We need to handle nested braces properly
    pos = 0
    length = len(text)
    
    while pos < length:
        # Skip whitespace
        while pos < length and text[pos] in ' \t\n\r':
            pos += 1
        
        if pos >= length:
            break
        
        # Try to read an identifier
        id_start = pos
        while pos < length and text[pos] not in ' \t\n\r={}':
            pos += 1
        
        identifier = text[id_start:pos].strip()
        
        if not identifier:
            pos += 1
            continue
        
        # Skip whitespace
        while pos < length and text[pos] in ' \t\n\r':
            pos += 1
        
        if pos >= length:
            break
        
        # Expect '='
        if text[pos] != '=':
            pos += 1
            continue
        pos += 1  # skip '='
        
        # Skip whitespace
        while pos < length and text[pos] in ' \t\n\r':
            pos += 1
        
        if pos >= length:
            break
        
        # Expect '{'
        if text[pos] != '{':
            # Not a block, skip this value
            while pos < length and text[pos] not in '\n\r':
                pos += 1
            continue
        
        # Find matching closing brace
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

        # HOI4 tech files wrap everything in a top-level 'technologies = { ... }' block.
        # Also, DLC conditionals (if/else/else_if) may wrap tech definitions.
        # In both cases, recurse into the inner content.
        if identifier in ('technologies', 'if', 'else', 'else_if'):
            inner_content = block_content[1:-1] if len(block_content) > 2 else ''
            inner_techs = extract_techs_from_text(inner_content, source_file, mod_name, verbose)
            techs.extend(inner_techs)
            continue

        # Filter: only consider blocks that look like tech definitions
        # Tech blocks typically contain research_cost, categories, or enable_equipments
        if is_tech_block(block_content):
            tech = parse_single_tech(identifier, block_content, source_file, mod_name)
            if tech:
                techs.append(tech)
                if verbose:
                    print(f"    [TECH] {tech.tech_id} | year={tech.start_year} | "
                          f"branch={tech.branch} | cat={tech.category} | "
                          f"deps={tech.dependencies}")

    return techs


def is_tech_block(block: str) -> bool:
    """Heuristic: does this block look like a technology definition?"""
    indicators = [
        'research_cost',
        'categories',
        'enable_equipments',
        'enable_equipment_modules',
        'enable_subunits',
        'start_year',
        'folder',
        'path',
    ]
    block_lower = block.lower()
    return any(ind in block_lower for ind in indicators)


def parse_single_tech(tech_id: str, block: str, source_file: str, mod_name: str) -> Optional[TechDef]:
    """Parse a single technology block into a TechDef."""
    
    # Skip known non-tech identifiers
    skip_ids = {'technologies', 'if', 'else', 'limit', 'OR', 'AND', 'NOT',
                'has_dlc', 'folder', 'doctrine', 'sub_technologies'}
    if tech_id in skip_ids:
        return None
    
    # Skip if tech_id contains characters that aren't valid identifiers
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', tech_id):
        return None
    
    tech = TechDef(tech_id=tech_id, source_file=source_file, source_mod=mod_name)
    
    # Extract start_year
    year_match = re.search(r'start_year\s*=\s*(\d{4})', block)
    if year_match:
        tech.start_year = int(year_match.group(1))
    
    # Extract categories
    cat_match = re.search(r'categories\s*=\s*\{([^}]*)\}', block)
    if cat_match:
        cats = cat_match.group(1).split()
        tech.categories = [c.strip() for c in cats if c.strip()]
    
    # Extract dependencies
    dep_match = re.search(r'dependencies\s*=\s*\{([^}]*)\}', block)
    if dep_match:
        # Dependencies are in format: tech_id = 1
        deps = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\d+', dep_match.group(1))
        tech.dependencies = deps
    
    # Check for XP gating
    if 'xp_research_type' in block or 'xp_cost' in block:
        tech.is_xp_gated = True
    
    # Check if doctrine
    if any(cat in tech.categories for cat in
           ['land_doctrine', 'naval_doctrine', 'air_doctrine',
            'cat_mobile_warfare', 'cat_superior_firepower',
            'cat_grand_battle_plan', 'cat_mass_assault',
            'cat_fleet_in_being', 'cat_trade_interdiction',
            'cat_base_strike']):
        tech.is_doctrine = True
    
    # Map to ARM branch and category
    map_tech_to_branch(tech)
    
    return tech


def map_tech_to_branch(tech: TechDef):
    """Map a tech's category tags to an ARM branch and category.

    Iterates CATEGORY_MAP in insertion order (priority order) and picks
    the first map entry whose key appears in the tech's categories.
    This gives us explicit control over priority — more specific tags
    must be listed before generic ones in the CATEGORY_MAP dict.
    """
    cat_set = set(tech.categories)

    # Current vanilla cruiser techs share ca_tech and are only separated by
    # screen/capital ship MIO tags.
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

    # Current vanilla main battle tank techs are tagged as medium armor.
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
    
    # Fallback: try partial matching for modded category tags.
    # Skip generic/ambiguous tags that would cause misclassification.
    SKIP_TAGS = {'naval_air', 'naval_equipment', 'air_equipment', 'light_air',
                 'medium_air', 'heavy_air', 'jet_technology', 'plane_modules_tech'}

    for cat_tag in tech.categories:
        if cat_tag.lower() in SKIP_TAGS:
            continue
        cat_lower = cat_tag.lower()

        # Try keyword matching — more specific patterns first
        if any(kw in cat_lower for kw in ['infantry', 'rifle', 'small_arms']):
            tech.branch, tech.category = "land", "infantry"
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
    
    # Could not map — leave as unknown
    tech.branch = "unknown"
    tech.category = "unknown"


# ============================================================================
# DEPENDENCY DEPTH CALCULATION
# ============================================================================

def calculate_dependency_depths(techs: list):
    """Calculate the dependency chain depth for each tech (used for tier heuristics)."""
    tech_map = {t.tech_id: t for t in techs}
    
    def get_depth(tech_id: str, visited: set = None) -> int:
        if visited is None:
            visited = set()
        if tech_id in visited:
            return 0  # Circular dependency guard
        if tech_id not in tech_map:
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
        
        # Adjust min_tier upward for deep dependency chains
        # (techs deep in the tree are more advanced)
        if tech.min_tier not in ("superpower",) and tech.dependency_depth >= 4:
            tech.min_tier = "great_power"
        elif tech.min_tier not in ("superpower", "great_power") and tech.dependency_depth >= 3:
            if tech.min_tier in ("micro", "minor", "minor_industrial"):
                tech.min_tier = "regional_power"


# ============================================================================
# CUSTOM MAPPING LOADER
# ============================================================================

def load_custom_mappings(filepath: Path) -> dict:
    """
    Load user-defined category tag mappings from a simple text file.
    
    Format (one per line):
        modded_tag_name → branch / category
    
    Example:
        my_mod_heavy_mech → land / mechanised
        special_radar_tech → industry_electronics / radar
    """
    custom = {}
    if not filepath.exists():
        return custom
    
    print(f"[INFO] Loading custom mappings from {filepath}")
    
    for line in filepath.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Support both → and -> as separator
        sep = '→' if '→' in line else '->'
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
        print(f"  [MAP] {tag} → {branch} / {category}")
    
    return custom


# ============================================================================
# OUTPUT GENERATOR
# ============================================================================

TIER_ORDER = ["micro", "minor", "minor_industrial", "regional_power", "great_power", "superpower"]

TARGET_YEAR_VAR_BY_BRANCH = {
    "land": "arm_target_year_land",
    "air": "arm_target_year_air",
    "naval": "arm_target_year_naval",
    "industry_electronics": "arm_target_year_industry",
}

COMPETENCE_VAR_BY_BRANCH = {
    "land": "arm_land_competence",
    "air": "arm_air_competence",
    "naval": "arm_naval_competence",
    "industry_electronics": "arm_industry_competence",
}

CATEGORY_FLAG_BY_CATEGORY = {
    "infantry": "arm_cat_infantry",
    "support": "arm_cat_support",
    "artillery": "arm_cat_artillery",
    "anti_air": "arm_cat_anti_air",
    "anti_tank": "arm_cat_anti_tank",
    "industry": "arm_cat_industry",
    "electronics": "arm_cat_electronics",
    "radar": "arm_cat_radar",
    "motorised": "arm_cat_motorised",
    "mechanised": "arm_cat_mechanised",
    "light_tanks": "arm_cat_light_tanks",
    "medium_tanks": "arm_cat_medium_tanks",
    "heavy_tanks": "arm_cat_heavy_tanks",
    "modern_tanks": "arm_cat_modern_tanks",
    "tanks_generic": "arm_cat_tanks_generic",
    "fighters": "arm_cat_fighters",
    "heavy_fighters": "arm_cat_heavy_fighters",
    "cas": "arm_cat_cas",
    "tactical_bombers": "arm_cat_tactical_bombers",
    "strategic_bombers": "arm_cat_strategic_bombers",
    "naval_bombers": "arm_cat_naval_bombers",
    "transport": "arm_cat_transport",
    "submarines": "arm_cat_submarines",
    "destroyers": "arm_cat_destroyers",
    "light_cruisers": "arm_cat_light_cruisers",
    "heavy_cruisers": "arm_cat_heavy_cruisers",
    "battleships": "arm_cat_battleships",
    "carriers": "arm_cat_carriers",
    "naval_support": "arm_cat_naval_support",
    "nuclear": "arm_cat_nuclear",
    "rockets": "arm_cat_rockets",
}

ADVANCED_TECH_CATEGORIES = {"nuclear", "rockets"}


def target_year_var_for_branch(branch: str) -> str:
    return TARGET_YEAR_VAR_BY_BRANCH.get(branch, f"arm_target_year_{branch}")


def competence_var_for_branch(branch: str) -> str:
    return COMPETENCE_VAR_BY_BRANCH.get(branch, f"arm_{branch}_competence")


def category_flag_for(category: str) -> str:
    return CATEGORY_FLAG_BY_CATEGORY.get(category, "")


def is_runtime_supported_tech(tech: TechDef) -> bool:
    # Doctrines are handled directly in scripted effects for current HOI4.
    return tech.branch != "unknown" and not tech.is_doctrine


def append_grant_limit_lines(lines: list, tech: TechDef, counter_var: str = "arm_grant_counter",
                             cap_var: str = "arm_quarterly_cap"):
    lines.append(
        f"            check_variable = {{ var = {counter_var} value = {cap_var} compare = less_than }}"
    )
    lines.append(
        f"            check_variable = {{ var = {target_year_var_for_branch(tech.branch)} "
        f"value = {tech.start_year} compare = greater_than_or_equals }}"
    )

    tier_index = TIER_ORDER.index(tech.min_tier) if tech.min_tier in TIER_ORDER else 0
    if tier_index > 0:
        lines.append(
            f"            check_variable = {{ var = arm_tier_index value = {tier_index} "
            f"compare = greater_than_or_equals }}"
        )

    if tech.min_branch_score > 0:
        lines.append(
            f"            check_variable = {{ var = {competence_var_for_branch(tech.branch)} "
            f"value = {tech.min_branch_score} compare = greater_than_or_equals }}"
        )

    category_flag = category_flag_for(tech.category)
    if category_flag:
        lines.append(f"            has_country_flag = {category_flag}")

    if tech.category in ADVANCED_TECH_CATEGORIES:
        lines.append("            arm_advanced_tech_allowed = yes")

    for dep in tech.dependencies:
        lines.append(f"            has_tech = {dep}")

    if tech.dlc_required:
        lines.append(f'            has_dlc = "{tech.dlc_required}"')


def generate_output_files(techs: list, output_dir: Path, mode: str, mod_name: str,
                          report_dir: Optional[Path] = None):
    """Generate ARM-compatible scripted effect files from parsed techs."""

    output_dir.mkdir(parents=True, exist_ok=True)
    if report_dir is None:
        report_dir = output_dir
    
    # Filter out unknown techs
    known_techs = [t for t in techs if is_runtime_supported_tech(t)]
    unknown_techs = [t for t in techs if t.branch == "unknown"]
    
    if unknown_techs:
        print(f"\n[WARN] {len(unknown_techs)} techs could not be mapped to a branch:")
        for t in unknown_techs[:20]:
            print(f"  - {t.tech_id} (categories: {t.categories}) from {t.source_mod}")
        if len(unknown_techs) > 20:
            print(f"  ... and {len(unknown_techs) - 20} more")
        print(f"  Add mappings to custom_mappings.txt to include these.")
    
    # Group by branch and category
    grouped = {}
    for tech in known_techs:
        key = (tech.branch, tech.category)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(tech)
    
    # Sort within each group by year then dependency depth
    for key in grouped:
        grouped[key].sort(key=lambda t: (t.start_year, t.dependency_depth))
    
    # Generate the scripted effects file
    # Always use the same filename — the file contains the complete merged
    # techlist (vanilla + mods) and replaces any previous version.
    filename = "auto_research_techlist.txt"
    filepath = output_dir / filename
    
    lines = []
    lines.append(f"# ═══════════════════════════════════════════════════════════════════")
    lines.append(f"# Arms Race Mechanics — Auto-Generated Tech Lists")
    lines.append(f"# Source: {mod_name}")
    lines.append(f"# Mode: {mode}")
    lines.append(f"# Total techs mapped: {len(known_techs)}")
    lines.append(f"# Unmapped techs: {len(unknown_techs)}")
    lines.append(f"# ═══════════════════════════════════════════════════════════════════")
    lines.append(f"# THIS FILE IS AUTO-GENERATED. Do not edit manually.")
    lines.append(f"# Re-run arm_tech_generator.py to regenerate.")
    lines.append(f"# ═══════════════════════════════════════════════════════════════════")
    lines.append("")
    
    # Generate a scripted effect per branch/category group
    for (branch, category), tech_list in sorted(grouped.items()):
        effect_name = f"arm_grant_{branch}_{category}"
        
        lines.append(f"# ── {branch.upper()} / {category.upper()} ({len(tech_list)} techs) ──")
        lines.append("")
        
        # Write tech data as comments + scripted checks
        # The actual ARM pulse logic reads these and uses add_technology
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
            
            lines.append(f"# {tech.tech_id}")
            lines.append(f"#   year={tech.start_year} branch={tech.branch} "
                        f"category={tech.category}")
            lines.append(f"#   min_tier={tech.min_tier} "
                        f"min_branch_score={tech.min_branch_score}"
                        f"{dep_str}{flag_str}")
            lines.append("")
        
        # Write the actual scripted effect
        lines.append(f"{effect_name} = {{")
        
        for tech in tech_list:
            # XP gate check
            if tech.is_xp_gated:
                lines.append(f"    # SKIPPED (XP-gated): {tech.tech_id}")
                continue

            lines.append(f"    # {tech.tech_id} — {tech.start_year}")
            lines.append(f"    if = {{")
            lines.append(f"        limit = {{")
            lines.append(f"            NOT = {{ has_tech = {tech.tech_id} }}")
            append_grant_limit_lines(lines, tech)

            lines.append(f"        }}")
            lines.append(f"        add_technology = {tech.tech_id}")
            lines.append(f"        add_to_variable = {{ arm_grant_counter = 1 }}")
            lines.append(f"    }}")
        
        lines.append(f"}}")
        lines.append("")
    
    # Generate empty stubs for any expected effects that had no techs.
    # This prevents HOI4 from logging errors when arm_grant.txt calls them.
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
    for (branch, category) in EXPECTED_EFFECTS:
        if (branch, category) not in grouped:
            effect_name = f"arm_grant_{branch}_{category}"
            lines.append(f"# ── {branch.upper()} / {category.upper()} (0 techs) ──")
            lines.append(f"{effect_name} = {{")
            lines.append(f"    # No techs matched this category.")
            lines.append(f"}}")
            lines.append("")

    # Write to file
    filepath.write_text('\n'.join(lines), encoding='utf-8')
    print(f"\n[OUTPUT] Written: {filepath}")
    print(f"         {len(known_techs)} techs in {len(grouped)} categories")
    
    # Generate the summary report (in report_dir, typically Tools/)
    report_path = report_dir / "arm_tech_report.txt"
    generate_report(techs, known_techs, unknown_techs, grouped, report_path)
    
    return filepath


def generate_mod_output_files(techs: list, output_dir: Path, mod_suffix: str,
                              mod_check: str, report_dir: Optional[Path] = None):
    """Generate separate mod compatibility files.

    Creates two files:
      1. auto_research_techlist_{mod_suffix}.txt
         — Scripted effects with suffixed names (e.g. arm_grant_land_infantry_rt56)
         — Each tech individually gated by mod_check inside its limit block
      2. arm_grant_{mod_suffix}.txt
         — Small orchestrator that calls the suffixed effects in priority order,
           wrapped in the mod_check condition.  Shares arm_grant_counter with vanilla.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    if report_dir is None:
        report_dir = output_dir

    known_techs = [t for t in techs if is_runtime_supported_tech(t)]
    unknown_techs = [t for t in techs if t.branch == "unknown"]

    if not known_techs:
        print(f"\n[INFO] No mod-exclusive techs to generate for '{mod_suffix}'.")
        return

    # Group by branch and category
    grouped = {}
    for tech in known_techs:
        key = (tech.branch, tech.category)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(tech)

    for key in grouped:
        grouped[key].sort(key=lambda t: (t.start_year, t.dependency_depth))

    # ── File 1: Tech list with suffixed effect names ──────────────
    filename = f"auto_research_techlist_{mod_suffix}.txt"
    filepath = output_dir / filename

    lines = []
    lines.append(f"# ═══════════════════════════════════════════════════════════════════")
    lines.append(f"# Arms Race Mechanics — Mod Tech Lists: {mod_suffix}")
    lines.append(f"# Total techs mapped: {len(known_techs)}")
    lines.append(f"# Unmapped techs: {len(unknown_techs)}")
    lines.append(f"# Mod detection: {mod_check}")
    lines.append(f"# ═══════════════════════════════════════════════════════════════════")
    lines.append(f"# THIS FILE IS AUTO-GENERATED. Do not edit manually.")
    lines.append(f"# Re-run arm_tech_generator.py to regenerate.")
    lines.append(f"# ═══════════════════════════════════════════════════════════════════")
    lines.append("")

    for (branch, category), tech_list in sorted(grouped.items()):
        effect_name = f"arm_grant_{branch}_{category}_{mod_suffix}"

        lines.append(f"# ── {branch.upper()} / {category.upper()} ({len(tech_list)} techs) ──")
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
            lines.append(f"# {tech.tech_id}")
            lines.append(f"#   year={tech.start_year} branch={tech.branch} "
                         f"category={tech.category}")
            lines.append(f"#   min_tier={tech.min_tier} "
                         f"min_branch_score={tech.min_branch_score}"
                         f"{dep_str}{flag_str}")
            lines.append("")

        lines.append(f"{effect_name} = {{")

        for tech in tech_list:
            if tech.is_xp_gated:
                lines.append(f"    # SKIPPED (XP-gated): {tech.tech_id}")
                continue

            lines.append(f"    # {tech.tech_id} — {tech.start_year}")
            lines.append(f"    if = {{")
            lines.append(f"        limit = {{")
            lines.append(f"            NOT = {{ has_tech = {tech.tech_id} }}")
            append_grant_limit_lines(lines, tech)

            lines.append(f"        }}")
            lines.append(f"        add_technology = {tech.tech_id}")
            lines.append(f"        add_to_variable = {{ arm_grant_counter = 1 }}")
            lines.append(f"    }}")

        lines.append(f"}}")
        lines.append("")

    filepath.write_text('\n'.join(lines), encoding='utf-8')
    print(f"\n[OUTPUT] Written: {filepath}")
    print(f"         {len(known_techs)} mod techs in {len(grouped)} categories")

    # ── File 2: Mod orchestrator ──────────────────────────────────
    # Mirrors arm_grant.txt priority structure, but only for categories
    # that actually have mod techs.  Gated by mod_check.
    PRIORITY_ORDER = [
        ("land", "infantry"),
        ("industry_electronics", "industry"),
        ("land", "support"),
        ("land", "artillery"), ("land", "anti_air"), ("land", "anti_tank"),
        ("land", "motorised"), ("land", "mechanised"),
        ("air", "fighters"), ("air", "cas"),
        ("land", "light_tanks"), ("land", "medium_tanks"),
        ("land", "heavy_tanks"), ("land", "modern_tanks"), ("land", "tanks_generic"),
        ("naval", "submarines"), ("naval", "destroyers"),
        ("naval", "light_cruisers"), ("naval", "heavy_cruisers"),
        ("naval", "battleships"), ("naval", "carriers"),
        ("industry_electronics", "electronics"), ("industry_electronics", "radar"),
        ("air", "heavy_fighters"), ("air", "tactical_bombers"),
        ("air", "strategic_bombers"), ("air", "naval_bombers"), ("air", "transport"),
        ("naval", "naval_support"),
        ("industry_electronics", "nuclear"), ("industry_electronics", "rockets"),
    ]

    orch_path = output_dir / f"arm_grant_{mod_suffix}.txt"
    orch = []
    orch.append(f"###############################################################################")
    orch.append(f"# arm_grant_{mod_suffix}.txt — Mod Compatibility Orchestrator")
    orch.append(f"# Mod: {mod_suffix}")
    orch.append(f"# Detection: {mod_check}")
    orch.append(f"#")
    orch.append(f"# Add the following line to arm_evaluate_and_grant in arm_grant.txt")
    orch.append(f"# (after the vanilla grants, before doctrines):")
    orch.append(f"#")
    orch.append(f"#   arm_grant_mod_{mod_suffix} = yes")
    orch.append(f"#")
    orch.append(f"# THIS FILE IS AUTO-GENERATED. Do not edit manually.")
    orch.append(f"###############################################################################")
    orch.append(f"")
    orch.append(f"arm_grant_mod_{mod_suffix} = {{")
    orch.append(f"    # Only run if the mod is active")
    orch.append(f"    if = {{")
    orch.append(f"        limit = {{ {mod_check} }}")
    orch.append(f"")

    # Doctrine effects get their own sub-section
    has_doctrines = False
    for (branch, category) in PRIORITY_ORDER:
        if (branch, category) not in grouped:
            continue
        if branch == "doctrine":
            has_doctrines = True
            continue
        orch.append(f"        arm_grant_{branch}_{category}_{mod_suffix} = yes")

    if has_doctrines:
        orch.append(f"")
        orch.append(f"        # Doctrines (shares arm_doctrine_grant_counter)")
        for (branch, category) in PRIORITY_ORDER:
            if branch == "doctrine" and (branch, category) in grouped:
                orch.append(f"        arm_grant_{branch}_{category}_{mod_suffix} = yes")

    orch.append(f"    }}")
    orch.append(f"}}")

    orch_path.write_text('\n'.join(orch), encoding='utf-8')
    print(f"[OUTPUT] Written: {orch_path}")
    print(f"         Orchestrator: arm_grant_mod_{mod_suffix}")
    print(f"")
    print(f"")
    print(f"  To activate, add this line to arm_grant.txt")
    print(f"  inside arm_evaluate_and_grant (after vanilla grants):")
    print(f"")
    print(f"    arm_grant_mod_{mod_suffix} = yes")

    # Generate mod-specific report
    report_path = report_dir / f"arm_tech_report_{mod_suffix}.txt"
    generate_report(techs, known_techs, unknown_techs, grouped, report_path)

    return filepath


def generate_report(all_techs, known, unknown, grouped, filepath):
    """Generate a human-readable summary report."""
    lines = []
    lines.append("ARMS RACE MECHANICS — TECH LIST GENERATION REPORT")
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
        lines.append(f"\n  [{branch} / {category}] — {len(tech_list)} techs")
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
# MOD AUTO-DETECTION
# ============================================================================

def auto_detect_mods(hoi4_dir: Path) -> list:
    """
    Try to detect active mods from HOI4 launcher settings.
    Looks for dlc_load.json in the HOI4 user directory.
    """
    # Common user data locations
    possible_paths = [
        Path.home() / "Documents" / "Paradox Interactive" / "Hearts of Iron IV",
        Path.home() / ".local" / "share" / "Paradox Interactive" / "Hearts of Iron IV",
    ]
    
    for user_dir in possible_paths:
        dlc_load = user_dir / "dlc_load.json"
        if dlc_load.exists():
            try:
                data = json.loads(dlc_load.read_text(encoding='utf-8'))
                enabled = data.get("enabled_mods", [])
                mod_paths = []
                
                for mod_entry in enabled:
                    # Entries can be like "mod/mymod.mod" or absolute paths
                    if isinstance(mod_entry, str):
                        mod_file = user_dir / mod_entry
                        if mod_file.exists():
                            # Parse .mod file to get path
                            mod_dir = parse_mod_file(mod_file, user_dir)
                            if mod_dir:
                                mod_paths.append(mod_dir)
                
                if mod_paths:
                    print(f"[INFO] Auto-detected {len(mod_paths)} active mods from {dlc_load}")
                    return mod_paths
                    
            except Exception as e:
                print(f"[WARN] Could not parse {dlc_load}: {e}")
    
    print("[WARN] Could not auto-detect mods. Use --mods to specify manually.")
    return []


def parse_mod_file(mod_file: Path, user_dir: Path) -> Optional[Path]:
    """Parse a .mod file to extract the mod's directory path."""
    try:
        text = mod_file.read_text(encoding='utf-8-sig')
        
        # Look for path="..." or path=...
        path_match = re.search(r'path\s*=\s*"?([^"\n]+)"?', text)
        if path_match:
            mod_path = Path(path_match.group(1).strip())
            
            # Could be relative to user dir
            if not mod_path.is_absolute():
                mod_path = user_dir / mod_path
            
            if mod_path.exists():
                return mod_path
    except Exception:
        pass
    
    return None


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
        "notes": "Kaiserreich economies tend to be slightly inflated. Thresholds raised."
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
        "notes": "Modern-era mods have much higher factory counts. Thresholds scaled up."
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
        "notes": "Rt56 keeps vanilla economy scale but adds many techs. Standard thresholds."
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
        "notes": "WW1 economies are smaller. Thresholds reduced."
    },
}


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Arms Race Mechanics — Tech List Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Vanilla only:
    python arm_tech_generator.py --hoi4 "C:/Program Files/Steam/steamapps/common/Hearts of Iron IV"

  Vanilla + expansion mod:
    python arm_tech_generator.py --hoi4 /path/to/hoi4 --mods /path/to/mod1

  Total overhaul (Kaiserreich):
    python arm_tech_generator.py --hoi4 /path/to/hoi4 --mods /path/to/kaiserreich --mode overhaul --preset kaiserreich

  Auto-detect active mods:
    python arm_tech_generator.py --hoi4 /path/to/hoi4 --auto-detect
        """
    )
    
    parser.add_argument('--hoi4', required=True, help='Path to HOI4 installation directory')
    parser.add_argument('--mods', nargs='+', help='Paths to mod directories (can specify multiple)')
    parser.add_argument('--auto-detect', action='store_true', help='Auto-detect active mods')
    parser.add_argument('--mode', choices=['expansion', 'overhaul'], default='expansion',
                        help='expansion (add mod techs alongside vanilla) or overhaul (mod techs replace vanilla)')
    parser.add_argument('--output', default=None,
                        help='Output directory (default: ../common/scripted_effects relative to this script)')
    parser.add_argument('--preset', choices=list(PRESETS.keys()), help='Tier threshold preset')
    parser.add_argument('--custom-mappings', default=None,
                        help='Path to custom category mapping file (default: custom_mappings.txt next to script)')
    parser.add_argument('--mod-name', default=None,
                        help='Short name for the mod (used in filenames and effect names). '
                             'Only alphanumeric/underscores. Defaults to sanitised directory name.')
    parser.add_argument('--mod-check', default=None,
                        help='Clausewitz trigger to detect if a mod is active '
                             '(e.g. "has_global_flag = rt56_active"). '
                             'When set, mod techs are written to a separate file '
                             'so they are only granted when the mod is loaded.')
    parser.add_argument('--dry-run', action='store_true', help='Parse and report without writing')
    parser.add_argument('--verbose', action='store_true', help='Print detailed parsing info')
    
    args = parser.parse_args()

    hoi4_dir = Path(args.hoi4)
    script_dir = Path(__file__).resolve().parent

    # Default output: ../common/scripted_effects relative to this script
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = script_dir.parent / "common" / "scripted_effects"

    if not hoi4_dir.exists():
        print(f"[ERROR] HOI4 directory not found: {hoi4_dir}")
        sys.exit(1)

    # Load custom mappings if available
    custom_map_path = Path(args.custom_mappings) if args.custom_mappings else script_dir / "custom_mappings.txt"
    custom_mappings = load_custom_mappings(custom_map_path)
    if custom_mappings:
        CATEGORY_MAP.update(custom_mappings)
    
    # Load preset if specified
    if args.preset:
        preset = PRESETS[args.preset]
        print(f"\n[INFO] Using preset: {preset['description']}")
        print(f"       {preset['notes']}")
    
    # Collect mod directories
    mod_dirs = []
    if args.auto_detect:
        mod_dirs = auto_detect_mods(hoi4_dir)
    elif args.mods:
        for mod_path in args.mods:
            p = Path(mod_path)
            if p.exists():
                mod_dirs.append(p)
            else:
                print(f"[WARN] Mod directory not found: {p}")
    
    # Parse vanilla techs
    print(f"\n{'=' * 60}")
    print(f"PARSING VANILLA TECHNOLOGIES")
    print(f"{'=' * 60}")
    vanilla_tech_dir = hoi4_dir / "common" / "technologies"
    vanilla_techs = parse_tech_files(vanilla_tech_dir, "vanilla", args.verbose)
    print(f"[INFO] Parsed {len(vanilla_techs)} vanilla techs")
    
    # Parse mod techs (keyed by mod directory)
    mod_techs_by_mod = {}  # mod_name -> list of TechDef
    for mod_dir in mod_dirs:
        raw_mod_name = mod_dir.name
        print(f"\n{'=' * 60}")
        print(f"PARSING MOD: {raw_mod_name}")
        print(f"{'=' * 60}")
        mod_tech_dir = mod_dir / "common" / "technologies"
        mt = parse_tech_files(mod_tech_dir, raw_mod_name, args.verbose)
        mod_techs_by_mod[raw_mod_name] = mt
        print(f"[INFO] Parsed {len(mt)} techs from {raw_mod_name}")

    # Flatten all mod techs for summary
    all_mod_techs = []
    for mt in mod_techs_by_mod.values():
        all_mod_techs.extend(mt)

    # Determine vanilla tech IDs for deduplication
    vanilla_tech_ids = {t.tech_id for t in vanilla_techs}

    # ── SEPARATE-FILE MODE (--mod-check) ──────────────────────────
    # Vanilla gets its own file.  Each mod gets a separate file with
    # suffixed effect names + a small orchestrator gated by mod-check.
    if args.mod_check and mod_techs_by_mod:
        # Calculate dependency depths for vanilla
        calculate_dependency_depths(vanilla_techs)

        # Summary — vanilla
        print(f"\n{'=' * 60}")
        print(f"SUMMARY — VANILLA")
        print(f"{'=' * 60}")
        print(f"Total techs: {len(vanilla_techs)}")
        branch_counts = {}
        for tech in vanilla_techs:
            branch_counts[tech.branch] = branch_counts.get(tech.branch, 0) + 1
        for branch in sorted(branch_counts.keys()):
            print(f"  {branch:<30} {branch_counts[branch]:>4}")

        if not args.dry_run:
            generate_output_files(vanilla_techs, output_dir, args.mode, "vanilla",
                                  report_dir=script_dir)

        # Resolve mod name (CLI override or sanitised dir name)
        for raw_mod_name, mod_tech_list in mod_techs_by_mod.items():
            if args.mod_name:
                safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', args.mod_name).lower()
            else:
                safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', raw_mod_name).lower()

            # Filter to mod-exclusive techs (not already in vanilla)
            mod_exclusive = [t for t in mod_tech_list if t.tech_id not in vanilla_tech_ids]
            print(f"\n{'=' * 60}")
            print(f"SUMMARY — MOD: {raw_mod_name} (suffix: {safe_name})")
            print(f"{'=' * 60}")
            print(f"Techs from mod: {len(mod_tech_list)}")
            print(f"  Overlap with vanilla (skipped): {len(mod_tech_list) - len(mod_exclusive)}")
            print(f"  Mod-exclusive techs: {len(mod_exclusive)}")

            if mod_exclusive:
                calculate_dependency_depths(mod_exclusive)
                branch_counts = {}
                for tech in mod_exclusive:
                    branch_counts[tech.branch] = branch_counts.get(tech.branch, 0) + 1
                for branch in sorted(branch_counts.keys()):
                    print(f"  {branch:<30} {branch_counts[branch]:>4}")

            if not args.dry_run:
                generate_mod_output_files(
                    mod_exclusive, output_dir, safe_name,
                    mod_check=args.mod_check,
                    report_dir=script_dir
                )

    # ── MERGED MODE (no --mod-check, or no mods) ─────────────────
    else:
        if args.mode == 'overhaul':
            mod_tech_ids = {t.tech_id for t in all_mod_techs}
            final_techs = [t for t in vanilla_techs if t.tech_id not in mod_tech_ids]
            final_techs.extend(all_mod_techs)
            print(f"\n[INFO] Overhaul mode: {len(mod_tech_ids)} vanilla techs replaced, "
                  f"{len(final_techs)} total")
        else:
            mod_tech_ids = {t.tech_id for t in all_mod_techs}
            final_techs = [t for t in vanilla_techs if t.tech_id not in mod_tech_ids]
            final_techs.extend(all_mod_techs)
            if mod_tech_ids:
                overridden = len(vanilla_techs) - len(final_techs) + len(all_mod_techs)
                print(f"\n[INFO] Expansion mode: {len(all_mod_techs)} mod techs added, "
                      f"{overridden} vanilla overrides, {len(final_techs)} total")

        calculate_dependency_depths(final_techs)

        print(f"\n{'=' * 60}")
        print(f"SUMMARY")
        print(f"{'=' * 60}")
        print(f"Total techs: {len(final_techs)}")
        print(f"Mode: {args.mode}")
        branch_counts = {}
        for tech in final_techs:
            branch_counts[tech.branch] = branch_counts.get(tech.branch, 0) + 1
        for branch in sorted(branch_counts.keys()):
            print(f"  {branch:<30} {branch_counts[branch]:>4}")

        if args.dry_run:
            print(f"\n[DRY RUN] No files written.")
            return

        mod_label = "overhaul" if args.mode == 'overhaul' else "expansion"
        generate_output_files(final_techs, output_dir, args.mode, mod_label,
                              report_dir=script_dir)

    if args.dry_run:
        print(f"\n[DRY RUN] No files written.")
        return

    # Generate preset file if applicable
    if args.preset:
        preset_data = PRESETS[args.preset]
        preset_path = output_dir / "arm_tier_preset.txt"
        lines = [
            f"# Arms Race Mechanics — Tier Threshold Preset: {args.preset}",
            f"# {preset_data['description']}",
            "",
        ]
        for tier, threshold in preset_data['tier_thresholds'].items():
            lines.append(f"set_variable = {{ arm_tier_threshold_{tier} = {threshold} }}")

        preset_path.write_text('\n'.join(lines), encoding='utf-8')
        print(f"[OUTPUT] Preset: {preset_path}")

    print(f"\n[DONE] Generated files written to: {output_dir}")
    if output_dir == script_dir.parent / "common" / "scripted_effects":
        print(f"       Files placed directly in the ARM mod — no copy needed.")
    else:
        print(f"       Copy auto_research_techlist.txt to /common/scripted_effects/")


if __name__ == "__main__":
    main()
