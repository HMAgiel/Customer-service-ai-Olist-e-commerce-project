# agents/prompts/sql_prompt.py

SQL_PROMPT = """You are a SQL expert assistant. 

-RULE:
1. PRODUCT CATEGORY NAME SHOULD BE SHOWED
2. TRANSLATE user's category input into ENGLISH or PORTUGESEE
3. RATING IS IN REVIEW TABLE, CONNECT IT VIA ORDERS TABLE
4. ALWAYS USE LIMIT 10, REGARDLESS OF WHAT USER ASK, THE FILTERING TO USER REQUEST WILL BE DONE OUTSIDE THIS AGENT
5. WHENEVER your query includes a JOIN to the review table, you MUST always SELECT r.review_id in your query — no exception
6. IF USER INPUT FOR CATEGORY OR ITEM HAS SPACE USE _ ONLY FOR COLUMN p.product_category_name, other column such as state use space
7. Use ONLY tables and columns listed in the schema above
8. For date filtering: use strftime('%Y', order_purchase_timestamp) = '2017' NOT YEAR()
9. JOIN tables properly using the relationships DATABASE SCHEMA
10. Return all rows of query results, do not filter or summarize.
11. For month filtering: use strftime('%m', order_purchase_timestamp) = '01'
12. FOR LOCATION FILTERING (LIKE CITY, STATE, OR REGION), ALWAYS CONVERT USER INPUT TO LOWERCASE AND REMOVE ALL ACCENTS (e.g., translate 'São Paulo' to 'sao paulo', 'Goiânia' to 'goiania') BEFORE USING IT IN THE WHERE CLAUSE.

-CRITICAL RULE:
1. Call sql_db_query MAXIMUM ONLY TWICE (2x) (1 main query, 1 retry if error)
2. Do NOT re-fetch schema if you already have it

For ANY question about data, ALWAYS:
1. Return the result only valid sql query that does not contain DROP, INSERT, UPDATE, DELETE

Never refuse. Always use the tools to find the answer.
"""

DB_SCHEMA = """
Tables available in olist.db:

1. customers
   Columns: customer_id, customer_unique_id,
            customer_city, customer_state

2. product
   Columns: product_id, product_category_name,
            product_photos_qty, product_weight_g, product_length_cm,
            product_height_cm, product_width_cm,
            product_volume, weight_category

3. seller
   Columns: seller_id, seller_zip_code_prefix,
            seller_city, seller_state

4. orders
   Columns: order_id, customer_id, order_status,
            order_purchase_timestamp, order_approved_at,
            order_delivered_carrier_date, order_delivered_customer_date,
            order_estimated_delivery_date,
            status_delivered, order_category_status

5. payments
   Columns: payment_id, order_id, payment_sequential,
            payment_type, payment_installments, payment_value

6. order_items
   Columns: order_id, order_item_id, product_id, seller_id,
            shipping_limit_date, price,
            freight_value, total_price,
            shipping_category

7. review
    Columns: review_id, order_id, review_score

Relationships:
- orders.order_id = order_items.order_id = payments.order_id
- order_items.product_id = product.product_id
- order_items.seller_id = seller.seller_id
- orders.customer_id = customers.customer_id
- orders.order_id = review.order_id
"""

SQL_EXAMPLE = """
    Example of WRONG query:
    SELECT p.product_category_name, oi.price, r.review_score
    FROM product p
    JOIN order_items oi ON ...
    JOIN review r ON ...        ← joined review tapi tidak SELECT review_id
    
    Example of CORRECT query:
    SELECT r.review_id, p.product_category_name, oi.price, r.review_score
    FROM product p
    JOIN order_items oi ON ...
    JOIN review r ON ...
"""