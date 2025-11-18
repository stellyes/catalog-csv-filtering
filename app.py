import streamlit as st
import csv
import io
import re

def extract_short_barcodes(barcode_str):
    """Extract 3-4 character alphanumeric entries from barcode string."""
    if not barcode_str or barcode_str.strip() == "":
        return "NULL"
    
    entries = [s.strip() for s in barcode_str.split(',')]
    short_codes = [e for e in entries if len(e) in (3, 4) and e.isalnum()]
    
    return ','.join(short_codes) if short_codes else "NULL"

def extract_long_barcodes(barcode_str):
    """Extract strings longer than 4 characters from barcode string."""
    if not barcode_str or barcode_str.strip() == "":
        return "NULL"
    
    entries = [s.strip() for s in barcode_str.split(',')]
    long_codes = [e for e in entries if len(e) > 4]
    
    return ','.join(long_codes) if long_codes else "NULL"

def format_price(price_str):
    """Format price as dollar value."""
    if not price_str or price_str.strip() == "":
        return "$0.00"
    
    try:
        clean_price = price_str.replace('$', '').strip()
        price_float = float(clean_price)
        return f"${price_float:.2f}"
    except ValueError:
        return "$0.00"

def extract_numeric_with_unit(value_str, unit="mg"):
    """Extract numeric value and append unit."""
    if not value_str or value_str.strip() == "":
        return "N/A"
    
    match = re.search(r'\d+\.?\d*', str(value_str))
    if match:
        return f"{match.group()}{unit}"
    return "N/A"

def format_size(amount, uom):
    """Format size value with unit abbreviations and clean numbers."""
    if uom and not amount:
        return ""
    
    if amount:
        try:
            num = float(amount)
            amount_str = f"{num:g}"
        except (ValueError, TypeError):
            amount_str = str(amount).strip()
    else:
        amount_str = ""
    
    if uom:
        uom = str(uom).strip()
        uom_upper = uom.upper()
        if uom_upper == "MILLIGRAMS":
            uom = "mg"
        elif uom_upper == "GRAMS":
            uom = "g"
    
    return f"{amount_str} {uom}".strip() if (amount_str or uom) else ""

def combine_columns(row, columns, separator=","):
    """Combine multiple column values with separator, skip empty values."""
    values = []
    for col in columns:
        val = row.get(col, "")
        if val is not None:
            val = str(val).strip()
            if val:
                values.append(val)
    return separator.join(values) if values else ""

def normalize_headers(row):
    """Normalize column headers by stripping whitespace, BOM, and extra quotes."""
    normalized = {}
    for key, value in row.items():
        if key:
            clean_key = key.replace('\ufeff', '').strip().strip('"').strip("'")
            normalized[clean_key] = value
    return normalized

def is_url(text):
    """Check if text is a URL."""
    if not text:
        return False
    text = str(text).strip().lower()
    return text.startswith('http://') or text.startswith('https://') or text.startswith('www.')

def is_promo_or_bogo(text):
    """Check if text contains promotional keywords or dollar values."""
    if not text:
        return False
    text = str(text).upper()
    
    if 'PROMO' in text or 'BOGO' in text:
        return True
    
    if '$' in text:
        return True
    
    return False

