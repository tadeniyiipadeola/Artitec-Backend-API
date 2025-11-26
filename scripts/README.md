# Data Collection Scripts

This directory contains utility scripts for managing and analyzing the data collection system.

## Available Scripts

### 1. analyze_community_builder_coverage.py

**Purpose:** Analyze how many communities have builders linked in the database.

**Usage:**
```bash
python scripts/analyze_community_builder_coverage.py
```

**Output:**
- Total communities count
- Communities WITH builders count and percentage
- Communities WITHOUT builders count and percentage
- Total builder-community associations
- Average builders per community
- List of communities missing builder data (up to 20)
- Actionable recommendations

**Example Output:**
```
📊 Total Communities: 35
✅ Communities WITH Builders: 27 (77.1% coverage)
❌ Communities WITHOUT Builders: 8 (22.9% gap)
🔗 Total Builder-Community Links: 179
📊 Average Builders per Community: 6.63
```

**When to Run:**
- Before running backfill operations
- After major data collection campaigns
- As part of regular data quality monitoring
- When investigating data completeness issues

---

### 2. backfill_missing_builders.py

**Purpose:** Create builder discovery jobs for communities that don't have any builders linked.

**Usage:**

**Dry Run (recommended first):**
```bash
python scripts/backfill_missing_builders.py
```

**Execute (actually create jobs):**
```bash
python scripts/backfill_missing_builders.py --execute
```

**Custom Priority:**
```bash
python scripts/backfill_missing_builders.py --execute --priority 8
```

**Options:**
- `--execute`: Actually create the jobs (default is dry-run mode)
- `--priority N`: Set job priority (1-10, default: 7)

**What It Does:**
1. Identifies communities without any builders
2. Creates builder discovery jobs for each community
3. Sets appropriate search queries and filters
4. Links jobs to parent communities
5. Marks jobs with `initiated_by='system_backfill'`

**Example Output:**
```
Found 8 communities without builders:
 1. Lakes of Rosehill | Tomball, TX        | ID: 37
 2. Legacy            | League City, TX    | ID: 16
 ...

✅ Created 8 builder discovery jobs
   Priority: 7
   Status: pending (ready to be processed)
```

**When to Run:**
- After running coverage analysis and identifying gaps
- When onboarding new communities
- As part of regular data maintenance
- After importing communities from external sources

---

## Workflow Recommendations

### Regular Data Quality Monitoring

**Weekly:**
1. Run coverage analysis to check current state
2. If coverage drops below 80%, run backfill script
3. Monitor job execution in admin dashboard
4. Review and approve discovered entities

**After Community Discovery:**
1. Run coverage analysis to identify new communities without builders
2. Run backfill script to create discovery jobs
3. Prioritize jobs for master-planned communities (use higher priority)

### Best Practices

1. **Always run dry-run first:** Use backfill script without `--execute` to preview changes
2. **Set appropriate priorities:**
   - 8-10: Urgent/master-planned communities
   - 5-7: Normal priority
   - 1-4: Low priority/HOA-only communities
3. **Monitor job execution:** Check admin dashboard after running backfill
4. **Review approvals:** Carefully review auto-discovered builders before approving
5. **Re-run analysis:** After jobs complete, run coverage analysis to verify improvement

### Automation Ideas

Consider scheduling these scripts:

**Coverage Monitoring:**
```bash
# Run every Sunday at midnight
0 0 * * 0 cd /path/to/project && python scripts/analyze_community_builder_coverage.py > /var/log/coverage_$(date +\%Y\%m\%d).log
```

**Auto-Backfill:**
```bash
# Run backfill for communities missing builders (if you trust auto-discovery)
# Use with caution - review jobs manually first!
0 2 * * 1 cd /path/to/project && python scripts/backfill_missing_builders.py --execute --priority 6
```

---

## Troubleshooting

### Coverage Analysis Fails
**Issue:** Script fails with database connection error
**Solution:**
- Verify `config.db.get_db()` is properly configured
- Check database credentials
- Ensure virtual environment is activated

### Backfill Creates Duplicate Jobs
**Issue:** Running backfill multiple times creates duplicate jobs
**Solution:**
- Jobs are only created for communities WITHOUT builders
- Once builders are discovered and approved, communities won't appear again
- Use dry-run mode to verify before executing

### Jobs Not Executing
**Issue:** Backfill jobs stay in pending state
**Solution:**
- Jobs need to be started manually via admin dashboard or API
- Check job executor is running
- Verify job priority isn't too low

---

## Related Documentation

- [Data Collection System](../docs/collection-system.md)
- [Duplicate Detection](../src/collection/duplicate_detection.py)
- [Admin Collection API](../routes/admin/collection.py)
- [Collection Jobs Model](../model/collection.py)

---

## Support

For issues or questions:
1. Check the main project README
2. Review collection system logs
3. Inspect failed job logs in admin dashboard
4. Check database for data integrity
