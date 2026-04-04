# TBM Internal Reference

This is your personal reference for how the mod works under the hood. Use it to understand the system, ask for changes, or plan improvements.

---

## The Big Picture

TBM runs a background loop that gives AI countries tech they "should" have based on how powerful and specialized they are. It doesn't replace the AI's research — it fills in gaps so the AI doesn't show up to WW2 with WW1 equipment.

**Default:** AI-only, Balanced mode, 6-month evaluation cycles.

---

## How the Loop Works

```
Game Start
  |
  v
BOOTSTRAP (on_startup)
  - Set global counters (year, month, bucket)
  - Auto-detect which overhaul mod is loaded (if any)
  - Assign every country to one of 6 buckets (0-5)
  - Run first-time scoring for all countries
  |
  v
WEEKLY (on_weekly)
  - For human players only: update the UI dashboard
  - No tech grants, no tier changes — just display refresh
  |
  v
MONTHLY (on_monthly) — this is the main loop
  - Figure out which bucket is up this month (month_counter mod 6)
  - For each country in that bucket:
      1. SCORE: Calculate global power + 4 branch competences
      2. TIER: Assign tier 0-5 (with hysteresis so it doesn't bounce)
      3. LAG: Compute how far behind the frontier each branch should be
      4. GATE: Decide which tech categories this country qualifies for
      5. GRANT: Give techs up to the cap, in priority order
      6. SPIRITS: Apply research speed modifiers
  - Advance month counter
```

**Key detail:** Each country is only evaluated once every 6 months. The monthly pulse processes 1/6 of all countries per month to keep performance smooth.

---

## Scoring Breakdown

### Global Power (determines tier)

Five components added together:

| Component | What it measures | Rough max |
|---|---|---|
| Economy | Factories (diminishing returns after 80) | ~200+ |
| Science | Research slots (6+ = 90 points) | 90 |
| Mobilization | Battalions + deployed manpower | 45 |
| Resources | Steel, aluminium, tungsten, chromium, rubber, oil | 40 |
| War Posture | Stability + war support + at-war bonus + PP | ~120 |

### Branch Competence (determines which techs)

Each branch score gates which tech categories a country can receive:

| Branch | Main inputs | Controls |
|---|---|---|
| Land | Military factories, manpower, steel, tungsten | Infantry, tanks, artillery, motorized, mechanized |
| Air | Military factories, aluminium, rubber, oil, slots | Fighters, bombers, CAS, transport |
| Naval | Dockyards, oil, steel, chromium, slots | Subs, destroyers, cruisers, battleships, carriers |
| Industry | Civilian factories, slots, stability, resource breadth | Electronics, radar, nuclear, rockets |

---

## The Tier System

| Tier | Name | Power needed | Base lag | Techs/cycle |
|---|---|---|---|---|
| 5 | Superpower | > 305 | 0.25 yr | 12 |
| 4 | Great Power | > 155 | 1.5 yr | 10 |
| 3 | Regional Power | > 95 | 2.5 yr | 8 |
| 2 | Minor Industrial | > 50 | 3.5 yr | 6 |
| 1 | Minor | > 25 | 4.5 yr | 4 |
| 0 | Micro | default | 6.0 yr | 2 |

**Hysteresis:** Countries need +5 above the threshold to promote, and must drop -5 below to demote. This prevents bouncing between tiers.

**Base lag** is then modified by the intensity mode:
- **Realistic:** +1.0 year added to base lag
- **Balanced:** No change (default)
- **Arcade:** -0.75 year subtracted from base lag
- **Historical:** Same as Realistic, plus bonuses for historical majors

---

## Tech Category Gating

Not every country gets every type of tech. Requirements:

| Category | Min tier | Min competence |
|---|---|---|
| Infantry | 0 (Micro) | Land >= 10 |
| Support, Artillery, AA, AT | 1 (Minor) | Land >= 15 |
| Industry | 1 (Minor) | Industry >= 15 |
| Motorized | 2 (Minor Ind) | Land >= 25 |
| Fighters, CAS | 2 (Minor Ind) | Air >= 25 |
| Submarines, Destroyers | 2 (Minor Ind) | Naval >= 25 |
| Electronics, Radar | 3 (Regional) | Industry >= 35 |
| Light tanks | 3 (Regional) | Land >= 35 |
| Medium tanks, Mechanized | 3 (Regional) | Land >= 45 |
| Heavy/Tactical bombers | 3 (Regional) | Air >= 45 |
| Cruisers | 3 (Regional) | Naval >= 45 |
| Heavy/Modern tanks | 4 (Great) | Land >= 70 |
| Strategic bombers | 4 (Great) | Air >= 70 |
| Battleships, Carriers | 4 (Great) | Naval >= 70 |
| Nuclear, Rockets | 5 (Super) | Industry >= 85 |

