# Database Migrations

This directory contains SQL migration scripts for the Artitec database schema.

## Running Migrations

Migrations should be applied manually to the database in numerical order.

### To apply a migration:

1. Connect to your MySQL database:
   ```bash
   mysql -h localhost -u Dev -p appdb
   ```

2. Run the migration script:
   ```bash
   source migrations/001_add_community_price_range.sql;
   ```

   Or from the command line:
   ```bash
   mysql -h localhost -u Dev -p appdb < migrations/001_add_community_price_range.sql
   ```

### Migration Naming Convention

Migrations follow the pattern: `{number}_{description}.sql`
- Number: 3-digit sequential number (001, 002, etc.)
- Description: Brief snake_case description of the changes

## Available Migrations

- **001_add_community_price_range.sql**: Adds `price_range_min` and `price_range_max` columns to the communities table to track home price ranges in communities.
