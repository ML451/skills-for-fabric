# FactSet SPAR Engine to OneLake

A Fabric **Python** notebook that fetches SPAR statistics for several strategies in a single
multi-unit calculation, keeps the raw response for audit, and merges a tidy result set into a
Delta table.

| File | Purpose |
|---|---|
| `factset_spar_multi_strategy.ipynb` | The notebook. 8 code cells. |
| `test_decode_logic.py` | Exercises the decoding helpers on synthetic SPAR-shaped tables. Runs outside Fabric. |

## Before the first run

1. **Import as a Python notebook.** The notebook metadata declares `language_info.name =
   "python"`, which is the documented minimum, but Fabric selects the kernel from its own
   metadata. After importing, confirm the language dropdown on the **Home** ribbon reads
   *Python* — switch it if it does not. Creating an empty Python notebook in the portal and
   pasting the cells in avoids the question entirely.
2. **Attach `hbcm_datahub`** as the default lakehouse. Every path resolves through the
   `/lakehouse/default` mount, so nothing works without it.
3. **Confirm the parameters cell.** Cell 4 carries the `parameters` tag. It should show the
   *Parameters* badge; if it does not, toggle it from the cell menu so pipeline and Job
   Scheduler runs can override the values.
4. **Fill the configuration.** `COMPONENTS` and `STRATEGIES` ship with `<FILL ...>`
   placeholders and the notebook raises before submitting anything while any remain.
5. **Run once with `DRY_RUN = True`** to confirm the unit list before spending a calculation.

## Configuration shape

`COMPONENTS` holds the saved SPAR component ids; the same set applies to every strategy, so
the request is their cross product. Three strategies and four components submit twelve
calculation units in one call. Unit ids are `{strategy}__{component}` and become columns in
the output.

Each strategy needs its account id and prefix, its benchmark id and prefix, and optionally a
peer universe id. **Prefixes are the usual cause of an unexplained 400** — `CLIENT:`,
`BENCH:`, `FDS_ETF:` and `RUSSELL:` are not interchangeable, and the error text does not say
which one was wrong.

Accounts default to `Net` returns (post-fee) and benchmarks to `Total`. Set
`USE_EACH_PORTFOLIO_INCEPTION = True` for a since-inception comparison across strategies whose
inception dates differ.

## Output

**Raw** — one JSON file per run at `Files/raw/spar/spar_{YYYYMMDDTHHMMSSZ}.json`, holding the
calculation id, the request parameters and every unit's response. Flat, dated in the filename,
write-once. It exists so a reshape never costs another API call, and so a vendor restatement
is provable after the fact.

**Curated** — `Tables/factset/spar_statistics`, one row per
`(as_of_date, strategy, component, table_index, row_label, statistic)`, which is also the merge
key. A re-run restates its own vintage instead of duplicating it. Values are kept twice:
`value_num` (numeric, null where the cell is not numeric) and `value_text` (the source
rendering). Nulls stay null; nothing is coerced to zero.

The long shape is deliberate. SPAR components differ in their column sets, and unpivoting means
adding or changing a component does not change the table schema.

## Behaviour worth knowing

- **Duplicate column labels are treated as valid.** A repeated statistic header is
  disambiguated deterministically (`Capture`, `Capture#2`) in `statistic`, with the original
  kept in `statistic_label`.
- **Empty tables are preserved, not dropped** — an empty result and a failed result are
  different things, and the reconciliation frame distinguishes them.
- **A table with only a label column contributes no rows** to the curated table. Its content
  remains in the raw file. Watch for this if a component is designed to return one.
- **Every unit is reconciled before anything is combined**: a tidy table must hold
  `rows x (columns - 1)` records, and the run raises if any unit fails, is missing, collides on
  the merge key, or carries a null row label.
- **Non-`Success` units do not silently vanish.** They appear in the reconciliation frame and
  fail validation.

## Maintenance

Python writes are not V-Ordered and get no automated compaction. At these volumes that is
unmeasurable, but the table will accumulate small files and an unbounded transaction log over
time. Schedule `OPTIMIZE` / `VACUUM` rather than assuming it happens, and re-frame any Direct
Lake model **before** vacuuming.

## Auth

Credentials come from the `HBCM_Config` variable library (`FACTSET_USERNAME`,
`FACTSET_API_KEY`) via `notebookutils.variableLibrary`. Two constraints follow from that:
access is same-workspace only, and variable library utilities do not currently support service
principals — so verify the executing identity before scheduling an unattended run. Moving to
OAuth `ConfidentialClient` with the app config in Key Vault replaces only the `spar_api_client`
helper.
