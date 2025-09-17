from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from ..config.database import Base
import uuid

class ExpenditureType(PyEnum):
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

class PaymentFrequency(PyEnum):
    WEEKLY = "weekly"
    FORTNIGHTLY = "fortnightly"
    FOUR_WEEKLY = "four_weekly"
    MONTHLY = "monthly"
    ANNUALLY = "annually"
    ONE_OFF = "one_off"

class Expenditure(Base):
    __tablename__ = "expenditures"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    
    # Expenditure details
    expenditure_type = Column(Enum(ExpenditureType), nullable=False)
    amount = Column(String, nullable=True)  # Store as string to avoid float precision
    frequency = Column(Enum(PaymentFrequency), nullable=True)
    
    # Provider/source information
    provider_name = Column(String(255), nullable=True)  # Who do you pay? (landlord, supplier, etc.)
    
    # Additional information
    additional_info = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    case = relationship("Case", back_populates="expenditures")
    files = relationship("FileUpload", back_populates="expenditure", cascade="all, delete-orphan")
    
    @property
    def expenditure_type_display(self):
        """Get human-readable expenditure type name"""
        display_names = {
            # Home
            ExpenditureType.RENT: "Rent",
            ExpenditureType.GROUND_RENT_SERVICE_CHARGES: "Ground Rent / Service Charges",
            ExpenditureType.MORTGAGE: "Mortgage(s)",
            ExpenditureType.SECURED_LOAN: "Secured Loan(s)",
            ExpenditureType.COUNCIL_TAX: "Council Tax",
            ExpenditureType.APPLIANCE_FURNITURE_RENTAL: "Appliance or Furniture Rental",
            ExpenditureType.TV_LICENSE: "TV License",
            ExpenditureType.OTHER_HOME_CONTENTS_COSTS: "Other Home or Contents Costs",
            
            # Utilities
            ExpenditureType.ELECTRICITY: "Electricity",
            ExpenditureType.GAS: "Gas",
            ExpenditureType.WATER_SUPPLY_WASTE: "Water Supply + Waste",
            ExpenditureType.OTHER_UTILITIES_COSTS: "Other Utilities Costs (i.e. Oil, Gas)",
            
            # Care + Health
            ExpenditureType.CHILDCARE: "Childcare",
            ExpenditureType.ADULT_CARE: "Adult Care",
            ExpenditureType.CHILD_MAINTENANCE: "Child Maintenance",
            ExpenditureType.PRESCRIPTIONS_MEDICINES: "Prescriptions / Medicines",
            ExpenditureType.DENTISTRY: "Dentistry",
            ExpenditureType.OPTICIANS: "Opticians",
            ExpenditureType.OTHER_HEALTH_COSTS: "Other Health Costs",
            
            # Transport / Travel
            ExpenditureType.PUBLIC_TRANSPORT: "Public Transport",
            ExpenditureType.HP_CONDITIONAL_SALE_VEHICLE: "Hire Purchase / Conditional Sale of a Vehicle",
            ExpenditureType.CAR_INSURANCE: "Car Insurance",
            ExpenditureType.ROAD_TAX: "Road Tax",
            ExpenditureType.MOT_ONGOING_MAINTENANCE: "MOT and Ongoing Maintenance",
            ExpenditureType.BREAKDOWN_COVER: "Breakdown Cover",
            ExpenditureType.FUEL_PARKING: "Fuel / Parking",
            ExpenditureType.OTHER_TRAVEL_COSTS: "Other Travel Costs",
            
            # School
            ExpenditureType.SCHOOL_UNIFORM: "School Uniform",
            ExpenditureType.AFTER_SCHOOL_CLUBS_TRIPS: "After School Clubs / School Trips",
            ExpenditureType.OTHER_SCHOOL_COSTS: "Other School Costs",
            
            # Pension / Insurance
            ExpenditureType.PAYMENTS_TO_PENSION: "Payments to a Pension",
            ExpenditureType.LIFE_INSURANCE: "Life Insurance",
            ExpenditureType.MORTGAGE_PAYMENT_PROTECTION: "Mortgage Payments Protection Insurance",
            ExpenditureType.BUILDING_CONTENTS_INSURANCE: "Building / Contents Insurance",
            ExpenditureType.HEALTH_INSURANCE: "Health Insurance",
            ExpenditureType.PET_INSURANCE: "Pet Insurance",
            ExpenditureType.OTHER_ESSENTIAL_COSTS: "Other Essential Costs",
            
            # Communications + Leisure
            ExpenditureType.PHONE_INTERNET: "Phone / Internet",
            ExpenditureType.TV_PACKAGE: "TV Package",
            ExpenditureType.STREAMING_SUBSCRIPTIONS: "Streaming Subscriptions",
            ExpenditureType.MOBILE_PHONE: "Mobile Phone",
            ExpenditureType.LEISURE_SOCIALISING: "Leisure / Socialising",
            ExpenditureType.GIFTS_BIRTHDAYS_CHRISTMAS: "Gifts (Birthdays, Christmas)",
            ExpenditureType.POCKET_MONEY: "Pocket Money",
            ExpenditureType.NEWSPAPERS_MAGAZINES: "Newspapers / Magazines",
            ExpenditureType.OTHER_COMMUNICATION_LEISURE_COSTS: "Other Costs",
            
            # Food + Housekeeping
            ExpenditureType.GROCERIES: "Groceries",
            ExpenditureType.NAPPIES_BABY_ITEMS: "Nappies / Baby Items",
            ExpenditureType.SCHOOL_MEALS: "School Meals",
            ExpenditureType.LAUNDRY_DRY_CLEANING: "Laundry / Dry Cleaning",
            ExpenditureType.SMOKING_VAPING: "Smoking / Vaping",
            ExpenditureType.VET_BILLS: "Vet Bills",
            ExpenditureType.HOUSE_REPAIRS: "House Repairs",
            ExpenditureType.OTHER_FOOD_HOUSEKEEPING_COSTS: "Other Costs",
            
            # Personal Costs
            ExpenditureType.CLOTHING_FOOTWEAR: "Clothing + Footwear",
            ExpenditureType.HAIRDRESSING: "Hairdressing",
            ExpenditureType.BEAUTY_TREATMENTS: "Beauty Treatments",
            ExpenditureType.TOILETRIES: "Toiletries",
            ExpenditureType.OTHER_PERSONAL_COSTS: "Other Costs",
            
            # Savings
            ExpenditureType.MONTHLY_SAVING_AMOUNT: "Monthly Saving Amount"
        }
        return display_names.get(self.expenditure_type, self.expenditure_type.value.replace('_', ' ').title())
    
    @property
    def frequency_display(self):
        """Get human-readable frequency"""
        if not self.frequency:
            return "Not specified"
        
        display_names = {
            PaymentFrequency.WEEKLY: "Weekly",
            PaymentFrequency.FORTNIGHTLY: "Fortnightly",
            PaymentFrequency.FOUR_WEEKLY: "Four Weekly", 
            PaymentFrequency.MONTHLY: "Monthly",
            PaymentFrequency.ANNUALLY: "Annually"
        }
        return display_names.get(self.frequency, self.frequency.value.replace('_', ' ').title())
    
    @property
    def category(self):
        """Get the category this expenditure belongs to"""
        home_types = [
            ExpenditureType.RENT, ExpenditureType.GROUND_RENT_SERVICE_CHARGES,
            ExpenditureType.MORTGAGE, ExpenditureType.SECURED_LOAN, ExpenditureType.COUNCIL_TAX,
            ExpenditureType.APPLIANCE_FURNITURE_RENTAL, ExpenditureType.TV_LICENSE,
            ExpenditureType.OTHER_HOME_CONTENTS_COSTS
        ]
        
        utilities_types = [
            ExpenditureType.ELECTRICITY, ExpenditureType.GAS,
            ExpenditureType.WATER_SUPPLY_WASTE, ExpenditureType.OTHER_UTILITIES_COSTS
        ]
        
        care_health_types = [
            ExpenditureType.CHILDCARE, ExpenditureType.ADULT_CARE, ExpenditureType.CHILD_MAINTENANCE,
            ExpenditureType.PRESCRIPTIONS_MEDICINES, ExpenditureType.DENTISTRY,
            ExpenditureType.OPTICIANS, ExpenditureType.OTHER_HEALTH_COSTS
        ]
        
        transport_types = [
            ExpenditureType.PUBLIC_TRANSPORT, ExpenditureType.HP_CONDITIONAL_SALE_VEHICLE,
            ExpenditureType.CAR_INSURANCE, ExpenditureType.ROAD_TAX,
            ExpenditureType.MOT_ONGOING_MAINTENANCE, ExpenditureType.BREAKDOWN_COVER,
            ExpenditureType.FUEL_PARKING, ExpenditureType.OTHER_TRAVEL_COSTS
        ]
        
        if self.expenditure_type in home_types:
            return "Home"
        elif self.expenditure_type in utilities_types:
            return "Utilities"
        elif self.expenditure_type in care_health_types:
            return "Care + Health"
        elif self.expenditure_type in transport_types:
            return "Transport / Travel"
        elif self.expenditure_type in [ExpenditureType.SCHOOL_UNIFORM, ExpenditureType.AFTER_SCHOOL_CLUBS_TRIPS, ExpenditureType.OTHER_SCHOOL_COSTS]:
            return "School"
        elif self.expenditure_type in [ExpenditureType.PAYMENTS_TO_PENSION, ExpenditureType.LIFE_INSURANCE, ExpenditureType.MORTGAGE_PAYMENT_PROTECTION, ExpenditureType.BUILDING_CONTENTS_INSURANCE, ExpenditureType.HEALTH_INSURANCE, ExpenditureType.PET_INSURANCE, ExpenditureType.OTHER_ESSENTIAL_COSTS]:
            return "Pension / Insurance"
        elif self.expenditure_type in [ExpenditureType.PHONE_INTERNET, ExpenditureType.TV_PACKAGE, ExpenditureType.STREAMING_SUBSCRIPTIONS, ExpenditureType.MOBILE_PHONE, ExpenditureType.LEISURE_SOCIALISING, ExpenditureType.GIFTS_BIRTHDAYS_CHRISTMAS, ExpenditureType.POCKET_MONEY, ExpenditureType.NEWSPAPERS_MAGAZINES, ExpenditureType.OTHER_COMMUNICATION_LEISURE_COSTS]:
            return "Communications + Leisure"
        elif self.expenditure_type in [ExpenditureType.GROCERIES, ExpenditureType.NAPPIES_BABY_ITEMS, ExpenditureType.SCHOOL_MEALS, ExpenditureType.LAUNDRY_DRY_CLEANING, ExpenditureType.SMOKING_VAPING, ExpenditureType.VET_BILLS, ExpenditureType.HOUSE_REPAIRS, ExpenditureType.OTHER_FOOD_HOUSEKEEPING_COSTS]:
            return "Food + Housekeeping"
        elif self.expenditure_type in [ExpenditureType.CLOTHING_FOOTWEAR, ExpenditureType.HAIRDRESSING, ExpenditureType.BEAUTY_TREATMENTS, ExpenditureType.TOILETRIES, ExpenditureType.OTHER_PERSONAL_COSTS]:
            return "Personal Costs"
        elif self.expenditure_type == ExpenditureType.MONTHLY_SAVING_AMOUNT:
            return "Savings"
        else:
            return "Other"
    
    @property
    def monthly_amount(self):
        """Convert amount to monthly equivalent for calculations"""
        if not self.amount or not self.frequency:
            return 0
        
        try:
            amount = float(self.amount)
            if self.frequency == PaymentFrequency.WEEKLY:
                return amount * 52 / 12  # 52 weeks per year / 12 months
            elif self.frequency == PaymentFrequency.FORTNIGHTLY:
                return amount * 26 / 12  # 26 fortnights per year / 12 months
            elif self.frequency == PaymentFrequency.FOUR_WEEKLY:
                return amount * 13 / 12  # 13 four-week periods per year / 12 months
            elif self.frequency == PaymentFrequency.MONTHLY:
                return amount
            elif self.frequency == PaymentFrequency.ANNUALLY:
                return amount / 12
            else:
                return amount
        except (ValueError, TypeError):
            return 0
    
    def __repr__(self):
        return f"<Expenditure {self.expenditure_type_display}: £{self.amount} {self.frequency_display}>"
