from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from ..config.database import Base
import uuid

class IncomeType(PyEnum):
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

class PaymentFrequency(PyEnum):
    WEEKLY = "weekly"
    FORTNIGHTLY = "fortnightly"
    FOUR_WEEKLY = "four_weekly"
    MONTHLY = "monthly"
    ANNUALLY = "annually"
    ONE_OFF = "one_off"

class Income(Base):
    __tablename__ = "incomes"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    
    # Income details
    income_type = Column(Enum(IncomeType), nullable=False)
    amount = Column(String, nullable=True)  # Store as string to avoid float precision
    frequency = Column(Enum(PaymentFrequency), nullable=True)
    
    # Source information
    employer_name = Column(String(255), nullable=True)  # For employment income
    source_description = Column(Text, nullable=True)  # For other income types
    
    # Employment specific fields
    is_regular_amount = Column(String(10), nullable=True)  # "Yes"/"No" - Are you paid the same amount every time?
    
    # Additional information
    additional_info = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    case = relationship("Case", back_populates="incomes")
    files = relationship("FileUpload", back_populates="income", cascade="all, delete-orphan")
    
    @property
    def income_type_display(self):
        """Get human-readable income type name"""
        display_names = {
            IncomeType.WAGES_FROM_WORK: "Wages from Work",
            IncomeType.SELF_EMPLOYMENT_EARNINGS: "Self Employment Earnings",
            IncomeType.SICK_PAY_FROM_WORK: "Sick Pay from Work",
            IncomeType.MATERNITY_PAY_FROM_WORK: "Maternity Pay from Work",
            IncomeType.BENEFITS: "Benefits",
            IncomeType.UNIVERSAL_CREDIT: "Universal Credit",
            IncomeType.CHILD_BENEFIT: "Child Benefit",
            IncomeType.HOUSING_BENEFIT: "Housing Benefit",
            IncomeType.COUNCIL_TAX_SUPPORT: "Council Tax Support",
            IncomeType.PERSONAL_INDEPENDENCE_PAYMENT: "Personal Independence Payment (PIP)",
            IncomeType.DISABILITY_LIVING_ALLOWANCE: "Disability Living Allowance (DLA)",
            IncomeType.ATTENDANCE_ALLOWANCE: "Attendance Allowance",
            IncomeType.CARERS_ALLOWANCE: "Carers Allowance",
            IncomeType.EMPLOYMENT_SUPPORT_ALLOWANCE: "Employment & Support Allowance (ESA)",
            IncomeType.GUARDIANS_ALLOWANCE: "Guardians Allowance",
            IncomeType.INDUSTRIAL_INJURIES_BENEFIT: "Industrial Injuries Benefit",
            IncomeType.MATERNITY_ALLOWANCE: "Maternity Allowance",
            IncomeType.PENSION_CREDIT: "Pension Credit",
            IncomeType.OTHER_BENEFIT: "Other Benefit",
            IncomeType.STATE_PENSION: "State Pension",
            IncomeType.PRIVATE_WORK_PENSION: "Private/Work Pension",
            IncomeType.CHILD_MAINTENANCE: "Child Maintenance",
            IncomeType.LODGER_INCOME: "Lodger Income",
            IncomeType.CONTRIBUTIONS_FROM_FAMILY_FRIENDS: "Contributions from Family / Friends",
            IncomeType.STUDENT_LOANS_GRANTS: "Student Loans / Grants",
            IncomeType.OTHER_INCOME_NOT_LISTED: "Other Income (Not Listed)"
        }
        return display_names.get(self.income_type, self.income_type.value.replace('_', ' ').title())
    
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
            PaymentFrequency.ANNUALLY: "Annually",
            PaymentFrequency.ONE_OFF: "One-off"
        }
        return display_names.get(self.frequency, self.frequency.value.replace('_', ' ').title())
    
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
            else:  # one_off
                return 0
        except (ValueError, TypeError):
            return 0
    
    def __repr__(self):
        return f"<Income {self.income_type_display}: £{self.amount} {self.frequency_display}>"
