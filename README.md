# Data Validation Prototype

## Problems Addressed

This prototype tackles data integrity issues identified in customer-provided menu and recipe data:


1.  **Missing Information in Master Item Data (`validate_items.py`):**
    * Essential details like item size, unit of measure (UOM), price, tax rate, or supplier codes might be missing from the master item list.
2.  **Incorrect Data Formats in Master Item Data (`validate_items.py`):**
    * Fields expected to be numeric (e.g., size, price) might contain text or incorrectly formatted numbers.
    * Units of Measure might not conform to a standard list or be missing.
3.  **Unreasonable Values in Master Item Data (`validate_items.py`):**
    * Item sizes might be orders of magnitude too large or small for their UOM (e.g., an item measured in grams having a size of 50,000, i.e., 50kg).
4.  **Potential Duplicate Entries in Master Item Data (`validate_items.py`):**
    * The same item might be listed multiple times, perhaps with slight name variations or from different suppliers, leading to inventory and purchasing confusion. This script uses fuzzy name matching combined with supplier, size, and price comparisons to flag potential duplicates.
5.  **Recipes Using Non-Stocked Ingredients (`find_missing_ingredients.py`):**
    * Recipes might call for ingredients that are not present in the master list of available items.
6.  **Incorrect Data Formats in Recipe Details (`validate_recipe_details.py`):**
    * Ingredient quantities in recipes might be non-numeric or missing.
    * Ingredient UOMs might be missing, invalid, or inconsistent.
