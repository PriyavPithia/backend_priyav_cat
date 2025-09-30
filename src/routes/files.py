from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Form, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from typing import Optional, List
import os
from datetime import datetime

from ..config.database import get_db
from ..config.settings import settings
from ..config.logging import get_logger, log_file_operation
from ..models.audit_log import AuditLog
from ..models.user import User
from ..models.case import Case
from ..models.file_upload import FileUpload, FileCategory, FileStatus
from ..schemas.file_upload import (
    FileUploadRequest, 
    FileUploadResponse, 
    FileListResponse,
    FileMetadataResponse
)
from .auth import get_current_user
from ..utils.auth import get_client_ip_address
from ..utils.file_utils import (
    save_uploaded_file, 
    read_uploaded_file, 
    get_file_mime_type,
    get_file_category_from_context,
    create_files_zip,
    get_client_id_from_user
)
from ..utils.s3_first_storage import s3_first_storage as hybrid_storage
from ..config.settings import settings

router = APIRouter()
logger = get_logger('files')

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    case_id: Optional[str] = Form(None),
    debt_id: Optional[str] = Form(None),
    asset_id: Optional[str] = Form(None),
    income_id: Optional[str] = Form(None),
    expenditure_id: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    debt_type: Optional[str] = Form(None),
    asset_type: Optional[str] = Form(None),
    income_type: Optional[str] = Form(None),
    expenditure_type: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a file for a case"""
    logger.info(f"File upload request: {file.filename} ({file.content_type}) by user {current_user.id} ({current_user.role})")
    
    try:
        # Validate request parameters using Pydantic model
        upload_request = FileUploadRequest(
            case_id=case_id,
            debt_id=debt_id,
            asset_id=asset_id,
            income_id=income_id,
            expenditure_id=expenditure_id,
            description=description,
            category=category,
            debt_type=debt_type,
            asset_type=asset_type,
            income_type=income_type,
            expenditure_type=expenditure_type
        )
        
        # Get user's case if case_id not provided
        if not upload_request.case_id:
            if current_user.role == 'CLIENT':
                case = db.query(Case).filter(Case.client_id == current_user.id).first()
                if not case:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="No case found for user. Create a case first."
                    )
                upload_request.case_id = case.id
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="case_id is required for non-client users"
                )
        
        # Verify case exists and user has access
        case = db.query(Case).filter(Case.id == upload_request.case_id).first()
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
        
        # Check access permissions
        if current_user.role == 'CLIENT' and case.client_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this case"
            )
        elif current_user.role != 'CLIENT' and case.office_id != current_user.office_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this case"
            )
        
        # Determine file category
        if not upload_request.category:
            upload_request.category = get_file_category_from_context(
                debt_type=upload_request.debt_type,
                asset_type=upload_request.asset_type,
                income_type=upload_request.income_type,
                expenditure_type=upload_request.expenditure_type
            )
        
        # Get client ID for file naming
        if current_user.role == 'CLIENT':
            client_id = get_client_id_from_user(current_user)
        else:
            # For admins/advisers, get client from case
            case_client = db.query(User).filter(User.id == case.client_id).first()
            client_id = get_client_id_from_user(case_client) if case_client else None
        
        logger.debug(f"Client ID for file naming: {client_id}")
        
        # Save file using hybrid storage (S3 + local)
        logger.debug("Calling hybrid storage save_file...")
        success, file_path, s3_key, metadata = await hybrid_storage.save_file(
            file=file,
            case_id=upload_request.case_id,
            uploaded_by_id=current_user.id,
            client_id=client_id,
            encrypt=True,
            category=upload_request.category
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save file"
            )
            
        logger.info(f"File saved successfully: {file.filename} -> {file_path}")
        
        # Create database record
        file_record = FileUpload(
            case_id=upload_request.case_id,
            debt_id=upload_request.debt_id,
            asset_id=upload_request.asset_id,
            income_id=upload_request.income_id,
            expenditure_id=upload_request.expenditure_id,
            original_filename=metadata['original_filename'],
            stored_filename=metadata['stored_filename'],
            file_path=metadata['file_path'],
            file_size=metadata['file_size'],
            file_extension=metadata['file_extension'],
            mime_type=metadata['mime_type'],
            # S3 fields
            s3_key=s3_key,
            storage_type=metadata.get('storage_type', 'local'),
            category=FileCategory(upload_request.category) if upload_request.category else FileCategory.OTHER,
            status=FileStatus.UPLOADED,
            file_hash=metadata['file_hash'],
            is_encrypted=metadata['is_encrypted'],
            encryption_key_id=metadata['encryption_key'],
            description=upload_request.description or None,
            uploaded_by_id=current_user.id,
            was_converted=metadata.get('was_converted', False),
            # Add type information for filtering
            debt_type=upload_request.debt_type,
            asset_type=upload_request.asset_type,
            income_type=upload_request.income_type,
            expenditure_type=upload_request.expenditure_type
        )
        
        db.add(file_record)
        db.commit()
        db.refresh(file_record)
        
        # Log successful file upload
        ip_address = get_client_ip_address(request)
        AuditLog.log_action(
            db,
            action="file_upload",
            user_id=current_user.id,
            office_id=current_user.office_id,
            description=f"Uploaded {file_record.original_filename} ({file_record.file_size_formatted}) for case {upload_request.case_id}",
            ip_address=ip_address,
            success=True,
            file_id=str(file_record.id),
            filename=file_record.original_filename,
            resource_type="file",
            resource_id=str(file_record.id)
        )
        db.commit()
        log_file_operation(
            "upload",
            file_id=str(file_record.id),
            user_id=current_user.id,
            details=f"Uploaded {file_record.original_filename} ({file_record.file_size_formatted}) for case {upload_request.case_id}",
            ip_address=ip_address
        )
        
        return FileUploadResponse(
            id=str(file_record.id),
            original_filename=file_record.original_filename,
            file_size=file_record.file_size,
            file_size_formatted=file_record.file_size_formatted,
            category=file_record.category.value,
            description=file_record.description,
            created_at=file_record.created_at.isoformat(),
            status="uploaded",
            was_converted=metadata.get('was_converted', False)
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Log failed upload attempt
        ip_address = get_client_ip_address(request)
        AuditLog.log_action(
            db,
            action="file_upload",
            user_id=current_user.id,
            office_id=current_user.office_id,
            description=f"Failed to upload {file.filename}: {str(e)}",
            ip_address=ip_address,
            success=False
        )
        db.commit()
        log_file_operation(
            "upload_failed",
            user_id=current_user.id,
            details=f"Failed to upload {file.filename}: {str(e)}",
            ip_address=ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )

@router.get("/list/{case_id}")
async def list_case_files(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all files for a case"""
    
    # Verify case exists and user has access
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # Check access permissions
    if current_user.role == 'CLIENT' and case.client_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this case"
        )
    elif current_user.role != 'CLIENT' and case.office_id != current_user.office_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this case"
        )
    
    files = db.query(FileUpload).filter(
        FileUpload.case_id == case_id,
        FileUpload.status != FileStatus.DELETED
    ).order_by(FileUpload.created_at.desc()).all()
    
    result = []
    for file in files:
        file_data = {
            "id": file.id,
            "original_filename": file.original_filename,
            "stored_filename": file.stored_filename,
            "file_size": file.file_size,
            "file_size_formatted": file.file_size_formatted,
            "category": file.category.value,
            "description": file.description,
            "created_at": file.created_at,
            "is_image": file.is_image,
            "is_document": file.is_document,
            "status": file.status.value,
            "uploaded_at": file.created_at,  # Add uploaded_at for compatibility
            "was_converted": file.was_converted if hasattr(file, 'was_converted') else False
        }

        # Preferred display filename includes client prefix already in stored_filename
        # If file was converted (HEIC to JPEG/PNG), show the converted extension
        try:
            if file.was_converted and file.original_filename.lower().endswith('.heic'):
                # Show converted extension for HEIC files, but keep the client prefix from stored_filename
                if file.stored_filename:
                    # Use the stored filename which already includes client prefix, just change the extension
                    base_name = os.path.splitext(file.stored_filename)[0]
                    converted_ext = os.path.splitext(file.stored_filename)[1] if file.stored_filename else '.jpg'
                    converted_display_name = f"{base_name}{converted_ext}"
                else:
                    # Fallback to original filename if no stored filename
                    base_name = os.path.splitext(file.original_filename)[0]
                    converted_display_name = f"{base_name}.jpg"
                file_data["display_filename"] = converted_display_name
            else:
                file_data["display_filename"] = file.stored_filename or file.original_filename
        except Exception:
            file_data["display_filename"] = file.original_filename
        
        # Add type information (from file record or related records)
        file_data["debt_type"] = file.debt_type
        file_data["asset_type"] = file.asset_type
        file_data["income_type"] = file.income_type
        file_data["expenditure_type"] = file.expenditure_type
        
        # If type fields are empty, try to get from related records
        if not file.debt_type and file.debt_id and file.debt:
            file_data["debt_type"] = file.debt.debt_type.value if file.debt.debt_type else None
        if not file.asset_type and file.asset_id and file.asset:
            file_data["asset_type"] = file.asset.asset_type.value if file.asset.asset_type else None
        if not file.income_type and file.income_id and file.income:
            file_data["income_type"] = file.income.income_type.value if file.income.income_type else None
        if not file.expenditure_type and file.expenditure_id and file.expenditure:
            file_data["expenditure_type"] = file.expenditure.expenditure_type.value if file.expenditure.expenditure_type else None
        
        result.append(file_data)
    
    return result

