import os
import json
from enum import StrEnum
from typing import Literal, Union, List
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

# ==========================================
# 1. CATEGORICAL ENUMS (FULLY POPULATED)
# ==========================================

class Region(StrEnum):
    AR="ar"; AT="at"; AU="au"; BE="be"; BR="br"; CA="ca"; CH="ch"; CL="cl"
    CN="cn"; CO="co"; CZ="cz"; DE="de"; DK="dk"; EE="ee"; EG="eg"; ES="es"
    FI="fi"; FR="fr"; GB="gb"; GR="gr"; HK="hk"; HU="hu"; ID="id"; IE="ie"
    IL="il"; IN="in"; IS="is"; IT="it"; JP="jp"; KR="kr"; KW="kw"; LK="lk"
    LT="lt"; LV="lv"; MX="mx"; MY="my"; NL="nl"; NO="no"; NZ="nz"; PE="pe"
    PH="ph"; PK="pk"; PL="pl"; PT="pt"; QA="qa"; RO="ro"; RU="ru"; SA="sa"
    SE="se"; SG="sg"; SR="sr"; SW="sw"; TH="th"; TR="tr"; TW="tw"; US="us"
    VE="ve"; VN="vn"; ZA="za"

class Exchange(StrEnum):
    BUE="BUE"; VIE="VIE"; ASX="ASX"; BRU="BRU"; SAO="SAO"; CNQ="CNQ"; NEO="NEO"
    TOR="TOR"; VAN="VAN"; EBS="EBS"; SGO="SGO"; SHH="SHH"; SHZ="SHZ"; BVC="BVC"
    PRA="PRA"; BER="BER"; DUS="DUS"; FRA="FRA"; GER="GER"; HAM="HAM"; MUN="MUN"
    STU="STU"; CPH="CPH"; TAL="TAL"; CAI="CAI"; MCE="MCE"; HEL="HEL"; PAR="PAR"
    AQS="AQS"; IOB="IOB"; LSE="LSE"; ATH="ATH"; HKG="HKG"; BUD="BUD"; JKT="JKT"
    ISE="ISE"; TLV="TLV"; BSE="BSE"; NSI="NSI"; ICE="ICE"; MIL="MIL"; FKA="FKA"
    JPX="JPX"; SAP="SAP"; KOE="KOE"; KSC="KSC"; KUW="KUW"; LIT="LIT"; RIS="RIS"
    MEX="MEX"; KLS="KLS"; AMS="AMS"; OSL="OSL"; NZE="NZE"; PHP="PHP"; PHS="PHS"
    WSE="WSE"; LIS="LIS"; DOH="DOH"; BVB="BVB"; SAU="SAU"; STO="STO"; SES="SES"
    SET="SET"; IST="IST"; TAI="TAI"; TWO="TWO"; ASE="ASE"; BTS="BTS"; CXI="CXI"
    NCM="NCM"; NGM="NGM"; NMS="NMS"; NYQ="NYQ"; OEM="OEM"; OQB="OQB"; OQX="OQX"
    PCX="PCX"; PNK="PNK"; YHD="YHD"; CCS="CCS"; JNB="JNB"

class Sector(StrEnum):
    BASIC_MATERIALS = "Basic Materials"
    COMMUNICATION_SERVICES = "Communication Services"
    CONSUMER_CYCLICAL = "Consumer Cyclical"
    CONSUMER_DEFENSIVE = "Consumer Defensive"
    ENERGY = "Energy"
    FINANCIAL_SERVICES = "Financial Services"
    HEALTHCARE = "Healthcare"
    INDUSTRIALS = "Industrials"
    REAL_ESTATE = "Real Estate"
    TECHNOLOGY = "Technology"
    UTILITIES = "Utilities"

