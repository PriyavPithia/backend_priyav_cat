from .office import Office
from .user import User, UserRole, UserStatus
from .client_details import ClientDetails, Title, Gender, Ethnicity, DisabilityStatus, MaritalStatus, HouseholdType, Occupation, HousingTenure
from .case import Case, CaseStatus, CasePriority
from .debt import Debt, DebtType
from .asset import Asset, AssetType
from .income import Income, IncomeType, PaymentFrequency
from .expenditure import Expenditure, ExpenditureType
from .file_upload import FileUpload, FileCategory, FileStatus
from .audit_log import AuditLog, AuditAction
from .notification import Notification, NotificationType
from .session_settings import SessionSettings

# Import the base and database config
from ..config.database import Base, engine

# Create all tables
def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

__all__ = [
    "Office",
    "User", "UserRole", "UserStatus",
    "ClientDetails", "Title", "Gender", "Ethnicity", "DisabilityStatus", "MaritalStatus", "HouseholdType", "Occupation", "HousingTenure",
    "Case", "CaseStatus", "CasePriority",
    "Debt", "DebtType",
    "Asset", "AssetType",
    "Income", "IncomeType", "PaymentFrequency",
    "Expenditure", "ExpenditureType", 
    "FileUpload", "FileCategory", "FileStatus",
    "AuditLog", "AuditAction",
    "Notification", "NotificationType",
    "SessionSettings",
    "Base", "engine", "create_tables"
]
