# Changelog: v2.0 to v3.0

**Quick Reference for SDK Development**

This document provides a comprehensive field-by-field comparison between v2.0 and v3.0 schemas to facilitate SDK upgrades.

---

## Summary Statistics

| Schema | v2.0 Fields | v3.0 Fields | Net Change |
|--------|-------------|-------------|------------|
| Meta | 10 | 16 | +6 fields |
| Campaign | 25 | 36 | +11 fields (but 7 removed, 18 added) |
| Line Item | 78 | 98 | +20 fields |
| Dictionary | 3 groups | 5 groups | +2 groups, renamed 1 |

**Total**: v2.0 had ~116 fields, v3.0 has ~155 fields (+39 fields net)

---

## Breaking Changes

### 1. Campaign Schema - Audience Fields

**REMOVED** (v2.0):
- `audience_name` (string)
- `audience_age_start` (integer)
- `audience_age_end` (integer)
- `audience_gender` (string, enum)
- `audience_interests` (array of strings)

**ADDED** (v3.0):
- `target_audiences` (array of objects)
  - Each object structure:
    - `name` (string, **required**)
    - `description` (string)
    - `demo_age_start` (integer)
    - `demo_age_end` (integer)
    - `demo_gender` (string, enum: Male/Female/Any)
    - `demo_attributes` (string)
    - `interest_attributes` (string)
    - `intent_attributes` (string)
    - `purchase_attributes` (string)
    - `content_attributes` (string)
    - `exclusion_list` (string)
    - `extension_approach` (string)
    - `population_size` (integer)

**SDK Impact**: Requires migration logic, validation updates, serialization changes

---

### 2. Campaign Schema - Location Fields

**REMOVED** (v2.0):
- `location_type` (string, enum: Country/State)
- `locations` (array of strings)

**ADDED** (v3.0):
- `target_locations` (array of objects)
  - Each object structure:
    - `name` (string, **required**)
    - `description` (string)
    - `location_type` (string, enum: Country/State/DMA/County/Postcode/Radius/POI)
    - `location_list` (array of strings)
    - `exclusion_type` (string, enum: Country/State/DMA/County/Postcode/Radius/POI)
    - `exclusion_list` (array of strings)
    - `population_percent` (number, 0-1)

**SDK Impact**: Requires migration logic, validation updates, expanded enum support

---

### 3. Dictionary Schema - Custom Dimensions Rename

**RENAMED**:
- v2.0: `custom_dimensions`
- v3.0: `lineitem_custom_dimensions`

**SDK Impact**: Field name mapping in serialization/deserialization

---

## Additive Changes (Non-Breaking)

### Meta Schema

**NEW FIELDS** (all optional):
- `dim_custom1` (string)
- `dim_custom2` (string)
- `dim_custom3` (string)
- `dim_custom4` (string)
- `dim_custom5` (string)
- `custom_properties` (object)

**SDK Impact**: Extend meta object model, add validation for custom dimensions

---

### Campaign Schema

**NEW FIELDS** (all optional):
- `kpi_name1` (string)
- `kpi_value1` (number)
- `kpi_name2` (string)
- `kpi_value2` (number)
- `kpi_name3` (string)
- `kpi_value3` (number)
- `kpi_name4` (string)
- `kpi_value4` (number)
- `kpi_name5` (string)
- `kpi_value5` (number)
- `dim_custom1` (string)
- `dim_custom2` (string)
- `dim_custom3` (string)
- `dim_custom4` (string)
- `dim_custom5` (string)
- `custom_properties` (object)

**SDK Impact**: Extend campaign object model, add KPI validation

---

### Line Item Schema

**NEW FIELDS** (all optional):

**Buy Information:**
- `kpi_value` (number)
- `buy_type` (string)
- `buy_commitment` (string)

**Aggregation:**
- `is_aggregate` (boolean)
- `aggregation_level` (string)

**Multi-Currency:**
- `cost_currency_exchange_rate` (number)

**Budget Constraints:**
- `cost_minimum` (number)
- `cost_maximum` (number)

