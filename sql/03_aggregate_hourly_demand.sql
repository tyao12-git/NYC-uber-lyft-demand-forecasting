---demand 1 with no dropoff zone included
CREATE OR REPLACE View zone_hourly_demand AS

SELECT
    
    request_hour,
    company_name AS company,
    pickup_zone,
    COUNT(*) AS demand,

    ROUND(AVG(temperature_f), 2) AS temp,
    ANY_VALUE(wind_category) AS wind_category,
    ANY_VALUE(rain_category) AS rain_category,
    ANY_VALUE(is_snowing) AS is_snowing


FROM final_cleaned_with_weather

GROUP BY
    request_hour,
    company_name,
    pickup_zone;
---demand 1 with no dropoff zone included



-----Demand 2 with dropoff zone included
CREATE OR REPLACE Table zone_hourly_demand_2 AS

SELECT
    
    request_hour,
    company_name AS company,
    pickup_zone,
    dropoff_zone,
    COUNT(*) AS demand,

    ROUND(AVG(temperature_f), 2) AS temp,
    ANY_VALUE(wind_category) AS wind_category,
    ANY_VALUE(rain_category) AS rain_category,
    ANY_VALUE(is_snowing) AS is_snowing


FROM final_cleaned_with_weather
GROUP BY
    request_hour,
    company_name,
    pickup_zone,
    dropoff_zone;

-----Demand 2 with dropoff zone included





----Desti_OutsideNYC_demand_route
Select
    request_hour,
    company,
    pickup_zone,

    SUM(demand) AS total_demand,
    ROUND(AVG(temp), 2) AS temp,
    ANY_VALUE(wind_category) AS wind_category,
    ANY_VALUE(rain_category) AS rain_category,
    ANY_VALUE(is_snowing) AS is_snowing
    from zone_hourly_demand_2
    where dropoff_zone='Outside of NYC'
    group by request_hour,company,pickup_zone
    order by total_demand desc
    limit 100;

Select 
    request_hour,
    pickup_zone,
    SUM(demand) AS total_demand
    from zone_hourly_demand_2
    where dropoff_zone='Outside of NYC'
    group by request_hour,pickup_zone
    order by total_demand desc
    limit 100;

----Desti_OutsideNYC_demand_route



----Within NYC Demand Query
CREATE OR REPLACE TABLE zone_hourly_without_outNY AS

SELECT
    request_hour,
    pickup_zone,
    dropoff_zone,
    SUM(demand) AS total_demand,
    ANY_VALUE(wind_category) AS wind_category,
    ANY_VALUE(rain_category) AS rain_category,
    ANY_VALUE(is_snowing) AS is_snowing
    from zone_hourly_demand_2
    where dropoff_zone!='Outside of NYC' 
    group by request_hour,pickup_zone,dropoff_zone
    Having sum(demand)>=15
    order by total_demand desc;

Select *
from zone_hourly_without_outNY;
----Within NYC Demand Query




----Hourly Demand By Rain Category
WITH hourly_demand AS (
    SELECT request_hour,
        rain_category,
        SUM(total_demand) AS hourly_total_demand
    FROM zone_hourly_without_outNY
    GROUP BY request_hour,
        rain_category
)
SELECT rain_category,
    ROUND(AVG(hourly_total_demand), 2) AS avg_hourly_demand
FROM hourly_demand
GROUP BY rain_category
ORDER BY avg_hourly_demand;

CREATE OR REPLACE TABLE zone_hourly_withRain AS

SELECT
    request_hour,
    pickup_zone,
    dropoff_zone,
    SUM(demand) AS total_demand,
    ANY_VALUE(wind_category) AS wind_category,
    ANY_VALUE(rain_category) AS rain_category,
    ANY_VALUE(is_snowing) AS is_snowing
    from zone_hourly_demand_2
    where rain_category !='No Rain' and dropoff_zone!='Outside of NYC'
    group by request_hour,pickup_zone,dropoff_zone;



