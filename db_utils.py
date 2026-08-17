import sqlite3
import os
from flask import current_app
from sqlalchemy import inspect
from app import db

def check_and_update_schema(app):
    """
    Checks database schema against models and adds missing columns.
    This works for SQLite to prevent 'no such column' errors.
    """
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Get all table names from models
        # This is a simplified approach assuming models match table names
        # For a production app, Flask-Migrate is recommended
        
        # List of models to check
        # We need to import classes inside the function to avoid circular imports if they were top-level
        from app import User, Donation, Notification, DonorRating
        
        models = [
            ('user', User),
            ('donation', Donation),
            ('notification', Notification),
            ('donor_rating', DonorRating)
        ]
        
        db_path = os.path.join(app.instance_path, 'foodshare.db')
        
        print(f"[*] Checking database schema at {db_path}...")
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            for table_name, model_class in models:
                if not inspector.has_table(table_name):
                    continue
                    
                # Get existing columns in DB
                cursor.execute(f"PRAGMA table_info({table_name})")
                existing_cols = {row[1] for row in cursor.fetchall()}
                
                # Get defined columns in Model
                mapper = inspect(model_class)
                for column_prop in mapper.attrs:
                    if hasattr(column_prop, 'columns'):
                        column = column_prop.columns[0]
                        col_name = column.name
                        
                        if col_name not in existing_cols:
                            # Found missing column!
                            col_type = str(column.type)
                            
                            # Map SQLAlchemy types to SQLite types roughly
                            if 'VARCHAR' in col_type or 'String' in col_type or 'Text' in col_type:
                                sql_type = 'TEXT'
                            elif 'Integer' in col_type:
                                sql_type = 'INTEGER'
                            elif 'Boolean' in col_type:
                                sql_type = 'BOOLEAN'
                            elif 'DateTime' in col_type:
                                sql_type = 'DATETIME'
                            else:
                                sql_type = 'TEXT' # Fallback
                                
                            print(f"[+] Adding missing column '{col_name}' to table '{table_name}'...")
                            
                            # Add default value logic if needed, simplify for now
                            try:
                                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {sql_type}")
                                print(f"    v Success.")
                            except Exception as e:
                                print(f"    x Failed: {e}")
            
            conn.commit()
            conn.close()
            print("[*] Schema check complete.")
            
        except Exception as e:
            print(f"[!] Schema check failed: {e}")
