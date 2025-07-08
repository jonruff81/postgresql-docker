-- Migration: Add qty_formula column to items table
ALTER TABLE takeoff.items
ADD COLUMN qty_formula TEXT;
