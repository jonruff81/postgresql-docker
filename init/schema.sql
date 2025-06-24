-- PostgreSQL 15 Schema for takeoff_pricing_db
-- Created for production deployment on Ubuntu 24.04

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create schema for organized table structure
CREATE SCHEMA IF NOT EXISTS pricing;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set search path
SET search_path TO pricing, public;

-- Audit table for tracking changes
CREATE TABLE audit.activity_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(50) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    user_name VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    old_values JSONB,
    new_values JSONB
);

-- Example pricing tables (customize as needed)
CREATE TABLE pricing.products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pricing.price_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES pricing.products(id) ON DELETE CASCADE,
    rule_name VARCHAR(255) NOT NULL,
    base_price DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    effective_from TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    effective_to TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pricing.takeoff_calculations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES pricing.products(id),
    quantity DECIMAL(10,2) NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    calculation_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- Create indexes for performance
CREATE INDEX idx_products_category ON pricing.products(category);
CREATE INDEX idx_price_rules_product_id ON pricing.price_rules(product_id);
CREATE INDEX idx_price_rules_active ON pricing.price_rules(is_active);
CREATE INDEX idx_takeoff_calculations_product_id ON pricing.takeoff_calculations(product_id);
CREATE INDEX idx_takeoff_calculations_date ON pricing.takeoff_calculations(calculation_date);

-- Create user for application access
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user WITH LOGIN PASSWORD 'SecureAppPassword123!';
    END IF;
END
$$;

-- Grant permissions
GRANT USAGE ON SCHEMA pricing TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA pricing TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA pricing TO app_user;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'PostgreSQL 15 schema for takeoff_pricing_db initialized successfully!';
    RAISE NOTICE 'Database ready for production use on Ubuntu 24.04';
END
$$;
