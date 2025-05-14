import pandas as pd
import numpy as np # For NaN and numerical operations
import os

# --- Configuration ---
ALLOWED_UOMS = ['g', 'kg', 'l', 'ml', 'ea']
# Basic conversion factors to a base unit (g for weight, ml for volume)
UOM_CONVERSION_FACTORS_TO_BASE = {
    'g': 1, 'gram': 1, 'grams': 1,
    'kg': 1000, 'kilogram': 1000, 'kilograms': 1000,
    'ml': 1, 'milliliter': 1, 'milliliters': 1,
    'l': 1000, 'liter': 1000, 'liters': 1000,
    'ea': 1 # 'each' is its own base
}
BASE_UNITS = {'weight': 'g', 'volume': 'ml', 'count': 'ea'}

# Thresholds for "unreasonable" recipe ingredient quantities
# These are examples and can be tuned based on typical recipe scales
RECIPE_QTY_MAGNITUDE_THRESHOLDS = {
    'g': 20000,  # e.g., > 20 kg for a single ingredient line entered in grams
    'ml': 20000, 
    'kg': 20,    
    'l': 20,     
    'ea': 200    
}

# --- Helper Functions ---
def clean_text_for_matching(text):
    if pd.isna(text) or not isinstance(text, str):
        return None
    return str(text).strip().lower()

def get_item_details(item_name_cleaned, items_df_cleaned):
    """Fetches details for an item from the cleaned items DataFrame."""
    item_row = items_df_cleaned[items_df_cleaned['cleaned_item_name'] == item_name_cleaned]
    if not item_row.empty:
        return item_row.iloc[0]
    return None

def get_base_unit_and_factor(uom_str):
    """Returns the base unit type (weight, volume, count) and conversion factor."""
    uom_cleaned = clean_text_for_matching(uom_str)
    if uom_cleaned is None:
        return None, None, None

    factor = UOM_CONVERSION_FACTORS_TO_BASE.get(uom_cleaned)
    if factor is None: # Not a directly known UOM for conversion
        return "unknown", None, uom_cleaned

    if uom_cleaned in ['g', 'kg', 'gram', 'grams', 'kilogram', 'kilograms']:
        return BASE_UNITS['weight'], factor, uom_cleaned
    elif uom_cleaned in ['ml', 'l', 'milliliter', 'milliliters', 'liter', 'liters']:
        return BASE_UNITS['volume'], factor, uom_cleaned
    elif uom_cleaned == 'ea':
        return BASE_UNITS['count'], factor, uom_cleaned
    return "unknown", None, uom_cleaned # Should not happen if factor is found

