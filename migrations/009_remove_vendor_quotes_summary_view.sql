-- Migration 009: Remove vendor quotes summary view
-- This migration removes the v_vendor_quotes_summary view as it's no longer needed

-- Drop the vendor quotes summary view
DROP VIEW IF EXISTS takeoff.v_vendor_quotes_summary;

-- Add a comment to document the removal
-- COMMENT: Removed v_vendor_quotes_summary view as per user request
-- The view was providing summary information about vendor quotes including
-- line item counts, attachment counts, and quote details
-- Data can still be accessed through the underlying tables if needed
