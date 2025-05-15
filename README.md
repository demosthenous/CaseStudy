# Data Validation Prototype

This repository contains a Python-based prototype for a lightweight internal tool to help catch and clean common data issues in Nory's customer datasets, specifically focusing on menus (items) and recipes.

## The Problem(s) Addressed

This prototype tackles several common data integrity issues identified in customer-provided menu and recipe data:

1.  **For Item Data (`items.csv`):**
    * **Missing Information:** Identifies items with blank fields for crucial attributes like 'Item size', 'Item Unit of Measure', '€ Price per unit (excluding VAT)', 'Tax rate', and 'Supplier code'.
    * **Invalid Data Types:** Flags non-numeric values in fields expected to be numeric (e.g., size, price, tax rate, supplier code).
    * **Invalid Units of Measure (UOM):** Checks 'Item Unit of Measure' against a predefined list of allowed UOMs.
    * **Unreasonable Size Magnitudes:** Flags items with potentially erroneous large sizes based on their UOM (e.g., 10,000g for an item).
    * **Potential Duplicate Items:** Identifies items that might be duplicates based on a combination of:
        * Fuzzy name matching.
        * Similar supplier.
        * Similar item size (within a tolerance).
        * Similar price (within a tolerance).

2.  **For Recipe Data (`recipes.csv`):**
    * **Recipes Referencing Unknown Ingredients:** Identifies ingredients listed in recipes that do not exist in the `items.csv` master list. A report of these missing links is generated, and the recipes CSV is augmented with status columns.
    * **Invalid or Missing Ingredient Quantities/UOMs:**
        * Flags missing or non-numeric ingredient quantities.
        * Validates ingredient UOMs against an allowed list.
        * Checks for UOM consistency between the recipe ingredient and the item master (e.g., 'g' vs 'kg' is convertible, 'g' vs 'ml' is a mismatch).
    * **Potentially High-Cost Recipes:** Estimates the cost of each ingredient line (where possible) and calculates a total recipe cost. It then flags recipes that are statistical outliers in terms of cost or exceed a predefined absolute threshold, potentially indicating data entry errors (e.g., incorrect quantity or UOM).

# Project: Recipe and Item Data Validation Suite

This project provides a suite of Python scripts designed to validate and clean data related to food items and recipes, typically managed in CSV files. The goal is to identify inconsistencies, errors, and potential issues in master item lists and recipe formulations, thereby improving data quality and operational efficiency.

## The Problems Tackled

This suite addresses several common data quality challenges in environments dealing with food items and recipes:

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

## How to Run Your Code

### Prerequisites:

* **Python 3.x** installed.
* **pip** (Python package installer) installed.
* Required Python libraries: `pandas`, `numpy`, `fuzzywuzzy`, `python-Levenshtein` (often needed by `fuzzywuzzy` for better performance, install it explicitly).

### Setup:

1.  **Clone or Download the Project:**
    Place the script files (`find_missing_ingredients.py`, `validate_items.py`, `validate_recipe_details.py`) in a directory (e.g., `src`).

2.  **Install Dependencies:**
    Open your terminal or command prompt and run:
    ```bash
    pip install pandas numpy fuzzywuzzy python-Levenshtein
    ```

3.  **Prepare Your Data:**
    * Create a subdirectory named `data` in the same directory where your `src` folder (containing the scripts) is located.
    * Place your input CSV files into this `data` folder.
        * For `find_missing_ingredients.py` and `validate_recipe_details.py`: You'll need `items.csv` and `recipes.csv`.
        * For `validate_items.py`: You'll need `items.csv`.
    * Ensure your CSV files have the expected column headers as detailed in the script explanations (e.g., "Item name", "Name (Ingredient 1)", "Qty (Ingredient 1)", "Unit (Ingredient 1)", etc.). Refer to the configuration sections within each script for specific column names they look for.

4.  **Create Output Directory:**
    The scripts will attempt to create an `output` subdirectory (at the same level as `src` and `data`) to store the generated CSV reports. If you have permission issues, you can create it manually.
    ```
    your_project_folder/
    ├── src/
    │   ├── find_missing_ingredients.py
    │   ├── validate_items.py
    │   └── validate_recipe_details.py
    ├── data/
    │   ├── items.csv
    │   └── recipes.csv
    └── output/  <-- This will be created by the scripts
    ```

### Running the Scripts:

Navigate to the `src` directory in your terminal and run each script individually using Python:

1.  **To find missing ingredients in recipes:**
    ```bash
    python find_missing_ingredients.py
    ```
    * **Output:**
        * Console messages summarizing findings.
        * `output/recipes_with_missing_status.csv`
        * `output/missing_ingredients_summary_report_raw.csv`

