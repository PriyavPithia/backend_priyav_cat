from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from ..config.database import Base
import uuid

class DebtType(PyEnum):
    # Priority Debts (16 types)
    MORTGAGE_ARREARS = "mortgage_arrears"
    RENT_ARREARS = "rent_arrears" 
    SECURED_LOAN_ARREARS = "secured_loan_arrears"
    COUNCIL_TAX_ARREARS = "council_tax_arrears"
    TV_LICENCE_ARREARS = "tv_licence_arrears"
    HIRE_PURCHASE_ARREARS = "hire_purchase_arrears"
    GAS_ARREARS = "gas_arrears"
    ELECTRICITY_ARREARS = "electricity_arrears"
    WATER_ARREARS = "water_arrears"
    CHILD_MAINTENANCE_ARREARS = "child_maintenance_arrears"
    MAGISTRATES_COURT_FINE = "magistrates_court_fine"
    NI_INCOME_TAX_ARREARS = "ni_income_tax_arrears"
    HMRC_TAX_CREDIT_OVERPAYMENT = "hmrc_tax_credit_overpayment"
    DWP_BENEFIT_OVERPAYMENT = "dwp_benefit_overpayment"
    FRIENDS_FAMILY_DEBT = "friends_family_debt"
    FIXED_PENALTY_NOTICE = "fixed_penalty_notice"
    FRAUD = "fraud"
    
    # Non-Priority Debts (17 types)
    BUSINESS_DEBT = "business_debt"
    CATALOGUE_DEBT = "catalogue_debt"
    CCJ_ORIGIN_UNKNOWN = "ccj_origin_unknown"
    CREDIT_CARD = "credit_card"
    LOAN_SHARK_DEBT = "loan_shark_debt"
    EMPLOYER_FORMER_EMPLOYER = "employer_former_employer"
    GAS_ELECTRICITY_FORMER_SUPPLIER = "gas_electricity_former_supplier"
    MOBILE_PHONE_ARREARS = "mobile_phone_arrears"
    NHS_COSTS_CHARGES = "nhs_costs_charges"
    PARKING_CHARGE_NOTICE = "parking_charge_notice"
    PAYDAY_LOAN = "payday_loan"
    RENT_ARREARS_FORMER_TENANCY = "rent_arrears_former_tenancy"
    STORE_CARD = "store_card"
    TELEPHONE_BROADBAND = "telephone_broadband"
    UNSECURED_BANK_LOAN = "unsecured_bank_loan"
    ANY_OTHER_DEBT = "any_other_debt"

class Debt(Base):
    __tablename__ = "debts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    
    # Debt details
    debt_type = Column(Enum(DebtType), nullable=False)
    amount_owed = Column(String, nullable=True)  # Store as string to avoid float precision
    creditor_name = Column(String(255), nullable=True)  # Who do you owe it to?
    # Joint flag
    is_joint = Column(Boolean, nullable=True)
    
    # Additional information
    additional_info = Column(Text, nullable=True)
    
    # Specific fields for certain debt types
    other_parent_name = Column(String(255), nullable=True)  # For child maintenance
    benefit_type = Column(String(255), nullable=True)  # For DWP benefit overpayment
    fine_reason = Column(Text, nullable=True)  # For fixed penalty notice
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    case = relationship("Case", back_populates="debts")
    files = relationship("FileUpload", back_populates="debt", cascade="all, delete-orphan")
    
    @property
    def is_priority_debt(self):
        """Check if this is a priority debt"""
        priority_debts = [
            DebtType.MORTGAGE_ARREARS, DebtType.RENT_ARREARS, DebtType.SECURED_LOAN_ARREARS,
            DebtType.COUNCIL_TAX_ARREARS, DebtType.TV_LICENCE_ARREARS, DebtType.HIRE_PURCHASE_ARREARS,
            DebtType.GAS_ARREARS, DebtType.ELECTRICITY_ARREARS, DebtType.WATER_ARREARS,
            DebtType.CHILD_MAINTENANCE_ARREARS, DebtType.MAGISTRATES_COURT_FINE, 
            DebtType.NI_INCOME_TAX_ARREARS, DebtType.HMRC_TAX_CREDIT_OVERPAYMENT,
            DebtType.DWP_BENEFIT_OVERPAYMENT, DebtType.FRIENDS_FAMILY_DEBT,
            DebtType.FIXED_PENALTY_NOTICE, DebtType.FRAUD
        ]
        return self.debt_type in priority_debts
    
    @property
    def debt_type_display(self):
        """Get human-readable debt type name"""
        display_names = {
            DebtType.MORTGAGE_ARREARS: "Mortgage Arrears",
            DebtType.RENT_ARREARS: "Rent Arrears",
            DebtType.SECURED_LOAN_ARREARS: "Secured Loan Arrears",
            DebtType.COUNCIL_TAX_ARREARS: "Council Tax Arrears",
            DebtType.TV_LICENCE_ARREARS: "TV Licence Arrears",
            DebtType.HIRE_PURCHASE_ARREARS: "Hire Purchase (HP) / Conditional Sale Arrears",
            DebtType.GAS_ARREARS: "Gas Arrears",
            DebtType.ELECTRICITY_ARREARS: "Electricity Arrears",
            DebtType.WATER_ARREARS: "Water Arrears",
            DebtType.CHILD_MAINTENANCE_ARREARS: "Child Maintenance Arrears (CMS)",
            DebtType.MAGISTRATES_COURT_FINE: "Magistrates Court Fine",
            DebtType.NI_INCOME_TAX_ARREARS: "NI Contribution / Income Tax Arrears",
            DebtType.HMRC_TAX_CREDIT_OVERPAYMENT: "HMRC Tax Credit Overpayment",
            DebtType.DWP_BENEFIT_OVERPAYMENT: "DWP Benefit Overpayment",
            DebtType.FRIENDS_FAMILY_DEBT: "Friends / Family Debt",
            DebtType.FIXED_PENALTY_NOTICE: "Fixed Penalty Notice",
            DebtType.FRAUD: "Fraud",
            DebtType.BUSINESS_DEBT: "Business Debt",
            DebtType.CATALOGUE_DEBT: "Catalogue Debt",
            DebtType.CCJ_ORIGIN_UNKNOWN: "CCJ (Origin Unknown)",
            DebtType.CREDIT_CARD: "Credit Card",
            DebtType.LOAN_SHARK_DEBT: "Debt to a Loan Shark",
            DebtType.EMPLOYER_FORMER_EMPLOYER: "Employer / Former Employer",
            DebtType.GAS_ELECTRICITY_FORMER_SUPPLIER: "Gas/Electricity to Former Supplier",
            DebtType.MOBILE_PHONE_ARREARS: "Mobile Phone Arrears",
            DebtType.NHS_COSTS_CHARGES: "NHS Costs and Charges",
            DebtType.PARKING_CHARGE_NOTICE: "Parking Charge Notice (PCN)",
            DebtType.PAYDAY_LOAN: "Payday Loan",
            DebtType.RENT_ARREARS_FORMER_TENANCY: "Rent Arrears (Former Tenancy)",
            DebtType.STORE_CARD: "Store Card",
            DebtType.TELEPHONE_BROADBAND: "Telephone / Broadband",
            DebtType.UNSECURED_BANK_LOAN: "Unsecured Loan or Bank Loan",
            DebtType.ANY_OTHER_DEBT: "Any Other Debt"
        }
        return display_names.get(self.debt_type, self.debt_type.value.replace('_', ' ').title())
    
    def __repr__(self):
        return f"<Debt {self.debt_type_display}: {self.amount_owed}>"
