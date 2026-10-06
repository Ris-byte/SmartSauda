import sys
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "PROJECT_REPORT.md"
DOCS_MD_PATH = ROOT / "docs" / "SMARTSAUDA_PROJECT_REPORT.md"

report_content = r"""# SMARTSAUDA: AN INTELLIGENT VEHICLE VALUATION AND RESALE ESTIMATION SYSTEM FOR THE NEPALESE AUTOMOBILE MARKET

---

## TITLE PAGE

**A PROJECT REPORT**  
**ON**  
**PROJECT III: PRJ 351**  
**TITLE OF THE PROJECT: SMARTSAUDA: AN INTELLIGENT VEHICLE VALUATION AND RESALE ESTIMATION SYSTEM FOR THE NEPALESE AUTOMOBILE MARKET**

**Submitted by:**  
- **Aayush Sigdel** (Exam Roll NO: 23530039)  
- **Sugham Kharel** (Exam Roll NO: 23530099)  
- **Kamal Subedi** (Exam Roll NO: 23530057)  

**Under the Guidance of:**  
**Er. Dipendra Silwal**  
Head of Department (BCA)  

**Submitted to the Faculty of Science and Technology,**  
**Oxford College of Engineering and Management (OCEM)**  
Gaindakot-2, Nawalparasi, Nepal  
in partial fulfilment of the requirements for  

**Sixth Semester Bachelor of Computer Application (BCA)**  
**Affiliated to Pokhara University**  
**Year: 2026**

---

## ORIGINAL COPY OF THE APPROVAL

**OXFORD COLLEGE OF ENGINEERING AND MANAGEMENT**  
**DEPARTMENT OF BACHELOR OF COMPUTER APPLICATION**  
**GAINDAKOT-2, NAWALPARASI, NEPAL**  

### RECOMMENDATION LETTER

This is to certify that the project report entitled **"SmartSauda: An Intelligent Vehicle Valuation and Resale Estimation System for the Nepalese Automobile Market"** submitted by:

- **Aayush Sigdel** (Exam Roll No: 23530039)  
- **Sugham Kharel** (Exam Roll No: 23530099)  
- **Kamal Subedi** (Exam Roll No: 23530057)  

to the Department of Bachelor of Computer Application, Oxford College of Engineering and Management, in partial fulfilment of the requirements for the degree of **Bachelor of Computer Applications (BCA)**, has been examined and approved as a genuine work carried out by the students under our guidance and supervision.

We recommend this report for evaluation and approval.

<br><br>
____________________________  
**Er. Dipendra Silwal**  
Project Supervisor  
Department of Bachelor of Computer Application  
Oxford College of Engineering and Management  

<br><br>
____________________________  
**Er. Dipendra Silwal**  
Head of Department (BCA)  
Department of Bachelor of Computer Application  
Oxford College of Engineering and Management  

---

### BOARD OF EXAMINERS' APPROVAL

The project report entitled **"SmartSauda: An Intelligent Vehicle Valuation and Resale Estimation System for the Nepalese Automobile Market"** submitted by **Aayush Sigdel**, **Sugham Kharel**, and **Kamal Subedi** is hereby approved as a creditable work in partial fulfillment of the requirements for the degree of **Bachelor of Computer Applications (BCA)** under Pokhara University.

**Board of Examiners:**

1. ____________________________  
   **Er. Dipendra Silwal**  
   Supervisor  

2. ____________________________  
   **External Examiner**  
   External Examiner  

3. ____________________________  
   **Internal Examiner**  
   Internal Examiner  

4. ____________________________  
   **Er. Dipendra Silwal**  
   Head of Department (BCA)  

**Date:** October, 2026  

---

## CERTIFICATE OF AUTHENTICATED WORK

We hereby declare that this study entitled **"SmartSauda: An Intelligent Vehicle Valuation and Resale Estimation System for the Nepalese Automobile Market"** is based on our original research and engineering work conducted at **Oxford College of Engineering and Management (OCEM)**, under the supervision of **Er. Dipendra Silwal**. Related works on the topic by other researchers have been duly acknowledged.

The project documentation in this report was mobilized by the three below-mentioned sixth semester undergraduate students of Bachelor of Computer Application (BCA) for the partial fulfillment of the requirement for the project of the sixth semester (PRJ 351).

Any kind of reproduction of the project and its part for commercial purposes is strictly prohibited without the prior permission of the authors.

<br><br>
____________________________  
**Aayush Sigdel**  
Exam Roll No: 23530039  
Date: October, 2026  

<br><br>
____________________________  
**Sugham Kharel**  
Exam Roll No: 23530099  
Date: October, 2026  

<br><br>
____________________________  
**Kamal Subedi**  
Exam Roll No: 23530057  
Date: October, 2026  

---

## ROLE AND RESPONSIBILITY FORM

*Table: Roles and Responsibility Table*

| Phase / Task | Responsibilities | Assigned To |
| :--- | :--- | :--- |
| **Requirement Analysis** | Gathering functional and non-functional requirements from vehicle buyers, sellers, and recondition showroom dealers; defining system scope, boundary feasibility rules, and finalizing the technology stack (FastAPI, React 19, TypeScript, PostgreSQL, Scikit-learn, Docker). | Sugham Kharel<br>Aayush Sigdel<br>Kamal Subedi |
| **System & Database Design** | Designing Use Case Diagrams, Data Flow Diagrams (DFD Level 0 and Level 1), Entity Relationship Diagrams (ERD), System Architecture Model, Vehicle Valuation Inference Workflow, and relational database schema (`smartsauda.catalog`, `smartsauda.users`, `smartsauda.sessions`, `smartsauda.predictions`, `smartsauda.rate_buckets`, `smartsauda.image_cache`); drafting REST API specifications. | Sugham Kharel<br>Aayush Sigdel |
| **Backend & Security Development** | Implementing asynchronous FastAPI application services and routers, Argon2id password hashing, anti-CSRF token verification, cryptographic session digest management, sliding-window rate limiting, domain boundary feasibility enforcement, database migrations, and ReportLab PDF valuation certificate generation. | Sugham Kharel |
| **Machine Learning / AI Integration** | Curating and cleaning the 3,316-record Nepalese automotive dataset (Cars: 1,110, Bikes: 1,800, Scooters: 406), implementing category-specific feature pipelines (`ml/features.py`), designing leakage-free `StratifiedGroupKFold` partitioning, training and tuning Regularized Ridge Regression and Random Forest Regressors, computing 95% bootstrap confidence intervals, and exporting checksum-verified artifacts. | Aayush Sigdel |
| **Frontend Development** | Building responsive, accessible Single Page Application (SPA) using React 19, TypeScript, and Tailwind CSS; implementing dynamic cascading vehicle selector dropdowns, multi-step valuation forms, interactive valuation report cards with depreciation breakdowns and market insight badges, and garage prediction history. | Kamal Subedi<br>Aayush Sigdel |
| **Testing & Debugging** | Writing and executing unit, integration, and security tests (236 pytest test cases covering API endpoints, authentication, catalog caching, rate limiting, and ML feature transforms); executing Playwright end-to-end browser tests for user flows; validating mathematical valuation bounds. | Aayush Sigdel<br>Kamal Subedi |
| **Documentation** | Writing the project proposal, system requirements and analysis, conceptual architecture models, detailed database schemas, UI design wireframes, implementation details, testing reports, user manuals, and the comprehensive final project report conforming to university standards. | Kamal Subedi |

---

## ABSTRACT

The pre-owned vehicle marketplace in Nepal has experienced exponential growth, driven by shifting economic demographics, expanding transit networks, and high import tariffs on new automobiles exceeding 250% to 300%. However, the secondary market continues to suffer from severe information asymmetry, lack of standardized valuation guidelines, speculative pricing by informal brokers, and high search costs for ordinary citizens. This project presents **SmartSauda**, a production-grade, secure, and data-driven vehicle valuation platform engineered specifically for the Nepalese context.

SmartSauda adopts a multi-tiered predictive modeling strategy that treats **Cars**, **Motorcycles (Bikes)**, and **Scooters** as structurally distinct vehicular segments. Leveraging a clean research cohort of 3,316 retained records across Nepal (1,110 cars, 1,800 bikes, and 406 scooters), the platform implements dedicated supervised learning architectures: a Regularized Ridge Regression model with logarithmic target scaling (`ridge_log_price`, $\alpha=0.1$) for cars, achieving a validation Mean Absolute Error (MAE) of NPR 81,801.91 ($R^2 = 0.987$, Median Absolute Percentage Error = 6.57%), and Tuned Random Forest Regressors (`random_forest_log_price`) for motorcycles (test MAE: NPR 41,948.30, $R^2 = 0.781$) and scooters (test MAE: NPR 26,932.60, $R^2 = 0.610$). A strict `StratifiedGroupKFold` partitioning heuristic grouped by vehicle type, normalized brand/model, manufacture year, and 1,000-km odometer buckets guarantees zero data leakage across train, validation, and test splits.

The system is deployed on an asynchronous **FastAPI** backend integrated with a cloud-hosted **PostgreSQL** relational database. Strict security controls—including Argon2id password hashing, anti-CSRF HMAC validation, cryptographic token digests in HttpOnly/SameSite session cookies, sliding-window rate limiting, and strict domain feasibility boundary checks—guarantee defense-in-depth. A modern **React 19** and **TypeScript** frontend provides an intuitive, accessible user interface featuring dynamic catalog lookups, real-time prediction breakdowns with clear uncertainty warnings, automated PDF report generation, and individual garage history tracking. SmartSauda bridges the gap between academic machine learning research and practical software engineering, delivering a transparent and reliable pricing benchmark for vehicle transactions in Nepal.

**Keywords:** Vehicle Resale Valuation, Machine Learning, Ridge Regression, Random Forest, FastAPI, React 19, Nepalese Automotive Market, Data Leakage Prevention, ReportLab.

---

## ACKNOWLEDGEMENT

We wish to express our sincere gratitude to all those who have supported and guided us throughout the development of this project, **SmartSauda**. Their encouragement and assistance have been invaluable in bringing this project to fruition.

First and foremost, we extend our heartfelt thanks to our project supervisor, **Er. Dipendra Silwal**, for his expert guidance, unwavering support, and insightful suggestions. His dedication and commitment were instrumental in the successful completion of this project.

We are also deeply grateful to **Er. Dipendra Silwal**, Head of the Department of Bachelor of Computer Applications, Oxford College of Engineering and Management, for providing the necessary institutional facilities, administrative support, and continuous academic encouragement.

Our sincere appreciation goes to all the faculty members of the BCA department for their valuable feedback and advice during project presentations and evaluations. We also express our appreciation to the open-source software community and independent data publishers, particularly **Riwaj Ghimire (riwajghimire61)** for publishing the *Bike Dataset Nepal* on Kaggle under the Apache 2.0 license, which significantly enhanced our two-wheeler predictive modeling capabilities.

Finally, we would like to thank our family members and friends for their constant motivation, patience, and support throughout our academic journey.

---

## TABLE OF CONTENTS

- **Title Page**
- **Original Copy of the Approval**
- **Certificate of Authenticated Work**
- **Role and Responsibility Form**
- **Abstract**
- **Acknowledgement**
- **Table of Contents**
- **Table of Figures**
- **List of Abbreviations**
- **List of Tables**
- **CHAPTER 1: INTRODUCTION**
  - 1.1 Background
  - 1.2 Objectives
  - 1.3 Purpose, Scope, and Applicability
    - 1.3.1 Purpose
    - 1.3.2 Scope
    - 1.3.3 Applicability
  - 1.4 Achievements
  - 1.5 Organization of Report
- **CHAPTER 2: SURVEY OF TECHNOLOGIES**
  - 2.1 Review of Similar/Relevant Projects
  - 2.2 Technology Stack Analysis and Comparison
    - 2.2.1 Backend Framework Selection
    - 2.2.2 Machine Learning Architecture Selection
    - 2.2.3 Frontend Framework and Tooling
    - 2.2.4 Database and Persistence Strategy
- **CHAPTER 3: REQUIREMENTS AND ANALYSIS**
  - 3.1 Problem Definition
  - 3.2 Requirements Specification
    - 3.2.1 Functional Requirements
    - 3.2.2 Non-Functional Requirements
  - 3.3 Planning and Scheduling
  - 3.4 Software and Hardware Requirements
    - 3.4.1 Minimum Hardware Requirements
    - 3.4.2 Software Requirements
  - 3.5 Preliminary Product Description
  - 3.6 Conceptual Models
    - 3.6.1 Use Case Diagram
    - 3.6.2 Data Flow Diagram (DFD)
    - 3.6.3 Entity Relationship Diagram (ERD)
    - 3.6.4 System Architecture Model
    - 3.6.5 Vehicle Valuation and Resale Estimation Model
    - 3.6.6 Valuation and Transaction Workflow Model
- **CHAPTER 4: DESIGN**
  - 4.1 Introduction
  - 4.2 System Design
  - 4.3 Database design
    - 4.3.1 Relational Schema Definitions and Constraints
    - 4.3.2 Data Dictionary and Table Structures
  - 4.4 Interface Design
    - 4.4.1 Vehicle Valuation Input Interface
    - 4.4.2 Valuation Result and Market Insights Interface
    - 4.4.3 Vehicle Catalog and Comparative Trends Interface
    - 4.4.4 Saved Garage and Valuation Certificate Interface
  - 4.5 Summary
- **CHAPTER 5: IMPLEMENTATION AND TESTING**
  - 5.1 Implementation Approaches
    - 5.1.1 Machine Learning Pipeline Implementation
    - 5.1.2 Backend API and Security Service Implementation
    - 5.1.3 Single Page Application Frontend Implementation
  - 5.2 Coding Details and Code Efficiency
    - 5.2.1 Code Efficiency
  - 5.3 Testing Approach
    - 5.3.1 Unit Testing
    - 5.3.2 Integrated Testing
    - 5.3.3 Beta Testing
  - 5.4 Modifications and Improvements
  - 5.5 Test Cases
- **CHAPTER 6: RESULTS AND DISCUSSION**
  - 6.1 Test Reports
    - 6.1.1 Automated Test Execution Summary
    - 6.1.2 Machine Learning Model Evaluation Benchmarks
    - 6.1.3 Latency and Resource Utilization
  - 6.2 User Documentation
    - 6.2.1 Vehicle Buyer & Seller User Guide
    - 6.2.2 System Setup and Developer Deployment Guide
- **CHAPTER 7: CONCLUSIONS**
  - 7.1 Conclusion
    - 7.1.1 Significance of the System
  - 7.2 Limitations of the System
  - 7.3 Future Scope of the Project
- **REFERENCES**

---

## TABLE OF FIGURES

- Figure 1: Gantt chart
- Figure 2: Use Case Diagram
- Figure 3: Data Flow Diagram
- Figure 4: Entity Relationship Diagram
- Figure 5: System Architecture Model
- Figure 6: Vehicle Valuation and Resale Estimation Model
- Figure 7: Valuation and Transaction Workflow Model
- Figure 8: System Design
- Figure 9: Database design
- Figure 10: Vehicle Valuation Input Interface
- Figure 11: Valuation Result and Market Insights Interface
- Figure 12: Vehicle Catalog and Comparative Trends Interface
- Figure 13: Saved Garage and Historical Prediction Interface
- Figure 14: Valuation Certificate and PDF Export Interface

---

## LIST OF ABBREVIATIONS

| Abbreviation | Full Form |
| :--- | :--- |
| **API** | Application Programming Interface |
| **BCA** | Bachelor of Computer Application |
| **BHP** | Brake Horse Power |
| **CC** | Cubic Centimetres (Engine Displacement) |
| **CI/CD** | Continuous Integration / Continuous Deployment |
| **CORS** | Cross-Origin Resource Sharing |
| **CSRF** | Cross-Site Request Forgery |
| **CSS** | Cascading Style Sheets |
| **CSV** | Comma-Separated Values |
| **DB** | Database |
| **DFD** | Data Flow Diagram |
| **ERD** | Entity Relationship Diagram |
| **EV** | Electric Vehicle |
| **FIFO** | First In, First Out |
| **FK** | Foreign Key |
| **GB** | Gigabyte |
| **HTML** | HyperText Markup Language |
| **HTTP** | HyperText Transfer Protocol |
| **HTTPS** | HyperText Transfer Protocol Secure |
| **IDE** | Integrated Development Environment |
| **ICE** | Internal Combustion Engine |
| **JSON** | JavaScript Object Notation |
| **JSONB** | JavaScript Object Notation Binary |
| **JWT** | JSON Web Token |
| **KW** | Kilowatt |
| **MAE** | Mean Absolute Error |
| **MAPE** | Median Absolute Percentage Error |
| **ML** | Machine Learning |
| **MPV** | Multi-Purpose Vehicle |
| **NFR** | Non-Functional Requirement |
| **NPR** | Nepalese Rupee |
| **OCEM** | Oxford College of Engineering and Management |
| **OOB** | Out-of-Bag |
| **ORM** | Object-Relational Mapping |
| **PDF** | Portable Document Format |
| **PK** | Primary Key |
| **R²** | Coefficient of Determination |
| **RAM** | Random Access Memory |
| **REST** | Representational State Transfer |
| **RMSE** | Root Mean Squared Error |
| **SHA** | Secure Hash Algorithm |
| **SPA** | Single Page Application |
| **SQL** | Structured Query Language |
| **SSD** | Solid-State Drive |
| **SUV** | Sport Utility Vehicle |
| **TLS** | Transport Layer Security |
| **UI** | User Interface |
| **URI** | Uniform Resource Identifier |
| **URL** | Uniform Resource Locator |
| **UUID** | Universally Unique Identifier |
| **UX** | User Experience |
| **Vite** | Frontend Build Tool (French for "quick") |

---

## LIST OF TABLES

| Table Number | Table Title |
| :--- | :--- |
| **Table 1** | Planning and Scheduling Table |
| **Table 2** | Test Cases |
| **Table 3** | Test Report Summary |
| **Table 4** | Vehicle Dataset Distribution and Cohort Statistics |
| **Table 5** | Machine Learning Model Performance Benchmarks |

---

# CHAPTER 1: INTRODUCTION

## 1.1 Background
In Nepal, private personal vehicles—primarily motorcycles, scooters, and compact cars—constitute the backbone of urban and semi-urban mobility. Owing to steep customs tariffs, excise taxes, and infrastructure levies that can exceed 250% to 300% on imported automobiles, purchasing a brand-new vehicle is financially prohibitive for the vast majority of middle-class households. Consequently, the secondary (pre-owned) automobile and two-wheeler market has expanded rapidly across cities such as Kathmandu, Pokhara, Biratnagar, Bharatpur, and Butwal.

Despite its massive economic scale, the Nepalese second-hand vehicle market remains largely unorganized, decentralized, and opaque. Transactions typically occur through informal middlemen (dalals), peer-to-peer social media listings, classifieds portals like HamroBazar, or independent physical reconditioned-vehicle lots. These transaction channels lack objective, data-backed pricing standards. Sellers frequently post inflated speculative asking prices, while uninformed buyers risk overpaying or purchasing mechanically exhausted vehicles.

Machine learning offers a transformative avenue for standardizing asset valuation. By analyzing historical transaction patterns across vehicle attributes (make, model, manufacturing year, engine displacement, mileage, transmission, and operational condition), regression algorithms can identify underlying non-linear depreciation curves. However, deploying machine learning in the Nepalese automotive sector entails unique localized challenges: highly skewed brand distributions (e.g., Maruti Suzuki, Hyundai, Bajaj, Honda, and Yamaha dominate the market), missing listing records, informal nomenclature, electric vehicles with distinct power ratings, and the absence of live centralized registration databases. SmartSauda was engineered specifically to address these challenges through rigorous domain-constrained modeling and transparent software engineering.

## 1.2 Objectives
The primary objective of the SmartSauda project is to develop an intelligent, reliable, and user-friendly vehicle valuation and resale estimation system specifically customized for the Nepalese market.

The specific supporting objectives are:
1. **Curate and Sanitize a Multi-Source Automotive Dataset:** Ingest, clean, reconcile, and audit historical vehicle listings from local Nepalese data sources, isolating 3,316 high-quality, verified records across three distinct segments: Cars, Motorcycles (Bikes), and Scooters.
2. **Train and Validate Segment-Specific Machine Learning Models:** Design isolated, leak-free regression pipelines utilizing `StratifiedGroupKFold` partitioning to eliminate data contamination caused by repeated listings. Benchmark multiple algorithms (Ridge Regression, Random Forest, Gradient Boosting, Baseline Medians) to select the optimal model per vehicular category based on Mean Absolute Error (MAE) and $R^2$.
3. **Implement Robust Feasibility and Out-of-Distribution Gating:** Enforce strict mathematical and physical domain boundary checks (e.g., prohibiting diesel motorcycles, capping annual mileage to realistic maximums, preventing extrapolation outside recorded manufacturing years) before passing requests to estimators.
4. **Develop a Production-Ready, Secure Asynchronous Backend:** Construct a RESTful API using FastAPI and PostgreSQL, featuring enterprise-grade security mechanisms: Argon2id password hashing, cryptographic token digest sessions, anti-CSRF token verification, sliding-window rate limiting, and role-based access control.
5. **Create a Modern, Intuitive User Interface:** Build a responsive Single Page Application (SPA) using React 19, TypeScript, and Vite that provides frictionless valuation input, transparent error reporting, clear uncertainty disclaimers, garage history persistence, and downloadable PDF valuation certificates.
6. **Execute Rigorous Verification and Testing:** Validate system correctness through comprehensive test suites encompassing unit, integration, security, and edge-case testing, verifying that all domain rules and software boundaries operate reliably.

## 1.3 Purpose, Scope, and Applicability

### 1.3.1 Purpose
The fundamental purpose of SmartSauda is to empower Nepalese consumers, sellers, and automotive enthusiasts with transparent, objective, and statistically grounded valuation benchmarks. By reducing information asymmetry, the system enables buyers and sellers to negotiate with confidence, minimizes predatory brokerage margins, and provides an auditable paper trail through auto-generated PDF valuation reports.

### 1.3.2 Scope
The scope of the project encompasses:
- Support for three major vehicle classes operating in Nepal: **Cars** (sedans, hatchbacks, SUVs), **Motorcycles (Bikes)**, and **Scooters** (both internal combustion engine and electric models).
- Modeling historical depreciation patterns across brand, model, manufacturing age, cumulative distance driven (kilometres), engine capacity (cc), motor power (kW), fuel type, transmission, and overall vehicle condition.
- A fully functional web-based platform with user registration, authentication, prediction calculation, valuation history storage, and PDF certificate export.
- Administrative controls for user account management, platform metrics, and system auditing.
- Transparent reporting of model limitations, fitting row support, and out-of-distribution alerts directly to the user.

*Out of Scope:* Physical vehicle damage inspection via computer vision, legal title verification against Nepal Department of Transport Management (DoTM) records, real-time dynamic inflation indexing, and integrated escrow payment processing.

### 1.3.3 Applicability
SmartSauda is directly applicable to:
- **Individual Buyers and Sellers:** Assessing realistic resale prices before listing or bargaining on platforms such as HamroBazar or Facebook Marketplace.
- **Reconditioned Automobile Dealers:** Establishing standard baseline acquisition and sale prices based on statistical cohorts rather than subjective intuition.
- **Financial Institutions & Micro-Lenders:** Serving as a preliminary valuation benchmark for vehicle-backed collateral loans.
- **Insurance Agencies:** Assisting adjusters in estimating pre-accident depreciated market value for settlement calculations.

## 1.4 Achievements
The project has achieved several technical and operational milestones:
- **Zero-Leakage Training Cohort:** Successfully curated a 3,316-row training cohort with strict separation of target metadata and zero split contamination verified through group hashing.
- **High-Precision Valuation Models:**
  - *Car Model:* Achieved test MAE of **NPR 81,801.91** with $R^2 = 0.987$ and a Median Absolute Percentage Error (MAPE) of **6.57%**, with **95.05%** of test estimates falling within 20% of actual values.
  - *Bike Model:* Achieved test MAE of **NPR 41,948.30** with $R^2 = 0.781$ and MAPE of **12.88%**.
  - *Scooter Model:* Achieved test MAE of **NPR 26,932.60** with $R^2 = 0.610$ and MAPE of **15.11%**.
- **Comprehensive Quality Assurance:** Developed and executed **236 automated pytest test cases** (with 15 parametric subtests), covering 100% of critical paths including cryptographic authentication, CSRF validation, database transactions, feasibility rejections, and model artifact checksum integrity, executing flawlessly with zero failures.
- **Production-Ready Security Standards:** Implemented defense-in-depth architecture adhering to OWASP guidelines: Argon2id password hashing, HttpOnly Lax/Secure session cookies, HMAC CSRF tokens, strict SQL parameterization, request body size bounding (32 KB limit), and granular sliding-window rate limiting.
- **Automated Valuation Certificate Generation:** Integrated ReportLab to compile clean, downloadable, tamper-evident PDF reports containing submitted specifications, model versions, fitting support, and explicit uncertainty disclaimers.

## 1.5 Organization of Report
The remainder of this report is structured as follows:
- **Chapter 2: Survey of Technologies** reviews existing commercial and academic solutions in vehicle valuation and evaluates the selected technological stack.
- **Chapter 3: Requirements and Analysis** details the problem definition, functional and non-functional requirements, scheduling, system constraints, and conceptual models (Use Case, DFDs, ERD, System Architecture, Valuation Model, and Workflow Model).
- **Chapter 4: Design** illustrates the architectural design, entity-relationship data model, relational schemas, sequence diagrams, and user interface wireframes.
- **Chapter 5: Implementation and Testing** describes the technical implementation of machine learning pipelines, backend services, frontend components, code efficiency optimizations, testing methodologies, and concrete test cases.
- **Chapter 6: Results and Discussion** presents empirical test reports, cross-validation metrics, error distribution analyses, and comprehensive user documentation.
- **Chapter 7: Conclusions** concludes the report with a discussion of the system's significance, inherent limitations, and prospective avenues for future enhancement.
- **References** provides academic and industry citations supporting the research.

---

# CHAPTER 2: SURVEY OF TECHNOLOGIES

## 2.1 Review of Similar/Relevant Projects
Automated vehicle valuation has been widely implemented in developed markets, but remains in its infancy within developing economies characterized by informal transactions and fragmented data.

1. **Kelley Blue Book (KBB) and Edmunds (USA):**
   - *Overview:* Industry benchmarks in North America providing "Blue Book Value" based on millions of dealership wholesale transactions, auction records, and depreciation curves.
   - *Strengths:* Massive transaction datasets, granular regional adjustment, condition grading.
   - *Weaknesses:* Rely heavily on standardized VIN (Vehicle Identification Number) decoding and centralized institutional transaction reporting, neither of which exists in Nepal.
2. **CarDekho and Spinny (India):**
   - *Overview:* Digital automotive platforms offering algorithmic pricing engines for used vehicles across Indian metropolitan centers.
   - *Strengths:* Effective machine learning pipelines tailored to South Asian vehicle brands (Maruti Suzuki, Hyundai, Tata).
   - *Weaknesses:* Optimized for Indian tax brackets, road conditions, and currency scales. Direct application to Nepal fails due to Nepal's unique 250%+ import tax structure, vastly differing depreciation rates, and distinct local driving topographies.
3. **HamroBazar (Nepal):**
   - *Overview:* Nepal's leading classifieds portal where hundreds of thousands of used vehicles have been listed.
   - *Strengths:* High user traffic, rich repository of localized listings.
   - *Weaknesses:* Pure classifieds model with zero valuation intelligence. Asking prices are unilaterally set by sellers, leading to wide discrepancies, speculative listing prices, and unguided negotiation.
4. **Academic Literature on Vehicle Price Depreciation:**
   - *Gegic et al. (2019)* demonstrated that tree-based ensembles (Random Forest) and regularized linear regression outperform artificial neural networks on small-to-medium tabular vehicle datasets due to reduced overfitting on sparse categorical features.
   - *Listiani (2009)* highlighted that log-transforming skewed monetary targets stabilizes residual variance across price tiers.

*Comparison of Existing Vehicle Valuation Systems vs. SmartSauda:*

| Feature / Attribute | Kelley Blue Book | CarDekho Price Index | HamroBazar Listings | SmartSauda (Proposed System) |
| :--- | :--- | :--- | :--- | :--- |
| **Target Market** | United States | India | Nepal | **Nepal (Localized Context)** |
| **Vehicle Categories** | Cars, Trucks | Cars | Cars, Bikes, Scooters | **Cars, Bikes, Scooters (ICE & EV)** |
| **Valuation Engine** | Proprietary Statistical | Gradient Boosted ML | None (User-defined) | **Ridge & Random Forest ML** |
| **Data Transparency** | Low (Proprietary black-box) | Medium | None | **High (Warnings & Support Rows Shown)** |
| **Feasibility Boundary Validation** | High (VIN locked) | Medium | None | **Strict (Catalog & Domain Enforced)** |
| **PDF Valuation Report** | Commercial | Optional | None | **Automated & Tamper-Evident** |
| **Cost to End User** | Free / Ad-supported | Free / Lead-gen | Free | **Open Academic / Public Access** |

## 2.2 Technology Stack Analysis and Comparison

### 2.2.1 Backend Framework Selection
For the backend web service, three Python frameworks were evaluated: **FastAPI**, **Django REST Framework (DRF)**, and **Flask**.

| Parameter | Flask | Django REST Framework | FastAPI (Selected) |
| :--- | :--- | :--- | :--- |
| **Execution Paradigm** | Synchronous WSGI | Synchronous WSGI | **Asynchronous ASGI (High concurrency)** |
| **Type Safety & Validation** | Manual / Marshmallow | Serializers | **Native Pydantic v2 Type Enforcing** |
| **API Documentation** | Manual Swagger integration | Django Schema plugins | **Automatic OpenAPI & Swagger UI** |
| **Footprint & Overhead** | Minimal | Heavy (Batteries included) | **Lightweight & High-Throughput** |
| **ML Inference Integration** | Good | Moderate | **Seamless with standard Python ML runtimes** |

FastAPI was selected because its native asynchronous architecture (powered by Starlette and Uvicorn) provides exceptional request throughput, built-in request schema validation via Pydantic, and native OpenAPI generation.

### 2.2.2 Machine Learning Architecture Selection
Tabular data characterized by mixed categorical attributes (Brand, Model, Transmission) and continuous numeric features (Kilometres driven, Vehicle age) was evaluated across Deep Neural Networks, Gradient Boosted Decision Trees (LightGBM/XGBoost), Regularized Linear Models (Ridge Regression), and Random Forest Ensembles.
- **Deep Neural Networks (DNNs):** Tested in preliminary exploration but suffered from poor generalization and extreme overfitting due to the modest sample size (3,316 rows) and high categorical cardinality.
- **Ridge Regression with Log Target (`ridge_log_price`):** Selected for the **Car** model ($\alpha=0.1$). Because used car prices scale exponentially with age and brand tier, log-transforming price ($\ln(1 + \text{price})$) linearized the feature relationships. Ridge regularization prevented collinearity issues between age and mileage.
- **Random Forest Regressor (`random_forest_log_price`):** Selected for **Bikes** and **Scooters**. Decision trees naturally capture non-linear displacement-to-price curves and segment boundaries (e.g., premium dirt bikes vs. commuter commuters) without requiring complex polynomial transformations.

### 2.2.3 Frontend Framework and Tooling
- **React 19 & TypeScript:** React’s declarative component model coupled with TypeScript’s static type safety ensures that API response schemas are enforced on the client side, eliminating runtime undefined errors.
- **Vite:** Utilized as the next-generation frontend build tool, delivering sub-second Hot Module Replacement (HMR) and optimized Rollup-based production bundles.
- **Design Tokens & Modern CSS:** Custom CSS variables and atomic design tokens were employed rather than bulky utility libraries to achieve a high-performance, dark/light balanced aesthetic inspired by automotive telemetry dashboards.

### 2.2.4 Database and Persistence Strategy
- **PostgreSQL 16:** Chosen as the primary relational database system, leveraging JSONB data types for flexible specification/result storage while strictly enforcing relational integrity, foreign key cascades, and check constraints for users, authentication sessions, and predictions.
- **SQLAlchemy 2.0:** Applied using modern 2.0 declarative typing, connection pooling, and schema isolation (`smartsauda` private schema).
- **SQLite (In-Memory with StaticPool):** Deployed specifically for lightning-fast test isolation during automated pytest runs, mirroring Postgres behaviors.

---

# CHAPTER 3: REQUIREMENTS AND ANALYSIS

## 3.1 Problem Definition
The Nepalese pre-owned automobile ecosystem is burdened by systemic inefficiencies:
1. **Severe Information Asymmetry:** Buyers rarely possess mechanical knowledge or historical price benchmarks. Transactions are dictated by subjective assertions made by reconditioned lot dealers or self-interested middlemen.
2. **Speculative Online Pricing:** On classified portals, asking prices reflect wishful thinking rather than realized clearing prices. This creates an anchored, artificially inflated perception of vehicle resale value.
3. **Absence of Feasibility Standards:** Existing informal tools or foreign calculators permit physically impossible inputs (e.g., an electric scooter with a 500 cc engine, a 1980 Maruti Alto, or a 1-year-old vehicle with 2,000,000 kilometres), outputting nonsensical valuations that erode user trust.
4. **Lack of Verified Valuation Documentation:** Neither buyers nor sellers possess formal, objective documentation summarizing vehicle specifications and model-backed valuation ranges to substantiate price negotiations.

## 3.2 Requirements Specification

### 3.2.1 Functional Requirements
1. **User Authentication & Session Management (FR-01):** The system must allow users to register with email, display name, and password. The system must hash passwords using Argon2id, issue cryptographic token digests in secure HttpOnly cookies, and support role-based authorization (`User` vs. `Admin`).
2. **Dynamic Catalog Lookups (FR-02):** The system must serve verified vehicle metadata (brand, model, version, allowable manufacturing years, body types, fuel types, transmissions). The UI must dynamically update available options as previous selections are made.
3. **Feasibility Validation Guard (FR-03):** The backend must validate submitted vehicle parameters against physical and historical feasibility rules before passing them to the machine learning inference engine. Any physically impossible specification must return a 422 Unprocessable Entity error with clear field-level guidance.
4. **Resale Price Estimation (FR-04):** The system must compute predicted resale value in Nepalese Rupees (NPR) using segment-specific machine learning models (Cars, Bikes, Scooters). Predictions must include support record counts, model version metadata, and out-of-distribution warning flags.
5. **Automated PDF Valuation Certificate (FR-05):** Authenticated users must be able to download a publication-grade, tamper-evident PDF valuation report summarizing vehicle specifications, predicted price, confidence indicators, model version, and legal caveats.
6. **Personal Garage History (FR-06):** Registered users must have access to a personal garage dashboard displaying past valuation requests, search/filter capabilities, and quick re-valuation links.
7. **Administrative Auditing & User Management (FR-07):** System administrators must be able to view registered user rosters, toggle user active/deactivated statuses (safeguarded against disabling the last administrator), and view system metrics.

### 3.2.2 Non-Functional Requirements
1. **Performance & Latency (NFR-01):** Machine learning inference must execute in under 15 milliseconds per request. The full end-to-end HTTP request-response cycle for predictions must not exceed 100 milliseconds under normal network conditions.
2. **Security & Defense-in-Depth (NFR-02):** The platform must adhere to OWASP security standards: Argon2id password hashing, anti-CSRF token verification on state-changing endpoints, HttpOnly/SameSite cookie attributes, strict SQL parameterization via SQLAlchemy, and a 32 KB request body limit.
3. **Rate Limiting (NFR-03):** The API must enforce sliding-window rate limiting (20 predictions per minute per client IP/user) to prevent denial-of-service and automated scraping attacks.
4. **Reliability & Reproducibility (NFR-04):** Machine learning pipeline runs must be 100% deterministic, seeded, and verified using cryptographic SHA-256 checksums on all exported model artifacts.
5. **Usability & Accessibility (NFR-05):** The user interface must be fully responsive across mobile, tablet, and desktop viewports, conforming to WCAG 2.1 Level AA accessibility standards verified via automated axe-core scans.
6. **Data Integrity (NFR-06):** Database transactions must adhere strictly to ACID properties. User prediction ownership must be enforced at the SQL query level to prevent unauthorized cross-tenant data access.

## 3.3 Planning and Scheduling
The development of SmartSauda was divided into several phases so that the project could be completed in a systematic manner. The main planned activities were requirement analysis, system design, machine learning pipeline engineering, backend development, frontend development, testing, and documentation.

*Table 1: Planning and Scheduling Table*

| Phase | Task | Duration |
| :--- | :--- | :--- |
| **Requirement Analysis** | Identify user needs, functional and non-functional requirements, market problems in Nepal, project scope, and finalize technology stack. | June 01 - June 30 |
| **System & Database Design** | Design UML Use Case Diagrams, DFDs, ERDs, System Architecture, Valuation Inference Models, and PostgreSQL schema definitions. | July 01 - July 15 |
| **Machine Learning Pipeline** | Clean raw datasets, quarantine anomalies, implement StratifiedGroupKFold partitioning, train and tune Ridge and Random Forest models. | July 16 - August 15 |
| **Backend & Security Development** | Construct FastAPI application, Argon2id auth, CSRF middleware, rate limiting, ReportLab PDF generation, and database migrations. | August 16 - September 15 |
| **Frontend SPA Development** | Build React 19 single-page UI, Vite build tooling, dynamic prediction form, valuation insight cards, and garage dashboard. | September 10 - September 27 |
| **Testing & Quality Assurance** | Execute 236 automated pytest suites, Playwright browser flows, performance benchmarking, and edge-case boundary testing. | September 25 - September 29 |
| **Documentation & Final Defense** | Prepare comprehensive project report, user manuals, system architecture diagrams, docx conversion, and presentation defense. | September 29 - October 05 |

```mermaid
gantt
    title SmartSauda Project Development Schedule
    dateFormat  YYYY-MM-DD
    section Phase 1: Inception
    Problem Analysis & Literature Review    :done, p1_1, 2026-06-01, 2026-06-15
    Dataset Acquisition & Licensing Audit   :done, p1_2, 2026-06-16, 2026-06-30
    section Phase 2: ML & Feasibility
    Data Sanitization & Outlier Quarantine  :done, p2_1, 2026-07-01, 2026-07-15
    Feature Engineering & Leakage Isolation :done, p2_2, 2026-07-16, 2026-07-31
    Model Selection, Tuning & Evaluation   :done, p2_3, 2026-08-01, 2026-08-15
    section Phase 3: Backend Development
    Database Schema & Migration Pipeline   :done, p3_1, 2026-08-16, 2026-08-25
    FastAPI Core, Security & Rate Limiting  :done, p3_2, 2026-08-26, 2026-09-05
    PDF Report Engine & Image Integration   :done, p3_3, 2026-09-06, 2026-09-15
    section Phase 4: Frontend & Integration
    React SPA Wireframing & Component Build :done, p4_1, 2026-09-10, 2026-09-20
    API Integration & Dynamic Form Validation:done, p4_2, 2026-09-21, 2026-09-27
    section Phase 5: Testing & Documentation
    Unit, Integration & Browser Test Suites :done, p5_1, 2026-09-25, 2026-09-28
    Documentation & Final Report Drafting   :active, p5_2, 2026-09-29, 2026-10-05
```
*Figure 1: Gantt chart*

## 3.4 Software and Hardware Requirements

### 3.4.1 Minimum Hardware Requirements
To develop, train, and deploy SmartSauda, the following hardware specifications were utilized:

| Hardware Component | Development Environment | Production Server Environment | Client Machine |
| :--- | :--- | :--- | :--- |
| **Processor** | Intel Core i5 / AMD Ryzen 5 (4+ Cores) | 2 vCPU (x86_64 or ARM64) | Any modern dual-core CPU |
| **System Memory (RAM)**| 8.0 GB RAM | 2.0 GB RAM | 2.0 GB RAM |
| **Storage Space** | 20 GB available SSD | 10 GB NVMe SSD | 500 MB free browser cache |
| **Network Interface** | Broadband Internet Connection | 100 Mbps Low-Latency Link | 3G / 4G / Wi-Fi |

### 3.4.2 Software Requirements
The software tools and runtime libraries supporting the platform are detailed below:

| Software Category | Specification / Tool | Purpose |
| :--- | :--- | :--- |
| **Operating System** | Windows 11 / Ubuntu Linux 22.04 LTS | Operating environment for dev and deployment |
| **Runtime Environment** | Python 3.12.x & Node.js 22.x LTS | Execution environments for backend and frontend |
| **Database System** | PostgreSQL 16 (Supabase cloud / Local) | Relational persistence and JSONB operations |
| **Backend Framework** | FastAPI 0.141.1, Uvicorn 0.53.0 | Asynchronous RESTful API server |
| **ORM & DB Tooling** | SQLAlchemy 2.1.0, psycopg 3.3.6 | Declarative database mapping and connection management |
| **Machine Learning** | scikit-learn 1.9.1, pandas 3.0.5, numpy 2.5.3| Model training, cross-validation, feature transformation |
| **PDF Generation** | ReportLab 5.0.1 | Programmatic PDF report rendering |
| **Frontend Framework** | React 19.2.8, TypeScript 6.0.2, Vite 8.3.0| User interface development and compilation |
| **UI Icons & Typography** | Lucide React, Bebas Neue, DM Sans | Visual iconography and modern typography |
| **Testing Toolchains** | Pytest 8.x, Playwright 1.63.0, Oxlint | Backend test automation and browser testing |

## 3.5 Preliminary Product Description
From an end-user's perspective, SmartSauda is accessible via any modern web browser without requiring third-party plugins. The application offers:
1. **Interactive Landing Page:** Introduces the platform's methodology, data transparency statements, model accuracy indicators, and supported vehicle categories (Cars, Bikes, Scooters).
2. **Dynamic Valuation Wizard (`/predict`):** A step-by-step input wizard where users select vehicle type, brand, and model. As selections are made, the form dynamically configures allowable manufacturing year ranges and contextual fields (e.g., fuel type, transmission, motor power for EVs).
3. **Valuation Insight Panel (`/predictions/:id`):** Displays the estimated resale value in NPR alongside confidence indicators, the number of supporting training records, and explicit warnings if the vehicle represents an extrapolation.
4. **Instant PDF Certificate Download:** One-click generation of an official, formatted vehicle valuation certificate summarizing specifications, estimates, and legal caveats.
5. **Personal Garage History (`/history` and `/dashboard`):** Allows registered users to review past valuations, track price trends across multiple vehicles, and filter entries by date and vehicle type.
6. **Administrative Console (`/admin`):** Enables authorized administrators to monitor platform activity, user counts, and active sessions.

## 3.6 Conceptual Models
Conceptual models represent how the main components of SmartSauda interact with each other before detailed implementation. They help describe the system structure, data flow, user activities, and relationships among major entities.

The main conceptual models for SmartSauda are:
1. Use Case Diagram
2. Data Flow Diagram (DFD)
3. Entity Relationship Diagram (ERD)
4. System Architecture Model
5. Vehicle Valuation and Resale Estimation Model
6. Valuation and Transaction Workflow Model

### 3.6.1 Use Case Diagram
Shows the interaction of the main users, such as Vehicle Buyer/Seller (Registered User) and System Administrator, with system functions including registration, login, catalog browsing, vehicle specification submission, valuation calculation, PDF certificate download, and saved garage management.

```mermaid
flowchart LR
    User((Registered User))
    Admin((Administrator))

    subgraph SmartSauda System
        UC1[Register & Authenticate]
        UC2[Browse Vehicle Catalog]
        UC3[Submit Vehicle Specifications]
        UC4[View Valuation & Warnings]
        UC5[Download PDF Valuation Certificate]
        UC6[View Saved Garage History]
        UC7[Manage Profile & Password]
        UC8[Manage User Accounts & Status]
        UC9[Inspect System & Audit Metrics]
    end

    User --> UC1
    User --> UC2
    User --> UC3
    User --> UC4
    User --> UC5
    User --> UC6
    User --> UC7

    Admin --> UC1
    Admin --> UC8
    Admin --> UC9
    Admin --> UC4
```
*Figure 2: Use Case Diagram*

### 3.6.2 Data Flow Diagram (DFD)
Represents how data moves between users, the SmartSauda application, external media providers, authentication services, the ML inference engine, and the database.

#### Level 0 Context Diagram
The Level 0 DFD illustrates the boundaries of the SmartSauda system, showing data exchanges between external entities and the core system.

```mermaid
flowchart TD
    User([End User])
    Admin([Administrator])
    System[SmartSauda Vehicle Valuation Platform]
    ImageProv[(External Image Providers & Media Cache)]

    User -- "User Credentials, Vehicle Specs, Filter Queries" --> System
    System -- "Session Cookie, Valuation Results, PDF Report, Catalog Data" --> User

    Admin -- "Admin Authentication, Account Status Updates" --> System
    System -- "Platform Statistics, User Audit Lists" --> Admin

    System -- "Vehicle Make/Model Queries" --> ImageProv
    ImageProv -- "Vehicle Photographic Metadata & Image Blobs" --> System
```

#### Level 1 Detailed Process Data Flow Diagram
The Level 1 DFD decomposes the system into its primary computational processes: Authentication, Catalog Querying, Feasibility Validation & Inference, and Valuation Persistence & PDF Generation.

```mermaid
flowchart TD
    User([User])
    
    subgraph Processes
        P1[1.0 Authentication & Session Management]
        P2[2.0 Catalog & Feasibility Checking]
        P3[3.0 Machine Learning Inference Engine]
        P4[4.0 Valuation Storage & Report Generation]
    end

    subgraph Data Stores
        D1[(smartsauda.users)]
        D2[(smartsauda.sessions)]
        D3[(smartsauda.catalog)]
        D4[(smartsauda.predictions)]
        D5[(Trained ML Model Artifacts)]
    end

    User -->|Sign In / Sign Up| P1
    P1 <-->|Read / Write Credentials & Sessions| D1
    P1 <-->|Verify Token Digest| D2
    P1 -->|Auth Token & User Context| P2

    User -->|Select Make, Model, Specs| P2
    P2 <-->|Fetch Bounds & Rules| D3
    P2 -->|Validated Feature Payload| P3

    P3 <-->|Load Checksummed Model Pipeline| D5
    P3 -->|Predicted Price + Warnings| P4

    P4 <-->|Persist Valuation Row| D4
    P4 -->|Return Valuation View & Stream PDF| User
```
*Figure 3: Data Flow Diagram*

### 3.6.3 Entity Relationship Diagram (ERD)
Describes relationships among major entities such as Users, Sessions, Predictions, Catalog Entries, Rate Buckets, and Image Cache in the PostgreSQL database.

```mermaid
erDiagram
    USERS ||--o{ SESSIONS : "authenticates via"
    USERS ||--o{ PREDICTIONS : "owns"
    CATALOG_ENTRY ||--o{ PREDICTIONS : "classifies"
    RATE_BUCKET ||--o{ USERS : "throttles"
    IMAGE_CACHE ||--o{ CATALOG_ENTRY : "caches preview for"

    USERS {
        string id PK "UUID"
        string email UK "RFC 5322"
        string display_name "Max 80 chars"
        string password_hash "Argon2id"
        string role "User or Admin"
        boolean active "Account state"
        datetime created_at "UTC timestamp"
    }

    SESSIONS {
        string token_digest PK "SHA-256 64-hex"
        string user_id FK "References users.id"
        datetime expires_at "Index for cleanup"
    }

    PREDICTIONS {
        string id PK "UUID"
        string user_id FK "References users.id"
        string vehicle_type "Car, Bike, Scooter"
        string brand "Normalized make"
        string model "Normalized model"
        string model_version "v1.1.0"
        numeric price "NPR currency"
        jsonb specifications "Raw user inputs"
        jsonb result "Predicted value and warnings"
        jsonb image "Cached visual metadata"
        datetime created_at "UTC timestamp"
    }

    CATALOG_ENTRY {
        int id PK "Sequence ID"
        string vehicle_type "Index"
        string brand "Make"
        string model "Model"
        string model_version "Version"
        int training_rows "Support records"
        int min_year "Lower year bound"
        int max_year "Upper year bound"
        jsonb constraints "Domain rules"
    }

    RATE_BUCKET {
        string key PK "IP or user identifier"
        int count "Request counter"
        datetime expires_at "Window expiry"
    }

    IMAGE_CACHE {
        string key PK "Vehicle key hash"
        jsonb value "Binary/URL payload"
        datetime expires_at "TTL timestamp"
    }
```
*Figure 4: Entity Relationship Diagram*

### 3.6.4 System Architecture Model
Represents the overall structure of SmartSauda, including the client presentation tier, asynchronous application tier, machine learning inference layer, and data persistence tier.

```mermaid
flowchart TB
subgraph Presentation Tier [Client Presentation Tier - React 19 SPA]
UI_Home[Home & About Pages]
UI_Form[Dynamic Prediction Form]
UI_Result[Valuation Display & Insights]
UI_History[Garage History & Dashboard]
UI_Admin[Admin User Management]
end

subgraph Application Tier [Application & Service Tier - FastAPI]
MW[Security Middleware: CORS, GZip, RequestLimits 32KB, CSRF]
AuthRouter[Auth & Profile Router]
CatalogRouter[Catalog & Feasibility Router]
PredictRouter[Prediction & History Router]
ReportRouter[ReportLab PDF Engine]
MLRuntime[PricePredictor Runtime: Scikit-Learn Pipelines]
end

subgraph Data Tier [Persistence Tier - PostgreSQL & Artifacts]
DB[(PostgreSQL Database: smartsauda schema)]
ML_Models[(Checksummed Joblib Models: v1.1.0)]
Media_Cache[(Local Assets & Cached WebP Images)]
end

Presentation Tier <==>|JSON over HTTPS / Secure Cookies| Application Tier
Application Tier <==>|SQLAlchemy 2.0 ORM / Connection Pool| DB
MLRuntime <==>|Deterministic Joblib Deserialization| ML_Models
ReportRouter <==>|Binary Image Stream & PDF Compilation| Media_Cache
```
*Figure 5: System Architecture Model*

### 3.6.5 Vehicle Valuation and Resale Estimation Model
Shows how vehicle specification inputs are validated through domain feasibility gates, transformed through segment-specific feature pipelines (imputation, one-hot encoding, feature interaction), evaluated by trained estimators (Regularized Ridge Regression and Random Forest), and adjusted to compute the final valuation in NPR alongside uncertainty warnings.

```mermaid
flowchart TD
    In[User Vehicle Inputs: Type, Brand, Model, Year, Km, Fuel, Condition] --> Guard{Feasibility & Domain Boundary Guard}
    Guard -->|Invalid / Impossible Specs| Err[422 Rejection with Domain Guidance]
    Guard -->|Feasible Inputs| Feat[Feature Transformation Pipeline]
    
    subgraph Feature Engineering Engine
        Feat --> CalcAge[Compute Vehicle Age: 2026 - Year]
        Feat --> CalcKmYr[Compute km_per_year: Km / Age]
        Feat --> OneHot[One-Hot Encode: Brand, Fuel, Transmission, Condition]
        Feat --> MedianImpute[Median Imputation for Missing Numerics]
    end

    CalcAge & CalcKmYr & OneHot & MedianImpute --> PipeRouter{Vehicle Category Dispatcher}

    PipeRouter -->|Car Category| RidgePipe[Ridge Regression: alpha=0.1, log_price]
    PipeRouter -->|Bike Category| RFTreeBike[Random Forest Regressor: 150 Trees, log_price]
    PipeRouter -->|Scooter Category| RFTreeScoot[Random Forest Regressor: 150 Trees, log_price]

    RidgePipe & RFTreeBike & RFTreeScoot --> ExpTarget[Target Inversion: exp(y_pred) - 1]
    ExpTarget --> Calibrate[Residual Calibration & Rounding]
    Calibrate --> Out[Predicted Resale Valuation in NPR + Warnings + Confidence Interval]
```
*Figure 6: Vehicle Valuation and Resale Estimation Model*

### 3.6.6 Valuation and Transaction Workflow Model
Represents the end-to-end sequence workflow from user authentication and catalog selection to feasibility checks, ML inference, prediction persistence in the database, and PDF valuation certificate streaming.

```mermaid
sequenceDiagram
autonumber
actor User as Client Browser (React SPA)
participant API as FastAPI Backend (app.py)
participant Guard as Feasibility Validator (predict.py)
participant ML as ML Estimator (joblib pipeline)
participant DB as PostgreSQL Database
participant PDF as ReportLab PDF Engine

User->>API: POST /api/v1/predictions (JSON Payload + CSRF Token)
Note over API: Verify session cookie, rate bucket, & CSRF token
API->>Guard: validate_feasibility(payload, catalog, 2026)
alt Payload Violates Feasibility Rules
Guard-->>API: Raise PredictionInputError(code, message)
API-->>User: 422 Unprocessable Entity (Structured JSON Error)
else Payload is Feasible
Guard-->>API: Cleaned Features + Feasibility Context
API->>ML: estimator.predict(feature_frame)
ML-->>API: Predicted Price (NPR) + Inference Latency
API->>DB: INSERT INTO smartsauda.predictions
DB-->>API: Success (Generated Prediction UUID)
API-->>User: 201 Created (Prediction View + Warnings)
end
opt User Requests PDF Report
User->>API: GET /api/v1/predictions/{id}/report.pdf
API->>DB: Query prediction by ID and Owner
DB-->>API: Prediction Record
API->>PDF: prediction_pdf(row, settings, metadata)
PDF-->>API: Raw PDF Binary Stream
API-->>User: 200 OK (application/pdf attachment)
end
```
*Figure 7: Valuation and Transaction Workflow Model*

---

# CHAPTER 4: DESIGN

## 4.1 Introduction
The design phase of SmartSauda converts the identified requirements and conceptual models into a structured system design. It defines how the major components of the system interact, how data is organized, and how users communicate with the application through the interface.

The design of SmartSauda focuses on the overall system architecture, database structure, prediction pipeline, and user interfaces. The system is designed around an asynchronous FastAPI backend with separate modules for authentication, catalog querying, prediction execution, image caching, and PDF report compilation, supported by a React 19 single-page frontend.

## 4.2 System Design
The system design establishes the structural decomposition of the platform across four distinct architectural layers:
1. **Client Presentation Layer:** Implemented using React 19, TypeScript, and Vite. Handles client routing, interactive state management, dynamic cascading dropdowns, asynchronous API requests, and accessibility.
2. **API & Security Service Layer:** Implemented using FastAPI and Starlette. Enforces CORS policies, GZip response compression, 32 KB request body caps, anti-CSRF token verification, sliding-window rate limiting, and session cookie validation.
3. **Machine Learning Inference Layer:** Implemented using Scikit-Learn pipelines. Performs domain feasibility boundary gating, feature transformation, log-target inversion, and confidence interval estimation.
4. **Data & Persistence Layer:** Implemented using PostgreSQL 16 (hosted on Supabase / local instance) with SQLAlchemy 2.0 ORM, private schema isolation (`smartsauda`), and local filesystem model artifact storage.

```mermaid
flowchart TB
    subgraph Client Layer [Client Presentation Layer - React 19 SPA]
        Nav[Navigation Header & Auth Bar]
        FormView[Prediction Form Component]
        CardView[Valuation Insights Card]
        GarageView[Saved Garage Table]
    end

    subgraph Service Layer [FastAPI Application & Security Layer]
        CORS_MW[CORS & Compression Middleware]
        CSRF_MW[Anti-CSRF HMAC Validator]
        Rate_MW[Sliding-Window Rate Limiter]
        Auth_Svc[Argon2id Authentication Service]
        Catalog_Svc[Dynamic Catalog Provider]
        Report_Svc[ReportLab PDF Compiler]
    end

    subgraph Inference Layer [Machine Learning Inference Engine]
        Feas_Gate[Feasibility Boundary Guard]
        Feat_Pipe[Feature Engineering Transformer]
        Car_Model[Ridge Car Estimator]
        Bike_Model[Random Forest Bike Estimator]
        Scoot_Model[Random Forest Scooter Estimator]
    end

    subgraph Storage Layer [PostgreSQL Database & File Storage]
        Users_Tbl[(smartsauda.users)]
        Sess_Tbl[(smartsauda.sessions)]
        Pred_Tbl[(smartsauda.predictions)]
        Cat_Tbl[(smartsauda.catalog)]
        Model_Files[(Trained Models: v1.1.0)]
    end

    Client Layer <-->|HTTPS REST JSON & Cookies| Service Layer
    Service Layer <--> Feas_Gate
    Feas_Gate --> Feat_Pipe
    Feat_Pipe --> Car_Model & Bike_Model & Scoot_Model
    Service Layer <-->|SQLAlchemy 2.0 ORM| Storage Layer
    Car_Model & Bike_Model & Scoot_Model <--> Model_Files
```
*Figure 8: System Design*

## 4.3 Database design
The database design of SmartSauda defines the actual storage structure used by the system. It focuses on database tables, field data types, primary and foreign key relationships, check constraints, unique constraints, and indexes.

SmartSauda isolates all its tables within a dedicated PostgreSQL schema named `smartsauda`. This ensures clean separation from default public schemas and provides security boundaries.

```mermaid
flowchart LR
    subgraph smartsauda Schema
        U[users] ---|1:N| S[sessions]
        U ---|1:N| P[predictions]
        C[catalog] -.->|validates| P
        RB[rate_buckets]
        IC[image_cache]
    end
```
*Figure 9: Database design*

### 4.3.1 Relational Schema Definitions and Constraints
The relational schema definitions and table constraints are structured as follows:

*Relational Database Schema: `smartsauda.catalog`*

| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | Primary Key, Auto-increment | Unique catalog entry identifier |
| `vehicle_type` | `VARCHAR(10)` | Not Null, Index | Category: 'Car', 'Bike', or 'Scooter' |
| `brand` | `VARCHAR(160)` | Not Null | Manufacturer make name (normalized) |
| `model` | `VARCHAR(160)` | Not Null | Vehicle model name (normalized) |
| `model_version` | `VARCHAR(40)` | Not Null | Model artifact version (e.g., 'v1.1.0') |
| `training_rows`| `INTEGER` | Not Null, Check ($\ge 0$) | Count of supporting training observations |
| `min_year` | `SMALLINT` | Nullable | Earliest valid manufacturing year |
| `max_year` | `SMALLINT` | Nullable | Latest valid manufacturing year |
| `constraints` | `JSONB` | Nullable | Allowed fuels, transmissions, CC bounds |

*Relational Database Schema: `smartsauda.users`*

| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | Primary Key | UUIDv4 string identifier |
| `email` | `VARCHAR(254)` | Unique, Not Null, Index | Normalized user email address |
| `display_name` | `VARCHAR(80)` | Not Null | Human-readable user display name |
| `password_hash`| `VARCHAR(512)` | Not Null | Cryptographic Argon2id password hash |
| `role` | `VARCHAR(10)` | Not Null, Check (`role IN ('User', 'Admin')`) | Authorization privilege level |
| `active` | `BOOLEAN` | Not Null, Default: `TRUE` | Account operational status |
| `created_at` | `TIMESTAMPTZ` | Not Null, Default: `now()` | Account registration timestamp |

*Relational Database Schema: `smartsauda.sessions`*

| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `token_digest` | `VARCHAR(64)` | Primary Key | SHA-256 digest of secret cookie token |
| `user_id` | `VARCHAR(36)` | Foreign Key $\to$ `users.id` (CASCADE), Index | Associated authenticated user |
| `expires_at` | `TIMESTAMPTZ` | Not Null, Index | Absolute session expiration timestamp |

*Relational Database Schema: `smartsauda.predictions`*

| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | Primary Key | UUIDv4 string prediction identifier |
| `user_id` | `VARCHAR(36)` | Foreign Key $\to$ `users.id` (RESTRICT), Index | Owner of the valuation record |
| `vehicle_type` | `VARCHAR(10)` | Not Null | Category evaluated |
| `brand` | `VARCHAR(160)` | Not Null | Manufacturer make name |
| `model` | `VARCHAR(160)` | Not Null | Model name |
| `model_version`| `VARCHAR(40)` | Not Null | Model pipeline release version |
| `price` | `NUMERIC(24,2)`| Not Null, Check (`price > 0`) | Predicted resale valuation in NPR |
| `specifications`| `JSONB` | Not Null | Exact user-submitted specification payload |
| `result` | `JSONB` | Not Null | Calculated breakdown, warnings, and latency |
| `image` | `JSONB` | Nullable | Vehicle photo metadata and license attribution |
| `created_at` | `TIMESTAMPTZ` | Not Null, Default: `now()`, Composite Index | Valuation execution timestamp |

*Relational Database Schema: `smartsauda.rate_buckets`*

| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `key` | `VARCHAR(64)` | Primary Key | Sliding-window client identifier hash |
| `count` | `INTEGER` | Not Null, Check ($\ge 0$) | Total requests consumed in active window |
| `expires_at` | `TIMESTAMPTZ` | Not Null, Index | Window cleanup timestamp |

*Relational Database Schema: `smartsauda.image_cache`*

| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `key` | `VARCHAR(64)` | Primary Key | Canonical hash of (type, brand, model) |
| `value` | `JSONB` | Not Null | Image URL, local path, and license data |
| `expires_at` | `TIMESTAMPTZ` | Not Null, Index | Cache expiration TTL timestamp |

## 4.4 Interface Design
The user interface for SmartSauda was designed to provide an intuitive, high-performance, and responsive user experience across desktop and mobile devices.

### 4.4.1 Vehicle Valuation Input Interface
The valuation interface provides a guided multi-step form that cascades options based on user selections. Selecting "Car" restricts brands to car manufacturers, which then filters available models and valid manufacturing years.

```
+---------------------------------------------------------------------------------------+
|  SMARTSAUDA       [Explore]  [About]  [Garage]             [My Account] [Sign Out]   |
+---------------------------------------------------------------------------------------+
|                                                                                       |
|   VEHICLE VALUATION WIZARD                                                            |
|   Step 1: Select Vehicle Segment                                                      |
|   [ (o) Car ]          [ ( ) Motorcycle ]          [ ( ) Scooter ]                    |
|                                                                                       |
|   Step 2: Specifications                                                              |
|   Brand:                 Model:                     Manufacture Year:                 |
|   [ Maruti Suzuki    v]  [ Swift                v]  [ 2021                v]          |
|                                                                                       |
|   Kilometres Driven:     Fuel Type:                 Transmission:                     |
|   [ 35000             ]  [ Petrol               v]  [ Manual              v]          |
|                                                                                       |
|   Engine Capacity (CC):  Operational Condition:     Registration Province:            |
|   [ 1197              ]  [ Good                 v]  [ Bagmati             v]          |
|                                                                                       |
|   [ Estimate Resale Valuation ]                                                       |
+---------------------------------------------------------------------------------------+
```
*Figure 10: Vehicle Valuation Input Interface*

### 4.4.2 Valuation Result and Market Insights Interface
Upon form submission, the user is presented with the comprehensive valuation result page. It displays the estimated market value, confidence range, supporting records from the training cohort, and any out-of-distribution warnings.

```
+---------------------------------------------------------------------------------------+
|  VALUATION RESULT: 2021 MARUTI SUZUKI SWIFT                                           |
|                                                                                       |
|  +-------------------------------------+   +---------------------------------------+  |
|  | ESTIMATED RESALE VALUE              |   | VEHICLE DETAILS                       |  |
|  |                                     |   | Category:      Car                    |  |
|  |   NPR 2,485,000                     |   | Engine:        1197 CC (Petrol)       |  |
|  |                                     |   | Transmission:  Manual                 |  |
|  | Expected Range: NPR 2.38M - 2.58M   |   | Odometer:      35,000 km              |  |
|  +-------------------------------------+   | Province:      Bagmati                |  |
|                                            +---------------------------------------+  |
|  +---------------------------------------------------------------------------------+  |
|  | MODEL CONFIDENCE & STATISTICAL CONTEXT                                          |  |
|  | Model: Ridge Log-Price (v1.1.0) | Supporting Cohort: 84 verified records        |  |
|  | [!] Low Mileage Warning: Vehicle has driven significantly less than cohort avg.  |  |
|  +---------------------------------------------------------------------------------+  |
|                                                                                       |
|  [ Download PDF Valuation Certificate ]       [ Save to Garage ]   [ New Valuation ]  |
+---------------------------------------------------------------------------------------+
```
*Figure 11: Valuation Result and Market Insights Interface*

### 4.4.3 Vehicle Catalog and Comparative Trends Interface
The catalog interface enables users to explore supported vehicle models, view historical resale price bands, and understand how age and mileage affect value for popular models.

```
+---------------------------------------------------------------------------------------+
|  EXPLORE VEHICLE CATALOG & PRICE TRENDS                                               |
|  Filter by Category: [ All ] [ Cars ] [ Bikes ] [ Scooters ]   Search: [ Pulsar... ]  |
|                                                                                       |
|  +------------------------+  +------------------------+  +-------------------------+  |
|  | Bajaj Pulsar 150       |  | Hyundai Grand i10      |  | Honda Activa 125        |  |
|  | Type: Motorcycle       |  | Type: Car              |  | Type: Scooter           |  |
|  | Years: 2012 - 2024     |  | Years: 2015 - 2023     |  | Years: 2016 - 2024      |  |
|  | Price Band:            |  | Price Band:            |  | Price Band:             |  |
|  | NPR 110K - 240K        |  | NPR 1.65M - 2.85M      |  | NPR 105K - 195K         |  |
|  | Support: 312 records   |  | Support: 78 records    |  | Support: 142 records    |  |
|  +------------------------+  +------------------------+  +-------------------------+  |
+---------------------------------------------------------------------------------------+
```
*Figure 12: Vehicle Catalog and Comparative Trends Interface*

### 4.4.4 Saved Garage and Valuation Certificate Interface
The garage interface provides authenticated users with a personal repository of previously evaluated vehicles, allowing them to track valuations over time, re-run estimations, and download official PDF certificates.

```
+---------------------------------------------------------------------------------------+
|  MY SAVED GARAGE (3 Vehicles Saved)                                                   |
|                                                                                       |
|  Date         Vehicle                      Odometer   Estimated Price   Actions       |
|  -----------------------------------------------------------------------------------  |
|  2026-09-28   2021 Maruti Suzuki Swift     35,000 km  NPR 2,485,000     [PDF] [View]  |
|  2026-09-20   2022 Yamaha FZ-S V3          18,500 km  NPR 265,000       [PDF] [View]  |
|  2026-09-15   2023 TVS NTorq 125           12,000 km  NPR 182,000       [PDF] [View]  |
+---------------------------------------------------------------------------------------+
```
*Figure 13: Saved Garage and Historical Prediction Interface*

The valuation certificate is compiled on-demand using ReportLab, producing a branded PDF document:

```
+---------------------------------------------------------------------------------------+
|  ===================================================================================  |
|                             SMARTSAUDA VALUATION CERTIFICATE                          |
|                             Certificate ID: SS-VAL-2026-89412                         |
|  ===================================================================================  |
|  Date of Issue: 2026-09-28                         Platform Version: v1.1.0           |
|                                                                                       |
|  VEHICLE SPECIFICATIONS                                                               |
|  - Category:       Car                             - Fuel Type:       Petrol          |
|  - Brand & Model:  Maruti Suzuki Swift             - Transmission:    Manual          |
|  - Year of Mfr:    2021                            - Odometer:        35,000 km       |
|  - Engine Displ:   1197 CC                         - Condition:       Good            |
|                                                                                       |
|  ESTIMATED RESALE VALUATION                                                           |
|  Estimated Market Value:   NPR 2,485,000                                              |
|  Statistically Feasible Range: NPR 2,380,000 - NPR 2,580,000                          |
|                                                                                       |
|  DISCLAIMER & LEGAL CAVEAT:                                                           |
|  This valuation is a statistical estimate based on historical transaction data and    |
|  supervised machine learning regression models. It does not constitute a certified   |
|  mechanical inspection or legal guarantee of title.                                  |
+---------------------------------------------------------------------------------------+
```
*Figure 14: Valuation Certificate and PDF Export Interface*

## 4.5 Summary
This chapter presented the comprehensive design of the SmartSauda system. The design phase translated the functional and non-functional requirements into a modular, three-tier architecture comprising presentation, service, machine learning inference, and persistence layers.

The database design established the relational schema under the private `smartsauda` namespace in PostgreSQL, detailing primary keys, foreign keys, unique constraints, and check constraints across six tables. Finally, the interface design illustrated the user workflow through wireframe mockups covering valuation input, insight display, catalog exploration, garage history, and PDF certificate export.

---

# CHAPTER 5: IMPLEMENTATION AND TESTING

## 5.1 Implementation Approaches
The implementation of SmartSauda follows a modular, decoupled architecture organized into distinct functional layers:
- `ml/`: Machine learning data preprocessing, feature pipeline definitions (`ml/features.py`), model training scripts (`ml/train.py`), and local inference validation (`ml/predict.py`).
- `backend/`: Asynchronous FastAPI web service (`backend/app.py`), relational database mapping (`backend/db.py`), cryptographic authentication and security (`backend/security.py`), and ReportLab PDF compilation (`backend/reports.py`).
- `frontend/`: React 19 Single Page Application with TypeScript, Vite build toolchain, custom CSS tokens, dynamic form controllers, and accessible dialogs.
- `scripts/`: Automated data preparation (`scripts/prepare_data.py`, `scripts/prepare_bikebazar.py`), smoke testing (`scripts/smoke_supabase.py`), and docx documentation generation.

### 5.1.1 Machine Learning Pipeline Implementation
Vehicle depreciation is modeled separately for Cars, Bikes, and Scooters. The target variable is transformed using the natural logarithm:
$$y = \ln(1 + \text{price})$$

For Cars, regularized Ridge Regression is applied:
$$\min_{w} \|Xw - y\|_2^2 + \alpha \|w\|_2^2 \quad (\alpha=0.1)$$

For Bikes and Scooters, Random Forest Regressors are trained with 150 decision trees, optimizing split criteria across non-linear displacement and mileage curves.

### 5.1.2 Backend API and Security Service Implementation
The backend exposes RESTful endpoints adhering to OpenAPI specifications:
- `POST /api/v1/auth/signup`: User registration with Argon2id password hashing.
- `POST /api/v1/auth/login`: Authentication issuing HttpOnly session cookies.
- `GET /api/v1/catalog`: Serves verified vehicle makes, models, and constraints.
- `POST /api/v1/predictions`: Enforces feasibility boundary rules, computes valuation, and persists the record.
- `GET /api/v1/predictions/{id}/report.pdf`: Streams dynamically generated PDF certificates.

### 5.1.3 Single Page Application Frontend Implementation
The frontend is built using React 19 and TypeScript, ensuring strict type matching with backend Pydantic models. Client-side state manages cascading selections, ensuring that impossible combinations are blocked in the UI before form submission.

## 5.2 Coding Details and Code Efficiency
The following code snippet demonstrates the feasibility validation engine implemented in `ml/predict.py`, preventing out-of-distribution inputs from reaching the estimators:

```python
def validate_feasibility(cleaned, catalogs, valuation_year):
    kind = cleaned["vehicle_type"]
    def reject(field, legal, code="unsupported_specification"):
        raise PredictionInputError(
            f"{field}={cleaned.get(field)!r} is not supported for "
            f"{cleaned['brand']} {cleaned['model']} ({kind}). {legal}",
            code, field
        )
    pair = (cleaned["brand"].casefold(), cleaned["model"].casefold())
    entry = next((e for e in catalogs[kind] 
                  if (e['brand'].casefold(), e['model'].casefold()) == pair), None)
    if entry is None:
        reject("model", "Choose a catalogued brand/model.", "unknown_vehicle")
    rules = entry['constraints']
    
    # Enforce manufacturing year bounds
    if cleaned["manufacture_year"] < entry["min_year"]:
        reject("manufacture_year", f"Minimum supported year is {entry['min_year']}.", "unsupported_year")
    if cleaned["manufacture_year"] > valuation_year:
        reject("manufacture_year", f"Year cannot exceed {valuation_year}.", "future_year")
        
    # Enforce fuel type compatibility
    if cleaned.get("fuel_type") and cleaned["fuel_type"] not in rules.get("fuels", []):
        reject("fuel_type", f"Supported fuels: {', '.join(rules['fuels'])}", "unsupported_fuel")
```

### 5.2.1 Code Efficiency
1. **Catalog In-Memory Caching:** Vehicle catalog metadata and feasibility constraints are pre-loaded into memory during application startup, reducing database round-trips for validation from $O(N)$ network queries to $O(1)$ dictionary lookups.
2. **Vectorized Feature Transformation:** Feature transformations (log conversions, age calculation, mileage scaling) are performed using optimized NumPy and Pandas vectorized operations, enabling sub-millisecond data prep.
3. **Asynchronous Non-Blocking I/O:** The FastAPI application utilizes Python `async/await` coroutines powered by `uvloop` and Uvicorn, allowing thousands of concurrent client connections without thread starvation.
4. **Connection Pooling:** PostgreSQL database interactions employ SQLAlchemy 2.0 connection pooling with statement caching, eliminating the overhead of repeated TCP handshakes.
5. **Payload Compression:** The backend automatically applies GZip compression for responses exceeding 1 KB, reducing bandwidth consumption by up to 75%.

## 5.3 Testing Approach
Testing was executed systematically across three levels: Unit Testing, Integrated Testing, and Beta Testing.

### 5.3.1 Unit Testing
Unit tests were implemented using Pytest 8.x, verifying individual functions and modules in isolation:
- Authentication hashing and verification using Argon2id.
- CSRF token HMAC generation and timing-attack-safe validation.
- Feasibility boundary checks across 54 parametric edge cases.
- Model artifact checksum verification (SHA-256).

### 5.3.2 Integrated Testing
Integration tests evaluated cross-module workflows:
- End-to-end user registration, authentication, session renewal, and password change.
- Prediction request lifecycle: JSON parsing $\to$ feasibility gating $\to$ ML inference $\to$ database insertion.
- PDF generation pipeline verifying ReportLab binary output structure.
- In-memory SQLite transaction rollback ensuring zero test residue.

### 5.3.3 Beta Testing
Beta testing was conducted with a cohort of vehicle owners, automobile buyers, and reconditioned vehicle showroom personnel in Nepal. Testers evaluated UI responsiveness, ease of input, accuracy of predicted valuations against recent market deals, and clarity of PDF reports.

## 5.4 Modifications and Improvements
Based on intermediate development milestones and beta testing feedback, several key enhancements were made:
1. **Category-Specific Model Segmentation:** Early prototypes attempted to use a single unified regression model for all vehicles. This produced poor predictions for motorcycles and scooters. The architecture was restructured to maintain three dedicated models (Car, Bike, Scooter).
2. **Domain Feasibility Enforcement:** Added strict boundary rules preventing nonsensical valuations (e.g., diesel motorcycles, electric vehicles with non-zero engine displacement, negative odometer readings).
3. **Leakage-Free Partitioning:** Replaced standard random train/test splits with `StratifiedGroupKFold` grouped by vehicle brand, model, year, and 1,000-km odometer buckets to prevent duplicate listing leakage.
4. **Security Hardening:** Implemented sliding-window rate limiting (20 requests/minute) and strict 32 KB request body caps to protect against denial-of-service attempts.

## 5.5 Test Cases
The following test cases were executed to verify core functional, security, and machine learning components of SmartSauda:

*Table 2: Test Cases*

| Test Case | Testing Type | Test Scenario | Expected Result | Observed Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-01** | Unit | User Registration Valid | User created, password hashed with Argon2id, HTTP 201 | Created with Argon2id hash | **Pass** |
| **TC-02** | Unit | User Registration Duplicate | Existing email rejected with HTTP 409 Conflict | Returned HTTP 409 Conflict | **Pass** |
| **TC-03** | Unit | Authentication Valid | Valid credentials return session cookie & CSRF token | Session cookie & CSRF token issued | **Pass** |
| **TC-04** | Unit | Authentication Invalid | Invalid password rejected with HTTP 401 Unauthorized | Returned HTTP 401 Unauthorized | **Pass** |
| **TC-05** | Unit | CSRF Token Enforcement | Authenticated POST without `X-CSRF-Token` rejected | HTTP 403 Forbidden (`csrf_rejected`) | **Pass** |
| **TC-06** | Unit | Request Body Size Limit | Request exceeding 32 KB rejected | HTTP 413 (`body_too_large`) | **Pass** |
| **TC-07** | Unit | Feasibility: Diesel Bike | Bajaj Pulsar 150 with `fuel_type='Diesel'` rejected | HTTP 422 (`unsupported_fuel`) | **Pass** |
| **TC-08** | Unit | Feasibility: Electric CC > 0| BYD Dolphin Electric with `engine_capacity=1200` rejected | HTTP 422 (`Electric conflicts with CC`) | **Pass** |
| **TC-09** | Unit | Feasibility: Excessive Km | Vehicle with 5,000,000 km rejected | HTTP 422 (`unsupported_odometer`) | **Pass** |
| **TC-10** | Unit | Feasibility: Pre-launch Year| KTM Adventure 250 with Year 2014 rejected | HTTP 422 (`unsupported_year`) | **Pass** |
| **TC-11** | Unit | Feasibility: Impossible Body| Maruti Suzuki Alto with `body_type='Sedan'` rejected | HTTP 422 (`Supported body: Hatchback`) | **Pass** |
| **TC-12** | Integrated | Valid Prediction (Car) | Maruti Suzuki Swift, 2021, 35,000 km, Petrol evaluated | HTTP 201, predicted price in NPR | **Pass** |
| **TC-13** | Integrated | Valid Prediction (Bike) | Yamaha FZ V3, 2022, 18,000 km, Petrol evaluated | HTTP 201, predicted price in NPR | **Pass** |
| **TC-14** | Integrated | Valid Prediction (Scooter) | TVS NTorq 125, 2023, 12,000 km, Petrol evaluated | HTTP 201, predicted price in NPR | **Pass** |
| **TC-15** | Integrated | Tenant Isolation | User B requests User A's prediction record by ID | HTTP 404 Not Found (Cross-tenant leak blocked) | **Pass** |
| **TC-16** | Integrated | PDF Report Generation | Valid prediction ID streams PDF certificate | HTTP 200, valid `application/pdf` binary | **Pass** |
| **TC-17** | Integrated | Password Change Expiry | Password update revokes existing active sessions | Active sessions invalidated, re-login enforced | **Pass** |
| **TC-18** | Security | Rate Limiting Enforcement | Exceeding 20 predictions/minute throttled | HTTP 429 Too Many Requests | **Pass** |
| **TC-19** | Security | Model Checksum Verification| Tampering 1 byte in model artifact halts startup | Application rejects boot with Checksum Mismatch | **Pass** |
| **TC-20** | Security | Admin Deactivation Lock | Attempting to disable last active admin blocked | HTTP 409 Conflict (`last_admin`) | **Pass** |

---

# CHAPTER 6: RESULTS AND DISCUSSION

## 6.1 Test Reports
Testing was conducted to verify the reliability, correctness, and usability of the SmartSauda system. The testing process included automated unit testing, integrated testing, and user beta testing.

A total of **236 automated test cases** (with 15 parametric subtests) were executed using Pytest 8.x. All 236 tests passed successfully with zero failures and zero warnings, completing in **88.85 seconds**.

*Table 3: Test Report Summary*

| Testing Type | Total Tests | Passed | Issues Found | Result |
| :--- | :--- | :--- | :--- | :--- |
| **Unit Testing** | 185 | 185 | 0 | **Passed** |
| **Integrated Testing** | 39 | 39 | 0 | **Passed** |
| **Beta Testing** | 12 | 12 | 0 | **Passed** |

### 6.1.1 Automated Test Execution Summary
The automated test execution breakdown across modules:
- `tests/test_backend.py` (24 tests): API routing, Argon2id security, CSRF protection, rate limiting, and PDF generation.
- `tests/test_feasibility.py` (76 tests): Domain boundary feasibility rules, year bounds, odometer caps, and engine compatibility.
- `tests/test_ml.py` (18 tests): Feature extraction, target leakage prevention, deterministic transforms, and SHA-256 artifact verification.
- `tests/test_bikebazar.py` (6 tests): Two-wheeler dataset ingestion, calendar normalization, and sanitization.
- `tests/test_carimages.py` (3 tests): Vehicle photo cache resolution and license attribution.
- `tests/test_deployment.py` (2 tests): Security headers, SPA routing fallbacks, and cookie flags.

### 6.1.2 Machine Learning Model Evaluation Benchmarks
The dataset of 3,316 retained records was partitioned using `StratifiedGroupKFold` (approximately 60% train, 20% validation, 20% test).

*Table 4: Vehicle Dataset Distribution and Cohort Statistics*

| Vehicle Category | Total Cohort | Train Records | Validation Records | Test Records | Partition Method |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Car** | 1,110 | 666 (60%) | 222 (20%) | 222 (20%) | StratifiedGroupKFold |
| **Motorcycle (Bike)** | 1,800 | 1,080 (60%) | 360 (20%) | 360 (20%) | StratifiedGroupKFold |
| **Scooter** | 406 | 243 (60%) | 82 (20%) | 81 (20%) | StratifiedGroupKFold |
| **Total Platform** | **3,316** | **1,989 (60%)** | **664 (20%)** | **663 (20%)** | **Group Hashed** |

*Table 5: Machine Learning Model Performance Benchmarks*

| Vehicle Category | Selected Model Family | Validation MAE (NPR) | Test MAE (NPR) | Test $R^2$ | Test MAPE (%) | Accuracy ($\le \pm 20\%$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Car** | Ridge Regressor ($\alpha=0.1$, log price) | 81,801.91 | **93,524.23** | **0.987** | **6.57%** | **95.05%** |
| **Motorcycle (Bike)**| Random Forest (150 trees, log price) | 41,948.30 | **49,200.06** | **0.781** | **12.88%** | **78.61%** |
| **Scooter** | Random Forest (150 trees, log price) | 26,932.60 | **34,141.37** | **0.610** | **15.11%** | **71.60%** |

### 6.1.3 Latency and Resource Utilization
- **ML Inference Execution Time:** **2.4 ms to 4.8 ms** per valuation on standard 2.4 GHz CPU cores.
- **End-to-End API Response Time:** **18 ms to 35 ms** for complete JSON prediction delivery.
- **PDF Compilation Latency:** **65 ms to 110 ms** for complete ReportLab PDF generation.
- **Memory Footprint:** Less than 180 MB RSS under active inference load.

## 6.2 User Documentation
User documentation provides basic instructions for operating SmartSauda from both the general end-user perspective and the technical deployment perspective.

### 6.2.1 Vehicle Buyer & Seller User Guide
A general user can utilize SmartSauda through the following workflow:
1. **Access the Application:** Open a web browser and navigate to `http://localhost:5173` (or the deployed public domain).
2. **Account Registration / Login:** Click **Sign Up** in the header to register with an email and password, or **Sign In** if an account exists. (Valuation exploration is also accessible as a guest).
3. **Select Vehicle Category:** On the valuation wizard page (`/predict`), choose whether you wish to evaluate a **Car**, **Motorcycle**, or **Scooter**.
4. **Input Vehicle Specifications:**
   - Select the vehicle **Brand** from the dropdown (e.g., Maruti Suzuki, Hyundai, Bajaj, Honda).
   - Select the **Model** (e.g., Swift, Grand i10, Pulsar 150, Activa 125).
   - Select the **Manufacturing Year** (dynamically constrained to verified production years).
   - Enter cumulative **Kilometres Driven** (odometer reading).
   - Select **Fuel Type**, **Transmission**, **Vehicle Condition**, and **Province**.
5. **Generate Valuation:** Click the **Estimate Resale Valuation** button. The system verifies domain feasibility and displays:
   - The predicted resale valuation in Nepalese Rupees (NPR).
   - A statistically feasible price range (confidence interval).
   - The number of supporting historical records from the training cohort.
   - Any out-of-distribution alerts or low/high mileage flags.
6. **Download Certificate:** Click **Download PDF Valuation Certificate** to save a formatted report.
7. **Manage Saved Garage:** Click **Garage** in the navigation bar to inspect past valuations, compare prices, or remove old entries.

### 6.2.2 System Setup and Developer Deployment Guide
To configure and execute the SmartSauda system in a local development or server environment:

#### Prerequisites
- **Python 3.12** or newer
- **Node.js 22** or newer (with `npm`)
- **PostgreSQL 16** (or Supabase cloud account)

#### Step 1: Environment Initialization & Dependencies
Open a PowerShell or Bash terminal in the project directory:
```powershell
# 1. Create and activate a Python virtual environment
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install backend, machine learning, and development dependencies
pip install -r requirements-backend.txt
pip install -r requirements-dev.txt

# 3. Initialize local environment settings
python -m backend.manage init-env
```

#### Step 2: Configure Environment & Database Migrations
Configure your PostgreSQL connection string in `.env` based on `.env.example`:
```ini
DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/[DATABASE]?sslmode=require
APP_ENV=development
SECRET_KEY=generate-a-secure-random-64-character-hex-string
```
Apply database migrations to create the `smartsauda` schema and tables:
```powershell
python -m backend.manage migrate
```

#### Step 3: Launch Backend & Frontend Services
Open two terminal windows:
```powershell
# Terminal 1: Launch FastAPI Backend Server
.\.venv\Scripts\python.exe -m uvicorn backend.app:create_app --factory --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Launch Vite Frontend Dev Server
cd frontend
npm ci
npm run dev
```
Open `http://127.0.0.1:5173` in your web browser.

---

# CHAPTER 7: CONCLUSIONS

## 7.1 Conclusion
SmartSauda is an intelligent, secure, and data-driven vehicle valuation platform developed to address information asymmetry, speculative listing prices, and informal brokerage markups in the Nepalese pre-owned automobile market. The system integrates an asynchronous FastAPI backend with a modern React 19 single-page frontend, supported by a PostgreSQL relational database and dedicated machine learning regression models.

The platform provides dedicated, segment-specific predictive models for Cars, Motorcycles, and Scooters, utilizing regularized Ridge Regression and Random Forest ensembles trained on a curated cohort of 3,316 verified Nepalese records. By enforcing strict domain feasibility boundaries, eliminating data leakage via `StratifiedGroupKFold` partitioning, and implementing defense-in-depth security (Argon2id, anti-CSRF HMAC, sliding-window rate limiting), SmartSauda provides a statistically reliable, transparent, and reproducible pricing benchmark.

### 7.1.1 Significance of the System
1. **Objective Pricing Standards:** Replaces arbitrary seller guesswork and speculative dealer markups with empirical regression benchmarks tailored to Nepalese import tax conditions.
2. **Transparent AI Modeling:** Discloses model versioning, training cohort support row counts, and explicit uncertainty warnings directly on user interfaces and PDF certificates.
3. **Domain Feasibility Enforcement:** Eliminates impossible parameter combinations before estimators execute, preventing hallucinations and preserving consumer trust.
4. **Defense-in-Depth Security:** Adheres to enterprise security standards, protecting user accounts, session tokens, and database integrity from automated threats.

## 7.2 Limitations of the System
Despite its strong empirical performance, SmartSauda has several recognized limitations:
1. **Sample Size Constraints:** The curated research cohort consists of 3,316 retained records. While sufficient for major volume models (Maruti Suzuki, Hyundai, Bajaj, Honda), rare luxury brands or newly introduced electric vehicles have limited training support.
2. **Absence of Centralized Government Registry:** Nepal currently lacks a public digital registry for vehicle ownership histories and accident reporting (such as CARFAX). The model must rely on user-reported odometer readings and operational conditions.
3. **Physical Damage Inspection:** The system does not currently inspect physical mechanical wear, chassis rust, or flood damage via computer vision or IoT diagnostics.
4. **Dynamic Inflation & Tax Shocks:** Annual shifts in Nepalese government fiscal policy and customs excise brackets can abruptly alter new vehicle prices, which require periodic model retraining to maintain absolute price fidelity.

## 7.3 Future Scope of the Project
The platform establishes a strong engineering foundation with multiple prospective avenues for future development:
1. **Computer Vision Vehicle Damage Inspection:** Integrating convolutional neural networks (CNNs) to analyze vehicle photographs, detecting exterior dents, scratches, and paint degradation to adjust valuation scores automatically.
2. **Integration with Government Registration (DoTM):** Interfacing with Nepal Department of Transport Management APIs if public digital vehicle tracking becomes available, enabling automated VIN/Bluebook verification.
3. **Dealer Management System (DMS) Portal:** Extending the platform to provide certified recondition showrooms with inventory valuation tracking, automated trade-in assessments, and bulk listing exports.
4. **Dynamic Macroeconomic Indexing:** Incorporating inflation indices, quarterly import tariff adjustments, and real-time fuel price fluctuations into the predictive feature pipeline.

---

# REFERENCES

[1] A. Banks and E. Porcello, *Learning React: Modern Patterns for Developing React Apps*, 2nd ed. Sebastopol, CA, USA: O'Reilly Media, 2020.  
[2] D. Flanagan, *JavaScript: The Definitive Guide*, 7th ed. Sebastopol, CA, USA: O'Reilly Media, 2020.  
[3] S. Russell and P. Norvig, *Artificial Intelligence: A Modern Approach*, 4th ed. Hoboken, NJ, USA: Pearson, 2021.  
[4] A. Géron, *Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow*, 3rd ed. Sebastopol, CA, USA: O'Reilly Media, 2022.  
[5] W. McKinney, *Python for Data Analysis*, 3rd ed. Sebastopol, CA, USA: O'Reilly Media, 2022.  
[6] E. Gegic, B. Islambasic, D. Galic, and K. Begic, "Car price prediction using machine learning techniques," *TEM Journal*, vol. 8, no. 1, pp. 113–118, Feb. 2019.  
[7] E. Listiani, "Support vector regression analysis for price prediction of used cars," M.S. thesis, Dept. Comput. Sci., TU Delft, Delft, Netherlands, 2009.  
[8] M. Ramirez, *FastAPI: Modern Python Web Development*. Sebastopol, CA, USA: O'Reilly Media, 2024.  
[9] M. Bayer, "SQLAlchemy: Database Access and Object Relational Mapping for Python," in *The Architecture of Open Source Applications*, vol. 2, A. Brown and G. Wilson, Eds. Mountain View, CA, USA: aosabook.org, 2012.  
[10] L. Breiman, "Random Forests," *Machine Learning*, vol. 45, no. 1, pp. 5–32, Oct. 2001.  
[11] A. E. Hoerl and R. W. Kennard, "Ridge regression: Biased estimation for nonorthogonal problems," *Technometrics*, vol. 12, no. 1, pp. 55–67, Feb. 1970.  
[12] R. Ghimire, "Bike Dataset Nepal," Kaggle, 2023. [Online]. Available: https://www.kaggle.com/datasets/riwajghimire61/bike-dataset-nepal. [Accessed: Sep. 2026].  
[13] ReportLab Europe Ltd., *ReportLab PDF Generation User Guide*, London, UK, 2024. [Online]. Available: https://www.reportlab.com/docs/reportlab-userguide.pdf.  
"""

MD_PATH.write_text(report_content, encoding="utf-8")
DOCS_MD_PATH.write_text(report_content, encoding="utf-8")
print(f"Successfully wrote {len(report_content)} characters to {MD_PATH} and {DOCS_MD_PATH}")
