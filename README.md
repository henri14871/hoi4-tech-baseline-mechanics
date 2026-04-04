# Tech Baseline Mechanics

**Keep AI countries technologically credible without taking over player research.**

TBM gives each country a believable tech baseline based on overall power and branch competence. Majors stop missing obvious armor, air, radar, or naval tech. Regional powers stay dangerous in the branches they can actually support. Minors remain relevant without turning into ahistorical superpowers.

**Version:** 2.0.0  
**HOI4:** 1.17.5.2  
**DLC Required:** None  
**Steam Workshop:** https://steamcommunity.com/sharedfiles/filedetails/?id=3683996696

---

## What It Changes

- AI nations stay closer to a believable tech floor.
- Countries under pressure get catch-up help instead of falling permanently irrelevant.
- Late-game wars are decided more by production, planning, and execution than wild tech gaps.
- Research still matters because TBM sets a baseline, not the ceiling.
- Players are untouched by default; player support is optional through game rules.

---

## How It Works

Every country gets a global power score. That score places it into one of six tiers, which determines how far behind the frontier it is allowed to fall and how many techs it can receive per evaluation.

TBM then checks four separate branch scores: Land, Air, Naval, and Industry. Countries only receive tech in branches they can plausibly support. A naval power gets naval tech. A land-heavy industrial state gets tanks, artillery, and support tech. Landlocked countries do not get free submarine progression.

Countries are processed on a 6-month rotation to keep performance predictable. Nations at war, in strong factions, under puppet support, or in bad strategic situations can receive catch-up reductions to effective lag so they do not spiral into permanent tech collapse.

### Power Tiers

| Tier | Name | Base Lag | Grants / Cycle |
|---|---|---|---|
| 5 | Superpower | 0.25 years | 12 |
| 4 | Great Power | 1.5 years | 10 |
| 3 | Regional Power | 2.5 years | 8 |
| 2 | Minor Industrial | 3.5 years | 6 |
| 1 | Minor | 4.5 years | 4 |
| 0 | Micro | 6.0 years | 2 |

---

## Highlights

- Six power tiers with hysteresis to prevent constant promotion and demotion
- Independent Land, Air, Naval, and Industry competence scoring
- Per-branch tech gating and grant caps
- War, faction, puppet, and anti-death-spiral catch-up logic
- Research-speed spirits tied to national competence
- Historical bias mode for stronger historical majors
- 13 game rules for scope, intensity, doctrines, notifications, and debug visibility
- Save-safe behavior for mid-campaign installation

---

## Game Rules

TBM exposes rules for:

- Scope: AI only, everyone, or disabled
- Intensity: realistic, balanced, arcade, or historical
- Tech scope: from core-only to full coverage
- Doctrine handling: disabled, AI only, or everyone
- Catch-up strength, grant caps, puppet sharing, and anti-death-spiral behavior
- Notifications and debug visibility

The default setup is tuned for AI-only use and a conservative frontier buffer.

---

## Compatibility

The core mod targets vanilla HOI4.

This repository also includes generated compatibility bundles under `compat_generated/` for major overhaul and expansion mods. Those bundles are separate generated outputs and should load after TBM and the target mod.

Rebuild generated compatibility bundles with:

```bash
python Tools/rebuild_builtin_major_compat.py
```

---

## For Modders

- Debug tools: use the Power Visibility rule to inspect scores, branch competence, lag, and next grant windows.
- Scoring API: see [SCORING_API.md](SCORING_API.md).
- Compatibility tooling: use `Tools/tbm_compat_tool.py`.
- Custom category mappings: `Tools/custom_mappings.txt`.
