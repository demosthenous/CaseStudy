import pandas as pd
import numpy as np
import os
from fuzzywuzzy import process, fuzz # For identifying potential duplicates

# --- Configuration ---
ALLOWED_UOMS = ['g', 'kg', 'l', 'ml', 'ea']
# Columns to check for missing data
MISSING_CHECK_COLS = ['Item size', 'Item Unit of Measure', '€ Price per unit (excluding VAT)', 'Tax rate', 'Supplier code']
# Columns to check for numerical data (after cleaning)
# Status column name is the value
NUMERICAL_CHECK_COLS_CONFIG = {
    'Item size': 'Size_Status',
    '€ Price per unit (excluding VAT)': 'Price_Status',
    'Tax rate': 'Tax_Rate_Status',
    'Supplier code': 'Supplier_Code_Status'
}
# Column for UOM validation
UOM_COL = 'Item Unit of Measure'
# Column for item name (used for duplicate check)
ITEM_NAME_COL = 'Item name'
SUPPLIER_COL = 'Supplier'
PRICE_COL = '€ Price per unit (excluding VAT)'
ITEM_SIZE_COL = 'Item size'

# Fuzzy matching threshold for names
DUPLICATE_NAME_THRESHOLD = 85
# Tolerances for numeric comparisons in duplicate check
SIZE_TOLERANCE_PERCENT = 0.01
PRICE_TOLERANCE_PERCENT = 0.01

# Thresholds for "unreasonable" size magnitudes
SIZE_MAGNITUDE_THRESHOLDS = {
    'g': 10000,  # e.g., > 10 kg entered as grams
    'ml': 10000, # e.g., > 10 L entered as ml
    'kg': 100,   # e.g., > 100 kg for a single item
    'l': 100,    # e.g., > 100 L for a single item
    'ea': 1000   # e.g., > 1000 "each" (can be adjusted based on typical pack sizes)
}

# --- Helper Functions ---
def clean_text_for_matching(text):
    if pd.isna(text) or not isinstance(text, str):
        return None
    return str(text).strip().lower()

def clean_percentage(value):
    if pd.isna(value):
        return np.nan
    try:
        return pd.to_numeric(str(value).replace('%', '')) / 100.0
    except (ValueError, TypeError):
        return np.nan

def clean_numeric(value, is_supplier_code=False):
    if pd.isna(value):
        return np.nan
    cleaned_value_str = str(value).strip()
    if is_supplier_code:
        # For supplier codes, allow only digits after stripping.
        # If it's meant to be purely numeric for calculations, this might change.
        # If it can have leading zeros and is an identifier, string type is fine.
        # This implementation checks if it's all digits, then returns as string.
        # If it should be an int, convert with pd.to_numeric after isdigit() check.
        return cleaned_value_str if cleaned_value_str.isdigit() else np.nan # Returns string if all digits, else NaN
    else:
        try:
            return pd.to_numeric(cleaned_value_str.replace(',', ''))
        except (ValueError, TypeError):
            return np.nan

