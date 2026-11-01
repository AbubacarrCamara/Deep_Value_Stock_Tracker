from __future__ import annotations

import math

import pandas as pd

from .config import (
    CALCULATED_METRICS_FILE,
    DEEP_VALUE_CORE_FILE,
    DEEP_VALUE_MAX_EV_FCF,
    DEEP_VALUE_MAX_MARKET_CAP,
    DEEP_VALUE_MAX_NET_DEBT_EBITDA,
    DEEP_VALUE_MAX_SHARE_DILUTION,
    DEEP_VALUE_MIN_MARKET_CAP,
    DEEP_VALUE_MIN_POSITIVE_FCF_YEARS,
    DEEP_VALUE_MIN_REVENUE_CAGR,
    DEEP_VALUE_PRIORITY_FILE,
    DEEP_VALUE_PRIORITY_MAX_EV_FCF,
    RESULTS_DATA_DIR,
)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------


def safe_float(value) -> float | None:
    """
    Convert a value to float safely.

    Returns None for:
    - NaN
    - infinity
    - invalid values
    """

    if value is None:
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if math.isnan(number) or math.isinf(number):
        return None

    return number


def passes_market_cap(
    row: pd.Series,
) -> bool:
    """
    Require:

    $50m <= market cap <= $2.5bn
    """

    market_cap = safe_float(
        row.get("market_cap")
    )

    if market_cap is None:
        return False

    return (
        DEEP_VALUE_MIN_MARKET_CAP
        <= market_cap
        <= DEEP_VALUE_MAX_MARKET_CAP
    )


def passes_ev_fcf(
    row: pd.Series,
) -> bool:
    """
    Require:

    0 < EV / normalised FCF <= 8x
    """

    ev_fcf = safe_float(
        row.get("ev_normalised_fcf")
    )

    if ev_fcf is None:
        return False

    return (
        0
        < ev_fcf
        <= DEEP_VALUE_MAX_EV_FCF
    )


def passes_positive_fcf_history(
    row: pd.Series,
) -> bool:
    """
    Require at least 3 positive FCF years.
    """

    positive_years = safe_float(
        row.get("positive_fcf_years")
    )

    if positive_years is None:
        return False

    return (
        positive_years
        >= DEEP_VALUE_MIN_POSITIVE_FCF_YEARS
    )


def passes_leverage(
    row: pd.Series,
) -> bool:
    """
    Require:

    Net Debt / EBITDA <= 2.5x

    Negative values are allowed and usually
    indicate net cash.

    If EBITDA is unavailable, the company does
    not automatically pass.
    """

    leverage = safe_float(
        row.get("net_debt_ebitda")
    )

    if leverage is None:
        return False

    return (
        leverage
        <= DEEP_VALUE_MAX_NET_DEBT_EBITDA
    )


def passes_revenue_trend(
    row: pd.Series,
) -> bool:
    """
    Require:

    3-year revenue CAGR >= -5%
    """

    revenue_cagr = safe_float(
        row.get("revenue_cagr_3y")
    )

    if revenue_cagr is None:
        return False

    return (
        revenue_cagr
        >= DEEP_VALUE_MIN_REVENUE_CAGR
    )


def has_excessive_dilution(
    row: pd.Series,
) -> bool:
    """
    Flag companies where share count has increased
    by more than 20%.

    This is currently a warning rather than an
    automatic rejection.
    """

    dilution = safe_float(
        row.get("share_count_change_pct")
    )

    if dilution is None:
        return False

    return (
        dilution
        > DEEP_VALUE_MAX_SHARE_DILUTION
    )


# ---------------------------------------------------------
# Scoring
# ---------------------------------------------------------


def valuation_score(
    ev_fcf: float | None,
) -> int:
    """
    Give cheaper companies a higher valuation score.

    Maximum: 40 points
    """

    if ev_fcf is None:
        return 0

    if ev_fcf <= 0:
        return 0

    if ev_fcf <= 3:
        return 40

    if ev_fcf <= 4:
        return 35

    if ev_fcf <= 5:
        return 30

    if ev_fcf <= 6:
        return 25

    if ev_fcf <= 7:
        return 20

    if ev_fcf <= 8:
        return 15

    return 0


def fcf_consistency_score(
    positive_years: float | None,
) -> int:
    """
    Maximum: 20 points
    """

    if positive_years is None:
        return 0

    if positive_years >= 5:
        return 20

    if positive_years >= 4:
        return 15

    if positive_years >= 3:
        return 10

    return 0


