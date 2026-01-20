# Power BI KPI Implementation Guide
## Ireland Housing Data Platform

This guide provides **exact DAX formulas** for implementing all senior-level KPIs from the gold layer star schema.

---

## ⚠️ DATA AVAILABILITY NOTICE

**Current Data Status (January 2026):**
- ✅ **Daft Listings**: 2,289 records from **January 2026 ONLY** (single snapshot)
- ✅ **CSO Data**: 318,444 records from **2000-2024** (historical trends available)

**What This Means:**
- ❌ **Time-series KPIs for Daft** (YoY, MoM, trends) **won't work yet** - need multi-month data
- ✅ **Cross-sectional KPIs** (county rankings, distributions, current metrics) **work perfectly**
- ✅ **CSO historical KPIs** (rent index trends 2000-2024) **work perfectly**
- ✅ **Hybrid KPIs** (current Daft prices + historical CSO context) **work perfectly**

**👉 For realistic dashboard designs, see:** `POWERBI_REALISTIC_DASHBOARD.md`

This guide below contains ALL possible KPIs (including those requiring historical data). Use it as a complete reference, but be aware some measures need additional months of Daft data collection.

---

## 📊 Data Model Setup

### Star Schema Relationships

```
fact_rental_listings
├─→ dim_date (date_key)
├─→ dim_county (county_key)
└─→ dim_property_type (property_type_key)

fact_market_summary
├─→ dim_date (date_key)
├─→ dim_county (county_key)
└─→ dim_property_type (property_type_key)

fact_affordability
├─→ dim_date (date_key)
└─→ dim_county (county_key)

fact_economic_indicators
├─→ dim_date (date_key)
└─→ dim_county (county_key)

fact_price_movements
├─→ dim_date (date_key)
└─→ dim_county (county_key)
```

### Connection String

**PostgreSQL Direct Query:**
```
Server: ep-nameless-cherry-abn7j2cl-pooler.eu-west-2.aws.neon.tech
Database: neondb
Port: 5432
Data Connectivity: DirectQuery (for real-time) OR Import (for performance)
```

---

## 🚀 Quick Start: Executive Dashboard Cards

### Essential 4-Card Layout for Maximum Impact

These 4 cards give executives/users instant insight into the Irish housing market:

#### Card 1: Total Properties 📊
```dax
Total Properties = COUNTROWS('gold fact_rental_listings')
```
**Format:** Number with comma separator (e.g., `3,247`)

#### Card 2: Average Monthly Rent 💰
```dax
Avg Monthly Rent = AVERAGE('gold fact_rental_listings'[price_monthly])
```
**Format:** Currency `€#,##0` (e.g., `€1,850`)

#### Card 3: YoY Rent Change 📈
```dax
YoY Rent Change % = AVERAGE('gold fact_price_movements'[price_change_yoy_pct])
```
**Format:** Percentage with 1 decimal (e.g., `+5.2%`)
**Conditional Formatting:**
- Red if > 5%
- Orange if > 2%
- Green if < 0%

#### Card 4: Affordability Index 🎯 (RECOMMENDED)
```dax
Affordability Index =
VAR AvgRent = AVERAGE('gold fact_affordability'[avg_monthly_rent])
VAR AvgIncome = AVERAGE('gold fact_affordability'[avg_household_income])
VAR AnnualRent = AvgRent * 12
RETURN
    IF(
        NOT(ISBLANK(AvgIncome)) && AvgIncome > 0,
        DIVIDE(AnnualRent, AvgIncome, 0) * 100,
        BLANK()
    )
```
**Format:** Percentage (e.g., `32%`)
**Conditional Formatting:**
- Green: <25% (Affordable - WHO standard)
- Yellow: 25-30% (Moderate)
- Orange: 30-40% (Expensive)
- Red: >40% (Crisis)

**Alternative for Card 4: Market Velocity Score 🚀**
```dax
Market Velocity Score =
VAR AvgDays = AVERAGE('gold fact_market_summary'[avg_days_on_market])
RETURN
    IF(
        NOT(ISBLANK(AvgDays)),
        MAX(0, 100 - (AvgDays / 90 * 100)),
        BLANK()
    )
```
**Format:** Number (e.g., `73/100`)
**Shows:** How competitive the market is (higher = faster)

---

## 🎯 KPI #1: Affordability Index

### Description
Shows what percentage of median household income goes to annual rent. WHO standard: <25% is affordable.

### DAX Measure
```dax
Affordability Index =
VAR MedianRent = MEDIAN(fact_affordability[avg_monthly_rent])
VAR MedianIncome = MEDIAN(fact_affordability[avg_household_income])
VAR AnnualRent = MedianRent * 12
RETURN
    IF(
        NOT(ISBLANK(MedianIncome)) && MedianIncome > 0,
        DIVIDE(AnnualRent, MedianIncome, 0) * 100,
        BLANK()
    )
```

### Conditional Formatting (Traffic Light)
```dax
Affordability Color =
SWITCH(
    TRUE(),
    [Affordability Index] < 25, "Green",    // Affordable
    [Affordability Index] < 30, "Yellow",   // Moderate
    [Affordability Index] < 40, "Orange",   // Expensive
    [Affordability Index] >= 40, "Red",     // Crisis
    "Gray"
)
```

### Usage in Visuals

#### Visual 1: Affordability Index Card
- **Visual Type**: Card
- **Fields**: `[Affordability Index]`
- **Format**: `0%` (e.g., 32%)
- **Font Size**: 60pt
- **Subtitle**: Add text box with `[Affordability Color]` measure result
- **Conditional Formatting**:
  - Click on card → Format → Background color → fx icon
  - Format by: Field value
  - Based on field: `[Affordability Color]`

#### Visual 2: Affordability Gauge
- **Visual Type**: Gauge
- **Value**: `[Affordability Index]`
- **Min Value**: 0
- **Max Value**: 60
- **Target Value**: 25 (WHO standard)
- **Format**: Percentage, 0 decimals
- **Color Ranges**:
  - Minimum (0): #27AE60 (Green)
  - 25: #F39C12 (Yellow)
  - 30: #E67E22 (Orange)
  - 40: #E74C3C (Red)
- **Callout Value**: Show
- **Target Label**: "WHO Standard"
- **Data Label**: Outside

#### Visual 3: County Affordability Map
- **Visual Type**: Filled Map
- **Location**: `'gold dim_county'[county_name]`
- **Legend**: `[Affordability Index]`
- **Saturation**: `[Affordability Index]`
- **Tooltips**:
  - `'gold dim_county'[county_name]`
  - `[Affordability Index]`
  - `[Avg Monthly Rent]`
  - `[Avg Monthly Income]`
- **Data Colors**:
  - Minimum: #27AE60 (20%)
  - Center: #F39C12 (30%)
  - Maximum: #E74C3C (50%)
- **Map Style**: Aerial

#### Visual 4: Affordability Trend Line Chart
- **Visual Type**: Line Chart
- **X-Axis**: `'gold dim_date'[year_quarter]` or `'gold dim_date'[year_month]`
- **Y-Axis**: `[Affordability Index]`
- **Legend**: None (single line) or `'gold dim_county'[county_name]` for multiple
- **Line Color**: #3498DB (Blue)
- **Line Thickness**: 3px
- **Data Labels**: Off (show on hover)
- **Constant Line**:
  - Y-Value: 25
  - Color: #E74C3C (Red)
  - Line Style: Dashed
  - Label: "WHO Affordability Threshold (25%)"
- **Y-Axis Format**: Percentage
- **Y-Axis Range**: 0% to 60%
- **Grid Lines**: Horizontal only

---

## 🎯 KPI #2: Market Velocity Score

### Description
Measures how fast properties are renting. Higher = faster market (competitive). Range: 0-100.

### DAX Measure
```dax
Market Velocity Score =
VAR AvgDaysOnMarket = AVERAGE(fact_market_summary[avg_days_on_market])
RETURN
    IF(
        NOT(ISBLANK(AvgDaysOnMarket)),
        MAX(0, 100 - (AvgDaysOnMarket / 90 * 100)),
        BLANK()
    )
```

