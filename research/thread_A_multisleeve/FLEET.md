# Running iteration 4 under /fleet

`/fleet` was not available in this environment, so the fan-out ran as OS
processes. The worker is written to be handed to your runner unchanged.

**Unit of work:** one symbol. Fully independent — no shared state, no ordering
requirement, no cross-symbol communication. This satisfies the Crucible
ownership map's INDEPENDENT classification, which is the only condition under
which parallel fan-out is safe.

**Contract:**
- Input: a path to a CSV with columns `DateTime, Open, High, Low, Close, Volume`.
- Output: a list of dicts (aggregate stats) plus a pickle of trade-level rows at
  `work/tr/<SYMBOL>.pkl` containing `date, pnl, r, sym, geo`.
- Failure mode: returns `[]` on any bad input. A dead symbol never blocks the fleet.

**To reproduce or extend:**
```
python fleet_run.py          # fans out over collected_stocks/*.csv
```
Change the glob in `fleet_run.py` to point at a different symbol set. To run the
decisive ETF test named in ASSESSMENT_iteration4.md §5, drop 20 index-ETF CSVs
into a directory and repoint that glob — no other change is needed.

**Do not parallelise across geometries or across the analysis stage.** Those are
COUPLED: the control must be generated in the same process as the strategy it is
matched to, and the date-clustered inference needs the whole pooled trade set.
Splitting them is exactly the failure mode the framework's fan-out rule exists
to prevent.
