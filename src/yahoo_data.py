from __future__ import annotations

import math
import re
import time
from typing import Iterable

import pandas as pd
import yfinance as yf

from .config import (
    CHECKPOINT_EVERY,
    HISTORY_YEARS,
    MAX_COMPANIES_TO_FETCH,
    MAX_RETRIES,
    PROCESSED_DATA_DIR,
    REQUEST_DELAY_SECONDS,
    YAHOO_FUNDAMENTALS_ERRORS_FILE,
    YAHOO_FUNDAMENTALS_FILE,
    YAHOO_UNIVERSE_FILE,
)


# ---------------------------------------------------------
# Row aliases
#
# Yahoo can use slightly different row names between
# companies. We therefore search several possible names.
# ---------------------------------------------------------

REVENUE_ALIASES = [
    "Total Revenue",
    "Operating Revenue",
]

EBIT_ALIASES = [
    "EBIT",
    "Operating Income",
]

EBITDA_ALIASES = [
    "EBITDA",
    "Normalized EBITDA",
]

OPERATING_CASH_FLOW_ALIASES = [
    "Operating Cash Flow",
    "Cash Flow From Continuing Operating Activities",
]

CAPEX_ALIASES = [
    "Capital Expenditure",
    "Capital Expenditures",
]

CASH_ALIASES = [
    "Cash Cash Equivalents And Short Term Investments",
    "Cash And Cash Equivalents",
    "Cash Financial",
]

TOTAL_DEBT_ALIASES = [
    "Total Debt",
]

STOCKHOLDERS_EQUITY_ALIASES = [
    "Stockholders Equity",
    "Common Stock Equity",
    "Total Equity Gross Minority Interest",
]

SHARES_OUTSTANDING_ALIASES = [
    "Ordinary Shares Number",
    "Share Issued",
]


# ---------------------------------------------------------
# Additional aliases for quality / ROIC calculations
# ---------------------------------------------------------

PRETAX_INCOME_ALIASES = [
    "Pretax Income",
    "Pre Tax Income",
    "Income Before Tax",
]

TAX_PROVISION_ALIASES = [
    "Tax Provision",
    "Income Tax Expense",
]

GROSS_PROFIT_ALIASES = [
    "Gross Profit",
]

OPERATING_INCOME_ALIASES = [
    "Operating Income",
]

TOTAL_ASSETS_ALIASES = [
    "Total Assets",
]

CURRENT_ASSETS_ALIASES = [
    "Current Assets",
    "Total Current Assets",
]

CURRENT_LIABILITIES_ALIASES = [
    "Current Liabilities",
    "Total Current Liabilities",
]


# ---------------------------------------------------------
# General helpers
# ---------------------------------------------------------


def normalise_label(value: str) -> str:
    """
    Normalise statement row names so:

    'Operating Cash Flow'
    'OperatingCashFlow'
    'operating_cash_flow'

    all become comparable.
    """

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).lower(),
    )


