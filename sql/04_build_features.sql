-- @conn NYC Ride




--- Group by Location and its popularity, extract Monday data for now
SELECT
    company_name,
    pickup_zone,
    pickup_borough,
    COUNT(*) AS trip_count
FROM Final_Clean
WHERE day_of_week = 'Monday' and pickup_borough='Queens'
GROUP BY
    company_name,
    pickup_zone,
    pickup_borough
ORDER BY company_name DESC,
         trip_count DESC;