@router.get("/view/{file_id}")
async def view_file(
    file_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """View a file in browser (inline display) with enhanced security"""
    
    # Get file record
    file_record = db.query(FileUpload).filter(FileUpload.id == file_id).first()
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Verify case access
    case = db.query(Case).filter(Case.id == file_record.case_id).first()
    if current_user.role == 'CLIENT' and case.client_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this file"
        )
    elif current_user.role != 'CLIENT' and case.office_id != current_user.office_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this file"
        )
    
    # Read file content from storage
    try:
        # Get file from storage using both s3_key and local_path
        s3_key = file_record.s3_key or file_record.file_path
        local_path = getattr(file_record, 'local_path', None) or file_record.file_path if not file_record.s3_key else None
        file_content = hybrid_storage.get_file(local_path, s3_key)
        
        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File content not found in storage"
            )
        
        # Decrypt if necessary
        if file_record.is_encrypted and file_record.encryption_key_id:
            from ..utils.file_utils import decrypt_file_content
            file_content = decrypt_file_content(file_content, file_record.encryption_key_id.encode())

        # Determine best-effort MIME type from decrypted content when stored MIME is generic
        actual_mime = file_record.mime_type
        if not actual_mime or actual_mime == 'application/octet-stream':
            try:
                if file_content:  # Additional safety check
                    detected = get_file_mime_type(file_content)
                    if detected:
                        actual_mime = detected
            except Exception:
                # fallback to stored mime_type if detection fails
                actual_mime = file_record.mime_type or 'application/octet-stream'

        # Generate display filename for view (with client prefix and converted extension)
        display_filename = file_record.original_filename
        if file_record.was_converted and file_record.original_filename.lower().endswith('.heic'):
            # Show converted extension for HEIC files, but keep the client prefix from stored_filename
            if file_record.stored_filename:
                # Use the stored filename which already includes client prefix, just change the extension
                base_name = os.path.splitext(file_record.stored_filename)[0]
                converted_ext = os.path.splitext(file_record.stored_filename)[1] if file_record.stored_filename else '.jpg'
                display_filename = f"{base_name}{converted_ext}"
            else:
                # Fallback to original filename if no stored filename
                base_name = os.path.splitext(file_record.original_filename)[0]
                display_filename = f"{base_name}.jpg"
        elif file_record.stored_filename:
            # Use stored filename which includes client prefix
            display_filename = file_record.stored_filename

        # Additional security headers for file viewing
        security_headers = {
            "Content-Type": actual_mime,
            "Content-Disposition": f"inline; filename={display_filename}",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:;"
        }

        # For PDFs, add additional headers
        if actual_mime == "application/pdf":
            security_headers["Content-Security-Policy"] += " object-src 'self';"

        # Log file view
        ip_address = get_client_ip_address(request)
        AuditLog.log_action(
            db,
            action="file_view",
            user_id=current_user.id,
            office_id=current_user.office_id,
            description=f"Viewed {file_record.original_filename} for case {file_record.case_id}",
            ip_address=ip_address,
            success=True,
            file_id=str(file_record.id),
            filename=file_record.original_filename,
            resource_type="file",
            resource_id=str(file_record.id)
        )
        db.commit()
        log_file_operation(
            "view",
            file_id=str(file_record.id),
            user_id=current_user.id,
            details=f"Viewed {file_record.original_filename} for case {file_record.case_id}",
            ip_address=ip_address
        )

        return Response(
            content=file_content,
            media_type=actual_mime,
            headers=security_headers
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read file: {str(e)}"
        )

