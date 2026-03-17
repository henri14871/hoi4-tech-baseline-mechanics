# Arms Race Mechanics

**Keep AI nations technologically credible without killing player research.**

Arms Race Mechanics fixes one of HOI4's most persistent late-game problems: countries falling absurdly far behind in tech branches they should realistically be able to support. Majors stop showing up with bizarre gaps in armor, air, radar, or naval tech. Regional powers stay dangerous in their strongest areas. Minors stay relevant without becoming ahistorical superpowers.

ARM gives each country a credible technological baseline based on its power, industry, and military profile. Countries stay closer to the curve, but the frontier is still reserved for active research. By default, the system is AI-only, so your own research game stays fully in your hands.

**What that means in practice:** stronger AI competition, fewer immersion-breaking tech gaps, more credible minors, and late-game wars decided by production, planning, and execution rather than one side still fielding outdated equipment.

**Version:** 2.0.0 | **HOI4:** 1.17.4.1+ | **DLC Required:** None

**Steam Workshop:** https://steamcommunity.com/sharedfiles/filedetails/?id=3683996696

---

## What changes in your game

- **AI nations stay near a believable baseline.** Majors no longer drift years behind in branches they obviously have the economy and slots to support.
- **Wars get harder to snowball.** Nations under pressure catch up faster, so one bad year doesn't become permanent tech irrelevance.
- **Minor nations contribute.** Romania gets artillery. Siam gets basic fighters. They're not world leaders, but they stop being free wins.
- **Late-game wars stay competitive.** 1944-45 conflicts are decided more by production, planning, and execution than by wild tech mismatches.
- **Your research choices matter more.** With a stronger baseline across the board, smart specialization and timing create the real edge.

---

## How it works

Every nation is scored on five dimensions: **economy, science, mobilization, resources, and war posture**. That composite score places them into one of six power tiers, from Micro to Superpower. Each tier sets a base technology lag (how far behind the frontier) and a grant cap (how many techs per evaluation cycle). Under the default Balanced rules, ARM also enforces a frontier buffer so auto-grants stay behind manual research.

### Power tiers

| Tier | Name | Base Lag | Grants / Cycle |
|---|---|---|---|
| 5 | Superpower | 0.25 years | 12 |
| 4 | Great Power | 1.5 years | 10 |
| 3 | Regional Power | 2.5 years | 8 |
| 2 | Minor Industrial | 3.5 years | 6 |
| 1 | Minor | 4.5 years | 4 |
| 0 | Micro | 6.0 years | 2 |

Tiers use hysteresis (a buffer zone) to prevent oscillation. A country must exceed the promotion threshold by +5 to move up and drop below the demotion threshold by -5 to move down. A tier-3 country at 88 power stays tier-3 until it drops below 85.

### Branch competence

On top of global power, four **branch competence** scores (Land, Air, Naval, Industry) control which specific tech categories a nation receives. A country with 50 dockyards and no air force gets destroyers and cruisers, not fighters. A landlocked nation with heavy industry gets tanks and artillery, not submarines. Tech grants match what a country can plausibly support.

Each branch competence also applies research speed modifiers:

| Level | Competence | Research Speed |
|---|---|---|
| Cutting Edge | > 84 | +10% |
| Advanced | > 59 | +5% |
| Standard | > 34 | +0% |
| Basic | > 14 | -5% |
| Minimal | < 15 | -10% |

### Evaluation cycle

Countries are evaluated on a **6-month rotation**: all nations are split into 6 buckets, and one bucket is processed each month. Each country gets evaluated and granted tech once every 6 months. This spreads the processing load and keeps performance smooth even with hundreds of nations.

### Catch-up bonuses

Nations at war, in factions with stronger allies, losing territory, or serving as puppet states receive catch-up bonuses that reduce their effective tech lag. The system prevents the snowball effect where one lost campaign leads to permanent technological irrelevance.

The system runs AI-only by default. Players keep full control of their own research unless they opt in via game rules.

---

## Features

- Six power tiers (Micro to Superpower) with hysteresis to prevent oscillation
- Four independent branch competence scores gate access to specific tech categories
- Technologies granted in strict priority order with configurable per-branch caps
- War, faction, desperation, and puppet catch-up bonuses for nations under pressure
- Anti-death-spiral system keeps late-game wars competitive
- Puppet tech sharing scales with overlord strength
- Per-tier and per-branch research speed national spirits (+10% to -10%)
- Historical bias mode boosts historically strong nations in their real-world specialties
- DLC-aware: Man the Guns, No Step Back, and By Blood Alone techs gated behind `has_dlc`
- 13 game rules for full control over scope, intensity, and behavior
- AI-only by default with opt-in for player nations
- Save-safe: handles mid-campaign installation and legacy saves

---

## Game rules

| Rule | Default | Options |
|---|---|---|
| Scope | AI Only | AI Only / Everyone / Disabled |
| Intensity | Balanced | Realistic / Balanced / Arcade / Historical |
| Compatibility Profile | Auto Detect | Auto Detect / Vanilla / 14 bundled mod profiles |
| Tech Scope | All Except Doctrines | Core Only / Core + Air/Naval / All Except Doctrines / Everything |
| Doctrine Handling | Disabled | Disabled / AI Only / Everyone |
| Advanced Tech | Excluded | Excluded / Superpowers Only / Included |
| War/Faction Catch-Up | Standard | Disabled / Standard / Enhanced |
| Grant Cap | Standard | Strict / Standard / Unlimited |
| Notifications | Major Only | Silent / Major Only / All |
| Power Visibility | Own Country | Hidden / Own Country / All (Debug) |
| Puppet Sharing | Standard | Disabled / Standard / Enhanced |
| Anti-Death Spiral | Standard | Disabled / Standard / Enhanced |
| Research Speed Bonuses | Full | Full / Tier Only / Disabled |

---

## Mod compatibility

ARM ships with built-in compatibility profiles that auto-detect your mod setup. No patches, no sub-mods, no load order headaches. Just enable both mods and leave Compatibility Profile on Auto Detect.

**Bundled profiles (14):**

| Mod | Techs | Doctrines |
|---|---|---|
| BlackICE | 2627 | 312 |
| Cold War Iron Curtain | 1417 | 251 |
| Endsieg | 1021 | 192 |
| Extended Tech Tree 1960 | 766 | 59 |
| The Great War | 789 | — |
| Great War Redux | 384 | — |
| Kaiserreich | 500 | 38 |
| Kaiserredux | 572 | 38 |
| Millennium Dawn | 972 | 6 |
| Novum Vexillum | 618 | — |
| Rise of Nations | 2339 | 317 |
| Road to 56 | 948 | 67 |
| The Fire Rises | 657 | 118 |
| The New Order | 897 | — |

Each profile uses mod-specific tech grant lists and tier thresholds tuned for that mod's tech tree. You can force a specific profile manually in the lobby if auto-detect doesn't fit your setup.

---

## Load order

No hard dependencies. When using a bundled profile, load ARM after the target overhaul mod.

---

## For modders and maintainers

**Debug tools** — Set the Power Visibility game rule to "All (Debug)" to inspect power scores, branch competence, effective lag, target years, and force immediate evaluation cycles via decisions.

**Scoring API** — See [SCORING_API.md](SCORING_API.md) for full documentation on integrating ARM's power scoring into your own mod.

**Rebuilding compatibility profiles:**

```bash
python Tools/build_builtin_compat_profiles.py
```

- Custom category tags: `Tools/custom_mappings.txt`
- Generated staging bundles: `compat_generated/`
- Baked-in profile files: `common/scripted_effects/arm_compat_generated_*.txt`
