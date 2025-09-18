from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer, ForeignKey, Enum, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from ..config.database import Base
import uuid

class Title(PyEnum):
    MR = "Mr"
    MRS = "Mrs"
    MISS = "Miss"
    MS = "Ms"
    DR = "Dr"
    PROF = "Prof"
    OTHER = "Other"

class Gender(PyEnum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"
    PREFER_NOT_TO_SAY = "Prefer not to say"

class Ethnicity(PyEnum):
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

class DisabilityStatus(PyEnum):
    NOT_DISABLED = "Not Disabled"
    DISABLED = "Disabled"
    LONG_TERM_HEALTH_CONDITION = "Long-Term Health Condition(s)"
    PREFER_NOT_TO_SAY = "Prefer not to say"

class MaritalStatus(PyEnum):
    SINGLE = "Single"
    MARRIED = "Married"
    CIVIL_PARTNERSHIP = "Civil Partnership"
    COHABITING = "Cohabiting"
    DIVORCED = "Divorced"
    WIDOWED = "Widowed"
    OTHER = "Other"
    PREFER_NOT_TO_SAY = "Prefer not to say"

class HouseholdType(PyEnum):
    SINGLE_ADULT = "Single Adult"
    SINGLE_ADULT_WITH_CHILDREN = "Single Adult with Children"
    COUPLE = "Couple"
    COUPLE_WITH_CHILDREN = "Couple with Children"
    OTHER_ADULTS = "Other Adults"
    OTHER = "Other"
    PREFER_NOT_TO_SAY = "Prefer not to say"

class Occupation(PyEnum):
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

class HousingTenure(PyEnum):
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

class ClientDetails(Base):
    __tablename__ = "client_details"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Personal Information
    title = Column(String(5), nullable=True)
    first_name = Column(String(100), nullable=False)
    surname = Column(String(100), nullable=False)
    
    # Contact Details
    home_address = Column(Text, nullable=False)
    postcode = Column(String(10), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(17), nullable=True)
    home_phone = Column(String(20), nullable=True)
    mobile_phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Communication Preferences
    happy_voicemail = Column(Boolean, default=False)
    happy_text_messages = Column(Boolean, default=False)
    preferred_contact_email = Column(Boolean, default=False)
    preferred_contact_mobile = Column(Boolean, default=False)
    preferred_contact_home_phone = Column(Boolean, default=False)
    preferred_contact_address = Column(Boolean, default=False)
    do_not_contact_methods = Column(Text, nullable=True)  # JSON array of methods to avoid
    
    # Research & Feedback
    agree_to_feedback = Column(Boolean, default=False)
    do_not_contact_feedback_methods = Column(Text, nullable=True)  # JSON array of methods to avoid
    
    # Optional Additional Demographic Information
    # Personal Background
    ethnicity = Column(String(31), nullable=True)
    ethnicity_other = Column(String(100), nullable=True)
    nationality = Column(String(100), nullable=True)
    nationality_other = Column(String(100), nullable=True)
    preferred_language = Column(String(100), nullable=True)
    preferred_language_other = Column(String(100), nullable=True)
    religion = Column(String(100), nullable=True)
    religion_other = Column(String(100), nullable=True)
    gender_identity = Column(String(100), nullable=True)
    gender_identity_other = Column(String(100), nullable=True)
    sexual_orientation = Column(String(100), nullable=True)
    sexual_orientation_other = Column(String(100), nullable=True)
    
    # Health & Disability
    disability_status = Column(String(26), nullable=True)
    disability_details = Column(Text, nullable=True)
    
    # Personal Circumstances
    marital_status = Column(String(17), nullable=True)
    marital_status_other = Column(String(100), nullable=True)
    household_type = Column(String(26), nullable=True)
    household_type_other = Column(String(100), nullable=True)
    occupation = Column(String(25), nullable=True)
    occupation_other = Column(String(100), nullable=True)
    housing_tenure = Column(String(27), nullable=True)
    housing_tenure_other = Column(String(100), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="client_details")
    
    def __repr__(self):
        return f"<ClientDetails {self.first_name} {self.surname} ({self.user_id})>"
