# Research intake and completeness queue

This applies the [monitoring workbook](https://docs.google.com/spreadsheets/d/1OtYxCVgk_Wb0m6KFSZtrDZeJpY3Io6NiiHQdbDrDCow/edit) to repeatable collection. It does not certify that the dashboard is complete.

The versioned registry contains 93 source-resource rows, 358 overlapping entity-registry rows (270 global / 88 Indonesia), 44 topic searches, 57 macro records, nine workstreams, 18 validation rules and the field dictionary. Its initial evidence and reviewed-record baseline is dated **18 October 2026**. Registry rows are not unique corporations. Source-resource rows are not working RSS feeds.

## Run and resume

```sh
python3 monitoring/test_refresh.py
python3 monitoring/refresh.py --through 2026-10-18 --plan-only
python3 monitoring/refresh.py --through 2026-10-18 --limit 500 --balanced-months --workers 6
```

Run the GitHub Action **Research intake and coverage audit** from Actions → Run workflow. Choose `all`, `entity`, `topic`, `publisher` or `feed`. It restores the previous state from the Actions cache and saves the next state plus review/coverage artifacts. A missing/expired cache restarts discovery; it does not invent previous progress. Download artifacts as a durable research backup. Runs are manual; no recurring schedule has been enabled.

The default date follows Jakarta. Future cutoffs are rejected. The initial January–October 2026 plan has 5,644 discovery/feed tasks before capped-query refinement. Current partial months and recent feeds can be rechecked; older successful searches become eligible weekly and failures hourly. These intervals govern eligibility when the runner is invoked, not a background schedule.

## Outputs

- `results/state.json`: resumable task attempts and every retained discovery record. Subject and identity mismatches are quarantined, preserved separately from eligible candidates. No five-headline collection cap. A request cap limits each run, not saved research.
- `results/coverage.csv`: one entity/month row, discovery state, unreviewed leads, unresolved narrower windows and the separately dated baseline reviewed-record count.
- `results/primary-review-queue.json`: all official/licensed resource tasks and macro-history reconciliation tasks, with access notes and definition guards.
- `results/summary.json`: actual attempted, blocked, capped and unchecked task counts; no automatic publication.

HTTP failures and invalid/non-feed responses remain **source-unavailable**. Successful zero-result searches become **searched-no-leads**, never “no company news.” A 100-item search is split into seven-day windows, then days; a capped day stays flagged. Native feeds are bounded snapshots, even if they contain fewer than 100 items. Google News date searches and feeds do not provide exhaustive historical coverage. Query match and publisher name are not source verification.

The GitHub workflow uses balanced month selection so every month gets a turn, with workstreams and publisher domains interleaved. It fetches up to six public feeds concurrently; only one thread writes collection state. The default current-first queue remains available locally.

The fair queue alternates entities, topics, publisher-domain searches and feeds. P0/current periods come first within each family. Exact alias, context and namesake exclusions run before entity attribution. Topic and official-feed discoveries without a company match may still enter the internal review queue; they are not assigned to a company. URL tracking parameters are normalized, but syndicated articles and similar headlines still need editorial event deduplication.

## Editorial workflow

1. W1 maintains the registry, aliases, domains, permissions and shared collection; W2–W8 verify their subject areas; W9 reconciles duplicates, publication decisions and monthly gaps. Detailed scopes and acceptance criteria are in `registry.json` and the workbook.
2. Review the original article or official document. Record separate publication date, event date, reporting period, checked date, factual claims, geography, entity, source URL and reviewer. Every automatic discovery remains `reviewed: false` and `verified: false`; it cannot alter market-share, policy, macro, funding or valuation figures.
3. Keep announced/signed/approved/closed transactions distinct. Keep funding, valuation, commitments and debt amounts distinct. No disclosed amount means **undisclosed**, not zero. Separate actual/provisional/forecast macro observations and series definitions.
4. Reconcile macro histories with BI/BPS/OJK/other original tables, including publication lags and revisions. A reviewed news item is not a complete numeric time series. Obtain permitted historical data for gaps; never interpolate missing actuals to simulate coverage.
5. After evidence review, update the project's existing curated research files, run the domain validation and build checks, then publish the reviewed app release. This intake action has read-only repository permissions and cannot push changes to the dashboard. Empty cards and backend collection failures stay out of the public UI.

Reuters/Tech in Asia/DealStreetAsia and subscription resources keep their access limitations. Feed failures are not bypassed. The 40 publisher domains also have indexed search fallbacks through the global publisher collector; the intake topic/entity searches provide broader discovery. Apple/Google developer review APIs require authorized apps and do not grant a public competitor archive. X/Twitter stays excluded.

## Maintaining the plan

Update `registry.json` when entities, official sources, aliases, releases or subscriptions change; retain evidence dates. Query and date boundaries determine stable task IDs, so unchanged jobs resume. Keep the packaged `news-relevance.py` and `collect-global-publisher-news.py` identity helpers synchronized with project scripts when changing guard rules; tests cover common namesakes. The full app's global collector now reads the shared 40-publisher registry and only activates native feeds that passed XML validation; other publishers retain search fallback. Public display limits remain separate from the full research store.

This is a public-source research workflow, not a paywall bypass or a licensed data subscription. “Checked” means an auditable attempt; completeness requires primary evidence review and still has source limits.


### Language coverage

Company discovery retains English searches and adds the selected operating markets’ local-language news editions. Publication titles stay in the original language; reviewed summaries and GoTo hypotheses are edited in English. Native-script aliases support major Asian brands. This is a selected-market language plan, not a claim to cover every Indian regional language or every operating country. Localized monthly feeds are bounded at the provider’s result limit; capped results are reported as unresolved, never complete archives. English historical search refinements retain their previous daily-window audit.
