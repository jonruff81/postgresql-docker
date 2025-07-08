#!/usr/bin/env python3
"""
Bulk Product and Vendor Pricing Importer

Usage:
    python3 scripts/bulk_product_vendor_import.py products.csv vendor_pricing.csv

products.csv columns:
    brand, style, color, finish, sku, size, model, material, product_url, notes

vendor_pricing.csv columns:
    sku, vendor_name, price, unit_of_measure

- All products will be attached to item_name "hardwood flooring"
- Each vendor_pricing row attaches a price to a product (by sku) and vendor
"""

import sys
import os
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG_DICT as DB_CONFIG

def get_or_create_item(cursor, item_name):
    cursor.execute("SELECT item_id FROM takeoff.items WHERE item_name = %s", (item_name,))
    row = cursor.fetchone()
    if row:
        return row['item_id']
    cursor.execute("INSERT INTO takeoff.items (item_name) VALUES (%s) RETURNING item_id", (item_name,))
    return cursor.fetchone()['item_id']

def get_or_create_product(cursor, item_id, product_attrs):
    cursor.execute("SELECT product_id FROM takeoff.products WHERE item_id = %s AND model = %s", (item_id, product_attrs['model']))
    row = cursor.fetchone()
    if row:
        return row['product_id']
    cursor.execute("""
        INSERT INTO takeoff.products (item_id, product_description, model)
        VALUES (%s, %s, %s) RETURNING product_id
    """, (item_id, product_attrs['description'], product_attrs['model']))
    return cursor.fetchone()['product_id']

def get_or_create_vendor(cursor, vendor_name):
    cursor.execute("SELECT vendor_id FROM takeoff.vendors WHERE vendor_name = %s", (vendor_name,))
    row = cursor.fetchone()
    if row:
        return row['vendor_id']
    cursor.execute("INSERT INTO takeoff.vendors (vendor_name) VALUES (%s) RETURNING vendor_id", (vendor_name,))
    return cursor.fetchone()['vendor_id']

def add_vendor_pricing(cursor, vendor_id, product_id, price, unit_of_measure):
    # Mark old as not current
    cursor.execute("""
        UPDATE takeoff.vendor_pricing
        SET is_current = FALSE
        WHERE vendor_id = %s AND product_id = %s AND is_current = TRUE
    """, (vendor_id, product_id))
    # Insert new
    cursor.execute("""
        INSERT INTO takeoff.vendor_pricing
        (vendor_id, product_id, price, unit_of_measure, is_current, is_active)
        VALUES (%s, %s, %s, %s, TRUE, TRUE)
    """, (vendor_id, product_id, price, unit_of_measure))

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 scripts/bulk_product_vendor_import.py products.csv vendor_pricing.csv")
        sys.exit(1)
    products_csv = sys.argv[1]
    vendor_pricing_csv = sys.argv[2]

    products_df = pd.read_csv(products_csv)
    vendor_df = pd.read_csv(vendor_pricing_csv)

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    item_id = get_or_create_item(cursor, "hardwood flooring")
    conn.commit()

    # Map SKU to product_id
    sku_to_product_id = {}
    for _, row in products_df.iterrows():
        product_attrs = {
            'description': f"{row['brand']} {row['style']} {row['color']} {row['finish']} {row['size']} {row['model']} {row['material']}",
            'model': row['sku']
        }
        product_id = get_or_create_product(cursor, item_id, product_attrs)
        sku_to_product_id[row['sku']] = product_id
    conn.commit()

    # Add vendor pricing
    for _, row in vendor_df.iterrows():
        sku = row['sku']
        vendor_name = row['vendor_name']
        price = row['price']
        unit_of_measure = row.get('unit_of_measure', 'EA')
        product_id = sku_to_product_id.get(sku)
        if not product_id:
            print(f"Warning: No product found for SKU {sku}")
            continue
        vendor_id = get_or_create_vendor(cursor, vendor_name)
        add_vendor_pricing(cursor, vendor_id, product_id, price, unit_of_measure)
    conn.commit()
    print("Bulk import complete.")

if __name__ == "__main__":
    main()