class Industry(StrEnum):
    # Basic Materials
    AGRICULTURAL_INPUTS = "Agricultural Inputs"
    ALUMINUM = "Aluminum"
    BUILDING_MATERIALS = "Building Materials"
    CHEMICALS = "Chemicals"
    COKING_COAL = "Coking Coal"
    COPPER = "Copper"
    GOLD = "Gold"
    LUMBER_WOOD_PRODUCTION = "Lumber & Wood Production"
    OTHER_INDUSTRIAL_METALS_MINING = "Other Industrial Metals & Mining"
    OTHER_PRECIOUS_METALS_MINING = "Other Precious Metals & Mining"
    PAPER_PAPER_PRODUCTS = "Paper & Paper Products"
    SILVER = "Silver"
    SPECIALTY_CHEMICALS = "Specialty Chemicals"
    STEEL = "Steel"
    # Communication Services
    ADVERTISING_AGENCIES = "Advertising Agencies"
    BROADCASTING = "Broadcasting"
    ELECTRONIC_GAMING_MULTIMEDIA = "Electronic Gaming & Multimedia"
    ENTERTAINMENT = "Entertainment"
    INTERNET_CONTENT_INFORMATION = "Internet Content & Information"
    PUBLISHING = "Publishing"
    TELECOM_SERVICES = "Telecom Services"
    # Consumer Cyclical
    APPAREL_MANUFACTURING = "Apparel Manufacturing"
    APPAREL_RETAIL = "Apparel Retail"
    AUTO_TRUCK_DEALERSHIPS = "Auto & Truck Dealerships"
    AUTO_MANUFACTURERS = "Auto Manufacturers"
    AUTO_PARTS = "Auto Parts"
    DEPARTMENT_STORES = "Department Stores"
    FOOTWEAR_ACCESSORIES = "Footwear & Accessories"
    FURNISHINGS_FIXTURES_APPLIANCES = "Furnishings, Fixtures & Appliances"
    GAMBLING = "Gambling"
    HOME_IMPROVEMENT_RETAIL = "Home Improvement Retail"
    INTERNET_RETAIL = "Internet Retail"
    LEISURE = "Leisure"
    LODGING = "Lodging"
    LUXURY_GOODS = "Luxury Goods"
    PACKAGING_CONTAINERS = "Packaging & Containers"
    PERSONAL_SERVICES = "Personal Services"
    RECREATIONAL_VEHICLES = "Recreational Vehicles"
    RESIDENTIAL_CONSTRUCTION = "Residential Construction"
    RESORTS_CASINOS = "Resorts & Casinos"
    RESTAURANTS = "Restaurants"
    SPECIALTY_RETAIL = "Specialty Retail"
    TEXTILE_MANUFACTURING = "Textile Manufacturing"
    TRAVEL_SERVICES = "Travel Services"
    # Consumer Defensive
    BEVERAGES_BREWERS = "Beverages - Brewers"
    BEVERAGES_NON_ALCOHOLIC = "Beverages - Non-Alcoholic"
    BEVERAGES_WINERIES_DISTILLERIES = "Beverages - Wineries & Distilleries"
    CONFECTIONERS = "Confectioners"
    DISCOUNT_STORES = "Discount Stores"
    EDUCATION_TRAINING_SERVICES = "Education & Training Services"
    FARM_PRODUCTS = "Farm Products"
    FOOD_DISTRIBUTION = "Food Distribution"
    GROCERY_STORES = "Grocery Stores"
    HOUSEHOLD_PERSONAL_PRODUCTS = "Household & Personal Products"
    PACKAGED_FOODS = "Packaged Foods"
    TOBACCO = "Tobacco"
    # Energy
    OIL_GAS_DRILLING = "Oil Gas Drilling"
    OIL_GAS_E_P = "Oil Gas E P"
    OIL_GAS_EQUIPMENT_SERVICES = "Oil Gas Equipment Services"
    OIL_GAS_INTEGRATED = "Oil Gas Integrated"
    OIL_GAS_MIDSTREAM = "Oil Gas Midstream"
    OIL_GAS_REFINING_MARKETING = "Oil Gas Refining Marketing"
    THERMAL_COAL = "Thermal Coal"
    URANIUM = "Uranium"
    # Financial Services
    ASSET_MANAGEMENT = "Asset Management"
    BANKS_DIVERSIFIED = "Banks Diversified"
    BANKS_REGIONAL = "Banks Regional"
    CAPITAL_MARKETS = "Capital Markets"
    CREDIT_SERVICES = "Credit Services"
    FINANCIAL_CONGLOMERATES = "Financial Conglomerates"
    FINANCIAL_DATA_STOCK_EXCHANGES = "Financial Data Stock Exchanges"
    INSURANCE_BROKERS = "Insurance Brokers"
    INSURANCE_DIVERSIFIED = "Insurance Diversified"
    INSURANCE_LIFE = "Insurance Life"
    INSURANCE_PROPERTY_CASUALTY = "Insurance Property Casualty"
    INSURANCE_REINSURANCE = "Insurance Reinsurance"
    INSURANCE_SPECIALTY = "Insurance Specialty"
    MORTGAGE_FINANCE = "Mortgage Finance"
    SHELL_COMPANIES = "Shell Companies"
    # Healthcare
    BIOTECHNOLOGY = "Biotechnology"
    DIAGNOSTICS_RESEARCH = "Diagnostics Research"
    DRUG_MANUFACTURERS_GENERAL = "Drug Manufacturers General"
    DRUG_MANUFACTURERS_SPECIALTY_GENERIC = "Drug Manufacturers Specialty Generic"
    HEALTH_INFORMATION_SERVICES = "Health Information Services"
    HEALTHCARE_PLANS = "Healthcare Plans"
    MEDICAL_CARE_FACILITIES = "Medical Care Facilities"
    MEDICAL_DEVICES = "Medical Devices"
    MEDICAL_DISTRIBUTION = "Medical Distribution"
    MEDICAL_INSTRUMENTS_SUPPLIES = "Medical Instruments Supplies"
    PHARMACEUTICAL_RETAILERS = "Pharmaceutical Retailers"
    # Industrials
    AEROSPACE_DEFENSE = "Aerospace Defense"
    AIRLINES = "Airlines"
    AIRPORTS_AIR_SERVICES = "Airports Air Services"
    BUILDING_PRODUCTS_EQUIPMENT = "Building Products Equipment"
    BUSINESS_EQUIPMENT_SUPPLIES = "Business Equipment Supplies"
    CONGLOMERATES = "Conglomerates"
    CONSULTING_SERVICES = "Consulting Services"
    ELECTRICAL_EQUIPMENT_PARTS = "Electrical Equipment Parts"
    ENGINEERING_CONSTRUCTION = "Engineering Construction"
    FARM_HEAVY_CONSTRUCTION_MACHINERY = "Farm Heavy Construction Machinery"
    INDUSTRIAL_DISTRIBUTION = "Industrial Distribution"
    INFRASTRUCTURE_OPERATIONS = "Infrastructure Operations"
    INTEGRATED_FREIGHT_LOGISTICS = "Integrated Freight Logistics"
    MARINE_SHIPPING = "Marine Shipping"
    METAL_FABRICATION = "Metal Fabrication"
    POLLUTION_TREATMENT_CONTROLS = "Pollution Treatment Controls"
    RAILROADS = "Railroads"
    RENTAL_LEASING_SERVICES = "Rental Leasing Services"
    SECURITY_PROTECTION_SERVICES = "Security Protection Services"
    SPECIALTY_BUSINESS_SERVICES = "Specialty Business Services"
    SPECIALTY_INDUSTRIAL_MACHINERY = "Specialty Industrial Machinery"
    STAFFING_EMPLOYMENT_SERVICES = "Staffing Employment Services"
    TOOLS_ACCESSORIES = "Tools Accessories"
    TRUCKING = "Trucking"
    WASTE_MANAGEMENT = "Waste Management"
    # Real Estate
    REAL_ESTATE_DEVELOPMENT = "Real Estate Development"
    REAL_ESTATE_DIVERSIFIED = "Real Estate Diversified"
    REAL_ESTATE_SERVICES = "Real Estate Services"
    REIT_DIVERSIFIED = "Reit Diversified"
    REIT_HEALTHCARE_FACILITIES = "Reit Healthcare Facilities"
    REIT_HOTEL_MOTEL = "Reit Hotel Motel"
    REIT_INDUSTRIAL = "Reit Industrial"
    REIT_MORTGAGE = "Reit Mortgage"
    REIT_OFFICE = "Reit Office"
    REIT_RESIDENTIAL = "Reit Residential"
    REIT_RETAIL = "Reit Retail"
    REIT_SPECIALTY = "Reit Specialty"
    # Technology
    COMMUNICATION_EQUIPMENT = "Communication Equipment"
    COMPUTER_HARDWARE = "Computer Hardware"
    CONSUMER_ELECTRONICS = "Consumer Electronics"
    ELECTRONIC_COMPONENTS = "Electronic Components"
    ELECTRONICS_COMPUTER_DISTRIBUTION = "Electronics Computer Distribution"
    INFORMATION_TECHNOLOGY_SERVICES = "Information Technology Services"
    SCIENTIFIC_TECHNICAL_INSTRUMENTS = "Scientific Technical Instruments"
    SEMICONDUCTOR_EQUIPMENT_MATERIALS = "Semiconductor Equipment Materials"
    SEMICONDUCTORS = "Semiconductors"
    SOFTWARE_APPLICATION = "Software Application"
    SOFTWARE_INFRASTRUCTURE = "Software Infrastructure"
    SOLAR = "Solar"
    # Utilities
    UTILITIES_DIVERSIFIED = "Utilities Diversified"
    UTILITIES_INDEPENDENT_POWER_PRODUCERS = "Utilities Independent Power Producers"
    UTILITIES_REGULATED_ELECTRIC = "Utilities Regulated Electric"
    UTILITIES_REGULATED_GAS = "Utilities Regulated Gas"
    UTILITIES_REGULATED_WATER = "Utilities Regulated Water"
    UTILITIES_RENEWABLE = "Utilities Renewable"

