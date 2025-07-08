-- Insert sample data into plans table
INSERT INTO plans (plan_name, architect, engineer)
VALUES 
  ('Plan 1', 'Architect 1', 'Engineer 1'),
  ('Plan 2', 'Architect 2', 'Engineer 2');

-- Insert sample data into plan_elevations table  
INSERT INTO plan_elevations (plan_id, elevation_name, foundation, heated_sf_inside_studs, total_sf_outside_studs)
VALUES
  (1, 'Elevation 1A', 'Slab', 1000, 1200),
  (1, 'Elevation 1B', 'Crawl', 1100, 1300),
  (2, 'Elevation 2A', 'Basement', 1500, 1800);
  
-- Insert sample data into plan_options table
INSERT INTO plan_options (plan_elevation_id, option_name, option_type)  
VALUES
  (1, 'Option 1A-1', 'Exterior'),
  (1, 'Option 1A-2', 'Interior'),
  (2, 'Option 1B-1', 'Exterior'),
  (3, 'Option 2A-1', 'Interior'),
  (3, 'Option 2A-2', 'Exterior');
