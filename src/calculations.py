from __future__ import annotations

import math
from statistics import mean, median

import pandas as pd

from .config import (
    CALCULATED_METRICS_FILE,
    HISTORY_YEARS,
    PROCESSED_DATA_DIR,
    YAHOO_FUNDAMENTALS_FILE,
)


# ---------------------------------------------------------
# General helpers
# ---------------------------------------------------------


def safe_float(value) -> float | None:
    """
    Convert a value to a usable float.

    Returns None for:
    - missing values
    - NaN
    - infinity
    - invalid strings
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


def safe_divide(
    numerator: float | None,
    denominator: float | None,
) -> float | None:
    """
    Divide two values safely.
    """

    if numerator is None:
        return None

    if denominator is None:
        return None

    if denominator == 0:
        return None

    return numerator / denominator


def get_history(
    row: pd.Series,
    prefix: str,
) -> list[float]:
    """
    Collect historical values such as:

    fcf_fy0
    fcf_fy1
    ...
    fcf_fy4

    Missing values are ignored.
    """

    values: list[float] = []

    for year_index in range(HISTORY_YEARS):

        column = f"{prefix}_fy{year_index}"

        if column not in row.index:
            continue

        value = safe_float(
            row[column]
        )

        if value is not None:
            values.append(value)

    return values


def get_latest(
    row: pd.Series,
    column: str,
) -> float | None:
    """
    Return a single numeric column safely.
    """

    if column not in row.index:
        return None

    return safe_float(
        row[column]
    )


# ---------------------------------------------------------
# Free cash flow calculations
# ---------------------------------------------------------


def calculate_fcf_statistics(
    row: pd.Series,
) -> dict:
    """
    Calculate historical free-cash-flow statistics.

    We deliberately use the median as our primary
    normalised FCF measure.

    This reduces the effect of one unusually strong
    or weak year.
    """

    fcf_values = get_history(
        row,
        "fcf",
    )

    if not fcf_values:
        return {
            "fcf_years_available": 0,
            "positive_fcf_years": 0,
            "negative_fcf_years": 0,
            "fcf_positive_ratio": None,
            "average_fcf": None,
            "median_fcf": None,
            "normalised_fcf": None,
            "minimum_fcf": None,
            "maximum_fcf": None,
        }

    positive_years = sum(
        value > 0
        for value in fcf_values
    )

    negative_years = sum(
        value < 0
        for value in fcf_values
    )

    return {
        "fcf_years_available": len(
            fcf_values
        ),

        "positive_fcf_years": (
            positive_years
        ),

        "negative_fcf_years": (
            negative_years
        ),

        "fcf_positive_ratio": (
            positive_years
            / len(fcf_values)
        ),

        "average_fcf": mean(
            fcf_values
        ),

        "median_fcf": median(
            fcf_values
        ),

        # For V1 we use the five-year median
        # as normalised FCF.
        "normalised_fcf": median(
            fcf_values
        ),

        "minimum_fcf": min(
            fcf_values
        ),

        "maximum_fcf": max(
            fcf_values
        ),
    }


# ---------------------------------------------------------
# Revenue calculations
# ---------------------------------------------------------


def calculate_revenue_cagr_3y(
    row: pd.Series,
) -> float | None:
    """
    Calculate the three-year revenue CAGR.

    Uses:

    FY0 = latest fiscal year
    FY3 = approximately three fiscal years earlier

    Formula:

    CAGR = (Latest / Earlier) ** (1 / 3) - 1
    """

    latest_revenue = get_latest(
        row,
        "revenue_fy0",
    )

    earlier_revenue = get_latest(
        row,
        "revenue_fy3",
    )

    if latest_revenue is None:
        return None

    if earlier_revenue is None:
        return None

    if latest_revenue <= 0:
        return None

    if earlier_revenue <= 0:
        return None

    return (
        latest_revenue
        / earlier_revenue
    ) ** (1 / 3) - 1


def calculate_revenue_change(
    row: pd.Series,
) -> float | None:
    """
    Calculate latest-year revenue growth.

    FY0 versus FY1.
    """

    latest_revenue = get_latest(
        row,
        "revenue_fy0",
    )

    previous_revenue = get_latest(
        row,
        "revenue_fy1",
    )

    if latest_revenue is None:
        return None

    if previous_revenue is None:
        return None

    if previous_revenue == 0:
        return None

    return (
        latest_revenue
        / previous_revenue
    ) - 1


# ---------------------------------------------------------
# Balance-sheet calculations
# ---------------------------------------------------------


def calculate_net_debt(
    row: pd.Series,
) -> float | None:
    """
    Net Debt = Total Debt - Cash

    A negative result means the company has net cash.
    """

    debt = get_latest(
        row,
        "total_debt",
    )

    cash = get_latest(
        row,
        "cash",
    )

    if debt is None and cash is None:
        return None

    if debt is None:
        debt = 0

    if cash is None:
        cash = 0

    return debt - cash


def calculate_enterprise_value(
    row: pd.Series,
) -> float | None:
    """
    Simplified enterprise value:

    EV = Market Cap + Debt - Cash

    Later versions can include:
    - preferred equity
    - minority interests
    - pension adjustments
    - other liabilities

    For the first screener this simpler definition
    is sufficient.
    """

    market_cap = get_latest(
        row,
        "market_cap",
    )

    debt = get_latest(
        row,
        "total_debt",
    )

    cash = get_latest(
        row,
        "cash",
    )

    if market_cap is None:
        return None

    if debt is None:
        debt = 0

    if cash is None:
        cash = 0

    return (
        market_cap
        + debt
        - cash
    )


# ---------------------------------------------------------
# Valuation calculations
# ---------------------------------------------------------


def calculate_ev_fcf(
    enterprise_value: float | None,
    normalised_fcf: float | None,
) -> float | None:
    """
    Enterprise Value / Normalised FCF.

    We only calculate this where normalised FCF
    is positive.

    Negative FCF does not produce a meaningful
    valuation multiple.
    """

    if enterprise_value is None:
        return None

    if normalised_fcf is None:
        return None

    if normalised_fcf <= 0:
        return None

    return (
        enterprise_value
        / normalised_fcf
    )


def calculate_fcf_yield(
    enterprise_value: float | None,
    normalised_fcf: float | None,
) -> float | None:
    """
    Normalised FCF / Enterprise Value.

    Example:

    EV = $100m
    Normalised FCF = $20m

    FCF yield = 20%
    """

    if enterprise_value is None:
        return None

    if enterprise_value <= 0:
        return None

    if normalised_fcf is None:
        return None

    return (
        normalised_fcf
        / enterprise_value
    )


# ---------------------------------------------------------
# Leverage
# ---------------------------------------------------------


def calculate_net_debt_ebitda(
    row: pd.Series,
    net_debt: float | None,
) -> float | None:
    """
    Net Debt / EBITDA.

    Negative values are allowed.

    Example:

    Net Debt = -$50m
    EBITDA = $25m

    Net Debt / EBITDA = -2.0x

    This indicates net cash.
    """

    ebitda = get_latest(
        row,
        "ebitda_fy0",
    )

    if net_debt is None:
        return None

    if ebitda is None:
        return None

    if ebitda <= 0:
        return None

    return (
        net_debt
        / ebitda
    )


# ---------------------------------------------------------
# Share dilution
# ---------------------------------------------------------


def calculate_share_count_change(
    row: pd.Series,
) -> dict:
    """
    Measure change in shares outstanding.

    We compare the newest available share-count figure
    with the oldest available figure.

    Positive percentage = dilution.

    Negative percentage = net buybacks.
    """

    shares: list[float] = []

    for year_index in range(
        HISTORY_YEARS
    ):

        value = get_latest(
            row,
            f"shares_outstanding_fy{year_index}",
        )

        if value is not None:
            if value > 0:
                shares.append(value)

    if len(shares) < 2:
        return {
            "share_history_years_available": (
                len(shares)
            ),
            "share_count_change_pct": None,
        }

    latest_shares = shares[0]
    oldest_shares = shares[-1]

    if oldest_shares == 0:
        return {
            "share_history_years_available": (
                len(shares)
            ),
            "share_count_change_pct": None,
        }

    change = (
        latest_shares
        / oldest_shares
    ) - 1

    return {
        "share_history_years_available": (
            len(shares)
        ),

        "share_count_change_pct": change,
    }


# ---------------------------------------------------------
# Individual company calculation
# ---------------------------------------------------------


def calculate_company_metrics(
    row: pd.Series,
) -> dict:
    """
    Calculate every Deep Value metric for a single
    company.
    """

    calculated = {}

    # -----------------------------------------------------
    # FCF
    # -----------------------------------------------------

    fcf_stats = (
        calculate_fcf_statistics(
            row
        )
    )

    calculated.update(
        fcf_stats
    )

    normalised_fcf = (
        fcf_stats[
            "normalised_fcf"
        ]
    )

    # -----------------------------------------------------
    # Revenue
    # -----------------------------------------------------

    calculated[
        "revenue_cagr_3y"
    ] = calculate_revenue_cagr_3y(
        row
    )

    calculated[
        "latest_revenue_growth"
    ] = calculate_revenue_change(
        row
    )

    # -----------------------------------------------------
    # Balance sheet
    # -----------------------------------------------------

    net_debt = calculate_net_debt(
        row
    )

    enterprise_value = (
        calculate_enterprise_value(
            row
        )
    )

    calculated[
        "net_debt"
    ] = net_debt

    calculated[
        "enterprise_value"
    ] = enterprise_value

    # -----------------------------------------------------
    # Valuation
    # -----------------------------------------------------

    calculated[
        "ev_normalised_fcf"
    ] = calculate_ev_fcf(
        enterprise_value,
        normalised_fcf,
    )

    calculated[
        "normalised_fcf_yield"
    ] = calculate_fcf_yield(
        enterprise_value,
        normalised_fcf,
    )

    # -----------------------------------------------------
    # Leverage
    # -----------------------------------------------------

    calculated[
        "net_debt_ebitda"
    ] = calculate_net_debt_ebitda(
        row,
        net_debt,
    )

    # -----------------------------------------------------
    # Dilution
    # -----------------------------------------------------

    share_stats = (
        calculate_share_count_change(
            row
        )
    )

    calculated.update(
        share_stats
    )

    # -----------------------------------------------------
    # Simple balance-sheet flags
    # -----------------------------------------------------

    calculated[
        "has_net_cash"
    ] = (
        net_debt is not None
        and net_debt < 0
    )

    calculated[
        "positive_normalised_fcf"
    ] = (
        normalised_fcf is not None
        and normalised_fcf > 0
    )

    return calculated


# ---------------------------------------------------------
# Main calculation process
# ---------------------------------------------------------


def load_fundamentals() -> pd.DataFrame:
    """
    Load Yahoo fundamentals.
    """

    if not YAHOO_FUNDAMENTALS_FILE.exists():

        raise FileNotFoundError(
            "\nYahoo fundamentals file "
            "does not exist:\n"
            f"{YAHOO_FUNDAMENTALS_FILE}\n\n"
            "Run:\n"
            "python -m src.yahoo_data\n"
            "first."
        )

    dataframe = pd.read_csv(
        YAHOO_FUNDAMENTALS_FILE
    )

    if dataframe.empty:

        raise ValueError(
            "Yahoo fundamentals file "
            "contains no companies."
        )

    return dataframe


def calculate_all_metrics(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate metrics for every company.

    The original Yahoo data is retained and the
    calculated metrics are added as new columns.
    """

    calculated_rows = []

    total = len(dataframe)

    print()
    print(
        "Calculating Deep Value metrics..."
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

        metrics = (
            calculate_company_metrics(
                row
            )
        )

        combined = row.to_dict()

        combined.update(
            metrics
        )

        calculated_rows.append(
            combined
        )

    return pd.DataFrame(
        calculated_rows
    )


def save_metrics(
    dataframe: pd.DataFrame,
) -> None:
    """
    Save calculated data.
    """

    PROCESSED_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        CALCULATED_METRICS_FILE,
        index=False,
    )

    print()
    print(
        f"Saved calculated metrics to:\n"
        f"{CALCULATED_METRICS_FILE}"
    )


