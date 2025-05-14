import pandas as pd
# import io # Not strictly needed if always reading from files
import os

def find_missing_recipe_items_from_files(items_file_path: str, recipes_file_path: str):
    """
    Identifies items listed in recipes that are not found in the items list,
    reading data directly from CSV files. It also returns the recipes DataFrame
    augmented with status columns for each ingredient.

    Args:
        items_file_path: Path to the items CSV file.
        recipes_file_path: Path to the recipes CSV file.

    Returns:
        A tuple: (missing_ingredients_report, recipes_df_augmented).
        - missing_ingredients_report: A list of dictionaries, where each dictionary contains
          'recipe_name', 'missing_ingredient_name', 'cleaned_missing_ingredient_name', and 'ingredient_column'.
        - recipes_df_augmented: The recipes DataFrame with added status columns.
        Returns (list_with_error_dict, pd.DataFrame()) if file reading fails or critical columns are missing.
    """

    # --- Load Data into Pandas DataFrames from files ---
    try:
        items_df = pd.read_csv(items_file_path)
        recipes_df = pd.read_csv(recipes_file_path)
    except FileNotFoundError:
        error_msg = f"Error: One or both files not found. Searched for '{items_file_path}' and '{recipes_file_path}'."
        print(error_msg)
        return [{"error": error_msg}], pd.DataFrame()
    except pd.errors.EmptyDataError:
        error_msg = "Error: One or both CSV files are empty."
        print(error_msg)
        return [{"error": error_msg}], pd.DataFrame()
    except Exception as e:
        error_msg = f"Error reading CSV files: {e}"
        print(error_msg)
        return [{"error": error_msg}], pd.DataFrame()

    # --- Basic Name Cleaning Function ---
    def clean_name(name):
        if pd.isna(name) or not isinstance(name, str):
            return None
        return name.strip().lower()

    # --- Prepare Item Names ---
    if 'Item name' not in items_df.columns:
        error_msg = "Error: 'Item name' column not found in items data."
        print(error_msg)
        return [{"error": error_msg}], recipes_df  # Return original recipes_df if items can't be processed

    items_df['cleaned_item_name'] = items_df['Item name'].apply(clean_name)
    valid_item_names = set(items_df['cleaned_item_name'].dropna().unique())

    # --- Identify Ingredient Name Columns in Recipes ---
    ingredient_name_cols = [col for col in recipes_df.columns if col.startswith('Name (Ingredient ')]

    if not ingredient_name_cols:
        error_msg = "Error: No ingredient name columns found in recipes data (e.g., 'Name (Ingredient 1)')."
        print(error_msg)
        return [{"error": error_msg}], recipes_df # Return original recipes_df

    if 'Menu item name' not in recipes_df.columns:
        print("Warning: 'Menu item name' column not found in recipes data. Missing ingredients will be listed without specific recipe context if this column is missing from a row.")

    missing_ingredients_report = []
    recipes_df_augmented = recipes_df.copy() # Work on a copy

    # --- Iterate Through Recipes and Ingredients to build report and augment DataFrame ---
    for ing_idx, ing_name_col in enumerate(ingredient_name_cols):
        # Derive the status column name, e.g., "Status (Ingredient 1)"
        ingredient_identifier = ing_name_col.split('(', 1)[1] if '(' in ing_name_col else f"UnknownIngredient_{ing_idx+1})"
        status_col_name = f"Status ({ingredient_identifier}"

        statuses = []
        for index, row in recipes_df.iterrows():
            recipe_name = row.get('Menu item name', f"Recipe at row index {index}")
            ingredient_name = row.get(ing_name_col)
            cleaned_ingredient_name = clean_name(ingredient_name)

            current_status = "" # Default to blank if no ingredient
            if cleaned_ingredient_name:
                if cleaned_ingredient_name not in valid_item_names:
                    current_status = "MISSING"
                    # Add to the separate report list
                    missing_ingredients_report.append({
                        'recipe_name': recipe_name,
                        'missing_ingredient_name': ingredient_name,
                        'cleaned_missing_ingredient_name': cleaned_ingredient_name, # Added for consistency if needed in report
                        'ingredient_column': ing_name_col
                    })
                else:
                    current_status = "FOUND"
            statuses.append(current_status)

        # Add the new status column to the augmented DataFrame
        unit_col_name = ing_name_col.replace("Name (", "Unit (")
        insert_loc = recipes_df_augmented.columns.get_loc(ing_name_col) + 1
        if unit_col_name in recipes_df_augmented.columns:
            try:
                insert_loc = recipes_df_augmented.columns.get_loc(unit_col_name) + 1
            except KeyError:
                pass

        recipes_df_augmented.insert(loc=insert_loc, column=status_col_name, value=statuses)

    return missing_ingredients_report, recipes_df_augmented

