from __future__ import annotations

import math
from statistics import median

import pandas as pd

from .config import (
    CALCULATED_METRICS_FILE,
    PROCESSED_DATA_DIR,
    QUALITY_METRICS_FILE,
)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------


def safe_float(value) -> float | None:
    """
    Convert values safely to float.

    Missing, infinite or invalid values return None.
    """

    if value is None:
        return None

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    if math.isnan(value) or math.isinf(value):
        return None

    return value


def safe_divide(
    numerator: float | None,
    denominator: float | None,
) -> float | None:
    """
    Divide two numbers safely.
    """

    if numerator is None:
        return None

    if denominator is None:
        return None

    if denominator == 0:
        return None

    return numerator / denominator


# ---------------------------------------------------------
# Tax rate
# ---------------------------------------------------------


def calculate_effective_tax_rate(
    row: pd.Series,
    year_index: int = 0,
) -> float | None:
    """
    Effective tax rate:

    Tax Provision / Pretax Income

    Tax rates outside a sensible range are treated
    as unreliable for ROIC purposes.

    We allow 0-50% rather than forcing a specific
    statutory rate.
    """

    pretax_income = safe_float(
        row.get(
            f"pretax_income_fy{year_index}"
        )
    )

    tax_provision = safe_float(
        row.get(
            f"tax_provision_fy{year_index}"
        )
    )

    if pretax_income is None:
        return None

    if tax_provision is None:
        return None

    if pretax_income <= 0:
        return None

    tax_rate = (
        tax_provision
        / pretax_income
    )

    if tax_rate < 0:
        return None

    if tax_rate > 0.50:
        return None

    return tax_rate


def calculate_normalised_tax_rate(
    row: pd.Series,
) -> float | None:
    """
    Use the median valid effective tax rate from
    the available fiscal years.

    This reduces the effect of a one-off tax year.
    """

    tax_rates = []

    for year_index in range(5):

        tax_rate = (
            calculate_effective_tax_rate(
                row,
                year_index,
            )
        )

        if tax_rate is not None:
            tax_rates.append(
                tax_rate
            )

    if not tax_rates:
        return None

    return median(
        tax_rates
    )


# ---------------------------------------------------------
# NOPAT
# ---------------------------------------------------------


def calculate_nopat(
    row: pd.Series,
    tax_rate: float | None,
) -> float | None:
    """
    NOPAT:

    EBIT × (1 - tax rate)

    NOPAT = Net Operating Profit After Tax.
    """

    ebit = safe_float(
        row.get("ebit_fy0")
    )

    if ebit is None:
        return None

    if ebit <= 0:
        return None

    if tax_rate is None:
        return None

    return ebit * (
        1 - tax_rate
    )


# ---------------------------------------------------------
# Invested capital
# ---------------------------------------------------------


def calculate_invested_capital(
    row: pd.Series,
    year_index: int,
) -> float | None:
    """
    Simplified invested capital:

    Total Debt
    + Stockholders' Equity
    - Cash

    This is suitable for a first-pass screener.

    Detailed research should later consider
    leases, minority interests, pensions and
    excess cash separately.
    """

    debt = safe_float(
        row.get(
            f"total_debt_fy{year_index}"
        )
    )

    equity = safe_float(
        row.get(
            f"stockholders_equity_fy{year_index}"
        )
    )

    cash = safe_float(
        row.get(
            f"cash_fy{year_index}"
        )
    )

    if equity is None:
        return None

    if debt is None:
        debt = 0

    if cash is None:
        cash = 0

    invested_capital = (
        debt
        + equity
        - cash
    )

    if invested_capital <= 0:
        return None

    return invested_capital


def calculate_average_invested_capital(
    row: pd.Series,
) -> float | None:
    """
    Average invested capital using FY0 and FY1.

    This is preferable to comparing an entire year's
    operating profit with only the closing balance
    sheet.
    """

    current = (
        calculate_invested_capital(
            row,
            0,
        )
    )

    previous = (
        calculate_invested_capital(
            row,
            1,
        )
    )

    if current is None:
        return None

    if previous is None:
        return current

    return (
        current + previous
    ) / 2


# ---------------------------------------------------------
# ROIC
# ---------------------------------------------------------


def calculate_roic(
    nopat: float | None,
    average_invested_capital: float | None,
) -> float | None:
    """
    ROIC = NOPAT / Average Invested Capital
    """

    if nopat is None:
        return None

    if average_invested_capital is None:
        return None

    if average_invested_capital <= 0:
        return None

    return (
        nopat
        / average_invested_capital
    )


