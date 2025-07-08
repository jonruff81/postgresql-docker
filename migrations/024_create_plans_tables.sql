-- Create plans table
CREATE TABLE IF NOT EXISTS plans (
  plan_id SERIAL PRIMARY KEY,
  plan_name VARCHAR(255) NOT NULL,
  architect VARCHAR(255),
  engineer VARCHAR(255)
);

-- Create plan_elevations table
CREATE TABLE IF NOT EXISTS plan_elevations (
  plan_elevation_id SERIAL PRIMARY KEY,
  plan_id INTEGER REFERENCES plans(plan_id),
  elevation_name VARCHAR(255) NOT NULL,
  foundation VARCHAR(255),
  heated_sf_inside_studs NUMERIC,
  total_sf_outside_studs NUMERIC
);

-- Create plan_options table  
CREATE TABLE IF NOT EXISTS plan_options (
  plan_option_id SERIAL PRIMARY KEY,
  plan_elevation_id INTEGER REFERENCES plan_elevations(plan_elevation_id),
  option_name VARCHAR(255) NOT NULL,
  option_type VARCHAR(255)
);
