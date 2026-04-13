from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SourceEra:
    name: str
    start_date: date | None
    end_date: date | None
    url_pattern: str
    file_format: str
    schema_note: str


@dataclass(frozen=True)
class DataSource:
    name: str
    eras: tuple[SourceEra, ...]
    max_requests_per_minute: int
    max_retries: int
    checksum: str
    parquet_partition_template: str
    failover_url_patterns: tuple[str, ...] = ()


SOURCE_REGISTRY: dict[str, DataSource] = {
    "NSE_EQUITY_BHAVCOPY": DataSource(
        name="NSE Equity Bhavcopy",
        eras=(
            SourceEra(
                name="pre_2010",
                start_date=None,
                end_date=date(2009, 12, 31),
                url_pattern="https://www1.nseindia.com/content/historical/EQUITIES/{YYYY}/{MON}/cm{DDMONYYYY}bhav.csv.zip",
                file_format="csv_zip",
                schema_note="Legacy csv with era-specific columns; parser normalizes to canonical OHLCV schema.",
            ),
            SourceEra(
                name="2010_2019",
                start_date=date(2010, 1, 1),
                end_date=date(2019, 12, 31),
                url_pattern="https://www1.nseindia.com/content/historical/EQUITIES/{YYYY}/{MON}/cm{DDMONYYYY}bhav.csv.zip",
                file_format="csv_zip",
                schema_note="CSV with standard symbol and OHLC fields.",
            ),
            SourceEra(
                name="2019_present",
                start_date=date(2020, 1, 1),
                end_date=None,
                url_pattern="https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{YYYYMMDD}_F_0000.csv.zip",
                file_format="csv_zip",
                schema_note="NSE archive csv with revised column names and metadata suffix fields.",
            ),
        ),
        max_requests_per_minute=20,
        max_retries=5,
        checksum="sha256",
        parquet_partition_template="source=nse_equity/year={YYYY}/month={MM}/day={DD}",
        failover_url_patterns=(
            "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{YYYYMMDD}_F_0000.csv.zip",
            "https://www1.nseindia.com/content/historical/EQUITIES/{YYYY}/{MON}/cm{DDMONYYYY}bhav.csv.zip",
        ),
    ),
    "NSE_FO_BHAVCOPY": DataSource(
        name="NSE F&O Bhavcopy",
        eras=(
            SourceEra(
                name="all",
                start_date=None,
                end_date=None,
                url_pattern="https://nsearchives.nseindia.com/content/fo/NSE_FO_bhavcopy_{YYYYMMDD}.csv",
                file_format="csv",
                schema_note="NSE F&O daily bhavcopy for derivatives contracts.",
            ),
        ),
        max_requests_per_minute=15,
        max_retries=5,
        checksum="sha256",
        parquet_partition_template="source=nse_fo/year={YYYY}/month={MM}/day={DD}",
    ),
    "BSE_EQUITY_BHAVCOPY": DataSource(
        name="BSE Equity Bhavcopy",
        eras=(
            SourceEra(
                name="all",
                start_date=None,
                end_date=None,
                url_pattern="https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_{YYYYMMDD}_F_0000.CSV",
                file_format="csv",
                schema_note="BSE equity bhavcopy primary path is CSV; official failovers include CSV and ZIP variants with OHLCV and ISIN columns.",
            ),
        ),
        max_requests_per_minute=12,
        max_retries=5,
        checksum="sha256",
        parquet_partition_template="source=bse_equity/year={YYYY}/month={MM}/day={DD}",
        failover_url_patterns=(
            "https://www.bseindia.com/download/BhavCopy/Equity/EQ_ISINCODE_{DDMMYY}_T0.CSV",
            "https://www.bseindia.com/download/BhavCopy/Equity/BSE_EQ_BHAVCOPY_{DDMMYYYY}_T0.ZIP",
            "https://www.bseindia.com/download/BhavCopy/Equity/EQ{DDMMYY}_CSV.ZIP",
            "https://www.bseindia.com/download/BhavCopy/Equity/eq{DDMMYY}_csv.zip",
            "https://www.bseindia.com/download/BhavCopy/Equity/EQ_ISINCODE_{DDMMYY}.ZIP",
        ),
    ),
    "NSE_FII_DII": DataSource(
        name="NSE FII DII Activity",
        eras=(
            SourceEra(
                name="all",
                start_date=None,
                end_date=None,
                url_pattern="https://www.nseindia.com/api/fiidiiTradeReact",
                file_format="json",
                schema_note="JSON activity feed with buy and sell values by participant class.",
            ),
        ),
        max_requests_per_minute=10,
        max_retries=5,
        checksum="sha256",
        parquet_partition_template="source=nse_fii_dii/year={YYYY}/month={MM}",
        failover_url_patterns=(
            "https://www.nseindia.com/api/fiidiiTradeReact?type=all",
        ),
    ),
    "INDIA_VIX": DataSource(
        name="India VIX",
        eras=(
            SourceEra(
                name="all",
                start_date=None,
                end_date=None,
                url_pattern="https://www.nseindia.com/api/allIndices",
                file_format="json",
                schema_note="All indices payload containing India VIX snapshot.",
            ),
        ),
        max_requests_per_minute=10,
        max_retries=5,
        checksum="sha256",
        parquet_partition_template="source=india_vix/year={YYYY}/month={MM}/day={DD}",
        failover_url_patterns=(
            "https://www.nseindia.com/api/allIndices",
        ),
    ),
    "NSE_CORPORATE_ACTIONS": DataSource(
        name="NSE Corporate Actions",
        eras=(
            SourceEra(
                name="all",
                start_date=None,
                end_date=None,
                url_pattern="https://www.nseindia.com/api/corporates-corporateActions?index=equities",
                file_format="json",
                schema_note="NSE corporate action API payload.",
            ),
        ),
        max_requests_per_minute=8,
        max_retries=5,
        checksum="sha256",
        parquet_partition_template="source=nse_ca/year={YYYY}/month={MM}/day={DD}",
        failover_url_patterns=(
            "https://www.nseindia.com/api/corporates-corporateActions?index=equities",
            "https://www.nseindia.com/api/corporate-announcements?index=equities",
        ),
    ),
    "BSE_CORPORATE_ACTIONS": DataSource(
        name="BSE Corporate Actions",
        eras=(
            SourceEra(
                name="all",
                start_date=None,
                end_date=None,
                url_pattern="https://api.bseindia.com/BseIndiaAPI/api/Corpforthresults/w",
                file_format="json",
                schema_note="BSE corporate action endpoint.",
            ),
        ),
        max_requests_per_minute=8,
        max_retries=5,
        checksum="sha256",
        parquet_partition_template="source=bse_ca/year={YYYY}/month={MM}/day={DD}",
        failover_url_patterns=(
            "https://api.bseindia.com/BseIndiaAPI/api/Corpforthresults/w?pageno=1&strCat=-1",
            "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w?pageno=1&strCat=-1&strPrevDate={YYYYMMDD}&strScrip=&strSearch=P&strToDate={YYYYMMDD}&strType=C",
        ),
    ),
    "GDELT": DataSource(
        name="GDELT",
        eras=(
            SourceEra(
                name="all",
                start_date=None,
                end_date=None,
                url_pattern="http://data.gdeltproject.org/gdeltv2/lastupdate.txt",
                file_format="txt",
                schema_note="Last update pointer for 15-minute global event stream.",
            ),
        ),
        max_requests_per_minute=12,
        max_retries=5,
        checksum="md5",
        parquet_partition_template="source=gdelt/year={YYYY}/month={MM}/day={DD}/hour={HH}",
    ),
    "RBI_DBIE": DataSource(
        name="RBI DBIE",
        eras=(
            SourceEra(
                name="all",
                start_date=None,
                end_date=None,
                url_pattern="https://dbie.rbi.org.in/DBIE/dbie.rbi?site=statistics",
                file_format="html_csv",
                schema_note="RBI statistical extraction endpoint with downloadable time series.",
            ),
        ),
        max_requests_per_minute=6,
        max_retries=5,
        checksum="sha256",
        parquet_partition_template="source=rbi_dbie/year={YYYY}/month={MM}",
    ),
    "MOSPI": DataSource(
        name="MOSPI",
        eras=(
            SourceEra(
                name="all",
                start_date=None,
                end_date=None,
                url_pattern="https://www.mospi.gov.in/data",
                file_format="html_csv",
                schema_note="MOSPI statistical dataset listings and downloadable files.",
            ),
        ),
        max_requests_per_minute=6,
        max_retries=5,
        checksum="sha256",
        parquet_partition_template="source=mospi/year={YYYY}/month={MM}",
    ),
    "AMFI_MONTHLY_PORTFOLIOS": DataSource(
        name="AMFI Monthly Portfolios",
        eras=(
            SourceEra(
                name="all",
                start_date=None,
                end_date=None,
                url_pattern="https://www.amfiindia.com/research-information/other-data/mf-scheme-portfolio-holdings",
                file_format="html_xlsx",
                schema_note="AMFI monthly portfolio disclosure files.",
            ),
        ),
        max_requests_per_minute=6,
        max_retries=5,
        checksum="sha256",
        parquet_partition_template="source=amfi_portfolios/year={YYYY}/month={MM}",
    ),
    "NSE_BULK_BLOCK_DEALS": DataSource(
        name="NSE Bulk Block Deals",
        eras=(
            SourceEra(
                name="all",
                start_date=None,
                end_date=None,
                url_pattern="https://www.nseindia.com/api/historicalOR/bulk-block-short-deals",
                file_format="json",
                schema_note="NSE bulk and block deal disclosures.",
            ),
        ),
        max_requests_per_minute=8,
        max_retries=5,
        checksum="sha256",
        parquet_partition_template="source=nse_bulk_block/year={YYYY}/month={MM}/day={DD}",
    ),
    "INSIDER_TRADES": DataSource(
        name="NSE and BSE Insider Trades",
        eras=(
            SourceEra(
                name="nse",
                start_date=None,
                end_date=None,
                url_pattern="https://www.nseindia.com/api/corporates-pit",
                file_format="json",
                schema_note="NSE PIT disclosures.",
            ),
            SourceEra(
                name="bse",
                start_date=None,
                end_date=None,
                url_pattern="https://api.bseindia.com/BseIndiaAPI/api/InsiderTrading/w",
                file_format="json",
                schema_note="BSE insider trading disclosures.",
            ),
        ),
        max_requests_per_minute=8,
        max_retries=5,
        checksum="sha256",
        parquet_partition_template="source=insider_trades/year={YYYY}/month={MM}/day={DD}",
    ),
}


def resolve_era(source_key: str, as_of: date) -> SourceEra:
    source = SOURCE_REGISTRY[source_key]
    for era in source.eras:
        start_ok = era.start_date is None or as_of >= era.start_date
        end_ok = era.end_date is None or as_of <= era.end_date
        if start_ok and end_ok:
            return era
    raise ValueError(f"No source era found for {source_key} on {as_of.isoformat()}")