---

## Catch-Up Bonuses (reduce effective lag)

These bonuses subtract from the base lag:

| Bonus | Standard | Enhanced |
|---|---|---|
| At war | -0.5 yr | -1.0 yr |
| Desperation (20%+ surrender) | -0.5 yr | -0.5 yr (at 10%) |
| Desperation (40%+ surrender) | -0.75 yr | -0.75 yr (at 20%) |
| In faction with Great Power+ | -0.5 yr | -1.0 yr |
| Puppet of Great Power | -0.5 yr | -0.5 yr |
| Puppet of Superpower | -1.0 yr | -1.0 yr |
| Defensive war (enemy on core) | -0.25 yr | -0.25 yr |
| Lend-lease from Great Power+ | -0.25 yr | -0.25 yr |

Bonuses stack. A minor at war, in a faction, and losing territory could get several years knocked off.

**Competence adjustments** also shift lag per-branch:
- Competence way above tier average: -0.5 to -1.0 yr
- Competence way below tier average: +0.5 to +1.0 yr

---

## Research Speed Spirits

Two layers of spirits are applied automatically:

**Tier spirits** (global research speed):
| Tier | Bonus |
|---|---|
| 5 Superpower | +10% |
| 4 Great Power | +7% |
| 3 Regional | +5% |
| 2 Minor Industrial | +3% |
| 1 Minor | +1% |
| 0 Micro | -2% |

**Branch spirits** (per-category research speed):
| Level | Competence | Bonus |
|---|---|---|
| Cutting Edge | > 84 | +10% |
| Advanced | > 59 | +5% |
| Standard | > 34 | +0% |
| Basic | > 14 | -5% |
| Minimal | < 15 | -10% |

---

## Historical Bias Mode

When intensity is set to Historical, these majors get competence bonuses:

| Country | Land | Air | Naval | Industry |
|---|---|---|---|---|
| Germany | +10 | +5 | — | — |
| UK | — | +5 | +10 | — |
| Japan | — | +5 | +10 | — |
| USA | +5 | +5 | +5 | +5 |
| Soviet Union | +10 | — | — | +5 |
| Italy | — | +5 | +5 | — |
| France | +5 | — | — | +5 |

---

## Tech Grant Priority Order

Within each branch, techs are granted in this order (first listed = first granted):

**Land:** Infantry > Support > Artillery > AA > AT > Motorized > Mechanized > Light tanks > Medium tanks > Heavy tanks > Generic tanks

**Air:** Fighters > CAS > Heavy fighters > Tactical bombers > Strategic bombers > Naval bombers > Transport

**Naval:** Submarines > Destroyers > Light cruisers > Heavy cruisers > Battleships > Carriers > Naval support

**Industry:** Electronics-industry > Electronics > Radar > Nuclear > Rockets

---

## Compatibility Profile System