**New Metrics (11 new):**
- `metric_view_starts` (number)
- `metric_view_completions` (number)
- `metric_reach` (number)
- `metric_units` (number)
- `metric_impression_share` (number)
- `metric_page_views` (number)
- `metric_likes` (number)
- `metric_shares` (number)
- `metric_comments` (number)
- `metric_conversions` (number)

**Formulas:**
- `metric_formulas` (object)
  - Keys: metric names (e.g., "metric_leads", "metric_clicks")
  - Values: formula configuration objects
    - `formula_type` (string) - e.g., "power_function", "conversion_rate", "cost_per_unit", "constant"
    - `base_metric` (string) - e.g., "cost_total", "metric_impressions"
    - `coefficient` (number)
    - `parameter1` (number)
    - `parameter2` (number)
    - `parameter3` (number)
    - `comments` (string)

**Extensibility:**
- `custom_properties` (object)

**SDK Impact**: Extend lineitem object model, add formula evaluation engine, add new metric validation

---

### Dictionary Schema

**NEW GROUPS** (all optional):

**meta_custom_dimensions** (new):
- Configures dim_custom1-5 for meta level
- Structure: `custom_field_config` (status, caption)

**campaign_custom_dimensions** (new):
- Configures dim_custom1-5 for campaign level
- Structure: `custom_field_config` (status, caption)

**standard_metrics** (new):
- Configures formula support for standard metrics
- Structure: `metric_formula_config` (formula_type, base_metric)
- Contains 25 formula-capable metrics

**custom_metrics** (enhanced):
- Added formula support fields
- Structure: `custom_metric_config` (status, caption, formula_type, base_metric)

**SDK Impact**: Dictionary parser updates, formula configuration validation, scoped dimension support

---

## SDK Component Impact Assessment

### 1. Schema Validation
- [ ] Update schema file references (2.0 → 3.0)
- [ ] Add validation for target_audiences array structure
- [ ] Add validation for target_locations array structure
- [ ] Add validation for metric_formulas object structure
- [ ] Update dictionary validation for renamed/new sections
- [ ] Add enum validation for expanded location_type
- [ ] Add range validation for population_percent (0-1)

### 2. Data Models / Classes
- [ ] Update Meta class: add dim_custom1-5, custom_properties
- [ ] Update Campaign class: remove 7 fields, add target_audiences, target_locations, KPIs, dimensions, custom_properties
- [ ] Update LineItem class: add 20 new fields including metric_formulas
- [ ] Update Dictionary class: rename custom_dimensions, add 2 new groups, enhance custom_metrics
- [ ] Create TargetAudience class (13 properties)
- [ ] Create TargetLocation class (7 properties)
- [ ] Create MetricFormula class (7 properties)

### 3. Migration Utility
- [ ] Implement v2→v3 migration function
- [ ] Audience field migration with name generation
- [ ] Location field migration with name generation
- [ ] Dictionary key rename (custom_dimensions → lineitem_custom_dimensions)
- [ ] Schema version update
- [ ] Validation after migration

### 4. Serialization / Deserialization
- [ ] Update JSON serializers for new structures
- [ ] Handle target_audiences array
- [ ] Handle target_locations array
- [ ] Handle metric_formulas object
- [ ] Handle custom_properties objects at 3 levels
- [ ] Update field mappings for renamed dictionary key

### 5. Query / Analysis Functions
- [ ] Add support for querying multiple audiences
- [ ] Add support for querying multiple locations
- [ ] Add formula evaluation engine
- [ ] Add KPI tracking/comparison functions
- [ ] Add custom properties accessor methods

### 6. Documentation
- [ ] Update API documentation
- [ ] Add v3.0 examples
- [ ] Document migration process
- [ ] Update field reference documentation

---

## Field Reference Tables

### Meta Fields Comparison