def transform_row(row):
    """Transform input row to output format with all mappings and conditions."""
    
    menu_title_raw = row.get("Menu Title", "")
    name_raw = row.get("Name", "")
    
    menu_title = str(menu_title_raw).strip() if menu_title_raw else ""
    name = str(name_raw).strip() if name_raw else ""
    
    final_name = menu_title if menu_title else name
    
    if not final_name:
        return None, "Both Menu Title and Name are empty"
    
    if is_url(final_name):
        return None, f"Name is a URL: {final_name}"
    
    if is_promo_or_bogo(final_name):
        return None, f"Name contains promotional keywords: {final_name}"
    
    classification = row.get("Classification", "").strip().lower()
    valid_classifications = ["sativa", "indica", "hybrid", "s/i", "i/s", "cbd"]
    
    if classification == "none":
        classification = ""
    
    if classification and classification not in valid_classifications:
        return None, f"Invalid Classification: '{row.get('Classification', '')}' (must be: sativa, indica, hybrid, s/i, i/s, or cbd)"
    
    category = row.get("Product Type", "").strip()
    
    if not category:
        return None, "Empty Category"
    
    doses = row.get("Doses", "").strip()
    if not doses:
        units_in_package = "1"
    else:
        units_in_package = doses
    
    price_raw = row.get("Price/Tier", "").strip()
    if not price_raw:
        price_raw = "0.01"
    
    needs_thc_cbd = category in ["Edibles", "Topicals", "Tinctures"]
    if needs_thc_cbd:
        thc_value = row.get("Total Mg THC", "").strip()
        cbd_value = row.get("Total Mg CBD", "").strip()
        if not thc_value or not cbd_value:
            return None, f"Missing THC/CBD for {category}"
    
    output = {}
    
    product_id_raw = row.get("Product ID", "")
    
    if product_id_raw is not None and str(product_id_raw).strip() != "":
        output["External ID"] = str(product_id_raw).strip()
    else:
        output["External ID"] = ""
    
    output["Name"] = final_name
    output["Product Type"] = row.get("Subtype", "")
    output["Category"] = category
    output["Subcategory"] = "None"
    output["Brand"] = row.get("Brand", "")
    output["Strain"] = "Undefined"
    output["Strain Prevalence"] = row.get("Classification", "") if classification else ""
    output["Quality Line"] = "Bronze"
    output["Product Description"] = row.get("Description", "")
    output["Instructions"] = "None"
    
    flavors = row.get("Flavors", "")
    if flavors is not None:
        flavors = str(flavors).strip()
    output["Attributes - Flavors"] = flavors if flavors else "None"
    
    output["Scents"] = "N/A"
    
    tags_cols = ["Attributes - General", "Attributes - Effects", 
                 "Attributes - Ingredients", "Attributes - Internal Tags"]
    output["Tags"] = combine_columns(row, tags_cols)
    
    image_cols = ["Image1", "Image2", "Image3", "Image4", 
                  "Image5", "Image6", "Image7", "Image8"]
    output["Images"] = combine_columns(row, image_cols)
    
    output["Former Name"] = "N/A"
    output["Variant Name"] = "N/A"
    
    amount = row.get("Amount", "")
    uom = row.get("UoM", "")
    output["Size"] = format_size(amount, uom)
    
    output["Units in Package"] = units_in_package
    output["Price"] = format_price(price_raw)
    output["Medical Price"] = "N/A"
    
    output["SKU"] = extract_short_barcodes(row.get("Product Barcodes", ""))
    
    output["THC / Unit"] = row.get("Total Mg THC", "")
    output["CBD / Unit"] = row.get("Total Mg CBD", "")
    output["Infused Content"] = "N/A"
    
    output["Strength Level"] = extract_numeric_with_unit(row.get("Mg Per Dose", ""))
    
    output["Sale Type"] = "Medical and Recreational"
    
    output["Barcode"] = extract_long_barcodes(row.get("Product Barcodes", ""))
    
    output["E-Commerce Enabled"] = "True"
    output["Sell By Weight"] = "False"
    
    return output, None

