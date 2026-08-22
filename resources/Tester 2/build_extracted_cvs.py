import os
import sys
import re
import pandas as pd

# Reconfigure stdout to use UTF-8 to handle Bengali/Unicode characters without crashing
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def remove_bengali(text):
    if not isinstance(text, str):
        return text
    # Remove Bengali Unicode characters
    text = re.sub(r'[\u0980-\u09ff]+', '', text)
    
    # Remove empty brackets/parentheses/braces and ones containing only punctuation/spaces (e.g. "( - )" or "( , )")
    text = re.sub(r'\(\s*[\s,\-/\(\)\[\]]*\s*\)', '', text)
    text = re.sub(r'\[\s*[\s,\-/\(\)\[\]]*\s*\]', '', text)
    text = re.sub(r'\{\s*[\s,\-/\(\)\[\]]*\s*\}', '', text)
    
    # Clean up spacing around parentheses that were removed
    text = re.sub(r'\s\s+', ' ', text)
    # Clean up dangling commas and dashes
    text = re.sub(r',\s*,', ',', text)
    text = re.sub(r'-\s*-', '-', text)
    text = re.sub(r'\s*,\s*', ', ', text)
    text = re.sub(r',\s*,\s*', ', ', text)
    
    # Process line by line to strip and filter
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        # Clean trailing/leading commas or dashes from line
        line = re.sub(r'^[,\-\s]+|[,\-\s]+$', '', line)
        line = re.sub(r'\s\s+', ' ', line)
        if line:
            lines.append(line)
            
    return '\n'.join(lines)

def clean_val(val):
    if pd.isna(val):
        return ""
    val_str = str(val).strip()
    if val_str.lower() in ["nan", "n/a", "none", "null", "no", "not applicable", "n/q", "."]:
        return ""
    return val_str

