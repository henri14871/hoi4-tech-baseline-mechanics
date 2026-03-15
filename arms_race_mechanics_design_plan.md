# Arms Race Mechanics | Consolidated Design Plan

## Concept

A dynamic catch-up mechanic that automatically grants researched technologies to nations based on their **overall national power** and their **branch-specific competence**. Stronger nations stay close to the technological frontier. Weaker nations lag behind, receive fewer technology categories, and only modernise in areas they can plausibly support.

The goal is not to make the AI "smart" at research. The goal is to make the world's technological development feel more realistic, more consistent, and less dependent on vanilla AI research choices.

This system is intended to operate as a complete, integrated mechanic from game start to late war, with all major systems included in one design rather than split into staged versions.

---

## Design Principles

1. **AI technology progression should reflect material power, not arbitrary picks.**
2. **Not all power translates equally into all branches.**
3. **Weak nations should get fewer categories, not just delayed versions of everything.**
4. **Technology spread should be gradual, capped, and believable.**
5. **Performance must be treated as a core design constraint.**
6. **The player should retain control by default unless game rules allow otherwise.**
7. **Losing nations should not enter unrecoverable tech death spirals.**
8. **Tier boundaries should be stable, not jittery.**
9. **Auto-research is a floor, not a ceiling. Manual research must remain the primary path to technological advantage.**
10. **Technologies once granted are never revoked, regardless of subsequent tier changes or power loss.**
11. **More powerful nations should research faster, reinforcing the value of manual research at every tier.**

---

## System Overview

Every country periodically recalculates:
- a **Global Power Score**
- four **Branch Competence Scores**
- a **Power Tier** (with hysteresis)
- a set of **Allowed Tech Categories**
- an **Effective Tech Lag** by branch

The system then checks curated lists of technologies and auto-grants eligible techs up to a cap.

The mechanic is driven by:
- overall state capacity,
- industrial and scientific base,
- military mobilisation,
- resource access,
- wartime urgency,
- faction-level technology sharing,
- puppet/overlord relationships,
- desperation pressure from territorial losses.

The system also provides **tier-based research speed bonuses** that make manual research faster for powerful nations, ensuring that auto-research acts as a floor while manual research remains the primary path to technological advantage.

---

# Phase 1 â€” Scoring Model

## 1.1 Global Power Score

The Global Power Score determines:
- overall tier,
- baseline lag behind the current year,
- grant cap,
- upper ceiling of technological access.

It answers:

**"How advanced should this country be overall?"**

### Formula Structure

```text
global_power =
    economy_score
  + science_score
  + mobilization_score
  + resource_score
  + war_posture_score
```

### A. Economy Score

Represents industrial and production capacity.

Suggested weight sources:

* civilian factories
* military factories
* dockyards

Suggested weighting:

* civilian factories Ã— 1.0
* military factories Ã— 1.5
* dockyards Ã— 1.2

Reasoning:

* mils matter more for direct military technology application
* dockyards matter for naval-industrial states
* civs still matter because they reflect broader industrial support

#### Diminishing Returns

Raw factory counts should use **logarithmic scaling** above a threshold to prevent late-game superpowers from generating absurdly inflated scores that break tier spacing.

Suggested model:

* first 80 factories of each type: count at full weight
* factories 81â€“160: count at 50% weight
* factories 161+: count at 25% weight

Example: a country with 200 military factories would score:

```text
(80 Ã— 1.5) + (80 Ã— 0.75) + (40 Ã— 0.375) = 120 + 60 + 15 = 195 economy from mils
```

This keeps the USA clearly dominant without letting a 1945 industrial monster score 500+ on economy alone and distort every other variable into irrelevance.

### B. Science Score

Represents formal research capability.

Suggested weight sources:

* research slots
* research speed modifiers

Suggested weighting:

* research slots Ã— 15
* research speed bonus: (total_research_speed_modifier - 1.0) Ã— 20, capped at +30

Research slots should remain the single strongest clean indicator of national R&D capacity. Research speed modifiers from national spirits, advisors, and focuses provide a modest additional signal but should not dominate.

### C. Mobilization Score

Represents actual military scale and pressure.

Suggested weight sources:

* deployed manpower
* division count

Suggested weighting:

* deployed manpower Ã· 50,000, **capped at 30 points**
* division count Ã— 0.1, **capped at 15 points**

The cap is critical. Without it, the USSR or China could score 60+ from manpower alone, which would overinflate their tier relative to their actual industrial sophistication. Large armies indicate urgency and feedback loops, but they do not substitute for factories and research infrastructure.

### D. Resource Score

Represents industrial input access.

This should use **available or in-use strategic resources**, not stockpiles.

Suggested weighting:

* steel: 1 point per 8
* aluminium: 1 point per 5
* tungsten: 1 point per 4
* chromium: 1 point per 4
* rubber: 1 point per 4
* oil: 1 point per 6

**Total resource score capped at 40 points.** This prevents resource-rich nations like the USA from pulling too far ahead on resources alone while ensuring resource-poor nations still feel the penalty.

### E. War Posture Score

Represents urgency and military pressure.

Suggested sources:

* stability
* war support
* at war
* political power gain rate

Suggested weighting:

* stability Ã— 0.5 (max 50 points at 100% stability)
* war support Ã— 0.3 (max 30 points at 100% war support)
* at war = +20
* political power gain rate Ã— 10, **capped at +20**

This should be meaningful but not large enough to let weak states become pseudo-majors by being unstable or permanently mobilised.

---

## 1.2 Branch Competence Scores

This is the key refinement that makes the system believable.

Global power determines **how advanced a country should be overall**. Branch competence determines **what it can actually keep up with**.

The system uses four branch scores:

* `land_competence`
* `air_competence`
* `naval_competence`
* `industry_electronics_competence`

These scores gate categories separately.

### A. Land Competence

Formula:

```text
land_competence =
    (military_factories Ã— 1.0, first 60 at full, rest at 0.5)
  + (deployed_manpower / 40,000, capped at 25)
  + (steel / 10, capped at 15)
  + (tungsten / 6, capped at 10)
  + (at_war Ã— 10)
```

Max theoretical: ~120

This controls:

* artillery
* anti-air / anti-tank
* motorised / mechanised
* tanks
* land support technologies

### B. Air Competence

Formula:

```text
air_competence =
    (military_factories Ã— 0.8, first 60 at full, rest at 0.4)
  + (aluminium / 5, capped at 15)
  + (rubber / 5, capped at 10)
  + (oil / 8, capped at 10)
  + (research_slots Ã— 8)
```

Max theoretical: ~110

This controls:

* fighters
* heavy fighters
* CAS
* tactical bombers
* strategic bombers
* transport planes
* naval bombers

### C. Naval Competence

Formula:

```text
naval_competence =
    (dockyards Ã— 2.0, first 30 at full, rest at 1.0)
  + (oil / 8, capped at 10)
  + (steel / 10, capped at 10)
  + (chromium / 5, capped at 10)
  + (research_slots Ã— 5)
```

Max theoretical: ~105

This controls:

* submarines
* destroyers
* cruisers
* battleships
* carriers
* naval support systems

### D. Industry / Electronics Competence

Formula:

```text
industry_electronics_competence =
    (civilian_factories Ã— 0.8, first 60 at full, rest at 0.4)
  + (research_slots Ã— 12)
  + (stability Ã— 0.3, max 30)
  + (resource_breadth_bonus)
```

Where `resource_breadth_bonus` = +3 for each strategic resource type the country has at least 8 units of access to, max +18.

Max theoretical: ~120

This controls:

* industry technologies
* construction/production techs
* radar
* electronics
* engineering
* advanced scientific branches

### Branch Competence Thresholds

Branch competence feeds into two systems:

