-- Connect to the PostgreSQL server using a superuser role
-- psql -h localhost -U odeine -d postgres

-- Drop all tables, sequences, views, types, and other objects
DO $$ DECLARE
    r RECORD;
BEGIN
    -- Drop all tables
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema()) LOOP
        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;

    -- Drop all sequences
    FOR r IN (SELECT sequencename FROM pg_sequences WHERE schemaname = current_schema()) LOOP
        EXECUTE 'DROP SEQUENCE IF EXISTS ' || quote_ident(r.sequencename) || ' CASCADE';
    END LOOP;

    -- Drop all views
    FOR r IN (SELECT viewname FROM pg_views WHERE schemaname = current_schema()) LOOP
        EXECUTE 'DROP VIEW IF EXISTS ' || quote_ident(r.viewname) || ' CASCADE';
    END LOOP;

    -- Drop all types
    FOR r IN (SELECT typname FROM pg_type WHERE typnamespace = 'public'::regnamespace) LOOP
        EXECUTE 'DROP TYPE IF EXISTS ' || quote_ident(r.typname) || ' CASCADE';
    END LOOP;

    -- Drop all other objects
    FOR r IN (SELECT oid::regclass::text FROM pg_class WHERE relkind IN ('r', 'S', 'v') AND relnamespace = 'public'::regnamespace) LOOP
        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.oid::regclass::text) || ' CASCADE';
    END LOOP;
END $$;

-- Optionally, drop the database itself
-- DROP DATABASE your_database_name;