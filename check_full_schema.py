from config.db import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    print('=== Full Schema Check for Community Relations ===\n')

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
        print(f'\n{table}:')
        print('-' * 80)

        # Get all columns
        result = db.execute(text(f"""
            SELECT column_name, data_type, column_type, is_nullable, column_key, extra
            FROM information_schema.columns
            WHERE table_name = '{table}'
            AND table_schema = DATABASE()
            ORDER BY ordinal_position
        """))
        cols = result.fetchall()

        if cols:
            for col in cols:
                nullable = 'NULL' if col[3] == 'YES' else 'NOT NULL'
                key = f'[{col[4]}]' if col[4] else ''
                extra = f'({col[5]})' if col[5] else ''
                print(f'  {col[0]:25} {col[2]:20} {nullable:10} {key} {extra}')

        # Get indexes
        result = db.execute(text(f"""
            SELECT DISTINCT index_name, column_name
            FROM information_schema.statistics
            WHERE table_name = '{table}'
            AND table_schema = DATABASE()
            ORDER BY index_name, column_name
        """))
        indexes = result.fetchall()

        if indexes:
            print(f'\n  Indexes:')
            for idx in indexes:
                print(f'    {idx[0]:40} -> {idx[1]}')

        # Get foreign keys
        result = db.execute(text(f"""
            SELECT
                constraint_name,
                column_name,
                referenced_table_name,
                referenced_column_name
            FROM information_schema.key_column_usage
            WHERE table_name = '{table}'
            AND table_schema = DATABASE()
            AND referenced_table_name IS NOT NULL
        """))
        fks = result.fetchall()

        if fks:
            print(f'\n  Foreign Keys:')
            for fk in fks:
                print(f'    {fk[0]:40} {fk[1]} -> {fk[2]}.{fk[3]}')

finally:
    db.close()
