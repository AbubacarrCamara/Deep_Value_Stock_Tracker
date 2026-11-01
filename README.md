# Small\-Cap Deep Value Screener

A Python\-based research tool for finding potentially undervalued US small\-cap companies using free public market data\.

The screener is built around a simple investment question:

> **If I bought the whole business today, what am I paying for its sustainable cash generation, and what could make that apparent value misleading?**

The application downloads a candidate stock universe, collects company financial statements, calculates deep\-value and quality metrics, applies screening rules, and produces a shortlist for manual investment research\.

This is a **research tool**, not an automated investment recommendation system\.

---

## Current Features

The application currently supports:

- US stock universe discovery
- Small\-cap market\-cap filtering
- Positive unlevered free cash flow screening
- Exclusion of Financial Services and Real Estate
- Historical revenue, operating cash flow and capital expenditure collection
- Historical free cash flow calculation
- Five\-year normalised free cash flow
- Enterprise value calculation
- EV / normalised FCF
- Normalised FCF yield
- Three\-year revenue CAGR
- Net debt and Net Debt / EBITDA
- Historical share\-count analysis
- Dilution / buyback measurement
- FCF consistency analysis
- ROIC and NOPAT calculation
- Gross margin and operating margin
- FCF margin and FCF / EBITDA conversion
- Current ratio
- Deep Value Core filtering
- Priority candidate filtering
- Quantitative research scoring
- Quality scoring
- CSV outputs for further analysis

---

## Investment Philosophy

The screener is designed around a deep\-value small\-cap approach\.

The goal is not simply to find stocks with low valuation multiples\. The goal is to find businesses where:

```text
Sustainable cash generation
        +
Balance-sheet strength
        +
Reasonable business quality
        +
Shareholder-friendly capital allocation
        >
Current market valuation
```

The screener should be treated as an **idea\-generation system**\. A stock passing the screen does not mean it should be purchased\.

Every candidate should still go through a manual research process that asks:

1. Why is the company cheap?
2. Is current free cash flow sustainable?
3. Is the industry structurally declining?
4. Is management aligned with shareholders?
5. Is the company diluting shareholders?
6. Could debt permanently impair the business?
7. What is the strongest argument against owning the company?
8. What evidence would invalidate the investment thesis?

---

## Project Structure

```text
small-cap-screener/
│
├── data/
│   ├── raw/
│   │   └── yahoo_universe.csv
│   │
│   ├── processed/
│   │   ├── yahoo_fundamentals.csv
│   │   ├── yahoo_fundamentals_errors.csv
│   │   ├── calculated_metrics.csv
│   │   └── quality_metrics.csv
│   │
│   └── results/
│       ├── deep_value_core.csv
│       └── deep_value_priority.csv
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── universe.py
│   ├── yahoo_data.py
│   ├── calculations.py
│   ├── filters.py
│   └── quality.py
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Application Pipeline

```text
US Equity Universe
        │
        ▼
src/universe.py
        │
        ▼
data/raw/yahoo_universe.csv
        │
        ▼
src/yahoo_data.py
        │
        ▼
data/processed/yahoo_fundamentals.csv
        │
        ▼
src/calculations.py
        │
        ▼
data/processed/calculated_metrics.csv
        │
        ├──────────────► src/filters.py
        │                      │
        │                      ▼
        │             data/results/
        │
        ▼
src/quality.py
        │
        ▼
data/processed/quality_metrics.csv
```

A future `ranking.py` stage will combine the Deep Value and Quality outputs into a final research\-priority shortlist\.

---

## Installation

### 1\. Move into the project directory

```bash
cd small-cap-screener
```

### 2\. Create a virtual environment

#### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3\. Install dependencies

```bash
python -m pip install -r requirements.txt
```

Current requirements:

```text
yfinance==1.7.0
pandas>=2.2,<3.0
```

---

## Configuration

Most screening rules are stored in:

```text
src/config.py
```

This keeps investment criteria separate from program logic\.

Example:

```python
MIN_MARKET_CAP = 50_000_000
MAX_MARKET_CAP = 2_500_000_000
```

This currently restricts the first\-pass universe to companies with a market capitalisation between **$50 million and $2\.5 billion**\.

---

## Step 1 — Build the Stock Universe

Run:

```bash
python -m src.universe
```

This searches for US equities that broadly satisfy:

```text
Region:
United States

