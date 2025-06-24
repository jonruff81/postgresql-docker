-- Complete, Consolidated Database Schema
-- This script combines all previous schema definitions and fixes into a single, authoritative file.

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create main schema
DROP SCHEMA IF EXISTS takeoff CASCADE;
CREATE SCHEMA takeoff;
SET search_path TO takeoff, public;

-- =====================================
-- REFERENCE TABLES
-- =====================================

CREATE TABLE divisions (
    division_id SERIAL PRIMARY KEY,
    division_name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE communities (
    community_id SERIAL PRIMARY KEY,
    division_id INT REFERENCES divisions(division_id),
    community_name VARCHAR(255) NOT NULL
);

CREATE TABLE cost_groups (
    cost_group_id SERIAL PRIMARY KEY,
    cost_group_code VARCHAR(50) NOT NULL UNIQUE,
    cost_group_name VARCHAR(255) NOT NULL
);

CREATE TABLE cost_codes (
    cost_code_id SERIAL PRIMARY KEY,
    cost_group_id INT REFERENCES cost_groups(cost_group_id),
    cost_code VARCHAR(50) NOT NULL UNIQUE,
    cost_code_description VARCHAR(255) NOT NULL
);

CREATE TABLE vendors (
    vendor_id SERIAL PRIMARY KEY,
    vendor_name VARCHAR(255) NOT NULL UNIQUE
);

-- =====================================
-- FORMULA ENGINE
-- =====================================

CREATE TABLE formulas (
    formula_id SERIAL PRIMARY KEY,
    formula_name VARCHAR(100) NOT NULL UNIQUE,
    formula_text TEXT NOT NULL,
    formula_type VARCHAR(50),
    depends_on_fields VARCHAR(255),
    calculation_order INT DEFAULT 100,
    is_active BOOLEAN DEFAULT TRUE
);

-- =====================================
-- ITEMS AND PRODUCTS
-- =====================================

CREATE TABLE items (
    item_id SERIAL PRIMARY KEY,
    item_name VARCHAR(255) NOT NULL UNIQUE,
    cost_code_id INT REFERENCES cost_codes(cost_code_id),
    formula_id INT REFERENCES formulas(formula_id),
    qty_type VARCHAR(50),
    default_unit VARCHAR(50)
);

CREATE TABLE item_attributes (
    attribute_id SERIAL PRIMARY KEY,
    item_id INT REFERENCES items(item_id) ON DELETE CASCADE,
    attribute_name VARCHAR(100) NOT NULL,
    attribute_value TEXT
);

CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    item_id INT REFERENCES items(item_id),
    product_description TEXT,
    model VARCHAR(100)
);

CREATE TABLE vendor_pricing (
    pricing_id SERIAL PRIMARY KEY,
    vendor_id INT REFERENCES vendors(vendor_id),
    product_id INT REFERENCES products(product_id),
    price DECIMAL(12,4) NOT NULL,
    unit_of_measure VARCHAR(50),
    is_current BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(vendor_id, product_id)
);

-- =====================================
-- PLAN STRUCTURE
-- =====================================

CREATE TABLE plans (
    plan_id SERIAL PRIMARY KEY,
    plan_name VARCHAR(100) NOT NULL UNIQUE,
    architect VARCHAR(255),
    engineer VARCHAR(255)
);

CREATE TABLE plan_elevations (
    plan_elevation_id SERIAL PRIMARY KEY,
    plan_id INT REFERENCES plans(plan_id),
    elevation_name VARCHAR(50) NOT NULL,
    foundation VARCHAR(50) NOT NULL,
    heated_sf_inside_studs INT,
    total_sf_outside_studs INT,
    UNIQUE(plan_id, elevation_name, foundation)
);

CREATE TABLE plan_options (
    plan_option_id SERIAL PRIMARY KEY,
    plan_elevation_id INT REFERENCES plan_elevations(plan_elevation_id),
    option_name VARCHAR(100) NOT NULL,
    option_type VARCHAR(50),
    UNIQUE(plan_elevation_id, option_name)
);

-- =====================================
-- JOBS AND TAKEOFFS
-- =====================================

CREATE TABLE jobs (
    job_id SERIAL PRIMARY KEY,
    job_name VARCHAR(255),
    plan_option_id INT REFERENCES plan_options(plan_option_id),
    is_template BOOLEAN DEFAULT TRUE
);

CREATE TABLE takeoffs (
    takeoff_id INT PRIMARY KEY,
    job_id INT REFERENCES jobs(job_id),
    product_id INT REFERENCES products(product_id),
    vendor_id INT REFERENCES vendors(vendor_id),
    quantity DECIMAL(12,4),
    unit_price DECIMAL(12,4),
    extended_price DECIMAL(12,2),
    quantity_source VARCHAR(100)
);

-- =====================================
-- FILE MANAGEMENT
-- =====================================

CREATE TABLE files (
    file_id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_type VARCHAR(50)
);

CREATE TABLE file_links (
    link_id SERIAL PRIMARY KEY,
    file_id INT REFERENCES files(file_id) ON DELETE CASCADE,
    job_id INT REFERENCES jobs(job_id) ON DELETE CASCADE,
    plan_option_id INT REFERENCES plan_options(plan_option_id) ON DELETE CASCADE,
    item_id INT REFERENCES items(item_id) ON DELETE CASCADE
);

-- =====================================
-- VIEWS
-- =====================================

CREATE VIEW v_job_cost_analysis AS
SELECT 
    j.job_id,
    j.job_name,
    p.plan_name,
    pe.elevation_name,
    pe.foundation,
    po.option_name,
    pe.heated_sf_inside_studs,
    SUM(t.extended_price) as total_cost,
    CASE 
        WHEN pe.heated_sf_inside_studs > 0 THEN SUM(t.extended_price) / pe.heated_sf_inside_studs
        ELSE 0 
    END as cost_per_heated_sq_ft
FROM takeoff.jobs j
JOIN takeoff.takeoffs t ON j.job_id = t.job_id
JOIN takeoff.plan_options po ON j.plan_option_id = po.plan_option_id
JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
JOIN takeoff.plans p ON pe.plan_id = p.plan_id
WHERE j.is_template = TRUE
GROUP BY j.job_id, j.job_name, p.plan_name, pe.elevation_name, pe.foundation, po.option_name, pe.heated_sf_inside_studs;

-- =====================================
-- INITIAL DATA
-- =====================================

INSERT INTO divisions (division_name) VALUES ('Custom'), ('Service'), ('Neighborhood'), ('Renovation');

INSERT INTO formulas (formula_name, formula_text, formula_type, depends_on_fields) VALUES
('Per Build', '1', 'Per_Unit', ''),
('Heated Sq Ft', 'heated_sf_inside_studs', 'SqFt_Calculation', 'heated_sf_inside_studs'),
('Under Roof Sq Ft', 'total_sf_outside_studs', 'SqFt_Calculation', 'total_sf_outside_studs');

SELECT 'Complete schema created successfully!' as status;