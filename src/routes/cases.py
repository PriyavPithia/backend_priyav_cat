from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx

from ..config.database import get_db
from ..config.logging import log_case_operation
from ..models import User, Case, CaseStatus, CasePriority, Debt, Asset, Income, Expenditure, DebtType, AssetType, IncomeType, ExpenditureType, PaymentFrequency
from ..utils.frequency_utils import normalize_frequency, get_frequency_multiplier
from .auth import get_current_user
from ..utils.auth import get_client_ip_address

router = APIRouter()

class CaseResponse(BaseModel):
    id: str
    status: str
    has_debt_emergency: Optional[bool]
    emergency_acknowledged: bool
    completion_percentage: float
    debts_completed: bool
    assets_completed: bool
    income_completed: bool
    expenditure_completed: bool
    total_priority_debt: Optional[str] = None
    total_non_priority_debt: Optional[str] = None
    total_assets_value: Optional[str] = None
    total_monthly_income: Optional[str] = None
    total_monthly_expenditure: Optional[str] = None
    monthly_surplus_deficit: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_step: Optional[int] = None

class EmergencyCheckRequest(BaseModel):
    has_debt_emergency: bool
    emergency_acknowledged: bool = False

class DebtData(BaseModel):
    debt_type: str
    amount_owed: Optional[str] = None
    creditor_name: Optional[str] = None
    is_joint: Optional[bool] = None
    additional_info: Optional[str] = None
    other_parent_name: Optional[str] = None
    benefit_type: Optional[str] = None
    fine_reason: Optional[str] = None

class AssetData(BaseModel):
    asset_type: str
    description: Optional[str] = None
    estimated_value: Optional[str] = None
    is_joint: Optional[bool] = None
    property_address: Optional[str] = None
    property_postcode: Optional[str] = None
    vehicle_registration: Optional[str] = None
    savings_institution: Optional[str] = None
    additional_info: Optional[str] = None

class IncomeData(BaseModel):
    income_type: str
    amount: Optional[str] = None
    frequency: Optional[str] = None
    employer_name: Optional[str] = None
    source_description: Optional[str] = None
    is_regular_amount: Optional[str] = None
    additional_info: Optional[str] = None

class ExpenditureData(BaseModel):
    expenditure_type: str
    amount: Optional[str] = None
    frequency: Optional[str] = None
    description: Optional[str] = None
    additional_info: Optional[str] = None

class AutoSaveRequest(BaseModel):
    debts: Optional[List[DebtData]] = None
    assets: Optional[List[AssetData]] = None
    income: Optional[List[IncomeData]] = None
    expenditure: Optional[List[ExpenditureData]] = None
    current_step: Optional[int] = None

class AutoSaveResponse(BaseModel):
    message: str
    case_id: str
    completion_percentage: float
    debts_completed: bool
    assets_completed: bool
    income_completed: bool
    expenditure_completed: bool
    last_step: Optional[int] = None

@router.get("/my-case", response_model=Optional[CaseResponse])
async def get_my_case(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's case"""
    
    if not current_user.is_client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can access this endpoint"
        )
    
    case = db.query(Case).filter(Case.client_id == current_user.id).first()
    
    if not case:
        return None
    
    # Safely get priority value with fallback
    try:
        priority_value = case.priority.value if getattr(case, 'priority', None) else 'NORMAL'
    except (AttributeError, ValueError):
        priority_value = 'NORMAL'  # Fallback if enum value is invalid
    
    return CaseResponse(
        id=case.id,
        status=case.status.value,
        has_debt_emergency=case.has_debt_emergency,
        emergency_acknowledged=case.emergency_acknowledged,
        completion_percentage=case.completion_percentage,
        debts_completed=case.debts_completed,
        assets_completed=case.assets_completed,
        income_completed=case.income_completed,
        expenditure_completed=case.expenditure_completed,
        total_priority_debt=case.total_priority_debt,
        total_non_priority_debt=case.total_non_priority_debt,
        total_assets_value=case.total_assets_value,
        total_monthly_income=case.total_monthly_income,
        total_monthly_expenditure=case.total_monthly_expenditure,
        monthly_surplus_deficit=case.monthly_surplus_deficit,
        created_at=case.created_at,
        updated_at=case.updated_at,
        last_step=case.last_step
    )

