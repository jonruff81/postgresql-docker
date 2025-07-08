-- Migration 029: Trigger to auto-populate item_description in products table
-- This trigger sets item_description based on item_type:
-- - For 'Product': item_name from items table
-- - For 'Quote': 'Quote_' + plan_full_name + option_name (joins plan_options and plan_elevations), or 'Quote' if plan_option_id is NULL
-- - For 'Attribute': brand_style_color_finish_sku_size (concatenated with underscores)

CREATE OR REPLACE FUNCTION takeoff.set_item_description_from_item_name()
RETURNS TRIGGER AS $$
DECLARE
    v_item_name text;
    v_plan_full_name text;
    v_option_name text;
BEGIN
    IF NEW.item_type = 'Product' THEN
        SELECT i.item_name INTO v_item_name
        FROM takeoff.items i
        WHERE i.item_id = NEW.item_id;
        NEW.item_description := v_item_name;
    ELSIF NEW.item_type = 'Quote' THEN
        IF NEW.plan_option_id IS NOT NULL THEN
            SELECT pe.plan_full_name, po.option_name
            INTO v_plan_full_name, v_option_name
            FROM takeoff.plan_options po
            JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
            WHERE po.plan_option_id = NEW.plan_option_id;
            NEW.item_description := 'Quote_' || COALESCE(v_plan_full_name, '') || COALESCE(v_option_name, '');
        ELSE
            NEW.item_description := 'Quote';
        END IF;
    ELSIF NEW.item_type = 'Attribute' THEN
        NEW.item_description := 
            COALESCE(NEW.brand, '') || '_' ||
            COALESCE(NEW.style, '') || '_' ||
            COALESCE(NEW.color, '') || '_' ||
            COALESCE(NEW.finish, '') || '_' ||
            COALESCE(NEW.sku, '') || '_' ||
            COALESCE(NEW.size, '');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_set_item_description_from_item_name ON takeoff.products;

CREATE TRIGGER trg_set_item_description_from_item_name
BEFORE INSERT OR UPDATE ON takeoff.products
FOR EACH ROW
EXECUTE FUNCTION takeoff.set_item_description_from_item_name();