Market cap:
$50m – $2.5bn

LTM unlevered free cash flow:
Positive

Excluded sectors:
Financial Services
Real Estate
```

Output:

```text
data/raw/yahoo_universe.csv
```

This is intentionally a broad first\-pass universe\. No company should be considered investable at this stage\.

---

## Step 2 — Download Company Fundamentals

Run:

```bash
python -m src.yahoo_data
```

This reads `data/raw/yahoo_universe.csv` and retrieves historical financial statements for each company\.

The collector currently attempts to obtain:

### Income Statement

- Revenue
- EBIT
- EBITDA
- Pretax income
- Tax provision
- Gross profit
- Operating income

### Balance Sheet

- Cash
- Total debt
- Shareholders’ equity
- Total assets
- Current assets
- Current liabilities
- Shares outstanding

### Cash Flow Statement

- Operating cash flow
- Capital expenditure

Output:

```text
data/processed/yahoo_fundamentals.csv
```

Failed downloads are recorded separately:

```text
data/processed/yahoo_fundamentals_errors.csv
```

### Testing on a Small Number of Companies

During development, change:

```python
MAX_COMPANIES_TO_FETCH = None
```

to something such as:

```python
MAX_COMPANIES_TO_FETCH = 10
```

inside `src/config.py`\.

Return the value to `None` when ready to process all candidates\.

---

## Step 3 — Calculate Deep Value Metrics

Run:

```bash
python -m src.calculations
```

Output:

```text
data/processed/calculated_metrics.csv
```

### Free Cash Flow

```text
FCF = Operating Cash Flow - Capital Expenditure
```

Yahoo commonly reports capital expenditure as a negative cash\-flow value, so the program handles the sign accordingly\.

### Normalised Free Cash Flow

The system uses the median of the available historical FCF observations as the first version of normalised FCF\.

Example:

```text
FY0    $43m
FY1    $17m
FY2    $14m
FY3    $18m
FY4    $16m
```

Normalised FCF:

```text
$17m
```

This reduces the chance that one unusually strong year makes a company appear artificially cheap\.

### Enterprise Value

The current simplified calculation is:

```text
Enterprise Value =
Market Capitalisation
+ Total Debt
- Cash
```

More advanced versions may later account for preferred equity, minority interests, pension liabilities, lease liabilities and other non\-operating items\.

### EV / Normalised FCF

```text
EV / Normalised FCF =
Enterprise Value / Normalised Free Cash Flow
```

The principal search range is:

```text
0x – 8x
```

The preferred hunting ground is:

```text
0x – 5x
```

A very low multiple should not automatically be viewed positively\. It should increase the need to determine **why the company is cheap**\.

### Normalised FCF Yield

```text
FCF Yield =
Normalised FCF / Enterprise Value
```

|EV / FCF|Approx. FCF Yield|
|-------:|----------------:|
|2x      |50.0%            |
|3x      |33.3%            |
|4x      |25.0%            |
|5x      |20.0%            |
|6x      |16.7%            |
|8x      |12.5%            |
|10x     |10.0%            |

### FCF Consistency

The application records:

```text
fcf_years_available
positive_fcf_years
negative_fcf_years
fcf_positive_ratio
average_fcf
median_fcf
normalised_fcf
minimum_fcf
maximum_fcf
```

The Deep Value Core screen currently requires at least **3 positive FCF years**\.

### Revenue CAGR

The system calculates approximately FY3 → FY0 revenue CAGR:

```text
Revenue CAGR =
(Latest Revenue / Revenue 3 Years Earlier)^(1/3) - 1
```

The Deep Value Core screen currently allows:

```text
Revenue CAGR >= -5%
```

### Net Debt

```text
Net Debt = Total Debt - Cash
```

A negative result means the business has net cash\.

### Net Debt / EBITDA

The current maximum is:

```text
2.5x
```

Negative values are allowed because they normally indicate a net\-cash balance sheet\.

### Share Dilution

The program compares the newest available share\-count figure with the oldest available figure\.

Positive values represent dilution\. Negative values generally represent net share repurchases\.

The application currently flags dilution above **20%** as a warning\.

---

## Step 4 — Apply the Deep Value Core Screen

Run:

```bash
python -m src.filters
```

This reads `data/processed/calculated_metrics.csv` and applies the Deep Value Core rules\.

|Metric             |Requirement  |
|-------------------|------------:|
|Market Cap         |$50m – $2.5bn|
|EV / Normalised FCF|>0x and <=8x |
|Priority EV / FCF  |<=5x         |
|Positive FCF Years |>=3          |
|Net Debt / EBITDA  |<=2.5x       |
|Revenue CAGR       |>=-5%        |

Output files:

```text
data/results/deep_value_core.csv
data/results/deep_value_priority.csv
```

`deep_value_priority.csv` contains the subset with EV / normalised FCF <= 5x\.

---

## Quantitative Screening Score

Candidates receive an initial research\-priority score out of 100\.

|Category       |Maximum|
|---------------|------:|
|Valuation      |40     |
|FCF Consistency|20     |
|Balance Sheet  |20     |
|Revenue Trend  |10     |
|Dilution       |10     |
|**Total**      |**100**|

The score determines **which companies deserve research first**\. It is not a buy signal\.

---

## Step 5 — Calculate Quality Metrics

Run:

```bash
python -m src.quality
```

Output:

```text
data/processed/quality_metrics.csv
```

The quality layer currently calculates:

- Effective tax rate
- Normalised tax rate
- NOPAT
- Invested capital
- Average invested capital
- ROIC
- Gross margin
- Operating margin
- Normalised FCF margin
- FCF / EBITDA
- Current ratio
- Quality score

### ROIC

Current screening calculation:

```text
NOPAT =
EBIT × (1 - Normalised Tax Rate)
```

```text
Invested Capital =
Total Debt
+ Shareholders' Equity
- Cash
```

```text
Average Invested Capital =
(FY0 Invested Capital + FY1 Invested Capital) / 2
```

```text
ROIC =
NOPAT / Average Invested Capital
```

This is a screening metric\. Detailed company research may require adjustments for acquisitions, goodwill, leases, pensions, minority interests, excess cash, restructuring charges and unusual tax items\.

---

## Quality Score

The current quality score is out of 100\.

|Category        |Maximum|
|----------------|------:|
|ROIC            |40     |
|Operating Margin|20     |
|FCF Conversion  |20     |
|Liquidity       |20     |
|**Total**       |**100**|

This is separate from the Deep Value screening score\.

---

## Recommended Run Order

For a complete fresh run:

```bash
python -m src.universe
python -m src.yahoo_data
python -m src.calculations
python -m src.filters
python -m src.quality
```

---

## Research Workflow

```text
Automated Screen
      ↓
