from __future__ import annotations

import pandas as pd
import yfinance as yf
from yfinance import EquityQuery

from .config import (
    ALLOWED_SECTORS,
    MAX_MARKET_CAP,
    MAX_PAGES,
    MIN_MARKET_CAP,
    MIN_UNLEVERED_FCF,
    PAGE_SIZE,
    RAW_DATA_DIR,
    REGION,
    YAHOO_UNIVERSE_FILE,
)


def build_universe_query() -> EquityQuery:
    """
    Build the Yahoo Finance query used to find potential
    Deep Value Core companies.

    Current requirements:

    - US equities
    - Market cap between $50m and $2.5bn
    - Positive LTM unlevered free cash flow
    - Exclude Financial Services
    - Exclude Real Estate
    """

    sector_query = EquityQuery(
        "or",
        [
            EquityQuery("eq", ["sector", sector])
            for sector in ALLOWED_SECTORS
        ],
    )

    query = EquityQuery(
        "and",
        [
            # US companies only
            EquityQuery(
                "eq",
                ["region", REGION],
            ),

            # Small-cap / lower-mid-cap range
            EquityQuery(
                "btwn",
                [
                    "intradaymarketcap",
                    MIN_MARKET_CAP,
                    MAX_MARKET_CAP,
                ],
            ),

            # Business must currently generate positive
            # unlevered free cash flow
            EquityQuery(
                "gt",
                [
                    "unleveredfreecashflow.lasttwelvemonths",
                    MIN_UNLEVERED_FCF,
                ],
            ),

            # Remove Financial Services and Real Estate
            sector_query,
        ],
    )

    return query


def fetch_universe() -> pd.DataFrame:
    """
    Download all companies matching our initial screen.

    Yahoo limits custom screen responses to 250 companies,
    so this function paginates through the results.
    """

    query = build_universe_query()

    all_quotes: list[dict] = []

    offset = 0

    print("Starting Deep Value Core universe download...")
    print()
    print(f"Region: {REGION.upper()}")
    print(
        f"Market cap: "
        f"${MIN_MARKET_CAP:,.0f} - "
        f"${MAX_MARKET_CAP:,.0f}"
    )
    print("Unlevered FCF: positive")
    print("Financial Services: excluded")
    print("Real Estate: excluded")
    print()

    for page_number in range(1, MAX_PAGES + 1):

        print(
            f"Downloading page {page_number} "
            f"(offset {offset})..."
        )

        response = yf.screen(
            query,
            offset=offset,
            size=PAGE_SIZE,
            sortField="intradaymarketcap",
            sortAsc=True,
        )

        quotes = response.get("quotes", [])

        if not quotes:
            print("No more results returned.")
            break

        all_quotes.extend(quotes)

        print(
            f"Received {len(quotes)} companies."
        )

        total_results = response.get("total")

        if total_results is not None:
            print(
                f"Yahoo reports approximately "
                f"{total_results} total results."
            )

        # Fewer than PAGE_SIZE means we reached
        # the final page.
        if len(quotes) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

        if total_results is not None:
            try:
                if offset >= int(total_results):
                    break
            except (TypeError, ValueError):
                pass

    if not all_quotes:
        print()
        print("No companies were returned.")
        return pd.DataFrame()

    dataframe = pd.json_normalize(all_quotes)

    # Remove duplicate companies if Yahoo returns
    # overlapping pages.
    if "symbol" in dataframe.columns:
        dataframe = dataframe.drop_duplicates(
            subset=["symbol"]
        )

    # Move the most useful columns to the front.
    preferred_columns = [
        "symbol",
        "shortName",
        "longName",
        "exchange",
        "fullExchangeName",
        "sector",
        "industry",
        "marketCap",
        "intradaymarketcap",
        "regularMarketPrice",
        "currency",
    ]

    existing_preferred_columns = [
        column
        for column in preferred_columns
        if column in dataframe.columns
    ]

    remaining_columns = [
        column
        for column in dataframe.columns
        if column not in existing_preferred_columns
    ]

    dataframe = dataframe[
        existing_preferred_columns
        + remaining_columns
    ]

    # Sort smallest companies first if market cap
    # information is available.
    if "marketCap" in dataframe.columns:
        dataframe = dataframe.sort_values(
            by="marketCap",
            ascending=True,
        )

    elif "intradaymarketcap" in dataframe.columns:
        dataframe = dataframe.sort_values(
            by="intradaymarketcap",
            ascending=True,
        )

    dataframe = dataframe.reset_index(drop=True)

    return dataframe


def save_universe(dataframe: pd.DataFrame) -> None:
    """
    Save the raw Yahoo candidate universe as a CSV.
    """

    RAW_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        YAHOO_UNIVERSE_FILE,
        index=False,
    )

    print()
    print(
        f"Saved {len(dataframe)} companies to:"
    )
    print(YAHOO_UNIVERSE_FILE)


def main() -> None:
    universe = fetch_universe()

    if universe.empty:
        print(
            "Universe download returned no usable data."
        )
        return

    save_universe(universe)

    print()
    print("Universe creation complete.")

    if "symbol" in universe.columns:
        print()
        print("First 10 tickers:")

        print(
            universe["symbol"]
            .head(10)
            .to_string(index=False)
        )


if __name__ == "__main__":
    main()