@router.post("/create-case", response_model=CaseResponse)
async def create_case(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new case for current user"""
    
    if not current_user.is_client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can create cases"
        )
    
    # If a case already exists, return it instead of 400 to make this idempotent
    existing_case = db.query(Case).filter(Case.client_id == current_user.id).first()
    if existing_case:
        return CaseResponse(
            id=existing_case.id,
            status=existing_case.status.value,
            has_debt_emergency=existing_case.has_debt_emergency,
            emergency_acknowledged=existing_case.emergency_acknowledged,
            completion_percentage=existing_case.completion_percentage,
            debts_completed=existing_case.debts_completed,
            assets_completed=existing_case.assets_completed,
            income_completed=existing_case.income_completed,
            expenditure_completed=existing_case.expenditure_completed,
            total_priority_debt=existing_case.total_priority_debt,
            total_non_priority_debt=existing_case.total_non_priority_debt,
            total_assets_value=existing_case.total_assets_value,
            total_monthly_income=existing_case.total_monthly_income,
            total_monthly_expenditure=existing_case.total_monthly_expenditure,
            monthly_surplus_deficit=existing_case.monthly_surplus_deficit,
            created_at=existing_case.created_at,
            updated_at=existing_case.updated_at,
            last_step=existing_case.last_step
        )
    
    # Create new case
    case = Case(
        client_id=current_user.id,
        office_id=current_user.office_id,
        status=CaseStatus.PENDING
    )
    
    db.add(case)
    db.commit()
    db.refresh(case)
    
    # Log case creation
    log_case_operation(
        operation="case_created",
        case_id=case.id,
        user_id=current_user.id,
        details=f"Created new case for client {current_user.email}",
        ip_address=get_client_ip_address(request)
    )
    
    return CaseResponse(
        id=case.id,
        status=case.status.value,
        has_debt_emergency=case.has_debt_emergency,
        emergency_acknowledged=case.emergency_acknowledged,
        completion_percentage=case.completion_percentage,
        debts_completed=case.debts_completed,
        assets_completed=case.assets_completed,
        income_completed=case.income_completed,
        expenditure_completed=case.expenditure_completed,
        total_priority_debt=case.total_priority_debt,
        total_non_priority_debt=case.total_non_priority_debt,
        total_assets_value=case.total_assets_value,
        total_monthly_income=case.total_monthly_income,
        total_monthly_expenditure=case.total_monthly_expenditure,
        monthly_surplus_deficit=case.monthly_surplus_deficit,
        created_at=case.created_at,
        updated_at=case.updated_at,
        last_step=case.last_step
    )

@router.post("/emergency-check")
async def emergency_check(
    request: EmergencyCheckRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record emergency check response"""
    
    if not current_user.is_client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can access this endpoint"
        )
    
    # Get or create case
    case = db.query(Case).filter(Case.client_id == current_user.id).first()
    if not case:
        case = Case(
            client_id=current_user.id,
            office_id=current_user.office_id,
            status=CaseStatus.PENDING
        )
        db.add(case)
    else:
        # Check if case can be updated
        if case.status == CaseStatus.SUBMITTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update a submitted case. Please contact an adviser if you need to make changes."
            )
        
        if case.status == CaseStatus.CLOSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update a closed case. Please contact an adviser if you need to make changes."
            )
    
    # Update emergency check
    case.has_debt_emergency = request.has_debt_emergency
    case.emergency_acknowledged = request.emergency_acknowledged
    
    # Automatically set priority to URGENT if case has debt emergency
    if request.has_debt_emergency:
        case.priority = CasePriority.URGENT
    
    db.commit()
    
    return {"message": "Emergency check recorded"}

