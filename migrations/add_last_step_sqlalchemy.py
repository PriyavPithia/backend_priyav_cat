from sqlalchemy import create_engine, Column, Integer, MetaData, Table, text
import os

def migrate():
    """Add last_step column to cases table using SQLAlchemy"""
    
    # Get the database path
    db_path = os.path.join(os.path.dirname(__file__), '..', 'ca_tadley_debt_tool.db')
    
    # Create engine
    engine = create_engine(f'sqlite:///{db_path}')
    
    # Create MetaData instance
    metadata = MetaData()
    
    try:
        # Reflect existing table
        cases = Table('cases', metadata, autoload_with=engine)
        
        # Check if column exists
        if 'last_step' not in cases.columns:
            # Add column using raw SQL with proper connection handling
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE cases ADD COLUMN last_step INTEGER'))
                conn.commit()
            print("✅ Added last_step column to cases table")
        else:
            print("ℹ️  last_step column already exists")
            
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        raise

if __name__ == "__main__":
    migrate()