def safe_number(value) -> float | None:
    """
    Convert a value to float.

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


def clean_statement(
    statement: pd.DataFrame | None,
) -> pd.DataFrame:
    """
    Return a cleaned financial statement.

    Yahoo normally returns:
    rows    = financial metrics
    columns = fiscal dates

    Columns are sorted newest first.
    """

    if statement is None:
        return pd.DataFrame()

    if statement.empty:
        return pd.DataFrame()

    statement = statement.copy()

    try:
        statement.columns = pd.to_datetime(
            statement.columns,
            errors="coerce",
        )

        valid_columns = [
            column
            for column in statement.columns
            if not pd.isna(column)
        ]

        statement = statement[valid_columns]

        statement = statement.reindex(
            sorted(
                statement.columns,
                reverse=True,
            ),
            axis=1,
        )

    except Exception:
        # If Yahoo changes its date format,
        # leave the column order untouched rather than
        # failing the entire ticker.
        pass

    return statement


def find_statement_row(
    statement: pd.DataFrame,
    aliases: Iterable[str],
) -> pd.Series | None:
    """
    Find a row within a Yahoo statement using a list
    of possible row names.
    """

    if statement.empty:
        return None

    normalised_index = {
        normalise_label(index): index
        for index in statement.index
    }

    for alias in aliases:
        normalised_alias = normalise_label(alias)

        if normalised_alias in normalised_index:
            actual_index = normalised_index[
                normalised_alias
            ]

            return statement.loc[actual_index]

    return None


def row_values(
    statement: pd.DataFrame,
    aliases: Iterable[str],
    limit: int = HISTORY_YEARS,
) -> list[tuple[str | None, float | None]]:
    """
    Return up to N historical values for a financial
    statement row.

    Example:

    [
        ("2025-12-31", 150000000),
        ("2024-12-31", 142000000),
        ...
    ]
    """

    row = find_statement_row(
        statement,
        aliases,
    )

    if row is None:
        return []

    values = []

    for date, value in row.items():
        parsed_value = safe_number(value)

        try:
            date_string = pd.Timestamp(
                date
            ).strftime("%Y-%m-%d")
        except Exception:
            date_string = str(date)

        values.append(
            (
                date_string,
                parsed_value,
            )
        )

        if len(values) >= limit:
            break

    return values


def latest_value(
    statement: pd.DataFrame,
    aliases: Iterable[str],
) -> float | None:
    """
    Return the newest available value for a row.
    """

    values = row_values(
        statement,
        aliases,
        limit=1,
    )

    if not values:
        return None

    return values[0][1]


def calculate_fcf(
    operating_cash_flow: float | None,
    capex: float | None,
) -> float | None:
    """
    Calculate free cash flow.

    Yahoo normally reports capital expenditure as a
    negative cash-flow number.

    Example:

    OCF   = 100
    Capex = -20

    FCF = 100 + (-20) = 80

    If Yahoo supplies CapEx as a positive number,
    subtract it instead.
    """

    if operating_cash_flow is None:
        return None

    if capex is None:
        return None

    if capex < 0:
        return operating_cash_flow + capex

    return operating_cash_flow - capex


def get_market_cap(
    universe_row: pd.Series,
) -> float | None:
    """
    Try both market-cap fields that may be returned
    by Yahoo's screener.
    """

    for column in [
        "marketCap",
        "intradaymarketcap",
    ]:
        if column in universe_row.index:
            value = safe_number(
                universe_row[column]
            )

            if value is not None:
                return value

    return None


# ---------------------------------------------------------
# Statement processing
# ---------------------------------------------------------


def add_history_columns(
    output: dict,
    prefix: str,
    values: list[tuple[str | None, float | None]],
) -> None:
    """
    Turn historical values into columns such as:

    revenue_fy0
    revenue_fy0_date
    revenue_fy1
    revenue_fy1_date
    """

    for year_index in range(HISTORY_YEARS):
        value_column = f"{prefix}_fy{year_index}"
        date_column = f"{prefix}_fy{year_index}_date"

        if year_index < len(values):
            date, value = values[year_index]

            output[value_column] = value
            output[date_column] = date

        else:
            output[value_column] = None
            output[date_column] = None


def collect_company_fundamentals(
    universe_row: pd.Series,
) -> dict:
    """
    Download and standardise the financial statements
    for one company.
    """

    symbol = str(
        universe_row["symbol"]
    ).strip()

    ticker = yf.Ticker(symbol)

    income_statement = clean_statement(
        ticker.get_income_stmt(
            freq="yearly",
            pretty=False,
        )
    )

    balance_sheet = clean_statement(
        ticker.get_balance_sheet(
            freq="yearly",
            pretty=False,
        )
    )

    cash_flow = clean_statement(
        ticker.get_cash_flow(
            freq="yearly",
            pretty=False,
        )
    )

    output = {
        "symbol": symbol,
        "company_name": universe_row.get(
            "longName",
            universe_row.get(
                "shortName",
                None,
            ),
        ),
        "sector": universe_row.get(
            "sector",
            None,
        ),
        "industry": universe_row.get(
            "industry",
            None,
        ),
        "exchange": universe_row.get(
            "fullExchangeName",
            universe_row.get(
                "exchange",
                None,
            ),
        ),
        "currency": universe_row.get(
            "currency",
            None,
        ),
        "market_cap": get_market_cap(
            universe_row
        ),
    }

    # -----------------------------------------------------
    # Income statement
    # -----------------------------------------------------

    revenue_history = row_values(
        income_statement,
        REVENUE_ALIASES,
    )

    ebit_history = row_values(
        income_statement,
        EBIT_ALIASES,
    )

    ebitda_history = row_values(
        income_statement,
        EBITDA_ALIASES,
    )

    pretax_income_history = row_values(
    income_statement,
    PRETAX_INCOME_ALIASES,
    )

    tax_provision_history = row_values(
        income_statement,
        TAX_PROVISION_ALIASES,
    )

    gross_profit_history = row_values(
        income_statement,
        GROSS_PROFIT_ALIASES,
    )

    operating_income_history = row_values(
        income_statement,
        OPERATING_INCOME_ALIASES,
    )

    add_history_columns(
        output,
        "revenue",
        revenue_history,
    )

    add_history_columns(
        output,
        "ebit",
        ebit_history,
    )

    add_history_columns(
        output,
        "ebitda",
        ebitda_history,
    )

    add_history_columns(
    output,
    "pretax_income",
    pretax_income_history,
    )

    add_history_columns(
        output,
        "tax_provision",
        tax_provision_history,
    )

    add_history_columns(
        output,
        "gross_profit",
        gross_profit_history,
    )

    add_history_columns(
        output,
        "operating_income",
        operating_income_history,
    )

    # -----------------------------------------------------
    # Cash-flow statement
    # -----------------------------------------------------

    ocf_history = row_values(
        cash_flow,
        OPERATING_CASH_FLOW_ALIASES,
    )

    capex_history = row_values(
        cash_flow,
        CAPEX_ALIASES,
    )

    add_history_columns(
        output,
        "operating_cash_flow",
        ocf_history,
    )

    add_history_columns(
        output,
        "capex",
        capex_history,
    )

    # -----------------------------------------------------
    # Calculate annual FCF
    # -----------------------------------------------------

    for year_index in range(HISTORY_YEARS):

        ocf = output.get(
            f"operating_cash_flow_fy{year_index}"
        )

        capex = output.get(
            f"capex_fy{year_index}"
        )

        output[
            f"fcf_fy{year_index}"
        ] = calculate_fcf(
            ocf,
            capex,
        )

    # -----------------------------------------------------

    # Balance-sheet history

    # -----------------------------------------------------

    cash_history = row_values(

        balance_sheet,

        CASH_ALIASES,

    )

    debt_history = row_values(

        balance_sheet,

        TOTAL_DEBT_ALIASES,

    )

    equity_history = row_values(

        balance_sheet,

        STOCKHOLDERS_EQUITY_ALIASES,

    )

    total_assets_history = row_values(

        balance_sheet,

        TOTAL_ASSETS_ALIASES,

    )

    current_assets_history = row_values(

        balance_sheet,

        CURRENT_ASSETS_ALIASES,

    )

    current_liabilities_history = row_values(

        balance_sheet,

        CURRENT_LIABILITIES_ALIASES,

    )

    add_history_columns(

        output,

        "cash",

        cash_history,

    )

    add_history_columns(

        output,

        "total_debt",

        debt_history,

    )

    add_history_columns(

        output,

        "stockholders_equity",

        equity_history,

    )

    add_history_columns(

        output,

        "total_assets",

        total_assets_history,

    )

    add_history_columns(

        output,

        "current_assets",

        current_assets_history,

    )

    add_history_columns(

        output,

        "current_liabilities",

        current_liabilities_history,

    )

    output["cash"] = latest_value(
        balance_sheet,
        CASH_ALIASES,
    )

    output["total_debt"] = latest_value(
        balance_sheet,
        TOTAL_DEBT_ALIASES,
    )

    output["stockholders_equity"] = latest_value(
        balance_sheet,
        STOCKHOLDERS_EQUITY_ALIASES,
    )

    shares_history = row_values(
        balance_sheet,
        SHARES_OUTSTANDING_ALIASES,
    )

    add_history_columns(
        output,
        "shares_outstanding",
        shares_history,
    )

    # -----------------------------------------------------
    # Basic availability flags
    #
    # These make it easier later to see where Yahoo
    # returned incomplete data.
    # -----------------------------------------------------

    output["has_income_statement"] = (
        not income_statement.empty
    )

    output["has_balance_sheet"] = (
        not balance_sheet.empty
    )

    output["has_cash_flow"] = (
        not cash_flow.empty
    )

    return output


# ---------------------------------------------------------
# Download orchestration
# ---------------------------------------------------------


def load_universe() -> pd.DataFrame:
    """
    Load the candidate universe produced by universe.py.
    """

    if not YAHOO_UNIVERSE_FILE.exists():
        raise FileNotFoundError(
            f"Universe file does not exist:\n"
            f"{YAHOO_UNIVERSE_FILE}\n\n"
            f"Run:\n"
            f"python -m src.universe\n"
            f"first."
        )

    universe = pd.read_csv(
        YAHOO_UNIVERSE_FILE
    )

    if "symbol" not in universe.columns:
        raise ValueError(
            "The universe CSV does not contain "
            "a 'symbol' column."
        )

    universe = universe.drop_duplicates(
        subset=["symbol"]
    )

    universe = universe.reset_index(
        drop=True
    )

    if MAX_COMPANIES_TO_FETCH is not None:
        universe = universe.head(
            MAX_COMPANIES_TO_FETCH
        )

    return universe


def save_checkpoint(
    results: list[dict],
) -> None:
    """
    Save successful downloads during the run.
    """

    if not results:
        return

    PROCESSED_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe = pd.DataFrame(
        results
    )

    dataframe.to_csv(
        YAHOO_FUNDAMENTALS_FILE,
        index=False,
    )


def save_errors(
    errors: list[dict],
) -> None:
    """
    Save ticker download errors separately.
    """

    if not errors:
        return

    PROCESSED_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    pd.DataFrame(
        errors
    ).to_csv(
        YAHOO_FUNDAMENTALS_ERRORS_FILE,
        index=False,
    )


def download_fundamentals() -> pd.DataFrame:
    """
    Download financial statements for every ticker in
    the candidate universe.
    """

    universe = load_universe()

    total_companies = len(universe)

    print()
    print(
        "Starting Yahoo fundamentals download..."
    )
    print(
        f"Companies to process: "
        f"{total_companies}"
    )
    print()

    results: list[dict] = []
    errors: list[dict] = []

    for index, universe_row in universe.iterrows():

        symbol = universe_row["symbol"]

        print(
            f"[{index + 1}/{total_companies}] "
            f"{symbol}"
        )

        success = False

        for attempt in range(
            1,
            MAX_RETRIES + 1,
        ):

            try:
                company_data = (
                    collect_company_fundamentals(
                        universe_row
                    )
                )

                results.append(
                    company_data
                )

                success = True

                break

            except Exception as exc:

                print(
                    f"  Attempt {attempt}/"
                    f"{MAX_RETRIES} failed: "
                    f"{exc}"
                )

                if attempt < MAX_RETRIES:
                    time.sleep(
                        REQUEST_DELAY_SECONDS * 4
                    )

        if not success:

            errors.append(
                {
                    "symbol": symbol,
                    "error": (
                        "Failed after "
                        f"{MAX_RETRIES} attempts"
                    ),
                }
            )

            print(
                "  Skipping ticker."
            )

        # Save periodic checkpoint
        if (
            (index + 1)
            % CHECKPOINT_EVERY
            == 0
        ):
            save_checkpoint(
                results
            )

            save_errors(
                errors
            )

            print(
                "  Checkpoint saved."
            )

        time.sleep(
            REQUEST_DELAY_SECONDS
        )

    # Final save
    save_checkpoint(
        results
    )

    save_errors(
        errors
    )

    dataframe = pd.DataFrame(
        results
    )

    print()
    print(
        "Fundamentals download complete."
    )
    print(
        f"Successful: {len(results)}"
    )
    print(
        f"Failed: {len(errors)}"
    )
    print()

    print(
        f"Saved to:\n"
        f"{YAHOO_FUNDAMENTALS_FILE}"
    )

    if errors:
        print()
        print(
            f"Errors saved to:\n"
            f"{YAHOO_FUNDAMENTALS_ERRORS_FILE}"
        )

    return dataframe


def main() -> None:
    dataframe = download_fundamentals()

    if dataframe.empty:
        print(
            "No fundamentals were downloaded."
        )
        return

    preview_columns = [
        column
        for column in [
            "symbol",
            "company_name",
            "market_cap",
            "revenue_fy0",
            "operating_cash_flow_fy0",
            "capex_fy0",
            "fcf_fy0",
            "cash",
            "total_debt",
            "ebitda_fy0",
        ]
        if column in dataframe.columns
    ]

    print()
    print("Preview:")
    print()

    print(
        dataframe[
            preview_columns
        ]
        .head(10)
        .to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()
    