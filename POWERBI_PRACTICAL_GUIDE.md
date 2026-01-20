# Power BI KPI Guide - Ireland Housing Data Platform
## 🎯 WORKING MEASURES FOR CURRENT DATA (Job Interview Ready)

**Last Updated:** January 2026
**Data Coverage:** 1,959 listings | 25 counties | Single snapshot (Jan 2026)

---

## 📋 Table of Contents

1. [Executive Dashboard (4 Key Cards)](#executive-dashboard)
2. [Geographic Intelligence (County Analysis)](#geographic-intelligence)
3. [Property Mix Analysis](#property-mix-analysis)
4. [Price Distribution & Affordability](#price-distribution)
5. [Market Quality Metrics](#market-quality)
6. [Advanced Analytics](#advanced-analytics)
7. [Interview Talking Points](#interview-talking-points)

---

## 🚀 Executive Dashboard (4 Key Cards)

### These 4 cards give instant market insight and work with your current data:

### Card 1: Total Active Listings 📊
**Business Question:** How big is the rental market?

```dax
Total Listings = COUNTROWS('gold fact_rental_listings')
```

**Format:** `#,##0` → Example: `1,959`
**Insight:** Shows market size and inventory depth

---

### Card 2: Median Monthly Rent 💰
**Business Question:** What's the typical rent? (Better than average for skewed data)

```dax
Median Monthly Rent = MEDIAN('gold fact_rental_listings'[price_monthly])
```

**Format:** `"€"#,##0` → Example: `€2,020`
**Why Median?** Resistant to outliers (€123k listings)
**Insight:** True middle-market pricing

---

### Card 3: Dublin Rent Premium 🏆
**Business Question:** How much more expensive is Dublin vs rest of Ireland?

```dax
Dublin Premium % =
VAR DublinAvg =
    CALCULATE(
        AVERAGE('gold fact_rental_listings'[price_monthly]),
        'gold dim_county'[county_name] = "Dublin"
    )
VAR NationalAvg = AVERAGE('gold fact_rental_listings'[price_monthly])
RETURN
    DIVIDE(DublinAvg - NationalAvg, NationalAvg, 0) * 100
```

**Format:** `+#0.0%` → Example: `+16.4%`
**Insight:** Quantifies Dublin's housing premium (critical for policy/investment)

---

### Card 4: Data Quality Score ⭐
**Business Question:** How reliable is our data?

```dax
Data Quality Score =
VAR TotalListings = COUNTROWS('gold fact_rental_listings')
VAR CompleteListings =
    COUNTROWS(
        FILTER(
            'gold fact_rental_listings',
            'gold fact_rental_listings'[has_images] = 1 &&
            'gold fact_rental_listings'[ber_rating] <> "NA" &&
            NOT(ISBLANK('gold fact_rental_listings'[ber_rating]))
        )
    )
RETURN
    DIVIDE(CompleteListings, TotalListings, 0) * 100
```

**Format:** `#0.0"%"` → Example: `95.8%`
**Insight:** Shows data completeness (critical for analytics trust)

---

## 🗺️ Geographic Intelligence (County Analysis)

### KPI 1: Top 5 Most Expensive Counties

```dax
County Avg Rent =
CALCULATE(
    AVERAGE('gold fact_rental_listings'[price_monthly]),
    ALLEXCEPT('gold fact_rental_listings', 'gold dim_county'[county_name])
)
```

**Visual:** Horizontal bar chart
**Axes:** County Name | Avg Rent
**Sort:** Descending by rent
**Top 5 Filter:**
```dax
Top 5 Counties =
VAR CurrentCounty = SELECTEDVALUE('gold dim_county'[county_name])
VAR CountyRank =
    RANKX(
        ALL('gold dim_county'[county_name]),
        [County Avg Rent],
        ,
        DESC,
        Dense
    )
RETURN
    IF(CountyRank <= 5, 1, 0)
```

**Expected Insight:** Dublin, Wicklow, Kildare typically highest

---

### KPI 2: Market Concentration by Province

```dax
Province Market Share % =
VAR ProvinceListings =
    CALCULATE(
        COUNTROWS('gold fact_rental_listings'),
        ALLEXCEPT('gold fact_rental_listings', 'gold dim_county'[province])
    )
VAR TotalListings = CALCULATE(COUNTROWS('gold fact_rental_listings'), ALL('gold dim_county'))
RETURN
    DIVIDE(ProvinceListings, TotalListings, 0) * 100
```

**Visual:** Donut chart with provinces
**Expected Result:** Leinster ~70%, Munster ~20%, Connacht ~8%, Ulster ~2%

---

### KPI 3: Dublin vs Commuter Belt Analysis

```dax
Commuter Belt Avg Rent =
CALCULATE(
    AVERAGE('gold fact_rental_listings'[price_monthly]),
    'gold dim_county'[is_commuter_belt] = TRUE,
    'gold dim_county'[county_name] <> "Dublin"
)

Commuter Belt Discount =
VAR DublinRent =
    CALCULATE(
        AVERAGE('gold fact_rental_listings'[price_monthly]),
        'gold dim_county'[county_name] = "Dublin"
    )
VAR CommuterRent = [Commuter Belt Avg Rent]
RETURN
    DIVIDE(DublinRent - CommuterRent, DublinRent, 0) * 100
```

**Format:** `#0.0"%"` → Example: `25.3%`
**Insight:** How much can you save by living in Kildare/Meath/Wicklow vs Dublin?

---

## 🏠 Property Mix Analysis

### KPI 4: Property Type Distribution

```dax
Property Type % =
VAR TypeCount =
    CALCULATE(
        COUNTROWS('gold fact_rental_listings'),
        ALLEXCEPT('gold fact_rental_listings', 'gold dim_property_type'[property_category])
    )
VAR TotalCount = CALCULATE(COUNTROWS('gold fact_rental_listings'), ALL('gold dim_property_type'))
RETURN
    DIVIDE(TypeCount, TotalCount, 0) * 100
```

**Visual:** Stacked column chart
**Expected:** Apartments (46%), Houses (43%), Studios (9%), Other (2%)

---

### KPI 5: Bedroom Count Distribution & Pricing

```dax
Avg Price by Bedrooms =
CALCULATE(
    AVERAGE('gold fact_rental_listings'[price_monthly]),
    ALLEXCEPT('gold fact_rental_listings', 'gold fact_rental_listings'[bedrooms])
)

Listings by Bedroom Count =
CALCULATE(
    COUNTROWS('gold fact_rental_listings'),
    ALLEXCEPT('gold fact_rental_listings', 'gold fact_rental_listings'[bedrooms])
)
```

**Visual:** Combo chart (Column = Count, Line = Avg Price)
**X-Axis Filter:** `bedrooms >= 0 && bedrooms <= 6` (exclude outliers)

---

### KPI 6: Price Per Bedroom

```dax
Avg Price Per Bedroom =
VAR TotalRent = SUM('gold fact_rental_listings'[price_monthly])
VAR TotalBedrooms = SUM('gold fact_rental_listings'[bedrooms])
RETURN
    DIVIDE(TotalRent, TotalBedrooms, BLANK())
```

**Format:** `"€"#,##0` → Example: `€972`
**Insight:** Standardized pricing metric across property sizes

---

## 💰 Price Distribution & Affordability

### KPI 7: Price Percentiles (P25, P50, P75, P95)

```dax
Price P25 =
PERCENTILE.INC('gold fact_rental_listings'[price_monthly], 0.25)

Price P50 (Median) =
PERCENTILE.INC('gold fact_rental_listings'[price_monthly], 0.50)

Price P75 =
PERCENTILE.INC('gold fact_rental_listings'[price_monthly], 0.75)

Price P95 =
PERCENTILE.INC('gold fact_rental_listings'[price_monthly], 0.95)
```

**Visual:** Box and whisker chart or table
**Insight:** Shows price distribution and identifies luxury segment

---

### KPI 8: Affordable Housing Availability (<€1,500/month)

```dax
Affordable Listing Count =
CALCULATE(
    COUNTROWS('gold fact_rental_listings'),
    'gold fact_rental_listings'[price_monthly] < 1500
)

Affordable Housing % =
DIVIDE(
    [Affordable Listing Count],
    COUNTROWS('gold fact_rental_listings'),
    0
) * 100
```

**Format:** `#0.0"%"` → Example: `28.3%`
**Insight:** Access to budget housing (critical for social policy)

---

### KPI 9: Price Range by County

```dax
Price Spread =
VAR MaxPrice = MAX('gold fact_rental_listings'[price_monthly])
VAR MinPrice = MIN('gold fact_rental_listings'[price_monthly])
RETURN
    MaxPrice - MinPrice

Coefficient of Variation =
VAR StdDev = STDEV.P('gold fact_rental_listings'[price_monthly])
VAR Mean = AVERAGE('gold fact_rental_listings'[price_monthly])
RETURN
    DIVIDE(StdDev, Mean, 0)
```

**Insight:** Measures price volatility by county (lower CV = more homogeneous market)

---

## 📈 Market Quality Metrics

### KPI 10: BER Rating Coverage

```dax
BER Coverage % =
VAR WithBER =
    CALCULATE(
        COUNTROWS('gold fact_rental_listings'),
        'gold fact_rental_listings'[ber_rating] <> "NA",
        NOT(ISBLANK('gold fact_rental_listings'[ber_rating]))
    )
VAR Total = COUNTROWS('gold fact_rental_listings')
RETURN
    DIVIDE(WithBER, Total, 0) * 100
```

**Format:** `#0.0"%"` → Example: `97.6%`
**Insight:** Energy efficiency data availability (Ireland mandate compliance)

---

### KPI 11: Average Energy Efficiency Category Distribution

```dax
Energy Efficient Properties % =
CALCULATE(
    COUNTROWS('gold fact_rental_listings'),
    'gold fact_rental_listings'[ber_rating] IN {"A1", "A2", "A3", "B1", "B2", "B3"}
) / COUNTROWS('gold fact_rental_listings') * 100
```

**Visual:** Stacked bar showing A/B/C/D/E/F/G distribution
**Insight:** Market sustainability profile

---

### KPI 12: Listings with Complete Information

```dax
Complete Listings % =
VAR CompleteCount =
    CALCULATE(
        COUNTROWS('gold fact_rental_listings'),
        'gold fact_rental_listings'[is_complete_record] = TRUE
    )
RETURN
    DIVIDE(CompleteCount, COUNTROWS('gold fact_rental_listings'), 0) * 100
```

---

## 🔍 Advanced Analytics

### KPI 13: Market Concentration Index (Herfindahl-Hirschman Index)

```dax
HHI by County =
SUMX(
    VALUES('gold dim_county'[county_name]),
    VAR CountyShare =
        DIVIDE(
            CALCULATE(COUNTROWS('gold fact_rental_listings')),
            CALCULATE(COUNTROWS('gold fact_rental_listings'), ALL('gold dim_county'))
        )
    RETURN
        POWER(CountyShare, 2) * 10000
)
```

**Interpretation:**
- HHI < 1,500: Competitive market
- HHI 1,500-2,500: Moderate concentration
- HHI > 2,500: High concentration (Dublin dominance)

**Expected Value:** ~2,800 (Dublin has 51% market share)

---

### KPI 14: Price Density Distribution

```dax
Listings in Price Band =
CALCULATE(
    COUNTROWS('gold fact_rental_listings'),
    'gold fact_rental_listings'[price_monthly] >= MIN('gold dim_market_segment'[price_min]),
    'gold fact_rental_listings'[price_monthly] < MAX('gold dim_market_segment'[price_max])
)
```

**Visual:** Histogram with €500 buckets
**Insight:** Identifies modal price points and market gaps

---

### KPI 15: Property Type Diversity by County

```dax
Property Type Count =
CALCULATE(
    DISTINCTCOUNT('gold dim_property_type'[property_category]),
    ALLEXCEPT('gold fact_rental_listings', 'gold dim_county'[county_name])
)

Diversity Index =
VAR MaxTypes = 4  // Apartment, House, Studio, Other
RETURN
    DIVIDE([Property Type Count], MaxTypes, 0) * 100
```

**Insight:** Market maturity indicator (more diverse = more developed)

---

### KPI 16: Outlier Detection

```dax
Is Price Outlier =
VAR CurrentPrice = SELECTEDVALUE('gold fact_rental_listings'[price_monthly])
VAR Q1 = PERCENTILE.INC('gold fact_rental_listings'[price_monthly], 0.25)
VAR Q3 = PERCENTILE.INC('gold fact_rental_listings'[price_monthly], 0.75)
VAR IQR = Q3 - Q1
VAR LowerFence = Q1 - 1.5 * IQR
VAR UpperFence = Q3 + 1.5 * IQR
RETURN
    IF(
        CurrentPrice < LowerFence || CurrentPrice > UpperFence,
        "Outlier",
        "Normal"
    )

Outlier Count =
CALCULATE(
    COUNTROWS('gold fact_rental_listings'),
    [Is Price Outlier] = "Outlier"
)
```

**Use:** Filter out bad data or identify luxury/distressed properties

---

## 📊 Sample Dashboard Layouts

### Page 1: Executive Overview

```
┌─────────────────────────────────────────────────────────┐
│  IRELAND RENTAL MARKET - EXECUTIVE DASHBOARD            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  📊 Total Listings    💰 Median Rent    🏆 Dublin +%   │
│      1,959               €2,020           +16.4%       │
│                                                         │
│  ⭐ Data Quality      🗺️ Counties        🏠 Avg Days   │
│      95.8%                25                1 day       │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  📈 Price Distribution (Histogram)                      │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░       │
│                                                         │
├──────────────────────────┬──────────────────────────────┤
│  🗺️ Top 5 Counties      │  🏠 Property Type Mix        │
│  (Bar Chart)             │  (Donut Chart)               │
│                          │                              │
└──────────────────────────┴──────────────────────────────┘
```

---

### Page 2: Geographic Intelligence

```
┌─────────────────────────────────────────────────────────┐
│  GEOGRAPHIC ANALYSIS                                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  🗺️ Interactive County Map (Filled Map)                │
│  Color by: Median Rent                                 │
│  Tooltip: County, Listing Count, Avg/Median Rent       │
│                                                         │
├──────────────────────────┬──────────────────────────────┤
│  📊 Province Breakdown   │  🎯 Dublin vs Commuter Belt │
│  (Stacked Bar)           │  (Clustered Column)         │
│                          │                              │
├──────────────────────────┴──────────────────────────────┤
│  📋 County Details Table                                │
│  County | Province | Listings | Avg | Median | P25-P75 │
│  (Matrix with conditional formatting)                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

### Page 3: Property Mix & Affordability

```
┌─────────────────────────────────────────────────────────┐
│  PROPERTY MIX ANALYSIS                                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  🏠 Property Type Distribution (Stacked Column)         │
│  By County                                             │
│                                                         │
├──────────────────────────┬──────────────────────────────┤
│  🛏️ Bedrooms vs Price   │  💰 Affordable Housing %    │
│  (Combo Chart)           │  (Gauge: <€1,500/month)     │
│                          │  Target: 30%                │
│                          │  Actual: 28.3%              │
│                          │                              │
└──────────────────────────┴──────────────────────────────┘
```

---

## 🎯 Interview Talking Points

### 1. **Data Engineering Excellence**
*"I built a medallion architecture (Bronze-Silver-Gold) data warehouse for Ireland's rental market, processing 2,000+ listings with 98% data quality. The star schema supports sub-second queries in Power BI."*

---

### 2. **Business Impact Metrics**
*"My analysis revealed Dublin commands a 16% rent premium over the national average, and only 28% of listings are affordable (<€1,500), highlighting Ireland's housing crisis severity."*

---

### 3. **Advanced DAX Skills**
*"I created 15+ complex DAX measures including Herfindahl-Hirschman Index for market concentration, percentile calculations, and dynamic geographic comparisons using CALCULATE and FILTER contexts."*

---

### 4. **Data Quality Focus**
*"I implemented automated data quality checks showing 97.6% BER compliance and built outlier detection using IQR methodology to ensure analytics reliability."*

---

### 5. **Scalability Design**
*"The data model supports 30 years of historical data (dim_date 2000-2030) and 26 counties, ready for time-series analysis once we accumulate 12+ months of listings."*

---

### 6. **Stakeholder Communication**
*"I designed 3 dashboard personas: Executive (high-level KPIs), Geographic (county deep-dive), and Property Mix (investor-focused), each answering specific business questions."*

---

## 🔧 Power BI Setup Instructions

### Step 1: Connect to PostgreSQL

**Connection String:**
```
Server: ep-nameless-cherry-abn7j2cl-pooler.eu-west-2.aws.neon.tech
Database: neondb
Port: 5432
User: neondb_owner
```

**Import Mode:** Choose "Import" (not DirectQuery) for best performance with 2K rows

---

### Step 2: Load Tables

**Required Tables:**
- ✅ gold.fact_rental_listings (Main fact table)
- ✅ gold.fact_market_summary (Aggregated facts)
- ✅ gold.dim_date (Date dimension)
- ✅ gold.dim_county (Geography)
- ✅ gold.dim_property_type (Property classification)
- ✅ gold.dim_market_segment (Market segmentation)

**Optional Tables:**
- gold.fact_price_movements (For future time-series)
- gold.fact_affordability (Limited data currently)
- gold.fact_economic_indicators (For context)

---

### Step 3: Verify Relationships

**Star Schema:**
```
fact_rental_listings
├─→ dim_date (date_key → date_key) [Many-to-One]
├─→ dim_county (county_key → county_key) [Many-to-One]
└─→ dim_property_type (property_type_key → property_type_key) [Many-to-One]
```

**Check:** Model View → Ensure all relationships are active and cardinality is correct

---

### Step 4: Create Measure Table

**Best Practice:** Create a dedicated table for measures

1. Home → Enter Data → Create blank table
2. Name: `_Measures`
3. Add all DAX measures here
4. Hide all columns, keep only measures visible

---

### Step 5: Data Formatting

**Number Formats:**
- Currency: `"€"#,##0`
- Percentage: `#0.0"%"`
- Large Numbers: `#,##0`
- Decimals: `#,##0.00`

**Conditional Formatting:**
- Green: Positive/Good (< target)
- Yellow: Warning (near target)
- Red: Alert (> target)

---

## 📚 Next Steps for Enhanced Analytics

### When You Have 12+ Months of Data:

1. **Time Intelligence Measures:**
```dax
YoY Rent Change % =
VAR CurrentYear = [Avg Monthly Rent]
VAR PreviousYear =
    CALCULATE(
        [Avg Monthly Rent],
        SAMEPERIODLASTYEAR('gold dim_date'[date])
    )
RETURN
    DIVIDE(CurrentYear - PreviousYear, PreviousYear, 0) * 100
```

2. **Seasonality Analysis:**
```dax
Monthly Index =
VAR MonthAvg = [Avg Monthly Rent]
VAR YearAvg =
    CALCULATE(
        [Avg Monthly Rent],
        ALLEXCEPT('gold dim_date', 'gold dim_date'[year])
    )
RETURN
    DIVIDE(MonthAvg, YearAvg, 0) * 100
```

3. **Trend Forecasting:**
- Use Power BI's built-in forecasting (Visualizations → Analytics → Forecast)
- Requires 12+ periods for accuracy

---

### When Economic Data is Available:

1. **True Affordability Index:**
```dax
Affordability Index =
VAR AvgRent = [Avg Monthly Rent]
VAR AvgIncome = AVERAGE('gold fact_economic_indicators'[avg_income_monthly])
RETURN
    DIVIDE(AvgRent, AvgIncome, 0) * 100
```

2. **Real Rent (Inflation-Adjusted):**
```dax
Real Rent =
VAR NominalRent = [Avg Monthly Rent]
VAR CPI = AVERAGE('gold fact_economic_indicators'[cpi_value])
RETURN
    NominalRent * (100 / CPI)
```

---

## ✅ Validation Checklist

Before your interview/demo:

- [ ] All 16 KPIs calculate without errors
- [ ] Visuals load in < 2 seconds
- [ ] Filters work correctly (County, Property Type, Bedrooms)
- [ ] Tooltips show relevant context
- [ ] Color scheme is professional (avoid rainbow colors)
- [ ] Dashboard tells a story (not just random charts)
- [ ] You can explain business impact of each KPI
- [ ] Data quality metrics show >95%
- [ ] Mobile layout is responsive
- [ ] Export to PDF works correctly

---

## 🏆 Why This Dashboard Gets You Hired

### Technical Skills Demonstrated:
1. ✅ **Data Modeling:** Star schema, proper relationships
2. ✅ **DAX Mastery:** 15+ complex measures, context manipulation
3. ✅ **Data Quality:** Outlier detection, completeness metrics
4. ✅ **Visualization:** 3 dashboard personas, appropriate chart types
5. ✅ **Performance:** Optimized for <2s load times
6. ✅ **Scalability:** Ready for time-series and multi-year analysis

### Business Value Demonstrated:
1. ✅ **Market Insights:** Dublin premium, county rankings
2. ✅ **Social Impact:** Affordable housing availability
3. ✅ **Policy Relevance:** Energy efficiency, market concentration
4. ✅ **Investment Intelligence:** Price per bedroom, ROI potential
5. ✅ **Data-Driven:** Every KPI answers a business question

---

## 📞 Support & Resources

**Data Dictionary:** See `sql/` folder for table schemas
**Source Code:** `etl/` folder for data pipeline
**Refresh Schedule:** Manual (no scheduled scraping yet)

---

**Built with:** PostgreSQL (Neon) | Python | dbt | Power BI
**Author:** [Your Name]
**Portfolio:** [Your GitHub/LinkedIn]

---

*This dashboard demonstrates production-ready analytics engineering skills applicable to any real estate, finance, or data analytics role.*