**1. Category gating** â€” each tech category requires a minimum branch score to qualify:

| Branch Score | Access Level |
|---|---|
| 0â€“14 | No branch access (too weak to sustain this domain) |
| 15â€“34 | Basic access (early-war tech only, e.g. 1936â€“1939 equivalents) |
| 35â€“59 | Standard access (mid-war tech, e.g. up to 1941â€“1942) |
| 60â€“84 | Advanced access (full mid-to-late war range) |
| 85+ | Cutting-edge access (latest generation, modern/jet/advanced) |

**2. Lag reduction bonus** â€” a country whose branch score significantly exceeds the average for its global tier can reduce lag in that branch:

```text
branch_lag_bonus = 0.0

IF branch_score > tier_average_for_branch + 20:
    branch_lag_bonus = -0.5

IF branch_score > tier_average_for_branch + 40:
    branch_lag_bonus = -1.0
```

Tier averages should be calibrated during testing. Starting estimates:

| Tier | Expected Average Branch Score |
|---|---|
| Superpower | 90 |
| Great Power | 65 |
| Regional Power | 40 |
| Minor Industrial | 25 |
| Minor | 12 |
| Micro | 5 |

---

# Phase 2 â€” Power Tiers

Global Power Score maps countries into dynamic tiers.

These tiers determine:

* baseline lag behind the frontier
* base grant cap
* broad category ceiling

## Tier Table

| Tier             | Global Power Score | Intended Position                | Base Lag  |
| ---------------- | ------------------ | -------------------------------- | --------- |
| Superpower       | 300+               | Near current frontier            | 0.0 years |
| Great Power      | 150â€“299            | Slightly behind frontier         | 0.5 years |
| Regional Power   | 90â€“149             | Competitive but not cutting-edge | 1.5 years |
| Minor Industrial | 45â€“89              | Gradual modernisation            | 3.0 years |
| Minor            | 20â€“44              | Delayed basics                   | 4.5 years |
| Micro            | 0â€“19               | Minimal industrial modernity     | 6.0 years |

These tiers update dynamically. A country that industrialises aggressively can move upward and start receiving more advanced categories faster.

## Tier Hysteresis

A country sitting right on a tier boundary could flip-flop between tiers each evaluation cycle, causing jittery tech grants and potential grant/revoke confusion.

To prevent this, tiers use **asymmetric thresholds**:

* **Promotion**: requires score to exceed the tier boundary by +5
* **Demotion**: requires score to drop below the tier boundary by -5

Example: a country with a score of 152 would promote to Great Power (needs 150+5=155? No â€” stays Regional). At 156, it promotes. Once at Great Power, it only demotes back at 144 (150-5=145? Stays Great Power). At 144, it demotes.

This creates a 10-point dead zone around each boundary that prevents oscillation.

Implementation: store the country's current tier as a variable. On each evaluation, only change tier if the score has crossed the hysteresis threshold.

---

# Phase 3 â€” Effective Lag by Branch

Base lag is determined by global tier, then modified by branch competence and strategic bonuses.

## General Form

```text
effective_branch_lag =
    base_tier_lag
  - branch_competence_bonus
  - war_bonus
  - faction_bonus
  - desperation_bonus
  - puppet_bonus

(minimum 0.0, never negative)
```

Each branch gets its own effective lag:

* `effective_land_lag`
* `effective_air_lag`
* `effective_naval_lag`
* `effective_industry_lag`

### Competence Bonus

A country with unusually strong branch competence for its overall tier can reduce lag in that branch slightly.

Example:

* UK may have strong naval and air competence even if not matching the absolute top industrial score
* USSR may have stronger land and industry competence than air or naval
* Sweden may overperform in industry/electronics relative to its raw geopolitical weight

This bonus should be modest. It is a refinement, not a replacement for overall tier.

Suggested maximum:

* up to -1.0 years for very strong branch competence

See Phase 1.2 Branch Competence Thresholds for the exact calculation.

### War Bonus

War should only accelerate **combat-relevant categories**, not every branch equally.

Suggested categories affected:

* infantry
* artillery
* tanks
* fighters
* CAS

Suggested values:

* Standard: -0.5 years
* Enhanced: -1.0 years

### Faction Bonus

Faction membership with a Great Power or Superpower should reduce lag modestly.

Suggested categories affected most:

* industry
* electronics/radar
* air
* light naval
* support technologies

Suggested values:

* Standard: -0.5 years
* Enhanced: -1.0 years

This models shared doctrine, imported methods, technical cooperation, and integration into a stronger bloc.

#### Lend-Lease Enhancement

If a country is **actively receiving lend-lease** from a Great Power or Superpower (defined as receiving any equipment deliveries in the last 90 days), the faction bonus increases by an additional -0.25 years. This stacks with the base faction bonus.

This models direct technology transfer â€” a nation receiving modern equipment from a major ally learns from that equipment.

### Desperation Bonus

A country that is **at war and has lost significant core territory** should receive a modest lag reduction on combat-critical categories. This prevents the "death spiral" where losing territory â†’ losing factories â†’ losing tier â†’ falling behind in tech â†’ losing harder.

Suggested trigger:

* country has lost 20%+ of its core state count to enemy occupation

Suggested bonus:

* -0.5 years on infantry, artillery, fighters, and CAS only
* only applies while at war
* does not apply to capitulated nations

This models the historical phenomenon of nations under existential pressure (USSR 1941â€“42, Germany 1944â€“45) frantically accelerating weapons development despite industrial losses.

### Puppet Bonus

Puppet states and subjects should inherit partial technology access from their overlord.

Suggested model:

* if the overlord is Great Power or above, the puppet gains -0.5 years on categories the overlord has researched
* if the overlord is Superpower, the puppet gains -1.0 years
* only applies to categories the puppet would otherwise qualify for (does not unlock new categories)

This models colonial/imperial technology transfer â€” India building equipment to British specs, Manchukuo receiving Japanese technical standards, etc.

---

# Phase 4 â€” Category Access System

The system should not merely decide **when** a country gets tech. It must decide **what kinds** of tech it can plausibly get.

Each technology category has three gates:

1. **Minimum Global Tier**
2. **Minimum Branch Competence Score**
3. **Minimum Branch Access Level**

A country must pass all three.

## Category Table

| Category               | Minimum Global Tier | Required Branch              | Min Branch Score |
| ---------------------- | ------------------- | ---------------------------- | ---------------- |
| Infantry Equipment     | Micro               | none                         | 0                |
| Support Equipment      | Minor               | land or industry/electronics | 15               |
| Artillery              | Minor               | land                         | 15               |
| Anti-Air / Anti-Tank   | Minor               | land                         | 15               |
| Industry               | Minor               | industry/electronics         | 15               |
| Electronics / Radar    | Regional Power      | industry/electronics         | 35               |
| Motorised              | Minor Industrial    | land                         | 25               |
| Mechanised             | Regional Power      | land                         | 45               |
| Light Tanks            | Regional Power      | land                         | 35               |
| Medium Tanks           | Regional Power      | land                         | 45               |
| Heavy / Modern Tanks   | Great Power         | land                         | 70               |
| Single-Engine Fighters | Minor Industrial    | air                          | 25               |
| Heavy Fighters         | Regional Power      | air                          | 45               |
| CAS                    | Minor Industrial    | air                          | 25               |
| Tactical Bombers       | Regional Power      | air                          | 45               |
| Strategic Bombers      | Great Power         | air                          | 70               |
| Naval Bombers          | Regional Power      | air                          | 35               |
| Transport Planes       | Minor Industrial    | air                          | 20               |
| Submarines             | Minor Industrial    | naval                        | 25               |
| Destroyers             | Minor Industrial    | naval                        | 25               |
| Light / Heavy Cruisers | Regional Power      | naval                        | 45               |
| Battleships / Carriers | Great Power         | naval                        | 70               |
| Naval Support Tech     | Minor Industrial    | naval                        | 20               |
| Nuclear / Rockets      | Superpower          | industry/electronics         | 85               |

