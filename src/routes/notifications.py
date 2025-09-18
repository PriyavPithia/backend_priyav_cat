from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..config.database import get_db
from ..models import User, Notification, NotificationType, Case
from .auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])

# Pydantic models for request/response
class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    message: str
    case_id: Optional[str] = None
    data: Optional[dict] = None
    read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class MarkAsReadRequest(BaseModel):
    notification_id: str

class CreateNotificationRequest(BaseModel):
    user_id: str
    type: str
    title: str
    message: str
    case_id: Optional[str] = None
    data: Optional[dict] = None

@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    unread_only: bool = False
):
    """Get notifications for the current user with role-based filtering"""
    
    # Base query for user's notifications
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    # Filter by read status if requested
    if unread_only:
        query = query.filter(Notification.read == False)
    
    # Role-based filtering
    if current_user.is_client:
        # Clients only see case_closed and case_updated notifications
        query = query.filter(
            Notification.type.in_([
                NotificationType.CASE_CLOSED,
                NotificationType.CASE_UPDATED
            ])
        )
    # Note: Advisers and admins currently don't receive notifications
    # This was implemented per user request to only show notifications to clients
    # If you want advisers/admins to see notifications, uncomment and modify below:
    # else:
    #     query = query.filter(
    #         Notification.type.in_([
    #             NotificationType.CASE_ASSIGNED,
    #             NotificationType.MENTION,
    #             NotificationType.SYSTEM
    #         ])
    #     )
    
    # Order by creation date (newest first)
    notifications = query.order_by(Notification.created_at.desc()).all()
    
    return notifications

@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get count of unread notifications for the current user"""
    
    # Base query for user's unread notifications
    query = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.read == False
    )
    
    # Role-based filtering
    if current_user.is_client:
        # Clients only see case_closed and case_updated notifications
        query = query.filter(
            Notification.type.in_([
                NotificationType.CASE_CLOSED,
                NotificationType.CASE_UPDATED
            ])
        )
    # Note: Advisers and admins currently don't receive notifications
    # This was implemented per user request to only show notifications to clients
    
    count = query.count()
    return {"unread_count": count}

@router.post("/mark-as-read")
async def mark_notification_as_read(
    request: MarkAsReadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a notification as read"""
    
    notification = db.query(Notification).filter(
        Notification.id == request.notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification.read = True
    notification.read_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Notification marked as read"}

@router.post("/mark-all-as-read")
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read for the current user"""
    
    # Get unread notifications for the user
    query = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.read == False
    )
    
    # Apply role-based filtering
    if current_user.is_client:
        query = query.filter(
            Notification.type.in_([
                NotificationType.CASE_CLOSED,
                NotificationType.CASE_UPDATED
            ])
        )
    else:
        query = query.filter(
            Notification.type.in_([
                NotificationType.CASE_ASSIGNED,
                NotificationType.MENTION,
                NotificationType.SYSTEM
            ])
        )
    
    unread_notifications = query.all()
    
    # Mark all as read
    for notification in unread_notifications:
        notification.read = True
        notification.read_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": f"Marked {len(unread_notifications)} notifications as read"}

@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a notification"""
    
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    db.delete(notification)
    db.commit()
    
    return {"message": "Notification deleted"}

@router.delete("/")
async def clear_all_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clear all notifications for the current user"""
    
    # Get all notifications for the user
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    # Apply role-based filtering
    if current_user.is_client:
        query = query.filter(
            Notification.type.in_([
                NotificationType.CASE_CLOSED,
                NotificationType.CASE_UPDATED
            ])
        )
    else:
        query = query.filter(
            Notification.type.in_([
                NotificationType.CASE_ASSIGNED,
                NotificationType.MENTION,
                NotificationType.SYSTEM
            ])
        )
    
    notifications = query.all()
    
    # Delete all notifications
    for notification in notifications:
        db.delete(notification)
    
    db.commit()
    
    return {"message": f"Cleared {len(notifications)} notifications"}

# Internal function to create notifications (used by other parts of the system)
def create_notification(
    db: Session,
    user_id: str,
    notification_type: NotificationType,
    title: str,
    message: str,
    case_id: Optional[str] = None,
    data: Optional[dict] = None
) -> Notification:
    """Create a new notification"""
    
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        case_id=case_id,
        data=data
    )
    
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    return notification