@router.post("/reset-case")
async def reset_case(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reset case data and start over"""
    
    if not current_user.is_client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can access this endpoint"
        )
    
    # Get the case
    case = db.query(Case).filter(Case.client_id == current_user.id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No case found for this user"
        )
    
    # Check if case can be reset
    if case.status == CaseStatus.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reset a submitted case. Please contact an adviser if you need to make changes."
        )
    
    if case.status == CaseStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reset a closed case. Please contact an adviser if you need to make changes."
        )
    
    # Delete all related records so no values persist
    # Note: Files are intentionally preserved during case reset to allow users to keep their uploaded documents
    db.query(Debt).filter(Debt.case_id == case.id).delete()
    db.query(Asset).filter(Asset.case_id == case.id).delete()
    db.query(Income).filter(Income.case_id == case.id).delete()
    db.query(Expenditure).filter(Expenditure.case_id == case.id).delete()

    # Reset all case flags and aggregates
    case.has_debt_emergency = None
    case.emergency_acknowledged = False
    case.debts_completed = False
    case.assets_completed = False
    case.income_completed = False
    case.expenditure_completed = False
    case.total_priority_debt = None
    case.total_non_priority_debt = None
    case.total_assets_value = None
    case.total_monthly_income = None
    case.total_monthly_expenditure = None
    case.monthly_surplus_deficit = None
    case.additional_notes = None
    case.client_comments = None
    case.status = CaseStatus.PENDING
    case.last_step = None
    
    db.commit()
    
    return {"message": "Case reset successfully"}

# TODO: Add more endpoints for:
# - Debt collection
# - Asset collection  
# - Income collection
# - Expenditure collection
# - File uploads
# - Case submission

@router.post("/submit-case")
async def submit_case(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit case for review - changes status to submitted and prevents further updates"""
    
    if not current_user.is_client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can access this endpoint"
        )
    
    # Get the case
    case = db.query(Case).filter(Case.client_id == current_user.id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No case found for this user"
        )
    
    # Check if case is already submitted
    if case.status == CaseStatus.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Case is already submitted"
        )
    
    # Check if case is complete
    if not case.is_complete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Case must be complete before submission"
        )
    
    # If assets are not completed, set default "none_of_above" selection
    if not case.assets_completed:
        # Check if user has any assets at all
        existing_assets = db.query(Asset).filter(Asset.case_id == case.id).all()
        
        if not existing_assets:
            # Create a "none_of_above" asset entry
            none_asset = Asset(
                case_id=case.id,
                asset_type=AssetType.NONE_OF_ABOVE,
                description="No assets declared",
                estimated_value="0.00"
            )
            db.add(none_asset)
            case.assets_completed = True
    
    # Submit the case
    case.status = CaseStatus.SUBMITTED
    case.submitted_at = datetime.utcnow()
    
    db.commit()
    
    # Log case submission
    log_case_operation(
        operation="case_submitted",
        case_id=case.id,
        user_id=current_user.id,
        details=f"Case submitted for review by client {current_user.email}",
        ip_address=get_client_ip_address(request)
    )
    
    return {"message": "Case submitted successfully"}

