# Storyboard & demo-video script

## Storyboard

**Big question:** *France is racing towards 400,000 public charge points by 2030 — is everyone getting
plugged in, or are some territories left out?*
**Audience:** department / region / energy-syndicate planners who fund chargers; EV drivers.
**Arc:** Hook → Context → 4 analyses → drill-down → what-if → trust → implications.

| # | Beat | User question | Visual (interaction) | Takeaway the viewer should leave with |
|---|---|---|---|---|
| 0 | Hook | Why care? | Headline with the live best/worst per-capita gap | Public charging is the precondition for EVs for people without a home charger, and access differs by an order of magnitude. |
| 1 | Context | How big is the network? | 5 KPIs (points, stations, MW, per 100k, fast share) — react to filters | Numbers are large and growing; per-capita is the fair lens. |
| 2 | Growth | How fast? | Cumulative stacked area by power class, 100k milestone annotated; yearly bars | Explosive growth since 2021; new points are increasingly fast. |
| 3 | Geography | Where? | Choropleth (click → zoom) + top/bottom ranking, indicator chosen in sidebar | Big gaps between departments; overseas departments far behind. |
| 4 | Equity | Cities vs countryside? | Density scatter (log) + Lorenz/Gini | Density explains only part of the gap — local choices matter. |
| 5 | Fast charging | Fast for long trips? | 100 % stacked bars by region + small multiples over time vs France | The new divide is power, not count. |
| 6 | Operators | Who builds it? | Top-10 operator bars + HHI; location types table | A fragmented market — coordination falls on public planners. |
| 7 | Drill-down | My department? | Station map coloured by max power, KPIs vs national | Make it personal and actionable. |
| 8 | What-if | 2030 reachable? | Projection: recent pace, your scenario (sliders), pace needed | The pace must multiply; with which assumptions. |
| 9 | Trust | Can we believe this? | Checks table, missingness bar chart, provenance | Data is useful but imperfect; limits stated. |
| 10 | So what | What should we do? | Computed takeaways + recommendations + next steps | Fund by per-capita/kW gaps, prioritise the bottom decile, enforce data publication. |

## Demo video script (≈ 3 min 30)

Record at 1440×900, browser zoom 90 %, sidebar open. Fill in the numbers your own run shows.

| Time | Screen | Voice-over (suggested) |
|---|---|---|
| 0:00–0:20 | Title + hook paragraph | "France now lists ___ public charging points and aims for 400,000 by 2030. But someone in ___ has ___ times more chargers per inhabitant than someone in ___. For people who can't charge at home, that gap decides whether an electric car is an option." |
| 0:20–0:35 | Audience / questions / caveats | "This dashboard is for the planners who decide where public money for chargers goes. It answers six questions, using the national open registry on data.gouv.fr." |
| 0:35–1:00 | KPIs + growth chart (hover a month, point at the 100k line) | "The network grew ___× in three years. The dashed line is the 100,000 target — officially reached in May 2023. And ___% of the points added this year are fast chargers." |
| 1:00–1:35 | Map + ranking; change the sidebar indicator to *fast points per 100k*; click a department | "Per inhabitant, the map is far from uniform… Switching to fast charging changes the leaders. Clicking a department sends us to its detail view." |
| 1:35–2:00 | Scatter + Lorenz | "Is it just cities vs countryside? The correlation with density is only ___, and the Gini is ___: geography explains part of it, local choices the rest." |
| 2:00–2:25 | Small multiples; filter **Region = Île-de-France** in sidebar; KPIs update | "Each panel is a region against the national curve in grey. Let me filter on one region — every chart and every headline sentence recomputes." |
| 2:25–2:50 | Zoom on the department map; What-if sliders (move pace, toggle Avere start) | "At the recent pace the 2030 target arrives in ___. Here I can test a scenario — the assumptions are listed right below." |
| 2:50–3:15 | Data quality section | "Transparency: ___ duplicates removed, coordinates repaired, and ___% of points have no commissioning date — the biggest limitation." |
| 3:15–3:35 | Takeaways | "Three takeaways: growth must speed up ___×, access is unequal, and power is the new divide. Next step: join EV registrations to measure vehicles per charger. Thanks!" |

Tips: reset filters before recording; rehearse the clicks once; keep the cursor still while talking.
