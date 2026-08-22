import os
import sys
import glob
import subprocess
from datetime import datetime
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load workspace env variables
load_dotenv()

def main():
    # Find pg_dump in standard PostgreSQL locations
    pg_dump_path = None
    search_pattern = r"C:\Program Files\PostgreSQL\*\bin\pg_dump.exe"
    found_paths = glob.glob(search_pattern)
    if found_paths:
        pg_dump_path = found_paths[0]
        print(f"Using pg_dump at: {pg_dump_path}")
    else:
        pg_dump_path = "pg_dump"
        print("pg_dump.exe not found in Program Files. Falling back to system 'pg_dump'...")

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL not found in .env file.")
        sys.exit(1)

    # Parse connection string
    try:
        parsed = urlparse(db_url)
        db_user = parsed.username or "postgres"
        db_pass = parsed.password or ""
        db_host = parsed.hostname or "localhost"
        db_port = str(parsed.port or 5432)
        db_name = parsed.path.lstrip("/")
    except Exception as e:
        print(f"Error parsing DATABASE_URL: {e}")
        sys.exit(1)

    # Create backup directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backup_dir = os.path.join(script_dir, "backups")
    os.makedirs(backup_dir, exist_ok=True)

    # Output file settings (use PostgreSQL custom compressed binary format, recommended for binary/blob column 'file_data')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"cv_platform_backup_{timestamp}.dump"
    backup_filepath = os.path.join(backup_dir, backup_filename)

    print(f"\nStarting backup of database '{db_name}'...")
    print(f"  Host: {db_host}:{db_port}")
    print(f"  User: {db_user}")
    print(f"  Target File: {backup_filepath}")

    # Set password environment variable for password-less pg_dump execution
    env = os.environ.copy()
    if db_pass:
        env["PGPASSWORD"] = db_pass

    cmd = [
        pg_dump_path,
        "-h", db_host,
        "-p", db_port,
        "-U", db_user,
        "-F", "c",          # Custom binary compressed format (restorable via pg_restore)
        "-b",                # Include large objects
        "-v",                # Verbose logging
        "-f", backup_filepath,
        db_name
    ]

    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
        print("\nBackup completed successfully!")
        print(f"Saved to: backups/{backup_filename}")
        print(f"File size: {os.path.getsize(backup_filepath):,} bytes")
    except subprocess.CalledProcessError as e:
        print(f"\npg_dump failed with exit code {e.returncode}:")
        print(e.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
