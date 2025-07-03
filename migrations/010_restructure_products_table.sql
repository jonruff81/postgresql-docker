-- Migration 010: Restructure products table with enhanced fields
-- This migration adds new fields to the products table for comprehensive product information

-- Add new columns to the products table
ALTER TABLE takeoff.products 
ADD COLUMN IF NOT EXISTS selection_level character varying(50),
ADD COLUMN IF NOT EXISTS brand character varying(100),
ADD COLUMN IF NOT EXISTS style character varying(100),
ADD COLUMN IF NOT EXISTS color character varying(50),
ADD COLUMN IF NOT EXISTS finish character varying(50),
ADD COLUMN IF NOT EXISTS sku character varying(100),
ADD COLUMN IF NOT EXISTS size character varying(50),
ADD COLUMN IF NOT EXISTS material character varying(100),
ADD COLUMN IF NOT EXISTS image text,
ADD COLUMN IF NOT EXISTS url_link text,
ADD COLUMN IF NOT EXISTS quote_file text,
ADD COLUMN IF NOT EXISTS brochure text,
ADD COLUMN IF NOT EXISTS item_type character varying(50),
ADD COLUMN IF NOT EXISTS is_active boolean DEFAULT true;

-- Add comments to document the new fields
COMMENT ON COLUMN takeoff.products.selection_level IS 'Product selection level (e.g., Standard, Upgrade, Premium)';
COMMENT ON COLUMN takeoff.products.brand IS 'Product brand name';
COMMENT ON COLUMN takeoff.products.style IS 'Product style description';
COMMENT ON COLUMN takeoff.products.color IS 'Product color';
COMMENT ON COLUMN takeoff.products.finish IS 'Product finish type';
COMMENT ON COLUMN takeoff.products.sku IS 'Stock Keeping Unit - unique product identifier';
COMMENT ON COLUMN takeoff.products.size IS 'Product size specifications';
COMMENT ON COLUMN takeoff.products.material IS 'Primary material composition';
COMMENT ON COLUMN takeoff.products.image IS 'Path or URL to product image';
COMMENT ON COLUMN takeoff.products.url_link IS 'Link to product webpage or documentation';
COMMENT ON COLUMN takeoff.products.quote_file IS 'Path to quote file or document';
COMMENT ON COLUMN takeoff.products.brochure IS 'Path to product brochure or specification sheet';
COMMENT ON COLUMN takeoff.products.item_type IS 'Type categorization for the product';
COMMENT ON COLUMN takeoff.products.is_active IS 'Whether the product is currently active/available';

-- Update the table comment
COMMENT ON TABLE takeoff.products IS 'Enhanced product catalog with comprehensive product information including brand, style, materials, and documentation links';
