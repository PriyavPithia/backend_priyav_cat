from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from ..config.database import Base
import uuid

class AssetType(PyEnum):
    PROPERTY = "property"
    VEHICLE = "vehicle"
    SAVINGS = "savings"
    CASH = "cash"
    OTHER_VALUABLE_ITEMS = "other_valuable_items"
    NONE_OF_ABOVE = "none_of_above"

class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    
    # Asset details
    asset_type = Column(Enum(AssetType), nullable=False)
    description = Column(Text, nullable=True)
    estimated_value = Column(String, nullable=True)  # Store as string to avoid float precision
    # Joint flag for ownership
    is_joint = Column(Boolean, nullable=True)
    
    # Specific fields for different asset types
    property_address = Column(Text, nullable=True)  # For property
    property_postcode = Column(String(20), nullable=True)  # For property postcode
    vehicle_registration = Column(String(20), nullable=True)  # For vehicles
    savings_institution = Column(String(255), nullable=True)  # For savings (where held)
    
    # Additional information
    additional_info = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    case = relationship("Case", back_populates="assets")
    files = relationship("FileUpload", back_populates="asset", cascade="all, delete-orphan")
    
    @property
    def asset_type_display(self):
        """Get human-readable asset type name"""
        display_names = {
            AssetType.PROPERTY: "Property",
            AssetType.VEHICLE: "Vehicle(s)",
            AssetType.SAVINGS: "Savings",
            AssetType.CASH: "Cash",
            AssetType.OTHER_VALUABLE_ITEMS: "Other Valuable Item(s)"
        }
        return display_names.get(self.asset_type, self.asset_type.value.replace('_', ' ').title())
    
    @property
    def formatted_value(self):
        """Format the estimated value with currency symbol"""
        if self.estimated_value:
            try:
                value = float(self.estimated_value)
                return f"£{value:,.2f}"
            except (ValueError, TypeError):
                return self.estimated_value
        return "Not specified"
    
    def __repr__(self):
        return f"<Asset {self.asset_type_display}: {self.formatted_value}>"