class PeerGroup(StrEnum):
    AEROSPACE_DEFENSE = "Aerospace & Defense"
    AUTO_COMPONENTS = "Auto Components"
    AUTOMOBILES = "Automobiles"
    BANKS = "Banks"
    BUILDING_PRODUCTS = "Building Products"
    CHEMICALS = "Chemicals"
    CHINA_FUND_AGGRESSIVE_ALLOCATION_FUND = "China Fund Aggressive Allocation Fund"
    CHINA_FUND_EQUITY_FUNDS = "China Fund Equity Funds"
    CHINA_FUND_QDII_GREATER_CHINA_EQUITY = "China Fund QDII Greater China Equity"
    CHINA_FUND_QDII_SECTOR_EQUITY = "China Fund QDII Sector Equity"
    CHINA_FUND_SECTOR_EQUITY_FINANCIAL_AND_REAL_ESTATE = "China Fund Sector Equity Financial and Real Estate"
    COMMERCIAL_SERVICES = "Commercial Services"
    CONSTRUCTION_ENGINEERING = "Construction & Engineering"
    CONSTRUCTION_MATERIALS = "Construction Materials"
    CONSUMER_DURABLES = "Consumer Durables"
    CONSUMER_SERVICES = "Consumer Services"
    CONTAINERS_PACKAGING = "Containers & Packaging"
    DIVERSIFIED_FINANCIALS = "Diversified Financials"
    DIVERSIFIED_METALS = "Diversified Metals"
    EAA_CE_GLOBAL_LARGE_CAP_BLEND_EQUITY = "EAA CE Global Large-Cap Blend Equity"
    EAA_CE_OTHER = "EAA CE Other"
    EAA_CE_SECTOR_EQUITY_BIOTECHNOLOGY = "EAA CE Sector Equity Biotechnology"
    EAA_CE_UK_LARGE_CAP_EQUITY = "EAA CE UK Large-Cap Equity"
    EAA_CE_UK_SMALL_CAP_EQUITY = "EAA CE UK Small-Cap Equity"
    EAA_FUND_ASIA_EX_JAPAN_EQUITY = "EAA Fund Asia ex-Japan Equity"
    EAA_FUND_CHINA_EQUITY = "EAA Fund China Equity"
    EAA_FUND_CHINA_EQUITY_A_SHARES = "EAA Fund China Equity - A Shares"
    EAA_FUND_DENMARK_EQUITY = "EAA Fund Denmark Equity"
    EAA_FUND_EUR_AGGRESSIVE_ALLOCATION_GLOBAL = "EAA Fund EUR Aggressive Allocation - Global"
    EAA_FUND_EUR_CORPORATE_BOND = "EAA Fund EUR Corporate Bond"
    EAA_FUND_EUR_MODERATE_ALLOCATION_GLOBAL = "EAA Fund EUR Moderate Allocation - Global"
    EAA_FUND_EMERGING_EUROPE_EX_RUSSIA_EQUITY = "EAA Fund Emerging Europe ex-Russia Equity"
    EAA_FUND_EUROPE_LARGE_CAP_BLEND_EQUITY = "EAA Fund Europe Large-Cap Blend Equity"
    EAA_FUND_EUROZONE_LARGE_CAP_EQUITY = "EAA Fund Eurozone Large-Cap Equity"
    EAA_FUND_GERMANY_EQUITY = "EAA Fund Germany Equity"
    EAA_FUND_GLOBAL_EMERGING_MARKETS_EQUITY = "EAA Fund Global Emerging Markets Equity"
    EAA_FUND_GLOBAL_EQUITY_INCOME = "EAA Fund Global Equity Income"
    EAA_FUND_GLOBAL_FLEX_CAP_EQUITY = "EAA Fund Global Flex-Cap Equity"
    EAA_FUND_GLOBAL_LARGE_CAP_BLEND_EQUITY = "EAA Fund Global Large-Cap Blend Equity"
    EAA_FUND_GLOBAL_LARGE_CAP_GROWTH_EQUITY = "EAA Fund Global Large-Cap Growth Equity"
    EAA_FUND_HONG_KONG_EQUITY = "EAA Fund Hong Kong Equity"
    EAA_FUND_JAPAN_LARGE_CAP_EQUITY = "EAA Fund Japan Large-Cap Equity"
    EAA_FUND_OTHER_BOND = "EAA Fund Other Bond"
    EAA_FUND_OTHER_EQUITY = "EAA Fund Other Equity"
    EAA_FUND_RMB_BOND_ONSHORE = "EAA Fund RMB Bond - Onshore"
    EAA_FUND_SECTOR_EQUITY_CONSUMER_GOODS_SERVICES = "EAA Fund Sector Equity Consumer Goods & Services"
    EAA_FUND_SECTOR_EQUITY_FINANCIAL_SERVICES = "EAA Fund Sector Equity Financial Services"
    EAA_FUND_SECTOR_EQUITY_INDUSTRIAL_MATERIALS = "EAA Fund Sector Equity Industrial Materials"
    EAA_FUND_SECTOR_EQUITY_TECHNOLOGY = "EAA Fund Sector Equity Technology"
    EAA_FUND_SOUTH_AFRICA_NAMIBIA_EQUITY = "EAA Fund South Africa & Namibia Equity"
    EAA_FUND_SWITZERLAND_EQUITY = "EAA Fund Switzerland Equity"
    EAA_FUND_US_LARGE_CAP_BLEND_EQUITY = "EAA Fund US Large-Cap Blend Equity"
    EAA_FUND_USD_CORPORATE_BOND = "EAA Fund USD Corporate Bond"
    ELECTRICAL_EQUIPMENT = "Electrical Equipment"
    ENERGY_SERVICES = "Energy Services"
    FOOD_PRODUCTS = "Food Products"
    FOOD_RETAILERS = "Food Retailers"
    HEALTHCARE = "Healthcare"
    HOMEBUILDERS = "Homebuilders"
    HOUSEHOLD_PRODUCTS = "Household Products"
    INDIA_CE_MULTI_CAP = "India CE Multi-Cap"
    INDIA_FUND_LARGE_CAP = "India Fund Large-Cap"
    INDIA_FUND_SECTOR_FINANCIAL_SERVICES = "India Fund Sector - Financial Services"
    INDUSTRIAL_CONGLOMERATES = "Industrial Conglomerates"
    INSURANCE = "Insurance"
    MACHINERY = "Machinery"
    MEDIA = "Media"
    MEXICO_FUND_MEXICO_EQUITY = "Mexico Fund Mexico Equity"
    OIL_GAS_PRODUCERS = "Oil & Gas Producers"
    PAPER_FORESTRY = "Paper & Forestry"
    PHARMACEUTICALS = "Pharmaceuticals"
    PRECIOUS_METALS = "Precious Metals"
    REAL_ESTATE = "Real Estate"
    REFINERS_PIPELINES = "Refiners & Pipelines"
    RETAILING = "Retailing"
    SEMICONDUCTORS = "Semiconductors"
    SOFTWARE_SERVICES = "Software & Services"
    STEEL = "Steel"
    TECHNOLOGY_HARDWARE = "Technology Hardware"
    TELECOMMUNICATION_SERVICES = "Telecommunication Services"
    TEXTILES_APPAREL = "Textiles & Apparel"
    TRADERS_DISTRIBUTORS = "Traders & Distributors"
    TRANSPORTATION = "Transportation"
    TRANSPORTATION_INFRASTRUCTURE = "Transportation Infrastructure"
    US_CE_CONVERTIBLES = "US CE Convertibles"
    US_CE_OPTIONS_BASED = "US CE Options-based"
    US_CE_PREFERRED_STOCK = "US CE Preferred Stock"
    US_FUND_CHINA_REGION = "US Fund China Region"
    US_FUND_CONSUMER_CYCLICAL = "US Fund Consumer Cyclical"
    US_FUND_DIVERSIFIED_EMERGING_MKTS = "US Fund Diversified Emerging Mkts"
    US_FUND_EQUITY_ENERGY = "US Fund Equity Energy"
    US_FUND_EQUITY_PRECIOUS_METALS = "US Fund Equity Precious Metals"
    US_FUND_FINANCIAL = "US Fund Financial"
    US_FUND_FOREIGN_LARGE_BLEND = "US Fund Foreign Large Blend"
    US_FUND_HEALTH = "US Fund Health"
    US_FUND_LARGE_BLEND = "US Fund Large Blend"
    US_FUND_LARGE_GROWTH = "US Fund Large Growth"
    US_FUND_LARGE_VALUE = "US Fund Large Value"
    US_FUND_MISCELLANEOUS_REGION = "US Fund Miscellaneous Region"
    US_FUND_NATURAL_RESOURCES = "US Fund Natural Resources"
    US_FUND_TECHNOLOGY = "US Fund Technology"
    US_FUND_TRADING_LEVERAGED_EQUITY = "US Fund Trading–Leveraged Equity"
    UTILITIES = "Utilities"

