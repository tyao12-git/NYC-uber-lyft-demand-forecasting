-- @conn NYC Rides 2025

--- basic raw data filter to create clean_trips--

CREATE OR REPLACE VIEW clean_trips AS

SELECT
    CASE
        WHEN rt.hvfhs_license_num = 'HV0003' THEN 'Uber'
        WHEN rt.hvfhs_license_num = 'HV0005' THEN 'Lyft'
        ELSE 'Other'
    END AS company_name,

    -- exclude the unnecessary columns that are useless for analysis
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
  And rt.request_datetime IS NOT NULL
  AND rt.dropoff_datetime IS NOT NULL
  AND request_datetime <= pickup_datetime
  AND pickup_datetime <= dropoff_datetime
  AND (
      on_scene_datetime IS NULL
      OR (
          request_datetime <= on_scene_datetime
          AND on_scene_datetime <= pickup_datetime
      )
  )
  AND rt.trip_miles > 0
  AND rt.trip_time > 0
  AND rt.base_passenger_fare > 0
  AND rt.hvfhs_license_num IN ('HV0003', 'HV0005');


--- basic raw data filter to create clean_trips--


---- Final Clean table without weather join

CREATE OR REPLACE VIEW Final_Clean AS

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
    DATE_TRUNC('hour', request_datetime) AS request_hour,
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



------ Final clean table with weather join
CREATE OR REPLACE VIEW final_cleaned_with_weather AS

SELECT
    w.*,

    -- =========================
    -- Temperature
    -- =========================
    ROUND(c.temperature_2m, 2) AS temperature_f,

    CASE
        WHEN c.temperature_2m < 50 THEN 'Cold'
        WHEN c.temperature_2m < 80 THEN 'Normal'
        WHEN c.temperature_2m < 90 THEN 'Hot'
        ELSE 'Extreme Hot'
    END AS temperature_category,


    -- =========================
    -- Rain
    -- =========================
    ROUND(c.rain, 2) AS rain_inches,

    CASE
        WHEN COALESCE(c.rain, 0) = 0 THEN 'No Rain'
        WHEN c.rain <= 0.10 THEN 'Light Rain'
        ELSE 'Heavy Rain'
    END AS rain_category,


    -- =========================
    -- Snowfall
    -- =========================
    ROUND(c.snowfall, 2) AS snowfall_inches,

    CASE
        WHEN COALESCE(c.snowfall, 0) = 0 THEN 'No Snow'
        WHEN c.snowfall <= 0.10 THEN 'Light Snow'
        ELSE 'Heavy Snow'
    END AS snowfall_category,


    -- =========================
    -- Wind
    -- =========================
    ROUND(c.wind_speed_10m, 2) AS wind_speed_mph,

    CASE
        WHEN COALESCE(c.wind_speed_10m, 0) <= 3 THEN 'No Wind'
        WHEN c.wind_speed_10m <= 15 THEN 'Light Wind'
        ELSE 'Strong Wind'
    END AS wind_category,


    -- =========================
    -- Precipitation
    -- =========================
    CASE
        WHEN c.is_precipitating = 1 THEN 'Yes'
        ELSE 'No'
    END AS is_precipitating,


    -- =========================
    -- Snow
    -- =========================
    CASE
        WHEN c.is_snowing = 1 THEN 'Yes'
        ELSE 'No'
    END AS is_snowing


FROM Final_Clean AS w

LEFT JOIN read_csv_auto(
    '/Users/tommyyao/Desktop/Uber Project/nyc-uber-lyft-demand-forecasting/data/raw/weather/nyc_weather_hourly_2025.csv'
) AS c 
ON c.weather_hour = w.request_hour;




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

-----


CREATE OR REPLACE TABLE data_quality_summary AS

WITH raw_stats AS (
    SELECT
        COUNT(*) AS total_records,

        COUNT(*) FILTER (
            WHERE pickup_datetime < request_datetime
        ) AS negative_wait_time,

        COUNT(*) FILTER (
            WHERE hvfhs_license_num = 'HV0003'
        ) AS uber_records,

        COUNT(*) FILTER (
            WHERE hvfhs_license_num = 'HV0005'
        ) AS lyft_records,

        COUNT(*) FILTER (
            WHERE pickup_datetime IS NULL
        ) AS missing_pickup_time,

        COUNT(*) FILTER (
            WHERE dropoff_datetime <= pickup_datetime
        ) AS invalid_trip_duration,

        COUNT(*) FILTER (
            WHERE hvfhs_license_num NOT IN ('HV0003', 'HV0005')
               OR hvfhs_license_num IS NULL
        ) AS unknown_company

    FROM raw_trips
),

clean_stats AS (
    SELECT
        COUNT(*) AS total_records,

        COUNT(*) FILTER (
            WHERE pickup_datetime < request_datetime
        ) AS negative_wait_time,

        COUNT(*) FILTER (
            WHERE company_name = 'Uber'
        ) AS uber_records,

        COUNT(*) FILTER (
            WHERE company_name = 'Lyft'
        ) AS lyft_records,

        COUNT(*) FILTER (
            WHERE pickup_datetime IS NULL
        ) AS missing_pickup_time,

        COUNT(*) FILTER (
            WHERE dropoff_datetime <= pickup_datetime
        ) AS invalid_trip_duration,

        COUNT(*) FILTER (
            WHERE company_name NOT IN ('Uber', 'Lyft')
               OR company_name IS NULL
        ) AS unknown_company

    FROM clean_trips
)

SELECT
    'Total Records' AS metric,
    r.total_records AS raw_data,
    c.total_records AS clean_data,
    ROUND(
        (c.total_records - r.total_records)
        * 100.0 / r.total_records,
        2
    ) || '%' AS change
FROM raw_stats r, clean_stats c

UNION ALL

SELECT
    'Negative Wait Time',
    r.negative_wait_time,
    c.negative_wait_time,
    'Removed'
FROM raw_stats r, clean_stats c

UNION ALL

SELECT
    'Uber Records',
    r.uber_records,
    c.uber_records,
    ROUND(
        (c.uber_records - r.uber_records)
        * 100.0 / NULLIF(r.uber_records, 0),
        2
    ) || '%'
FROM raw_stats r, clean_stats c

UNION ALL

SELECT
    'Lyft Records',
    r.lyft_records,
    c.lyft_records,
    ROUND(
        (c.lyft_records - r.lyft_records)
        * 100.0 / NULLIF(r.lyft_records, 0),
        2
    ) || '%'
FROM raw_stats r, clean_stats c

UNION ALL

SELECT
    'Missing Pickup Time',
    r.missing_pickup_time,
    c.missing_pickup_time,
    'Removed'
FROM raw_stats r, clean_stats c

UNION ALL

SELECT
    'Invalid Trip Duration',
    r.invalid_trip_duration,
    c.invalid_trip_duration,
    'Removed'
FROM raw_stats r, clean_stats c

UNION ALL

SELECT
    'Unknown Company',
    r.unknown_company,
    c.unknown_company,
    'Removed'
FROM raw_stats r, clean_stats c;




----test query zone 

select * from data_quality_summary;


Select *
from final_cleaned_with_weather
where pickup_date = '2025-09-30'
    and pickup_borough = 'Manhattan'
    and request_hour = '2025-09-30 20:00'
    and company_name = 'Uber'
limit 10;





select *
from final_cleaned_with_weather
where temperature_f >= 80 and pickup_date='2025-07-15'
limit 10; 
---- test query above end