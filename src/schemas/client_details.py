from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import date, datetime
from enum import Enum

class Title(str, Enum):
    MR = "Mr"
    MRS = "Mrs"
    MISS = "Miss"
    MS = "Ms"
    DR = "Dr"
    PROF = "Prof"
    OTHER = "Other"

class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"
    PREFER_NOT_TO_SAY = "Prefer not to say"

class Ethnicity(str, Enum):
    WHITE_BRITISH = "White British"
    WHITE_IRISH = "White Irish"
    WHITE_GYPSY_OR_IRISH_TRAVELLER = "White Gypsy or Irish Traveller"
    WHITE_OTHER = "White Other"
    MIXED_WHITE_AND_BLACK_CARIBBEAN = "Mixed White and Black Caribbean"
    MIXED_WHITE_AND_BLACK_AFRICAN = "Mixed White and Black African"
    MIXED_WHITE_AND_ASIAN = "Mixed White and Asian"
    MIXED_OTHER = "Mixed Other"
    ASIAN_BRITISH_INDIAN = "Asian British Indian"
    ASIAN_BRITISH_PAKISTANI = "Asian British Pakistani"
    ASIAN_BRITISH_BANGLADESHI = "Asian British Bangladeshi"
    ASIAN_BRITISH_CHINESE = "Asian British Chinese"
    ASIAN_OTHER = "Asian Other"
    BLACK_BRITISH_AFRICAN = "Black British African"
    BLACK_BRITISH_CARIBBEAN = "Black British Caribbean"
    BLACK_OTHER = "Black Other"
    ARAB = "Arab"
    OTHER = "Other"
    PREFER_NOT_TO_SAY = "Prefer not to say"

class DisabilityStatus(str, Enum):
    NOT_DISABLED = "Not Disabled"
    DISABLED = "Disabled"
    LONG_TERM_HEALTH_CONDITION = "Long-Term Health Condition(s)"
    PREFER_NOT_TO_SAY = "Prefer not to say"

class MaritalStatus(str, Enum):
    SINGLE = "Single"
    MARRIED = "Married"
    CIVIL_PARTNERSHIP = "Civil Partnership"
    COHABITING = "Cohabiting"
    DIVORCED = "Divorced"
    WIDOWED = "Widowed"
    OTHER = "Other"
    PREFER_NOT_TO_SAY = "Prefer not to say"

class HouseholdType(str, Enum):
    SINGLE_ADULT = "Single Adult"
    SINGLE_ADULT_WITH_CHILDREN = "Single Adult with Children"
    COUPLE = "Couple"
    COUPLE_WITH_CHILDREN = "Couple with Children"
    OTHER_ADULTS = "Other Adults"
    OTHER = "Other"
    PREFER_NOT_TO_SAY = "Prefer not to say"

class Occupation(str, Enum):
    EMPLOYED_FULL_TIME = "Employed (Full Time)"
    EMPLOYED_PART_TIME = "Employed (Part Time)"
    SELF_EMPLOYED = "Self Employed"
    UNEMPLOYED = "Unemployed"
    CARER = "Carer"
    PERMANENTLY_SICK_DISABLED = "Permanently Sick/Disabled"
    RETIRED = "Retired"
    STUDENT = "Student"
    TEMPORARILY_SICK = "Temporarily Sick"
    OTHER = "Other"
    PREFER_NOT_TO_SAY = "Prefer not to say"

class HousingTenure(str, Enum):
    OWNED_OUTRIGHT = "Owned Outright"
    MORTGAGED_PROPERTY = "Mortgaged Property"
    SHARED_OWNERSHIP = "Shared-Ownership"
    PRIVATELY_RENTING = "Privately Renting"
    SOCIALLY_RENTING = "Socially Renting (e.g. Housing Association)"
    HOMELESS = "Homeless"
    CARE_HOME = "Care Home"
    RENTING_FROM_FAMILY_FRIENDS = "Renting from Family/Friends"
    STAYING_WITH_FAMILY_FRIENDS = "Staying with Family/Friends"
    OTHER = "Other"
    PREFER_NOT_TO_SAY = "Prefer not to say"

