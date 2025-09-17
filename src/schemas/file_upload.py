"""
Pydantic schemas for file upload validation
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum

class FileCategory(str, Enum):
    """File category enumeration"""
    DEBT_DOCUMENT = "debt_document"
    ASSET_DOCUMENT = "asset_document"
    INCOME_DOCUMENT = "income_document"
    EXPENDITURE_DOCUMENT = "expenditure_document"
    OTHER = "other"

class DebtType(str, Enum):
    """Debt type enumeration"""
    CREDIT_CARD = "credit_card"
    LOAN = "loan"
    MORTGAGE = "mortgage"
    OVERDRAFT = "overdraft"
    UTILITY_BILL = "utility_bill"
    COUNCIL_TAX = "council_tax"
    RENT_ARREARS = "rent_arrears"
    OTHER = "other"

class AssetType(str, Enum):
    """Asset type enumeration"""
    PROPERTY = "property"
    VEHICLE = "vehicle"
    SAVINGS = "savings"
    CASH = "cash"
    OTHER_VALUABLE_ITEMS = "other_valuable_items"

class IncomeType(str, Enum):
    """Income type enumeration"""
    WAGES_FROM_WORK = "wages_from_work"
    SELF_EMPLOYMENT_EARNINGS = "self_employment_earnings"
    SICK_PAY_FROM_WORK = "sick_pay_from_work"
    MATERNITY_PAY_FROM_WORK = "maternity_pay_from_work"
    BENEFITS = "benefits"
    UNIVERSAL_CREDIT = "universal_credit"
    CHILD_BENEFIT = "child_benefit"
    HOUSING_BENEFIT = "housing_benefit"
    COUNCIL_TAX_SUPPORT = "council_tax_support"
    PERSONAL_INDEPENDENCE_PAYMENT = "personal_independence_payment"
    DISABILITY_LIVING_ALLOWANCE = "disability_living_allowance"
    ATTENDANCE_ALLOWANCE = "attendance_allowance"
    CARERS_ALLOWANCE = "carers_allowance"
    EMPLOYMENT_SUPPORT_ALLOWANCE = "employment_support_allowance"
    GUARDIANS_ALLOWANCE = "guardians_allowance"
    INDUSTRIAL_INJURIES_BENEFIT = "industrial_injuries_benefit"
    MATERNITY_ALLOWANCE = "maternity_allowance"
    PENSION_CREDIT = "pension_credit"
    OTHER_BENEFIT = "other_benefit"
    STATE_PENSION = "state_pension"
    PRIVATE_WORK_PENSION = "private_work_pension"
    CHILD_MAINTENANCE = "child_maintenance"
    LODGER_INCOME = "lodger_income"
    CONTRIBUTIONS_FROM_FAMILY_FRIENDS = "contributions_from_family_friends"
    STUDENT_LOANS_GRANTS = "student_loans_grants"
    OTHER_INCOME_NOT_LISTED = "other_income_not_listed"

class ExpenditureType(str, Enum):
    """Expenditure type enumeration"""
    # Home
    RENT = "rent"
    GROUND_RENT_SERVICE_CHARGES = "ground_rent_service_charges"
    MORTGAGE = "mortgage"
    SECURED_LOAN = "secured_loan"
    COUNCIL_TAX = "council_tax"
    APPLIANCE_FURNITURE_RENTAL = "appliance_furniture_rental"
    TV_LICENSE = "tv_license"
    OTHER_HOME_CONTENTS_COSTS = "other_home_contents_costs"
    
    # Utilities
    ELECTRICITY = "electricity"
    GAS = "gas"
    WATER_SUPPLY_WASTE = "water_supply_waste"
    OTHER_UTILITIES_COSTS = "other_utilities_costs"
    
    # Care + Health
    CHILDCARE = "childcare"
    ADULT_CARE = "adult_care"
    CHILD_MAINTENANCE = "child_maintenance"
    PRESCRIPTIONS_MEDICINES = "prescriptions_medicines"
    DENTISTRY = "dentistry"
    OPTICIANS = "opticians"
    OTHER_HEALTH_COSTS = "other_health_costs"
    
    # Transport / Travel
    PUBLIC_TRANSPORT = "public_transport"
    HP_CONDITIONAL_SALE_VEHICLE = "hp_conditional_sale_vehicle"
    CAR_INSURANCE = "car_insurance"
    ROAD_TAX = "road_tax"
    MOT_ONGOING_MAINTENANCE = "mot_ongoing_maintenance"
    BREAKDOWN_COVER = "breakdown_cover"
    FUEL_PARKING = "fuel_parking"
    OTHER_TRAVEL_COSTS = "other_travel_costs"
    
    # School
    SCHOOL_UNIFORM = "school_uniform"
    AFTER_SCHOOL_CLUBS_TRIPS = "after_school_clubs_trips"
    OTHER_SCHOOL_COSTS = "other_school_costs"
    
    # Pension / Insurance
    PAYMENTS_TO_PENSION = "payments_to_pension"
    LIFE_INSURANCE = "life_insurance"
    MORTGAGE_PAYMENT_PROTECTION = "mortgage_payment_protection"
    BUILDING_CONTENTS_INSURANCE = "building_contents_insurance"
    HEALTH_INSURANCE = "health_insurance"
    PET_INSURANCE = "pet_insurance"
    OTHER_ESSENTIAL_COSTS = "other_essential_costs"
    
    # Communications + Leisure
    PHONE_INTERNET = "phone_internet"
    TV_PACKAGE = "tv_package"
    STREAMING_SUBSCRIPTIONS = "streaming_subscriptions"
    MOBILE_PHONE = "mobile_phone"
    LEISURE_SOCIALISING = "leisure_socialising"
    GIFTS_BIRTHDAYS_CHRISTMAS = "gifts_birthdays_christmas"
    POCKET_MONEY = "pocket_money"
    NEWSPAPERS_MAGAZINES = "newspapers_magazines"
    OTHER_COMMUNICATION_LEISURE_COSTS = "other_communication_leisure_costs"
    
    # Food + Housekeeping
    GROCERIES = "groceries"
    NAPPIES_BABY_ITEMS = "nappies_baby_items"
    SCHOOL_MEALS = "school_meals"
    LAUNDRY_DRY_CLEANING = "laundry_dry_cleaning"
    SMOKING_VAPING = "smoking_vaping"
    VET_BILLS = "vet_bills"
    HOUSE_REPAIRS = "house_repairs"
    OTHER_FOOD_HOUSEKEEPING_COSTS = "other_food_housekeeping_costs"
    
    # Personal Costs
    CLOTHING_FOOTWEAR = "clothing_footwear"
    HAIRDRESSING = "hairdressing"
    BEAUTY_TREATMENTS = "beauty_treatments"
    TOILETRIES = "toiletries"
    OTHER_PERSONAL_COSTS = "other_personal_costs"
    
    # Savings
    MONTHLY_SAVING_AMOUNT = "monthly_saving_amount"

class FileUploadRequest(BaseModel):
    """Schema for file upload request validation"""
    case_id: Optional[str] = Field(None, description="Case ID for the file")
    debt_id: Optional[str] = Field(None, description="Debt ID if file is related to a specific debt")
    asset_id: Optional[str] = Field(None, description="Asset ID if file is related to a specific asset")
    income_id: Optional[str] = Field(None, description="Income ID if file is related to a specific income")
    expenditure_id: Optional[str] = Field(None, description="Expenditure ID if file is related to a specific expenditure")
    description: Optional[str] = Field(None, max_length=500, description="Description of the file")
    category: Optional[FileCategory] = Field(None, description="File category")
    debt_type: Optional[DebtType] = Field(None, description="Type of debt if applicable")
    asset_type: Optional[AssetType] = Field(None, description="Type of asset if applicable")
    income_type: Optional[IncomeType] = Field(None, description="Type of income if applicable")
    expenditure_type: Optional[ExpenditureType] = Field(None, description="Type of expenditure if applicable")

    @validator('case_id')
    def validate_case_id(cls, v):
        """Validate case ID format"""
        if v is not None and not v.strip():
            raise ValueError('Case ID cannot be empty')
        return v

    @validator('debt_id')
    def validate_debt_id(cls, v):
        """Validate debt ID format"""
        if v is not None and not v.strip():
            raise ValueError('Debt ID cannot be empty')
        return v

    @validator('asset_id')
    def validate_asset_id(cls, v):
        """Validate asset ID format"""
        if v is not None and not v.strip():
            raise ValueError('Asset ID cannot be empty')
        return v

    @validator('income_id')
    def validate_income_id(cls, v):
        """Validate income ID format"""
        if v is not None and not v.strip():
            raise ValueError('Income ID cannot be empty')
        return v

    @validator('expenditure_id')
    def validate_expenditure_id(cls, v):
        """Validate expenditure ID format"""
        if v is not None and not v.strip():
            raise ValueError('Expenditure ID cannot be empty')
        return v

    @validator('description')
    def validate_description(cls, v):
        """Validate description"""
        if v is not None and len(v.strip()) == 0:
            raise ValueError('Description cannot be empty')
        return v

    class Config:
        use_enum_values = True

class FileUploadResponse(BaseModel):
    """Schema for file upload response"""
    id: str = Field(..., description="File ID")
    original_filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    file_size_formatted: str = Field(..., description="Human-readable file size")
    category: str = Field(..., description="File category")
    description: Optional[str] = Field(None, description="File description")
    created_at: str = Field(..., description="Upload timestamp")
    status: str = Field(..., description="Upload status")
    was_converted: bool = Field(False, description="Whether the file was converted (e.g., HEIC to JPEG)")

class FileListResponse(BaseModel):
    """Schema for file list response"""
    files: List[FileUploadResponse] = Field(..., description="List of files")
    total_count: int = Field(..., description="Total number of files")
    total_size: int = Field(..., description="Total size of all files in bytes")
    total_size_formatted: str = Field(..., description="Human-readable total size")

class FileDeleteRequest(BaseModel):
    """Schema for file deletion request"""
    file_id: str = Field(..., description="File ID to delete")

class FileDownloadRequest(BaseModel):
    """Schema for file download request"""
    file_id: str = Field(..., description="File ID to download")

class FileMetadataResponse(BaseModel):
    """Schema for file metadata response"""
    id: str = Field(..., description="File ID")
    original_filename: str = Field(..., description="Original filename")
    stored_filename: str = Field(..., description="Stored filename")
    file_size: int = Field(..., description="File size in bytes")
    file_size_formatted: str = Field(..., description="Human-readable file size")
    mime_type: str = Field(..., description="MIME type")
    category: str = Field(..., description="File category")
    description: Optional[str] = Field(None, description="File description")
    created_at: str = Field(..., description="Upload timestamp")
    uploaded_by_id: str = Field(..., description="User ID who uploaded the file")
    was_converted: bool = Field(False, description="Whether the file was converted")
    is_encrypted: bool = Field(False, description="Whether the file is encrypted")