---

## 4.1 Hard Category Ceilings by Tier

Even if time advances, weaker countries should not gain access to everything.

### Micro

Allowed:

* infantry equipment only
* earliest industry basics (construction I, concentrated/dispersed industry I)

### Minor

Allowed:

* infantry
* support
* artillery
* anti-air / anti-tank
* basic industry (up to construction II, industry II)

### Minor Industrial

Allowed:

* all Minor categories
* motorised
* fighters
* CAS
* transport planes
* submarines
* destroyers
* naval support tech
* electronics basics (radio, basic computing)

### Regional Power

Allowed:

* all Minor Industrial categories
* mechanised
* light/medium tanks
* heavy fighters
* tactical bombers
* naval bombers
* cruisers
* radar
* advanced electronics

### Great Power

Allowed:

* all Regional categories
* heavy / modern tanks
* strategic bombers
* battleships
* carriers
* full advanced branch access

### Superpower

Allowed:

* all Great Power categories
* nuclear / rockets if enabled by rules

This prevents absurd outcomes such as Nepal eventually receiving strategic bombers or modern tank lines solely because the calendar advanced.

---

# Phase 5 â€” Technology Eligibility Logic

A technology is eligible for auto-grant only if all of the following are true:

1. the system is enabled by game rule
2. the country is allowed by system scope rule (AI/everyone)
3. the country is not excluded by player control rule
4. the country is not fully capitulated
5. the category is globally allowed for that tier
6. the country meets the minimum branch competence score for the category
7. the technology is in the curated auto-research lists
8. all hard prerequisites for the tech are met
9. the technology's base year is within the country's effective lag threshold for that branch
10. the country has not exceeded its grant cap for the current evaluation pulse
11. the technology is not an XP-gated variant (unless safe bypass exists)
12. for doctrines: the technology is on the country's assigned doctrine path

This should be strict. The system should never indiscriminately dump techs.

---

# Phase 6 â€” Dynamic Tech Pool System

The system should **not** scan the entire technology tree at runtime every pulse, but it also should **not** rely on manually hand-written curated lists that break whenever a mod changes the tech tree.

The solution is **auto-generated tech lists** produced by a Python tool that reads any mod's technology files, maps them through category tags, and outputs ready-to-use scripted effect files.

## How It Works

Every HOI4 technology â€” vanilla or modded â€” has a `categories = { ... }` block containing tags like `infantry_weapons`, `cat_fighter`, `armor`, etc. These tags are mandatory because the game uses them for research speed bonuses. The generator tool reads these tags and maps each tech to an ARM branch and category automatically.

The tool reads the tech files, extracts every tech's ID, `start_year`, `categories`, and `dependencies`, then outputs HOI4 scripted effect files that the ARM pulse logic calls directly.

## Category Tag â†’ Branch Mapping

The core mapping table handles all standard vanilla tags and common modded conventions:

```text
# Land branch
infantry_weapons, infantry_tech            â†’ land / infantry
artillery, cat_artillery                   â†’ land / artillery
support_tech, engineer_tech, recon_tech    â†’ land / support
motorized_equipment                        â†’ land / motorised
cat_mechanized                             â†’ land / mechanised
cat_light_armor                            â†’ land / light_tanks
cat_medium_armor                           â†’ land / medium_tanks
cat_heavy_armor, cat_super_heavy_armor     â†’ land / heavy_tanks
cat_modern_armor                           â†’ land / modern_tanks

# Air branch
cat_fighter, light_fighter                 â†’ air / fighters
cat_heavy_fighter                          â†’ air / heavy_fighters
cas_bomber, cat_cas                        â†’ air / cas
cat_tactical_bomber                        â†’ air / tactical_bombers
cat_strategic_bomber                       â†’ air / strategic_bombers
naval_bomber                               â†’ air / naval_bombers
tp_tech                                    â†’ air / transport

# Naval branch
dd_tech                                    â†’ naval / destroyers
cl_tech                                    â†’ naval / light_cruisers
ca_tech                                    â†’ naval / heavy_cruisers
bb_tech                                    â†’ naval / battleships
cv_tech                                    â†’ naval / carriers
ss_tech, sub_tech                          â†’ naval / submarines

# Industry / Electronics branch
industry, construction_tech                â†’ industry_electronics / industry
electronics, computing_tech                â†’ industry_electronics / electronics
radar_tech                                 â†’ industry_electronics / radar
nuclear                                    â†’ industry_electronics / nuclear
rocketry                                   â†’ industry_electronics / rockets

# Doctrines
land_doctrine, cat_mobile_warfare, etc.    â†’ doctrine / land_doctrine
naval_doctrine, cat_fleet_in_being, etc.   â†’ doctrine / naval_doctrine
air_doctrine                               â†’ doctrine / air_doctrine
```

Any modded tech that uses standard category tags â€” which they almost all do because the game requires them â€” gets correctly assigned automatically. The tool doesn't need to know what `my_cool_modded_rifle_3` is. It sees `infantry_weapons` in the categories and maps it.

## Fallback Keyword Matching

For modded techs using completely custom category tags, the tool uses keyword matching as a fallback. If a tag contains "armor" or "tank" it maps to land/tanks. If it contains "bomber" it maps to air. This catches most convention-following mods.

For truly unrecognised tags, the tool reports them as unmapped. The user can add one-line entries to `custom_mappings.txt`:

```text
my_mod_special_armor -> land / medium_tanks
kaiserreich_light_tank -> land / light_tanks
```

One line per tag. Run the tool again and it picks them up.

## Tier Assignment Heuristics

Minimum tier is assigned automatically based on the tech's category and dependency depth:

* Category determines the base tier (infantry = Micro, fighters = Minor Industrial, heavy tanks = Great Power, nuclear = Superpower)
* Dependency chain depth adjusts upward â€” techs with 3+ prerequisites are bumped to Regional, 4+ to Great Power
* This gets 90%+ of techs assigned correctly without manual intervention

## Generated Output Format

The tool outputs HOI4 scripted effect files with one effect per branch/category:

```text
arm_grant_land_infantry = {
    # infantry_weapons1 â€” 1936
    if = {
        limit = {
            NOT = { has_technology = infantry_weapons1 }
            check_variable = { arm_grant_counter < arm_quarterly_cap }
            check_variable = { arm_target_year_land >= 1936 }
        }
        add_technology = infantry_weapons1
        add_to_variable = { arm_grant_counter = 1 }
    }
    # infantry_weapons2 â€” 1939
    if = {
        limit = {
            NOT = { has_technology = infantry_weapons2 }
            check_variable = { arm_grant_counter < arm_quarterly_cap }
            check_variable = { arm_target_year_land >= 1939 }
            has_technology = infantry_weapons1
        }
        add_technology = infantry_weapons2
        add_to_variable = { arm_grant_counter = 1 }
    }
}
```

These files drop directly into the mod's `/common/scripted_effects/` folder. The ARM pulse logic calls these effects in priority order. No manual editing needed.

## Generator Tool Usage

```text
# Vanilla only (ships with the mod, pre-generated)
python arm_tech_generator.py --hoi4 "/path/to/hoi4"

# Vanilla + expansion mod (adds new file alongside vanilla lists)
python arm_tech_generator.py --hoi4 "/path/to/hoi4" --mods "/path/to/mymod"

# Total overhaul (replaces vanilla lists entirely)
python arm_tech_generator.py --hoi4 "/path/to/hoi4" --mods "/path/to/kaiserreich" --mode overhaul --preset kaiserreich

# Auto-detect active mods from HOI4 launcher
python arm_tech_generator.py --hoi4 "/path/to/hoi4" --auto-detect
```