class ClientDetailsCreate(BaseModel):
    # Personal Information (Mandatory)
    title: Optional[str] = None  # Changed from Title enum to str
    first_name: str
    surname: str
    
    # Contact Details (Mandatory)
    home_address: str
    postcode: str
    date_of_birth: str  # Changed from date to str to handle frontend input
    gender: Optional[str] = None  # Changed from Gender enum to str
    home_phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    email: Optional[EmailStr] = None
    
    # Communication Preferences (Mandatory)
    happy_voicemail: bool = False
    happy_text_messages: bool = False
    preferred_contact_email: bool = False
    preferred_contact_mobile: bool = False
    preferred_contact_home_phone: bool = False
    preferred_contact_address: bool = False
    do_not_contact_methods: Optional[List[str]] = None
    
    # Research & Feedback (Mandatory)
    agree_to_feedback: bool = False
    do_not_contact_feedback_methods: Optional[List[str]] = None
    
    # Optional Additional Demographic Information
    # Personal Background (Optional)
    ethnicity: Optional[str] = None  # Changed from Ethnicity enum to str
    ethnicity_other: Optional[str] = None
    nationality: Optional[str] = None
    nationality_other: Optional[str] = None
    preferred_language: Optional[str] = None
    preferred_language_other: Optional[str] = None
    religion: Optional[str] = None
    religion_other: Optional[str] = None
    gender_identity: Optional[str] = None
    gender_identity_other: Optional[str] = None
    sexual_orientation: Optional[str] = None
    sexual_orientation_other: Optional[str] = None
    
    # Health & Disability (Optional)
    disability_status: Optional[str] = None  # Changed from DisabilityStatus enum to str
    disability_details: Optional[str] = None
    
    # Personal Circumstances (Optional)
    marital_status: Optional[str] = None  # Changed from MaritalStatus enum to str
    marital_status_other: Optional[str] = None
    household_type: Optional[str] = None  # Changed from HouseholdType enum to str
    household_type_other: Optional[str] = None
    occupation: Optional[str] = None  # Changed from Occupation enum to str
    occupation_other: Optional[str] = None
    housing_tenure: Optional[str] = None  # Changed from HousingTenure enum to str
    housing_tenure_other: Optional[str] = None

    @validator('postcode')
    def validate_postcode(cls, v):
        if not v or len(v.strip()) < 3:  # Reduced minimum length
            raise ValueError('Postcode must be at least 3 characters')
        return v.upper().strip()
    
    @validator('date_of_birth')
    def validate_date_of_birth(cls, v):
        if v:
            try:
                # Try to parse the date string
                parsed_date = datetime.strptime(v, "%Y-%m-%d").date()
                if parsed_date > date.today():
                    raise ValueError('Date of birth cannot be in the future')
            except ValueError as e:
                if "cannot be in the future" in str(e):
                    raise e
                raise ValueError('Invalid date format. Please use YYYY-MM-DD')
        return v
    
    @validator('home_phone', 'mobile_phone')
    def validate_phone(cls, v):
        if v:
            # Remove all non-digit characters
            digits_only = ''.join(filter(str.isdigit, v))
            if len(digits_only) < 7:  # Further reduced minimum length for UK numbers
                raise ValueError('Phone number must be at least 7 digits')
        return v

class ClientDetailsResponse(BaseModel):
    id: str
    user_id: str
    
    # Personal Information
    title: Optional[str] = None  # Changed from Title enum to str
    first_name: str
    surname: str
    
    # Contact Details
    home_address: str
    postcode: str
    date_of_birth: str  # Changed from date to str
    gender: Optional[str] = None  # Changed from Gender enum to str
    home_phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    email: Optional[str] = None
    
    # Communication Preferences
    happy_voicemail: bool
    happy_text_messages: bool
    preferred_contact_email: bool
    preferred_contact_mobile: bool
    preferred_contact_home_phone: bool
    preferred_contact_address: bool
    do_not_contact_methods: Optional[List[str]] = None
    
    # Research & Feedback
    agree_to_feedback: bool
    do_not_contact_feedback_methods: Optional[List[str]] = None
    
    # Optional Additional Demographic Information
    # Personal Background
    ethnicity: Optional[str] = None  # Changed from Ethnicity enum to str
    ethnicity_other: Optional[str] = None
    nationality: Optional[str] = None
    nationality_other: Optional[str] = None
    preferred_language: Optional[str] = None
    preferred_language_other: Optional[str] = None
    religion: Optional[str] = None
    religion_other: Optional[str] = None
    gender_identity: Optional[str] = None
    gender_identity_other: Optional[str] = None
    sexual_orientation: Optional[str] = None
    sexual_orientation_other: Optional[str] = None
    
    # Health & Disability
    disability_status: Optional[str] = None  # Changed from DisabilityStatus enum to str
    disability_details: Optional[str] = None
    
    # Personal Circumstances
    marital_status: Optional[str] = None  # Changed from MaritalStatus enum to str
    marital_status_other: Optional[str] = None
    household_type: Optional[str] = None  # Changed from HouseholdType enum to str
    household_type_other: Optional[str] = None
    occupation: Optional[str] = None  # Changed from Occupation enum to str
    occupation_other: Optional[str] = None
    housing_tenure: Optional[str] = None  # Changed from HousingTenure enum to str
    housing_tenure_other: Optional[str] = None
    
    # Metadata
    created_at: str
    updated_at: str

    @validator('do_not_contact_methods', 'do_not_contact_feedback_methods', pre=True)
    def parse_json_lists(cls, v):
        """Convert JSON strings back to lists for response"""
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        return v or []

    @validator('created_at', 'updated_at', pre=True)
    def convert_datetime_to_string(cls, v):
        """Convert datetime objects to ISO format strings"""
        if hasattr(v, 'isoformat'):
            return v.isoformat()
        return str(v) if v else ""

    class Config:
        from_attributes = True