Priority Candidates
      ↓
15-Minute Rejection Test
      ↓
Normalise Financials Manually
      ↓
Read Annual Reports
      ↓
Understand Why It Is Cheap
      ↓
Investigate Management
      ↓
Investigate Dilution
      ↓
Investigate Debt
      ↓
Build Bear / Base / Bull Valuation
      ↓
Write Investment Thesis
      ↓
Watchlist or Reject
```

Most companies should be rejected\. The purpose of the application is to make the research universe smaller and more interesting\.

---

## The 15\-Minute Rejection Test

Before spending hours researching a company, ask:

### Business

- What does the company actually do?
- Who pays it?
- Why do customers continue paying?
- Is the industry structurally growing, stable or declining?

### Valuation

- Why is EV / FCF so low?
- Is FCF temporarily elevated?
- Has capital expenditure been unusually low?
- Has working capital temporarily boosted cash flow?

### Balance Sheet

- How much debt exists?
- When does the debt mature?
- Is the company dependent on refinancing?

### Revenue

- Is revenue stable?
- Is volume falling?
- Is growth being created purely through price increases or acquisitions?

### Shareholders

- Is the share count rising?
- Are options or stock compensation significant?
- Has the company repeatedly raised equity?

### Management

- Does management own meaningful shares?
- Has management bought stock with personal money?
- Has management historically allocated capital intelligently?

If a serious flaw appears during this stage, the candidate can be rejected before deeper analysis\.

---

## Melting Ice Cube Risk

A low valuation multiple does not necessarily represent value\.

A company may appear cheap because its underlying economics are deteriorating due to:

- Structural demand decline
- Technological disruption
- Customer losses
- Regulatory change
- Margin compression
- Permanent volume decline
- Industry substitution

The central question is:

> **If nothing changes over the next five years, is this business likely to be worth more or less than it is today?**

A business trading at 3x FCF can still be expensive if that FCF is disappearing rapidly\.

---

## Data Sources and Limitations

The current application uses Yahoo Finance data through the `yfinance` Python package\.

This is useful for screening, idea generation, historical financial collection, market data and initial valuation work\.

It should not be treated as the final authoritative source for investment decisions\.

Any company that survives the screen should eventually have key financial figures checked against primary filings\.

For US\-listed companies, this means documents such as:

```text
10-K
10-Q
8-K
S-3
DEF 14A
Form 4
```

Future versions of the application are intended to integrate directly with SEC EDGAR\.

---

## Missing Data

Not every company reports every financial statement line in the same way\.

The application deliberately treats unavailable financial values as missing rather than inventing data\.

This can result in some companies being excluded because metrics such as EBITDA, revenue history, current assets, current liabilities, tax provision or invested capital cannot be calculated reliably\.

This behaviour is intentional\. It is better to lose a candidate than create false precision\.

---

## Financial Companies

Financial Services companies are excluded from the Deep Value Core screen\.

Traditional metrics such as EV / FCF and Net Debt / EBITDA are generally unsuitable for banks and many other financial businesses\.

Banks will eventually require a separate model based on measures such as:

- Price / Tangible Book Value
- ROTCE
- ROE
- CET1 capital
- Net interest margin
- Deposit growth
- Deposit costs
- Non\-performing loans
- Credit losses
- Tangible book value per share

---

## REITs

Real Estate companies and REITs are also excluded from the current core screen\.

For REITs, metrics such as FFO, AFFO, NAV, Debt / EBITDA, occupancy and rental growth are usually more useful than conventional industrial\-company FCF analysis\.

---

## Planned Development

### Next — `ranking.py`

The next major section will combine:

```text
Deep Value Score
        +
