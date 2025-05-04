# migrate_db.py
import argparse
import os
import shutil
import sqlite3
import sys


def migrate_database_schema(db_path="repo_files.db"):
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist. Nothing to migrate.")
        return 0

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(file_system_entries)")
        columns = [col[1] for col in cursor.fetchall()]

        if "content_status" in columns:
            print("content_status column already exists. No migration needed.")
            return 0

        print(f"Migrating database {db_path} to add content_status column...")

        backup_path = f"{db_path}.backup"
        conn.close()

        shutil.copy2(db_path, backup_path)
        print(f"Database backed up to {backup_path}")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("ALTER TABLE file_system_entries ADD COLUMN content_status TEXT DEFAULT 'NONE'")

        conn.commit()
        print("Migration completed successfully.")
        return 0

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()

        if os.path.exists(backup_path):
            conn.close()

            os.remove(db_path)
            os.rename(backup_path, db_path)
            print("Restored from backup due to error.")

        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate the repository database schema")
    parser.add_argument("--db-path", default="repo_files.db", help="Path to the database file (default: repo_files.db)")

    args = parser.parse_args()
    sys.exit(migrate_database_schema(args.db_path))