def process_csv(uploaded_file):
    """Process CSV with all transformations and filters."""
    
    output_columns = [
        "External ID", "Name", "Product Type", "Category", "Subcategory",
        "Brand", "Strain", "Strain Prevalence", "Quality Line", "Product Description",
        "Instructions", "Attributes - Flavors", "Scents", "Tags", "Images",
        "Former Name", "Variant Name", "Size", "Units in Package", "Price",
        "Medical Price", "SKU", "THC / Unit", "CBD / Unit", "Infused Content",
        "Strength Level", "Sale Type", "Barcode", "E-Commerce Enabled", "Sell By Weight"
    ]
    
    filtered_rows = []
    skipped_rows = []
    
    seen_product_ids = {}
    seen_duplicates = {}
    
    content = uploaded_file.read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(content))
    
    first_row = None
    row_count = 0
    
    for idx, row in enumerate(reader, start=2):
        row_count += 1
        
        if first_row is None:
            first_row = row
        
        row = normalize_headers(row)
        
        if row_count == 1:
            product_id_debug = row.get("Product ID", "NOT_FOUND")
            st.write(f"DEBUG - First row Product ID: '{product_id_debug}'")
        
        transformed, error = transform_row(row)
        
        if transformed:
            product_id = transformed.get("External ID", "")
            
            if product_id and product_id in seen_product_ids:
                old_idx = seen_product_ids[product_id]
                filtered_rows[old_idx] = transformed
                skipped_rows.append((idx, f"Duplicate Product ID (kept newer): {product_id}", transformed.get("Name", "N/A")))
            else:
                dup_key = (
                    transformed.get("Name", "").strip().lower(),
                    transformed.get("Size", "").strip().lower(),
                    transformed.get("Strain Prevalence", "").strip().lower()
                )
                
                if dup_key in seen_duplicates and dup_key[0]:
                    old_idx = seen_duplicates[dup_key]
                    filtered_rows[old_idx] = transformed
                    skipped_rows.append((idx, f"Likely duplicate (kept newer): {transformed.get('Name', 'N/A')}", transformed.get("Name", "N/A")))
                else:
                    current_idx = len(filtered_rows)
                    filtered_rows.append(transformed)
                    
                    if product_id:
                        seen_product_ids[product_id] = current_idx
                    if dup_key[0]:
                        seen_duplicates[dup_key] = current_idx
        else:
            skipped_rows.append((idx, error, row.get("Menu Title", row.get("Name", "N/A"))))
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=output_columns)
    writer.writeheader()
    writer.writerows(filtered_rows)
    
    available_cols = list(first_row.keys()) if first_row else []
    
    return output.getvalue(), len(filtered_rows), skipped_rows, available_cols

st.set_page_config(page_title="CSV Product Transformer", page_icon="📊", layout="wide")

st.title("🛍️ Product CSV Transformer")
st.markdown("Upload your product CSV file to transform and filter it according to the predefined rules.")

uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'])

if uploaded_file is not None:
    with st.spinner("Processing CSV..."):
        try:
            output_csv, processed_count, skipped_rows, available_cols = process_csv(uploaded_file)
            
            with st.expander("🔍 Debug: Available Columns in Your CSV"):
                st.write("Column names found in your file:")
                for col in available_cols:
                    st.code(f'"{col}"')
            
            if processed_count > 0:
                with st.expander("🔍 Debug: Sample External IDs"):
                    st.write("First few External IDs from output (to verify they're populated):")
                    sample_lines = output_csv.split('\n')[1:6]
                    for i, line in enumerate(sample_lines, 1):
                        if line.strip():
                            external_id = line.split(',')[0] if ',' in line else line[:50]
                            st.code(f"Row {i}: {external_id}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.success(f"✅ Successfully processed {processed_count} rows")
            with col2:
                st.warning(f"⚠️ Skipped {len(skipped_rows)} rows")
            
            if skipped_rows:
                with st.expander(f"View {len(skipped_rows)} skipped rows"):
                    for row_num, reason, title in skipped_rows:
                        st.text(f"Row {row_num}: {title} - {reason}")
            
            st.download_button(
                label="📥 Download Transformed CSV",
                data=output_csv,
                file_name="transformed_products.csv",
                mime="text/csv",
                type="primary"
            )
            
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")
            st.exception(e)

with st.expander("ℹ️ Transformation Rules"):
    st.markdown("""
    ### Column Mappings:
    - Product ID → External ID
    - Menu Title → Name (required, non-empty)
    - Subtype → Product Type
    - Product Type → Category (required)
    - Brand → Brand
    - Classification → Strain Prevalence (must be: sativa, indica, hybrid, s/i, i/s, or cbd)
    
    ### Required Fields:
    - Name (Menu Title)
    - Category (Product Type)
    - Units in Package (Doses) - defaults to 1 if empty
    - Price (Price/Tier) - defaults to $0.01 if empty
    - THC/CBD Units (only for Edibles, Topicals, Tinctures)
    
    ### Filters:
    - Removes products with PROMO, BOGO, or $ in name
    - Removes duplicate Product IDs (keeps latest)
    - Removes likely duplicates (same name, size, classification)
    
    ### Special Transformations:
    - Tags: Combines Attributes columns
    - Images: Combines Image1-Image8
    - Size: Combines Amount + UoM (MILLIGRAMS→mg, GRAMS→g)
    - SKU: 3-4 character barcodes
    - Barcode: Barcodes longer than 4 characters
    - Price: Formatted as dollar values
    """)
