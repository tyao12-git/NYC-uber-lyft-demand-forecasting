-- @conn NYC Ride

--- basic raw data filter to create clean_trips--
CREATE OR REPLACE TABLE clean_trips AS

SELECT
    CASE
        WHEN rt.hvfhs_license_num = 'HV0003' THEN 'Uber'
        WHEN rt.hvfhs_license_num = 'HV0005' THEN 'Lyft'
        ELSE 'Other'
    END AS company_name,

    -- 排除不需要的字段，以及需要重新转换的时间字段
    rt.* EXCLUDE (
        hvfhs_license_num,
        dispatching_base_num,
        originating_base_num,
        sales_tax,
        cbd_congestion_fee,
        access_a_ride_flag,
        PULocationID,
        DOLocationID,
        base_passenger_fare,
        driver_pay
    ),



    rt.base_passenger_fare AS base_pass_fare,
    rt.driver_pay,

    pu.Borough AS pickup_borough,
    pu.Zone AS pickup_zone,
    pu.service_zone AS pickup_service_zone,

    do_zone.Borough AS dropoff_borough,
    do_zone.Zone AS dropoff_zone,
    do_zone.service_zone AS dropoff_service_zone

FROM raw_trips AS rt

LEFT JOIN taxi_zones AS pu
    ON rt.PULocationID = pu.LocationID

LEFT JOIN taxi_zones AS do_zone
    ON rt.DOLocationID = do_zone.LocationID

WHERE rt.pickup_datetime IS NOT NULL
  AND rt.dropoff_datetime IS NOT NULL
  AND rt.trip_miles > 0
  AND rt.trip_time > 0
  AND rt.base_passenger_fare > 0
  AND rt.hvfhs_license_num IN ('HV0003', 'HV0005');

SELECT *
FROM clean_trips
LIMIT 10;
--- basic raw data filter to create clean_trips--


---- Uber and Lyft trip count and the percentage of it
SELECT
    company_name,
    COUNT(*) AS trip_count,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (),
        2
    ) AS percentage
FROM clean_trips
GROUP BY company_name
ORDER BY trip_count DESC;

select*
from clean_trips
limit 5;
--- abnormal value table from original data

SELECT
    COUNT(*) FILTER (WHERE trip_miles <= 0) AS invalid_miles,
    COUNT(*) FILTER (WHERE trip_time <= 0) AS invalid_time,
    COUNT(*) FILTER (WHERE base_passenger_fare < 0) AS negative_fare,
    COUNT(*) FILTER (
        WHERE PULocationID NOT BETWEEN 1 AND 265
    ) AS invalid_pickup_zone
FROM raw_trips;

---- Final Clean table

CREATE OR REPLACE TABLE Final_Clean AS

SELECT
    company_name,

    pickup_datetime,
    dropoff_datetime,
    DATE_DIFF(
    'minute',
    request_datetime,
    pickup_datetime
) AS wait_time_minutes,

    Round(trip_time / 60.0,2) AS trip_minutes,
    Round(trip_miles,2) AS trip_miles,

    STRFTIME(

        pickup_datetime,

        '%Y-%m-%d'

    ) AS pickup_date,

    STRFTIME(pickup_datetime, '%A') AS day_of_week,
    EXTRACT(day FROM pickup_datetime) AS day_of_month,

    CASE
        WHEN EXTRACT(dow FROM pickup_datetime) IN (0, 6) --is(0/Sunday, 6/Satuarday)
        THEN 'Yes'
        ELSE 'No'
    END AS is_weekend,


    pickup_zone,
    pickup_borough,
    dropoff_zone,
    dropoff_borough,



    CASE
        WHEN trip_time > 0
        THEN round(trip_miles / (trip_time / 3600.0),2)
        ELSE NULL
    END AS average_speed_mph,

    base_pass_fare,
    driver_pay,
    tolls,
    tips,
    

    shared_request_flag,
    shared_match_flag

FROM clean_trips;

SELECT*
from Final_Clean
where day_of_month ='2'
limit 10;