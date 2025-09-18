#!/usr/bin/env python3
"""
Initialize the CA Tadley Debt Advice Tool database
Creates default office and admin user for testing
"""
import sys
import os
from sqlalchemy.orm import Session

# Add src to path to import models
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.config.database import engine, SessionLocal
from src.models import Office, User, UserRole, UserStatus, create_tables, Notification, NotificationType
from src.utils.auth import hash_password

def init_database():
    """Initialize database with default data"""
    
    print("🚀 Initializing CA Tadley Debt Advice Tool Database...")
    
    # Create tables
    create_tables()
    print("✅ Database tables created")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Check if default office exists
        default_office = db.query(Office).filter(Office.code == "CAT").first()
        
        if not default_office:
            # Create Citizens Advice Tadley office
            default_office = Office(
                name="Citizens Advice Tadley",
                code="CAT",
                contact_email="admin@catadley.com",
                contact_phone="0118 981 7567",
                address="Citizens Advice Tadley\nTurbary Building\nFranklin Avenue\nTadley\nRG26 4ET",
                is_active=True,
                privacy_statement_url="https://citizensadvicetadley.org.uk/privacy",
                terms_url="https://citizensadvicetadley.org.uk/terms"
            )
            db.add(default_office)
            db.commit()
            db.refresh(default_office)
            print(f"✅ Created default office: {default_office.name} ({default_office.code})")
        else:
            print(f"ℹ️  Default office already exists: {default_office.name}")
        
        # Check if admin user exists
        admin_user = db.query(User).filter(
            User.email == "admin@catadley.com"
        ).first()
        
        if not admin_user:
            # Create default superuser
            admin_user = User(
                email="admin@catadley.com",
                password_hash=hash_password("TadleyAdmin2024!"),  # Change in production!
                first_name="System",
                last_name="Administrator",
                role=UserRole.SUPERUSER,
                status=UserStatus.ACTIVE,
                office_id=default_office.id,
                is_2fa_enabled=False
            )
            db.add(admin_user)
            db.commit()
            print("✅ Created default admin user:")
            print("   📧 Email: admin@catadley.com")
            print("   🔐 Password: TadleyAdmin2024!")
            print("   ⚠️  CHANGE THIS PASSWORD IN PRODUCTION!")
        else:
            print("ℹ️  Admin user already exists")
        
        # Create a test adviser user
        adviser_user = db.query(User).filter(
            User.email == "adviser@citizensadvicetadley.org.uk"
        ).first()
        
        if not adviser_user:
            adviser_user = User(
                email="adviser@citizensadvicetadley.org.uk",
                password_hash=hash_password("TadleyAdviser2024!"),
                first_name="Test",
                last_name="Adviser",
                role=UserRole.ADVISER,
                status=UserStatus.ACTIVE,
                office_id=default_office.id,
                is_2fa_enabled=False
            )
            db.add(adviser_user)
            db.commit()
            print("✅ Created test adviser user:")
            print("   📧 Email: adviser@citizensadvicetadley.org.uk")
            print("   🔐 Password: TadleyAdviser2024!")
        else:
            print("ℹ️  Adviser user already exists")
        
        print("\n🎉 Database initialization complete!")
        print("\n📋 Summary:")
        print(f"   🏢 Office: {default_office.name} ({default_office.code})")
        print(f"   👥 Users created: Admin, Adviser")
        print(f"   🔒 Security: Invitation-only registration enabled")
        print(f"   🌐 API: http://localhost:8000")
        print(f"   📚 Docs: http://localhost:8000/api/docs")
        
        print("\n⚠️  IMPORTANT SECURITY NOTES:")
        print("   - Change default passwords immediately in production")
        print("   - Configure proper SMTP settings for email notifications")
        print("   - Set up SSL/TLS certificates for production deployment")
        print("   - Review and update security settings in settings.py")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        db.rollback()
        raise
    
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