The tool also generates a human-readable report listing every tech found, its assigned branch, category, year, and any unmapped techs.

## Advantages Over Hand-Written Lists

1. **Universal compatibility** â€” any mod that uses standard category tags works automatically
2. **No maintenance** â€” when a mod updates and adds techs, re-run the tool
3. **Transparent** â€” the report shows exactly what was mapped and what was missed
4. **Extensible** â€” custom_mappings.txt handles edge cases without touching code
5. **Performance** â€” output is pre-compiled scripted effects, same performance as hand-written lists
6. **Mod author friendly** â€” mod authors can run the tool and ship the output as a built-in compatibility file

## What Ships With The Mod

* Pre-generated vanilla tech lists (user never needs to run the tool for vanilla)
* The generator script (`arm_tech_generator.py`)
* The custom mappings template (`custom_mappings.txt`)
* Tier threshold presets for popular overhauls (Kaiserreich, Road to 56, Millennium Dawn, Great War)

---

# Phase 7 â€” Time and Date Logic

Half-year gaps should not be rounded away into blunt whole years.

At the same time, exact daily simulation is unnecessary.

## Recommended Model: Quarter-Based Time Logic

Use:

* quarterly evaluation windows
* quarter-based lag thresholds
* 0.5-year lag represented as two quarters
* 1.5-year lag represented as six quarters

This gives smooth progression without excessive scripting complexity.

## Interpretation

* `0.0 years`: current-year tech can be reached within the current annual cycle
* `0.5 years`: current-year tech becomes available slightly later
* `1.5 years`: country remains broadly one to two years behind
* `3.0 years`: country sits roughly three years behind the frontier
* `4.5+ years`: country remains confined to old-generation systems

This is much cleaner than pure annual cutoffs.

## Date Comparison Method

HOI4 scripting works with `date > "1940.1.1"` style checks. The recommended approach:

* store `target_year` as a variable per branch per country
* calculate: `target_year = current_year - effective_branch_lag`
* for half-year precision, add `.7.1` (July 1st) for .5 boundaries
* compare each curated tech's base year against the target year

Example: in January 1943, a country with 1.5-year land lag has `target_year = 1941.7.1`. Techs with base year 1941 qualify. Techs with base year 1942 do not yet qualify.

---

# Phase 8 â€” Pulse Logic and Performance Architecture

Performance is one of the main technical risks of the entire design.

A full:

* every country
* every month
* every technology
* with prerequisite checks

would be unnecessarily heavy.

## Recommended Evaluation Architecture

Use a **staggered quarterly pulse**.

### Bucket System

Divide all countries into three evaluation buckets:

* Bucket A
* Bucket B
* Bucket C

Each month, only one bucket is processed.

Example:

* January / April / July / October â†’ Bucket A
* February / May / August / November â†’ Bucket B
* March / June / September / December â†’ Bucket C

Each country is therefore evaluated once per quarter, not once per month.

### Bucket Assignment Method

Countries should be assigned to buckets deterministically at game start using their **country tag index modulo 3**. HOI4 country tags are three-letter codes (ENG, GER, USA, etc.) which have a stable internal index.

Pseudocode:

```text
on_startup:
    FOR each country:
        bucket = country_tag_index MOD 3
        set_variable = { auto_research_bucket = bucket }
```

Alternatively, use alphabetical grouping by first letter of tag:

* Aâ€“I â†’ Bucket A
* Jâ€“R â†’ Bucket B
* Sâ€“Z â†’ Bucket C

The key requirement is that assignment is **deterministic, stable, and evenly distributed**.

### Early Exit Optimisation

Before running the full evaluation, each country should pass a quick pre-check:

```text
IF num_civilian_factories < 1 AND num_military_factories < 1:
    skip (no industry = nothing to auto-research)
```

This immediately skips dozens of micro-nations with zero industry and saves significant script time.

## Advantages

* lower per-tick script load
* more stable game speed
* smoother tech distribution over time
* easier debugging during observe-mode testing

---

# Phase 9 â€” Grant Cap and Priority Logic

Technology should not all arrive at once when a country crosses a year threshold or rises a tier.

## Quarterly Cap Table

| Tier             | Max Techs Granted per Evaluation |
| ---------------- | -------------------------------- |
| Superpower       | 6                                |
| Great Power      | 5                                |
| Regional Power   | 4                                |
| Minor Industrial | 3                                |
| Minor            | 2                                |
| Micro            | 1                                |

This cap should be adjustable by game rule.

## Priority Order

If more eligible techs exist than the cap allows, grant in this order:

1. infantry
2. industry
3. support equipment
4. artillery / AA / AT
5. motorised / mechanised
6. fighters / CAS
7. tanks
8. submarines / destroyers
9. cruisers / capitals
10. electronics / radar
11. advanced strategic technologies

This ensures that countries always modernise in the most foundational areas first.

## Interaction with Active AI Research

If the AI is **currently researching** a technology that the auto-research system wants to grant:

* **Grant the tech immediately** and free the research slot
* The AI will then pick a new research project on its next research tick

This is beneficial â€” it effectively gives the AI a free research slot redirect, which means the AI can focus its manual slots on things the auto-research system doesn't cover (doctrines, ahead-of-time, niche techs).

---

# Phase 10 â€” Player Handling

By default, the player should **not** receive automatic research.

This system exists to correct AI research behavior, not to replace human agency.

## Default

* AI countries: enabled
* player-controlled country: excluded

## Optional Rule

A game rule may allow:

* AI only
* everyone
* disabled entirely

This preserves sandbox flexibility without compromising the normal intended experience.

## Multiplayer Handling

In multiplayer games:

* **All human-controlled nations** are excluded by default, not just "the player"
* The game rule "Enabled (Everyone)" should mean everyone including all human players
* Each human player's country should be checked via `is_ai = no`

This prevents one human player getting free tech while others don't, which would create balance issues in MP.

---

# Phase 11 â€” Research Mechanic Preservation

This is arguably the most important design phase in the entire mod. Auto-research must act as a **passive floor**, not a replacement for manual research. The research mechanic should feel *more* rewarding for powerful nations, not less. A player or AI that actively manages their research slots should always outperform one that leaves them idle.

## 11.1 Why Manual Research Must Still Matter

The auto-research system has several built-in limitations that make manual research valuable:

* **Timing**: auto-research grants tech quarterly, subject to priority order and grant caps. Manual research delivers whenever you finish it. In a war, 3â€“6 months of delay is the difference between winning and losing an air campaign.
* **Ahead-of-time**: auto-research **never** grants tech before its base year. Manual research is the only way to get tech early. This is the single biggest advantage of active research management.
* **Priority control**: auto-research follows a fixed priority list (infantry first, electronics last). Manual research lets you jump the queue on whatever you actually need right now.
* **Excluded categories**: doctrines (by default), nuclear/rocket tech (by default), and XP-gated variants are never auto-granted. These must be manually researched.
* **Grant cap**: even Superpowers only get 6 techs per quarter. If 12 techs are eligible, half wait until next quarter. Manual research bypasses this bottleneck entirely.

However, these limitations alone are not enough. The plan must **actively reinforce** the value of manual research through positive incentives, not just passive gaps. That is what the following systems do.

## 11.2 Tier-Based Research Speed Bonuses

More powerful nations have better universities, larger scientific communities, bigger R&D budgets, and more institutional knowledge. This should translate into faster manual research.

Each power tier grants a **general research speed modifier** applied via a dynamic national spirit that updates when tier changes.

