# Evaluation Report: LLM Split Rubric Screening Test

This report documents the details, configuration, and top 10 results of the historical match evaluation run from **July 16, 2026, at 12:23:11 PM** for the project **Software Developer - .Net**.

The evaluation was executed using the **LLM Split Rubric** algorithm, which prompts the LLM to generate exactly 5 distinct screening criteria with integer weights (totaling 100%), scores candidates out of 100 on each category separately, and computes a final weighted match percentage.

---

## 1. Test Configuration & Environment
* **Project**: Software Developer - .Net (ID: `10`)
* **Match Algorithm**: LLM Judge (Split Rubric, 5-Criteria Scoring) (`llm_split_rubric`)
* **LLM Engine**: `gpt-oss:20b` (deterministic parameters: `temperature=1`, `top_p=1`, `top_k=1`)
* **Execution Timestamp**: `2026-07-16T12:23:11.444294+06:00`
* **Total Candidates Scored**: 30 resumes

---

## 2. Input Job Description
```text
Primary Purpose: Development and maintenance of software applications built using Microsoft stack. Essential Duties and Responsibilities: Following is a summary of the essential functions for this job. Other duties may be performed, both major and minor, which are not mentioned below. Specific activities may change from time to time. Design, develop and test software applications Maintain systems by identifying and correcting software defects Create technical specifications and unit test plans Work with QA to align understanding of requirements and to develop system test plans Work as part of an Agile development team to solve problems and develop projects in a fast paced environment Follow instructions and pre-established guidelines to perform the functions of the job Demonstrate a basic degree of creativity and problem solving skills Follow the established software development life cycle Follow established coding standards and naming conventions Support applications using software development methodologies including structured programming, documentation, design and code review Work with business analysts and application users to define and design robust user centric application solutions Collaborate with UX resources to drive consistent look and feel of user interface Collaborate with database resources to ensure robust and complete data access and manipulation Collaborate with IT Operations to ensure hardware and software are aligned to deliver business requirements Mentor junior and other new developers On-site regular attendance and punctuality are essential functions of the job Minimum Skills and Competencies: The requirements listed below are representative of the knowledge, skill and/or ability required. Reasonable accommodations may be made to enable individuals with disabilities to perform the essential functions. Bachelor's Degree or in-lieu of degree equivalent education, training and work-related experience High school diploma or general education degree (GED) required 5+ years of experience in Microsoft technology stack Expert in C#, JavaScript, MSSQL 2012 or above Proficient with MVC, Angular, Asp.Net, JQuery Hands on experience with Visual Studio & TFS as source control tool Must have good understanding of SOLID object oriented programming (OOP) concepts Must have experience with WCF Experience in end-to-end Software Development Life Cycle (SDLC) project Experience working with Agile/Scrum methodologies Good at understanding requirements, getting clarifications Have passion for learning new technologies and enhancing existing skills Proactive issue resolution with a positive attitude Understand solution at the project level Effective organization and time management skills with the ability to work under pressure and adhere to project deadlines Excellent interpersonal skills with the ability to establish working relationships with individuals at varying levels within the organization Demonstrated integrity within a professional environment Ability to adapt to new situations and learn quickly Must perform well in high-energy, dynamic and team-oriented environments Must possess effective verbal and written communication skills Desired Skills: Insurance industry experience Familiarity with writing unit tests Relevant Microsoft certification Experience with Web API, Entity Framework Experience with Crystal Reports, SSRS and/or SSIS
```

---

## 3. Generated Scoring Rubric Criteria
The LLM analyzed the job description and generated the following 5 weighted screening criteria:

1. **Microsoft Technology Stack Proficiency (Weight: 30%)**
   * *Description*: Expertise in C#, .NET, MVC, Angular, ASP.NET, JavaScript, jQuery, Visual Studio, TFS, SOLID OOP principles, and WCF services.
   * *Sub-criteria*: C# proficiency, ASP.NET MVC / Web API experience, Angular/JavaScript skillset, Source control (TFS) usage.
2. **Software Development Lifecycle & Methodologies (Weight: 25%)**
   * *Description*: Experience with end‑to‑end SDLC, Agile/Scrum practices, unit testing, code reviews, and adherence to coding standards.
   * *Sub-criteria*: Agile/Scrum participation, Unit test writing, Code review & documentation, SDLC ownership.