7.  **UOM Mismatches Between Recipes and Item Master (`validate_recipe_details.py`):**
    * A recipe might specify an ingredient in one UOM (e.g., kilograms) while the master item list defines that ingredient in a different, potentially incompatible or non-convertible, UOM (e.g., milliliters vs. grams, or even just grams vs. kilograms if conversion isn't handled). The script attempts to identify convertible UOMs.
8.  **Unreasonable Ingredient Quantities in Recipes (`validate_recipe_details.py`):**
    * A recipe might specify an unusually large quantity for an ingredient (e.g., 20 liters of spice for a single dish).

## How to Run the Code

### Prerequisites:

* **Python/ Python 3** installed.
* **pip** installed.
* Required Python libraries: `pandas`, `numpy`, `fuzzywuzzy`, `python-Levenshtein` (needed by `fuzzywuzzy` for better performance, install it explicitly).

### Setup:

1.  **Clone or Download the Project:**
    Place the script files (`find_missing_ingredients.py`, `validate_items.py`, `validate_recipe_details.py`) in a directory (e.g., `src`).
2. **Create and activate Python virtual environment:
    ```bash
   python3 -m venv venv
   source venv/bin/activate
    ```
3.  **Install Dependencies:**
    Open your terminal or command prompt and run:
    ```bash
    pip install pandas numpy fuzzywuzzy python-Levenshtein
    ```

4.  **Prepare Your Data:**
    * Create a subdirectory named `data` in the same directory where your `src` folder (containing the scripts) is located.
    * Place your input CSV files into this `data` folder.
        * For `find_missing_ingredients.py` and `validate_recipe_details.py`: You'll need `items.csv` and `recipes.csv`.
        * For `validate_items.py`: You'll need `items.csv`.
    * Ensure your CSV files have the expected column headers as detailed in the script explanations (e.g., "Item name", "Name (Ingredient 1)", "Qty (Ingredient 1)", "Unit (Ingredient 1)", etc.). Refer to the configuration sections within each script for specific column names they look for.

5.  **Create Output Directory:**
    The scripts will attempt to create an `output` subdirectory (at the same level as `src` and `data`) to store the generated CSV reports. 

### Running the Scripts:

Navigate to the `src` directory in your terminal and run the scripts using Python:

1.  **Run the scripts**
    ```bash
    python find_missing_ingredients.py
    python validate_items.py
    python validate_recipe_details.py
    ```
    * **Output:**
        * Console messages summarizing findings.
        * `output/recipes_with_missing_status.csv`
        * `output/missing_ingredients_summary_report_raw.csv`
        * `output/items_with_validation_flags.csv`
        * `output/recipes_with_qty_uom_validation.csv`

Review the console output for summaries and check the generated CSV files in the `output` directory for detailed results.

## Assumptions/ Limitations

### Assumptions:

* **Input File Format:** Input data is expected in CSV format.
* **File Location:** Scripts assume input CSVs (`items.csv`, `recipes.csv`) are in a `./data/` subdirectory relative to where the scripts are run (or where the `src` folder is located if you run from one level above `src`). Output is saved to `./output/`.
* **Column Naming Conventions:**
    * `items.csv` is expected to have specific column names like "Item name", "Item Unit of Measure", "Item size", etc., as referenced in `validate_items.py` and other scripts.
    * `recipes.csv` is expected to have ingredient columns following the pattern "Name (Ingredient X)", "Qty (Ingredient X)", "Unit (Ingredient X)". It may also have a "Menu item name" column.
    * Deviations from these names will require modifying the scripts.
* **Data Structure for Recipes:** The scripts assume that each row in `recipes.csv` can represent a recipe, and its ingredients are spread across multiple columns (Ingredient 1, Ingredient 2, ...).
* **UOM Consistency:** The `ALLOWED_UOMS` list and conversion factors are predefined. Custom or less common UOMs will be flagged as invalid unless added to the configurations within the scripts.
* **Duplicate Criteria:** The definition of a "duplicate" item in `validate_items.py` (name similarity threshold, size/price tolerances) is configurable but based on specific heuristics.
* **Magnitude Thresholds:** The thresholds for "unreasonable" sizes/quantities are examples and may need tuning based on the specific context of the data.

### Limitations:


* **Complex UOM Conversions:** The current UOM conversion in `validate_recipe_details.py` handles direct conversions to a base unit (e.g., g to kg, ml to L). It does not handle density-based conversions (e.g., ml of flour to grams of flour) as this requires item-specific density data, which is not present.
* **Contextual Understanding of "Unreasonable":** The magnitude checks are based on fixed thresholds. They don't understand the context (e.g., a large quantity of water might be reasonable for a soup stock recipe but not for a garnish).
* **Fuzzy Matching Imperfections:** Fuzzy matching is powerful but not perfect. It might occasionally flag non-duplicates as similar or miss very cleverly disguised duplicates. The detailed output from the duplicate check is meant for human review.
* **Single File Processing:** Each script processes one primary input file (or a pair for recipe-item comparisons) at a time as defined by the file paths in the script. It's not set up as a pipeline that automatically feeds output from one script to another.
  

## Potential Improvements

1.  **Configuration Files:**
    * Move all configurable parameters (allowed UOMs, thresholds, column names, file paths) into external configuration files (e.g., JSON, YAML) instead of hardcoding them in the scripts. This would make the suite much more flexible and easier to adapt for different users/datasets without code changes.

2.  **Integrated Pipeline & Workflow:**
    * Create a master script or a simple CLI tool that allows running selected validations in a sequence, potentially using the output of one script as an input or guide for another.
    * For instance, after `validate_items.py`, use its output to refine the `items.csv` before running `find_missing_ingredients.py`.

3.  **Enhanced UOM Conversion & Management:**
    * Integrate a more sophisticated UOM library.
    * Allow for item-specific density data in `items.csv` to enable volume-to-weight conversions (e.g., "flour 1 cup = 120g").
    * Provide tools for UOM mapping if input data uses varied or non-standard UOMs.

4.  **Web Interface:**
    * Develop a simple web interface or a desktop GUI to allow users to upload files, select validation options, run scripts, and view/download reports without directly interacting with the terminal.

5.  **Database Integration:**
    * Allow scripts to read from and write validation flags/reports to a database instead of just CSV files. This would be better for managing larger, persistent datasets and tracking changes over time.

6.  **Duplicate Detection:**
    * Explore more advanced machine learning-based duplicate detection techniques if fuzzy matching proves insufficient for very noisy data.
    * Incorporate learning from user feedback on flagged duplicates (e.g., "mark as not a duplicate").