def balance_sheet_score(
    net_debt_ebitda: float | None,
) -> int:
    """
    Maximum: 20 points
    """

    if net_debt_ebitda is None:
        return 0

    # Net cash
    if net_debt_ebitda < 0:
        return 20

    if net_debt_ebitda <= 0.5:
        return 18

    if net_debt_ebitda <= 1:
        return 15

    if net_debt_ebitda <= 1.5:
        return 12

    if net_debt_ebitda <= 2:
        return 8

    if net_debt_ebitda <= 2.5:
        return 5

    return 0


def revenue_score(
    revenue_cagr: float | None,
) -> int:
    """
    Maximum: 10 points
    """

    if revenue_cagr is None:
        return 0

    if revenue_cagr >= 0.10:
        return 10

    if revenue_cagr >= 0.05:
        return 9

    if revenue_cagr >= 0:
        return 8

    if revenue_cagr >= -0.02:
        return 6

    if revenue_cagr >= -0.05:
        return 4

    return 0


def dilution_score(
    share_change: float | None,
) -> int:
    """
    Maximum: 10 points.

    Negative share-count change indicates
    buybacks.
    """

    if share_change is None:
        return 5

    if share_change <= -0.10:
        return 10

    if share_change <= 0:
        return 9

    if share_change <= 0.05:
        return 8

    if share_change <= 0.10:
        return 6

    if share_change <= 0.20:
        return 3

    return 0


def calculate_screen_score(
    row: pd.Series,
) -> int:
    """
    Initial quantitative research score.

    Maximum: 100.

    This is NOT an investment score.

    It only determines which companies deserve
    research first.
    """

    ev_fcf = safe_float(
        row.get("ev_normalised_fcf")
    )

    positive_years = safe_float(
        row.get("positive_fcf_years")
    )

    leverage = safe_float(
        row.get("net_debt_ebitda")
    )

    revenue_cagr = safe_float(
        row.get("revenue_cagr_3y")
    )

    share_change = safe_float(
        row.get("share_count_change_pct")
    )

    score = (
        valuation_score(
            ev_fcf
        )
        + fcf_consistency_score(
            positive_years
        )
        + balance_sheet_score(
            leverage
        )
        + revenue_score(
            revenue_cagr
        )
        + dilution_score(
            share_change
        )
    )

    return score


# ---------------------------------------------------------
# Filter individual company
# ---------------------------------------------------------


def evaluate_company(
    row: pd.Series,
) -> dict:
    """
    Evaluate one company against all Deep Value Core
    rules.
    """

    market_cap_pass = (
        passes_market_cap(row)
    )

    ev_fcf_pass = (
        passes_ev_fcf(row)
    )

    fcf_history_pass = (
        passes_positive_fcf_history(row)
    )

    leverage_pass = (
        passes_leverage(row)
    )

    revenue_pass = (
        passes_revenue_trend(row)
    )

    excessive_dilution = (
        has_excessive_dilution(row)
    )

    passes_core = all(
        [
            market_cap_pass,
            ev_fcf_pass,
            fcf_history_pass,
            leverage_pass,
            revenue_pass,
        ]
    )

    ev_fcf = safe_float(
        row.get("ev_normalised_fcf")
    )

    priority_candidate = (
        passes_core
        and ev_fcf is not None
        and ev_fcf
        <= DEEP_VALUE_PRIORITY_MAX_EV_FCF
    )

    return {
        "passes_market_cap": (
            market_cap_pass
        ),

        "passes_ev_fcf": (
            ev_fcf_pass
        ),

        "passes_fcf_history": (
            fcf_history_pass
        ),

        "passes_leverage": (
            leverage_pass
        ),

        "passes_revenue_trend": (
            revenue_pass
        ),

        "excessive_dilution_warning": (
            excessive_dilution
        ),

        "passes_deep_value_core": (
            passes_core
        ),

        "priority_candidate": (
            priority_candidate
        ),

        "screen_score": (
            calculate_screen_score(row)
        ),
    }


# ---------------------------------------------------------
# Load data
# ---------------------------------------------------------


def load_calculated_metrics() -> pd.DataFrame:
    """
    Load data produced by calculations.py.
    """

    if not CALCULATED_METRICS_FILE.exists():

        raise FileNotFoundError(
            "\nCalculated metrics file does "
            "not exist:\n"
            f"{CALCULATED_METRICS_FILE}\n\n"
            "Run:\n"
            "python -m src.calculations\n"
            "first."
        )

    dataframe = pd.read_csv(
        CALCULATED_METRICS_FILE
    )

    if dataframe.empty:
        raise ValueError(
            "Calculated metrics file is empty."
        )

    return dataframe


# ---------------------------------------------------------
# Apply filters
# ---------------------------------------------------------