@router.get("/download/{file_id}")
async def download_file(
    file_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download a file"""
    
    # Get file record
    file_record = db.query(FileUpload).filter(FileUpload.id == file_id).first()
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Verify case access
    case = db.query(Case).filter(Case.id == file_record.case_id).first()
    if current_user.role == 'CLIENT' and case.client_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this file"
        )
    elif current_user.role != 'CLIENT' and case.office_id != current_user.office_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this file"
        )
    
    # Update download tracking
    file_record.download_count += 1
    file_record.last_downloaded = datetime.utcnow()
    file_record.downloaded_by_id = current_user.id
    db.commit()
    
    # Try to use S3 presigned URL for direct download (more efficient)
    s3_key = file_record.s3_key or file_record.file_path
    local_path = getattr(file_record, 'local_path', None) or file_record.file_path if not file_record.s3_key else None
    
    logger.info(f"File download request for {file_id}:")
    logger.info(f"  - file_record.s3_key: {file_record.s3_key}")
    logger.info(f"  - file_record.file_path: {file_record.file_path}")
    logger.info(f"  - computed s3_key: {s3_key}")
    logger.info(f"  - computed local_path: {local_path}")
    
    # Download file content and serve directly (with decryption for encrypted files)
    try:
        logger.info(f"Serving file {file_id} directly through API with decryption")
        
        # Get encrypted file content from storage
        file_content = hybrid_storage.get_file(local_path, s3_key)
        
        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File content not found in storage"
            )
        
        # Decrypt if needed
        if file_record.encryption_key_id:
            from ..utils.file_utils import decrypt_file_content
            logger.info(f"Decrypting file {file_id} with encryption key")
            file_content = decrypt_file_content(
                file_content, 
                file_record.encryption_key_id.encode()
            )
            logger.info(f"File {file_id} decrypted successfully")
        
        # Generate display filename for download (with client prefix and converted extension)
        display_filename = file_record.original_filename
        if file_record.was_converted and file_record.original_filename.lower().endswith('.heic'):
            # Show converted extension for HEIC files, but keep the client prefix from stored_filename
            if file_record.stored_filename:
                # Use the stored filename which already includes client prefix, just change the extension
                base_name = os.path.splitext(file_record.stored_filename)[0]
                converted_ext = os.path.splitext(file_record.stored_filename)[1] if file_record.stored_filename else '.jpg'
                display_filename = f"{base_name}{converted_ext}"
            else:
                # Fallback to original filename if no stored filename
                base_name = os.path.splitext(file_record.original_filename)[0]
                display_filename = f"{base_name}.jpg"
        elif file_record.stored_filename:
            # Use stored filename which includes client prefix
            display_filename = file_record.stored_filename
        
        # Log file download
        ip_address = get_client_ip_address(request)
        AuditLog.log_action(
            db,
            action="file_download",
            user_id=current_user.id,
            office_id=current_user.office_id,
            description=f"Downloaded {file_record.original_filename} for case {file_record.case_id}",
            ip_address=ip_address,
            success=True,
            file_id=str(file_record.id),
            filename=file_record.original_filename,
            resource_type="file",
            resource_id=str(file_record.id)
        )
        db.commit()
        log_file_operation(
            "download",
            file_id=str(file_record.id),
            user_id=current_user.id,
            details=f"Downloaded {file_record.original_filename} for case {file_record.case_id}",
            ip_address=ip_address
        )
        
        # Return file content as response for download
        return Response(
            content=file_content,
            media_type=file_record.mime_type,
            headers={
                "Content-Type": file_record.mime_type,
                "Content-Disposition": f"attachment; filename={display_filename}"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read file: {str(e)}"
        )

@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a file from both database and storage"""
    
    logger.info(f"File deletion request: file_id={file_id} by user {current_user.id} ({current_user.role})")
    
    # Get file record
    file_record = db.query(FileUpload).filter(FileUpload.id == file_id).first()
    if not file_record:
        logger.warning(f"File not found: {file_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    logger.debug(f"File found: {file_record.original_filename}")
    
    # Verify case access
    case = db.query(Case).filter(Case.id == file_record.case_id).first()
    if current_user.role == 'CLIENT' and case.client_id != current_user.id:
        logger.warning(f"Access denied - client {current_user.id} trying to access other client's file {file_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this file"
        )
    elif current_user.role != 'CLIENT' and case.office_id != current_user.office_id:
        logger.warning(f"Access denied - user {current_user.id} trying to access other office's file {file_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this file"
        )
    
    # Delete file from S3 storage
    s3_key = file_record.s3_key or file_record.file_path
    local_path = getattr(file_record, 'local_path', None) or file_record.file_path if not file_record.s3_key else None
    logger.debug(f"Attempting to delete file from storage: s3_key={s3_key}, local_path={local_path}")
    
    try:
        storage_deleted = hybrid_storage.delete_file(local_path, s3_key)
        logger.info(f"File deletion from storage: {'success' if storage_deleted else 'failed'}")
    except Exception as e:
        logger.error(f"Error deleting file from storage: {str(e)}")
        # For S3-only storage, we should fail the deletion if S3 deletion fails
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file from storage: {str(e)}"
        )
    
    # Delete database record
    try:
        # Remove existing audit log entries referencing this file to avoid FK violations
        db.query(AuditLog).filter(AuditLog.file_id == str(file_record.id)).delete(synchronize_session=False)

        db.delete(file_record)
        logger.info(f"File record deleted from database: {file_id}")

        # Log successful file deletion without dangling FK reference
        ip_address = get_client_ip_address(request)

        AuditLog.log_action(
            db,
            action="file_deletion",
            user_id=current_user.id,
            office_id=current_user.office_id,
            description=f"Deleted {file_record.original_filename} for case {file_record.case_id} (storage_deleted: {storage_deleted})",
            ip_address=ip_address,
            success=True,
            resource_type="file",
            resource_id=str(file_record.id)
        )

        log_file_operation(
            "delete",
            file_id=str(file_record.id),
            user_id=current_user.id,
            details=f"Deleted {file_record.original_filename} for case {file_record.case_id} (storage_deleted: {storage_deleted})",
            ip_address=ip_address
        )

        db.commit()
    except Exception as e:
        logger.error(f"Error deleting file record from database: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file record: {str(e)}"
        )
    
    # Note: No local directory cleanup needed for S3-only storage
    
    return {
        "message": "File deleted successfully",
        "storage_deleted": storage_deleted,
        "filename": file_record.original_filename
    }

@router.get("/download-zip/{case_id}")
async def download_case_files_zip(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download all files for a case as a ZIP file"""
    
    # Verify case exists and user has access
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # Check access permissions
    if current_user.role == 'CLIENT' and case.client_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this case"
        )
    elif current_user.role != 'CLIENT' and case.office_id != current_user.office_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this case"
        )
    
    # Get all files for the case
    files = db.query(FileUpload).filter(
        FileUpload.case_id == case_id,
        FileUpload.status != FileStatus.DELETED
    ).all()
    
    if not files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No files found for this case"
        )
    
    try:
        # Create ZIP file
        zip_content = await create_files_zip(files, settings.upload_dir)
        
        # Get client info for filename
        case_client = db.query(User).filter(User.id == case.client_id).first()
        client_id = get_client_id_from_user(case_client) if case_client else "UNKNOWN"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"{client_id}_case_files_{timestamp}.zip"
        
        return Response(
            content=zip_content,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create ZIP file: {str(e)}"
        )

@router.get("/metadata/{file_id}")
async def get_file_metadata(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get file metadata for document viewer"""
    
    # Get file record
    file_record = db.query(FileUpload).filter(FileUpload.id == file_id).first()
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Verify case access
    case = db.query(Case).filter(Case.id == file_record.case_id).first()
    if current_user.role == 'CLIENT' and case.client_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this file"
        )
    elif current_user.role != 'CLIENT' and case.office_id != current_user.office_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this file"
        )
    
    return {
        "id": file_record.id,
        "original_filename": file_record.original_filename,
        "file_size": file_record.file_size,
        "file_size_formatted": file_record.file_size_formatted,
        "mime_type": file_record.mime_type,
        "file_extension": file_record.file_extension,
        "category": file_record.category.value,
        "description": file_record.description,
        "created_at": file_record.created_at,
        "is_image": file_record.is_image,
        "is_document": file_record.is_document,
        "view_url": f"/api/files/view/{file_id}",
        "download_url": f"/api/files/download/{file_id}"
    }

@router.get("/upload-requirements")
async def get_upload_requirements():
    """Get file upload requirements for frontend validation"""
    from ..utils.file_utils import get_upload_requirements
    return get_upload_requirements()