3. **Database and Data Access Expertise (Weight: 20%)**
   * *Description*: Proficiency with MSSQL (2012+), Entity Framework, SSRS/SSIS or Crystal Reports, and robust data manipulation.
   * *Sub-criteria*: MSSQL database design & tuning, Entity Framework usage, Reporting tools (SSRS/Crystal), ETL processes.
4. **Soft Skills & Collaboration (Weight: 15%)**
   * *Description*: Strong communication, teamwork, mentoring, problem‑solving, adaptability, and time‑management under pressure.
   * *Sub-criteria*: Interpersonal communication, Mentoring junior developers, Problem‑resolution attitude, Time management & deadline adherence.
5. **Domain Experience & Certifications (Weight: 10%)**
   * *Description*: Insurance industry knowledge, relevant Microsoft certifications, and familiarity with Web API.
   * *Sub-criteria*: Insurance domain exposure, Microsoft certification(s), Web API development.

---

## 4. Top 10 Candidate Rankings

| Rank | ID | Filename | Candidate Name | Score | Experience | Seniority |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | 402 | `12.docx` | **AviaBit Performed** | 76.7% | 20.5 yrs | Lead / Principal |
| 2 | 415 | `25.docx` | **NgRx** | 66.5% | 0.0 yrs | Senior |
| 3 | 404 | `14.docx` | **XHTML** | 66.05% | 9.9 yrs | Executive |
| 4 | 397 | `7.docx` | **Crestron SW-SIMPL** | 43.25% | 11.5 yrs | Executive |
| 5 | 394 | `4.docx` | **Frameworks** | 42.5% | 3.0 yrs | Mid-level |
| 6 | 399 | `9.docx` | **Dell** | 41.25% | 6.9 yrs | Senior |
| 7 | 414 | `24.docx` | **Alamofire** | 37.75% | 0.0 yrs | Senior |
| 8 | 416 | `26.docx` | **Unknown** | 36.95% | 5.0 yrs | Executive |
| 9 | 408 | `18.docx` | **Apps** | 35.0% | 0.0 yrs | Senior |
| 10 | 407 | `17.docx` | **Israel** | 34.1% | 1.9 yrs | Senior |

---

## 5. Detailed Candidate Breakdowns

### Rank 1: AviaBit Performed (`12.docx`)
* **ID**: 402
* **Overall Match Score**: **76.7%**
* **Calculated Experience**: 20.5 years
* **Heuristic Seniority**: Lead / Principal
* **Criteria Score Breakdown**:
  * **Microsoft Technology Stack Proficiency (22.5/30)**: The candidate demonstrates solid C#/.NET experience, frequent use of TFS, and strong JavaScript skills, but lacks explicit ASP.NET MVC/Web API or Angular expertise, limiting full Microsoft stack proficiency.
  * **Software Development Lifecycle & Methodologies (23.0/25)**: The candidate demonstrates comprehensive end‑to‑end SDLC ownership, Agile/Scrum leadership, extensive unit testing with Jest/Enzyme, rigorous code reviews, and established coding standards across multiple projects.
  * **Database and Data Access Expertise (15.0/20)**: The candidate demonstrates strong MSSQL proficiency with stored procedures, query optimization, OLAP, and data‑warehouse design, yet does not mention Entity Framework or reporting tools such as SSRS/Crystal Reports, resulting in a solid but incomplete fit for the full sub‑criteria.
  * **Soft Skills & Collaboration (13.2/15)**: The CV demonstrates strong communication, leadership, mentoring through hiring and training new team members, a proven problem‑resolution attitude with complex technical solutions, and effective time management evidenced by on‑time project launches and Scrum implementation.
  * **Domain Experience & Certifications (3.0/10)**: The candidate demonstrates strong Web API development skills and aviation‑industry experience, but lacks direct insurance domain exposure and any listed Microsoft certifications.

