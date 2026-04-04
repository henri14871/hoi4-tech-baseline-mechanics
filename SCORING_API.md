# Tech Baseline Scoring & Tier System

A drop-in power scoring and tier classification system for Hearts of Iron IV mods. Evaluates every country's global power, branch-specific military competence, and assigns a tier that other systems can key off.

Use this if your mod needs to answer "how powerful is this country?" at runtime.

---

## Quick start

Copy these files into your mod:

```
common/scripted_effects/tbm_scoring.txt       # power & competence calculation
common/scripted_effects/tbm_evaluation.txt    # tier assignment, lag, category gating
common/scripted_triggers/tbm_triggers.txt     # helper triggers
```

Call from any country scope:

```
tbm_calculate_global_power = yes        # sets tbm_global_power
tbm_calculate_land_competence = yes     # sets tbm_land_competence
tbm_calculate_air_competence = yes      # sets tbm_air_competence
tbm_calculate_naval_competence = yes    # sets tbm_naval_competence
tbm_calculate_industry_competence = yes # sets tbm_industry_competence
tbm_assign_power_tier = yes             # sets tbm_tier_index (0-5)
```

All variables are set on the country scope and persist until the next evaluation.

---

## Variables reference

### Global power

After calling `tbm_calculate_global_power`:

| Variable | Type | Description |
|---|---|---|
| `tbm_global_power` | float | Sum of all five component scores |
| `tbm_economy_score` | float | Factories with diminishing returns |
| `tbm_science_score` | float | Research slots |
| `tbm_mobilization_score` | float | Battalions + deployed manpower |
| `tbm_resource_score` | float | Weighted resource access (capped at 40) |
| `tbm_war_posture_score` | float | Stability + war support + at-war bonus + political power |

### Branch competence

| Variable | Type | Description |
|---|---|---|
| `tbm_land_competence` | float | Military factories + manpower + steel + tungsten + at-war bonus |
| `tbm_air_competence` | float | Military factories + aluminium + rubber + oil + research slots |
| `tbm_naval_competence` | float | Dockyards + oil + steel + chromium + research slots |
| `tbm_industry_competence` | float | Civilian factories + research slots + stability + resource breadth |

### Tier assignment

After calling `tbm_assign_power_tier`:

| Variable | Type | Description |
|---|---|---|
| `tbm_tier_index` | int | 0-5, current power tier |
| `tbm_base_lag` | float | Base technology lag in years |
| `tbm_quarterly_cap` | int | Tech grants allowed per 6-month evaluation cycle |
| `tbm_tier_avg` | float | Expected average competence for this tier (used for bonus thresholds) |

---

## Power tiers

| Index | Name | Promote at | Demote at | Base lag | Grants / cycle |
|---|---|---|---|---|---|
| 5 | Superpower | > 305 | < 295 | 0.25 | 12 |
| 4 | Great Power | > 155 | < 145 | 1.5 | 10 |
| 3 | Regional Power | > 95 | < 85 | 2.5 | 8 |
| 2 | Minor Industrial | > 50 | < 40 | 3.5 | 6 |
| 1 | Minor | > 25 | < 15 | 4.5 | 4 |
| 0 | Micro | -- | -- | 6.0 | 2 |

Hysteresis prevents oscillation. A country at tier 3 with 88 power stays at tier 3 until it drops below 85. Promotion requires exceeding the next tier's threshold by +5; demotion requires falling below the current tier's threshold by -5.

---

## Scoring formulas

### Economy score

Each factory type uses diminishing returns: first 80 at full weight, 81-160 at half, 161+ at quarter.

| Factory type | Weight |
|---|---|
| Civilian | 1.0 |
| Military | 1.5 |
| Dockyards | 1.2 |

Example: 100 military factories = (80 + 20 * 0.5) * 1.5 = 135

### Science score

| Research slots | Score |
|---|---|
| 6+ | 90 |
| 5 | 75 |
| 4 | 60 |
| 3 | 45 |
| 2 | 30 |
| 1 | 15 |

### Mobilisation score

- Battalions * 0.1, capped at 15
- Deployed manpower thresholds: 1.5M = 30, 1M = 20, 500K = 10, 250K = 5, 100K = 2

