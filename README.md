# Quorum

**Cities decide slowly, across many meetings, under changing labels. Residents lose because nobody can hold the thread. Quorum holds the thread.**

Quorum maintains a persistent model of the civic issues that touch a specific address. It ingests Baltimore City Council's published legislative record, resolves each item to a parcel, decides whether the item is a *continuation of an issue it has already seen*, explains what changed since the last appearance, and drafts a public comment carrying the correct file number and hearing date.

It never submits anything on a person's behalf.

Built for the **Agents for Humans Hackathon**, Good Neighbor track, with the [Strands Agents SDK](https://strandsagents.com).

**Live demo: https://rickygole.github.io/Quorum/**

The published site runs entirely on a cached, timestamped corpus. It never touches the
live internet, and the fetch timestamp is shown on screen.

---

## The three gates

The build spec required three questions answered with real data before any agent code was written. Here are the answers, with the numbers.

### Gate A: does one source carry every item type?

**Yes.** Baltimore runs Legistar, and its Web API is live, public and unauthenticated at
`https://webapi.legistar.com/v1/baltimore`. It carries matters, action histories, sponsors,
attachments and event agendas.

Quorum's scope is deliberately drawn around what this **one** source holds: City Council
ordinances and resolutions. Zoning appeals (BMZA), liquor licenses (BLLC) and tax sale
(Bureau of Revenue Collections) are three other agencies with three other publishing habits,
and Quorum does not claim them. One source, one city, deep.

### Gate B: does the hero example exist?

**Yes, and it is live right now.** Found by hand in the corpus before the Continuity Agent
was written.

**205-209 East Cold Spring Lane, Kernewood**, owned by Loyola University Maryland.

| | File | Introduced | Sponsor | Scope | Outcome |
|---|---|---|---|---|---|
| 1 | `23-0411` | 2023-07-17 | Mark Conway | Block 5053I, Lots 001, **002, 003** | **Failed, End of Term** |
| 2 | `26-0148` | 2026-02-09 | Mark Conway | Block 5053I, Lots 001, **002** | **In Committee** |

Both bills rezone the same land from `R-1-C` to `EC-2`. The first died quietly when the
council term ended. Two and a half years later the same sponsor reintroduced it under an
unrelated file number, one lot smaller, and a **public hearing is scheduled for 2026-09-24**.

This case is the product thesis in one row, and it is hard on purpose:

- The file numbers share nothing (`23-0411` vs `26-0148`).
- The titles differ in formatting (`East Cold Spring Lane` vs `E Cold Spring Lane`,
  `R-1-C` vs `R 1 C`), so naive string matching fails.
- What carries the match is the **parcel** (block 5053I), the **sponsor**, and the
  **zoning transition**, not title similarity. That is exactly the drivers and non-drivers
  distinction the Continuity Agent is built to make explicit.

Independent corroboration from the city's own parcel table: block 5053I holds exactly two
lots today (the 2023 bill named three), and its zoning is still `R-1-C`, so the 2023
rezoning demonstrably never happened.

A second verified case, **4911-4925 West Forest Park Avenue**: `22-0295` (Withdrawn) then
`23-0417` (Failed, End of Term), identical titles, two sponsors narrowing to one.

### Gate C: what does the corpus actually support?

Counted, not estimated:

| | |
|---|---|
| Matters, 2021-01-01 to 2026-09 | **1,679** |
| Matters introduced since 2025-01-01 | **505** |
| Of those: Ordinances / Executive Nominations / Resolutions | 203 / 174 / 63 |
| Address-bearing titles, Jan 2025 to Jul 2026 (19 months) | **51** |
| Addresses appearing under 2+ distinct file numbers, 2021–2026 | **13** |
| Parcels in the gazetteer | **237,092** |

Those 13 multi-file addresses are the population the Continuity Agent is evaluated
against. It is a small number and Quorum says so out loud rather than implying a
larger one. See `eval/RESULTS.md` for what the agent actually scored on it.

---

## Data sources

Both are public, open, and cached to disk with a `fetched_at` timestamp that is
displayed in the product. **No demo touches the live internet.**

- **Legislative record**: Legistar Web API, City of Baltimore.
- **Parcel gazetteer**: the City of Baltimore's open property layer
  (`egisdata.baltimorecity.gov`, dmxOwnership/Properties): `BLOCKLOT`, `BLOCK`, `LOT`,
  `FULLADDR`, `NEIGHBOR`, `ZONECODE`, owner. 237,092 parcels.

---

## Limitations

Written before a judge finds them.

- **One city.** Baltimore only. Nothing here claims to generalize to another
  jurisdiction without new ingestion adapters and a new gazetteer.
- **One source.** City Council legislation via Legistar. Zoning appeals, liquor
  licences and tax sale run through three other Baltimore agencies and are out of scope.
- **A small evaluation population.** 28 hand-labeled pairs drawn from the 270
  parcel-resolvable records in a 1,679 record corpus. That is what the corpus supports
  and the number is stated rather than implied.
- **Parcels are resolved from titles.** 270 of 1,679 records name a parcel Quorum can
  resolve. The rest are budget, procurement, personnel and citywide matters that name no
  property, and Quorum drops them rather than guessing.
- **Quorum never submits.** It drafts a comment and stops. The human sends it or does not.
  This is a design decision, not a missing feature.

## Setup

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e .

python -m ingest.cache 2021-01-01
python -m ingest.gazetteer
python site_export.py
```

The cached corpus and gazetteer are committed, so the first two commands are only needed
to refresh them. `site_export.py` regenerates `docs/data/site.json`, which is what the
published site reads.

The site is plain static files in `docs/`, published by GitHub Pages from the `main`
branch. There is no build step and no framework.

## License

MIT. See [LICENSE](LICENSE).