### Rank 2: NgRx (`25.docx`)
* **ID**: 415
* **Overall Match Score**: **66.5%**
* **Calculated Experience**: 0.0 years
* **Heuristic Seniority**: Senior
* **Criteria Score Breakdown**:
  * **Microsoft Technology Stack Proficiency (24.0/30)**: The candidate demonstrates strong C#, ASP.NET MVC/Web API, and Angular skills with Azure DevOps usage, but lacks explicit TFS, jQuery, Visual Studio, SOLID OOP principles, and WCF experience.
  * **Software Development Lifecycle & Methodologies (13.8/25)**: The candidate demonstrates some SDLC ownership and team‑lead responsibilities but lacks explicit evidence of Agile/Scrum participation, unit test writing, code reviews, or adherence to coding standards.
  * **Database and Data Access Expertise (14.0/20)**: The candidate demonstrates solid MSSQL and Entity Framework experience with database design and T\u2011SQL skills, plus SSRS usage, but lacks explicit evidence of advanced tuning, ETL (SSIS) or Crystal Reports expertise.
  * **Soft Skills & Collaboration (12.8/15)**: The CV demonstrates strong teamwork and leadership through multiple team\u2011lead roles, mentoring experience as a bootcamp manager, clear evidence of effective communication with stakeholders, problem\u2011solving in scope negotiations, and successful delivery of concurrent projects under deadlines.
  * **Domain Experience & Certifications (2.0/10)**: The CV shows experience with Web API but lacks any insurance domain exposure or Microsoft certifications, resulting in a low fit for this criterion.

### Rank 3: XHTML (`14.docx`)
* **ID**: 404
* **Overall Match Score**: **66.05%**
* **Calculated Experience**: 9.9 years
* **Heuristic Seniority**: Executive
* **Criteria Score Breakdown**:
  * **Microsoft Technology Stack Proficiency (21.0/30)**: The candidate demonstrates strong C# and ASP.NET MVC experience, moderate JavaScript/jQuery skills, but lacks evidence of Angular proficiency and TFS usage, resulting in a solid yet incomplete fit for the Microsoft Technology Stack criterion.
  * **Software Development Lifecycle & Methodologies (12.5/25)**: The CV shows strong end\u2011to\u2011end SDLC ownership and team leadership, yet it provides no clear evidence of Agile/Scrum participation, unit test writing, or systematic code review/documentation practices.
  * **Database and Data Access Expertise (14.0/20)**: The candidate demonstrates solid MSSQL design and tuning skills with complex queries, stored procedures, and optimization, but lacks explicit experience with Entity Framework, SSRS/SSIS or Crystal Reports, limiting full coverage of the criterion.
  * **Soft Skills & Collaboration (12.8/15)**: The candidate demonstrates strong leadership and collaboration through managing a 13\u2011person team, coordinating with contractors, mentoring implied by leading roles, resolving complex migration challenges, and consistently meeting large project deadlines.
  * **Domain Experience & Certifications (5.8/10)**: The candidate shows relevant Microsoft training and experience in a financial firm, yet lacks explicit insurance industry exposure and concrete evidence of Web API development, resulting in a moderate fit for the criterion.

### Rank 4: Crestron SW-SIMPL (`7.docx`)
* **ID**: 397
* **Overall Match Score**: **43.25%**
* **Calculated Experience**: 11.5 years
* **Heuristic Seniority**: Executive
* **Criteria Score Breakdown**:
  * **Microsoft Technology Stack Proficiency (13.5/30)**: The candidate demonstrates moderate Microsoft stack experience with C#/.NET and some web\u2011related skills (JavaScript, jQuery), but lacks evidence of ASP.NET MVC/Web API, Angular, SOLID OOP, WCF services, or TFS usage, resulting in a partial fit.
  * **Software Development Lifecycle & Methodologies (15.0/25)**: The candidate demonstrates Agile participation and involvement in all SDLC stages, but lacks evidence of unit testing, code reviews, or explicit adherence to coding standards.
  * **Database and Data Access Expertise (4.0/20)**: The candidate has minimal database experience (MySQL, MongoDB, T\u2011SQL) and only a beginner T\u2011SQL course; there is no evidence of MSSQL design/tuning, Entity Framework usage, SSRS/SSIS or Crystal Reports skills, nor ETL processes, resulting in low fit for the criterion.
  * **Soft Skills & Collaboration (8.2/15)**: The CV shows some teamwork and communication experience (representing team interests, agile collaboration) but lacks explicit evidence of mentoring, strong problem\u2011resolution attitude or proven time\u2011management under pressure.
  * **Domain Experience & Certifications (2.5/10)**: The CV shows no evidence of insurance industry exposure or Microsoft certifications, though it includes some Web API experience via REST and Postman usage.