def validate_items_data(items_df: pd.DataFrame):
    """
    Validates items data for missing fields, non-numerical values, UOM, size magnitude, and duplicates.
    """
    if items_df is None or items_df.empty:
        print("Items DataFrame is empty.")
        return pd.DataFrame()

    items_df_validated = items_df.copy()

    # --- Create cleaned/numeric versions of columns for internal use ---
    # Use .get() with a default pd.Series to prevent KeyError if a column is missing
    items_df_validated['cleaned_item_name'] = items_df_validated.get(ITEM_NAME_COL, pd.Series(dtype='object')).apply(clean_text_for_matching)
    items_df_validated['cleaned_supplier'] = items_df_validated.get(SUPPLIER_COL, pd.Series(dtype='object')).apply(clean_text_for_matching)
    items_df_validated['numeric_item_size'] = items_df_validated.get(ITEM_SIZE_COL, pd.Series(dtype='object')).apply(lambda x: clean_numeric(x, is_supplier_code=False))
    items_df_validated['numeric_price'] = items_df_validated.get(PRICE_COL, pd.Series(dtype='object')).apply(lambda x: clean_numeric(x, is_supplier_code=False))
    items_df_validated['numeric_tax_rate'] = items_df_validated.get('Tax rate', pd.Series(dtype='object')).apply(clean_percentage)
    items_df_validated['cleaned_supplier_code_str'] = items_df_validated.get('Supplier code', pd.Series(dtype='object')).apply(lambda x: clean_numeric(x, is_supplier_code=True)) # Kept as string
    items_df_validated['cleaned_uom'] = items_df_validated.get(UOM_COL, pd.Series(dtype='object')).apply(clean_text_for_matching)


    # --- 1. Missing Data Check ---
    print("Checking for missing data...")
    missing_flags = []
    for index, row in items_df_validated.iterrows():
        missing_cols_for_row = []
        for col in MISSING_CHECK_COLS:
            if col not in row.index or pd.isna(row[col]) or str(row[col]).strip() == "":
                missing_cols_for_row.append(col)
        missing_flags.append(f"Missing: {', '.join(missing_cols_for_row)}" if missing_cols_for_row else "OK")
    items_df_validated['Missing_Data_Flag'] = missing_flags
    print(f"Found {sum(1 for flag in missing_flags if flag != 'OK')} rows with missing data in key columns.")

    # --- 2. Numerical Validation ---
    print("Validating numerical fields...")
    for col_original, status_col_name in NUMERICAL_CHECK_COLS_CONFIG.items():
        if col_original not in items_df_validated.columns:
            items_df_validated[status_col_name] = "Column Missing"
            print(f"Warning: Numerical check column '{col_original}' not found.")
            continue

        numeric_series_to_check = None
        if col_original == ITEM_SIZE_COL: numeric_series_to_check = items_df_validated['numeric_item_size']
        elif col_original == PRICE_COL: numeric_series_to_check = items_df_validated['numeric_price']
        elif col_original == 'Tax rate': numeric_series_to_check = items_df_validated['numeric_tax_rate']
        elif col_original == 'Supplier code': numeric_series_to_check = items_df_validated['cleaned_supplier_code_str'] # Using the string version for check

        statuses = ["Check Error"] * len(items_df_validated) # Default
        if numeric_series_to_check is not None:
            for i, original_value in enumerate(items_df_validated[col_original]):
                if pd.isna(original_value) or str(original_value).strip() == "":
                    statuses[i] = "Missing"
                # For supplier code, numeric_series_to_check contains strings or NaN.
                # If it's NaN here, it means clean_numeric(is_supplier_code=True) returned NaN, indicating non-digit.
                elif pd.isna(numeric_series_to_check.iloc[i]):
                    statuses[i] = "Non-Numeric/Invalid Format" # More specific for supplier code
                else:
                    statuses[i] = "OK"
        items_df_validated[status_col_name] = statuses
        print(f"Found {statuses.count('Non-Numeric/Invalid Format')} non-numeric/invalid values in column '{col_original}'.")


    # --- 3. UOM Validation ---
    print("Validating Unit of Measure...")
    if UOM_COL not in items_df_validated.columns:
        items_df_validated['UOM_Status'] = "Column Missing"
        print(f"Warning: UOM column '{UOM_COL}' not found.")
    else:
        items_df_validated['UOM_Status'] = items_df_validated['cleaned_uom'].apply(
            lambda uom: "Missing" if not uom else ("Invalid UOM" if uom not in ALLOWED_UOMS else "OK")
        )
        print(f"Found {items_df_validated['UOM_Status'].tolist().count('Invalid UOM')} invalid UOMs.")

    # --- 3.5 Size Magnitude Check ---
    print("Checking for unreasonable size magnitudes...")
    size_magnitude_flags = []
    if 'numeric_item_size' in items_df_validated.columns and \
       'cleaned_uom' in items_df_validated.columns and \
       'Size_Status' in items_df_validated.columns:
        for index, row in items_df_validated.iterrows():
            numeric_size = row['numeric_item_size']
            cleaned_uom = row['cleaned_uom']
            size_status = row.get('Size_Status', 'OK')

            if size_status == "OK" and pd.notna(cleaned_uom) and cleaned_uom in SIZE_MAGNITUDE_THRESHOLDS and pd.notna(numeric_size) :
                if numeric_size > SIZE_MAGNITUDE_THRESHOLDS[cleaned_uom]:
                    size_magnitude_flags.append(f"Potentially Too Large (>{SIZE_MAGNITUDE_THRESHOLDS[cleaned_uom]}{cleaned_uom})")
                else:
                    size_magnitude_flags.append("OK")
            elif size_status != "OK" or pd.isna(cleaned_uom) or pd.isna(numeric_size):
                size_magnitude_flags.append("N/A (Size/UOM Invalid or Missing)")
            else: # UOM is valid but not in our threshold dict
                size_magnitude_flags.append("N/A (UOM not in threshold check)")
        items_df_validated['Size_Magnitude_Flag'] = size_magnitude_flags
        print(f"Found {sum(1 for flag in size_magnitude_flags if flag.startswith('Potentially Too Large'))} items with potentially too large sizes.")
    else:
        items_df_validated['Size_Magnitude_Flag'] = "N/A (Required columns missing for check)"
        print("Skipped Size Magnitude Check due to missing required columns (numeric_item_size, cleaned_uom, or Size_Status).")


    # --- 4. Duplicate Check ---
    print("Checking for potential duplicate items (enhanced)...")
    if ITEM_NAME_COL not in items_df_validated.columns:
        items_df_validated['Potential_Duplicates_Info'] = "Name Column Missing"
    else:
        potential_duplicates_info_map = {}
        all_items_tuples = [(idx, name) for idx, name in items_df_validated['cleaned_item_name'].items() if pd.notna(name)]

        for current_idx, current_row in items_df_validated.iterrows():
            current_cleaned_name = current_row['cleaned_item_name']
            if pd.isna(current_cleaned_name):
                continue

            candidate_tuples_for_fuzz = [(name, idx) for idx, name in all_items_tuples if idx != current_idx]
            if not candidate_tuples_for_fuzz:
                continue

            candidate_names = [name for name, idx in candidate_tuples_for_fuzz]

            fuzzy_name_matches = process.extract(current_cleaned_name, candidate_names,
                                                 scorer=fuzz.token_sort_ratio, limit=5)
            found_duplicates_details = []
            processed_match_indices_for_current = set()

            for matched_name_str, name_score in fuzzy_name_matches:
                if name_score >= DUPLICATE_NAME_THRESHOLD:
                    indices_for_this_matched_name = [idx for name, idx in candidate_tuples_for_fuzz if name == matched_name_str]

                    for matched_idx in indices_for_this_matched_name:
                        if matched_idx in processed_match_indices_for_current:
                            continue
                        processed_match_indices_for_current.add(matched_idx)

                        matched_row = items_df_validated.loc[matched_idx]

                        details = [f"Idx:{matched_idx}", f"NameScore:{name_score}"]

                        # Supplier
                        if pd.notna(current_row['cleaned_supplier']) and pd.notna(matched_row['cleaned_supplier']) and \
                           current_row['cleaned_supplier'] == matched_row['cleaned_supplier']:
                            details.append("SupMatch:Y")
                        elif pd.notna(current_row['cleaned_supplier']) or pd.notna(matched_row['cleaned_supplier']):
                            details.append("SupMatch:N")

                        # Size
                        current_size, matched_size = current_row['numeric_item_size'], matched_row['numeric_item_size']
                        if pd.notna(current_size) and pd.notna(matched_size):
                            if current_size == 0 and matched_size == 0:
                                details.append("SizeMatch:Y (Both 0)")
                            elif max(abs(current_size), abs(matched_size)) == 0 :
                                 details.append("SizeMatch:N (Zero involved or non-comparable)") # Should ideally not happen if both are numbers and one non-zero
                            elif abs(current_size - matched_size) <= (SIZE_TOLERANCE_PERCENT * max(abs(current_size), abs(matched_size)) if max(abs(current_size), abs(matched_size)) != 0 else 0) :
                                details.append("SizeMatch:Y")
                            else:
                                details.append("SizeMatch:N")
                        elif pd.notna(current_size) or pd.notna(matched_size):
                            details.append("SizeMatch:Partial")

                        # Price
                        current_price, matched_price = current_row['numeric_price'], matched_row['numeric_price']
                        if pd.notna(current_price) and pd.notna(matched_price):
                            if current_price == 0 and matched_price == 0:
                                details.append("PriceMatch:Y (Both 0)")
                            elif max(abs(current_price), abs(matched_price)) == 0:
                                details.append("PriceMatch:N (Zero involved or non-comparable)")
                            elif abs(current_price - matched_price) <= (PRICE_TOLERANCE_PERCENT * max(abs(current_price), abs(matched_price)) if max(abs(current_price), abs(matched_price)) != 0 else 0) :
                                details.append("PriceMatch:Y")
                            else:
                                details.append("PriceMatch:N")
                        elif pd.notna(current_price) or pd.notna(matched_price):
                            details.append("PriceMatch:Partial")

                        found_duplicates_details.append(f"Item:'{matched_row.get(ITEM_NAME_COL, 'N/A')}' ({','.join(details)})")

            if found_duplicates_details:
                potential_duplicates_info_map[current_idx] = " | ".join(found_duplicates_details)

        items_df_validated['Potential_Duplicates_Info'] = items_df_validated.index.map(potential_duplicates_info_map).fillna("None")
        print(f"Flagged {len(potential_duplicates_info_map)} rows with potential duplicates based on enhanced criteria.")

    # Drop intermediate helper columns before returning
    helper_cols_to_drop = ['cleaned_item_name', 'cleaned_supplier',
                           'numeric_item_size', 'numeric_price',
                           'numeric_tax_rate', 'cleaned_supplier_code_str', 'cleaned_uom'] # updated supplier code col name
    items_df_validated.drop(columns=[col for col in helper_cols_to_drop if col in items_df_validated.columns], inplace=True, errors='ignore')
    return items_df_validated

