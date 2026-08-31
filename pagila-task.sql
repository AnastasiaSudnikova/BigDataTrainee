-- Запрос 1:
SELECT c.name, COUNT(fc.film_id) AS film_count
FROM category c
JOIN film_category fc ON c.category_id = fc.category_id
GROUP BY c.name
ORDER BY film_count DESC;

-- Запрос 2:
SELECT a.actor_id, a.first_name, a.last_name, COUNT(r.rental_id) AS rental_count
FROM actor a
JOIN film_actor fa ON a.actor_id = fa.actor_id
JOIN inventory i ON fa.film_id = i.film_id
JOIN rental r ON i.inventory_id = r.inventory_id
GROUP BY a.actor_id, a.first_name, a.last_name
ORDER BY rental_count DESC
LIMIT 10;

-- Запрос 3:
SELECT c.name, SUM(p.amount) AS total_revenue
FROM category c
JOIN film_category fc ON c.category_id = fc.category_id
JOIN inventory i ON fc.film_id = i.film_id
JOIN rental r ON i.inventory_id = r.inventory_id
JOIN payment p ON r.rental_id = p.rental_id
GROUP BY c.category_id, c.name
ORDER BY total_revenue DESC
LIMIT 1;

--Запрос 4:
SELECT f.title
FROM film f
LEFT JOIN inventory i ON f.film_id = i.film_id
WHERE i.inventory_id IS NULL;

--Запрос 5:
WITH actor_counts AS (
    SELECT 
        a.actor_id,
        a.first_name,
        a.last_name,
        COUNT(fa.film_id) AS film_count,
        DENSE_RANK() OVER (ORDER BY COUNT(fa.film_id) DESC) AS rnk
    FROM actor a
    JOIN film_actor fa ON a.actor_id = fa.actor_id
    JOIN film_category fc ON fa.film_id = fc.film_id
    JOIN category c ON fc.category_id = c.category_id
    WHERE c.name = 'Children'
    GROUP BY a.actor_id, a.first_name, a.last_name
)
SELECT actor_id, first_name, last_name, film_count
FROM actor_counts
WHERE rnk <= 3;

--Запрос 6:
SELECT 
    c.city,
    COUNT(CASE WHEN cu.active = 1 THEN 1 END) AS active_customers,
    COUNT(CASE WHEN cu.active = 0 THEN 1 END) AS inactive_customers
FROM city c
JOIN address a ON c.city_id = a.city_id
JOIN customer cu ON a.address_id = cu.address_id
GROUP BY c.city_id, c.city
ORDER BY inactive_customers DESC;

--Запрос 7:
WITH city_category_rentals AS (
    SELECT 
        ci.city,
        cat.name AS category_name,
        SUM(r.return_date - r.rental_date) AS total_rental_duration,
        RANK() OVER (
            PARTITION BY ci.city_id 
            ORDER BY SUM(r.return_date - r.rental_date) DESC
        ) as rnk
    FROM customer cu
    JOIN address a ON cu.address_id = a.address_id
    JOIN city ci ON a.city_id = ci.city_id
    JOIN rental r ON cu.customer_id = r.customer_id
    JOIN inventory i ON r.inventory_id = i.inventory_id
    JOIN film f ON i.film_id = f.film_id
    JOIN film_category fc ON f.film_id = fc.film_id
    JOIN category cat ON fc.category_id = cat.category_id
    WHERE LOWER(cat.name) LIKE 'a%' 
       OR ci.city LIKE '%-%'
    GROUP BY ci.city_id, ci.city, cat.category_id, cat.name
)
SELECT 
    city,
    category_name,
    total_rental_duration
FROM city_category_rentals
WHERE rnk = 1;