Quality Score
        ↓
Final Research Priority
```

The purpose is to prevent a company such as:

```text
EV/FCF = 2.8x
ROIC = 2%
High leverage
Revenue declining
```

from automatically ranking ahead of:

```text
EV/FCF = 4.6x
ROIC = 16%
Net cash
5/5 positive FCF years
Stable revenue
No dilution
```

### Future Features

Potential future development includes:

- Final combined ranking
- Excel export
- Automated research queue
- SEC EDGAR integration
- 10\-K retrieval
- 10\-Q retrieval
- S\-3 dilution detection
- Form 4 insider transaction analysis
- Debt maturity extraction
- Customer concentration detection
- Management ownership
- Stock\-based compensation analysis
- Historical buyback analysis
- Bear / base / bull valuation models
- Automated thesis template
- Watchlist tracking
- UK equity support
- Dedicated bank screener
- Dedicated brokerage screener
- Dedicated REIT screener
- Streamlit interface

---

## Development Principle

The project should remain understandable\.

Avoid adding complexity that does not improve the investment process\.

The application does not need to become Bloomberg\. Its purpose is narrower:

> **Find small businesses whose market valuation appears unusually low relative to sustainable cash generation and financial strength, then provide enough information to decide which businesses deserve deeper research.**

---

## Disclaimer

This project is for personal research and educational purposes\.

The output of the application is not financial advice and should not be treated as a recommendation to buy or sell securities\.

Financial data may be missing, delayed, incorrect or interpreted differently between providers\.

Always verify important figures against primary company filings before making an investment decision\.