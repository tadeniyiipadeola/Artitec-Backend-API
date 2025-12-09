import asyncio
import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from db.database import get_db

async def check_awards():
    async for db in get_db():
        # Check table structure
        print('=== Community Awards Table Structure ===')
        result = await db.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'community_awards'
            ORDER BY ordinal_position
        """))
        columns = result.fetchall()
        
        for col in columns:
            print(f'{col[0]:20} {col[1]:20} nullable={col[2]:5} default={col[3]}')
        
        print('\n=== Sample Community Awards Data ===')
        result = await db.execute(text("""
            SELECT ca.*, c.name as community_name
            FROM community_awards ca
            JOIN communities c ON ca.community_id = c.id
            ORDER BY ca.created_at DESC
            LIMIT 10
        """))
        awards = result.fetchall()
        
        if awards:
            for award in awards:
                print(f'\nID: {award.id}')
                print(f'Community: {award.community_name} (ID: {award.community_id})')
                print(f'Title: {award.title}')
                print(f'Year: {award.year}')
                print(f'Issuer: {award.issuer}')
                print(f'Icon: {award.icon}')
                print(f'Note: {award.note}')
        else:
            print('No awards found in database')
        
        print(f'\n=== Total Awards Count ===')
        result = await db.execute(text('SELECT COUNT(*) FROM community_awards'))
        count = result.scalar()
        print(f'Total awards: {count}')
        
        print(f'\n=== Awards by Community ===')
        result = await db.execute(text("""
            SELECT c.name, c.community_id, COUNT(ca.id) as award_count
            FROM communities c
            LEFT JOIN community_awards ca ON c.id = ca.community_id
            GROUP BY c.id, c.name, c.community_id
            HAVING COUNT(ca.id) > 0
            ORDER BY award_count DESC
            LIMIT 10
        """))
        counts = result.fetchall()
        
        for row in counts:
            print(f'{row[0]:30} ({row[1]}): {row[2]} awards')
        
        break

asyncio.run(check_awards())