# ==========================================
# 2. NUMERIC KEY ENUM (FULLY POPULATED)
# ==========================================

class NumericField(StrEnum):
    # Price
    PRICE = "price"
    EODPRICE = "eodprice"
    FIFTYTWOWKPERCENTCHANGE = "fiftytwowkpercentchange"
    INTRADAYMARKETCAP = "intradaymarketcap"
    INTRADAYPRICE = "intradayprice"
    INTRADAYPRICECHANGE = "intradaypricechange"
    LASTCLOSE52WEEKHIGH_LTM = "lastclose52weekhigh.lasttwelvemonths"
    LASTCLOSE52WEEKLOW_LTM = "lastclose52weeklow.lasttwelvemonths"
    LASTCLOSEMARKETCAP_LTM = "lastclosemarketcap.lasttwelvemonths"
    PERCENTCHANGE = "percentchange"
    
    # Trading
    AVGDAILYVOL3M = "avgdailyvol3m"
    BETA = "beta"
    DAYVOLUME = "dayvolume"
    EODVOLUME = "eodvolume"
    PCTHELDINSIDER = "pctheldinsider"
    PCTHELDINST = "pctheldinst"
    SHORT_INTEREST = "short_interest"
    DAYS_TO_COVER_SHORT_VALUE = "days_to_cover_short.value"
    SHORT_INTEREST_VALUE = "short_interest.value"
    SHORT_INTEREST_PERCENTAGE_CHANGE_VALUE = "short_interest_percentage_change.value"
    SHORT_PERCENTAGE_OF_FLOAT_VALUE = "short_percentage_of_float.value"
    SHORT_PERCENTAGE_OF_SHARES_OUTSTANDING_VALUE = "short_percentage_of_shares_outstanding.value"
    
    # Valuation
    BOOKVALUESHARE_LTM = "bookvalueshare.lasttwelvemonths"
    LASTCLOSEMARKETCAPTOTALREVENUE_LTM = "lastclosemarketcaptotalrevenue.lasttwelvemonths"
    LASTCLOSEPRICEEARNINGS_LTM = "lastclosepriceearnings.lasttwelvemonths"
    LASTCLOSEPRICETANGIBLEBOOKVALUE_LTM = "lastclosepricetangiblebookvalue.lasttwelvemonths"
    LASTCLOSETEVTOTALREVENUE_LTM = "lastclosetevtotalrevenue.lasttwelvemonths"
    PEGRATIO_5Y = "pegratio_5y"
    PERATIO_LTM = "peratio.lasttwelvemonths"
    PRICEBOOKRATIO_Q = "pricebookratio.quarterly"
    
    # Profitability
    CONSECUTIVE_YEARS_OF_DIVIDEND_GROWTH_COUNT = "consecutive_years_of_dividend_growth_count"
    FORWARD_DIVIDEND_PER_SHARE = "forward_dividend_per_share"
    FORWARD_DIVIDEND_YIELD = "forward_dividend_yield"
    RETURNONASSETS_LTM = "returnonassets.lasttwelvemonths"
    RETURNONEQUITY_LTM = "returnonequity.lasttwelvemonths"
    RETURNONTOTALCAPITAL_LTM = "returnontotalcapital.lasttwelvemonths"
    
    # Leverage
    EBITDAINTERESTEXPENSE_LTM = "ebitdainterestexpense.lasttwelvemonths"
    EBITINTERESTEXPENSE_LTM = "ebitinterestexpense.lasttwelvemonths"
    LASTCLOSETEVEBIT_LTM = "lastclosetevebit.lasttwelvemonths"
    LASTCLOSETEVEBITDA_LTM = "lastclosetevebitda.lasttwelvemonths"
    LTDEBTEQUITY_LTM = "ltdebtequity.lasttwelvemonths"
    NETDEBTEBITDA_LTM = "netdebtebitda.lasttwelvemonths"
    TOTALDEBTEBITDA_LTM = "totaldebtebitda.lasttwelvemonths"
    TOTALDEBTEQUITY_LTM = "totaldebtequity.lasttwelvemonths"
    
    # Liquidity
    ALTMANZSCORE_LTM = "altmanzscoreusingtheaveragestockinformationforaperiod.lasttwelvemonths"
    CURRENTRATIO_LTM = "currentratio.lasttwelvemonths"
    OPERATINGCASHFLOWTOCURRENTLIABILITIES_LTM = "operatingcashflowtocurrentliabilities.lasttwelvemonths"
    QUICKRATIO_LTM = "quickratio.lasttwelvemonths"
    
    # Income Statement
    BASICEPSCONTINUINGOPERATIONS_LTM = "basicepscontinuingoperations.lasttwelvemonths"
    DILUTEDEPS1YRGROWTH_LTM = "dilutedeps1yrgrowth.lasttwelvemonths"
    DILUTEDEPSCONTINUINGOPERATIONS_LTM = "dilutedepscontinuingoperations.lasttwelvemonths"
    EBIT_LTM = "ebit.lasttwelvemonths"
    EBITDA_LTM = "ebitda.lasttwelvemonths"
    EBITDA1YRGROWTH_LTM = "ebitda1yrgrowth.lasttwelvemonths"
    EBITDAMARGIN_LTM = "ebitdamargin.lasttwelvemonths"
    EPSGROWTH_LTM = "epsgrowth.lasttwelvemonths"
    GROSSPROFIT_LTM = "grossprofit.lasttwelvemonths"
    GROSSPROFITMARGIN_LTM = "grossprofitmargin.lasttwelvemonths"
    NETEPSBASIC_LTM = "netepsbasic.lasttwelvemonths"
    NETEPSDILUTED_LTM = "netepsdiluted.lasttwelvemonths"
    NETINCOME1YRGROWTH_LTM = "netincome1yrgrowth.lasttwelvemonths"
    NETINCOMEIS_LTM = "netincomeis.lasttwelvemonths"
    NETINCOMEMARGIN_LTM = "netincomemargin.lasttwelvemonths"
    OPERATINGINCOME_LTM = "operatingincome.lasttwelvemonths"
    QUARTERLYREVENUEGROWTH_Q = "quarterlyrevenuegrowth.quarterly"
    TOTALREVENUES_LTM = "totalrevenues.lasttwelvemonths"
    TOTALREVENUES1YRGROWTH_LTM = "totalrevenues1yrgrowth.lasttwelvemonths"
    
    # Balance Sheet
    TOTALASSETS_LTM = "totalassets.lasttwelvemonths"
    TOTALCASHANDSHORTTERMINVESTMENTS_LTM = "totalcashandshortterminvestments.lasttwelvemonths"
    TOTALCOMMONEQUITY_LTM = "totalcommonequity.lasttwelvemonths"
    TOTALCOMMONSHARESOUTSTANDING_LTM = "totalcommonsharesoutstanding.lasttwelvemonths"
    TOTALCURRENTASSETS_LTM = "totalcurrentassets.lasttwelvemonths"
    TOTALCURRENTLIABILITIES_LTM = "totalcurrentliabilities.lasttwelvemonths"
    TOTALDEBT_LTM = "totaldebt.lasttwelvemonths"
    TOTALEQUITY_LTM = "totalequity.lasttwelvemonths"
    TOTALSHARESOUTSTANDING = "totalsharesoutstanding"
    
    # Cash Flow
    CAPITALEXPENDITURE_LTM = "capitalexpenditure.lasttwelvemonths"
    CASHFROMOPERATIONS_LTM = "cashfromoperations.lasttwelvemonths"
    CASHFROMOPERATIONS1YRGROWTH_LTM = "cashfromoperations1yrgrowth.lasttwelvemonths"
    LEVEREDFREECASHFLOW_LTM = "leveredfreecashflow.lasttwelvemonths"
    LEVEREDFREECASHFLOW1YRGROWTH_LTM = "leveredfreecashflow1yrgrowth.lasttwelvemonths"
    UNLEVEREDFREECASHFLOW_LTM = "unleveredfreecashflow.lasttwelvemonths"
    
    # ESG
    ENVIRONMENTAL_SCORE = "environmental_score"
    ESG_SCORE = "esg_score"
    GOVERNANCE_SCORE = "governance_score"
    HIGHEST_CONTROVERSY = "highest_controversy"
    SOCIAL_SCORE = "social_score"

