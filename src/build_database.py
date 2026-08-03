from pathlib import Path

import duckdb


# 当前项目根目录
PROJECT_DIR = Path(__file__).resolve().parent

PARQUET_PATH = Path(

    "/Users/tommyyao/Desktop/Uber Project/nyc-uber-lyft-demand-forecasting/data/raw/fhvhv/2025-09.parquet"

)

DATABASE_PATH = Path(

    "/Users/tommyyao/Desktop/Uber Project/nyc-uber-lyft-demand-forecasting/database/nyc_rides.duckdb"

)


def main() -> None:
    if not PARQUET_PATH.exists():
        raise FileNotFoundError(
            f"找不到 Parquet 文件：{PARQUET_PATH}"
        )

    # 自动创建 database 文件夹
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 连接到持久化 DuckDB 数据库
    con = duckdb.connect(str(DATABASE_PATH))

    try:
        # 建立一个指向 Parquet 文件的 View
        # 不复制 1900 多万行数据，因此速度快，也节省硬盘
        parquet_sql_path = str(PARQUET_PATH).replace("'", "''")


        con.execute(
            f"""
            CREATE OR REPLACE VIEW raw_trips AS
            SELECT *
            FROM read_parquet('{parquet_sql_path}')
            """
        )

        print("数据库创建成功。")
        print(f"数据库位置：{DATABASE_PATH}")

        print("\n表和 View：")
        print(con.execute("SHOW ALL TABLES").df())

        print("\n数据前 5 行：")
        print(
            con.execute(
                """
                SELECT *
                FROM raw_trips
                LIMIT 5
                """
            ).df()
        )

        print("\n总行数：")
        print(
            con.execute(
                """
                SELECT COUNT(*) AS total_rows
                FROM raw_trips
                """
            ).df()
        )

        print("\n字段结构：")
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