| Tier | Research Speed Modifier |
|---|---|
| Superpower | +15% |
| Great Power | +10% |
| Regional Power | +5% |
| Minor Industrial | +0% (baseline) |
| Minor | -5% |
| Micro | -10% |

This means:

* The USA's research slots chew through tech significantly faster. A tech that takes 120 days for a Minor Industrial takes ~102 days for a Superpower.
* Nepal's research slots are painfully slow. Their auto-research floor does most of the work, but any manual research they attempt takes ages.
* The gap between "waiting for auto-research" and "researching it yourself" is widest for Superpowers and narrowest for Micro states. This is exactly the right incentive structure.

### Implementation

Apply as a national spirit with `research_speed_factor` modifier. The spirit is invisible or visible depending on the Power Score Visibility game rule. It updates on each quarterly evaluation when tier is recalculated.

## 11.3 Ahead-of-Time Penalty Reduction

This is the most impactful research bonus. Vanilla ahead-of-time penalties are brutal â€” researching something a year early can double the research time. For powerful nations, this penalty should be reduced, making aggressive ahead-of-time research viable.

| Tier | Ahead-of-Time Penalty Reduction |
|---|---|
| Superpower | -50% (penalty halved) |
| Great Power | -35% |
| Regional Power | -15% |
| Minor Industrial | 0% |
| Minor | 0% |
| Micro | 0% |

This means:

* The USA can start researching 1945 fighters in mid-1944 and actually finish in a reasonable time. Auto-research would never hand them that tech until 1945 at the earliest. This is the **exclusive domain of manual research** and the single biggest reason to actively use your research slots.
* Germany as a Great Power can push ahead-of-time research with a meaningful but not game-breaking reduction. They can stay competitive with the USA's auto-research floor by being smart about what they research ahead of time.
* Nepal gains nothing. Ahead-of-time research is already impractical for them, and this correctly reflects that a Micro state cannot realistically sprint ahead of the technological frontier.

### Implementation

Apply via the same tier national spirit using the `research_speed_factor` modifier on ahead-of-time techs specifically. HOI4 supports category-targeted research speed modifiers, and ahead-of-time penalty interaction can be modelled through a custom modifier or through adjusting the effective research time in scripted effects.

**Important HOI4 scripting note**: vanilla HOI4 does not expose a clean "ahead-of-time penalty reduction" modifier directly. The practical implementation may need to use one of:

* a flat `research_speed_factor` bonus that disproportionately helps ahead-of-time research (since the penalty is multiplicative, a flat bonus offsets it more when penalties are active)
* a technology-specific approach where techs above the current year get a targeted speed boost applied via scripted effect
* or, if modding tools allow, a direct modifier on the ahead-of-time penalty value

This should be prototyped and tested early in development to confirm the best implementation path.

## 11.4 Branch-Specific Research Speed

A country that has heavily invested in a particular military branch should research tech in that branch faster. This rewards strategic investment and creates meaningful decisions about where to focus research slots.

Branch competence score maps to a branch-specific research speed modifier:

| Branch Score | Research Speed in That Branch |
|---|---|
| 85+ (cutting-edge) | +10% |
| 60â€“84 (advanced) | +5% |
| 35â€“59 (standard) | +0% |
| 15â€“34 (basic) | -5% |
| 0â€“14 (none) | -10% |

These **stack** with the tier-based general research speed bonus.

Example stacking:

* **USA researching a fighter** (Superpower tier, 90+ air competence): +15% (tier) + 10% (branch) = **+25% research speed**, with ahead-of-time penalty halved. Their fighter research is blazing fast and they can push well ahead of the auto-research floor.
* **USSR researching a battleship** (Superpower tier, 30 naval competence): +15% (tier) - 5% (branch) = **+10% research speed**, no ahead-of-time reduction on naval. They can research it, but it's slow and ahead-of-time is painful. Reflects the USSR's weak naval R&D infrastructure.
* **Sweden researching industry tech** (Minor Industrial tier, 55 industry/electronics competence): +0% (tier) + 0% (branch) = **+0% research speed**. Completely vanilla speed. They're on their own.
* **Nepal researching infantry** (Micro tier, 8 land competence): -10% (tier) - 10% (branch) = **-20% research speed**. Agonisingly slow. Auto-research is doing the real work.

### Implementation

Branch-specific research speed is more complex to implement because HOI4's `research_speed_factor` is not natively branch-aware. The recommended approach:

* Use **category-specific research speed modifiers**: HOI4 supports research speed bonuses per technology category (e.g. `land_doctrine_research_speed_factor`, `infantry_weapons_research_speed_factor`, etc.)
* Map each branch competence score to modifiers on the relevant tech categories
* Apply via the same dynamic national spirit, with category-specific modifiers updated each evaluation

This requires mapping every tech category to a branch, which is already done in the curated tech pool system (Phase 6). The same mapping drives both auto-research grants and manual research speed bonuses.

## 11.5 Combined Effect on Gameplay

The combined effect of all three systems creates a clean hierarchy:

### For Superpowers (USA, late-game USSR, late-game Germany)

* Auto-research provides a floor â€” you'll never fall behind on basics
* +15% general research speed makes your slots highly productive
* Halved ahead-of-time penalties let you push 6â€“12 months ahead of the floor
* Strong branch scores give another +5â€“10% in your best domains
* **Net effect**: a well-managed Superpower is always 6â€“12 months ahead of where auto-research alone would place them. Research slots feel powerful and impactful. You'd never leave a slot empty.

### For Great Powers (UK, Japan, Italy, France)

* Auto-research keeps you broadly competitive
* +10% speed and -35% ahead-of-time reduction let you push ahead in your strong branches
* You can match Superpower auto-research levels through smart manual research, especially in your specialised branches
* **Net effect**: research feels important and you can punch above your weight in specific areas. The UK can match US naval tech through aggressive manual research even if their auto-research floor is slightly lower.

### For Regional Powers (Canada, Romania, Spain)

* Auto-research handles most of your catch-up
* +5% speed is modest but helps
* Ahead-of-time reduction is small â€” pushing ahead is hard but not impossible
* **Net effect**: research matters for specific priorities but you're mostly relying on the floor. Your slots are best used on areas auto-research hasn't reached yet rather than trying to race ahead.

### For Minor Industrial and Below

* Auto-research is your primary tech source
* No speed bonuses (or penalties for Minor/Micro)
* Ahead-of-time research is impractical
* **Net effect**: your 1â€“2 research slots are best used on categories auto-research doesn't cover (doctrines, niche picks) or on whatever you need most urgently. The floor carries you.

## 11.6 Technology Permanence Rule

**Technologies once granted are never revoked**, regardless of subsequent tier changes, power loss, territorial collapse, or any other factor.

A country does not forget how to build a medium tank because it lost half its factories. Knowledge is permanent. The penalty for decline is **stagnation** (no new tech grants, slower manual research from tier drop), not **regression** (losing existing tech).

This is a hard design rule, not optional. Revoking tech would:

* break production lines mid-game
* invalidate unit templates
* create nonsensical gameplay (divisions suddenly weaker with no explanation)
* violate basic realism (nations don't un-learn engineering)

The natural consequence of power loss is already modelled: lower tier â†’ wider lag â†’ fewer grants â†’ slower manual research. The country falls behind the frontier gradually without losing what it already has.

## 11.7 Game Rule â€” Research Speed Bonuses

This system should be controllable by game rule.

| Option | Effect |
|---|---|
| Full *(default)* | Tier research speed, ahead-of-time reduction, and branch speed all active |
| Tier Only | Only general tier-based research speed modifier applies. No ahead-of-time reduction or branch bonuses |
| Disabled | No research speed modifiers from the auto-research system. Vanilla research speeds for everyone |

---

# Phase 12 â€” War, Faction, and Special Situations

## 12.1 War Acceleration

Countries actively at war should gain a reduction in lag for combat-relevant categories.

Suggested affected categories:

* infantry
* artillery
* fighters
* CAS
* light/medium tanks

Suggested values:

* Enabled: -0.5 years
* Enhanced: -1.0 year
* Disabled: no effect

This represents emergency wartime adaptation.

### Defensive War Modifier

Countries fighting a **defensive war on their own core territory** (enemy controls at least one of their core states) gain an additional -0.25 years on top of the standard war bonus, for combat categories only.

This models the historical urgency of nations under direct invasion (USSR 1941, France 1940, UK during the Blitz).

## 12.2 Faction Technology Sharing

A country in a faction with a Great Power or Superpower should gain a moderate catch-up bonus.

Suggested affected categories:

* support
* industry
* electronics
* radar
* air
* light naval

Suggested values:

* Enabled: -0.5 years
* Enhanced: -1.0 year
* Disabled: no effect

This represents shared technical standards, imported expertise, and alliance coordination.

#### Lend-Lease Enhancement

If a country is actively receiving lend-lease deliveries from a Great Power or Superpower, the faction bonus increases by an additional -0.25 years. See Phase 3 for details.

## 12.3 Capitulated Nations

A fully capitulated nation should receive no auto-research at all.

A government-in-exile should not continue independently producing new weapons generations as though its industrial state were intact.

## 12.4 Puppet and Subject States

Puppet states, dominions, and integrated puppets should inherit partial technology access from their overlord.

* If the overlord is Great Power or above, the puppet gains -0.5 years on categories the overlord has already researched
* If the overlord is Superpower, the puppet gains -1.0 years
* This only applies to categories the puppet would otherwise qualify for (does not unlock new categories beyond the puppet's tier ceiling)

Autonomy level can optionally scale this:

| Autonomy Level | Puppet Bonus Multiplier |
|---|---|
| Integrated Puppet | 100% |
| Puppet | 100% |
| Dominion | 75% |
| Satellite | 50% |
| Free (autonomous subject) | 25% |

## 12.5 Research Slot and Focus Interaction

Focuses, spirits, and modifiers that grant:

* research slots
* research speed
* industrial capacity

should naturally feed into the scoring system rather than require special handling.

That means the mod respects existing progression paths without needing special exceptions.

## 12.6 Desperation Bonus (Anti-Death-Spiral)

A country that is at war and has lost significant core territory receives a modest lag reduction to prevent unrecoverable tech spirals.

Trigger:

* at war = yes
* 20%+ of core states occupied by enemies
* not capitulated

Bonus:

* -0.5 years on infantry, artillery, fighters, CAS only
* increases to -0.75 if 40%+ occupied
* does not stack with war bonus (takes the higher of the two if both apply to the same category)

This prevents the scenario where Germany in 1944 loses half its factories, drops two tiers, and suddenly falls to 1940-era infantry tech while the player is pushing into the Reich. The AI should still be fielding plausible equipment even while losing.

---

# Phase 13 â€” Advanced Technology Handling

## Nuclear and Rocket Technology

These should not be treated like ordinary technologies.

They should be gated by:

* game rule
* Superpower tier or equivalent advanced threshold
* very high industry/electronics competence (85+)
* relevant prerequisite chain

Suggested options:

* Excluded
* Superpowers Only
* Included Normally

## Doctrines

Doctrines are more sensitive than hardware and may be more controversial in an auto-grant system.

Because the plan is intended as one integrated system, doctrine handling should still be defined.

Recommended doctrine policy:

* doctrine auto-research is controlled by a dedicated rule
* default is conservative (no auto-research)
* doctrine grants use stricter lag than equipment (+1.0 year added to effective lag)
* doctrine grants never bypass category restrictions or cap logic

### Doctrine Path Selection

This is the critical problem with doctrine auto-research. HOI4 land doctrines have **mutually exclusive branches** (e.g. Superior Firepower splits into Integrated Support vs Dispersed Support). The system cannot simply grant "the next doctrine" â€” it must choose a path.

Recommended approach:

* **At game start**, assign each AI country a **doctrine path preference** stored as a variable
* Path preference should be chosen based on historical alignment or national strengths:
  - Countries with high land competence and manpower â†’ Mass Assault path
  - Countries with high industry competence â†’ Superior Firepower (Integrated)
  - Countries with high air competence â†’ Grand Battleplan or Superior Firepower (Dispersed)
  - Historical overrides for majors (Germany â†’ Mobile Warfare, USSR â†’ Deep Battle, UK â†’ Grand Battleplan, etc.)
* The auto-research system only grants doctrines that are on the assigned path
* Alternatively, **use HOI4's existing AI doctrine weights** if accessible via script, since the AI already has path preferences coded

If this is too complex, the simplest safe option is to leave doctrines excluded by default and only offer it as an experimental game rule.

If enabled, doctrines should sit behind:

* minimum Minor Industrial or Regional threshold depending on branch
* slightly stricter cap priority than hardware
* separate doctrine cap of 1 per evaluation (doctrines should arrive slowly)

## XP-Gated Technologies

Any technologies or unlocks that depend on Army XP, Air XP, or Naval XP should not automatically bypass those systems unless explicitly designed for it.

Recommended logic:

* if a tech is blocked by XP or variant-specific mechanics, skip it
* do not globally override XP systems
* mark these techs in the curated lists with a `xp_gated = yes` flag so the pulse logic can skip them cleanly

This prevents hidden breakage and preserves branch identity.

---

# Phase 14 â€” Modern HOI4 Scope Boundaries

Modern HOI4 includes systems such as:

* Military Industrial Organizations
* Special Projects

This mod should explicitly define its scope.

## Scope Decision

The auto-research system governs:

* standard researchable technologies in the main tech trees

It does **not** directly govern:

* MIO progression
* special project progress
* project site mechanics
* non-standard research subsystems

However, the scoring and game rules should be written so compatibility patches can later reference these systems if desired.

This prevents scope explosion while keeping the core mechanic clean.

---

# Phase 15 â€” Game Start Initialisation

The system needs defined behaviour for the first evaluation cycle.

## Day-One Logic

On game start (typically January 1st 1936, or the selected bookmark date):

1. **Calculate initial power scores and tiers for all countries.** This establishes baselines.
2. **Assign bucket membership** for staggered evaluation.
3. **Do NOT grant any technologies on startup.** Countries begin with their vanilla starting tech. The auto-research system only begins granting tech after the first quarterly evaluation.
4. **Store initial tier** for hysteresis tracking.

## Non-1936 Start Dates

If the game starts from a later bookmark (1939, 1941, etc.):

* The system should still calculate scores and tiers normally
* The first evaluation cycle may grant a larger number of techs since countries may already be behind
* The quarterly cap still applies, so any large backlog will trickle in over multiple quarters rather than dumping all at once

This avoids a massive first-tick tech dump while still catching countries up naturally.

---

# Phase 16 â€” Game Rules

All game rules should live in the standard HOI4 game rules framework and be readable by the pulse logic.

The system should use a compact but complete rule set.

## Rule 1 â€” Auto-Research Scope

| Option                        | Effect                                        |
| ----------------------------- | --------------------------------------------- |
| Enabled (AI Only) *(default)* | Applies only to AI-controlled countries       |
| Enabled (Everyone)            | Applies to all countries including the player  |
| Disabled                      | System inactive                               |

## Rule 2 â€” Auto-Research Intensity

| Option               | Effect                                                                       |
| -------------------- | ---------------------------------------------------------------------------- |
| Relaxed              | Increase all lag values by +1.0 year                                         |
| Balanced *(default)* | Use standard lag values                                                      |
| Aggressive           | Reduce all lag values by -0.5 years, minimum 0                               |
| Historical Bias      | Apply scripted country modifiers to selected majors on top of normal scoring |

Historical Bias should not replace the dynamic system. It should only slightly weight known historical strengths (e.g. Germany +10 land competence, UK +10 naval competence, Japan +10 naval competence).

## Rule 3 â€” Tech Scope

| Option                       | Effect                                                              |
| ---------------------------- | ------------------------------------------------------------------- |
| Core Only                    | Infantry, support, artillery, basic industry                        |
| Core + Air/Naval *(default)* | Core plus aircraft and naval equipment                              |
| All Except Doctrines         | Includes nearly all eligible hardware and support tech              |
| Everything                   | Includes doctrines and advanced branches subject to all other gates |

## Rule 4 â€” Doctrine Handling

| Option                       | Effect                                              |
| ---------------------------- | --------------------------------------------------- |
| No Auto-Research *(default)* | Doctrines never auto-grant                          |
| AI Only                      | Only AI countries auto-receive doctrine progression  |
| Everyone                     | Player and AI receive doctrine auto-research         |

## Rule 5 â€” Advanced Technology

| Option               | Effect                                     |
| -------------------- | ------------------------------------------ |
| Excluded *(default)* | Nuclear and rocket tech are excluded       |
| Superpowers Only     | Only top-tier states may auto-receive them |
| Included             | Follows normal category and branch gating  |

## Rule 6 â€” War and Faction Catch-Up

| Option               | Effect                               |
| -------------------- | ------------------------------------ |
| Disabled             | No war/faction lag reduction         |
| Standard *(default)* | Use standard war and faction bonuses |
| Enhanced             | Use stronger war and faction bonuses |

## Rule 7 â€” Grant Cap

| Option               | Effect                                     |
| -------------------- | ------------------------------------------ |
| Strict               | Quarterly caps halved (rounded up)         |
| Standard *(default)* | Use default cap table                      |
| Unlimited            | All eligible techs can grant at evaluation |

## Rule 8 â€” Notifications

| Option                         | Effect                                                          |
| ------------------------------ | --------------------------------------------------------------- |
| Silent                         | No notifications                                                |
| Major Nations Only *(default)* | Notify only for major milestone grants in Great Powers or above |
| All Notifications              | Notify for every grant                                          |

## Rule 9 â€” Power Score Visibility

| Option                       | Effect                                                      |
| ---------------------------- | ----------------------------------------------------------- |
| Hidden                       | No visible score information                                |
| Own Country Only *(default)* | Show the player their own score/tier via national spirit     |
| All Countries                | Show all countries' score/tier for transparency and testing  |

## Rule 10 â€” Puppet Technology Sharing

| Option               | Effect                                               |
| -------------------- | ---------------------------------------------------- |
| Disabled             | Puppets receive no bonus from overlord               |
| Standard *(default)* | Puppets gain lag reduction based on overlord tier     |
| Enhanced             | Puppet bonus values doubled                          |

## Rule 11 â€” Anti-Death-Spiral

| Option               | Effect                                                                |
| -------------------- | --------------------------------------------------------------------- |
| Disabled             | No desperation bonus for losing nations                               |
| Standard *(default)* | Countries losing 20%+ core territory get combat tech lag reduction    |
| Enhanced             | Lower threshold (10%+ territory) and stronger bonus                   |

## Rule 12 â€” Research Speed Bonuses

| Option               | Effect                                                                                          |
| -------------------- | ----------------------------------------------------------------------------------------------- |
| Full *(default)*     | Tier research speed, ahead-of-time reduction, and branch-specific speed all active              |
| Tier Only            | Only general tier-based research speed modifier applies. No ahead-of-time or branch bonuses     |
| Disabled             | No research speed modifiers from the auto-research system. Vanilla research speeds for everyone |

---

# Phase 17 â€” Scripting Structure

## Suggested Folder Layout

```text
/common/game_rules/auto_research_rules.txt
/common/national_spirit/auto_research_spirits.txt
/common/on_actions/auto_research_on_actions.txt
/common/scripted_effects/auto_research_scoring.txt
/common/scripted_effects/auto_research_evaluation.txt
/common/scripted_effects/auto_research_grant.txt
/common/scripted_effects/auto_research_research_speed.txt
/common/scripted_triggers/auto_research_triggers.txt
/common/scripted_localisation/auto_research_loc.txt
/events/auto_research_events.txt
/decisions/auto_research_debug.txt
/localisation/english/auto_research_l_english.yml
```

## Core Components

### Scripted Effects

* `calculate_global_power` â€” runs the full global power formula
* `calculate_branch_competence` â€” runs all four branch formulas
* `assign_power_tier` â€” maps score to tier with hysteresis
* `assign_allowed_categories` â€” sets category flags per tier + branch
* `compute_effective_lag` â€” calculates per-branch lag with all modifiers
* `evaluate_and_grant_technologies` â€” runs the curated list check and grants up to cap
* `update_research_speed_spirit` â€” applies/updates the tier and branch research speed national spirit

### Scripted Triggers

* `auto_research_system_enabled` â€” checks Rule 1
* `country_eligible_for_auto_research` â€” checks AI status, capitulation, factory minimum
* `category_allowed_for_country` â€” checks tier ceiling + branch score
* `tech_eligible_for_grant` â€” checks prerequisites, year, XP gate, doctrine path
* `player_included_check` â€” checks Rule 1 setting for player inclusion

### On Actions

* `on_startup` â€” initial score calculation, bucket assignment, tier storage
* `on_monthly` â€” triggers the appropriate bucket's evaluation

### Decisions

* `debug_view_power_score` â€” visible only if Rule 9 allows, shows score breakdown
* `debug_view_tier` â€” shows current tier and branch competences
* `debug_force_evaluation` â€” manually triggers an evaluation cycle (testing only)

### Events

* `auto_research.1` â€” major milestone notification (new tank generation, jet fighters, etc.)
* `auto_research.100â€“199` â€” debug reporting events
* `auto_research.200â€“299` â€” optional news event hooks for player awareness

---

# Phase 18 â€” Implementation Logic Pseudocode

## Country Evaluation Loop

```text
FOR each country in current evaluation bucket:
    IF system disabled by Rule 1:
        skip

    IF is_ai = no AND player_excluded by Rule 1:
        skip

    IF fully capitulated:
        skip

    IF num_civilian_factories < 1 AND num_military_factories < 1:
        skip (early exit optimisation)

    calculate_global_power
    calculate_land_competence
    calculate_air_competence
    calculate_naval_competence
    calculate_industry_electronics_competence

    assign_tier_from_global_power (with hysteresis check)
    assign_allowed_categories (from tier ceiling + branch scores)
    compute_effective_lag_per_branch (base - competence - war - faction - desperation - puppet)
    compute_quarterly_grant_cap (from tier, adjusted by Rule 7)
    update_research_speed_spirit (tier speed + ahead-of-time reduction + branch speed, if Rule 12 allows)

    SET grant_counter = 0

    FOR each priority category (in priority order 1â€“11):
        IF grant_counter >= quarterly_cap:
            break

        IF category not allowed for this country:
            continue

        get_curated_tech_list_for_category

        FOR each tech in list (ordered by year ascending):
            IF grant_counter >= quarterly_cap:
                break

            IF country already has tech:
                continue

            IF tech prerequisites not met:
                continue

            IF tech is XP-gated:
                continue

            IF tech is doctrine AND not on assigned doctrine path:
                continue

            IF tech base year > (current_date - effective_branch_lag for this category's branch):
                continue

            IF blocked by Rule 3 (tech scope) or Rule 5 (advanced tech):
                continue

            grant tech via add_technology
            increment grant_counter

            IF Rule 8 = All Notifications OR (Rule 8 = Major Only AND tier >= Great Power AND tech is milestone):
                fire notification event
```

---

# Phase 19 â€” Balancing Guidelines

## What to Watch During Testing

1. Are majors staying close enough to the frontier?
2. Are minors modernising too fast or too slowly?
3. Are branch asymmetries believable? (e.g. does Japan have better naval than land tech?)
4. Are faction minors benefiting too much from alliances?
5. Are tech jumps too bursty at year boundaries?
6. Is the quarterly cap too permissive or too restrictive?
7. Is the evaluation pulse affecting game speed?
8. Do tier hysteresis thresholds prevent jitter without being too sticky?
9. Does the desperation bonus prevent death spirals without making losing nations unrealistically strong?
10. Are puppet states getting appropriate tech for their situation?
11. Are doctrine paths (if enabled) producing sensible results?

## Key Test Comparisons

The system should be observed against countries with very different profiles:

* **Superpowers**: USA, Germany, USSR
* **Great Powers**: UK, Japan, Italy, France
* **Regional Powers**: Canada, Australia, Romania, Spain
* **Minor Industrials**: Turkey, Brazil, Sweden, Siam
* **Minors**: Iraq, Portugal, Finland, Hungary
* **Micros**: Nepal, Bhutan, Liberia, Luxembourg

Additionally, test specific scenarios:

* **USSR 1941â€“42**: loses massive territory. Does desperation bonus keep them fielding plausible infantry/fighters?
* **Germany 1944â€“45**: losing factories and territory. Does tech remain at a believable level?
* **India as British puppet**: does puppet bonus give them appropriate but not excessive tech?
* **Italy switching factions**: does faction bonus update correctly?
* **Sweden neutral**: no war bonus, no faction bonus. Does it still progress at a reasonable regional pace?

That spread should expose whether the model properly distinguishes:

* industrial size
* resource access
* branch specialization
* alliance support
* weak-state limits
* wartime pressure
* puppet/subject dynamics

---

# Phase 20 â€” Compatibility

The dynamic tech pool system (Phase 6) and the generator tool make compatibility the mod's strongest feature rather than its weakest.

## Compatibility Tiers

### Tier 1 â€” Works Out of the Box (~70% of popular mods)

Mods that don't touch the tech tree at all:

* focus tree expansions (Road to 56 focuses, etc.)
* cosmetic mods (portraits, map skins, flags)
* AI improvement mods
* music and sound mods
* map mods
* division template mods

The scoring system reads factories, resources, research slots, and manpower â€” all of which exist in every mod. The pre-generated vanilla tech lists handle all vanilla techs. Zero user action needed.

### Tier 2 â€” Run the Generator (~20% of popular mods)

Mods that add techs to the existing vanilla tree or extend it:

* Road to 56 (extended tech trees)
* tech expansion mods
* equipment mods that add new tech lines

The user runs the generator in expansion mode:

```text
python arm_tech_generator.py --hoi4 /path/to/hoi4 --mods /path/to/mod --mode expansion
```

This generates an additional tech list file that sits alongside the vanilla lists. Both load. Both work. Takes 10 seconds.

### Tier 3 â€” Run the Generator with Preset (~10% of popular mods)

Total overhaul mods that replace the tech tree entirely:

* Kaiserreich
* The New Order
* Millennium Dawn
* The Great War
* Old World Blues

The user runs the generator in overhaul mode with a preset:

```text
python arm_tech_generator.py --hoi4 /path/to/hoi4 --mods /path/to/kaiserreich --mode overhaul --preset kaiserreich
```

This replaces the vanilla tech lists with ones built from the overhaul's tech tree, and applies adjusted tier thresholds for the mod's economic scale. Presets ship with the mod for popular overhauls.

If the overhaul uses custom category tags the generator doesn't recognise, the user adds entries to `custom_mappings.txt` and re-runs. The report file tells them exactly which techs were unmapped.

## Dynamic Research Slots Mods

These stack naturally. Extra research slots feed into the science score and branch competence calculations. No compatibility issues.

## Mod Authors

Mod authors who want to ship native ARM compatibility can:

1. Run the generator against their mod
2. Include the generated tech list files in their mod (or as a sub-mod)
3. Optionally include a custom_mappings.txt if they use non-standard category tags
4. Optionally include a tier threshold preset if their mod changes economic scale

This is a one-time task that takes minutes. When they update their mod and add techs, they re-run the generator and update the output files.

## What the User Never Has to Do

* Edit HOI4 script files
* Understand the scoring system
* Know what a "curated tech list" is
* Create a sub-mod

Everything goes into the main ARM mod folder. One folder, one Workshop item, one mod to enable.

---

# Phase 21 â€” Final Design Position

This mod should be understood as:

**A dynamic, branch-aware auto-research framework for HOI4 that synchronises AI technological progression with national capability, industrial reality, military pressure, and alliance support.**

It is not:

* a cheat blanket,
* a full replacement for manual player research,
* a simulation of every R&D subsystem,
* a doctrine/MIO/special-project merger.

It is:

* a structured technological convergence model,
* focused on realism and AI competence,
* tuned for gradual and believable spread,
* designed with performance safety in mind,
* resilient against death spirals and tier jitter,
* aware of puppet, faction, and lend-lease dynamics,
* built to preserve and enhance the value of manual research, not replace it.

---

# Summary of Improvements Over Previous Draft

The following gaps have been addressed:

1. **Branch competence now has concrete formulas** with actual weights, caps, and diminishing returns â€” not just "suggested sources."
2. **Branch competence thresholds are defined** â€” specific score ranges map to access levels, and the category table now includes minimum branch scores.
3. **Diminishing returns on factory counts** prevent late-game score inflation from breaking tier spacing.
4. **All sub-scores have caps** to prevent any single variable from dominating the global power score.
5. **Tier hysteresis** prevents countries from oscillating between tiers at boundaries.
6. **Desperation bonus** prevents the losing-nation death spiral where territory loss â†’ factory loss â†’ tier drop â†’ tech collapse.
7. **Puppet/subject handling** with autonomy-level scaling.
8. **Lend-lease enhancement** to faction bonus.
9. **Defensive war modifier** for nations under direct invasion.
10. **Doctrine path selection logic** for when doctrine auto-research is enabled.
11. **Multiplayer handling** â€” all human players excluded, not just "the player."
12. **Game start initialisation** â€” defined behaviour for day one and non-1936 bookmarks.
13. **Active research interaction** â€” what happens when auto-grant overlaps with AI's current research.
14. **Bucket assignment method** â€” concrete algorithm instead of "deterministic method."
15. **Early exit optimisation** for zero-industry nations.
16. **Curated tech pool now includes example vanilla tech IDs** as a starting reference.
17. **Date comparison method** â€” concrete approach for half-year precision using HOI4's date system.
18. **Two additional game rules** â€” Puppet Technology Sharing and Anti-Death-Spiral.
19. **Specific scenario test cases** added to balancing guidelines (USSR 1941, Germany 1944, etc.).
20. **Compatibility template** recommendation for overhaul mod support.
21. **Research Mechanic Preservation (Phase 11)** â€” dedicated system ensuring manual research remains valuable at every tier, with tier-based research speed bonuses, ahead-of-time penalty reduction, and branch-specific research speed modifiers.
22. **Technology Permanence Rule** â€” explicit hard design rule that granted techs are never revoked under any circumstances.
23. **New game rule (Rule 12)** â€” Research Speed Bonuses with Full/Tier Only/Disabled options.
24. **New design principles** â€” auto-research is a floor not a ceiling, tech is permanent, powerful nations research faster.