# ==========================================
# 3. DISCRIMINATED MODELS
# ==========================================

class OperationEnum(StrEnum):
    EQUALS = "equals"
    GREATER_THAN = "greater  than"
    LESS_THAN = "less than"
    GREATER_THAN_OR_EQUAL_TO = "greater than or equal to"
    LESS_THAN_OR_EQUAL_TO = "less than or equal to"
    IS_IN_LIST  = "is-in"
    BETWEEN = "between two values"

class RegionFilter(BaseModel):
    filterName: Literal["region"]
    filterCategory: Literal["region"] = "region"
    filterValue: Region 
    operation: OperationEnum

class SectorFilter(BaseModel):
    filterName: Literal["sector"]
    filterCategory: Literal["sector"] = "sector"
    filterValue: Sector 
    operation: OperationEnum

class IndustryFilter(BaseModel):
    filterName: Literal["industry"]
    filterCategory: Literal["industry"] = "industry"
    filterValue: Industry 
    operation: OperationEnum

class PeerGroupFilter(BaseModel):
    filterName: Literal["peer_group"]
    filterCategory: Literal["peer_group"] = "peer_group"
    filterValue: PeerGroup
    operation: OperationEnum

class NumericFilter(BaseModel):
    filterName: NumericField
    filterCategory: str
    filterValue: str
    operation: OperationEnum

