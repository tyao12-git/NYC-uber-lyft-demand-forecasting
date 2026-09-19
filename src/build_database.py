from pathlib import Path

import duckdb


# root directory for the project
PROJECT_DIR = Path(__file__).resolve().parent

# folder containing all 2025 monthly parquet files
PARQUET_DIR = Path(
    "/Users/tommyyao/Desktop/Uber Project/nyc-uber-lyft-demand-forecasting/data/raw/fhvhv"
)

DATABASE_PATH = Path(
    "/Users/tommyyao/Desktop/Uber Project/nyc-uber-lyft-demand-forecasting/database/nyc_rides.duckdb"
)


def main() -> None:

    # check parquet folder
    if not PARQUET_DIR.exists():
        raise FileNotFoundError(
            f"Cannot find Parquet folder: {PARQUET_DIR}"
        )

    # check how many parquet files exist
    parquet_files = sorted(PARQUET_DIR.glob("fhvhv_tripdata_2025-*.parquet"))

    if not parquet_files:
        raise FileNotFoundError(
            f"No 2025 parquet files found in: {PARQUET_DIR}"
        )

    print(f"Found {len(parquet_files)} parquet files:")

    for file in parquet_files:
        print(f"  - {file.name}")

    # create database folder automatically
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # connect to DuckDB database
    con = duckdb.connect(str(DATABASE_PATH))

    try:

        parquet_sql_path = str(
            PARQUET_DIR / "fhvhv_tripdata_2025-*.parquet"
        ).replace("'", "''")

        # create raw_trips view from all monthly parquet files
        con.execute(
            f"""
            CREATE OR REPLACE VIEW raw_trips AS
            SELECT *
            FROM read_parquet(
                '{parquet_sql_path}',
                union_by_name = true
            )
            """
        )

        print("\nDatabase created successfully.")
        print(f"Database location: {DATABASE_PATH}")

        print("\nTables and views:")
        print(
            con.execute(
                """
                SHOW ALL TABLES
                """
            ).df()
        )

        print("\nFirst 5 rows:")
        print(
            con.execute(
                """
                SELECT *
                FROM raw_trips
                LIMIT 5
                """
            ).df()
        )

        print("\nDate range:")
        print(
            con.execute(
                """
                SELECT
                    MIN(request_datetime) AS min_date,
                    MAX(request_datetime) AS max_date
                FROM raw_trips
                """
            ).df()
        )

        print("\nRows by month:")
        print(
            con.execute(
                """
                SELECT
                    DATE_TRUNC('month', request_datetime) AS month,
                    COUNT(*) AS total_rows
                FROM raw_trips
                GROUP BY month
                ORDER BY month
                """
            ).df()
        )

        print("\nField structure:")
        print(
            con.execute(
                """
                DESCRIBE raw_trips
                """
            ).df()
        )

    finally:
        con.close()


if __name__ == "__main__":
    main()