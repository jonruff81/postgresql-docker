-- Migration 007: Remove job cost analysis view
-- This migration removes the v_job_cost_analysis view as it's no longer needed

-- Drop the job cost analysis view
DROP VIEW IF EXISTS takeoff.v_job_cost_analysis;

-- Add a comment to document the removal
-- COMMENT: Removed v_job_cost_analysis view as per user request
-- The view was aggregating job costs with plan and elevation details
-- Data can still be accessed through the underlying tables if needed
