import pandas as pd
import numpy as np # For NaN and numerical operations
import os

# --- Configuration ---
ALLOWED_UOMS = ['g', 'kg', 'l', 'ml', 'ea']
# Basic conversion factors to a base unit (g for weight, ml for volume)
# 'ea' is tricky as it doesn't convert universally.
UOM_CONVERSION_FACTORS_TO_BASE = {
    'g': 1, 'gram': 1, 'grams': 1,
    'kg': 1000, 'kilogram': 1000, 'kilograms': 1000,
    'ml': 1, 'milliliter': 1, 'milliliters': 1,
    'l': 1000, 'liter': 1000, 'liters': 1000,
    'ea': 1 # 'each' is its own base, direct comparison or specific logic needed if priced differently
}
BASE_UNITS = {'weight': 'g', 'volume': 'ml', 'count': 'ea'}

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
    Validates recipes data for numerical quantities, UOM, and high costs.

    Args:
        items_df: DataFrame of items.
        recipes_df: DataFrame of recipes.

    Returns:
        A DataFrame (recipes_df_validated) with added validation/status columns.
    """
    if items_df is None or items_df.empty:
        print("Items DataFrame is empty. Cannot perform full validation.")
        return recipes_df.copy() # Return original if no items to check against
    if recipes_df is None or recipes_df.empty:
        print("Recipes DataFrame is empty.")
        return pd.DataFrame()

    recipes_df_validated = recipes_df.copy()

    # Prepare items_df for easier lookup
    items_df_cleaned = items_df.copy()
    if 'Item name' not in items_df_cleaned.columns:
        print("Critical Error: 'Item name' column missing from items data.")
        return recipes_df_validated # Cannot proceed with item-dependent checks
    items_df_cleaned['cleaned_item_name'] = items_df_cleaned['Item name'].apply(clean_text_for_matching)

    # Ensure necessary price and UOM columns exist in items_df
    item_price_col = '€ Price per unit (excluding VAT)'
    item_uom_col = 'Item Unit of Measure'

    if item_price_col not in items_df_cleaned.columns:
        print(f"Warning: Item price column '{item_price_col}' not found in items data. Cost calculations will be affected.")
        items_df_cleaned[item_price_col] = np.nan
    else:
        items_df_cleaned[item_price_col] = pd.to_numeric(
            items_df_cleaned[item_price_col].astype(str).str.replace(',', ''), errors='coerce'
        )

    if item_uom_col not in items_df_cleaned.columns:
        print(f"Warning: Item UOM column '{item_uom_col}' not found in items data. UOM matching will be affected.")
        items_df_cleaned[item_uom_col] = None

    ingredient_name_cols = [col for col in recipes_df.columns if col.startswith('Name (Ingredient ')]
    recipe_total_costs = []

    for index, row in recipes_df_validated.iterrows():
        current_recipe_total_cost = 0
        cost_calculable_for_recipe = False

        for i in range(1, len(ingredient_name_cols) + 1):
            name_col = f'Name (Ingredient {i})'
            qty_col = f'Qty (Ingredient {i})'
            unit_col = f'Unit (Ingredient {i})'

            qty_status_col = f'Qty_Status (Ingredient {i})'
            uom_status_col = f'UOM_Status (Ingredient {i})'
            ing_cost_col = f'Est_Cost (Ingredient {i})'

            if qty_status_col not in recipes_df_validated.columns:
                recipes_df_validated[qty_status_col] = ""
            if uom_status_col not in recipes_df_validated.columns:
                recipes_df_validated[uom_status_col] = ""
            if ing_cost_col not in recipes_df_validated.columns:
                recipes_df_validated[ing_cost_col] = np.nan

            if name_col not in row.index or qty_col not in row.index or unit_col not in row.index:
                continue

            ingredient_name = row.get(name_col)
            raw_quantity = row.get(qty_col)
            raw_unit = row.get(unit_col)
            cleaned_ingredient_name = clean_text_for_matching(ingredient_name)

            numeric_quantity = pd.to_numeric(raw_quantity, errors='coerce')
            if pd.isna(raw_quantity) or str(raw_quantity).strip() == "":
                recipes_df_validated.loc[index, qty_status_col] = "Missing"
            elif pd.isna(numeric_quantity):
                recipes_df_validated.loc[index, qty_status_col] = "Non-Numeric"
            else:
                recipes_df_validated.loc[index, qty_status_col] = "OK"

            cleaned_unit = clean_text_for_matching(raw_unit)
            if not cleaned_unit:
                recipes_df_validated.loc[index, uom_status_col] = "Missing"
            elif cleaned_unit not in ALLOWED_UOMS:
                recipes_df_validated.loc[index, uom_status_col] = "Invalid UOM"
            else:
                item_details = get_item_details(cleaned_ingredient_name, items_df_cleaned)
                if item_details is not None:
                    master_uom_raw = item_details.get(item_uom_col)
                    master_uom_cleaned = clean_text_for_matching(master_uom_raw)

                    if not master_uom_cleaned:
                        recipes_df_validated.loc[index, uom_status_col] = "OK (No Master UOM)"
                    elif master_uom_cleaned not in ALLOWED_UOMS:
                        recipes_df_validated.loc[index, uom_status_col] = "OK (Master UOM Invalid)"
                    elif cleaned_unit != master_uom_cleaned:
                        recipe_uom_type, recipe_factor, _ = get_base_unit_and_factor(cleaned_unit)
                        master_uom_type, master_factor, _ = get_base_unit_and_factor(master_uom_cleaned)
                        if recipe_uom_type == master_uom_type and recipe_uom_type is not None and recipe_uom_type != 'unknown':
                            recipes_df_validated.loc[index, uom_status_col] = "OK (Convertible)"
                        else:
                            recipes_df_validated.loc[index, uom_status_col] = f"UOM Mismatch (Item: {master_uom_cleaned})"
                    else:
                        recipes_df_validated.loc[index, uom_status_col] = "OK"
                else:
                    if cleaned_ingredient_name:
                        recipes_df_validated.loc[index, uom_status_col] = "Item Not Found"

            if pd.notna(numeric_quantity) and cleaned_ingredient_name:
                item_details = get_item_details(cleaned_ingredient_name, items_df_cleaned)
                if item_details is not None and pd.notna(item_details.get(item_price_col)):
                    item_price = item_details[item_price_col]
                    item_master_uom_raw = item_details.get(item_uom_col)
                    recipe_uom_type, recipe_uom_factor, recipe_uom_cleaned = get_base_unit_and_factor(raw_unit)
                    item_master_uom_type, item_master_uom_factor, item_master_uom_cleaned = get_base_unit_and_factor(item_master_uom_raw)

                    if recipe_uom_type != 'unknown' and item_master_uom_type != 'unknown' and \
                       recipe_uom_factor is not None and item_master_uom_factor is not None:
                        if recipe_uom_type == item_master_uom_type:
                            ingredient_cost_this_line = np.nan
                            if item_master_uom_cleaned == recipe_uom_cleaned:
                                ingredient_cost_this_line = numeric_quantity * item_price
                            elif item_master_uom_type in [BASE_UNITS['weight'], BASE_UNITS['volume']]: # Check if types match before division
                                if item_master_uom_factor == 0: # Avoid division by zero
                                     print(f"Warning: item_master_uom_factor is zero for item {cleaned_ingredient_name}, UOM {item_master_uom_cleaned}. Cannot calculate cost.")
                                else:
                                    quantity_in_item_uom = numeric_quantity * (recipe_uom_factor / item_master_uom_factor)
                                    ingredient_cost_this_line = quantity_in_item_uom * item_price
                            elif item_master_uom_type == BASE_UNITS['count'] and recipe_uom_type == BASE_UNITS['count']:
                                pass # Already handled if UOMs are identical

                            if pd.notna(ingredient_cost_this_line):
                                recipes_df_validated.loc[index, ing_cost_col] = ingredient_cost_this_line
                                current_recipe_total_cost += ingredient_cost_this_line
                                cost_calculable_for_recipe = True
        recipe_total_costs.append({'recipe_name': row.get('Menu item name'), 'total_cost': current_recipe_total_cost if cost_calculable_for_recipe else np.nan})

    if recipe_total_costs:
        recipes_df_validated['Calculated_Recipe_Total_Cost'] = [c['total_cost'] for c in recipe_total_costs]
        valid_costs = pd.Series([c['total_cost'] for c in recipe_total_costs]).dropna()
        if not valid_costs.empty:
            mean_cost = valid_costs.mean()
            std_cost = valid_costs.std()
            high_cost_threshold_abs = 500
            high_cost_threshold_std = mean_cost + 3 * std_cost
            if pd.isna(high_cost_threshold_std):
                high_cost_threshold_std = float('inf')

            recipes_df_validated['Recipe_Cost_Warning'] = np.where(
                (recipes_df_validated['Calculated_Recipe_Total_Cost'] > high_cost_threshold_std) |
                (recipes_df_validated['Calculated_Recipe_Total_Cost'] > high_cost_threshold_abs),
                "Potentially High Cost",
                "OK"
            )
            recipes_df_validated.loc[pd.isna(recipes_df_validated['Calculated_Recipe_Total_Cost']), 'Recipe_Cost_Warning'] = "Cost Not Calculated"
        else:
            recipes_df_validated['Recipe_Cost_Warning'] = "Cost Not Calculated"
    return recipes_df_validated

# --- Main execution block ---
if __name__ == "__main__":
    print(f"Script is running. Current working directory: {os.getcwd()}")

    # Define input file paths relative to the project root
    items_csv_file = os.path.join('data', 'items.csv')
    recipes_csv_file = os.path.join('data', 'recipes.csv')

    # Define the output directory and file path
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True) # Create output directory if it doesn't exist
    output_csv_file_path = os.path.join(output_dir, 'recipes_with_validation_flags.csv')

    print(f"Attempting to load items from: {items_csv_file}")
    print(f"Attempting to load recipes from: {recipes_csv_file}")

    try:
        items_df_raw = pd.read_csv(items_csv_file)
        recipes_df_raw = pd.read_csv(recipes_csv_file)
    except FileNotFoundError:
        print(f"Error: Ensure '{items_csv_file}' and '{recipes_csv_file}' are in your current working directory or provide full paths.")
        exit()
    except Exception as e:
        print(f"Error loading CSV files: {e}")
        exit()

    if items_df_raw.empty or recipes_df_raw.empty:
        print("One or both input CSV files are empty. Exiting.")
        exit()

    recipes_validated_df = validate_recipes_data(items_df_raw, recipes_df_raw)

    if not recipes_validated_df.empty:
        try:
            recipes_validated_df.to_csv(output_csv_file_path, index=False)
            print(f"\nValidation complete. Output saved to: {output_csv_file_path}")
            print("The output file contains original recipe data plus new columns like:")
            print("  - 'Qty_Status (Ingredient X)' (OK, Non-Numeric, Missing)")
            print("  - 'UOM_Status (Ingredient X)' (OK, Invalid UOM, UOM Mismatch, Item Not Found, Missing)")
            print("  - 'Est_Cost (Ingredient X)' (Estimated cost for the ingredient line)")
            print("  - 'Calculated_Recipe_Total_Cost' (Sum of estimated ingredient costs for the recipe row)")
            print("  - 'Recipe_Cost_Warning' (Potentially High Cost, OK, Cost Not Calculated)")
        except Exception as e:
            print(f"Error saving validated recipes CSV: {e}")
    else:
        print("\nValidation process did not produce an output DataFrame (or it was empty).")

    # --- Print summary of issues found in the console ---
    if not recipes_validated_df.empty: # Ensure dataframe exists before trying to access columns
        print("\n--- Validation Summary (Console) ---")
        for i in range(1, 6): # Check for first 5 ingredients as an example
            qty_stat_col = f'Qty_Status (Ingredient {i})'
            uom_stat_col = f'UOM_Status (Ingredient {i})'
            if qty_stat_col in recipes_validated_df.columns:
                non_numeric_qty = recipes_validated_df[recipes_validated_df[qty_stat_col] == "Non-Numeric"]
                if not non_numeric_qty.empty:
                    print(f"\nFound {len(non_numeric_qty)} non-numeric quantities for Ingredient {i}.")
                    # print(non_numeric_qty[['Menu item name', f'Name (Ingredient {i})', f'Qty (Ingredient {i})']].head())

            if uom_stat_col in recipes_validated_df.columns:
                # Adjusted to check for specific issue strings
                uom_issues = recipes_validated_df[
                    recipes_validated_df[uom_stat_col].isin(["Invalid UOM", "UOM Mismatch (Item: Invalid UOM)", "Item Not Found"]) |
                    recipes_validated_df[uom_stat_col].str.contains("UOM Mismatch", na=False)
                ]
                if not uom_issues.empty:
                    print(f"\nFound {len(uom_issues)} UOM issues for Ingredient {i}.")
                    # print(uom_issues[['Menu item name', f'Name (Ingredient {i})', f'Unit (Ingredient {i})', uom_stat_col]].head())

        if 'Recipe_Cost_Warning' in recipes_validated_df.columns:
            high_cost_recipes = recipes_validated_df[recipes_validated_df['Recipe_Cost_Warning'] == "Potentially High Cost"]
            if not high_cost_recipes.empty:
                print(f"\nFound {len(high_cost_recipes)} recipes with potentially high costs.")
                # print(high_cost_recipes[['Menu item name', 'Calculated_Recipe_Total_Cost']].head())
    else:
        print("\nNo validated recipes data to summarize.")

    print(f"\nReview the generated CSV file '{output_csv_file_path}' for detailed status on each ingredient.")