| v2.0 Field | v3.0 Field | Status | Type |
|------------|------------|--------|------|
| id | id | Unchanged | string |
| schema_version | schema_version | **Updated value** | string |
| name | name | Unchanged | string |
| created_by_id | created_by_id | Unchanged | string |
| created_by_name | created_by_name | Unchanged | string |
| created_at | created_at | Unchanged | string (datetime) |
| comments | comments | Unchanged | string |
| is_current | is_current | Unchanged | boolean |
| is_archived | is_archived | Unchanged | boolean |
| parent_id | parent_id | Unchanged | string |
| - | dim_custom1 | **NEW** | string |
| - | dim_custom2 | **NEW** | string |
| - | dim_custom3 | **NEW** | string |
| - | dim_custom4 | **NEW** | string |
| - | dim_custom5 | **NEW** | string |
| - | custom_properties | **NEW** | object |

---

### Campaign Fields Comparison

| v2.0 Field | v3.0 Field | Status | Type |
|------------|------------|--------|------|
| id | id | Unchanged | string |
| name | name | Unchanged | string |
| objective | objective | Unchanged | string |
| start_date | start_date | Unchanged | string (date) |
| end_date | end_date | Unchanged | string (date) |
| budget_currency | budget_currency | Unchanged | string |
| budget_total | budget_total | Unchanged | number |
| agency_id | agency_id | Unchanged | string |
| agency_name | agency_name | Unchanged | string |
| advertiser_id | advertiser_id | Unchanged | string |
| advertiser_name | advertiser_name | Unchanged | string |
| product_id | product_id | Unchanged | string |
| product_name | product_name | Unchanged | string |
| product_description | product_description | Unchanged | string |
| campaign_type_id | campaign_type_id | Unchanged | string |
| campaign_type_name | campaign_type_name | Unchanged | string |
| **audience_name** | - | **REMOVED** | - |
| **audience_age_start** | - | **REMOVED** | - |
| **audience_age_end** | - | **REMOVED** | - |
| **audience_gender** | - | **REMOVED** | - |
| **audience_interests** | - | **REMOVED** | - |
| - | **target_audiences** | **NEW** | array[object] |
| **location_type** | - | **REMOVED** | - |
| **locations** | - | **REMOVED** | - |
| - | **target_locations** | **NEW** | array[object] |
| workflow_status_id | workflow_status_id | Unchanged | string |
| workflow_status_name | workflow_status_name | Unchanged | string |
| - | kpi_name1 | **NEW** | string |
| - | kpi_value1 | **NEW** | number |
| - | kpi_name2 | **NEW** | string |
| - | kpi_value2 | **NEW** | number |
| - | kpi_name3 | **NEW** | string |
| - | kpi_value3 | **NEW** | number |
| - | kpi_name4 | **NEW** | string |
| - | kpi_value4 | **NEW** | number |
| - | kpi_name5 | **NEW** | string |
| - | kpi_value5 | **NEW** | number |
| - | dim_custom1 | **NEW** | string |
| - | dim_custom2 | **NEW** | string |
| - | dim_custom3 | **NEW** | string |
| - | dim_custom4 | **NEW** | string |
| - | dim_custom5 | **NEW** | string |
| - | custom_properties | **NEW** | object |

---

### Line Item Fields Comparison