### Rank 5: Frameworks (`4.docx`)
* **ID**: 394
* **Overall Match Score**: **42.5%**
* **Calculated Experience**: 3.0 years
* **Heuristic Seniority**: Mid-level
* **Criteria Score Breakdown**:
  * **Microsoft Technology Stack Proficiency (4.5/30)**: The CV shows experience with Angular and TFS but no evidence of C#, .NET, ASP.NET MVC/Web API, or WCF services, resulting in a low fit for the Microsoft Technology Stack.
  * **Software Development Lifecycle & Methodologies (16.2/25)**: The candidate shows clear Agile/Scrum participation and some documentation work, but lacks explicit evidence of unit test writing, code reviews, or full SDLC ownership.
  * **Database and Data Access Expertise (2.0/20)**: The CV shows experience with MySQL, PostgreSQL, MongoDB and Couchbase but lacks any mention of MSSQL, Entity Framework, SSRS/SSIS or Crystal Reports, resulting in a very low fit for the database and data\u2011access expertise criterion.
  * **Soft Skills & Collaboration (12.8/15)**: The CV demonstrates strong teamwork and communication through cross\u2011functional scrum participation, mentoring via manuals for peers, a problem\u2011resolution attitude highlighted by refactoring and critical issue fixes, and implied time\u2011management skills from Agile delivery expectations.
  * **Domain Experience & Certifications (7.0/10)**: The candidate has insurance domain experience and RESTful Web API development skills, but lacks Microsoft certifications, resulting in a moderate fit for the criterion.

### Rank 6: Dell (`9.docx`)
* **ID**: 399
* **Overall Match Score**: **41.25%**
* **Calculated Experience**: 6.9 years
* **Heuristic Seniority**: Senior
* **Criteria Score Breakdown**:
  * **Microsoft Technology Stack Proficiency (10.5/30)**: The candidate has limited Microsoft stack experience—only basic C# and ASP.NET mention with no MVC/Web API or TFS usage, though they demonstrate strong JavaScript skills but lack Angular expertise.
  * **Software Development Lifecycle & Methodologies (20.0/25)**: The CV shows consistent Agile/Scrum involvement, unit testing with Jest, code reviews, pair programming, and use of ESLint for coding standards across multiple projects.
  * **Database and Data Access Expertise (2.0/20)**: The CV shows only limited backend experience with ASP.NET and Node.js, without any explicit mention of MSSQL, Entity Framework, reporting tools or ETL processes, indicating very low fit for the Database and Data Access Expertise criterion.
  * **Soft Skills & Collaboration (8.2/15)**: The CV demonstrates teamwork through pair\u2011programming, code reviews, and use of collaboration tools, but lacks explicit evidence of mentoring juniors or strong time\u2011management practices, resulting in a moderate fit for the Soft Skills & Collaboration criterion.
  * **Domain Experience & Certifications (0.5/10)**: The CV shows no evidence of insurance industry experience, lacks any listed Microsoft certifications, and only mentions general web development skills without explicit Web API development or consumption.

### Rank 7: Alamofire (`24.docx`)
* **ID**: 414
* **Overall Match Score**: **37.75%**
* **Calculated Experience**: 0.0 years
* **Heuristic Seniority**: Senior
* **Criteria Score Breakdown**:
  * **Microsoft Technology Stack Proficiency (13.5/30)**: The candidate demonstrates basic C#/.NET proficiency and some front\u2011end work with Angular JS, but lacks evidence of ASP.NET MVC/Web API experience, advanced Angular/JavaScript skills, TFS usage, SOLID OOP principles or WCF services, resulting in a moderate fit for the Microsoft Technology Stack.
  * **Software Development Lifecycle & Methodologies (15.0/25)**: Shows Agile/Scrum involvement and CI practices but does not provide evidence of unit testing, code review, or full SDLC ownership.
  * **Database and Data Access Expertise (2.0/20)**: The candidate has general SQL and database experience (PostgreSQL, MySQL, MongoDB) but lacks any demonstrated proficiency with MSSQL 2012+, Entity Framework, SSRS/SSIS or Crystal Reports, and no ETL work is mentioned.
  * **Soft Skills & Collaboration (5.2/15)**: The CV shows experience working in Scrum teams and CI environments, indicating some teamwork and communication skills, but lacks explicit evidence of mentoring, problem\u2011resolution attitude, or time\u2011management under pressure.
  * **Domain Experience & Certifications (2.0/10)**: The CV shows no evidence of insurance industry exposure or Microsoft certifications, though it does demonstrate some experience with REST APIs.

