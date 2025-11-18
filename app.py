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
    # If UoM is not empty but Amount is, leave blank
    if uom and not amount:
        return ""
    
    # Clean the amount - remove trailing zeros and decimal points
    if amount:
        try:
            num = float(amount)
            # Format without trailing zeros
            amount_str = f"{num:g}"
        except (ValueError, TypeError):
            amount_str = str(amount).strip()
    else:
        amount_str = ""
    
    # Abbreviate units
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
        # Convert to string if not already
        if val is not None:
            val = str(val).strip()
            if val:
                values.append(val)
    return separator.join(values) if values else ""
    """Combine multiple column values with separator, skip empty values."""
    values = []
    for col in columns:
        val = row.get(col, "")
        # Convert to string if not already
        if val is not None:
            val = str(val).strip()
            if val:
                values.append(val)
    return separator.join(values) if values else ""

def is_url(text):
    """Check if text is a URL."""
    if not text:
        return False
    text = str(text).strip().lower()
    return text.startswith('http://') or text.startswith('https://') or text.startswith('www.')

def transform_row(row):
    """Transform input row to output format with all mappings and conditions."""
    
    # Check Menu Title OR Name (use whichever is populated)
    menu_title_raw = row.get("Menu Title", "")
    name_raw = row.get("Name", "")
    
    # Convert to strings and strip
    menu_title = str(menu_title_raw).strip() if menu_title_raw else ""
    name = str(name_raw).strip() if name_raw else ""
    
    # Use Menu Title if available, otherwise use Name
    final_name = menu_title if menu_title else name
    
    if not final_name:
        return None, f"Both Menu Title and Name are empty"
    
    # Check if name is a URL
    if is_url(final_name):
        return None, f"Name is a URL: {final_name}"
    
    # Check Classification validity (input column is "Classification", output is "Strain Prevalence")
    classification = row.get("Classification", "").strip().lower()
    valid_classifications = ["sativa", "indica", "hybrid", "s/i", "i/s", "cbd"]
    
    # Handle "NONE" classification - set to empty string
    if classification == "none":
        classification = ""
    
    # Allow empty classification ONLY if we have a valid (non-URL) product name
    # If classification exists but is invalid, reject the row
    if classification and classification not in valid_classifications:
        return None, f"Invalid Classification: '{row.get('Classification', '')}' (must be: sativa, indica, hybrid, s/i, i/s, or cbd)"
    
    # Get Category for conditional checks
    category = row.get("Product Type", "").strip()
    
    # Check required fields
    if not category:
        return None, "Empty Category"
    
    # Units in Package (from Doses) - if empty, set to 1
    doses = row.get("Doses", "").strip()
    if not doses:
        units_in_package = "1"
    else:
        units_in_package = doses
    
    # Price check - if empty, set to $0.01
    price_raw = row.get("Price/Tier", "").strip()
    if not price_raw:
        price_raw = "0.01"
    
    # THC/CBD checks for specific categories
    needs_thc_cbd = category in ["Edibles", "Topicals", "Tinctures"]
    if needs_thc_cbd:
        thc_value = row.get("Total Mg THC", "").strip()
        cbd_value = row.get("Total Mg CBD", "").strip()
        if not thc_value or not cbd_value:
            return None, f"Missing THC/CBD for {category}"
    
    # Build output row
    output = {}
    
    # Debug: Check what we're getting for Product ID
    product_id_raw = row.get("Product ID", "")
    
    # Make sure Product ID is converted to string and stripped
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
    # Use original classification value from input, or empty string if it was "none"
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
    
    # Use new format_size function
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

def normalize_headers(row):
    """Normalize column headers by stripping whitespace and handling BOM."""
    normalized = {}
    for key, value in row.items():
        if key:
            # Remove BOM and strip whitespace
            clean_key = key.replace('\ufeff', '').strip()
            normalized[clean_key] = value
    return normalized

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
    
    # Read uploaded file
    content = uploaded_file.read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(content))
    
    # Show available columns for debugging
    first_row = None
    row_count = 0
    
    for idx, row in enumerate(reader, start=2):  # Start at 2 (row 1 is header)
        row_count += 1
        
        if first_row is None:
            first_row = row
        
        # Normalize column names
        row = normalize_headers(row)
        
        # Debug first row to see Product ID
        if row_count == 1:
            product_id_debug = row.get("Product ID", "NOT_FOUND")
            st.write(f"DEBUG - First row Product ID: '{product_id_debug}'")
        
        transformed, error = transform_row(row)
        if transformed:
            filtered_rows.append(transformed)
        else:
            skipped_rows.append((idx, error, row.get("Menu Title", row.get("Name", "N/A"))))
    
    # Create output CSV in memory
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=output_columns)
    writer.writeheader()
    writer.writerows(filtered_rows)
    
    # Return available columns from first row for debugging
    available_cols = list(first_row.keys()) if first_row else []
    
    return output.getvalue(), len(filtered_rows), skipped_rows, available_cols

# Streamlit UI
st.set_page_config(page_title="CSV Product Transformer", page_icon="📊", layout="wide")

st.title("🛍️ Product CSV Transformer")
st.markdown("Upload your product CSV file to transform and filter it according to the predefined rules.")

# File uploader
uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'])

if uploaded_file is not None:
    with st.spinner("Processing CSV..."):
        try:
            output_csv, processed_count, skipped_rows, available_cols = process_csv(uploaded_file)
            
            # Display available columns for debugging
            with st.expander("🔍 Debug: Available Columns in Your CSV"):
                st.write("Column names found in your file:")
                for col in available_cols:
                    st.code(f'"{col}"')
            
            # Show sample of first few External IDs
            if processed_count > 0:
                with st.expander("🔍 Debug: Sample External IDs"):
                    st.write("First few External IDs from output (to verify they're populated):")
                    sample_lines = output_csv.split('\n')[1:6]  # Skip header, show first 5 rows
                    for i, line in enumerate(sample_lines, 1):
                        if line.strip():
                            external_id = line.split(',')[0] if ',' in line else line[:50]
                            st.code(f"Row {i}: {external_id}")
            
            # Display results
            col1, col2 = st.columns(2)
            with col1:
                st.success(f"✅ Successfully processed {processed_count} rows")
            with col2:
                st.warning(f"⚠️ Skipped {len(skipped_rows)} rows")
            
            # Show skipped rows if any
            if skipped_rows:
                with st.expander(f"View {len(skipped_rows)} skipped rows"):
                    for row_num, reason, title in skipped_rows:
                        st.text(f"Row {row_num}: {title} - {reason}")
            
            # Download button
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

# Instructions
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
    - Units in Package (Doses)
    - Price (Price/Tier)
    - THC/CBD Units (only for Edibles, Topicals, Tinctures)
    
    ### Special Transformations:
    - Tags: Combines Attributes columns
    - Images: Combines Image1-Image8
    - Size: Combines Amount + UoM
    - SKU: 3-4 character barcodes
    - Barcode: Barcodes longer than 4 characters
    - Price: Formatted as dollar values
    """)
