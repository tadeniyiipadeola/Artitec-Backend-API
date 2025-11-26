#!/usr/bin/env python3
"""
Backfill Missing Builder Data

This script creates builder discovery jobs for communities that don't have
any builders linked yet.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from config.db import get_db
from model.collection import CollectionJob
from datetime import datetime

def backfill_missing_builders(dry_run=True, priority=7):
    """
    Create builder discovery jobs for communities without builders.

    Args:
        dry_run: If True, only show what would be done without creating jobs
        priority: Priority for the created jobs (1-10, higher = more urgent)
    """

    # Create database session
    db = next(get_db())

    try:
        print("=" * 80)
        print("BACKFILL MISSING BUILDER DATA")
        print("=" * 80)
        print()

        if dry_run:
            print("🔍 DRY RUN MODE - No jobs will be created")
        else:
            print("⚠️  LIVE MODE - Jobs will be created")
        print()

        # Get communities without builders
        result = db.execute(text("""
            SELECT c.id, c.name, c.city, c.state, c.community_id
            FROM communities c
            LEFT JOIN builder_communities bc ON c.id = bc.community_id
            WHERE bc.community_id IS NULL
            ORDER BY c.name
        """))

        communities_without_builders = result.fetchall()

        if not communities_without_builders:
            print("✅ All communities already have builders linked!")
            print("   No backfill needed.")
            return

        print(f"Found {len(communities_without_builders)} communities without builders:")
        print()

        jobs_to_create = []

        for i, row in enumerate(communities_without_builders, 1):
            location = f"{row.city}, {row.state}" if row.city and row.state else None

            print(f"{i:2d}. {row.name:40s} | {location or 'No location':30s} | ID: {row.id}")

            # Prepare job data
            search_query = f"{row.name} builders"
            if location:
                search_query += f" {location}"

            job_data = {
                'community_id': row.id,
                'community_name': row.name,
                'search_query': search_query,
                'location': location,
                'priority': priority
            }

            jobs_to_create.append(job_data)

        print()
        print("=" * 80)

        if dry_run:
            print("DRY RUN SUMMARY")
            print("=" * 80)
            print()
            print(f"Would create {len(jobs_to_create)} builder discovery jobs with priority {priority}")
            print()
            print("Example job:")
            if jobs_to_create:
                example = jobs_to_create[0]
                print(f"  Community: {example['community_name']}")
                print(f"  Search Query: {example['search_query']}")
                print(f"  Location: {example.get('location', 'N/A')}")
                print(f"  Priority: {example['priority']}")
            print()
            print("To create these jobs, run with --execute flag")
        else:
            print("CREATING JOBS")
            print("=" * 80)
            print()

            created_count = 0

            for job_data in jobs_to_create:
                try:
                    # Create builder discovery job
                    job = CollectionJob(
                        entity_type='builder',
                        entity_id=None,
                        job_type='discovery',
                        parent_entity_type='community',
                        parent_entity_id=job_data['community_id'],
                        status='pending',
                        priority=job_data['priority'],
                        search_query=job_data['search_query'],
                        search_filters={
                            'community_id': job_data['community_id'],
                            'community_name': job_data['community_name'],
                            'location': job_data.get('location')
                        },
                        initiated_by='system_backfill'
                    )

                    db.add(job)
                    created_count += 1

                    print(f"✅ Created job for: {job_data['community_name']}")

                except Exception as e:
                    print(f"❌ Failed to create job for {job_data['community_name']}: {e}")

            # Commit all jobs
            db.commit()

            print()
            print("=" * 80)
            print("BACKFILL COMPLETE")
            print("=" * 80)
            print()
            print(f"✅ Created {created_count} builder discovery jobs")
            print(f"   Priority: {priority}")
            print(f"   Status: pending (ready to be processed)")
            print()
            print("Next steps:")
            print("1. Monitor job execution in the admin dashboard")
            print("2. Review and approve discovered builders")
            print("3. Run coverage analysis again to verify improvement")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Backfill missing builder data for communities')
    parser.add_argument('--execute', action='store_true',
                       help='Actually create jobs (default is dry-run)')
    parser.add_argument('--priority', type=int, default=7,
                       help='Priority for created jobs (1-10, default: 7)')

    args = parser.parse_args()

    dry_run = not args.execute

    try:
        backfill_missing_builders(dry_run=dry_run, priority=args.priority)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
