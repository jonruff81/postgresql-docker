-- Migration 008: Remove takeoff analysis view
-- This migration removes the v_takeoff_analysis view as it's no longer needed

-- Drop the takeoff analysis view
DROP VIEW IF EXISTS takeoff.v_takeoff_analysis;

-- Add a comment to document the removal
-- COMMENT: Removed v_takeoff_analysis view as per user request
-- The view was providing comprehensive takeoff analysis with plan, cost code, 
-- item, product, and vendor details
-- Data can still be accessed through the underlying tables if needed
