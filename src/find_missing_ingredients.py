import pandas as pd
import os

def find_missing_recipe_items_from_files(items_file_path: str, recipes_file_path: str):

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

   
    def clean_name(name):
        if pd.isna(name):
            return None
        return str(name).strip().lower() 

    # --- Prepare Item Names ---
    if 'Item name' not in items_df.columns:
        error_msg = "Error: 'Item name' column not found in items data."
        print(error_msg)
        # Return empty DataFrame for augmented if critical column missing
        return [{"error": error_msg}], pd.DataFrame()

    items_df['cleaned_item_name'] = items_df['Item name'].apply(clean_name)
    valid_item_names = set(items_df['cleaned_item_name'].dropna().unique())

    # --- Identify Ingredient Name Columns in Recipes ---
    ingredient_name_cols = [col for col in recipes_df.columns if col.startswith('Name (Ingredient ')]

    if not ingredient_name_cols:
        error_msg = "Error: No ingredient name columns found in recipes data (e.g., 'Name (Ingredient 1)')."
        print(error_msg)

        return [{"error": error_msg}], pd.DataFrame()

    if 'Menu item name' not in recipes_df.columns:
        print("Warning: 'Menu item name' column not found in recipes data. Missing ingredients will be listed without specific recipe context if this column is missing from a row.")

    missing_ingredients_report = []
    recipes_df_augmented = recipes_df.copy() # Work on a copy

    # --- Iterate Through Recipes and Ingredients to build report ---
    for ing_idx, ing_name_col in enumerate(ingredient_name_cols):

        status_col_name = ing_name_col.replace("Name (", "Status (", 1)

        if status_col_name == ing_name_col:
            status_col_name = f"Status_UnknownIngredient_{ing_idx+1}"

        statuses = []
        for index, row in recipes_df.iterrows(): 
            recipe_name = row.get('Menu item name', f"Recipe at row index {index}")
            ingredient_name = row.get(ing_name_col)
            cleaned_ingredient_name = clean_name(ingredient_name)

            current_status = "" 
            if cleaned_ingredient_name:
                if cleaned_ingredient_name not in valid_item_names:
                    current_status = "MISSING"
                    
                    missing_ingredients_report.append({
                        'recipe_name': recipe_name,
                        'missing_ingredient_name': ingredient_name, # Original name
                        'cleaned_missing_ingredient_name': cleaned_ingredient_name # Cleaned name
                    })
                else:
                    current_status = "FOUND"
            statuses.append(current_status)

        # Add the new status column to the augmented DataFrame

        insert_loc = recipes_df_augmented.columns.get_loc(ing_name_col) + 1
        unit_col_name = ing_name_col.replace("Name (", "Unit (", 1) # Match potential unit column
        if unit_col_name in recipes_df_augmented.columns:
            try:
                insert_loc = recipes_df_augmented.columns.get_loc(unit_col_name) + 1
            except KeyError:

                pass
        
        # Ensure insert_loc is within bounds
        if insert_loc > len(recipes_df_augmented.columns):
            recipes_df_augmented[status_col_name] = statuses # Append if loc is out of bounds
        else:
            recipes_df_augmented.insert(loc=insert_loc, column=status_col_name, value=statuses)

    return missing_ingredients_report, recipes_df_augmented

# --- Main execution block ---
if __name__ == "__main__":
    print(f"Script is running. Current working directory: {os.getcwd()}")



    items_csv_file = os.path.join('data', 'items.csv')
    recipes_csv_file = os.path.join('data', 'recipes.csv')

    # Define the output directory
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)

    print(f"Attempting to load items from: {items_csv_file}")
    print(f"Attempting to load recipes from: {recipes_csv_file}")

    missing_items_output, recipes_df_with_status = find_missing_recipe_items_from_files(items_csv_file, recipes_csv_file)

    print("\n--- Analysis Complete ---")

    processing_error_occurred = False
    if missing_items_output and isinstance(missing_items_output, list) and len(missing_items_output) > 0 and \
       isinstance(missing_items_output[0], dict) and "error" in missing_items_output[0]:
        print(f"An error occurred during processing: {missing_items_output[0]['error']}")
        processing_error_occurred = True

    # --- Displaying the summary report of missing items (grouped by recipe) ---
    if not processing_error_occurred:
        if not missing_items_output: 
            print("No missing ingredients found in recipes when compared to the items list.")
        else:
            print("\n--- Summary Report: Missing Ingredients Found (Grouped by Recipe) ---")
            grouped_missing_items = {}
            for item_info in missing_items_output: 
                recipe_name = item_info['recipe_name']
                if recipe_name not in grouped_missing_items:
                    grouped_missing_items[recipe_name] = []

                grouped_missing_items[recipe_name].append({
                    'original_name': item_info['missing_ingredient_name'],
                    'cleaned_name': item_info.get('cleaned_missing_ingredient_name', 'N/A') 
                })

            recipes_with_issues_count = len(grouped_missing_items)
            if recipes_with_issues_count > 0:
                print(f"Number of unique recipes with missing ingredients: {recipes_with_issues_count}")
                for recipe_name, ingredients in grouped_missing_items.items():
                    print(f"Recipe: '{recipe_name}'")
                    print("  Missing Ingredients:")
                    for ing_detail in ingredients:

                        print(f"    - {ing_detail['original_name']} (Cleaned: {ing_detail['cleaned_name']})")
                print("-" * 40)
            else: 
                print("No missing ingredients found in recipes when compared to the items list.")


    # --- Saving the augmented recipes DataFrame ---
    if not processing_error_occurred:
        if not recipes_df_with_status.empty:
            try:
                output_filename_augmented_recipes = os.path.join(output_dir, 'recipes_with_missing_status.csv')
                recipes_df_with_status.to_csv(output_filename_augmented_recipes, index=False)
                print(f"\nAugmented recipes data saved to: {output_filename_augmented_recipes}")
            except Exception as e:
                print(f"Error saving augmented recipes CSV: {e}")
        else:

            print("\nNo augmented recipes data to save (input might have been empty or resulted in an empty processed DataFrame).")
    else:
        print("\nAugmented recipes data not saved due to a processing error.")


    # --- Saving the separate missing items report (raw list) ---
    if not processing_error_occurred:
        if missing_items_output: 
            try:

                report_data_for_csv = []
                for item in missing_items_output: # item_info still has 'cleaned_missing_ingredient_name' here
                    report_data_for_csv.append({
                        'recipe_name': item['recipe_name'],
                        'missing_ingredient_name': item['missing_ingredient_name']
                    })
                
                report_df = pd.DataFrame(report_data_for_csv)
                # --- End of modification for CSV data ---

                if not report_df.empty:
                    output_filename_report = os.path.join(output_dir, 'missing_ingredients_summary_report_raw.csv')
                    report_df.to_csv(output_filename_report, index=False)
                    print(f"\nRaw summary report of missing ingredients (without cleaned column) saved to: {output_filename_report}")
                else:
                    print("\nMissing items report is empty after DataFrame conversion (no missing items to report), not saving.")
            except Exception as e:
                print(f"Error saving raw summary report CSV: {e}")
        else:
            print("\nNo missing items to save in the raw report (all ingredients found or no ingredients to check).")
    else:
        print("\nRaw missing items report not saved due to a processing error.")
