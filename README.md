# Arms Race Mechanics

**A Hearts of Iron IV mod that keeps the world technologically relevant.**

It's 1943. The problem is not that the AI never researches. It does. The problem is that too many countries, including major powers, lag several years behind where they should be in key branches. A large country may be mostly fine in infantry and industry, but still be strangely behind in air, armor, radar, or naval development despite having the slots and economy to keep up.

ARM fixes that by giving each country a credible technological baseline based on its power, industry, and military profile. Major industrial powers stay closer to the frontier across the branches they can realistically support, but the frontier itself is still left for active research. Regional states remain relevant in their strongest areas. Minor countries still lag behind, but they no longer fall so far off the curve that they stop mattering.

**Your research game stays relevant.** ARM runs AI-only by default, but it also works well if you enable it for players. You still decide what to rush, what to delay, and how to specialize. ARM raises the baseline while preserving a frontier gap by default, so research choices matter more because the competition is stronger.

**Version:** 1.0.0 | **HOI4:** 1.17.4.1+ | **DLC Required:** None

---

## What changes in your game

- **AI nations stay closer to the curve.** The issue is no longer big countries mysteriously running years behind in key branches they should be able to maintain.
- **Wars get harder and last longer.** Nations under pressure catch up faster. Losing a war triggers desperate innovation, not a tech death spiral.
- **Minor nations matter.** Romania gets artillery. Siam gets basic fighters. They're not world leaders, but they're not pushovers either.
- **Late game stays competitive.** 1944-45 wars are decided by strategy, not by one side having jets while the other has biplanes.
- **Your research choices matter more, not less.** When the baseline is higher, the edge you get from smart timing and specialization is the real differentiator.

---

## How it works

Every nation is scored on five dimensions: **economy, science, mobilization, resources, and war posture**. That score places them into one of six power tiers, from Micro to Superpower. Each tier sets a technology lag (how many years behind the frontier) and a quarterly grant cap (how many techs per cycle). Under the default balanced rules, ARM also keeps auto-grants at least one year behind the frontier so manual research retains a real role.

| Tier | Name | Base Lag | Grants/Quarter |
|---|---|---|---|
| 5 | Superpower | 0.0 years | 6 |
| 4 | Great Power | 0.5 years | 5 |
| 3 | Regional Power | 1.5 years | 4 |
| 2 | Minor Industrial | 3.0 years | 3 |
| 1 | Minor | 5.0 years | 2 |
| 0 | Micro | 7.0 years | 1 |

On top of global power, four **branch competence** scores (Land, Air, Naval, Industry) control which specific tech categories a nation receives. A country with 50 dockyards and no air force gets destroyers and cruisers, not fighters. A landlocked nation with heavy industry gets tanks and artillery, not submarines. Tech grants follow what a country can plausibly support, not a flat one-size-fits-all tech dump.

Nations at war, in factions with stronger allies, or losing badly get catch-up bonuses that reduce their tech lag. Puppet nations benefit from their overlord's strength. The system prevents the snowball effect where one lost battle leads to permanent technological irrelevance.

Evaluation runs monthly on a rotating third of all countries for performance. The system runs AI-only by default, so players keep full control of their own research unless they opt in.

---

## Features

- Six power tiers (Micro to Superpower) with hysteresis to prevent oscillation
- Four independent branch competence scores gate access to specific tech categories
- Per-tier and per-branch research speed national spirits (+10% to -10%)
- Technologies granted quarterly in strict priority order with configurable caps
- War, faction, and desperation catch-up bonuses for nations under pressure
- Anti-death-spiral system keeps late-game wars competitive
- Puppet tech sharing scales with overlord strength
- Historical bias mode boosts historically advanced nations in their strongest branches
- DLC-aware: Man the Guns, No Step Back, and By Blood Alone techs gated behind `has_dlc`
- 13 game rules for full control over scope, intensity, and behavior
- AI-only by default with opt-in for player nations

---

## Game rules

| Rule | Default | Options |
|---|---|---|
| Scope | AI Only | AI Only / Everyone / Disabled |
| Intensity | Balanced | Relaxed / Balanced / Aggressive / Historical |
| Compatibility Profile | Auto Detect | Auto Detect / Vanilla / bundled major-mod profiles |
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

**Bundled profiles:** Road to 56, Kaiserreich, Kaiserredux, BlackICE, Cold War Iron Curtain, Endsieg, Extended Tech Tree 1960, Novum Vexillum, Rise of Nations, The New Order, Millennium Dawn, The Fire Rises, The Great War, The Great War Redux

Each profile uses mod-specific tech grant lists and tier thresholds. You can force a specific profile manually in the lobby if needed.

---

## Load order

No hard dependencies. When using a bundled profile, load ARM after the target overhaul or expansion mod.

---

## For modders and maintainers

**Debug tools** — Set the Power Visibility game rule to Debug to inspect power scores, branch competence, effective lag, target years, and force immediate evaluation cycles via decisions.

**Rebuilding compatibility profiles:**

```bash
python Tools/rebuild_builtin_major_compat.py
```

- Custom category tags: `Tools/custom_mappings.txt`
- Generated staging bundles: `compat_generated/`
- Baked-in profile files: `common/scripted_effects/arm_compat_generated_*.txt`