# Union to enforce schema choice
FilterObject = Union[
    RegionFilter, 
    SectorFilter, 
    IndustryFilter, 
    PeerGroupFilter, 
    NumericFilter
]

class AgentFilterResponse(BaseModel):
    filters: List[FilterObject]
    sqlQuery: str

class StockMarket(StrEnum):
    US = "US"
    SA = "SR"

# ==========================================
# 4. AGENT LOGIC
# ==========================================

class NLPToFilterAgent:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.prompt_path = os.environ.get("FILTER_AGENT_PROMPT_PATH")
        # Load JSON for context if needed, though types are now handled in code
        try:
            with open(os.environ.get("EXPECTED_FILTER_FIELDS_JSON"), "r") as f:
                self.json_entries = json.load(f)
        except:
             self.json_entries = {}
    
    def _build_prompt(self, nlp_input: str) -> str:
        try:
            with open(self.prompt_path, "r") as file:
                template = file.read()
        except FileNotFoundError:
             # Fallback if file missing for testing
             template = "Map this user query to filters: {nlp_input}. Use the valid fields provided: {fields}"
            
        return template.replace("{fields}", json.dumps(self.json_entries)).replace("{nlp_input}", nlp_input)

    def filter_stocks(self, nlp_input: str, market: StockMarket= StockMarket.US) -> dict:
        final_prompt = self._build_prompt(nlp_input)
        
        if market == StockMarket.SA:
            final_prompt += "\nNote: Focus on stocks listed in the Saudi Arabian market."
        elif market == StockMarket.US:
            final_prompt += "\nNote: Focus on stocks listed in the US market."

        response = self.client.beta.chat.completions.parse(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
            messages=[
                {"role": "system", "content": "You are an expert financial analyst. Convert the user's NLP query into strict database filters using the specific Enums provided in the schema."},
                {"role": "user", "content": final_prompt}
            ],
            response_format=AgentFilterResponse
        )
        
        return response.choices[0].message.parsed.model_dump(mode="json", exclude_none=True)

# ==========================================
# 5. EXECUTION
# ==========================================

if __name__ == "__main__":
    agent = NLPToFilterAgent()
    # Example Query
    nlp_input = "Find me Software Infrastructure companies with a PE ratio under 25 and high ebitda growth"
    
    try:
        result = agent.filter_stocks(nlp_input, StockMarket.US)
        print("--- Result ---")
        for f in result.get("filters"):
            print(f"Filter: {f.get("filterName")} | Value: {f.get("filterValue")} | Operation: {f.get("operation")}")
        
        print(f"SQL Query: {result.get("sqlQuery")}")
            
    except Exception as e:
        print(f"Error: {e}")