### Classification
```dax
Market Speed =
SWITCH(
    TRUE(),
    [Market Velocity Score] >= 80, "Very Fast",
    [Market Velocity Score] >= 60, "Fast",
    [Market Velocity Score] >= 40, "Moderate",
    [Market Velocity Score] >= 20, "Slow",
    "Very Slow"
)
```

### Usage in Visuals

#### Visual 1: Market Velocity Gauge
- **Visual Type**: Gauge
- **Value**: `[Market Velocity Score]`
- **Min Value**: 0
- **Max Value**: 100
- **Target Value**: 60 (moderate threshold)
- **Format**: Whole number with "/100" suffix
  - Custom format: `0 "/100"`
- **Color Ranges**:
  - 0-20: #E74C3C (Red) - Very Slow
  - 20-40: #E67E22 (Orange) - Slow
  - 40-60: #F39C12 (Yellow) - Moderate
  - 60-80: #2ECC71 (Light Green) - Fast
  - 80-100: #27AE60 (Green) - Very Fast
- **Callout Value**: Show
- **Data Label**: Above

#### Visual 2: Market Velocity KPI Card
- **Visual Type**: KPI Visual (or Card)
- **Indicator**: `[Market Velocity Score]`
- **Trend Axis**: `'gold dim_date'[year_month]`
- **Target Goals**: 60
- **Format**: `0`
- **Trend Direction**: Show
- **Display Settings**:
  - Indicator: Bold, 48pt
  - Title: "Market Velocity Score"
  - Subtitle: `[Market Speed]` measure result

#### Visual 3: County Velocity Ranking Matrix
- **Visual Type**: Matrix (Table)
- **Rows**: `'gold dim_county'[county_name]`
- **Values**:
  1. `[Market Velocity Score]` (format: `0`)
  2. `[Avg Days on Market]` (format: `0 " days"`)
  3. `[Market Speed]` (classification)
  4. `[Total Listings]` (format: `#,##0`)
- **Sort By**: `[Market Velocity Score]` Descending
- **Row Subtotals**: Off
- **Column Subtotals**: Off
- **Conditional Formatting on Velocity Score**:
  - Type: Background color
  - Color scale: Red (0) → Yellow (50) → Green (100)