| v2.0 Field | v3.0 Field | Status | Type |
|------------|------------|--------|------|
| id | id | Unchanged | string |
| name | name | Unchanged | string |
| start_date | start_date | Unchanged | string (date) |
| end_date | end_date | Unchanged | string (date) |
| channel | channel | Unchanged | string |
| channel_custom | channel_custom | Unchanged | string |
| vehicle | vehicle | Unchanged | string |
| vehicle_custom | vehicle_custom | Unchanged | string |
| partner | partner | Unchanged | string |
| partner_custom | partner_custom | Unchanged | string |
| media_product | media_product | Unchanged | string |
| media_product_custom | media_product_custom | Unchanged | string |
| location_type | location_type | Unchanged | string (enum) |
| location_name | location_name | Unchanged | string |
| target_audience | target_audience | Unchanged | string |
| adformat | adformat | Unchanged | string |
| adformat_custom | adformat_custom | Unchanged | string |
| kpi | kpi | Unchanged | string |
| kpi_custom | kpi_custom | Unchanged | string |
| - | kpi_value | **NEW** | number |
| dayparts | dayparts | Unchanged | string |
| dayparts_custom | dayparts_custom | Unchanged | string |
| inventory | inventory | Unchanged | string |
| inventory_custom | inventory_custom | Unchanged | string |
| - | buy_type | **NEW** | string |
| - | buy_commitment | **NEW** | string |
| dim_custom1 | dim_custom1 | Unchanged | string |
| dim_custom2 | dim_custom2 | Unchanged | string |
| dim_custom3 | dim_custom3 | Unchanged | string |
| dim_custom4 | dim_custom4 | Unchanged | string |
| dim_custom5 | dim_custom5 | Unchanged | string |
| dim_custom6 | dim_custom6 | Unchanged | string |
| dim_custom7 | dim_custom7 | Unchanged | string |
| dim_custom8 | dim_custom8 | Unchanged | string |
| dim_custom9 | dim_custom9 | Unchanged | string |
| dim_custom10 | dim_custom10 | Unchanged | string |
| - | is_aggregate | **NEW** | boolean |
| - | aggregation_level | **NEW** | string |
| cost_currency | cost_currency | Unchanged | string |
| - | cost_currency_exchange_rate | **NEW** | number |
| cost_total | cost_total | Unchanged | number |
| cost_media | cost_media | Unchanged | number |
| cost_buying | cost_buying | Unchanged | number |
| cost_platform | cost_platform | Unchanged | number |
| cost_data | cost_data | Unchanged | number |
| cost_creative | cost_creative | Unchanged | number |
| cost_custom1-10 | cost_custom1-10 | Unchanged | number (×10) |
| - | cost_minimum | **NEW** | number |
| - | cost_maximum | **NEW** | number |
| metric_impressions | metric_impressions | Unchanged | number |
| metric_clicks | metric_clicks | Unchanged | number |
| metric_views | metric_views | Unchanged | number |
| - | metric_view_starts | **NEW** | number |
| - | metric_view_completions | **NEW** | number |
| - | metric_reach | **NEW** | number |
| - | metric_units | **NEW** | number |
| - | metric_impression_share | **NEW** | number |
| metric_engagements | metric_engagements | Unchanged | number |
| metric_followers | metric_followers | Unchanged | number |
| metric_visits | metric_visits | Unchanged | number |
| metric_leads | metric_leads | Unchanged | number |
| metric_sales | metric_sales | Unchanged | number |
| metric_add_to_cart | metric_add_to_cart | Unchanged | number |
| metric_app_install | metric_app_install | Unchanged | number |
| metric_application_start | metric_application_start | Unchanged | number |
| metric_application_complete | metric_application_complete | Unchanged | number |
| metric_contact_us | metric_contact_us | Unchanged | number |
| metric_download | metric_download | Unchanged | number |
| metric_signup | metric_signup | Unchanged | number |
| - | metric_page_views | **NEW** | number |
| - | metric_likes | **NEW** | number |
| - | metric_shares | **NEW** | number |
| - | metric_comments | **NEW** | number |
| - | metric_conversions | **NEW** | number |
| metric_max_daily_spend | metric_max_daily_spend | Unchanged | number |
| metric_max_daily_impressions | metric_max_daily_impressions | Unchanged | number |
| metric_audience_size | metric_audience_size | Unchanged | number |
| metric_custom1-10 | metric_custom1-10 | Unchanged | number (×10) |
| - | metric_formulas | **NEW** | object |
| - | custom_properties | **NEW** | object |

---

### Dictionary Groups Comparison