# ---------------------------------------------------------
# Console preview
# ---------------------------------------------------------


def print_summary(
    dataframe: pd.DataFrame,
) -> None:
    """
    Display useful summary information.
    """

    print()
    print(
        "---------------------------------------"
    )
    print(
        "DEEP VALUE CALCULATION SUMMARY"
    )
    print(
        "---------------------------------------"
    )

    print(
        f"Companies analysed: "
        f"{len(dataframe)}"
    )

    if (
        "positive_normalised_fcf"
        in dataframe.columns
    ):

        positive_fcf = (
            dataframe[
                "positive_normalised_fcf"
            ]
            .fillna(False)
            .sum()
        )

        print(
            f"Positive normalised FCF: "
            f"{positive_fcf}"
        )

    if "has_net_cash" in dataframe.columns:

        net_cash = (
            dataframe[
                "has_net_cash"
            ]
            .fillna(False)
            .sum()
        )

        print(
            f"Net cash companies: "
            f"{net_cash}"
        )

    if (
        "ev_normalised_fcf"
        in dataframe.columns
    ):

        under_8 = dataframe[
            (
                dataframe[
                    "ev_normalised_fcf"
                ] > 0
            )
            &
            (
                dataframe[
                    "ev_normalised_fcf"
                ] <= 8
            )
        ]

        under_5 = dataframe[
            (
                dataframe[
                    "ev_normalised_fcf"
                ] > 0
            )
            &
            (
                dataframe[
                    "ev_normalised_fcf"
                ] <= 5
            )
        ]

        print(
            f"EV/FCF <= 8x: "
            f"{len(under_8)}"
        )

        print(
            f"EV/FCF <= 5x: "
            f"{len(under_5)}"
        )