def format_candidate_cv(row, district_cols):

    lines = []
    
    # Candidate Name
    name = clean_val(row.get('Full Name (পূর্ণ নাম)'))
    if name:
        lines.append(f"NAME: {name}")
        
    # Email & Phone
    email = clean_val(row.get('Email Address'))
    phone = clean_val(row.get('Phone number (ফোন নম্বর)'))
    contact_info = []
    if email:
        contact_info.append(f"Email: {email}")
    if phone:
        contact_info.append(f"Phone: {phone}")
    if contact_info:
        lines.append(" | ".join(contact_info))
        
    # Gender & Date of Birth
    gender = clean_val(row.get('Your gender (আপনার লিঙ্গ)'))
    dob = clean_val(row.get('Date of Birth according to NID/ Birth Certificate (জাতীয় পরিচয়পত্র / জন্ম সনদ অনুযায়ী জন্ম তারিখ)'))
    personal_details = []
    if gender:
        personal_details.append(f"Gender: {gender}")
    if dob:
        personal_details.append(f"Date of Birth: {dob}")
    if personal_details:
        lines.append(" | ".join(personal_details))
        
    # Address (combining present address with division and district from all 8 possible district columns)
    addr = clean_val(row.get('Present Address (বর্তমান ঠিকানা)'))
    div = clean_val(row.get('Which division do you live in?  (আপনি কোন বিভাগে থাকেন?) '))
    
    # Resolve district from the 8 columns
    dist = ""
    for col in district_cols:
        val = clean_val(row.get(col))
        if val:
            dist = val
            break
            
    address_parts = [addr, dist, div]
    address_full = ", ".join([p for p in address_parts if p])
    if address_full:
        lines.append(f"Address: {address_full}")
        
    # Portfolio Link
    portfolio = clean_val(row.get('Portfolio Link (ポートフォリオリンク / Portfolio Link)'))
    if not portfolio:
        # Search columns for portfolio if the long key changed slightly
        portfolio_col = [c for c in row.index if 'Portfolio' in c]
        if portfolio_col:
            portfolio = clean_val(row.get(portfolio_col[0]))
    if portfolio:
        lines.append(f"Portfolio Link: {portfolio}")
        

    # Education
    edu_lines = []
    univ = clean_val(row.get("University Name - Bachelor's/Honors (বিশ্ববিদ্যালয়ের নাম - স্নাতক)"))
    univ2 = clean_val(row.get("University Name - Bachelor's/Honors (বিশ্ববিদ্যালয়ের নাম - স্নাতক) 2"))
    subj = clean_val(row.get("Bachelors/Honors Subject (ব্যাচেলর্স/অনার্স বিষয়)"))
    major = clean_val(row.get("Bachelors/Honors Major (ব্যাচেলর্স/অনার্স মেজর)"))
    year = clean_val(row.get("Year of Bachelors/Honors completion (স্নাতক সম্পন্নের বছর)"))
    cgpa = clean_val(row.get("CGPA (সিজিপিএ)"))
    
    if univ or subj:
        edu_lines.append("EDUCATION")
        if univ:
            edu_lines.append(f"  University: {univ}")
        if univ2:
            edu_lines.append(f"  University 2: {univ2}")
        if subj:
            edu_lines.append(f"  Subject: {subj}")
        if major:
            edu_lines.append(f"  Major: {major}")
        if year:
            edu_lines.append(f"  Year of Completion: {year}")
        if cgpa:
            edu_lines.append(f"  CGPA: {cgpa}")
            
    if edu_lines:
        lines.append("\n" + "\n".join(edu_lines))
        
    # Work Experience
    work_keys = [
        # (Designation, Organization, Start Date, End Date)
        ("Designation (পদবী)  ", "Organization (প্রতিষ্ঠান)", "Starting Date (শুরুর তারিখ)  ", "Ending Date (শেষের তারিখ)"),
        ("Designation (পদবী)   2", "Organization (প্রতিষ্ঠান) 2", "Starting Date (শুরুর তারিখ)   2", "Ending Date (শেষের তারিখ) 2"),
        ("Designation (পদবী)   3", "Organization (প্রতিষ্ঠান) 3", "Starting Date (শুরুর তারিখ)   3", "Ending Date (শেষের তারিখ) 3")
    ]
    work_lines = []
    for d_col, o_col, s_col, e_col in work_keys:
        desig = clean_val(row.get(d_col))
        org = clean_val(row.get(o_col))
        start = clean_val(row.get(s_col))
        end = clean_val(row.get(e_col))
        
        if desig or org:
            if not work_lines:
                work_lines.append("WORK EXPERIENCE")
            job_desc = f"  - Designation: {desig}" if desig else "  - Job"
            if org:
                job_desc += f" at {org}"
            duration = []
            if start:
                duration.append(f"From: {start}")
            if end:
                duration.append(f"To: {end}")
            if duration:
                job_desc += f" ({', '.join(duration)})"
            work_lines.append(job_desc)
            
    if work_lines:
        lines.append("\n" + "\n".join(work_lines))
        
    # Certifications & Courses
    cert_keys = [
        # (Course Name, Duration, Start Date)
        ("Name of the Certification or Courses (সার্টিফিকেশন বা কোর্সের নাম)", "Course Duration (কোর্সের মেয়াদ)", "Course Starting Date (কোর্স শুরুর তারিখ)"),
        ("Name of the Certification or Courses (সার্টিফিকেশন বা কোর্সের নাম) 2", "Course Duration (কোর্সের মেয়াদ) 2", "Course Starting Date (কোর্স শুরুর তারিখ) 2"),
        ("Name of the Certification or Courses (সার্টিফিকেশন বা কোর্সের নাম) 3", "Course Duration (কোর্সের মেয়াদ) 3", "Course Starting Date (কোর্স শুরুর তারিখ) 3")
    ]
    cert_lines = []
    for n_col, d_col, s_col in cert_keys:
        cert_name = clean_val(row.get(n_col))
        dur = clean_val(row.get(d_col))
        start = clean_val(row.get(s_col))
        
        if cert_name:
            if not cert_lines:
                cert_lines.append("CERTIFICATIONS & COURSES")
            desc = f"  - {cert_name}"
            details = []
            if dur:
                details.append(f"Duration: {dur}")
            if start:
                details.append(f"Started: {start}")
            if details:
                desc += f" ({', '.join(details)})"
            cert_lines.append(desc)
            
    if cert_lines:
        lines.append("\n" + "\n".join(cert_lines))

    # Trainings
    tr_keys = [
        # (Training Name, Organization, Duration)
        ("Training Name (প্রশিক্ষণের নাম)", "Training Organization (প্রশিক্ষণ প্রতিষ্ঠান)", "Training Duration (প্রশিক্ষণের মেয়াদ)"),
        ("Training Name (প্রশিক্ষণের নাম) 2", "Training Organization (প্রশিক্ষণ প্রতিষ্ঠান) 2", "Training Duration (প্রশিক্ষণের মেয়াদ) 2"),
        ("Training Name (প্রশিক্ষণের নাম) 3", "Training Organization (প্রশিক্ষণ প্রতিষ্ঠান) 3", "Training Duration (প্রশিক্ষণের মেয়াদ) 3")
    ]
    tr_lines = []
    for n_col, o_col, d_col in tr_keys:
        tr_name = clean_val(row.get(n_col))
        tr_org = clean_val(row.get(o_col))
        tr_dur = clean_val(row.get(d_col))
        
        if tr_name or tr_org:
            if not tr_lines:
                tr_lines.append("TRAININGS")
            desc = f"  - {tr_name}" if tr_name else "  - Training"
            if tr_org:
                desc += f" at {tr_org}"
            if tr_dur:
                desc += f" (Duration: {tr_dur})"
            tr_lines.append(desc)
            
    if tr_lines:
        lines.append("\n" + "\n".join(tr_lines))

    # Skills
    skills_lines = []
    
    # Try to dynamically locate skills columns using substrings
    dig_col = next((c for c in row.index if 'Digital Skills' in c), None)
    tech_col = next((c for c in row.index if 'Technical Skills' in c), None)
    lang_col = next((c for c in row.index if 'Language Skills' in c), None)
    soft_col = next((c for c in row.index if 'Soft Skills' in c), None)
    
    dig = clean_val(row.get(dig_col)) if dig_col else ""
    tech = clean_val(row.get(tech_col)) if tech_col else ""
    lang = clean_val(row.get(lang_col)) if lang_col else ""
    soft = clean_val(row.get(soft_col)) if soft_col else ""
            
    if dig or tech or lang or soft:
        skills_lines.append("SKILLS")
        if dig:
            skills_lines.append(f"  Digital: {dig}")
        if tech:
            skills_lines.append(f"  Technical: {tech}")
        if lang:
            skills_lines.append(f"  Language: {lang}")
        if soft:
            skills_lines.append(f"  Soft: {soft}")
            
    if skills_lines:
        lines.append("\n" + "\n".join(skills_lines))
        
    return remove_bengali("\n".join(lines))

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "cv_list 2.csv")
    output_path = os.path.join(script_dir, "extracted_cvs_231.csv")

    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    df_csv = pd.read_csv(csv_path)
    print(f"Loaded {len(df_csv)} candidates from {csv_path}.")

    # Gather district columns to pass to formatter
    district_cols = [c for c in df_csv.columns if 'Which district do you live in?' in c]

    extracted_records = []
    for idx, row in df_csv.iterrows():
        uid = f"{idx + 1}.docx"
        raw_text = format_candidate_cv(row, district_cols)
        extracted_records.append({
            "filename": uid,
            "raw_text": raw_text
        })

    df_out = pd.DataFrame(extracted_records)
    df_out.to_csv(output_path, index=False)
    print(f"Saved {len(df_out)} structured CV texts to {output_path}.")

    # Also save as extracted_cvs_tester2.csv for alternate referencing
    alt_output_path = os.path.join(script_dir, "extracted_cvs_tester2.csv")
    df_out.to_csv(alt_output_path, index=False)
    print(f"Saved duplicate copy to {alt_output_path}.")

if __name__ == "__main__":
    main()