def validate_recipes_data(items_df: pd.DataFrame, recipes_df: pd.DataFrame):
    """
    Validates recipes data for numerical quantities, UOMs, and unreasonable quantity magnitudes.
    """
    if items_df is None or items_df.empty:
        print("Items DataFrame is empty. Cannot perform full validation related to item master.")

        return recipes_df.copy()
    if recipes_df is None or recipes_df.empty:
        print("Recipes DataFrame is empty.")
        return pd.DataFrame()

    recipes_df_validated = recipes_df.copy()

    items_df_cleaned = items_df.copy()
    if 'Item name' not in items_df_cleaned.columns:
        print("Warning: 'Item name' column missing from items data. Cannot perform UOM comparison with item master.")
    else:
        items_df_cleaned['cleaned_item_name'] = items_df_cleaned['Item name'].apply(clean_text_for_matching)

    item_uom_col = 'Item Unit of Measure'
    if item_uom_col not in items_df_cleaned.columns and 'Item name' in items_df_cleaned.columns:
        print(f"Warning: Item UOM column '{item_uom_col}' not found in items data. UOM matching with item master will be affected.")
        items_df_cleaned[item_uom_col] = None # Create dummy if missing to prevent errors later if 'Item name' was present

    ingredient_name_cols = [col for col in recipes_df.columns if col.startswith('Name (Ingredient ')]

    for index, row in recipes_df_validated.iterrows():
        for i in range(1, len(ingredient_name_cols) + 1):
            name_col = f'Name (Ingredient {i})'
            qty_col = f'Qty (Ingredient {i})'
            unit_col = f'Unit (Ingredient {i})'

            qty_status_col = f'Qty_Format_Status (Ingredient {i})'
            uom_status_col = f'UOM_Validation_Status (Ingredient {i})' 
            qty_magnitude_status_col = f'Qty_Magnitude_Status (Ingredient {i})' 

            # Initialize status columns if they don't exist
            if qty_status_col not in recipes_df_validated.columns:
                recipes_df_validated[qty_status_col] = ""
            if uom_status_col not in recipes_df_validated.columns:
                recipes_df_validated[uom_status_col] = ""
            if qty_magnitude_status_col not in recipes_df_validated.columns:
                recipes_df_validated[qty_magnitude_status_col] = ""


            if name_col not in row.index or qty_col not in row.index or unit_col not in row.index:
                continue

            # Get ingredient data from the current row
            ingredient_name = row.get(name_col)
            raw_quantity = row.get(qty_col)
            raw_unit = row.get(unit_col)
            cleaned_ingredient_name = clean_text_for_matching(ingredient_name)

            # --- 1. Validate Quantity Format ---
            numeric_quantity = pd.to_numeric(raw_quantity, errors='coerce')
            current_qty_status = "OK"
            if pd.isna(raw_quantity) or str(raw_quantity).strip() == "":
                if pd.notna(ingredient_name) and str(ingredient_name).strip() != "": # Only flag missing qty if ingredient name exists
                    current_qty_status = "Missing"
                else:
                    current_qty_status = "OK (No Ingredient)" # No ingredient, so missing qty is not an issue
            elif pd.isna(numeric_quantity):
                current_qty_status = "Non-Numeric"
            recipes_df_validated.loc[index, qty_status_col] = current_qty_status

            # --- 2. Validate UOM Format and against Item Master ---
            cleaned_unit = clean_text_for_matching(raw_unit)
            current_uom_status = ""
            if not cleaned_unit:
                if pd.notna(ingredient_name) and str(ingredient_name).strip() != "": # Only flag missing UOM if ingredient name exists
                    current_uom_status = "Missing"
                else:
                    current_uom_status = "OK (No Ingredient)"
            elif cleaned_unit not in ALLOWED_UOMS:
                current_uom_status = f"Invalid UOM ('{raw_unit}')"
            else: # UOM is in allowed list, now check against item master if possible
                current_uom_status = "OK (Format Valid)" # Base status if item master cannot be checked
                if 'Item name' in items_df_cleaned.columns and item_uom_col in items_df_cleaned.columns : # Check if item master check is possible
                    item_details = get_item_details(cleaned_ingredient_name, items_df_cleaned)
                    if item_details is not None:
                        master_uom_raw = item_details.get(item_uom_col)
                        master_uom_cleaned = clean_text_for_matching(master_uom_raw)

                        if not master_uom_cleaned:
                            current_uom_status = "OK (No Master UOM for item)"
                        elif master_uom_cleaned not in ALLOWED_UOMS:
                            current_uom_status = f"OK (Master UOM '{master_uom_raw}' Invalid)"
                        elif cleaned_unit != master_uom_cleaned:
                            recipe_uom_type, _, _ = get_base_unit_and_factor(cleaned_unit)
                            master_uom_type, _, _ = get_base_unit_and_factor(master_uom_cleaned)
                            if recipe_uom_type == master_uom_type and recipe_uom_type not in [None, "unknown"]:
                                current_uom_status = f"OK (Convertible: Recipe '{cleaned_unit}', Item '{master_uom_cleaned}')"
                            else:
                                current_uom_status = f"UOM Mismatch (Recipe: '{cleaned_unit}', Item: '{master_uom_cleaned}')"
                        else: # cleaned_unit == master_uom_cleaned
                            current_uom_status = "OK (Matches Item Master)"
                    else:
                        if cleaned_ingredient_name: # Only flag if ingredient name was present
                            current_uom_status = "Item Not Found in Master"
            recipes_df_validated.loc[index, uom_status_col] = current_uom_status

            # --- 3. Validate Quantity Magnitude ---
            current_qty_magnitude_status = "N/A"
            if current_qty_status == "OK" and pd.notna(numeric_quantity): # Check if quantity is numeric
                if cleaned_unit in RECIPE_QTY_MAGNITUDE_THRESHOLDS: # Check if UOM is one we have a threshold for
                    threshold = RECIPE_QTY_MAGNITUDE_THRESHOLDS[cleaned_unit]
                    if numeric_quantity > threshold:
                        current_qty_magnitude_status = f"Potentially Too Large (>{threshold}{cleaned_unit})"
                    else:
                        current_qty_magnitude_status = "OK"
                elif cleaned_unit and cleaned_unit in ALLOWED_UOMS: # UOM is valid but no specific threshold
                    current_qty_magnitude_status = "OK (No Specific Threshold)"
                elif cleaned_unit: # UOM is present but not in ALLOWED_UOMS
                     current_qty_magnitude_status = "N/A (UOM Invalid)"
                # If cleaned_unit is None/empty, it's handled by uom_status, magnitude remains N/A or set based on Qty
            elif current_qty_status != "OK" and current_qty_status != "OK (No Ingredient)":
                 current_qty_magnitude_status = "N/A (Qty Invalid)"

            recipes_df_validated.loc[index, qty_magnitude_status_col] = current_qty_magnitude_status

    return recipes_df_validated


