import os
import sys
import csv
import glob
import time

# Ensure backend directory is in the import path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from backend.database import SessionLocal
from backend.models import Project, CV
from backend.services import ocr as ocr_service
from backend.services import ner as ner_service

def seed_database():
    csv_path = "resources/Tester/5_vacancies.csv"
    cv_dir = "resources/Tester/CV"
    
    if not os.path.exists(csv_path):
        print(f"Error: Vacancies CSV file not found at {csv_path}")
        return
        
    if not os.path.exists(cv_dir):
        print(f"Error: CV directory not found at {cv_dir}")
        return

    # 1. Read job titles from CSV
    print(f"Reading vacancies from {csv_path}...")
    job_titles = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("job_title")
            if title:
                job_titles.append(title.strip())
                
    print(f"Found {len(job_titles)} job titles: {job_titles}")
    
    # 2. Get list of CV files
    cv_files = glob.glob(os.path.join(cv_dir, "*.docx"))
    # Sort files numerically if possible, otherwise alphabetically
    def get_sort_key(filepath):
        name = os.path.splitext(os.path.basename(filepath))[0]
        try:
            return (0, int(name))
        except ValueError:
            return (1, name)
            
    cv_files.sort(key=get_sort_key)
    cv_files = cv_files[:30]
    print(f"Found {len(cv_files)} CV docx files in {cv_dir}")
    
    if not job_titles:
        print("No job titles to process.")
        return
        
    if not cv_files:
        print("No CV files to process.")
        return

    db = SessionLocal()
    
    # 3. Create projects
    project_ids = {}
    for title in job_titles:
        proj = db.query(Project).filter(Project.name == title).first()
        if not proj:
            print(f"Creating project: '{title}'")
            proj = Project(name=title)
            db.add(proj)
            db.commit()
            db.refresh(proj)
        else:
            print(f"Project '{title}' already exists with ID {proj.id}")
        project_ids[title] = proj.id

    # 4. Process CV files and cache extraction/NER results
    print("\nStarting CV processing and database seeding...")
    cache = {}  # filepath -> dict of processed CV data
    
    # We will loop through each project and each CV
    total_projects = len(job_titles)
    total_cvs = len(cv_files)
    total_inserted = 0
    
    # Initialize spacy models to avoid lazy loading delays mid-loop
    print("Pre-loading spaCy models...")
    start_load = time.time()
    nlp1 = ner_service.get_model1()
    nlp2 = ner_service.get_model2()
    ner_service.get_skills_nlp()
    print(f"spaCy models loaded in {time.time() - start_load:.2f} seconds.")

    for p_idx, title in enumerate(job_titles, 1):
        proj_id = project_ids[title]
        print(f"\n[{p_idx}/{total_projects}] Seeding CVs for project: '{title}' (ID: {proj_id})")
        
        for c_idx, cv_path in enumerate(cv_files, 1):
            filename = os.path.basename(cv_path)
            
            # Check cache
            if cv_path in cache:
                data = cache[cv_path]
                cached_status = "cached"
            else:
                cached_status = "processed"
                # Run full pipeline
                # Read bytes
                with open(cv_path, "rb") as f:
                    file_bytes = f.read()
                
                # Extract text
                raw_text = ocr_service.extract_docx(file_bytes)
                
                # Convert docx to pdf (fast if it skips/returns None)
                stored_bytes = file_bytes
                stored_ext = "docx"
                pdf_bytes = ocr_service.convert_docx_to_pdf(file_bytes)
                if pdf_bytes:
                    stored_bytes = pdf_bytes
                    stored_ext = "pdf"
                    
                # Run NER models
                ner1 = ner_service.run_ner(raw_text, nlp1)
                ner2 = ner_service.run_ner(raw_text, nlp2)
                merged = ner_service.merge_ner(ner1, ner2)
                skills_ner = ner_service.run_skills_ner(raw_text)
                
                # Experience and seniority
                years, seniority = ner_service.estimate_experience_and_seniority(raw_text)
                exp_val = [f"{years} yrs" if years > 0 else "0 yrs"]
                sen_val = [seniority]
                
                # Inject experience/seniority metadata
                for ner_dict in (ner1, ner2, merged):
                    if "YEARS_OF_EXPERIENCE" not in ner_dict:
                        ner_dict["YEARS_OF_EXPERIENCE"] = exp_val
                    if "SENIORITY_LEVEL" not in ner_dict:
                        ner_dict["SENIORITY_LEVEL"] = sen_val
                        
                # Cache results
                data = {
                    "raw_text": raw_text,
                    "file_type": stored_ext,
                    "file_data": stored_bytes,
                    "ner_model1": ner1,
                    "ner_model2": ner2,
                    "ner_merged": merged,
                    "ner_skills": skills_ner,
                    "years_of_experience": years,
                    "seniority_level": seniority
                }
                cache[cv_path] = data
                
            # Create CV entry
            cv_obj = CV(
                filename=filename,
                file_type=data["file_type"],
                file_data=data["file_data"],
                extraction_method="python-docx",
                raw_text=data["raw_text"],
                ner_model1=data["ner_model1"],
                ner_model2=data["ner_model2"],
                ner_merged=data["ner_merged"],
                ner_skills=data["ner_skills"],
                years_of_experience=data["years_of_experience"],
                seniority_level=data["seniority_level"],
                status="classified",
                project_id=proj_id
            )
            
            db.add(cv_obj)
            db.commit()
            db.refresh(cv_obj)
            
            total_inserted += 1
            if c_idx % 10 == 0 or c_idx == total_cvs:
                print(f"  - CV progress: {c_idx}/{total_cvs} ({cached_status})")
                
    db.close()
    print(f"\nSuccessfully seeded {total_inserted} CV entries across {total_projects} projects!")

if __name__ == "__main__":
    start_time = time.time()
    seed_database()
    print(f"Total time elapsed: {time.time() - start_time:.2f} seconds.")
