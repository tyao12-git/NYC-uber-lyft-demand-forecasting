
CREATE OR REPLACE Table demand_features AS

SELECT

    request_hour,
    company,
    pickup_zone,

    -- TARGET
    demand,

    --------------------------------------------------
    -- TIME FEATURES
    --------------------------------------------------

    EXTRACT(HOUR FROM request_hour) AS hour_of_day,

    EXTRACT(DOW FROM request_hour) AS day_of_week,

    EXTRACT(MONTH FROM request_hour) AS month,

    CASE
        WHEN EXTRACT(DOW FROM request_hour) IN (0, 6)
        THEN 1
        ELSE 0
    END AS is_weekend,


    --------------------------------------------------
    -- WEATHER FEATURES
    --------------------------------------------------

    temp,
    wind_category,
    rain_category,
    is_snowing,


    --------------------------------------------------
    -- LAG FEATURES
    --------------------------------------------------

    LAG(demand, 1) OVER (
        PARTITION BY company, pickup_zone
        ORDER BY request_hour
    ) AS lag_1h,


    LAG(demand, 2) OVER (
        PARTITION BY company, pickup_zone
        ORDER BY request_hour
    ) AS lag_2h,


    LAG(demand, 24) OVER (
        PARTITION BY company, pickup_zone
        ORDER BY request_hour
    ) AS lag_24h,


    LAG(demand, 168) OVER (
        PARTITION BY company, pickup_zone
        ORDER BY request_hour
    ) AS lag_168h,


    --------------------------------------------------
    -- ROLLING FEATURES
    --------------------------------------------------

    AVG(demand) OVER (
        PARTITION BY company, pickup_zone
        ORDER BY request_hour
        ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING
    ) AS rolling_3h_avg,


    AVG(demand) OVER (
        PARTITION BY company, pickup_zone
        ORDER BY request_hour
        ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING
    ) AS rolling_6h_avg,


    AVG(demand) OVER (
        PARTITION BY company, pickup_zone
        ORDER BY request_hour
        ROWS BETWEEN 24 PRECEDING AND 1 PRECEDING
    ) AS rolling_24h_avg


FROM zone_hourly_demand;

-----Temporary View
Select*
from demand_features
where lag_168h is Not null
limit10;
-----Temporary View
COPY demand_features
TO 'demand_features.csv'
(HEADER, DELIMITER ',');

SELECT COUNT(*)
FROM zone_hourly_demand;

COPY zone_hourly_demand
TO 'Zone_Hourly_Demand.csv'
(HEADER, DELIMITER ',');

-----Rolling and lag features quality check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN time_gap != INTERVAL '1 hour' THEN 1 ELSE 0 END)
        AS irregular_gaps
FROM (
    SELECT
        request_hour,
        request_hour - LAG(request_hour, 1) OVER (
            PARTITION BY company, pickup_zone
            ORDER BY request_hour
        ) AS time_gap
    FROM zone_hourly_demand

    
);

SELECT
    company,
    pickup_zone,
    request_hour,

    request_hour - LAG(request_hour, 1) OVER (
        PARTITION BY company, pickup_zone
        ORDER BY request_hour
    ) AS time_gap

FROM zone_hourly_demand
LIMIT 1000;
-----deeper inspection


WITH gaps AS (
    SELECT
        request_hour -
        LAG(request_hour, 1) OVER (
            PARTITION BY company, pickup_zone
            ORDER BY request_hour
        ) AS time_gap
    FROM zone_hourly_demand
)

SELECT
    time_gap,
    COUNT(*) AS observations
FROM gaps
WHERE time_gap IS NOT NULL
GROUP BY time_gap
ORDER BY observations DESC
LIMIT 20;