### Resource score (capped at 40 total)

| Resource | Points per unit | Example: 80 units |
|---|---|---|
| Steel | 1 per 8 | 10 |
| Aluminium | 1 per 5 | 16 (capped by thresholds) |
| Tungsten | 1 per 4 | 20 |
| Chromium | 1 per 4 | 20 |
| Rubber | 1 per 4 | 20 |
| Oil | 1 per 6 | 13 |

Resources use threshold chains (not continuous math) for Clausewitz compatibility.

### War posture score

- Stability * 0.5 (max 50, threshold chain at 0.1 intervals)
- War support * 0.3 (max 30, threshold chain at 0.1 intervals)
- At war: +20
- Political power: 400+ = 20, 300+ = 16, 200+ = 12, 100+ = 8, 50+ = 4

---

## Branch competence formulas

### Land competence

| Component | Formula | Cap |
|---|---|---|
| Military factories | First 60 full, rest * 0.5 | -- |
| Deployed manpower | Threshold chain (1M = 25, 800K = 20, ...) | 25 |
| Steel | /10 threshold chain | 15 |
| Tungsten | /6 threshold chain | 10 |
| At war | +10 | 10 |

### Air competence

| Component | Formula | Cap |
|---|---|---|
| Military factories | (First 60 full, rest * 0.4) * 0.8 | -- |
| Aluminium | /5 threshold chain | 15 |
| Rubber | /5 threshold chain | 10 |
| Oil | /8 threshold chain | 10 |
| Research slots | * 8 threshold chain | 48 |

### Naval competence

| Component | Formula | Cap |
|---|---|---|
| Dockyards | (First 30 full, rest * 1.0) * 2.0 | -- |
| Oil | /8 threshold chain | 10 |
| Steel | /10 threshold chain | 10 |
| Chromium | /5 threshold chain | 10 |
| Research slots | * 5 threshold chain | 30 |

### Industry competence

| Component | Formula | Cap |
|---|---|---|
| Civilian factories | (First 60 full, rest * 0.4) * 0.8 | -- |
| Research slots | * 12 threshold chain | 72 |
| Stability | * 0.3 threshold chain | 30 |
| Resource breadth | +3 per resource with 8+ access | 18 |

---

## Triggers reference

All triggers run in country scope.

| Trigger | Returns true when |
|---|---|
| `tbm_system_enabled` | TBM is not disabled by game rule |
| `tbm_country_eligible` | Country should be evaluated (not capitulated, has factories, AI or rule allows) |
| `tbm_is_in_faction_with_major` | In faction with a Great Power+ leader |
| `tbm_is_puppet_eligible` | Is subject and puppet-sharing rule not disabled |
| `tbm_is_desperation_eligible` | At war, losing territory, rule not disabled |
| `tbm_doctrine_allowed` | Doctrine auto-research permitted for this country |
| `tbm_is_defensive_war` | Enemy controls at least one core state |

---

## Using tier in your own mod

The simplest integration -- check `tbm_tier_index` in your own triggers or effects:

```
# Give a bonus to Great Powers and above
if = {
    limit = { check_variable = { tbm_tier_index > 3 } }
    add_political_power = 50
}
```

```
# Scale an effect by tier
if = {
    limit = { check_variable = { tbm_tier_index = 5 } }
    add_stability = 0.05
}
else_if = {
    limit = { check_variable = { tbm_tier_index = 4 } }
    add_stability = 0.03
}
```

```
# Gate a decision behind branch competence
my_build_carriers_decision = {
    available = {
        check_variable = { tbm_naval_competence > 60 }
    }
}
```

If TBM isn't loaded, `tbm_tier_index` will be 0 (unset) and competence variables will be 0. Design your fallbacks accordingly.

---

## Dependencies

None. The scoring system uses only vanilla triggers and variables -- no DLC required, no other mods required. Remove the game rule checks from `tbm_evaluation.txt` if you don't want the configurable rules.

---

## License

Part of [Tech Baseline Mechanics](https://github.com/henri14871/hoi4-tech-baseline-mechanics). Free to use and adapt in your own mods.