2.  **To validate your master items list:**
    ```bash
    python validate_items.py
    ```
    * **Output:**
        * Console messages summarizing validation checks.
        * `output/items_with_validation_flags.csv`

3.  **To validate recipe ingredient quantities and UOMs:**
    ```bash
    python validate_recipe_details.py
    ```
    * **Output:**
        * Console messages summarizing validation checks.
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

* **Scalability with Very Large Files:** While pandas is efficient, processing extremely large CSV files (many millions of rows or hundreds of ingredient columns) using iterative row-by-row processing (`iterrows`) might become slow. Vectorized operations could improve performance but would increase code complexity for some of the detailed conditional logic.
* **Complex UOM Conversions:** The current UOM conversion in `validate_recipe_details.py` handles direct conversions to a base unit (e.g., g to kg, ml to L). It does not handle density-based conversions (e.g., ml of flour to grams of flour) as this requires item-specific density data, which is not assumed to be present.
* **Contextual Understanding of "Unreasonable":** The magnitude checks are based on fixed thresholds. They don't understand the context (e.g., a large quantity of water might be reasonable for a soup stock recipe but not for a garnish).
* **Fuzzy Matching Imperfections:** Fuzzy matching is powerful but not infallible. It might occasionally flag non-duplicates as similar or miss very cleverly disguised duplicates. The detailed output from the duplicate check is meant for human review.
* **Single File Processing:** Each script processes one primary input file (or a pair for recipe-item comparisons) at a time as defined by the file paths in the script. It's not set up as a pipeline that automatically feeds output from one script to another (though the generated CSVs can be used as input for subsequent manual analysis or other processes).
* **Error Handling Scope:** Error handling primarily covers file I/O and basic data format issues. Unexpected data structures within rows might still cause issues if not fitting the assumed patterns.

## What You’d Improve or Build Next (With More Time)

1.  **Configuration Files:**
    * Move all configurable parameters (allowed UOMs, thresholds, column names, file paths) into external configuration files (e.g., JSON, YAML) instead of hardcoding them in the scripts. This would make the suite much more flexible and easier to adapt for different users/datasets without code changes.

2.  **Integrated Pipeline & Workflow:**
    * Create a master script or a simple CLI (Command Line Interface) tool that allows running selected validations in a sequence, potentially using the output of one script as an input or guide for another.
    * For instance, after `validate_items.py`, use its output to refine the `items.csv` before running `find_missing_ingredients.py`.

3.  **Enhanced UOM Conversion & Management:**
    * Integrate a more sophisticated UOM library.
    * Allow for item-specific density data in `items.csv` to enable volume-to-weight conversions (e.g., "flour 1 cup = 120g").
    * Provide tools for UOM mapping if input data uses varied or non-standard UOMs.

4.  **Improved Performance for Large Datasets:**
    * Refactor `iterrows()` loops to use pandas vectorized operations or `apply()` where feasible for performance gains on very large datasets. This is a trade-off with readability for some complex conditional logic.

5.  **Web Interface / GUI:**
    * Develop a simple web interface (using Flask or Django) or a desktop GUI (using Tkinter, PyQt) to allow users to upload files, select validation options, run scripts, and view/download reports without directly interacting with the command line.

6.  **Database Integration:**
    * Allow scripts to read from and write validation flags/reports to a database instead of just CSV files. This would be better for managing larger, persistent datasets and tracking changes over time.

7.  **Advanced Duplicate Detection:**
    * Explore more advanced machine learning-based duplicate detection techniques if fuzzy matching proves insufficient for very noisy data.
    * Incorporate learning from user feedback on flagged duplicates (e.g., "mark as not a duplicate").

8.  **Interactive Reporting & Visualization:**
    * Generate interactive HTML reports (e.g., using libraries like `plotly` or `bokeh`) to better visualize validation issues, especially for duplicates or UOM mismatches.
    * Dashboarding of data quality metrics over time.

9.  **Automated Data Cleaning Suggestions:**
    * For certain types of errors (e.g., common UOM typos, simple numeric format issues), the script could suggest automated corrections or even apply them if a "safe mode" is enabled.

10. **More Granular Error/Warning Levels:**
    * Differentiate between critical errors, warnings, and informational flags more explicitly in the output.

11. **User-Defined Validation Rules:**
    * Allow users to define custom validation rules (perhaps via a simple DSL or configuration) without modifying the core Python code.

12. **Test Suite:**
    * Develop a comprehensive suite of unit and integration tests to ensure the reliability of the scripts as they evolve.