# --- Main execution block ---
if __name__ == "__main__":
    print(f"Script is running. Current working directory: {os.getcwd()}")

    # Define input file paths relative to the project root
    items_csv_file = os.path.join('data', 'items.csv')
    recipes_csv_file = os.path.join('data', 'recipes.csv')

    # Define the output directory
    output_dir = 'output'
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    print(f"Attempting to load items from: {items_csv_file}")
    print(f"Attempting to load recipes from: {recipes_csv_file}")

    missing_items_output, recipes_df_with_status = find_missing_recipe_items_from_files(items_csv_file, recipes_csv_file)

    print("\n--- Analysis Complete ---")

    # --- Displaying the summary report of missing items (grouped by recipe) ---
    recipes_with_issues_count = 0
    if missing_items_output:
        if missing_items_output and isinstance(missing_items_output[0], dict) and "error" in missing_items_output[0]:
            print(f"An error occurred during processing: {missing_items_output[0]['error']}")
        else:
            if not missing_items_output:
                print("No missing ingredients found in recipes when compared to the items list (summary report).")
            else:
                print("\n--- Summary Report: Missing Ingredients Found (Grouped by Recipe) ---")

                grouped_missing_items = {}
                for item_info in missing_items_output:
                    recipe_name = item_info['recipe_name']
                    if recipe_name not in grouped_missing_items:
                        grouped_missing_items[recipe_name] = []
                    grouped_missing_items[recipe_name].append({
                        'original_name': item_info['missing_ingredient_name'],
                        'cleaned_name': item_info.get('cleaned_missing_ingredient_name', 'N/A'), # Use .get for safety
                        'column': item_info['ingredient_column']
                    })

                recipes_with_issues_count = len(grouped_missing_items) # Count of unique recipes with issues

                for recipe_name, ingredients in grouped_missing_items.items():
                    print(f"Recipe: '{recipe_name}'")
                    print("  Missing Ingredients:")
                    for ing_detail in ingredients:
                        print(f"    - {ing_detail['original_name']} (Cleaned: {ing_detail['cleaned_name']})")
                print("-" * 40)
    else:
        print("No missing ingredients found in recipes when compared to the items list (summary report).")

    # --- Saving the augmented recipes DataFrame ---
    if not recipes_df_with_status.empty:
        try:
            output_filename_augmented_recipes = os.path.join(output_dir, 'recipes_with_missing_status.csv')
            recipes_df_with_status.to_csv(output_filename_augmented_recipes, index=False)
            print(f"\nAugmented recipes data saved to: {output_filename_augmented_recipes}")
        except Exception as e:
            print(f"Error saving augmented recipes CSV: {e}")
    elif not (missing_items_output and isinstance(missing_items_output[0], dict) and "error" in missing_items_output[0]):
        print("\nNo augmented recipes data to save.")


    # --- Saving the separate missing items report (optional, raw list) ---
    if missing_items_output and not (missing_items_output and isinstance(missing_items_output[0], dict) and "error" in missing_items_output[0]):
        if missing_items_output:
            try:
                report_df = pd.DataFrame(missing_items_output)
                # Define the output file path for the report within the output directory
                output_filename_report = os.path.join(output_dir, 'missing_ingredients_summary_report_raw.csv')
                report_df.to_csv(output_filename_report, index=False)
                print(f"\nRaw summary report of missing ingredients saved to: {output_filename_report}")
            except Exception as e:
                print(f"Error saving raw summary report CSV: {e}")
    # The commented out section for statistics was removed as it seemed incomplete in the original.
    # If you want to add it back, ensure it's correctly implemented.