# --- Main execution block ---
if __name__ == "__main__":
    print(f"Script is running. Current working directory: {os.getcwd()}")

    # Define input file path relative to the project root
    items_csv_file_path = os.path.join('data', 'items.csv')

    # Define the output directory and file path
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True) # Create output directory if it doesn't exist
    output_csv_file_path = os.path.join(output_dir, 'items_with_validation_flags.csv')

    print(f"Attempting to load items from: {items_csv_file_path}")

    try:
        items_df_raw = pd.read_csv(items_csv_file_path)
    except FileNotFoundError:
        print(f"Error: Ensure '{items_csv_file_path}' exists. Searched in '{os.path.abspath(items_csv_file_path)}'")
        exit()
    except Exception as e:
        print(f"Error loading CSV file '{items_csv_file_path}': {e}")
        exit()

    if items_df_raw.empty:
        print(f"Input items CSV file '{items_csv_file_path}' is empty. Exiting.")
        exit()

    items_validated_df = validate_items_data(items_df_raw.copy()) # Pass a copy to avoid modifying original df in unexpected ways

    if not items_validated_df.empty:
        try:
            # Reorder columns to put flags near the end for better readability
            status_cols_ordered = [
                'Missing_Data_Flag', 'Size_Status', 'Price_Status',
                'Tax_Rate_Status', 'Supplier_Code_Status', 'UOM_Status',
                'Size_Magnitude_Flag',
                'Potential_Duplicates_Info'
            ]
            # Get original columns that still exist in the validated DataFrame
            original_cols = [col for col in items_df_raw.columns if col in items_validated_df.columns]

            # Get status columns that were actually created
            final_status_cols = [col for col in status_cols_ordered if col in items_validated_df.columns]

            # Combine original columns and status columns, avoiding duplicates
            # Ensure original columns come first, then status columns not already in original
            final_cols_order = original_cols + [col for col in final_status_cols if col not in original_cols]

            # Add any other newly created columns that are not in original_cols or final_status_cols
            # (e.g. if a new helper column was accidentally not dropped)
            other_new_cols = [col for col in items_validated_df.columns if col not in final_cols_order]
            final_cols_order.extend(other_new_cols)
            
            # Ensure all columns in final_cols_order exist in items_validated_df to prevent KeyError
            final_cols_order = [col for col in final_cols_order if col in items_validated_df.columns]


            items_validated_df = items_validated_df[final_cols_order]
            items_validated_df.to_csv(output_csv_file_path, index=False)
            print(f"\nValidation complete. Output saved to: {output_csv_file_path}")
        except Exception as e:
            print(f"Error saving validated items CSV to '{output_csv_file_path}': {e}")
    else:
        print("\nValidation process did not produce an output DataFrame.")

    # --- Print a summary of rows with issues ---
    if not items_validated_df.empty:
        print("\n--- Validation Summary (Console) ---")
        filter_conditions = []
        # Safely add conditions only if the column exists
        if 'Missing_Data_Flag' in items_validated_df: filter_conditions.append(items_validated_df['Missing_Data_Flag'] != "OK")
        if 'Size_Status' in items_validated_df: filter_conditions.append(items_validated_df['Size_Status'] == "Non-Numeric/Invalid Format")
        if 'Price_Status' in items_validated_df: filter_conditions.append(items_validated_df['Price_Status'] == "Non-Numeric/Invalid Format")
        if 'Tax_Rate_Status' in items_validated_df: filter_conditions.append(items_validated_df['Tax_Rate_Status'] == "Non-Numeric/Invalid Format")
        if 'Supplier_Code_Status' in items_validated_df: filter_conditions.append(items_validated_df['Supplier_Code_Status'] == "Non-Numeric/Invalid Format")
        if 'UOM_Status' in items_validated_df: filter_conditions.append(items_validated_df['UOM_Status'] == "Invalid UOM")
        if 'Size_Magnitude_Flag' in items_validated_df: filter_conditions.append(items_validated_df['Size_Magnitude_Flag'].str.startswith("Potentially Too Large", na=False))
        if 'Potential_Duplicates_Info' in items_validated_df: filter_conditions.append(items_validated_df['Potential_Duplicates_Info'] != "None")

        if filter_conditions: # Check if any conditions were added
            issues_df = items_validated_df[np.logical_or.reduce(filter_conditions)]
            if not issues_df.empty:
                print(f"Found {len(issues_df)} rows with potential issues.")
                print("Example rows with issues (showing key columns and flags):")
                cols_to_show_base = [ITEM_NAME_COL, SUPPLIER_COL, ITEM_SIZE_COL, PRICE_COL, 'Supplier code', UOM_COL]
                # Use the status_cols_ordered from above, as it defines the desired order and existence
                cols_to_show_status_actual = [col for col in status_cols_ordered if col in issues_df.columns]
                
                final_cols_to_show = [col for col in cols_to_show_base if col in issues_df.columns] + \
                                     cols_to_show_status_actual
                # Remove duplicates if any base columns are also status columns (unlikely here but good practice)
                final_cols_to_show = sorted(list(set(final_cols_to_show)), key=final_cols_to_show.index)
                
                print(issues_df[final_cols_to_show].head(10))
            else:
                print("No major validation issues flagged by the script based on the defined criteria.")
        else:
            print("No filter conditions available for issues summary (columns might be missing).")
    else:
        print("\nNo validated items data to summarize.")

    print(f"\nReview '{output_csv_file_path}' for detailed flags on all items.")
