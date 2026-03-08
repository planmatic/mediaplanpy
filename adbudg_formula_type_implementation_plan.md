# Implementation Plan: Add `adbudg` Formula Type Support

## Adbudg Formula

The Adbudg formula is a diminishing-returns response curve:

```
metric_value = coefficient * base_metric^parameter2 / (parameter1 + base_metric^parameter2)
```

From the example:
```
metric_sales = 753083.697519 * metric_impressions^0.8315 / (3857364.900788 + metric_impressions^0.8315)
```

**Reverse calculation** (solve for coefficient given metric_value and base_metric):
```
coefficient = metric_value * (parameter1 + base_metric^parameter2) / base_metric^parameter2
```

---

## Affected Areas & Changes Required

### 1. Forward Calculation — `lineitem.py:_calculate_metric_from_formula()`
**File:** `src/mediaplanpy/models/lineitem.py` (lines 816-912)

- Add `elif formula_type == "adbudg"` branch
- Read `parameter1` and `parameter2` from formula (both already supported on the model)
- Implement: `result = coefficient * (base^parameter2) / (parameter1 + base^parameter2)`
- Handle edge cases: parameter1 + base^parameter2 == 0
- Update the error message listing valid types (line 907)

### 2. Reverse Calculation — `lineitem.py:_reverse_calculate_coefficient()`
**File:** `src/mediaplanpy/models/lineitem.py` (lines 914-1017)

- Add `elif formula_type == "adbudg"` branch
- Implement: `coefficient = metric_value * (parameter1 + base^parameter2) / base^parameter2`
- Handle edge cases: base^parameter2 == 0
- Read `parameter2` from formula (currently only reads `parameter1` for power_function)
- Update the error message listing valid types (line 1012)

### 3. Literal Type Constraint — `mediaplan_formulas.py`
**File:** `src/mediaplanpy/models/mediaplan_formulas.py` (line 18)

- Add `"adbudg"` to the `Literal[...]` type annotation for `formula_type` parameter

### 4. Model Documentation — `metric_formula.py`
**File:** `src/mediaplanpy/models/metric_formula.py` (line 44)

- Add `'adbudg'` to the Field description for `formula_type`

### 5. Dictionary Model Documentation — `dictionary.py`
**File:** `src/mediaplanpy/models/dictionary.py` (lines 58, 88)

- Add `'adbudg'` to Field descriptions for `formula_type` in both `MetricFormulaConfig` and `CustomMetricConfig`

### 6. JSON Schema Definitions
**Files:**
- `src/mediaplanpy/schema/definitions/3.0/lineitem.schema.json` (line 409)
- `src/mediaplanpy/schema/definitions/3.0/dictionary.schema.json` (lines 167, 193)

- Add `'adbudg'` to the description strings listing common formula types

### 7. Excel Exporter — `exporter.py`
**File:** `src/mediaplanpy/excel/exporter.py`

The exporter uses **hardcoded, formula-type-specific logic** for column generation, coefficient writing, and Excel formula construction. Changes needed:

**a) Column header generation — `_determine_calculated_columns()` (~line 335):**
- Add `elif formula_type == "adbudg"` branch
- Create 3 columns: `{metric}_coef` ("Sales Coefficient"), `{metric}_param1` ("Sales Parameter 1"), `{metric}_param2` ("Sales Parameter 2")

**b) Column header generation — `_determine_calculated_columns_multi()` (~line 418):**
- Add `elif formula_type == "adbudg"` branch (multi-lineitem variant of the above)

**c) Coefficient population — `_populate_coefficient_column()` (~line 663):**
- Add `elif formula_type == "adbudg"` branch for coefficient calculation

**d) Cell writing — `_populate_metric_formula_cells()` (~line 814):**
- Add `elif formula_type == "adbudg"` branch to write coefficient, parameter1, and parameter2 to their respective cells

**e) Excel formula generation (~line 814):**
- Add adbudg Excel formula: `=IF(base=0, 0, coef*(base^param2) / (param1 + base^param2))`

**f) Column suffix mapping — `_read_coefficient_for_formula_type()` (~line 272):**
- Add `elif formula_type == "adbudg"` → `_coef` suffix mapping

**g) Help text (~line 1862):**
- Add `'adbudg'` to the formula types list

### 8. Excel Importer — `importer.py`
**File:** `src/mediaplanpy/excel/importer.py`

The importer uses **hardcoded header patterns and suffix mappings** to reconstruct formulas from Excel columns. Changes needed:

**a) Column header pattern matching:**
- Add recognition for `"... Parameter 2"` header pattern → `{metric}_param2` suffix
- Ensure `"... Coefficient"` and `"... Parameter 1"` patterns work for adbudg (may already work if shared with power_function)

**b) `_read_coefficient_for_formula_type()` function:**
- Add `elif formula_type == "adbudg"` → `_coef` suffix mapping

**c) Reverse calculation during import:**
- Add adbudg reverse calculation: `coefficient = metric_value * (param1 + base^param2) / base^param2`
- Read `parameter2` from `{metric}_param2` column (currently only reads `parameter1` for power_function)

**d) Build metric_formulas dict:**
- Include `parameter2` in the formula entry when formula_type is adbudg

### 9. MediaPlan Model Docstrings — `mediaplan.py`
**File:** `src/mediaplanpy/models/mediaplan.py` (lines ~1075, ~1199)

- Update method parameter docstrings that list valid formula types

### 10. SDK Reference Documentation
**File:** `SDK_REFERENCE.md` (lines 520, 961)

- Add `'adbudg'` to formula type documentation

### 11. Unit Tests — `test_formulas.py`
**File:** `tests/unit/test_formulas.py`

Add new test cases:
- **Forward calculation**: Test `_calculate_metric_from_formula()` with adbudg type, verify against the example data (151774.95 cost → 82177448 impressions → 374140.90 sales)
- **Reverse calculation**: Test `_reverse_calculate_coefficient()` with adbudg type
- **`set_metric_value()`**: Test setting a metric value with adbudg formula updates coefficient correctly
- **`configure_metric_formula()`**: Test configuring adbudg formula parameters and recalculation
- **`select_metric_formula()`**: Test selecting adbudg at plan level with propagation
- **Edge cases**: Zero base value, zero parameter1, zero parameter2

### 12. Test Fixtures — `conftest.py`
**File:** `tests/conftest.py` (lines 99-141)

- Add adbudg test fixture with sample data (e.g., the Meridian response curve example from the line item)

### 13. Excel Integration Tests — `test_excel.py`
**File:** `tests/integration/test_excel.py`

- Add adbudg formula to Excel round-trip export/import tests
- Verify coefficient, parameter1, and parameter2 survive the round-trip

### 14. Changelog
**File:** `CHANGE_LOG.md`

- Add release note entry for adbudg formula type support

### 15. Examples (Optional)
**File:** `examples/examples_15_formulas.py`

- Consider adding an adbudg example demonstrating the Meridian-style response curve

---

## Files Changed (Summary)

| # | File | Change |
|---|------|--------|
| 1 | `src/mediaplanpy/models/lineitem.py` | Add adbudg forward & reverse calculation logic, update error messages |
| 2 | `src/mediaplanpy/models/mediaplan_formulas.py` | Add "adbudg" to Literal type |
| 3 | `src/mediaplanpy/models/metric_formula.py` | Update description string |
| 4 | `src/mediaplanpy/models/dictionary.py` | Update description strings (2 places) |
| 5 | `src/mediaplanpy/models/mediaplan.py` | Update method parameter docstrings |
| 6 | `src/mediaplanpy/schema/definitions/3.0/lineitem.schema.json` | Update description |
| 7 | `src/mediaplanpy/schema/definitions/3.0/dictionary.schema.json` | Update descriptions (2 places) |
| 8 | `src/mediaplanpy/excel/exporter.py` | Add adbudg branches in 5 functions, column generation, Excel formula, help text |
| 9 | `src/mediaplanpy/excel/importer.py` | Add adbudg header pattern matching, parameter2 reading, reverse calculation |
| 10 | `SDK_REFERENCE.md` | Update documentation |
| 11 | `tests/unit/test_formulas.py` | Add adbudg test cases |
| 12 | `tests/conftest.py` | Add adbudg test fixture |
| 13 | `tests/integration/test_excel.py` | Add adbudg Excel round-trip test |
| 14 | `CHANGE_LOG.md` | Add release note entry |

## No Changes Required

- **MetricFormula model**: Already supports `parameter1`, `parameter2`, `parameter3` — no structural changes needed
- **JSON schema structure**: Already supports arbitrary `formula_type` strings and all parameters — no schema structure changes
- **Schema migration**: No migration needed — adbudg is additive, existing plans unaffected
- **Storage backends**: Formula serialization is generic — no changes needed
- **Dependency graph / topological sort**: Already works with any formula type — no changes needed
- **MetricValue wrapper**: Already exposes all formula fields — no changes needed