# ---------------------------------------------------------
# Profitability margins
# ---------------------------------------------------------


def calculate_gross_margin(
    row: pd.Series,
) -> float | None:

    gross_profit = safe_float(
        row.get("gross_profit_fy0")
    )

    revenue = safe_float(
        row.get("revenue_fy0")
    )

    return safe_divide(
        gross_profit,
        revenue,
    )


def calculate_operating_margin(
    row: pd.Series,
) -> float | None:

    operating_income = safe_float(
        row.get(
            "operating_income_fy0"
        )
    )

    revenue = safe_float(
        row.get("revenue_fy0")
    )

    return safe_divide(
        operating_income,
        revenue,
    )


def calculate_fcf_margin(
    row: pd.Series,
) -> float | None:
    """
    Normalised FCF margin:

    Normalised FCF / latest revenue
    """

    normalised_fcf = safe_float(
        row.get("normalised_fcf")
    )

    revenue = safe_float(
        row.get("revenue_fy0")
    )

    return safe_divide(
        normalised_fcf,
        revenue,
    )


# ---------------------------------------------------------
# Cash conversion
# ---------------------------------------------------------


def calculate_fcf_to_ebitda(
    row: pd.Series,
) -> float | None:
    """
    Measures how much reported EBITDA ultimately
    becomes free cash flow.

    This is only a screening measure, not a full
    accounting analysis.
    """

    normalised_fcf = safe_float(
        row.get("normalised_fcf")
    )

    ebitda = safe_float(
        row.get("ebitda_fy0")
    )

    if normalised_fcf is None:
        return None

    if ebitda is None:
        return None

    if ebitda <= 0:
        return None

    return (
        normalised_fcf
        / ebitda
    )


# ---------------------------------------------------------
# Current ratio
# ---------------------------------------------------------


def calculate_current_ratio(
    row: pd.Series,
) -> float | None:

    current_assets = safe_float(
        row.get(
            "current_assets_fy0"
        )
    )

    current_liabilities = safe_float(
        row.get(
            "current_liabilities_fy0"
        )
    )

    return safe_divide(
        current_assets,
        current_liabilities,
    )


# ---------------------------------------------------------
# Quality scoring
# ---------------------------------------------------------


def score_roic(
    roic: float | None,
) -> int:
    """
    Maximum: 40 points.
    """

    if roic is None:
        return 0

    if roic >= 0.25:
        return 40

    if roic >= 0.20:
        return 35

    if roic >= 0.15:
        return 30

    if roic >= 0.10:
        return 25

    if roic >= 0.05:
        return 15

    if roic > 0:
        return 5

    return 0


def score_operating_margin(
    margin: float | None,
) -> int:
    """
    Maximum: 20 points.

    This is deliberately broad because margins differ
    significantly between industries.
    """

    if margin is None:
        return 0

    if margin >= 0.20:
        return 20

    if margin >= 0.15:
        return 17

    if margin >= 0.10:
        return 14

    if margin >= 0.05:
        return 10

    if margin > 0:
        return 5

    return 0


def score_fcf_conversion(
    conversion: float | None,
) -> int:
    """
    Maximum: 20 points.
    """

    if conversion is None:
        return 0

    if conversion >= 0.80:
        return 20

    if conversion >= 0.60:
        return 17

    if conversion >= 0.40:
        return 13

    if conversion >= 0.20:
        return 8

    if conversion > 0:
        return 4

    return 0


def score_liquidity(
    current_ratio: float | None,
) -> int:
    """
    Maximum: 20 points.

    Extremely high current ratios are not awarded
    extra points indefinitely because idle capital
    can also reduce returns.
    """

    if current_ratio is None:
        return 0

    if 1.5 <= current_ratio <= 3:
        return 20

    if 1.2 <= current_ratio < 1.5:
        return 15

    if 1.0 <= current_ratio < 1.2:
        return 10

    if current_ratio > 3:
        return 15

    if current_ratio > 0:
        return 5

    return 0


# ---------------------------------------------------------
# Company quality calculations
# ---------------------------------------------------------


