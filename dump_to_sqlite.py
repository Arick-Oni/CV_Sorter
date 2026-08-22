import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load environment
load_dotenv()

# Import models to register them on Base.metadata
from backend.models import Base, Project, CV, MatchHistory

# Define projects to exclude from the Render SQLite database
EXCLUDED_PROJECTS = {"TEST", "DN", "CodeSprint2026"}

def main():
    pg_url = os.getenv("DATABASE_URL")
    if not pg_url or not pg_url.startswith("postgresql"):
        print("Error: DATABASE_URL in .env is not set to a postgresql connection string.")
        return

    print(f"Connecting to source PostgreSQL database...")
    pg_engine = create_engine(pg_url)
    PgSession = sessionmaker(bind=pg_engine)
    pg_session = PgSession()

    sqlite_file = "cv_platform.db"
    if os.path.exists(sqlite_file):
        print(f"Warning: '{sqlite_file}' already exists. Overwriting it...")
        os.remove(sqlite_file)

    print(f"Creating SQLite database '{sqlite_file}'...")
    sqlite_engine = create_engine(f"sqlite:///{sqlite_file}")
    
    # Create tables in SQLite
    Base.metadata.create_all(bind=sqlite_engine)
    
    SqliteSession = sessionmaker(bind=sqlite_engine)
    sqlite_session = SqliteSession()

    print(f"Copying projects (excluding: {', '.join(EXCLUDED_PROJECTS)})...")
    projects = pg_session.query(Project).all()
    excluded_project_ids = set()
    copied_projects_count = 0
    for p in projects:
        if p.name in EXCLUDED_PROJECTS:
            excluded_project_ids.add(p.id)
            print(f" - Excluding project: {p.name} (ID: {p.id})")
            continue
        sqlite_p = Project(
            id=p.id,
            name=p.name,
            created_at=p.created_at
        )
        sqlite_session.add(sqlite_p)
        copied_projects_count += 1
    sqlite_session.commit()
    print(f"-> Copied {copied_projects_count} projects. Excluded {len(excluded_project_ids)} projects.")

    print("Copying CVs (excluding those assigned to excluded projects)...")
    cvs = pg_session.query(CV).all()
    copied_cvs_count = 0
    excluded_cvs_count = 0
    for c in cvs:
        if c.project_id in excluded_project_ids:
            excluded_cvs_count += 1
            continue
        sqlite_c = CV(
            id=c.id,
            filename=c.filename,
            file_type=c.file_type,
            file_data=c.file_data,
            uploaded_at=c.uploaded_at,
            status=c.status,
            extraction_method=c.extraction_method,
            raw_text=c.raw_text,
            ner_model1=c.ner_model1,
            ner_model2=c.ner_model2,
            ner_merged=c.ner_merged,
            ner_skills=c.ner_skills,
            years_of_experience=c.years_of_experience,
            seniority_level=c.seniority_level,
            project_id=c.project_id
        )
        sqlite_session.add(sqlite_c)
        copied_cvs_count += 1
    sqlite_session.commit()
    print(f"-> Copied {copied_cvs_count} CVs. Excluded {excluded_cvs_count} CVs.")

    print("Copying Match History (excluding runs for excluded projects)...")
    history = pg_session.query(MatchHistory).all()
    copied_history_count = 0
    excluded_history_count = 0
    for h in history:
        if h.project_id in excluded_project_ids:
            excluded_history_count += 1
            continue
        sqlite_h = MatchHistory(
            id=h.id,
            project_id=h.project_id,
            jd_text=h.jd_text,
            rubric=h.rubric,
            method=h.method,
            llm_model=h.llm_model,
            created_at=h.created_at,
            results=h.results
        )
        sqlite_session.add(sqlite_h)
        copied_history_count += 1
    sqlite_session.commit()
    print(f"-> Copied {copied_history_count} match runs. Excluded {excluded_history_count} runs.")

    pg_session.close()
    sqlite_session.close()
    print(f"Migration completed! Generated '{sqlite_file}'.")

if __name__ == "__main__":
    main()