@router.get("/can-edit")
async def can_edit_case(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user can edit their case"""
    
    if not current_user.is_client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can access this endpoint"
        )
    
    # Get the case
    case = db.query(Case).filter(Case.client_id == current_user.id).first()
    if not case:
        return {"can_edit": True, "reason": "No case exists"}
    
    # Check if case is submitted
    if case.status == CaseStatus.SUBMITTED:
        return {"can_edit": False, "reason": "Case is submitted and cannot be edited"}
    
    # Check if case is closed
    if case.status == CaseStatus.CLOSED:
        return {"can_edit": False, "reason": "Case is closed and cannot be edited"}
    
    return {"can_edit": True, "reason": "Case can be edited"}

@router.post("/auto-save", response_model=AutoSaveResponse)
async def auto_save_case_data(
    request: AutoSaveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Auto-save case data including debts, assets, income, and expenditure"""
    
    if not current_user.is_client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can access this endpoint"
        )
    
    # Get or create case
    case = db.query(Case).filter(Case.client_id == current_user.id).first()
    if not case:
        case = Case(
            client_id=current_user.id,
            office_id=current_user.office_id,
            status=CaseStatus.PENDING
        )
        db.add(case)
        db.flush()  # Get the ID without committing
    
    # Check if case can be updated
    if case.status == CaseStatus.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update a submitted case"
        )
    
    if case.status == CaseStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update a closed case"
        )
    
    try:
        # Save debts if provided
        if request.debts is not None:
            # Delete existing debts
            db.query(Debt).filter(Debt.case_id == case.id).delete()
            
            # Add new debts
            total_priority_debt = 0
            total_non_priority_debt = 0
            
            for debt_data in request.debts:
                debt = Debt(
                    case_id=case.id,
                    debt_type=DebtType(debt_data.debt_type),
                    amount_owed=debt_data.amount_owed,
                    creditor_name=debt_data.creditor_name,
                    is_joint=debt_data.is_joint,
                    additional_info=debt_data.additional_info,
                    other_parent_name=debt_data.other_parent_name,
                    benefit_type=debt_data.benefit_type,
                    fine_reason=debt_data.fine_reason
                )
                db.add(debt)
                

                
                # Calculate totals
                if debt_data.amount_owed:
                    try:
                        amount = float(debt_data.amount_owed.replace(',', ''))
                        if debt.is_priority_debt:
                            total_priority_debt += amount
                        else:
                            total_non_priority_debt += amount
                    except (ValueError, TypeError):
                        pass
            
            case.total_priority_debt = str(total_priority_debt) if total_priority_debt > 0 else None
            case.total_non_priority_debt = str(total_non_priority_debt) if total_non_priority_debt > 0 else None
            # Mark as completed if user has made selections (even if details are incomplete)
            case.debts_completed = len(request.debts) > 0
        
        # Helper: normalize and validate postcode (basic UK format: outward + space + inward)
        def _normalize_postcode(pc: Optional[str]) -> Optional[str]:
            if not pc:
                return None
            try:
                cleaned = pc.replace(" ", "").upper()
                # Minimal length check and alnum
                if len(cleaned) < 5 or len(cleaned) > 8 or not cleaned.isalnum():
                    return None
                # Insert space before last 3 characters
                return cleaned[:-3] + " " + cleaned[-3:]
            except Exception:
                return None

        # Save assets if provided
        if request.assets is not None:
            # Delete existing assets
            db.query(Asset).filter(Asset.case_id == case.id).delete()
            
            # Add new assets
            total_assets_value = 0
            
            for asset_data in request.assets:
                # Enforce postcode validation/normalization for property only
                normalized_pc = _normalize_postcode(asset_data.property_postcode) if asset_data.asset_type == 'property' else None
                asset = Asset(
                    case_id=case.id,
                    asset_type=AssetType(asset_data.asset_type),
                    description=asset_data.description,
                    estimated_value=asset_data.estimated_value,
                    is_joint=asset_data.is_joint,
                    property_address=asset_data.property_address,
                    property_postcode=normalized_pc,
                    vehicle_registration=asset_data.vehicle_registration,
                    savings_institution=asset_data.savings_institution,
                    additional_info=asset_data.additional_info
                )
                db.add(asset)
                

                
                # Calculate total
                if asset_data.estimated_value:
                    try:
                        value = float(asset_data.estimated_value.replace(',', ''))
                        total_assets_value += value
                    except (ValueError, TypeError):
                        pass
            
            case.total_assets_value = str(total_assets_value) if total_assets_value > 0 else None
            # Mark as completed if user has made selections (even if details are incomplete)
            case.assets_completed = len(request.assets) > 0
        
        # Save income if provided
        if request.income is not None:
            # Delete existing income
            db.query(Income).filter(Income.case_id == case.id).delete()
            
            # Add new income
            total_monthly_income = 0
            
            for income_data in request.income:
                income = Income(
                    case_id=case.id,
                    income_type=IncomeType(income_data.income_type),
                    amount=income_data.amount,
                    frequency=normalize_frequency(income_data.frequency),
                    employer_name=income_data.employer_name,
                    source_description=income_data.source_description,
                    is_regular_amount=income_data.is_regular_amount,
                    additional_info=income_data.additional_info
                )
                db.add(income)
                

                
                # Calculate monthly total
                if income_data.amount:
                    try:
                        amount = float(income_data.amount.replace(',', ''))
                        frequency = normalize_frequency(income_data.frequency)
                        multiplier = get_frequency_multiplier(frequency)
                        total_monthly_income += amount * multiplier
                    except (ValueError, TypeError):
                        pass
            
            case.total_monthly_income = str(total_monthly_income) if total_monthly_income > 0 else None
            # Mark as completed if user has made selections (even if details are incomplete)
            case.income_completed = len(request.income) > 0
        
        # Save expenditure if provided
        if request.expenditure is not None:
            # Delete existing expenditure
            db.query(Expenditure).filter(Expenditure.case_id == case.id).delete()
            
            # Add new expenditure
            total_monthly_expenditure = 0
            
            for expenditure_data in request.expenditure:
                expenditure = Expenditure(
                    case_id=case.id,
                    expenditure_type=ExpenditureType(expenditure_data.expenditure_type),
                    amount=expenditure_data.amount,
                    frequency=normalize_frequency(expenditure_data.frequency),
                    provider_name=expenditure_data.description,  # Map description to provider_name
                    additional_info=expenditure_data.additional_info
                )
                db.add(expenditure)
                

                
                # Calculate monthly total
                if expenditure_data.amount:
                    try:
                        amount = float(expenditure_data.amount.replace(',', ''))
                        frequency = normalize_frequency(expenditure_data.frequency)
                        multiplier = get_frequency_multiplier(frequency)
                        total_monthly_expenditure += amount * multiplier
                    except (ValueError, TypeError):
                        pass
            
            case.total_monthly_expenditure = str(total_monthly_expenditure) if total_monthly_expenditure > 0 else None
            # Mark as completed if user has made selections (even if details are incomplete)
            case.expenditure_completed = len(request.expenditure) > 0
        
        # Calculate monthly surplus/deficit
        if case.total_monthly_income and case.total_monthly_expenditure:
            try:
                income = float(case.total_monthly_income)
                expenditure = float(case.total_monthly_expenditure)
                surplus_deficit = income - expenditure
                case.monthly_surplus_deficit = str(surplus_deficit)
            except (ValueError, TypeError):
                case.monthly_surplus_deficit = None

        # Persist last step if provided
        if request.current_step is not None:
            try:
                # Clamp to sensible bounds 0..5
                step = int(request.current_step)
                if step < 0:
                    step = 0
                if step > 5:
                    step = 5
                case.last_step = step
            except Exception:
                pass
        
        db.commit()
        
        return AutoSaveResponse(
            message="Case data saved successfully",
            case_id=case.id,
            completion_percentage=case.completion_percentage,
            debts_completed=case.debts_completed,
            assets_completed=case.assets_completed,
            income_completed=case.income_completed,
            expenditure_completed=case.expenditure_completed,
            last_step=case.last_step
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save case data: {str(e)}"
        )