CREATE OR REPLACE TABLE hourly_rain_comparison AS

WITH hourly_total AS (
    SELECT
        request_hour,

        EXTRACT(HOUR FROM request_hour) AS hour_of_day,

        CASE
            WHEN rain_category = 'No Rain'
                THEN 'No Rain'
            ELSE 'Rain'
        END AS rain_status,

        SUM(demand) AS hourly_demand

    FROM zone_hourly_demand_2

    GROUP BY
        request_hour,
        hour_of_day,
        rain_status
)

SELECT
    hour_of_day,
    rain_status,
    ROUND(AVG(hourly_demand), 2) AS avg_hourly_demand

FROM hourly_total

GROUP BY
    hour_of_day,
    rain_status

ORDER BY
    hour_of_day,
    rain_status;
select*
from hourly_rain_comparison;


CREATE OR REPLACE TABLE route_rain_lift AS

WITH route_stats AS (

    SELECT
        company,
        pickup_zone,
        dropoff_zone,

        AVG(
            CASE
                WHEN rain_category != 'No Rain'
                THEN demand
            END
        ) AS avg_rain_demand,

        AVG(
            CASE
                WHEN rain_category = 'No Rain'
                THEN demand
            END
        ) AS avg_no_rain_demand,

        SUM(demand) AS total_demand

    FROM zone_hourly_demand_2

    GROUP BY
        company,
        pickup_zone,
        dropoff_zone
)

SELECT
    company,
    pickup_zone,
    dropoff_zone,

    pickup_zone || ' → ' || dropoff_zone AS route,

    ROUND(avg_rain_demand, 2) AS avg_rain_demand,
    ROUND(avg_no_rain_demand, 2) AS avg_no_rain_demand,

    ROUND(
        avg_rain_demand
        / NULLIF(avg_no_rain_demand, 0)
        - 1,
        4
    ) AS rain_lift,

    total_demand

FROM route_stats

WHERE
    avg_no_rain_demand >= 5
    AND total_demand >= 500

ORDER BY rain_lift DESC;

Select *
from route_rain_lift;

----Hourly Demand By Rain Category


CREATE OR REPLACE TABLE route_snow__lift AS

WITH route_stats AS (

    SELECT
        company,
        pickup_zone,
        dropoff_zone,

        AVG(
            CASE
                WHEN is_snowing != 'No'
                THEN demand
            END
        ) AS avg_snow_demand,

        AVG(
            CASE
                WHEN is_snowing = 'No'
                THEN demand
            END
        ) AS avg_no_snow_demand,

        SUM(demand) AS total_demand

    FROM zone_hourly_demand_2

    GROUP BY
        company,
        pickup_zone,
        dropoff_zone
)

SELECT
    company,
    pickup_zone,
    dropoff_zone,

    pickup_zone || ' → ' || dropoff_zone AS route,

    ROUND(avg_snow_demand, 2) AS avg_snow_demand,
    ROUND(avg_no_snow_demand, 2) AS avg_no_snow_demand,

    ROUND(
        avg_snow_demand
        / NULLIF(avg_no_snow_demand, 0)
        - 1,
        4
    ) AS snow_lift,

    total_demand

FROM route_stats

WHERE
    avg_no_snow_demand >= 5
    AND total_demand >= 500

ORDER BY snow_lift DESC;

Select *
from route_snow__lift;







---------Inspection for multiple weather condition query 
SELECT
    request_hour,
    COUNT(DISTINCT wind_category) AS n_wind,
    COUNT(DISTINCT rain_category) AS n_rain,
    COUNT(DISTINCT is_snowing) AS n_snow
FROM final_cleaned_with_weather
GROUP BY request_hour
HAVING
    COUNT(DISTINCT wind_category) > 1
    OR COUNT(DISTINCT rain_category) > 1
    OR COUNT(DISTINCT is_snowing) > 1;
----------