# --- Main execution block ---
if __name__ == "__main__":
    print(f"Script is running. Current working directory: {os.getcwd()}")

    items_csv_file = os.path.join('data', 'items.csv')
    recipes_csv_file = os.path.join('data', 'recipes.csv')

    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    output_csv_file_path = os.path.join(output_dir, 'recipes_with_qty_uom_validation.csv') # New name

    print(f"Attempting to load items from: {items_csv_file}")
    print(f"Attempting to load recipes from: {recipes_csv_file}")

    try:
        items_df_raw = pd.read_csv(items_csv_file)
    except FileNotFoundError:
        print(f"Error: Items file not found at '{items_csv_file}'. Ensure the file exists in the 'data' directory.")
        items_df_raw = pd.DataFrame() # Create empty df to allow recipe validation to proceed with warnings
        print("Proceeding with recipe validation but UOM comparison with item master will be affected.")
    except Exception as e:
        print(f"Error loading items CSV file '{items_csv_file}': {e}")
        items_df_raw = pd.DataFrame()
        print("Proceeding with recipe validation but UOM comparison with item master will be affected.")


    try:
        recipes_df_raw = pd.read_csv(recipes_csv_file)
    except FileNotFoundError:
        print(f"Error: Recipes file not found at '{recipes_csv_file}'. Ensure the file exists in the 'data' directory.")
        exit()
    except Exception as e:
        print(f"Error loading recipes CSV file '{recipes_csv_file}': {e}")
        exit()

    if recipes_df_raw.empty: # Items_df_raw can be empty if not found, but recipes must exist.
        print("Recipes CSV file is empty. Exiting.")
        exit()

    recipes_validated_df = validate_recipes_data(items_df_raw, recipes_df_raw)

    if not recipes_validated_df.empty:
        try:
            recipes_validated_df.to_csv(output_csv_file_path, index=False)
            print(f"\nValidation complete. Output saved to: {output_csv_file_path}")
            print("The output file contains original recipe data plus new columns like:")
            print("  - 'Qty_Format_Status (Ingredient X)' (OK, Non-Numeric, Missing)")
            print("  - 'UOM_Validation_Status (Ingredient X)' (OK, Invalid UOM, UOM Mismatch, Item Not Found, Missing, etc.)")
            print("  - 'Qty_Magnitude_Status (Ingredient X)' (OK, Potentially Too Large, N/A)")
        except Exception as e:
            print(f"Error saving validated recipes CSV: {e}")
    else:
        print("\nValidation process did not produce an output DataFrame (or it was empty).")

    if not recipes_validated_df.empty:
        print("\n--- Validation Summary (Console) ---")
        for i in range(1, 6): # Example for first 5 ingredients
            qty_fmt_stat_col = f'Qty_Format_Status (Ingredient {i})'
            uom_val_stat_col = f'UOM_Validation_Status (Ingredient {i})'
            qty_mag_stat_col = f'Qty_Magnitude_Status (Ingredient {i})'

            if qty_fmt_stat_col in recipes_validated_df.columns:
                non_numeric_qty = recipes_validated_df[recipes_validated_df[qty_fmt_stat_col] == "Non-Numeric"]
                if not non_numeric_qty.empty:
                    print(f"\nFound {len(non_numeric_qty)} Non-Numeric quantities for Ingredient {i}.")

            if uom_val_stat_col in recipes_validated_df.columns:
                uom_issues = recipes_validated_df[
                    recipes_validated_df[uom_val_stat_col].str.contains("Invalid UOM|Mismatch|Item Not Found", na=False)
                ]
                if not uom_issues.empty:
                    print(f"\nFound {len(uom_issues)} UOM validation issues for Ingredient {i}.")

            if qty_mag_stat_col in recipes_validated_df.columns:
                large_qty = recipes_validated_df[recipes_validated_df[qty_mag_stat_col].str.startswith("Potentially Too Large", na=False)]
                if not large_qty.empty:
                    print(f"\nFound {len(large_qty)} Potentially Too Large quantities for Ingredient {i}.")
    else:
        print("\nNo validated recipes data to summarize for console.")

    print(f"\nReview the generated CSV file '{output_csv_file_path}' for detailed status on each ingredient.")