@router.get("/validate-postcode/{postcode}", name="validate_postcode")
async def validate_postcode(
    postcode: str
):
    """Validate a UK postcode using postcodes.io"""
    try:
        # Clean the postcode
        cleaned = postcode.replace(" ", "").upper()
        print(f"Validating postcode: {cleaned}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Validate
            validate_url = f"https://api.postcodes.io/postcodes/{cleaned}/validate"
            print(f"Calling validation endpoint: {validate_url}")
            validate_response = await client.get(validate_url)
            
            if validate_response.status_code != 200:
                print(f"Validation API error: {validate_response.status_code}")
                return {"isValid": False, "message": f"Postcode.io API error: {validate_response.status_code}"}
                
            validate_data = validate_response.json()
            print(f"Validation response: {validate_data}")
            
            if not validate_data.get("result"):
                return {"isValid": False, "message": "Invalid postcode format"}
            
            # Lookup details
            lookup_url = f"https://api.postcodes.io/postcodes/{cleaned}"
            print(f"Calling lookup endpoint: {lookup_url}")
            lookup_response = await client.get(lookup_url)
            
            if lookup_response.status_code != 200:
                print(f"Lookup API error: {lookup_response.status_code}")
                return {"isValid": True, "message": "Valid postcode but unable to retrieve details"}
                
            lookup_data = lookup_response.json()
            result = lookup_data.get("result", {})
            print(f"Lookup response: {result}")
            
            if not result:
                return {"isValid": True, "message": "Valid postcode but no details available"}
            
            return {
                "isValid": True,
                "message": f"✓ Valid postcode - {result.get('admin_district', 'Unknown District')}, {result.get('region', 'Unknown Region')}",
                "addressData": {
                    "admin_district": result.get("admin_district", "Unknown"),
                    "region": result.get("region", "Unknown"),
                    "country": result.get("country", "Unknown")
                }
            }
            
    except httpx.TimeoutException:
        print("Postcode validation timeout")
        return {"isValid": False, "message": "Validation service timeout"}
    except httpx.RequestError as e:
        print(f"Postcode validation request error: {str(e)}")
        return {"isValid": False, "message": "Unable to connect to validation service"}
    except Exception as e:
        print(f"Postcode validation error: {str(e)}")
        return {"isValid": False, "message": "Error validating postcode"}

@router.get("/case-data")
async def get_case_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get complete case data including debts, assets, income, and expenditure"""
    
    if not current_user.is_client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can access this endpoint"
        )
    
    case = db.query(Case).filter(Case.client_id == current_user.id).first()
    if not case:
        return {"case": None, "debts": [], "assets": [], "income": [], "expenditure": []}
    
    # Get debts
    debts = db.query(Debt).filter(Debt.case_id == case.id).all()
    debt_data = []
    for debt in debts:
        debt_data.append({
            "debt_type": debt.debt_type.value,
            "amount_owed": debt.amount_owed,
            "creditor_name": debt.creditor_name,
            "is_joint": debt.is_joint,
            "additional_info": debt.additional_info,
            "other_parent_name": debt.other_parent_name,
            "benefit_type": debt.benefit_type,
            "fine_reason": debt.fine_reason
        })
    
    # Get assets
    assets = db.query(Asset).filter(Asset.case_id == case.id).all()
    asset_data = []
    for asset in assets:
        asset_data.append({
            "asset_type": asset.asset_type.value,
            "description": asset.description,
            "estimated_value": asset.estimated_value,
            "is_joint": asset.is_joint,
            "property_address": asset.property_address,
            "property_postcode": asset.property_postcode,
            "vehicle_registration": asset.vehicle_registration,
            "savings_institution": asset.savings_institution,
            "additional_info": asset.additional_info
        })
    
    # Get income
    income = db.query(Income).filter(Income.case_id == case.id).all()
    income_data = []
    for inc in income:
        income_data.append({
            "income_type": inc.income_type.value,
            "amount": inc.amount,
            "frequency": inc.frequency.value if inc.frequency else None,
            "employer_name": inc.employer_name,
            "source_description": inc.source_description,
            "is_regular_amount": inc.is_regular_amount,
            "additional_info": inc.additional_info
        })
    
    # Get expenditure
    expenditure = db.query(Expenditure).filter(Expenditure.case_id == case.id).all()
    expenditure_data = []
    for exp in expenditure:
        expenditure_data.append({
            "expenditure_type": exp.expenditure_type.value,
            "amount": exp.amount,
            "frequency": exp.frequency.value if exp.frequency else None,
            "description": exp.provider_name,  # Map provider_name back to description
            "additional_info": exp.additional_info
        })
    
    return {
        "case": {
            "id": case.id,
            "status": case.status.value,
            "has_debt_emergency": case.has_debt_emergency,
            "emergency_acknowledged": case.emergency_acknowledged,
            "completion_percentage": case.completion_percentage,
            "debts_completed": case.debts_completed,
            "assets_completed": case.assets_completed,
            "income_completed": case.income_completed,
            "expenditure_completed": case.expenditure_completed,
            "total_priority_debt": case.total_priority_debt,
            "total_non_priority_debt": case.total_non_priority_debt,
            "total_assets_value": case.total_assets_value,
            "total_monthly_income": case.total_monthly_income,
            "total_monthly_expenditure": case.total_monthly_expenditure,
            "monthly_surplus_deficit": case.monthly_surplus_deficit,
            "ca_client_number": current_user.ca_client_number,
            "client_name": f"{current_user.first_name or ''} {current_user.last_name or ''}".strip(),
            "created_at": case.created_at,
            "updated_at": case.updated_at
        },
        "debts": debt_data,
        "assets": asset_data,
        "income": income_data,
        "expenditure": expenditure_data
    }
