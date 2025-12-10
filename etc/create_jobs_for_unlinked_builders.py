"""
Create collection jobs for unlinked builder cards

This script:
1. Finds all builder cards without builder_profile_id
2. Groups them by unique builder name
3. Creates collection jobs for each unique builder
4. Jobs will auto-link to their cards when approved via the existing metadata system
"""
import pymysql
import os
import sys
from dotenv import load_dotenv
from datetime import datetime
import json
import time
import random
import string

# Load environment variables
load_dotenv()

# Check for --yes flag
auto_confirm = "--yes" in sys.argv or "-y" in sys.argv

# Parse DB URL
db_url = os.getenv("DB_URL")
parts = db_url.replace("mysql+pymysql://", "").split("@")
user_pass = parts[0].split(":")
user = user_pass[0]
password = user_pass[1]
host_port_db = parts[1].split("/")
host_port = host_port_db[0].split(":")
host = host_port[0]
port = int(host_port[1])
database = host_port_db[1]

print("=" * 80)
print("CREATE COLLECTION JOBS FOR UNLINKED BUILDERS")
print("=" * 80)
print(f"\nConnecting to database: {host}:{port}/{database}")

connection = pymysql.connect(
    host=host,
    port=port,
    user=user,
    password=password,
    database=database,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

try:
    with connection.cursor() as cursor:
        # Get all unlinked builder cards
        print("\n" + "=" * 80)
        print("STEP 1: Fetching unlinked builder cards")
        print("=" * 80)

        cursor.execute("""
            SELECT
                id,
                name,
                community_id,
                subtitle,
                icon,
                followers,
                is_verified
            FROM community_builders
            WHERE builder_profile_id IS NULL
            ORDER BY name, community_id
        """)

        unlinked_cards = cursor.fetchall()
        print(f"\nFound {len(unlinked_cards)} unlinked builder cards")

        if not unlinked_cards:
            print("\n✓ All builder cards are already linked!")
            exit(0)

        # Group by unique builder name
        print("\n" + "=" * 80)
        print("STEP 2: Grouping by unique builder names")
        print("=" * 80)

        builders_map = {}  # name -> list of card IDs
        for card in unlinked_cards:
            name = card['name']
            if name not in builders_map:
                builders_map[name] = {
                    'name': name,
                    'card_ids': [],
                    'communities': set(),
                    'sample_card': card
                }
            builders_map[name]['card_ids'].append(card['id'])
            builders_map[name]['communities'].add(card['community_id'])

        print(f"\nFound {len(builders_map)} unique builder names:")
        for idx, (name, data) in enumerate(sorted(builders_map.items(), key=lambda x: len(x[1]['card_ids']), reverse=True), 1):
            print(f"  {idx}. {name}: {len(data['card_ids'])} card(s) across {len(data['communities'])} community/communities")

        # Check for existing jobs for these builders
        print("\n" + "=" * 80)
        print("STEP 3: Checking for existing collection jobs")
        print("=" * 80)

        builder_names = list(builders_map.keys())
        if builder_names:
            # Create placeholders for the IN clause
            placeholders = ','.join(['%s'] * len(builder_names))
            cursor.execute(f"""
                SELECT
                    id,
                    search_filters,
                    status
                FROM collection_jobs
                WHERE entity_type = 'builder'
                AND JSON_UNQUOTE(JSON_EXTRACT(search_filters, '$.builder_name')) IN ({placeholders})
            """, builder_names)

            existing_jobs = cursor.fetchall()

            # Map existing jobs to builder names
            existing_builders = {}
            for job in existing_jobs:
                filters = json.loads(job['search_filters']) if job['search_filters'] else {}
                builder_name = filters.get('builder_name')
                if builder_name:
                    if builder_name not in existing_builders:
                        existing_builders[builder_name] = []
                    existing_builders[builder_name].append(job)

            if existing_builders:
                print(f"\nFound {len(existing_builders)} builders with existing jobs:")
                for name, jobs in existing_builders.items():
                    statuses = [j['status'] for j in jobs]
                    print(f"  - {name}: {len(jobs)} job(s) ({', '.join(statuses)})")

                # Remove builders that already have pending or in_progress jobs
                for name in list(builders_map.keys()):
                    if name in existing_builders:
                        jobs = existing_builders[name]
                        active_jobs = [j for j in jobs if j['status'] in ('pending', 'in_progress')]
                        if active_jobs:
                            print(f"\n⚠️  Skipping '{name}' - has {len(active_jobs)} active job(s)")
                            del builders_map[name]
            else:
                print("\n✓ No existing jobs found")

        if not builders_map:
            print("\n✓ All unlinked builders already have active collection jobs!")
            exit(0)

        # Create jobs
        print("\n" + "=" * 80)
        print("STEP 4: Creating collection jobs")
        print("=" * 80)
        print(f"\nWill create {len(builders_map)} collection job(s)")

        # Show summary
        print("\nJobs to create:")
        for idx, (name, data) in enumerate(sorted(builders_map.items()), 1):
            card_count = len(data['card_ids'])
            print(f"  {idx}. {name} ({card_count} card{'s' if card_count > 1 else ''} will auto-link)")

        # Ask for confirmation
        if auto_confirm:
            print(f"\nAuto-confirming creation of {len(builders_map)} jobs (--yes flag provided)")
            response = 'yes'
        else:
            response = input(f"\nCreate {len(builders_map)} collection jobs? (yes/no): ").strip().lower()

        if response != 'yes':
            print("\n✗ Job creation cancelled")
            exit(0)

        # Create the jobs
        created_jobs = []
        for name, data in builders_map.items():
            sample_card = data['sample_card']
            card_ids = data['card_ids']

            # Create search filters with builder name and card IDs for auto-linking
            search_filters = {
                'builder_name': name,
                'community_builder_card_ids': card_ids,  # Multiple cards will all link to same profile
                'source': 'unlinked_cards_script'
            }

            # Generate unique job_id
            timestamp = str(int(time.time()))
            random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            job_id_str = f"JOB-{timestamp}-{random_suffix}"

            # Insert collection job
            cursor.execute("""
                INSERT INTO collection_jobs (
                    job_id,
                    entity_type,
                    job_type,
                    search_filters,
                    status,
                    priority,
                    created_at
                )
                VALUES (
                    %s,
                    'builder',
                    'discovery',
                    %s,
                    'pending',
                    5,
                    NOW()
                )
            """, (job_id_str, json.dumps(search_filters)))

            created_jobs.append({
                'job_id': job_id_str,
                'builder_name': name,
                'card_count': len(card_ids)
            })

            print(f"  ✓ Created job {job_id_str} for '{name}' ({len(card_ids)} card{'s' if len(card_ids) > 1 else ''})")

        connection.commit()

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"\n✓ Successfully created {len(created_jobs)} collection jobs")

        total_cards = sum(job['card_count'] for job in created_jobs)
        print(f"\nWhen these jobs are collected and approved:")
        print(f"  - {len(created_jobs)} builder profiles will be created")
        print(f"  - {total_cards} builder cards will be automatically linked")

        print("\nNext steps:")
        print("  1. Run the builder collector to gather data for these jobs")
        print("  2. Review and approve the builders in the admin panel")
        print("  3. Upon approval, all matching cards will auto-link via builder_profile_id")

        print("\nJobs created:")
        for job in created_jobs:
            print(f"  - Job {job['job_id']}: {job['builder_name']} → {job['card_count']} card(s)")

finally:
    connection.close()
    print("\n✓ Database connection closed")