TBM auto-detects overhaul mods by checking for mod-specific country tags. Each profile has its own:
- Tier thresholds (some mods need different power breakpoints)
- Tech grant lists (mapped to that mod's tech tree)
- Doctrine handling (some mods have safe doctrine paths, others don't)

14 profiles are bundled. The Python build tool (`Tools/build_builtin_compat_profiles.py`) compiles staging bundles from `compat_generated/` into the main mod files.

---

## File Map

| File | What it does |
|---|---|
| `common/on_actions/tbm_on_actions.txt` | Main loop: startup, daily, weekly, monthly hooks |
| `common/scripted_effects/tbm_scoring.txt` | Power and competence calculations |
| `common/scripted_effects/tbm_evaluation.txt` | Tier assignment, lag, category gating |
| `common/scripted_effects/tbm_grant.txt` | Orchestrates evaluation + tech granting |
| `common/scripted_effects/tbm_research_speed.txt` | Spirit assignment |
| `common/scripted_effects/tbm_runtime_bootstrap.txt` | Save-safe initialization |
| `common/scripted_effects/tbm_historical_bias.txt` | Historical mode bonuses |
| `common/scripted_effects/tbm_time.txt` | Year resolution from game dates |
| `common/scripted_effects/tbm_doctrine_paths.txt` | Doctrine handling stubs |
| `common/scripted_effects/auto_research_techlist.txt` | Vanilla tech grant lists |
| `common/scripted_effects/tbm_compat_generated_*.txt` | Profile-specific dispatch + grants |
| `common/scripted_triggers/tbm_triggers.txt` | All eligibility and helper triggers |
| `common/game_rules/tbm_game_rules.txt` | 13 game rules |
| `events/tbm_events.txt` | Notifications and debug events |
| `localisation/english/tbm_l_english.yml` | All user-facing text |
| `Tools/build_builtin_compat_profiles.py` | Compiles compat profiles into mod |

---

## How to Ask for Changes

Here are the kinds of things you can ask to change and where they live:

| "I want to..." | What to change |
|---|---|
| Adjust tier thresholds | `tbm_evaluation.txt` — promote/demote values in `tbm_assign_power_tier` |
| Change base lag for a tier | `tbm_evaluation.txt` — `tbm_base_lag` values |
| Change grant caps | `tbm_evaluation.txt` — `tbm_quarterly_cap` values |
| Add/remove catch-up bonuses | `tbm_evaluation.txt` — `tbm_prepare_country_context_cache` and `tbm_compute_effective_lag` |
| Change which techs need which competence | `tbm_evaluation.txt` — `tbm_apply_structural_capability_rules` |
| Adjust scoring weights | `tbm_scoring.txt` — component formulas for power/competence |
| Change tech grant order | `auto_research_techlist.txt` — order of `set_technology` calls |
| Add historical bias for a country | `tbm_historical_bias.txt` — add a new country block |
| Change research speed bonuses | `tbm_research_speed.txt` — spirit thresholds and values |
| Change evaluation frequency | `tbm_on_actions.txt` — bucket count and month_counter logic |
| Add a new game rule option | `tbm_game_rules.txt` + `tbm_l_english.yml` + wherever the rule is checked |
| Add a new compat profile | Run the Python tools, add staging bundle to `compat_generated/` |

---

## Pros and Cons

### Pros
- Fixes the single most common complaint about HOI4 AI: nonsensical tech gaps
- AI-only by default preserves player agency completely
- Branch competence prevents nonsensical grants (landlocked nations don't get carriers)
- Hysteresis prevents tier oscillation jank
- 13 game rules give full control without touching code
- Works with 14 major overhaul mods out of the box
- 6-month staggered evaluation keeps performance impact minimal
- Catch-up bonuses prevent death spirals and make wars feel more realistic
- Save-safe — can be added mid-campaign without breaking saves
- Research speed spirits give an extra layer of flavor

### Cons
- Tech grants happen in bulk every 6 months, not gradually — can feel like a sudden jump
- Scoring uses threshold chains instead of real math (Clausewitz limitation) — can feel "steppy"
- No per-country customization — all countries at the same tier get the same treatment
- Competence scoring doesn't account for terrain, strategic situation, or doctrine choice
- The `tbm_quarterly_cap` variable name is misleading (it's actually per 6-month cycle now)
- No awareness of what the AI is actually building — a country might get tank tech but never build tanks
- Nuclear/rockets are very restricted by default (Superpower + industry 85+) — maybe too restrictive
- Historical bias mode only covers 7 majors, ignores secondary powers like Canada, Australia, etc.
- No feedback loop: if granting tech doesn't help the AI perform better, the system doesn't adapt
- Debug UI is functional but not pretty — requires decision clicks to see reports

---

## Potential Improvements

### High Impact
- **Gradual monthly grants** — Instead of bulk-granting every 6 months, spread grants across months for smoother progression
- **Production awareness** — Check if a country actually has the templates/production lines to use the tech being granted
- **Dynamic competence from army composition** — If a country has 50 divisions of infantry and 0 tanks, boost infantry competence and reduce tank competence
- **Per-country overrides** — Allow specific countries to have custom tier/lag/cap values via scripted variables or country flags

### Medium Impact
- **Expanded historical bias** — Cover more countries (Canada, Australia, Poland, China, etc.) and make it data-driven instead of hardcoded
- **Smarter doctrine handling** — Track which doctrine path the AI is actually pursuing and only grant along that path
- **War theater awareness** — Countries fighting in naval theaters get naval bonuses, land theaters get land bonuses
- **Frontier tracking per-branch** — Instead of using a single global "current year," track the actual tech frontier per category

### Quality of Life
- **Better debug UI** — Show all info in the decision category tooltip instead of requiring event popups
- **Notification customization** — Let players pick which milestone events they care about
- **Rename `tbm_quarterly_cap`** — Rename to `tbm_cycle_cap` or `tbm_grant_cap` to match the actual 6-month cycle
- **Profile auto-generation** — Detect unknown mods and auto-generate basic tech lists instead of requiring manual profile creation
- **Localization for more languages** — Currently English-only