def apply_filters(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Evaluate every company.

    Adds pass/fail columns and a quantitative
    screening score.
    """

    evaluated_rows = []

    total = len(dataframe)

    print()
    print(
        "Applying Deep Value Core filters..."
    )
    print(
        f"Companies: {total}"
    )
    print()

    for index, row in dataframe.iterrows():

        symbol = row.get(
            "symbol",
            "UNKNOWN",
        )

        print(
            f"[{index + 1}/{total}] "
            f"{symbol}"
        )

        evaluation = evaluate_company(
            row
        )

        combined = row.to_dict()

        combined.update(
            evaluation
        )

        evaluated_rows.append(
            combined
        )

    return pd.DataFrame(
        evaluated_rows
    )


# ---------------------------------------------------------
# Create result tables
# ---------------------------------------------------------


def create_core_results(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Return only companies that pass every required
    Deep Value Core filter.
    """

    core = dataframe[
        dataframe[
            "passes_deep_value_core"
        ]
        == True
    ].copy()

    core = core.sort_values(
        by=[
            "screen_score",
            "ev_normalised_fcf",
        ],
        ascending=[
            False,
            True,
        ],
    )

    return core.reset_index(
        drop=True
    )


def create_priority_results(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Return companies in our preferred <=5x
    EV / normalised FCF hunting ground.
    """

    priority = dataframe[
        dataframe[
            "priority_candidate"
        ]
        == True
    ].copy()

    priority = priority.sort_values(
        by=[
            "screen_score",
            "ev_normalised_fcf",
        ],
        ascending=[
            False,
            True,
        ],
    )

    return priority.reset_index(
        drop=True
    )


# ---------------------------------------------------------
# Save results
# ---------------------------------------------------------


def save_results(
    core: pd.DataFrame,
    priority: pd.DataFrame,
) -> None:
    """
    Save final screening results.
    """

    RESULTS_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    core.to_csv(
        DEEP_VALUE_CORE_FILE,
        index=False,
    )

    priority.to_csv(
        DEEP_VALUE_PRIORITY_FILE,
        index=False,
    )

    print()
    print(
        "Results saved:"
    )

    print(
        f"\nDeep Value Core:\n"
        f"{DEEP_VALUE_CORE_FILE}"
    )

    print(
        f"\nPriority <=5x:\n"
        f"{DEEP_VALUE_PRIORITY_FILE}"
    )


# ---------------------------------------------------------
# Console summaries
# ---------------------------------------------------------


def print_filter_summary(
    dataframe: pd.DataFrame,
    core: pd.DataFrame,
    priority: pd.DataFrame,
) -> None:
    """
    Show how many companies survived.
    """

    total = len(dataframe)

    print()
    print(
        "======================================="
    )
    print(
        "DEEP VALUE CORE RESULTS"
    )
    print(
        "======================================="
    )

    print(
        f"Companies analysed: {total}"
    )

    print(
        f"Passed core screen: {len(core)}"
    )

    print(
        f"Priority <=5x EV/FCF: "
        f"{len(priority)}"
    )

    if total > 0:

        pass_rate = (
            len(core)
            / total
        ) * 100

        print(
            f"Core pass rate: "
            f"{pass_rate:.1f}%"
        )


def print_priority_companies(
    priority: pd.DataFrame,
    number: int = 20,
) -> None:
    """
    Print the highest-priority research candidates.
    """

    if priority.empty:

        print()
        print(
            "No companies entered the "
            "priority group."
        )

        return

    display_columns = [
        column
        for column in [
            "symbol",
            "company_name",
            "screen_score",
            "market_cap",
            "enterprise_value",
            "normalised_fcf",
            "ev_normalised_fcf",
            "normalised_fcf_yield",
            "positive_fcf_years",
            "net_debt",
            "net_debt_ebitda",
            "revenue_cagr_3y",
            "share_count_change_pct",
            "excessive_dilution_warning",
        ]
        if column in priority.columns
    ]

    print()
    print(
        "TOP PRIORITY RESEARCH CANDIDATES"
    )
    print(
        "---------------------------------------"
    )

    print(
        priority[
            display_columns
        ]
        .head(number)
        .to_string(
            index=False
        )
    )


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------


def main() -> None:

    calculated = (
        load_calculated_metrics()
    )

    evaluated = apply_filters(
        calculated
    )

    core = create_core_results(
        evaluated
    )

    priority = create_priority_results(
        evaluated
    )

    save_results(
        core,
        priority,
    )

    print_filter_summary(
        evaluated,
        core,
        priority,
    )

    print_priority_companies(
        priority
    )


if __name__ == "__main__":
    main()