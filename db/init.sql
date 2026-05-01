-- =====================================================
-- Orders Database Schema — Seed Script for Demo
-- =====================================================

-- Customer tiers enum
CREATE TYPE customer_tier AS ENUM ('STANDARD', 'GOLD', 'PLATINUM');

-- Order status enum
CREATE TYPE order_status AS ENUM ('PENDING', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED');

-- ─── Customers ──────────────────────────────────────
CREATE TABLE customers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) NOT NULL UNIQUE,
    name        VARCHAR(100) NOT NULL,
    tier        customer_tier NOT NULL DEFAULT 'STANDARD',
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

COMMENT ON TABLE customers IS 'Registered customers with loyalty tiers';
COMMENT ON COLUMN customers.tier IS 'Loyalty tier: STANDARD, GOLD, or PLATINUM. GOLD customers get 10% discount on orders over $500';

-- ─── Orders ─────────────────────────────────────────
CREATE TABLE orders (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id       UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    status            order_status NOT NULL DEFAULT 'PENDING',
    total_amount      NUMERIC(12,2) NOT NULL CHECK (total_amount >= 0),
    discount_applied  NUMERIC(12,2) NOT NULL DEFAULT 0.00 CHECK (discount_applied >= 0),
    notes             TEXT,
    created_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

COMMENT ON TABLE orders IS 'Customer orders. Business rule: GOLD tier customers receive 10% discount when total > $500';
COMMENT ON COLUMN orders.discount_applied IS 'Discount amount in dollars. Applied per business rules based on customer tier and order total';

CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);

-- ─── Order Items ────────────────────────────────────
CREATE TABLE order_items (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id    UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id  VARCHAR(100) NOT NULL,
    quantity    INTEGER NOT NULL CHECK (quantity > 0),
    unit_price  NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0),
    line_total  NUMERIC(12,2) GENERATED ALWAYS AS (quantity * unit_price) STORED
);

COMMENT ON TABLE order_items IS 'Line items within an order. line_total is auto-computed';
COMMENT ON COLUMN order_items.quantity IS 'Must be positive (CHECK quantity > 0)';

CREATE INDEX idx_order_items_order_id ON order_items(order_id);

-- ─── Views ──────────────────────────────────────────
CREATE VIEW order_summary AS
SELECT
    o.id AS order_id,
    c.name AS customer_name,
    c.tier AS customer_tier,
    o.status,
    o.total_amount,
    o.discount_applied,
    (o.total_amount - o.discount_applied) AS final_amount,
    o.created_at,
    COUNT(oi.id) AS item_count
FROM orders o
JOIN customers c ON o.customer_id = c.id
LEFT JOIN order_items oi ON o.id = oi.order_id
GROUP BY o.id, c.name, c.tier, o.status, o.total_amount, o.discount_applied, o.created_at;

COMMENT ON VIEW order_summary IS 'Denormalized view joining orders with customer info and item counts';

-- ─── Seed Data ──────────────────────────────────────
INSERT INTO customers (id, email, name, tier) VALUES
    ('11111111-1111-1111-1111-111111111111', 'john@example.com', 'John Doe', 'STANDARD'),
    ('22222222-2222-2222-2222-222222222222', 'jane@example.com', 'Jane Smith', 'GOLD'),
    ('33333333-3333-3333-3333-333333333333', 'bob@example.com', 'Bob Premium', 'PLATINUM');

INSERT INTO orders (id, customer_id, status, total_amount, discount_applied) VALUES
    ('aaaa1111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', 'PENDING', 250.00, 0.00),
    ('aaaa2222-2222-2222-2222-222222222222', '22222222-2222-2222-2222-222222222222', 'CONFIRMED', 600.00, 60.00),
    ('aaaa3333-3333-3333-3333-333333333333', '22222222-2222-2222-2222-222222222222', 'SHIPPED', 300.00, 0.00);

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
    ('aaaa1111-1111-1111-1111-111111111111', 'PROD-001', 2, 100.00),
    ('aaaa1111-1111-1111-1111-111111111111', 'PROD-002', 1, 50.00),
    ('aaaa2222-2222-2222-2222-222222222222', 'PROD-003', 3, 200.00),
    ('aaaa3333-3333-3333-3333-333333333333', 'PROD-001', 3, 100.00);