def print_cheapest_companies(
    dataframe: pd.DataFrame,
    number: int = 20,
) -> None:
    """
    Display the lowest EV / normalised FCF companies.

    This is only a research preview.

    It is NOT the final Deep Value filter.
    """

    if (
        "ev_normalised_fcf"
        not in dataframe.columns
    ):
        return

    valid = dataframe[
        (
            dataframe[
                "ev_normalised_fcf"
            ].notna()
        )
        &
        (
            dataframe[
                "ev_normalised_fcf"
            ] > 0
        )
    ].copy()

    if valid.empty:
        return

    valid = valid.sort_values(
        by="ev_normalised_fcf",
        ascending=True,
    )

    columns = [
        column
        for column in [
            "symbol",
            "company_name",
            "market_cap",
            "enterprise_value",
            "normalised_fcf",
            "ev_normalised_fcf",
            "normalised_fcf_yield",
            "net_debt",
            "net_debt_ebitda",
            "revenue_cagr_3y",
            "positive_fcf_years",
            "share_count_change_pct",
        ]
        if column in valid.columns
    ]

    print()
    print(
        "Cheapest companies by "
        "EV / normalised FCF:"
    )
    print()

    print(
        valid[
            columns
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

    fundamentals = (
        load_fundamentals()
    )

    calculated = (
        calculate_all_metrics(
            fundamentals
        )
    )

    save_metrics(
        calculated
    )

    print_summary(
        calculated
    )

    print_cheapest_companies(
        calculated
    )


if __name__ == "__main__":
    main()