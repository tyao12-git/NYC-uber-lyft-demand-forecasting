-- @conn NYC Rides 2025

--------Excel for identifying taxi zones------------
INSTALL excel;
LOAD excel;

CREATE OR REPLACE TABLE taxi_zones AS
SELECT *
FROM read_csv('/Users/tommyyao/Desktop/Uber Project/nyc-uber-lyft-demand-forecasting/data/raw/taxi_zones/taxi_zone_lookup.csv');

Describe taxi_zones;

Select*
from taxi_zones
limit 10;
--------Excel for identifying taxi zones------------

CREATE OR REPLACE VIEW raw_trips AS
SELECT *
FROM read_parquet(
    '/Users/tommyyao/Desktop/Uber Project/nyc-uber-lyft-demand-forecasting/data/raw/fhvhv/fhvhv_tripdata_2025-*.parquet',
    union_by_name = TRUE
);

SELECT *
FROM raw_trips
LIMIT 5;


----Date Range Check
SELECT
    MIN(request_datetime) AS min_date,
    MAX(request_datetime) AS max_date
FROM raw_trips;
----Date Range Check

