"""Exercise the notebook's decoding logic on synthetic SPAR-shaped tables.

Covers the cases that bite in practice: duplicate display labels, a valid empty table,
a single-column table, non-numeric cells, and nulls. Requires nbformat and pandas; runs
outside Fabric because the functions under test touch neither the SDK nor notebookutils.

    python notebooks/factset-spar/test_decode_logic.py
"""

from pathlib import Path

import nbformat
import pandas as pd

NOTEBOOK = Path(__file__).with_name("factset_spar_multi_strategy.ipynb")
nb = nbformat.read(NOTEBOOK, as_version=4)
helpers_src = [c.source for c in nb.cells if c.cell_type == "code" and "def tidy_tables" in c.source][0]

ns = {"pd": pd}
exec(helpers_src, ns)
resolve_duplicate_labels = ns["resolve_duplicate_labels"]
tidy_tables = ns["tidy_tables"]
TIDY_COLUMNS = ns["TIDY_COLUMNS"]

failures = []


def check(name, condition, detail=""):
    print(("PASS  " if condition else "FAIL  ") + name + (f"  {detail}" if detail and not condition else ""))
    if not condition:
        failures.append(name)


# 1. duplicate display labels resolve deterministically and preserve originals
labels = ["Portfolio", "Alpha", "Beta", "Alpha", "Alpha"]
resolved = resolve_duplicate_labels(labels)
check("duplicate labels disambiguated", resolved == ["Portfolio", "Alpha", "Beta", "Alpha#2", "Alpha#3"], str(resolved))
check("resolution is deterministic", resolve_duplicate_labels(labels) == resolved)
check("unique labels untouched", resolve_duplicate_labels(["a", "b"]) == ["a", "b"])

# 2. a normal statistics table
normal = pd.DataFrame(
    {
        "Name": ["HBCM LC", "Russell 1000", "Peer median"],
        "Annualized Return": [12.4, 11.1, 10.2],
        "Tracking Error": [3.8, None, 4.1],
        "Rank": ["1st quartile", "n/a", "2nd quartile"],
    }
)
# 3. duplicate column labels, as a component with repeated statistic headers returns
duplicated = pd.DataFrame(
    [["HBCM SMID", 1.0, 2.0], ["Benchmark", 3.0, 4.0]],
    columns=["Name", "Capture", "Capture"],
)
# 4. a valid empty table and a single-column table
empty = pd.DataFrame(columns=["Name", "Annualized Return"])
single = pd.DataFrame({"Name": ["HBCM LCS"]})

frames = [normal, duplicated, empty, single]
tidied = tidy_tables("LC__risk_stats", frames)

check("one tidy frame per source table", len(tidied) == len(frames))
check("columns stable across frames", all(list(t.columns) == TIDY_COLUMNS for t in tidied))

expected_normal = len(normal) * (normal.shape[1] - 1)
check("normal table row count", len(tidied[0]) == expected_normal, f"{len(tidied[0])} != {expected_normal}")
check("strategy parsed from unit id", set(tidied[0]["strategy"]) == {"LC"})
check("component parsed from unit id", set(tidied[0]["component"]) == {"risk_stats"})
check("row labels preserved", set(tidied[0]["row_label"]) == set(normal["Name"]))
check("label column recorded", set(tidied[0]["label_column"]) == {"Name"})

expected_dup = len(duplicated) * (duplicated.shape[1] - 1)
check("duplicate-label table row count", len(tidied[1]) == expected_dup, f"{len(tidied[1])} != {expected_dup}")
check(
    "duplicate statistics keyed uniquely",
    sorted(tidied[1]["statistic"].unique()) == ["Capture", "Capture#2"],
    str(sorted(tidied[1]["statistic"].unique())),
)
check(
    "original labels retained",
    set(tidied[1]["statistic_label"].unique()) == {"Capture"},
    str(set(tidied[1]["statistic_label"].unique())),
)
check(
    "duplicate-label rows unique on the merge key",
    not tidied[1].duplicated(subset=["strategy", "component", "table_index", "row_label", "statistic"]).any(),
)

check("empty table preserved, not dropped", len(tidied[2]) == 0 and list(tidied[2].columns) == TIDY_COLUMNS)
check("single-column table yields no rows", len(tidied[3]) == 0)

# 5. value typing: nulls stay null, text stays text
combined = pd.concat(tidied, ignore_index=True)
combined["value_num"] = pd.to_numeric(combined["value_raw"], errors="coerce")
combined["value_text"] = combined["value_raw"].map(lambda v: None if pd.isna(v) else str(v))

tracking_error_bench = combined[
    (combined["row_label"] == "Russell 1000") & (combined["statistic"] == "Tracking Error")
]
check("source null stays null in both columns",
      bool(tracking_error_bench["value_num"].isna().all()) and bool(tracking_error_bench["value_text"].isna().all()))

rank_rows = combined[combined["statistic"] == "Rank"]
check("non-numeric coerces to null, text retained",
      bool(rank_rows["value_num"].isna().all()) and set(rank_rows["value_text"]) == set(normal["Rank"]))

numeric_row = combined[(combined["row_label"] == "HBCM LC") & (combined["statistic"] == "Annualized Return")]
check("numeric value preserved", float(numeric_row["value_num"].iloc[0]) == 12.4)
check("no zero substitution for nulls", int((combined["value_num"] == 0).sum()) == 0)

# 6. reconciliation arithmetic matches the notebook's expectation formula
for index, (source, tidy) in enumerate(zip(frames, tidied)):
    expected = 0 if source.empty or source.shape[1] < 2 else len(source) * (source.shape[1] - 1)
    check(f"reconciliation table {index}", len(tidy) == expected, f"{len(tidy)} != {expected}")

print()
print(f"{len(failures)} failing checks" if failures else "all checks passed")
raise SystemExit(1 if failures else 0)
