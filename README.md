# Tech Baseline Mechanics

**Stop AI nations from showing up to WW2 with WW1 equipment.**

TBM gives every country a believable technology floor based on its actual national power and military specialization. Majors get the tech majors should have. Minors stay relevant without becoming ahistorical superpowers. Your research is never touched — TBM targets AI by default.

**Version:** 2.0.0 | **HOI4:** 1.17.5.2 | **DLC Required:** None  
**Steam Workshop:** https://steamcommunity.com/sharedfiles/filedetails/?id=3683996696

---

## How It Works

Every country is scored across five dimensions (economy, science, mobilization, resources, war posture) and placed into one of **six power tiers**:

| Tier | Name | Base Tech Lag | Grants / Cycle |
|---|---|---|---|
| 5 | Superpower | 0.25 years | 12 |
| 4 | Great Power | 1.5 years | 10 |
| 3 | Regional Power | 2.5 years | 8 |
| 2 | Minor Industrial | 3.5 years | 6 |
| 1 | Minor | 4.5 years | 4 |
| 0 | Micro | 6.0 years | 2 |

Four independent **branch competence scores** — Land, Air, Naval, Industry — determine which techs a country actually receives. A landlocked nation won't get submarine tech. A country with no air industry won't get jets. Each branch gates its own tech categories based on competence thresholds.

Countries at war, in strong alliances, receiving lend-lease, or losing territory get **catch-up bonuses** to prevent permanent tech collapse.

---

## Features

- **Six power tiers** with hysteresis to prevent constant tier bouncing
- **Four branch scores** (Land, Air, Naval, Industry) evaluated independently
- **Smart tech gating** — countries only get tech they can plausibly support
- **Catch-up mechanics** — war, factions, puppets, lend-lease, and desperation all reduce lag
- **Research speed spirits** — 26 national spirits tied to tier and branch competence
- **Historical mode** — authentic strength bonuses for Germany, UK, Japan, USA, USSR, Italy, France
- **13 game rules** — full control over scope, intensity, coverage, and behavior
- **Save-safe** — install mid-campaign without issues
- **Performance-friendly** — staggered bucket evaluation spreads load across months

---

## Game Rules

All configurable from the game rules screen before starting a game:

| Rule | Options |
|---|---|
| **Scope** | AI only, everyone, or disabled |
| **Intensity** | Realistic, Balanced, Arcade, Historical |
| **Tech scope** | Core only, core + air/naval, all except doctrines, everything |
| **Doctrines** | Disabled, AI only, everyone |
| **Advanced tech** | Excluded, superpowers only, included |
| **War/faction catch-up** | Disabled, standard, enhanced |
| **Grant caps** | Strict, standard, unlimited |
| **Anti-death-spiral** | Disabled, standard, enhanced |
| **Puppet sharing** | Disabled, standard, enhanced |
| **Research speed bonuses** | Full, tier only, disabled |
| **Bucket spread** | 1 / 2 / 3 / 6 months |
| **Notifications** | Silent, major only, all |
| **Power visibility** | Hidden, own country, all (debug) |

---

## Compatibility

Works with vanilla HOI4. No DLC required.

Built-in auto-detected compatibility profiles for 14 major mods:

> BlackICE, Road to 56, Kaiserreich, KaiserreduX, The New Order, Millennium Dawn, The Great War, Great War Redux, Cold War Iron Curtain, Endsieg, Extended Tech Tree 1960, Novum Vexillum, Rise of Nations, The Fire Rises

Compatibility bundles are in `compat_generated/`. Rebuild them with:

```bash
python Tools/rebuild_builtin_major_compat.py
```

---

## For Modders

- **Debug tools:** Set Power Visibility to "All" in game rules for full score inspection
- **Scoring API:** See [SCORING_API.md](SCORING_API.md)
- **Compatibility tooling:** `Tools/tbm_compat_tool.py`
- **Custom category mappings:** `Tools/custom_mappings.txt`
