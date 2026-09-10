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

Counted, not estimated. Every figure below comes from the same cached corpus and the
same parcel parser, so they can be added up against each other.

| | |
|---|---|
| Matters in the corpus, introduced 2021-01-11 to 2026-07-13 | **1,679** |
| Fetched at | `2026-09-10T02:14:14Z` |
| Matters that name a parcel Quorum can parse | **270** |
| Of those, resolving to a parcel in the city gazetteer | **252** |
| Parcels appearing under two or more file numbers | **9** |
| Matters introduced 2025-01-01 onward | **505** |
| Of those, naming a parcel | **59** |
| Parcels in the gazetteer | **237,092** |

**How the evaluation set relates to those numbers.** The labeled set is **50 pairs**, not 50
records, and it is built in two tiers:

| Tier | How pairs were generated | Pairs | Continuations | Distinct issues | Hard |
|---|---|---|---|---|---|
| Parcel | Both records touch the same parcel or the same block | 28 | 8 | 20 | 14 |
| Citywide | No shared parcel; shared sponsor and title cosine at or above 0.97 | 22 | 11 | 11 | 12 |
| **Total** | | **50** | **19** | **31** | **26** |

The second tier exists because the first one is not enough on its own. Probing what parcel
matching misses turned up a whole class of true continuation it cannot see: citywide bills
that die at end of term and return under a new file number with no parcel anywhere in them.
Sitting immediately beside them are recurring annual bills with identical titles that are
**not** continuations. See [eval/RESULTS.md](eval/RESULTS.md).

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
- **A small evaluation population.** 50 hand labeled pairs, 19 of them continuations. That
  is what a corpus of 1,679 records with 270 parcel bearing items supports, and the number
  is stated rather than implied.
- **The labels are one person's judgment.** They were assigned by reading the source
  documents, and a tuned two clause rule reproduces them exactly. Both facts are reported
  in [eval/RESULTS.md](eval/RESULTS.md) rather than left for a reader to discover.
- **Parcels are resolved from titles.** 270 of 1,679 records name a parcel Quorum can parse
  and 252 of those resolve against the city gazetteer. The remainder are budget,
  procurement, personnel and citywide matters that name no property, and Quorum drops them
  rather than guessing.
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
