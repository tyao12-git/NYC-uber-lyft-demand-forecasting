-- @conn NYC Ride

--------Excel for identifying taxi zones------------
INSTALL excel;
LOAD excel;

CREATE OR REPLACE TABLE taxi_zones AS
SELECT *
FROM read_csv('/Users/tommyyao/Desktop/taxi_zone_lookup.csv');

Describe taxi_zones;

Select*
from taxi_zones
limit 10;
--------Excel for identifying taxi zones------------

CREATE OR REPLACE VIEW raw_trips AS
SELECT *
FROM read_parquet(
    '/Users/tommyyao/Desktop/Uber Project/nyc-uber-lyft-demand-forecasting/database/2025-09.parquet'
);

SELECT *
FROM raw_trips
LIMIT 5;