from config.db import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    print('=== Foreign Key Relationships Using Numeric community_id ===\n')
    
    tables = [
        'community_awards',
        'community_builder_cards', 
        'community_amenities',
        'community_admins',
        'community_events',
        'community_threads',
        'community_phases'
    ]
    
    for table in tables:
        result = db.execute(text(f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = '{table}'
            AND column_name IN ('community_id', 'id')
            ORDER BY ordinal_position
        """))
        cols = result.fetchall()
        
        if cols:
            print(f'{table}:')
            for col in cols:
                print(f'  {col[0]:20} {col[1]:20}')
            
            # Check if there's data
            result = db.execute(text(f'SELECT COUNT(*) FROM {table}'))
            count = result.scalar()
            print(f'  Records: {count}')
            print()
        
finally:
    db.close()