| v2.0 Group | v3.0 Group | Status | Structure |
|------------|------------|--------|-----------|
| - | meta_custom_dimensions | **NEW** | custom_field_config (dim_custom1-5) |
| - | campaign_custom_dimensions | **NEW** | custom_field_config (dim_custom1-5) |
| **custom_dimensions** | **lineitem_custom_dimensions** | **RENAMED** | custom_field_config (dim_custom1-10) |
| - | standard_metrics | **NEW** | metric_formula_config (25 metrics) |
| custom_metrics | custom_metrics | **Enhanced** | custom_metric_config (added formula fields) |
| custom_costs | custom_costs | Unchanged | custom_field_config (cost_custom1-10) |

---

## Enum Changes

### location_type (expanded)

**v2.0**: `["Country", "State"]`

**v3.0**: `["Country", "State", "DMA", "County", "Postcode", "Radius", "POI"]`

**SDK Impact**: Validation must accept expanded enum values

---

## New Object Structures

### target_audiences item

```json
{
  "name": "string (required)",
  "description": "string",
  "demo_age_start": "integer",
  "demo_age_end": "integer",
  "demo_gender": "string (enum: Male/Female/Any)",
  "demo_attributes": "string",
  "interest_attributes": "string",
  "intent_attributes": "string",
  "purchase_attributes": "string",
  "content_attributes": "string",
  "exclusion_list": "string",
  "extension_approach": "string",
  "population_size": "integer"
}
```

### target_locations item

```json
{
  "name": "string (required)",
  "description": "string",
  "location_type": "string (enum)",
  "location_list": ["string"],
  "exclusion_type": "string (enum)",
  "exclusion_list": ["string"],
  "population_percent": "number (0-1)"
}
```

### metric_formulas value

```json
{
  "metric_leads": {
    "formula_type": "string",
    "base_metric": "string",
    "coefficient": "number",
    "parameter1": "number",
    "parameter2": "number",
    "parameter3": "number",
    "comments": "string"
  }
}
```

---

## Testing Checklist

### Unit Tests
- [ ] Test v2→v3 migration with all field combinations
- [ ] Test audience name generation logic
- [ ] Test location name generation logic (1, 2, 3, 4+ locations)
- [ ] Test location name truncation at 50 chars
- [ ] Test dictionary rename
- [ ] Test schema validation for v3.0 files
- [ ] Test backward compatibility (SDK reads v2.0 files)

### Integration Tests
- [ ] Test full migration pipeline on real v2.0 files
- [ ] Test validation of migrated v3.0 files
- [ ] Test round-trip (v2→v3→serialize→deserialize)
- [ ] Test formula evaluation engine
- [ ] Test custom properties handling

### Edge Cases
- [ ] Empty audience fields → omit target_audiences
- [ ] Empty locations → omit target_locations
- [ ] Missing location_type → omit in v3.0
- [ ] Very long location names → truncate properly
- [ ] Missing dictionary → no dictionary in v3.0
- [ ] Partial audience data (only name, only age, etc.)

---

## Migration Priority

**Phase 1 (Required - Backward Compatibility)**
1. Schema validation updates
2. Data model updates for breaking changes
3. Migration utility (v2→v3)
4. Serialization/deserialization updates

**Phase 2 (New Features)**
1. Formula evaluation engine
2. KPI tracking functions
3. Custom properties support
4. Extended query capabilities

**Phase 3 (Enhancement)**
1. Analysis tools for new fields
2. Optimization using cost_min/max
3. Multi-currency calculations
4. Aggregate line item support

---

## Version Detection

SDK should detect version from `meta.schema_version`:

```python
def detect_version(mediaplan_json):
    version = mediaplan_json.get("meta", {}).get("schema_version", "1.0")
    return version

def validate(mediaplan_json):
    version = detect_version(mediaplan_json)
    if version == "2.0":
        return validate_v2(mediaplan_json)
    elif version == "3.0":
        return validate_v3(mediaplan_json)
    else:
        # Handle other versions
```

---

## Related Documents

- **MIGRATION_V2_TO_V3.md** - Step-by-step migration instructions with systematic rules
- **README.md** - Full v3.0 feature documentation
- **Schema files** - schemas/3.0/*.schema.json
- **Example file** - examples/example_mediaplan_v3.0.json