def calculate_quality_metrics(
    row: pd.Series,
) -> dict:

    tax_rate = (
        calculate_normalised_tax_rate(
            row
        )
    )

    nopat = calculate_nopat(
        row,
        tax_rate,
    )

    invested_capital = (
        calculate_invested_capital(
            row,
            0,
        )
    )

    average_invested_capital = (
        calculate_average_invested_capital(
            row
        )
    )

    roic = calculate_roic(
        nopat,
        average_invested_capital,
    )

    gross_margin = (
        calculate_gross_margin(
            row
        )
    )

    operating_margin = (
        calculate_operating_margin(
            row
        )
    )

    fcf_margin = (
        calculate_fcf_margin(
            row
        )
    )

    fcf_to_ebitda = (
        calculate_fcf_to_ebitda(
            row
        )
    )

    current_ratio = (
        calculate_current_ratio(
            row
        )
    )

    quality_score = (
        score_roic(
            roic
        )
        + score_operating_margin(
            operating_margin
        )
        + score_fcf_conversion(
            fcf_to_ebitda
        )
        + score_liquidity(
            current_ratio
        )
    )

    return {
        "normalised_tax_rate": tax_rate,

        "nopat": nopat,

        "invested_capital": (
            invested_capital
        ),

        "average_invested_capital": (
            average_invested_capital
        ),

        "roic": roic,

        "gross_margin": (
            gross_margin
        ),

        "operating_margin": (
            operating_margin
        ),

        "normalised_fcf_margin": (
            fcf_margin
        ),

        "fcf_to_ebitda": (
            fcf_to_ebitda
        ),

        "current_ratio": (
            current_ratio
        ),

        "quality_score": (
            quality_score
        ),
    }


# ---------------------------------------------------------
# Dataset processing
# ---------------------------------------------------------


def load_calculated_metrics() -> pd.DataFrame:

    if not CALCULATED_METRICS_FILE.exists():

        raise FileNotFoundError(
            "\nCalculated metrics file does "
            "not exist:\n"
            f"{CALCULATED_METRICS_FILE}\n\n"
            "Run:\n"
            "python -m src.yahoo_data\n"
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


def calculate_all_quality_metrics(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:

    results = []

    total = len(dataframe)

    print()
    print(
        "Calculating quality metrics..."
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

        quality = (
            calculate_quality_metrics(
                row
            )
        )

        combined = row.to_dict()

        combined.update(
            quality
        )

        results.append(
            combined
        )

    return pd.DataFrame(
        results
    )


def save_quality_metrics(
    dataframe: pd.DataFrame,
) -> None:

    PROCESSED_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        QUALITY_METRICS_FILE,
        index=False,
    )

    print()
    print(
        "Quality metrics saved to:"
    )

    print(
        QUALITY_METRICS_FILE
    )


# ---------------------------------------------------------
# Console output
# ---------------------------------------------------------


def print_quality_summary(
    dataframe: pd.DataFrame,
) -> None:

    print()
    print(
        "======================================="
    )

    print(
        "QUALITY ANALYSIS SUMMARY"
    )

    print(
        "======================================="
    )

    print(
        f"Companies analysed: "
        f"{len(dataframe)}"
    )

    valid_roic = dataframe[
        dataframe["roic"].notna()
    ]

    print(
        f"Companies with calculable ROIC: "
        f"{len(valid_roic)}"
    )

    if not valid_roic.empty:

        over_5 = valid_roic[
            valid_roic["roic"] >= 0.05
        ]

        over_10 = valid_roic[
            valid_roic["roic"] >= 0.10
        ]

        over_15 = valid_roic[
            valid_roic["roic"] >= 0.15
        ]

        print(
            f"ROIC >= 5%: {len(over_5)}"
        )

        print(
            f"ROIC >= 10%: {len(over_10)}"
        )

        print(
            f"ROIC >= 15%: {len(over_15)}"
        )


def print_high_quality_companies(
    dataframe: pd.DataFrame,
    number: int = 20,
) -> None:

    valid = dataframe[
        dataframe[
            "quality_score"
        ].notna()
    ].copy()

    if valid.empty:
        return

    valid = valid.sort_values(
        by=[
            "quality_score",
            "roic",
        ],
        ascending=[
            False,
            False,
        ],
    )

    display_columns = [
        column
        for column in [
            "symbol",
            "company_name",
            "quality_score",
            "roic",
            "operating_margin",
            "gross_margin",
            "normalised_fcf_margin",
            "fcf_to_ebitda",
            "current_ratio",
            "ev_normalised_fcf",
        ]
        if column in valid.columns
    ]

    print()
    print(
        "TOP QUALITY COMPANIES"
    )

    print(
        "---------------------------------------"
    )

    print(
        valid[
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

    dataframe = (
        load_calculated_metrics()
    )

    quality = (
        calculate_all_quality_metrics(
            dataframe
        )
    )

    save_quality_metrics(
        quality
    )

    print_quality_summary(
        quality
    )

    print_high_quality_companies(
        quality
    )


if __name__ == "__main__":
    main()