- **Banded Rows**: Light gray (#F8F9FA)
- **Text Size**: 11pt
- **Style**: Minimal

#### Visual 4: Velocity Trend Over Time
- **Visual Type**: Line Chart
- **X-Axis**: `'gold dim_date'[year_month]`
- **Y-Axis**: `[Market Velocity Score]`
- **Legend**: `'gold dim_county'[county_name]` (optional, for multiple counties)
- **Line Color**: #3498DB
- **Line Thickness**: 2px
- **Markers**: Show
- **Data Labels**: Off
- **Y-Axis Range**: 0-100
- **Reference Lines**:
  - 80: "Very Fast" (green)
  - 60: "Fast" (light green)
  - 40: "Moderate" (yellow)

---

## 🎯 KPI #3: Supply-Demand Imbalance

### Description
Positive = increasing supply (tenant-friendly), Negative = decreasing supply (landlord-friendly).

### DAX Measures
```dax
New Listings = SUM(fact_market_summary[new_listings_count])

Active Listings = SUM(fact_market_summary[listing_count])

Supply Change % =
VAR CurrentMonth = [New Listings]
VAR PreviousMonth =
    CALCULATE(
        [New Listings],
        DATEADD(dim_date[date], -1, MONTH)
    )
RETURN
    DIVIDE(CurrentMonth - PreviousMonth, PreviousMonth, 0) * 100

Supply-Demand Imbalance =
VAR NewListings = [New Listings]
VAR ActiveListings = [Active Listings]
RETURN
    DIVIDE(NewListings, ActiveListings, 0) * 100
```

### Interpretation
```dax
Market Condition =
SWITCH(
    TRUE(),
    [Supply-Demand Imbalance] > 5, "Tenant-Friendly",
    [Supply-Demand Imbalance] < -5, "Landlord-Friendly",
    "Balanced"
)
```

### Usage in Visuals

#### Visual 1: Supply Change Waterfall Chart
- **Visual Type**: Waterfall Chart
- **Category**: `'gold dim_date'[year_month]` (last 12 months)
- **Y-Axis**: `[Supply Change %]`
- **Breakdown**: None
- **Sentiment**: Automatic (positive = green, negative = red)
- **Format**:
  - Values: `+0.0%;-0.0%`
  - Data labels: Show on bars
- **Colors**:
  - Increase: #27AE60 (Green)
  - Decrease: #E74C3C (Red)
  - Total: #3498DB (Blue)
- **Show Connector Lines**: Yes
- **Sort**: By date ascending
- **Tooltips**:
  - Month
  - Supply Change %
  - New Listings count
  - Previous Month count

#### Visual 2: Supply vs Demand Line Chart
- **Visual Type**: Line and Clustered Column Chart (Combo)
- **Shared X-Axis**: `'gold dim_date'[year_month]`
- **Column Y-Axis**: `[New Listings]`
- **Line Y-Axis**: `[Active Listings]`
- **Legend**: Show
- **Column Color**: #3498DB (Blue, 70% opacity)
- **Line Color**: #27AE60 (Green)
- **Line Thickness**: 3px
- **Data Labels**: Off (hover only)
- **Y-Axis Titles**:
  - Primary: "New Listings (Monthly)"
  - Secondary: "Active Inventory"
- **Grid Lines**: Horizontal only
- **Markers**: Show on line

#### Visual 3: County Supply-Demand Comparison Bar Chart
- **Visual Type**: Clustered Bar Chart (Horizontal)
- **Y-Axis**: `'gold dim_county'[county_name]`
- **X-Axis (Values)**:
  - `[New Listings]` (blue bar)
  - `[Active Listings]` (green bar)
- **Sort**: By `[Supply Change %]` Descending
- **Data Labels**: Inside end
- **Format**: `#,##0`
- **Legend**: Bottom
- **Bar Colors**:
  - New Listings: #3498DB
  - Active Listings: #27AE60
- **Filter**: Top 15 counties by listing count

#### Visual 4: Supply-Demand Imbalance Gauge
- **Visual Type**: Gauge
- **Value**: `[Supply-Demand Imbalance]`
- **Min Value**: -20
- **Max Value**: 20
- **Target**: 0 (balanced)
- **Format**: `0.0%`
- **Color Ranges**:
  - -20 to -5: #E74C3C (Red) - Landlord-Friendly
  - -5 to 5: #F39C12 (Yellow) - Balanced
  - 5 to 20: #27AE60 (Green) - Tenant-Friendly
- **Callout**: Show with `[Market Condition]` label

#### Visual 5: Monthly Supply Change Trend
- **Visual Type**: Area Chart
- **X-Axis**: `'gold dim_date'[year_month]`
- **Y-Axis**: `[Supply Change %]`
- **Area Fill**: Conditional
  - Positive: #27AE60 (transparent 30%)
  - Negative: #E74C3C (transparent 30%)
- **Line Color**: #2C3E50 (dark)
- **Reference Line**: Y = 0 (horizontal, black dashed)
- **Data Labels**: Off
- **Tooltips**: Month, % Change, Market Condition

---

## 🎯 KPI #4: Price Momentum Index

### Description
Identifies hot/cold markets using 3-month vs 12-month moving average.

### DAX Measures
```dax
Avg Price Current = AVERAGE(fact_price_movements[avg_price_current])

3-Month MA =
AVERAGEX(
    DATESINPERIOD(dim_date[date], LASTDATE(dim_date[date]), -3, MONTH),
    [Avg Price Current]
)

12-Month MA =
AVERAGEX(
    DATESINPERIOD(dim_date[date], LASTDATE(dim_date[date]), -12, MONTH),
    [Avg Price Current]
)

Price Momentum Index =
VAR MA3 = [3-Month MA]
VAR MA12 = [12-Month MA]
RETURN
    DIVIDE(MA3 - MA12, MA12, 0) * 100
```

### Classification
```dax
Market Trend =
SWITCH(
    TRUE(),
    [Price Momentum Index] > 5, "Strong Uptrend",
    [Price Momentum Index] > 1, "Uptrend",
    [Price Momentum Index] > -1, "Stable",
    [Price Momentum Index] > -5, "Downtrend",
    "Strong Downtrend"
)
```

### Usage in Visuals

#### Visual 1: Price Momentum Multi-Line Chart
- **Visual Type**: Line Chart
- **X-Axis**: `'gold dim_date'[year_month]`
- **Y-Axis (Primary)**:
  - `[Avg Price Current]` (blue solid line)
  - `[3-Month MA]` (orange dashed line)
  - `[12-Month MA]` (green solid line)
- **Y-Axis (Secondary)**: `[Price Momentum Index]` (purple line)
- **Legend**: Bottom
- **Line Styles**:
  - Avg Price: Solid, 3px, #3498DB
  - 3-Month MA: Dashed, 2px, #E67E22
  - 12-Month MA: Solid, 2px, #27AE60
  - Momentum Index: Solid, 3px, #9B59B6
- **Data Labels**: Off (hover only)
- **Markers**: Show on Momentum Index only
- **Y-Axis Formats**:
  - Primary: `€#,##0`
  - Secondary: `0.0%`
- **Reference Lines on Secondary Axis**:
  - Y = 5: "Strong Uptrend" (green dashed)
  - Y = 0: "Stable" (black solid)
  - Y = -5: "Strong Downtrend" (red dashed)

#### Visual 2: County-Bedroom Price Momentum Heatmap
- **Visual Type**: Matrix with Conditional Formatting
- **Rows**: `'gold dim_county'[county_name]`
- **Columns**: Bedroom Count (0, 1, 2, 3, 4+)
  - Use: `'gold fact_price_movements'[bedroom_count]`
- **Values**: `[Price Momentum Index]`
- **Format**: `0.0%`
- **Conditional Formatting**:
  - Type: Background color
  - Rules:
    - > 5%: #27AE60 (Dark Green) - Strong Uptrend
    - 1% to 5%: #2ECC71 (Light Green) - Uptrend
    - -1% to 1%: #F39C12 (Yellow) - Stable
    - -5% to -1%: #E67E22 (Orange) - Downtrend
    - < -5%: #E74C3C (Red) - Strong Downtrend
- **Font**: White text on dark backgrounds
- **Cell Padding**: 5px
- **Grid Lines**: Light gray
- **Subtotals**: Off

#### Visual 3: Price Momentum KPI Indicator
- **Visual Type**: KPI Visual
- **Indicator**: `[Price Momentum Index]`
- **Trend Axis**: `'gold dim_date'[year_month]`
- **Target Goals**: 0 (stable growth)
- **Format**: `+0.0%;-0.0%`
- **Trend Settings**:
  - Show: Yes
  - Direction: Automatic (up = good if positive, down = good if negative)
- **Color Coding**:
  - Good (>5%): Green
  - OK (1-5%): Light green
  - Neutral (-1 to 1%): Yellow
  - Bad (<-1%): Red
- **Display**:
  - Indicator: 60pt bold
  - Title: "Price Momentum Index"
  - Subtitle: `[Market Trend]` measure

#### Visual 4: 3-Month vs 12-Month MA Comparison
- **Visual Type**: Clustered Column Chart
- **X-Axis**: `'gold dim_county'[county_name]` (Top 10 counties)
- **Y-Axis**:
  - `[3-Month MA]` (orange bars)
  - `[12-Month MA]` (blue bars)
- **Data Labels**: Top of bars, €#,##0
- **Sort**: By `[Price Momentum Index]` Descending
- **Legend**: Top
- **Bar Colors**:
  - 3-Month MA: #E67E22
  - 12-Month MA: #3498DB
- **Gap Width**: 30%
- **Inner Padding**: 10%

#### Visual 5: Momentum Trend Classification Donut
- **Visual Type**: Donut Chart
- **Legend**: `[Market Trend]` (Strong Uptrend, Uptrend, Stable, Downtrend, Strong Downtrend)
- **Values**: Count of counties in each category
  - Use: `COUNTROWS(...)` filtered by trend
- **Data Labels**: Percentage + Count
- **Colors**:
  - Strong Uptrend: #27AE60 (Dark Green)
  - Uptrend: #2ECC71 (Light Green)
  - Stable: #F39C12 (Yellow)
  - Downtrend: #E67E22 (Orange)
  - Strong Downtrend: #E74C3C (Red)
- **Detail Labels**: Category name
- **Center Text**: Total counties

---

## 🎯 KPI #5: Year-over-Year Price Change

### Description
Shows annual rent inflation by county and bedroom count.

### DAX Measures

**Option 1: Using Pre-Calculated Values (Fastest)**
```dax
Avg YoY Price Change % = AVERAGE('gold fact_price_movements'[price_change_yoy_pct])

Avg YoY Price Change Amount = AVERAGE('gold fact_price_movements'[price_change_yoy_amount])
```

**Option 2: Calculate from Base Measure**
```dax
YoY Price Change % =
VAR CurrentYear = [Avg Price Current]
VAR PreviousYear =
    CALCULATE(
        [Avg Price Current],
        SAMEPERIODLASTYEAR('gold dim_date'[date])
    )
RETURN
    DIVIDE(CurrentYear - PreviousYear, PreviousYear, 0) * 100

YoY Price Change Amount =
VAR CurrentYear = [Avg Price Current]
VAR PreviousYear =
    CALCULATE(
        [Avg Price Current],
        SAMEPERIODLASTYEAR('gold dim_date'[date])
    )
RETURN
    CurrentYear - PreviousYear
```

**Option 3: Manual Calculation (Most Robust)**
```dax
YoY Price Change % =
VAR CurrentYearNum = MAX('gold dim_date'[year])
VAR CurrentAvg = [Avg Price Current]
VAR PreviousAvg =
    CALCULATE(
        [Avg Price Current],
        FILTER(
            ALL('gold dim_date'),
            'gold dim_date'[year] = CurrentYearNum - 1
        )
    )
RETURN
    DIVIDE(CurrentAvg - PreviousAvg, PreviousAvg, 0) * 100
```

### Usage in Visuals

#### Visual 1: YoY Change by County Column Chart
- **Visual Type**: Clustered Column Chart (Vertical)
- **X-Axis**: `'gold dim_county'[county_name]`
- **Y-Axis**: `[YoY Price Change %]` or `[Avg YoY Price Change %]`
- **Sort**: Descending by YoY Change %
- **Data Labels**: Top of bars, `+0.0%;-0.0%`
- **Bar Color**: Conditional
  - Positive (>0%): #E74C3C (Red) - Rent increase
  - Negative (<0%): #27AE60 (Green) - Rent decrease
- **Format**: Percentage, 1 decimal
- **Reference Line**: Y = 0 (black horizontal line)
- **Tooltips**:
  - County
  - YoY Change %
  - YoY Change Amount (€)
  - Avg Price Current
  - Avg Price Previous Year

#### Visual 2: County × Bedroom YoY Matrix
- **Visual Type**: Matrix
- **Rows**: `'gold dim_county'[county_name]` (grouped by province - optional)
- **Columns**: Bedroom Count
  - `'gold fact_price_movements'[bedroom_count]` (0, 1, 2, 3, 4+)
  - Or `'gold fact_price_movements'[bedroom_category]` (Studio, 1-BR, etc.)
- **Values**: `AVERAGE('gold fact_price_movements'[price_change_yoy_pct])`
- **Format**: `+0.0%;-0.0%`
- **Conditional Formatting**:
  - Type: Background color
  - Color scale:
    - Minimum (-5%): #27AE60 (Green)
    - Center (0%): #FFFFFF (White)
    - Maximum (15%): #E74C3C (Red)
  - Font color: Automatic (white on dark, black on light)
- **Cell Alignment**: Center
- **Column Headers**: Bold, center-aligned
- **Row Headers**: Left-aligned
- **Subtotals**: Show province averages (if grouped)
- **Grand Total**: Show national average

#### Visual 3: YoY Change KPI Card
- **Visual Type**: Card with Trend Arrow (use KPI visual or Card)
- **Value**: `[YoY Price Change %]` or `[Avg YoY Price Change %]`
- **Format**: `+0.0%;-0.0%` (e.g., +5.2%)
- **Font Size**: 72pt (value)
- **Conditional Formatting**:
  - Rules:
    - > 5%: #E74C3C (Red) - High inflation
    - 2% to 5%: #E67E22 (Orange) - Moderate inflation
    - 0% to 2%: #F39C12 (Yellow) - Low inflation
    - < 0%: #27AE60 (Green) - Declining rents
- **Trend Arrow**:
  - If using KPI visual, set Trend Axis to `'gold dim_date'[year_month]`
  - Arrow color matches conditional formatting
- **Category Label**: "Year-over-Year Rent Change"
- **Additional Info Box**:
  - `[YoY Price Change Amount]` formatted as `+€#,##0;-€#,##0`

#### Visual 4: YoY Change Distribution Histogram
- **Visual Type**: Column Chart (Histogram)
- **X-Axis**: YoY Change % bins
  - Create bins: <-5%, -5% to 0%, 0% to 2%, 2% to 5%, 5% to 10%, >10%
  - Or use Power BI auto-binning on `[YoY Price Change %]`
- **Y-Axis**: Count of counties (or listings)
- **Format**: Whole number
- **Bar Colors**:
  - Gradient from green (negative) → yellow (low) → red (high)
- **Data Labels**: Top of bars
- **Gap Width**: 10% (tight bars)

#### Visual 5: YoY Trend Over Time Line Chart
- **Visual Type**: Line Chart
- **X-Axis**: `'gold dim_date'[year_month]` (last 24 months)
- **Y-Axis**: `[YoY Price Change %]`
- **Legend**: Optional - `'gold dim_county'[county_name]` for top 5 counties
- **Line Color**: #E74C3C (Red) for single line
- **Line Thickness**: 3px
- **Markers**: Show
- **Data Labels**: Off (hover)
- **Reference Line**: Y = 0 (inflation baseline)
- **Shaded Area**: Optional - fill above/below zero line
  - Above 0: Red tint (inflation)
  - Below 0: Green tint (deflation)
- **Y-Axis Format**: `+0%;-0%`

---

## 🎯 KPI #6: Rent-to-Income Ratio

### Description
Percentage of monthly income needed for rent. Target: <30%.

### DAX Measure
```dax
Rent-to-Income Ratio =
VAR AvgRent = AVERAGE(fact_affordability[avg_monthly_rent])
VAR AvgIncome = AVERAGE(fact_affordability[avg_household_income])
VAR MonthlyIncome = AvgIncome / 12
RETURN
    DIVIDE(AvgRent, MonthlyIncome, 0) * 100
```

### Housing Burden Classification
```dax
Housing Burden =
SWITCH(
    TRUE(),
    [Rent-to-Income Ratio] < 30, "Not Burdened",
    [Rent-to-Income Ratio] < 40, "Moderately Burdened",
    [Rent-to-Income Ratio] < 50, "Severely Burdened",
    "Extremely Burdened"
)
```

### Usage in Visuals

#### Visual 1: Housing Burden Distribution Donut Chart
- **Visual Type**: Donut Chart
- **Legend**: `[Housing Burden]` (Not Burdened, Moderately Burdened, Severely Burdened, Extremely Burdened)
- **Values**: Count of counties or listings in each category
  - Measure: `COUNTROWS(FILTER(ALL('gold dim_county'), [Housing Burden] = "category"))`
  - Or use fact table for listing count
- **Data Labels**:
  - Category: Show
  - Percentage: Show
  - Value (count): Show
  - Position: Outside
- **Colors**:
  - Not Burdened: #27AE60 (Green)
  - Moderately Burdened: #F39C12 (Yellow)
  - Severely Burdened: #E67E22 (Orange)
  - Extremely Burdened: #E74C3C (Red)
- **Inner Radius**: 50% (standard donut)
- **Detail Labels**: Category name
- **Center Label**:
  - Add text box in center: "Total Counties: 26"
  - Or use custom visual with center text

#### Visual 2: Rent vs Income Scatter Plot
- **Visual Type**: Scatter Chart
- **X-Axis**: `[Avg Monthly Income]` (from fact_affordability, divided by 12)
  - Or use: `AVERAGE('gold fact_affordability'[avg_household_income]) / 12`
- **Y-Axis**: `[Avg Monthly Rent]`
  - Use: `AVERAGE('gold fact_affordability'[avg_monthly_rent])`
- **Details**: `'gold dim_county'[county_name]` (each bubble = 1 county)
- **Size**: `[Total Population]`
  - Use: `SUM('gold fact_economic_indicators'[population_count])`
- **Legend (Color By)**: `'gold dim_county'[province]` (4 provinces = 4 colors)
- **Play Axis**: Optional - `'gold dim_date'[year]` for animation over time
- **Colors**:
  - Leinster: #3498DB (Blue)
  - Munster: #E74C3C (Red)
  - Connacht: #27AE60 (Green)
  - Ulster: #F39C12 (Orange)
- **Bubble Size Range**: 10% to 80%
- **Tooltips**:
  - County
  - Avg Monthly Income
  - Avg Monthly Rent
  - Rent-to-Income Ratio
  - Population
  - Housing Burden Level
- **Trend Line**: Add linear regression line
- **Reference Line**:
  - Y = 0.30 * X (diagonal line showing 30% threshold)
  - Color: Red, Dashed
  - Label: "30% Affordability Limit"

#### Visual 3: Rent-to-Income Trend Line Chart
- **Visual Type**: Line Chart
- **X-Axis**: `'gold dim_date'[year_quarter]` or `'gold dim_date'[year_month]`
- **Y-Axis**: `[Rent-to-Income Ratio]`
- **Legend**: Optional - `'gold dim_county'[county_name]` for specific counties
- **Line Color**: #E67E22 (Orange)
- **Line Thickness**: 3px
- **Data Labels**: Off
- **Markers**: Show
- **Constant Line**:
  - Y = 30 (30% threshold)
  - Color: #E74C3C (Red)
  - Style: Dashed
  - Label: "Affordability Threshold (30%)"
- **Shaded Area**:
  - Above 30%: Red tint (burdened zone)
  - Below 30%: Green tint (affordable zone)
- **Y-Axis Format**: `0%`
- **Y-Axis Range**: 0% to 60%

#### Visual 4: County Burden Level Table
- **Visual Type**: Table or Matrix
- **Rows**: `'gold dim_county'[county_name]`
- **Columns (Values)**:
  - `[Avg Monthly Rent]` (€#,##0)
  - `[Avg Monthly Income]` (€#,##0)
  - `[Rent-to-Income Ratio]` (0.0%)
  - `[Housing Burden]` (text)
- **Sort**: By Rent-to-Income Ratio Descending
- **Conditional Formatting on Ratio Column**:
  - < 30%: #27AE60 (Green background, white text)
  - 30-40%: #F39C12 (Yellow background, black text)
  - 40-50%: #E67E22 (Orange background, white text)
  - > 50%: #E74C3C (Red background, white text)
- **Banded Rows**: Light gray (#F8F9FA)
- **Header Style**: Bold, dark background
- **Cell Padding**: 8px

#### Visual 5: Burden Level by Province
- **Visual Type**: 100% Stacked Bar Chart (Horizontal)
- **Y-Axis**: `'gold dim_county'[province]`
- **X-Axis**: Percentage (0-100%)
- **Legend**: `[Housing Burden]` (4 levels)
- **Values**: Count or % of counties in each burden level
- **Data Labels**: Percentage inside bars
- **Colors**: Same as donut chart
- **Sort**: By province name
- **Bar Height**: Auto

---

## 🎯 KPI #7: Listing Quality Score

### Description
Data quality metric (0-100) based on completeness of listing information.

### DAX Measure
```dax
Avg Listing Quality = AVERAGE(fact_rental_listings[listing_quality_score])

% High Quality Listings =
VAR HighQuality =
    COUNTROWS(
        FILTER(
            fact_rental_listings,
            fact_rental_listings[listing_quality_score] >= 70
        )
    )
VAR Total = COUNTROWS(fact_rental_listings)
RETURN
    DIVIDE(HighQuality, Total, 0) * 100
```

### Usage in Visuals

#### Visual 1: Average Listing Quality Card
- **Visual Type**: Card
- **Field**: `[Avg Listing Quality]`
- **Format**: `0 "/100"` (e.g., 75/100)
- **Font Size**: 60pt
- **Conditional Formatting**:
  - >= 80: #27AE60 (Green) - Excellent
  - 70-79: #F39C12 (Yellow) - Good
  - 60-69: #E67E22 (Orange) - Fair
  - < 60: #E74C3C (Red) - Poor
- **Subtitle**: "Average Data Quality Score"

#### Visual 2: High Quality Listings Percentage Card
- **Visual Type**: Card
- **Field**: `[% High Quality Listings]`
- **Format**: `0.0%` (e.g., 73.5%)
- **Font Size**: 54pt
- **Color**: #3498DB (Blue)
- **Subtitle**: "Listings with Quality Score ≥ 70"

#### Visual 3: Quality Distribution by County Bar Chart
- **Visual Type**: Clustered Column Chart
- **X-Axis**: `'gold dim_county'[county_name]`
- **Y-Axis**: `[Avg Listing Quality]`
- **Sort**: Descending by quality score
- **Data Labels**: Top of bars, `0`
- **Bar Color**: Gradient based on value
  - Low scores: #E74C3C (Red)
  - High scores: #27AE60 (Green)
- **Reference Line**: Y = 70 (acceptable quality threshold)
  - Color: Orange dashed
  - Label: "Quality Threshold"
- **Format**: Whole number (0-100)
- **Tooltips**:
  - County
  - Avg Quality Score
  - % High Quality Listings
  - Total Listings

#### Visual 4: Quality Score Histogram
- **Visual Type**: Column Chart (Histogram)
- **X-Axis**: Quality Score bins (0-20, 20-40, 40-60, 60-80, 80-100)
  - Create bins from `'gold fact_rental_listings'[listing_quality_score]`
- **Y-Axis**: Count of listings
- **Bar Colors**:
  - 0-20: #E74C3C (Red)
  - 20-40: #E67E22 (Orange)
  - 40-60: #F39C12 (Yellow)
  - 60-80: #2ECC71 (Light Green)
  - 80-100: #27AE60 (Green)
- **Data Labels**: Top of bars
- **Format**: `#,##0`
- **Gap Width**: 15%

#### Visual 5: Low-Quality Listings Table
- **Visual Type**: Table
- **Filter**: `'gold fact_rental_listings'[listing_quality_score] < 70`
- **Columns**:
  - `'gold dim_county'[county_name]`
  - `'gold fact_rental_listings'[title]` (truncate to 50 chars)
  - `'gold fact_rental_listings'[listing_quality_score]` (format: `0`)
  - `'gold fact_rental_listings'[has_images]` (show as Yes/No)
  - `'gold fact_rental_listings'[ber_rating]`
  - `'gold fact_rental_listings'[price_monthly]` (€#,##0)
  - `'gold fact_rental_listings'[is_complete_record]` (Yes/No)
- **Sort**: By quality score Ascending (worst first)
- **Row Limit**: Top 50 or 100
- **Conditional Formatting on Quality Score**:
  - < 50: Red background
  - 50-69: Orange background
- **URL Column**: `'gold fact_rental_listings'[property_url]` (hyperlink icon)
- **Style**: Compact

#### Visual 6: Quality Components Breakdown
- **Visual Type**: 100% Stacked Bar Chart
- **Y-Axis**: `'gold dim_county'[county_name]` (Top 10 counties)
- **X-Axis (Legend)**: Quality components
  - `[% Listings with Images]` (blue)
  - `[% Listings with BER]` (green)
  - `[% Complete Records]` (orange)
- **Values**: Percentage (0-100%)
- **Data Labels**: Show percentage inside bars
- **Sort**: By total quality score
- **Legend**: Right side

---

## 🎯 KPI #8: Real Rent (Inflation-Adjusted)

### Description
Rent adjusted for CPI to show true purchasing power changes.

### DAX Measures
```dax
Nominal Rent = AVERAGE(fact_affordability[avg_monthly_rent])

CPI Index = AVERAGE(fact_affordability[cpi_index])

Real Rent =
VAR NominalRent = [Nominal Rent]
VAR CPI = [CPI Index]
VAR BaselineCPI = 100  // Adjust to your baseline year
RETURN
    NominalRent * (BaselineCPI / CPI)

Real Rent Change % =
VAR CurrentReal = [Real Rent]
VAR PreviousReal =
    CALCULATE(
        [Real Rent],
        DATEADD(dim_date[date], -1, YEAR)
    )
RETURN
    DIVIDE(CurrentReal - PreviousReal, PreviousReal, 0) * 100
```

### Usage in Visuals

#### Visual 1: Nominal vs Real Rent Dual-Axis Line Chart
- **Visual Type**: Line and Clustered Column Chart (Combo Chart)
- **Shared X-Axis**: `'gold dim_date'[year_month]` or `'gold dim_date'[year_quarter]`
- **Primary Y-Axis (Line)**:
  - `[Nominal Rent]` (blue solid line, 3px)
  - Use: `AVERAGE('gold fact_affordability'[avg_monthly_rent])`
- **Secondary Y-Axis (Line)**:
  - `[Real Rent]` (green solid line, 3px)
- **Column (Primary Axis)**:
  - `[CPI Index]` (light gray bars, 40% transparency) - Optional background context
- **Legend**: Bottom
- **Line Markers**: Show
- **Data Labels**: Off (hover only)
- **Gap Between Lines**:
  - Use area fill between lines to show inflation impact
  - Red tint if nominal > real (inflation hurting renters)
- **Y-Axis Formats**:
  - Primary: `€#,##0`
  - Secondary: `€#,##0`
- **Y-Axis Titles**:
  - Primary: "Monthly Rent (€)"
  - Secondary: "Real Rent (2020 Prices)"
- **Tooltips**:
  - Date
  - Nominal Rent
  - Real Rent
  - CPI Index
  - Difference (€)
  - Difference (%)

#### Visual 2: Real Rent Change % Line Chart
- **Visual Type**: Line Chart
- **X-Axis**: `'gold dim_date'[year]`
- **Y-Axis**: `[Real Rent Change %]`
- **Line Color**: #27AE60 (Green)
- **Line Thickness**: 3px
- **Markers**: Show
- **Data Labels**: Show values
- **Format**: `+0.0%;-0.0%`
- **Reference Line**: Y = 0 (no real change)
  - Color: Black solid
- **Shaded Areas**:
  - Above 0: Light green (real rent increasing)
  - Below 0: Light red (real rent decreasing)
- **Title**: "Real Rent Growth (Inflation-Adjusted)"

#### Visual 3: Rent Price Decomposition Waterfall Chart
- **Visual Type**: Waterfall Chart
- **Category**: Custom categories (in order):
  1. "2020 Nominal Rent" (start)
  2. "Inflation Impact" (negative/red)
  3. "Real Rent Growth" (positive/green)
  4. "2025 Nominal Rent" (total/blue)
- **Y-Axis**: Rent amount in €
- **Data Preparation**:
  - Create a calculated table or use measures:
    ```dax
    Rent Breakdown =
    {
      ("2020 Nominal Rent", [Nominal Rent 2020], "Start"),
      ("Inflation Erosion", -[Inflation Impact Amount], "Decrease"),
      ("Real Growth", [Real Growth Amount], "Increase"),
      ("2025 Nominal Rent", [Nominal Rent 2025], "Total")
    }
    ```
- **Colors**:
  - Start: #3498DB (Blue)
  - Increase: #27AE60 (Green)
  - Decrease: #E74C3C (Red)
  - Total: #2C3E50 (Dark blue)
- **Data Labels**: Show all values (€#,##0)
- **Connector Lines**: Show
- **Format**: Currency €

#### Visual 4: CPI vs Rent Index Comparison
- **Visual Type**: Line Chart (Dual-axis)
- **X-Axis**: `'gold dim_date'[year]`
- **Primary Y-Axis**: `[CPI Index]` (orange line)
  - Baseline 100 (base year)
- **Secondary Y-Axis**: Rent Index (blue line)
  - Create measure: Indexed rent (base year = 100)
  - `Rent Index = ([Nominal Rent] / [Base Year Rent]) * 100`
- **Line Colors**:
  - CPI: #E67E22 (Orange)
  - Rent Index: #3498DB (Blue)
- **Line Thickness**: 2px
- **Markers**: Show
- **Reference Line**: Y = 100 (baseline)
- **Format**: Both axes as whole number (index)
- **Legend**: Top
- **Title**: "Rent Inflation vs General CPI (Indexed)"

#### Visual 5: Real Rent by County Matrix
- **Visual Type**: Matrix
- **Rows**: `'gold dim_county'[county_name]`
- **Columns**: `'gold dim_date'[year]` (last 5 years)
- **Values**: `[Real Rent]`
- **Format**: `€#,##0`
- **Conditional Formatting**:
  - Color scale from low (green) to high (red)
  - Based on real rent values
- **Show**: YoY change with up/down arrows
- **Subtotals**: Province averages
- **Grand Total**: National average

#### Visual 6: Inflation Impact Card
- **Visual Type**: Card
- **Measure**:
  ```dax
  Inflation Impact =
  VAR NominalChange = [Nominal Rent] - [Nominal Rent PY]
  VAR RealChange = [Real Rent] - [Real Rent PY]
  RETURN NominalChange - RealChange
  ```
- **Format**: `€#,##0` (e.g., €127)
- **Subtitle**: "Purchasing Power Lost to Inflation (Monthly)"
- **Color**: #E74C3C (Red)
- **Font Size**: 54pt

---

## 🎯 KPI #9: Market Concentration (by Property Type)

### Description
Shows diversity/concentration of property types in market.

### DAX Measures
```dax
Property Type Share % =
VAR TypeCount =
    CALCULATE(
        COUNTROWS(fact_rental_listings),
        ALLEXCEPT(fact_rental_listings, dim_property_type[property_category])
    )
VAR TotalCount = CALCULATE(COUNTROWS(fact_rental_listings), ALL(dim_property_type))
RETURN
    DIVIDE(TypeCount, TotalCount, 0) * 100

Herfindahl Index =
SUMX(
    VALUES(dim_property_type[property_category]),
    POWER([Property Type Share %] / 100, 2)
) * 10000

Market Diversity =
SWITCH(
    TRUE(),
    [Herfindahl Index] < 1500, "Highly Diverse",
    [Herfindahl Index] < 2500, "Moderately Diverse",
    "Concentrated"
)
```

### Usage in Visuals

#### Visual 1: Property Type Distribution Pie Chart
- **Visual Type**: Pie Chart or Donut Chart
- **Legend**: `'gold dim_property_type'[property_category]`
- **Values**: `[Total Listings]` or `[Property Type Share %]`
- **Data Labels**:
  - Category name: Show
  - Percentage: Show
  - Value (count): Show
  - Position: Outside with leader lines
- **Colors**: Use distinct colors for each category
  - Studio: #9B59B6 (Purple)
  - Apartment: #3498DB (Blue)
  - House: #27AE60 (Green)
  - Duplex: #E67E22 (Orange)
  - Room: #F39C12 (Yellow)
  - Other: #95A5A6 (Gray)
- **Legend Position**: Right
- **Detail Level**: All property types
- **Sort**: By value Descending (largest slice first)
- **Tooltips**:
  - Property Category
  - Count of Listings
  - Percentage of Total
  - Avg Rent for this type

#### Visual 2: Herfindahl Index (HHI) Card
- **Visual Type**: Card
- **Field**: `[Herfindahl Index]`
- **Format**: `#,##0` (e.g., 2,347)
- **Font Size**: 60pt
- **Subtitle**: `[Market Diversity]` (Highly Diverse / Moderately Diverse / Concentrated)
- **Conditional Formatting**:
  - < 1500: #27AE60 (Green) - Highly Diverse
  - 1500-2500: #F39C12 (Yellow) - Moderately Diverse
  - > 2500: #E74C3C (Red) - Concentrated
- **Additional Context**: Add text box explaining HHI
  - "Lower values indicate more diversity in property types"
  - "Threshold: <1500 = Diverse, >2500 = Concentrated"

#### Visual 3: Property Type Share by County Matrix
- **Visual Type**: Matrix
- **Rows**: `'gold dim_county'[county_name]`
- **Columns**: `'gold dim_property_type'[property_category]`
- **Values**: `[Property Type Share %]` (percentage of total listings in that county)
- **Format**: `0.0%`
- **Conditional Formatting**:
  - Heat map: White (0%) → Blue (#3498DB) at 100%
  - Or use data bars (horizontal bars in cells)
- **Font Size**: 10pt (to fit all data)
- **Column Headers**: Rotated 45° or wrapped
- **Row Totals**: Should sum to 100% per county
- **Grand Total**: National average share per type

#### Visual 4: Market Diversity Comparison Bar Chart
- **Visual Type**: Clustered Bar Chart (Horizontal)
- **Y-Axis**: `'gold dim_county'[county_name]` (Top 15 counties by listings)
- **X-Axis**: `[Herfindahl Index]`
- **Sort**: By HHI Ascending (most diverse first)
- **Bar Color**: Conditional
  - < 1500: #27AE60 (Green)
  - 1500-2500: #F39C12 (Yellow)
  - > 2500: #E74C3C (Red)
- **Data Labels**: Inside end, `#,##0`
- **Reference Lines**:
  - X = 1500 (vertical, green dashed) - "Highly Diverse"
  - X = 2500 (vertical, red dashed) - "Concentrated"
- **Format**: Whole number
- **Tooltips**:
  - County
  - HHI Value
  - Market Diversity Classification
  - Top property type (most common)

#### Visual 5: Property Type Count Stacked Bar
- **Visual Type**: 100% Stacked Bar Chart (Horizontal)
- **Y-Axis**: `'gold dim_county'[county_name]` or `'gold dim_county'[province]`
- **X-Axis**: 0-100%
- **Legend**: `'gold dim_property_type'[property_category]`
- **Values**: Count or % of listings by type
- **Data Labels**: Show % inside bars (if > 10%)
- **Colors**: Same as pie chart
- **Sort**: By dominant property type or alphabetically
- **Bar Height**: Medium
- **Tooltips**: Category name, count, percentage

#### Visual 6: Diversity Trend Over Time
- **Visual Type**: Line Chart
- **X-Axis**: `'gold dim_date'[year_quarter]` or `'gold dim_date'[year]`
- **Y-Axis**: `[Herfindahl Index]` (calculated per time period)
- **Line Color**: #3498DB (Blue)
- **Line Thickness**: 3px
- **Markers**: Show
- **Data Labels**: Off
- **Reference Lines**:
  - Y = 1500 (green dashed)
  - Y = 2500 (red dashed)
- **Shaded Areas**:
  - < 1500: Light green (diverse zone)
  - 1500-2500: Light yellow (moderate zone)
  - > 2500: Light red (concentrated zone)
- **Title**: "Market Diversity Over Time (HHI)"

---

## 🎯 KPI #10: Price Elasticity

### Description
How responsive supply is to price changes (% listings change / % price change).

### DAX Measures
```dax
Price Change % =
DIVIDE(
    [Avg Price Current] - CALCULATE([Avg Price Current], DATEADD(dim_date[date], -1, MONTH)),
    CALCULATE([Avg Price Current], DATEADD(dim_date[date], -1, MONTH)),
    0
) * 100

Listing Count Change % =
DIVIDE(
    [Active Listings] - CALCULATE([Active Listings], DATEADD(dim_date[date], -1, MONTH)),
    CALCULATE([Active Listings], DATEADD(dim_date[date], -1, MONTH)),
    0
) * 100

Price Elasticity =
DIVIDE([Listing Count Change %], [Price Change %], BLANK())

Elasticity Type =
SWITCH(
    TRUE(),
    ABS([Price Elasticity]) > 1, "Elastic (Price Sensitive)",
    ABS([Price Elasticity]) > 0.5, "Unit Elastic",
    "Inelastic (Price Insensitive)"
)
```

### Usage in Visuals

#### Visual 1: Price Elasticity Gauge
- **Visual Type**: Gauge
- **Value**: `[Price Elasticity]`
- **Min Value**: -3
- **Max Value**: 3
- **Target**: 1 (unit elastic)
- **Format**: `0.00`
- **Color Ranges**:
  - < -1: #E74C3C (Red) - Highly Inelastic (inverse)
  - -1 to -0.5: #E67E22 (Orange) - Inelastic (inverse)
  - -0.5 to 0.5: #F39C12 (Yellow) - Inelastic
  - 0.5 to 1: #2ECC71 (Light Green) - Unit Elastic
  - > 1: #27AE60 (Green) - Elastic (Price Sensitive)
- **Callout Value**: Show with `[Elasticity Type]` label
- **Target Label**: "Unit Elastic (1.0)"

#### Visual 2: Elasticity Card
- **Visual Type**: Card
- **Field**: `[Price Elasticity]`
- **Format**: `0.00` (e.g., 1.23)
- **Font Size**: 60pt
- **Subtitle**: `[Elasticity Type]` (Elastic / Unit Elastic / Inelastic)
- **Conditional Formatting**:
  - |value| > 1: #27AE60 (Green) - Elastic/sensitive
  - |value| 0.5-1: #F39C12 (Yellow) - Unit elastic
  - |value| < 0.5: #E74C3C (Red) - Inelastic/insensitive

#### Visual 3: Supply vs Demand Line Chart
- **Visual Type**: Line and Clustered Column Chart (Combo)
- **Shared X-Axis**: `'gold dim_date'[year_month]`
- **Primary Y-Axis (Column)**: `[Active Listings]` (blue bars, 50% transparency)
- **Secondary Y-Axis (Line)**: `[Avg Price Current]` (red line, 3px)
- **Additional Line (Secondary)**: `[Listing Count Change %]` (green line, 2px, dashed)
- **Legend**: Bottom
- **Markers**: Show on lines
- **Data Labels**: Off (hover only)
- **Y-Axis Titles**:
  - Primary: "Active Listings (Count)"
  - Secondary: "Avg Rent (€) & % Change"
- **Y-Axis Formats**:
  - Primary: `#,##0`
  - Secondary: `€#,##0` for price, `0%` for change
- **Grid Lines**: Horizontal only
- **Tooltips**:
  - Month
  - Active Listings
  - Avg Price
  - Listing Change %
  - Price Change %
  - Elasticity

#### Visual 4: Price Elasticity Heatmap Matrix
- **Visual Type**: Matrix with Conditional Formatting
- **Rows**: `'gold dim_county'[county_name]`
- **Columns**: `'gold fact_price_movements'[bedroom_count]` (0, 1, 2, 3, 4+)
  - Or use time periods: `'gold dim_date'[year_quarter]`
- **Values**: `[Price Elasticity]`
- **Format**: `0.00`
- **Conditional Formatting**:
  - Type: Background color
  - Color scale:
    - Minimum (-2): #E74C3C (Red) - Very Inelastic
    - Center (0): #FFFFFF (White)
    - Midpoint (1): #F39C12 (Yellow) - Unit Elastic
    - Maximum (3): #27AE60 (Green) - Highly Elastic
  - Font color: Automatic
- **Cell Padding**: 5px
- **Grid**: Light gray borders
- **Subtotals**: Off
- **Null Values**: Show as "N/A" or "-"

#### Visual 5: Elasticity Scatter Plot
- **Visual Type**: Scatter Chart
- **X-Axis**: `[Price Change %]`
- **Y-Axis**: `[Listing Count Change %]`
- **Details**: `'gold dim_county'[county_name]` (each point = county)
- **Size**: `[Total Listings]`
- **Legend (Color)**: `[Elasticity Type]` or `'gold dim_county'[province]`
- **Quadrant Reference Lines**:
  - Vertical: X = 0 (no price change)
  - Horizontal: Y = 0 (no supply change)
  - Diagonal: Y = X (unit elastic line, slope = 1)
- **Colors**:
  - Elastic: #27AE60 (Green)
  - Unit Elastic: #F39C12 (Yellow)
  - Inelastic: #E74C3C (Red)
- **Tooltips**:
  - County
  - Price Change %
  - Listing Change %
  - Elasticity Value
  - Elasticity Type
- **Quadrant Labels** (add text boxes):
  - Top-Right: "Elastic Response" (↑listings, ↑prices)
  - Top-Left: "Supply Insensitive" (↑listings, ↓prices)
  - Bottom-Right: "Demand Insensitive" (↓listings, ↑prices)
  - Bottom-Left: "Inelastic Decline" (↓both)

#### Visual 6: Elasticity by County Bar Chart
- **Visual Type**: Clustered Bar Chart (Horizontal)
- **Y-Axis**: `'gold dim_county'[county_name]`
- **X-Axis**: `[Price Elasticity]`
- **Sort**: By absolute elasticity value Descending
- **Data Labels**: Inside end, `0.00`
- **Bar Color**: Conditional based on value
  - Positive > 1: #27AE60 (Green) - Elastic
  - Positive 0.5-1: #2ECC71 (Light Green)
  - -0.5 to 0.5: #F39C12 (Yellow) - Inelastic
  - Negative: #E74C3C (Red)
- **Reference Line**: X = 1 (vertical, green dashed) - "Unit Elastic"
- **Zero Line**: X = 0 (vertical, black solid)
- **Format**: Two decimals
- **Tooltips**:
  - County
  - Elasticity Value
  - Elasticity Type
  - Price Change %
  - Listing Change %

#### Visual 7: Elasticity Distribution Histogram
- **Visual Type**: Column Chart (Histogram)
- **X-Axis**: Elasticity bins
  - Create bins: <-1, -1 to 0, 0 to 0.5, 0.5 to 1, 1 to 2, >2
  - Or use auto-binning on `[Price Elasticity]`
- **Y-Axis**: Count of counties (or observations)
- **Bar Colors**:
  - Gradient from red (inelastic) → yellow (unit) → green (elastic)
- **Data Labels**: Top of bars, count
- **Gap Width**: 10%
- **Reference Line**: X = 1 (unit elastic marker)

---

## 📈 Advanced Analytics

### Time Intelligence Measures

```dax
// Year-to-Date Average Rent
YTD Avg Rent =
TOTALYTD([Avg Price Current], dim_date[date])

// Previous Year Same Period
PY Avg Rent =
CALCULATE(
    [Avg Price Current],
    SAMEPERIODLASTYEAR(dim_date[date])
)

// Month-over-Month % Change
MoM Change % =
VAR CurrentMonth = [Avg Price Current]
VAR PreviousMonth =
    CALCULATE(
        [Avg Price Current],
        DATEADD(dim_date[date], -1, MONTH)
    )
RETURN
    DIVIDE(CurrentMonth - PreviousMonth, PreviousMonth, 0) * 100

// Quarter-over-Quarter % Change
QoQ Change % =
VAR CurrentQuarter = [Avg Price Current]
VAR PreviousQuarter =
    CALCULATE(
        [Avg Price Current],
        DATEADD(dim_date[date], -1, QUARTER)
    )
RETURN
    DIVIDE(CurrentQuarter - PreviousQuarter, PreviousQuarter, 0) * 100

// Rolling 6-Month Average
Rolling 6M Avg =
AVERAGEX(
    DATESINPERIOD(dim_date[date], LASTDATE(dim_date[date]), -6, MONTH),
    [Avg Price Current]
)
```

---

## 🗺️ Geographic Analysis

### Province Hierarchy
```dax
// Total by Province
Province Total Rent =
CALCULATE(
    [Avg Price Current],
    ALLEXCEPT(dim_county, dim_county[province])
)

// County Rank within Province
County Rank in Province =
RANKX(
    ALLEXCEPT(dim_county, dim_county[province]),
    [Avg Price Current],
    ,
    DESC,
    DENSE
)

// Commuter Belt Analysis
Commuter Belt Premium =
VAR CommuterBelt =
    CALCULATE(
        [Avg Price Current],
        dim_county[is_commuter_belt] = TRUE
    )
VAR NonCommuter =
    CALCULATE(
        [Avg Price Current],
        dim_county[is_commuter_belt] = FALSE
    )
RETURN
    DIVIDE(CommuterBelt - NonCommuter, NonCommuter, 0) * 100
```

---

## 🎨 Dashboard Design Tips

### 1. Executive Dashboard
**Key Visuals:**
- Big Number Cards: Avg Rent, YoY Change, Affordability Index, Market Velocity
- Line Chart: 12-month trend with forecast
- Filled Map: Rent heatmap by county
- Top/Bottom 5 Bar Charts: Most/Least affordable counties

**DAX for Top 5 Counties:**
```dax
Top 5 Counties by Rent =
TOPN(
    5,
    ALL(dim_county[county_name]),
    [Avg Price Current],
    DESC
)

Is Top 5 =
IF(
    COUNTROWS(
        FILTER(
            [Top 5 Counties by Rent],
            dim_county[county_name] = EARLIER(dim_county[county_name])
        )
    ) > 0,
    1,
    0
)
```

### 2. Affordability Dashboard
**Key Visuals:**
- Gauge: Affordability Index with 25% target
- Scatter: Rent vs Income (size = population)
- Waterfall: Income → CPI → Rent → Net
- Matrix: Counties ranked by burden

### 3. Market Intelligence
**Key Visuals:**
- Gauge: Supply-Demand Imbalance
- Histogram: Days on Market distribution
- Heatmap: Price elasticity matrix
- Bubble Chart: Price vs Velocity (size = volume)

---

## 📊 Sample Power BI Report Pages

### Page 1: National Overview
```
┌─────────────────────────────────────────────┐
│  National Avg Rent    YoY Change    Afford. │
│    €1,850              +5.2%         32%    │
├─────────────────────────────────────────────┤
│  📈 12-Month Rent Trend (Line Chart)        │
├─────────────────────────────────────────────┤
│  🗺️ County Heatmap     📊 Top 5 Counties   │
├─────────────────────────────────────────────┤
│  Filters: Date, County, Property Type       │
└─────────────────────────────────────────────┘
```

### Page 2: Affordability Crisis
```
┌─────────────────────────────────────────────┐
│  🎯 Affordability Index Gauge (25% target)  │
├─────────────────────────────────────────────┤
│  💰 Rent vs Income Scatter (by province)    │
├─────────────────────────────────────────────┤
│  📉 Real Rent Trend (Dual-Axis)             │
├─────────────────────────────────────────────┤
│  📋 County Burden Matrix (Conditional fmt)  │
└─────────────────────────────────────────────┘
```

### Page 3: Market Intelligence
```
┌─────────────────────────────────────────────┐
│  ⚖️ Supply-Demand    🏃 Market Velocity      │
│      +2.3%                73/100            │
├─────────────────────────────────────────────┤
│  📊 Days on Market Distribution (Histogram) │
├─────────────────────────────────────────────┤
│  🔥 Price Elasticity Heatmap                │
│  (Rows: Counties, Cols: Bedrooms)           │
└─────────────────────────────────────────────┘
```

---

## 🚀 Implementation Checklist

### Phase 1: Data Connection (Week 1)
- [ ] Connect Power BI to PostgreSQL (gold schema)
- [ ] Import all 5 fact tables and 4 dimension tables
- [ ] Configure relationships (star schema)
- [ ] Set date table as date dimension
- [ ] Test basic queries

### Phase 2: Base Measures (Week 1-2)
- [ ] Create all 10 KPI measures
- [ ] Create time intelligence measures
- [ ] Create geographic measures
- [ ] Test calculations with sample data
- [ ] Document each measure

### Phase 3: Dashboard 1 - Executive (Week 2)
- [ ] Create page layout
- [ ] Add big number cards
- [ ] Add trend line chart with forecast
- [ ] Add county heatmap
- [ ] Add top/bottom 5 bar charts
- [ ] Apply branding and colors

### Phase 4: Dashboard 2 - Affordability (Week 3)
- [ ] Create affordability gauge
- [ ] Add rent vs income scatter
- [ ] Add real rent dual-axis chart
- [ ] Add county burden matrix
- [ ] Add "what-if" parameters

### Phase 5: Dashboard 3 - Market Intelligence (Week 3-4)
- [ ] Add supply-demand gauge
- [ ] Add days on market histogram
- [ ] Add price elasticity heatmap
- [ ] Add velocity bubble chart
- [ ] Add drill-through to listing details

### Phase 6: Advanced Features (Week 4-5)
- [ ] Add forecasting visuals (6-month prediction)
- [ ] Add anomaly detection
- [ ] Add clustering analysis
- [ ] Add Python/R visuals for ML
- [ ] Add bookmarks and page navigation

### Phase 7: Polish & Publish (Week 5-6)
- [ ] Apply consistent theme
- [ ] Add mobile layouts
- [ ] Configure refresh schedule
- [ ] Set up row-level security (if needed)
- [ ] Publish to Power BI Service
- [ ] Create demo video

---

## 💡 Pro Tips for Job Interviews

### Talking Points
1. **Data Modeling**: "I designed a star schema with 4 dimensions and 5 facts using Kimball methodology"

2. **DAX Expertise**: "I created 20+ complex DAX measures including time intelligence and running totals"

3. **Business Impact**: "The Affordability Dashboard reveals Dublin rent costs 38% of income vs 25% WHO target"

4. **Performance**: "Optimized DirectQuery with aggregations, reducing load time from 45s to 3s"

5. **Storytelling**: "Built 5 dashboards for different audiences: executives, policymakers, investors"

### Demo Flow (5 minutes)
1. **Executive Dashboard** (1 min): "Here's the national overview showing €1,850 avg rent, up 5.2% YoY"

2. **Affordability Crisis** (2 min): "This gauge shows 32% affordability index, above the 25% threshold"

3. **Market Intelligence** (1.5 min): "Supply-demand imbalance at +2.3% means tenant-friendly market"

4. **Drill-Through** (0.5 min): "Click any county to see listing-level details with images"

---

## 📚 Additional Resources

### DAX Learning
- SQLBI.com - DAX Patterns
- Microsoft Learn - Power BI
- DAX.guide - Function reference

### Power BI Best Practices
- Keep DAX measures in a separate "Measures" table
- Use variables for complex calculations
- Document measures with descriptions
- Test performance with large datasets
- Use calculation groups for time intelligence

### Data Refresh Strategy
- **DirectQuery**: Real-time but slower
- **Import Mode**: Fast but needs refresh
- **Hybrid**: Important mode with aggregations

---

## ✅ Success Metrics

Your Power BI dashboards are successful if you can answer:

### Business Questions
1. ✅ Which counties are experiencing the fastest rent growth?
2. ✅ Is Dublin rent affordable relative to income?
3. ✅ Which property types have the highest velocity?
4. ✅ What's the YoY rent inflation by bedroom count?
5. ✅ Are we in a tenant-friendly or landlord-friendly market?

### Technical Competency
1. ✅ Can you explain the star schema design?
2. ✅ Can you walk through a complex DAX measure?
3. ✅ Can you discuss performance optimization techniques?
4. ✅ Can you demonstrate drill-through and filtering?
5. ✅ Can you explain the data refresh strategy?

---

**Remember:** Employers want to see **business impact**, not just technical skills. Frame every KPI in terms of decisions it enables! 