### Rank 8: Unknown (`26.docx`)
* **ID**: 416
* **Overall Match Score**: **36.95%**
* **Calculated Experience**: 5.0 years
* **Heuristic Seniority**: Executive
* **Criteria Score Breakdown**:
  * **Microsoft Technology Stack Proficiency (0.0/30)**: The CV contains no evidence of experience or proficiency in C#, .NET, MVC, Angular, ASP.NET, JavaScript, jQuery, Visual Studio, TFS, SOLID OOP principles, or WCF services.
  * **Software Development Lifecycle & Methodologies (18.8/25)**: The CV demonstrates solid Agile/Scrum participation, extensive unit testing with PyTest, and SDLC ownership via architecture and migration initiatives, yet it does not explicitly mention code reviews or detailed documentation practices.
  * **Database and Data Access Expertise (1.0/20)**: The CV demonstrates experience with PostgreSQL and general backend development but contains no evidence of MSSQL (2012+), Entity Framework, SSRS/SSIS, Crystal Reports, or related ETL processes required for this criterion.
  * **Soft Skills & Collaboration (13.2/15)**: The CV demonstrates strong teamwork and mentoring experience, effective communication with product managers, proactive problem\u2011solving, and disciplined time management through scrum facilitation and process improvements.
  * **Domain Experience & Certifications (4.0/10)**: The candidate has some insurance domain exposure from BestDoctor but lacks Microsoft certifications and explicit Web API development experience, resulting in a moderate fit.

### Rank 9: Apps (`18.docx`)
* **ID**: 408
* **Overall Match Score**: **35.0%**
* **Calculated Experience**: 0.0 years
* **Heuristic Seniority**: Senior
* **Criteria Score Breakdown**:
  * **Microsoft Technology Stack Proficiency (1.5/30)**: The candidate’s experience is focused on iOS development with Swift and related technologies, with no evidence of proficiency in C#, .NET, MVC, Angular, JavaScript, jQuery, Visual Studio, TFS, SOLID OOP principles, or WCF services.
  * **Software Development Lifecycle & Methodologies (19.5/25)**: The candidate shows strong SDLC ownership through design, testing, and code review practices, but does not provide explicit evidence of Agile/Scrum participation.
  * **Database and Data Access Expertise (2.0/20)**: The CV shows experience only with CoreData, REALM, and Firebase, lacking any evidence of MSSQL, Entity Framework, SSRS/SSIS or Crystal Reports expertise required for this criterion.
  * **Soft Skills & Collaboration (10.5/15)**: Candidate shows strong time\u2011management and problem\u2011solving skills, collaborates effectively with QA and cross\u2011functional teams, yet provides limited evidence of mentoring junior developers.
  * **Domain Experience & Certifications (1.5/10)**: The CV demonstrates basic Web API experience but lacks any evidence of insurance industry exposure or relevant Microsoft certifications, resulting in a low fit for the criterion.

### Rank 10: Israel (`17.docx`)
* **ID**: 407
* **Overall Match Score**: **34.1%**
* **Calculated Experience**: 1.9 years
* **Heuristic Seniority**: Senior
* **Criteria Score Breakdown**:
  * **Microsoft Technology Stack Proficiency (3.6/30)**: The CV shows experience with JavaScript frameworks (React, Vue.js) and Python/Django backend, but lacks any evidence of C#, .NET, ASP.NET MVC/Web API, Angular, or TFS usage, resulting in a very low fit for the Microsoft Technology Stack proficiency criterion.
  * **Software Development Lifecycle & Methodologies (15.0/25)**: The candidate demonstrates end\u2011to\u2011end development experience and some unit testing (pytest, Cypress), yet there is no clear evidence of Agile/Scrum participation, systematic code reviews, documentation, or comprehensive SDLC ownership.
  * **Database and Data Access Expertise (3.0/20)**: The CV shows only PostgreSQL/MySQL usage and general SQL optimization, with no evidence of MSSQL, Entity Framework, SSRS/SSIS or Crystal Reports expertise, resulting in a low fit for the database and data\u2011access criterion.
  * **Soft Skills & Collaboration (10.5/15)**: The CV demonstrates teamwork, problem\u2011resolution skills, and collaboration with support teams, though it lacks explicit evidence of mentoring or detailed time\u2011management practices.
  * **Domain Experience & Certifications (2.0/10)**: The candidate has experience developing APIs with Django and some front\u2011end work but lacks any insurance domain exposure or Microsoft certifications, resulting in a low fit for this criterion.

---

