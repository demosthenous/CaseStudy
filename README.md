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

