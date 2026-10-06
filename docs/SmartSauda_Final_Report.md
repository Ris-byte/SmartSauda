# A Project Report

On

Project: ____________________

Title of the Project: SmartSauda

Vehicle Valuation and Resale Estimation System

Submitted by:

Prabin Thanet                    Exam Roll No: ______________
Rishab Magar                     Exam Roll No: ______________
Rajan Shah                       Exam Roll No: ______________

Under the Guidance
of
____________________________

Submitted to the Faculty of ____________________________
________________________________________________
in partial fulfilment of the requirements for

________________________________________________
Semester: ______________    Year: ______________

College / Institution: ______________________________
Affiliated University: ______________________________
Address: ________________________________________

<!-- page -->
# ORIGINAL COPY OF THE APPROVAL

This is to certify that the project report entitled SmartSauda: Vehicle Valuation and Resale Estimation System submitted by:

Prabin Thanet                  Exam Roll No: ______________
Rishab Magar                   Exam Roll No: ______________
Rajan Shah                     Exam Roll No: ______________

to the Department of ______________________________, at ________________________________________________, in partial fulfilment of the requirements for the degree of ________________________________________________, has been examined and approved as the work carried out by the students.

____________________________             Date: ______________
Name: ______________________
Head of Department
Institution: ______________________________________
(Seal / Stamp)

____________________________
External Examiner
Name: ______________________
Date: _______________________

<!-- page -->
# CERTIFICATE OF AUTHENTICATED WORK

We hereby declare that the project entitled SmartSauda: Vehicle Valuation and Resale Estimation System presents our project work. The external materials and software documentation used in the study have been acknowledged in the report.

This report is submitted by the students named below in partial fulfilment of the requirements for ________________________________________________, under the supervision of ________________________________________________.

The work covers the design and implementation of the application, preparation of vehicle data, training and evaluation of prediction models, and integration of the models with a web interface. The limitations of the available data and the resulting estimates are stated in the report.

____________________________
Prabin Thanet
Registration No.: ______________________________

____________________________
Rishab Magar
Registration No.: ______________________________

____________________________
Rajan Shah
Registration No.: ______________________________

Date: _______________________

<!-- page -->
# ROLE AND RESPONSIBILITY FORM

Table: Roles and Responsibility Table

| Phase / Task | Responsibilities | Assigned To |
| --- | --- | --- |
| Backend development | Develop API endpoints, authentication, session handling, input validation, prediction services and PDF report generation. Integrate the trained models with application services. | Prabin Thanet |
| Frontend development | Design the application pages, navigation, account forms, vehicle input form, result display, garage dashboard and prediction history. Connect the interface to the backend API. | Rishab Magar |
| Model training | Prepare vehicle records, define features, create grouped data partitions, compare regression models and export the selected models with evaluation records. | Rajan Shah |
| Database development | Design and maintain the database schema, relationships, catalog records, user records and prediction storage. Support database integration and data consistency. | Rajan Shah |

The responsibilities above describe the primary areas assigned to each project member.

Signatures:

Prabin Thanet: ______________________________

Rishab Magar: _______________________________

Rajan Shah: _________________________________

<!-- page -->
# ABSTRACT

SmartSauda is a web application for estimating the resale value of cars, bikes and scooters in Nepal. It gives users a starting point for discussing a used vehicle's price by applying trained regression models to vehicle details. Users can enter a supported brand and model, manufacture year, distance travelled and other relevant specifications, then save the result in a private account.

The application uses React and TypeScript for the frontend, FastAPI for the backend, and PostgreSQL for persistent storage. The backend validates vehicle details, selects the appropriate model and stores the estimate with its inputs and model version. The interface provides a garage dashboard, searchable prediction history and a downloadable PDF valuation report.

The retained modelling dataset contains 3,316 records: 1,110 cars, 1,800 bikes and 406 scooters. Separate models are trained for each vehicle category. Records with similar identifying attributes are kept in the same data partition to reduce leakage between training and evaluation. Ridge regression is selected for cars, while random forest regression is selected for bikes and scooters. The stored test results show mean absolute errors of NPR 81,801.91, NPR 41,948.30 and NPR 26,932.60 respectively.

These results describe performance on the available historical dataset. They do not establish accuracy for present-day transactions. Listing dates are unavailable, part of the source data has unverified provenance, and the system uses a fixed 2026 reference year for vehicle age. SmartSauda therefore presents an estimate with its limitations, rather than a guaranteed sale price. The project demonstrates how a prediction pipeline, database and web application can be combined into a usable vehicle valuation system.

Keywords: Vehicle valuation, resale price, regression, Nepal, FastAPI, React, PostgreSQL.

<!-- page -->
# ACKNOWLEDGEMENT

We would like to thank our project supervisor, ______________________________, for the guidance and feedback provided during the development of SmartSauda.

We are grateful to the Department of ______________________________ at ________________________________________________ for the opportunity to carry out this project. We also thank our teachers for their suggestions during the preparation of the application and this report.

We acknowledge the developers and maintainers of the open-source software used in the project. Their documentation helped us understand the tools needed for building the interface, handling application requests, maintaining the database and evaluating prediction models.

We also acknowledge Riwaj Ghimire, the publisher of Bike Dataset Nepal, whose dataset is recorded among the project's data sources. The source attribution and declared licence are retained with the project materials [8].

Finally, we thank our families and friends for their support throughout the project.

Prabin Thanet
Rishab Magar
Rajan Shah

<!-- page -->
# TABLE OF CONTENTS
{{CONTENTS_1}}

<!-- page -->
# TABLE OF CONTENTS (CONTINUED)
{{CONTENTS_2}}

<!-- page -->
# TABLE OF FIGURES
{{FIGURES}}

<!-- page -->
# LIST OF ABBREVIATIONS

| Abbreviation | Full Form |
| --- | --- |
| API | Application Programming Interface |
| BHP | Brake Horsepower |
| CC | Cubic Centimetre |
| CORS | Cross-Origin Resource Sharing |
| CSRF | Cross-Site Request Forgery |
| CSS | Cascading Style Sheets |
| DFD | Data Flow Diagram |
| ERD | Entity Relationship Diagram |
| FK | Foreign Key |
| HTML | HyperText Markup Language |
| HTTP | HyperText Transfer Protocol |
| HTTPS | HyperText Transfer Protocol Secure |
| JSON | JavaScript Object Notation |
| JSONB | Binary JSON storage type |
| MAE | Mean Absolute Error |
| ML | Machine Learning |
| NPR | Nepalese Rupee |
| PDF | Portable Document Format |
| PK | Primary Key |
| REST | Representational State Transfer |
| RMSE | Root Mean Squared Error |
| SQL | Structured Query Language |
| UI | User Interface |
| URL | Uniform Resource Locator |

<!-- page -->
# LIST OF TABLES
{{TABLES}}

<!-- page -->
# CHAPTER 1: INTRODUCTION
## 1.1 Background

Buying or selling a used vehicle usually begins with a question about price. A buyer may compare several advertisements, while a seller may rely on the amount originally paid or on advice from a dealer. These approaches can give different answers because vehicles differ in age, usage, condition and specifications. A listed price also does not necessarily represent the amount accepted in a completed transaction.

For a person comparing cars, bikes or scooters in Nepal, it is useful to have a consistent way of relating vehicle details to a price estimate. A calculation based only on vehicle age misses other differences. For example, two vehicles manufactured in the same year may have different odometer readings, engine capacities and model characteristics.

SmartSauda addresses this problem through a web application connected to trained regression models. The user selects a vehicle category and a supported brand and model, enters the relevant details, and receives an estimated resale value in Nepalese rupees. The estimate is saved with the submitted details so that the user can return to it later.

The project covers both the prediction task and the application around it. Data preparation and model evaluation determine how an estimate is produced. Authentication, database storage, validation and interface design determine whether users can enter information, understand the result and manage their saved records.

The available dataset also sets a clear boundary for the project. Its prices are historical, listing dates are missing, and one source has unverified provenance. SmartSauda displays these limitations with the result. Its purpose is to support an initial price discussion, while a purchase decision still requires inspection, ownership checks and consideration of the actual market.

<!-- page -->
## 1.2 Objectives

The main objective is to develop a vehicle resale estimation system that connects trained prediction models with a usable web interface.

The specific objectives are:

- To prepare a consistent dataset for cars, bikes and scooters and retain information about its sources and limitations.
- To compare regression models using separate training, validation and test partitions.
- To accept supported vehicle details and return an estimated price in NPR.
- To provide account access, a private garage, prediction history and downloadable reports.
- To validate inputs and prevent users from accessing another account's saved estimates.
- To communicate the scope and limitations of the estimate alongside the result.

## 1.3 Purpose, Scope, and Applicability
### 1.3.1 Purpose

SmartSauda provides a repeatable starting point for vehicle price comparison. A user can submit a set of details, inspect the result and preserve a copy for later reference. For the project team, the application also brings together data preparation, model training, backend services, database design and frontend development in one system.

### 1.3.2 Scope

The implemented scope includes registration and sign-in, catalog-based vehicle selection, validation, price estimation, saved results, dashboard summaries, history filters, profile management and PDF report download. The model release contains separate estimators for cars, bikes and scooters. Supported combinations and operating limits are obtained from the catalog and model metadata.

<!-- page -->
### 1.3.3 Applicability

The application can assist an individual who wants an indicative value before speaking with a buyer, seller or dealer. It can also be used in an academic setting to demonstrate how a regression pipeline is exposed through an authenticated application.

The estimate does not replace a physical inspection or establish a legally binding valuation. The application does not arrange payments, transfer ownership, publish sale listings or verify a vehicle's accident history. These activities are outside the implemented scope.

## 1.4 Achievements

The project contains a working connection between the interface, API, database and model artifacts. It keeps the prediction inputs, output and model version together, making saved estimates easier to interpret after the original request.

The supplied interface screenshots show the landing page, sign-in screen, garage dashboard, filtered history page and a saved valuation result. The dashboard example contains 19 estimates across all three vehicle categories. These are application records shown in the screenshots, not a count of evaluation participants or a measure of predictive accuracy.

The model release includes partition assignments, held-out predictions and an evaluation file. These artifacts allow the reported model scores to be traced to a specific release. The codebase also contains tests for application behaviour, data preparation, model consistency and input feasibility.

## 1.5 Organization of Report

Chapter 1 introduces the project and its scope. Chapter 2 reviews related approaches and the selected technologies. Chapter 3 presents requirements, planning and conceptual models. Chapter 4 describes the system, database and interface design. Chapter 5 discusses implementation and testing. Chapter 6 presents the stored evaluation results and user documentation. Chapter 7 gives the conclusions, limitations and possible future improvements.

<!-- page -->
# CHAPTER 2: SURVEY OF TECHNOLOGIES
## 2.1 Review of Similar/Relevant Projects

Vehicle price estimation can be approached through manual comparison, fixed depreciation rules or statistical prediction. Each approach answers a slightly different question. Manual comparison shows the prices attached to available vehicles. A depreciation rule provides a repeatable calculation. A regression model learns relationships from a collection of examples.

A comparison of advertisements is useful when the vehicles are similar, but it requires care. Differences in year, model, distance travelled and condition can make two advertisements difficult to compare. Asking prices may also include room for negotiation. The project therefore treats recorded prices as dataset labels, without assuming that they are verified transaction values.

A fixed depreciation method starts with an initial value and reduces it using a rate or schedule. It is easy to explain, but one rule may not describe all vehicle categories or models. SmartSauda instead compares a simple median-price baseline with regression models, then chooses a model separately for each category.

Ridge regression extends a linear model with a penalty on coefficient size [1]. It offers a relatively simple candidate when relationships can be expressed through numerical features and encoded categories. Random forest regression combines multiple decision trees; in the project it provides another way to represent differences between vehicle groups and usage patterns.

The comparison is based on validation error rather than on the complexity of the algorithm. The selected car model is ridge regression with a logarithmic price target. The selected bike and scooter models are random forests with the same target transformation. Final performance is measured on a separate test partition, as described in Chapter 6.

<!-- page -->
## 2.2 Technologies Used

The frontend is written in React and TypeScript. React components provide a structure for reusable interface elements [2]. In SmartSauda, the pages share navigation, form controls, authentication state and common result displays. Vite provides the frontend development and build tooling.

FastAPI provides the backend framework. It supports request handling based on Python type declarations [3]. The project uses Pydantic schemas to describe accepted request fields and validation rules. Keeping these rules on the server is necessary because requests can be submitted independently of the browser form.

PostgreSQL stores accounts, sessions, catalog entries and prediction records. The schema combines ordinary relational columns with JSONB fields for structured specifications and saved result objects. PostgreSQL documents JSONB as a processed representation of JSON that supports indexing [4]. In this project, it allows a result snapshot to retain details that vary between vehicle categories.

The modelling pipeline uses pandas, NumPy and scikit-learn. Feature transformations, missing-value handling and fitted estimators are bundled together. Group-aware splitting keeps related records together when dividing data; StratifiedGroupKFold combines non-overlapping groups with an attempt to preserve label proportions [5]. Here, source labels are used for balancing, not as model inputs.

SQLAlchemy manages database operations, while ReportLab produces the valuation PDF returned by the application. The repository also contains pytest tests for Python components and Playwright tests for browser interactions. These tools address different parts of the system and do not replace evaluation on independent vehicle data.

<!-- page -->
# CHAPTER 3: REQUIREMENTS AND ANALYSIS
## 3.1 Problem Definition

The project problem is to turn incomplete and varied vehicle information into a consistent, explainable estimation workflow. The application must accept only supported inputs, use the correct model, preserve the result, and clearly state what the estimate represents.

A prediction service without validation may accept a vehicle combination outside its intended coverage. An interface without saved records makes it difficult for users to compare previous estimates. A result without the relevant limitations may be mistaken for a current-market appraisal. These concerns shape the application requirements as much as the choice of regression algorithm.

The system also handles private account data. A user should see only the estimates attached to that account. A prediction identifier in a URL must not be enough to retrieve someone else's result or report. Ownership checks are therefore part of the backend requirements.

## 3.2 Requirements Specification

The requirements are divided into functional and non-functional requirements. Functional requirements describe the operations available to users and administrators. Non-functional requirements describe the expected qualities of those operations, including validation, access control, maintainability and understandable results.

The application has three relevant access states: a visitor without a session, an authenticated user and an administrator. Public information and catalog access support the initial journey. Creating and managing saved estimates requires authentication. Administrative account operations require an administrator role.

<!-- page -->
### 3.2.1 Functional Requirements

| ID | Requirement |
| --- | --- |
| FR-01 | Register an account with a display name, email address and password. |
| FR-02 | Sign in, identify the current account and sign out. |
| FR-03 | Retrieve supported vehicle types, brands, models and input constraints. |
| FR-04 | Validate a vehicle request and estimate its price using the matching category model. |
| FR-05 | Save submitted specifications, the result, model version and creation time. |
| FR-06 | Display garage totals, category counts and recent estimates. |
| FR-07 | Search and filter the account's prediction history. |
| FR-08 | Open an owned prediction and download its PDF report. |
| FR-09 | Update a display name and change an account password. |
| FR-10 | Allow an administrator to inspect account statistics and change account active status. |

Table 1: Functional Requirements

The browser provides a guided form, but the server remains responsible for accepting or rejecting a request. For example, a client must not be able to bypass a model-specific year limit by sending the request directly to the API.

The API stores results under the authenticated user's identifier. History, detail and report operations use this relationship when checking access. Administrative privileges do not automatically grant access to another user's private prediction report.

<!-- page -->
### 3.2.2 Non-Functional Requirements

Security: Passwords are stored as hashes. Sessions expire, and their stored representation is a token digest. Authenticated changes require a CSRF token. Production configuration requires secure transport settings. These controls reduce specific risks; they do not by themselves establish that every deployment is secure.

Data integrity: Prediction prices must be positive, account email addresses must be unique, and prediction records must reference an existing user. Database constraints support these rules in addition to request validation.

Usability: The interface should keep vehicle selection, entry of details and interpretation of results understandable. Form feedback should identify the field that needs correction. A saved estimate should remain reachable from both the garage and prediction history.

Reliability: Failure to obtain a remote vehicle image should not prevent the user from receiving a valid estimate. The application includes image fallback behaviour. A failure to load required model artifacts, however, must be treated as a service readiness problem.

Maintainability: Frontend pages, backend services, model code and database migrations are stored separately. Model releases include metadata and checksums so that a change can be associated with the artifacts used to produce it.

Performance: Catalog lookup, filtering and prediction should avoid unnecessary repeated work. Owner-and-time indexes support history queries. No numerical response-time guarantee is claimed here because an acceptance benchmark has not been supplied.

Acceptance response time: ______________
Expected concurrent users: ______________
Deployment availability target: ______________

<!-- page -->
## 3.3 Planning and Scheduling

The work is divided into requirements, data preparation, design, implementation, integration and testing. Model development and application development can proceed in parallel once the prediction request and response formats are agreed. Integration then connects the selected model release to the API and interface.

The table records the main tasks and primary responsibilities. Actual dates and durations are left for completion from the team's project records.

| Phase / Task | Primary Responsibility | Start | Finish |
| --- | --- | --- | --- |
| Backend design and API implementation | Prabin Thanet | ______ | ______ |
| Frontend design and page implementation | Rishab Magar | ______ | ______ |
| Data preparation and model training | Rajan Shah | ______ | ______ |
| Database design and setup | Rajan Shah | ______ | ______ |
| Integration and review | ______________ | ______ | ______ |
| Testing and documentation | ______________ | ______ | ______ |

Table 2: Planning and Scheduling Table

![Figure 1: Project Work Sequence](report-assets/workflow.png)

The sequence represents task dependencies. It does not claim that a particular calendar schedule was followed.

<!-- page -->
## 3.4 Software and Hardware Requirements

The project run instructions specify Python 3.12 and Node.js 22 or newer for setup on another computer. The Python environment must include the pinned backend and modelling dependencies. The frontend dependencies are installed from the package lock file.

| Component | Requirement / Purpose |
| --- | --- |
| Python | Python 3.12; backend, data preparation and model execution |
| Node.js | Version 22 or newer; frontend tooling |
| Database | PostgreSQL connection configured for the application |
| Browser | A browser supporting the application's JavaScript and CSS |
| Model artifacts | Active model manifest, estimators and metadata |
| Network | Database access; external image access where configured |
| Optional deployment tools | Docker and a suitable hosting environment |

Table 3: Software Requirements

The development computer and hosting configuration affect training time, memory use and application capacity. Since the project's hardware measurements were not supplied, they are recorded below as fields for completion.

Processor: ______________________________________
Memory: ________________________________________
Storage: ________________________________________
Operating system: ________________________________
Deployment host: _________________________________

The proposed deployment should be checked with representative requests before setting minimum hardware requirements. A machine that serves an already trained model may need different resources from one used to train several candidate models.

<!-- page -->
## 3.5 Preliminary Product Description

SmartSauda opens with an Explore page that introduces the application and provides an entry point for selecting a vehicle category. The left navigation connects the main areas: vehicle valuation, garage, prediction history and information about the project.

An account is used to keep estimates private. After signing in, the user can start a new estimate, select the supported vehicle details and submit the form. The frontend obtains catalog information from the backend so that available models follow the selected category and brand.

The API validates the request before model execution. It checks broad schema rules, such as numeric type and non-negative distance, and also applies catalog-specific restrictions. The selected model produces a price, while the result includes information about its reference year, fitting support and applicable warnings.

The saved prediction becomes part of the user's garage and history. The result page shows the estimated price, the vehicle details and the limits of the estimate. A PDF report can be downloaded for an owned prediction. This report is a record of the application output, not an independent vehicle inspection certificate.

The administrator has separate account-management operations. This role can inspect account statistics and change whether an account is active. It does not turn the application into a public vehicle marketplace or a transaction-processing service.

The product therefore centres on one complete journey: enter a supported vehicle, receive an estimate, understand its limits and retain the record for later use.

<!-- page -->
## 3.6 Conceptual Models
### 3.6.1 Use Case Diagram

The use case model separates public browsing, account operations and administrative actions. A registered user creates and reviews estimates. An administrator manages account status through restricted operations.

![Figure 2: Use Case Diagram](report-assets/usecase.png)

Sign-in establishes the session needed for private operations. Creating an estimate includes server validation and model execution. Viewing history, opening a result and downloading a report all require ownership checks.

The administrator's account-management role is separate from prediction ownership. The application tests include an explicit check that another account's private prediction remains inaccessible even to an administrator.

<!-- page -->
### 3.6.2 Data Flow Diagram

The data flow model follows a request from the browser to the stored result. The browser supplies vehicle details and receives either validation feedback or a completed prediction. The model artifacts are loaded for inference; they are not trained again for each request.

![Figure 3: Data Flow Diagram](report-assets/dfd.png)

The catalog supplies supported vehicle combinations and their limits. The prediction service transforms accepted fields using the shared feature code, then runs the selected estimator. The database stores a snapshot under the account identifier.

For later retrieval, the service reads only a prediction belonging to the current account. The report operation formats that stored result as a PDF. Keeping retrieval separate from inference avoids silently replacing an old estimate with a newly calculated value.

<!-- page -->
### 3.6.3 Entity Relationship Diagram

The account is the central owner of private application records. One user can have several sessions and several predictions. Each session and prediction belongs to one user.

![Figure 4: Entity Relationship Diagram](report-assets/erd.png)

The catalog, image cache and rate-limit buckets serve the application rather than a single user's history. A prediction stores brand, model and model version as a snapshot; the schema does not define a foreign key from predictions to catalog entries.

This distinction matters when a new model release changes the catalog. A saved prediction still describes the input and model version used at the time it was created. The account relationships are enforced through foreign keys, while catalog identity is constrained by vehicle type, brand, model and model version.

<!-- page -->
### 3.6.4 System Architecture Model

The application has a presentation layer, an API layer, a prediction component and persistent storage. React pages communicate with the FastAPI service. The service handles authentication, validation, database access and report generation.

![Figure 5: System Architecture Model](report-assets/architecture.png)

The prediction component reads the active release selected by the model configuration. Each category has a fitted estimator and corresponding metadata. Database migrations establish the tables required by the service.

Image retrieval is a supporting operation. The project includes local vehicle images and remote image handling, so the price estimate does not depend on a particular external image provider being available.

<!-- page -->
### 3.6.5 Vehicle Valuation Model

Training starts from the retained vehicle records. Cleaning and feature construction produce a consistent input format. Data is divided into grouped training, validation and test partitions before final evaluation.

![Figure 6: Model Training and Selection Workflow](report-assets/training.png)

Candidate configurations are compared using validation MAE in NPR. Tuning takes place within the training data. The selected configuration is fitted on training and validation records together, evaluated on the held-out test partition and exported without fitting on the test records.

The exported estimator includes preprocessing and the inverse target transformation. During a user request, the application applies the same feature definitions and runs prediction only. This keeps training decisions separate from the online estimation workflow.

<!-- page -->
# CHAPTER 4: DESIGN
## 4.1 Introduction

The design links a simple user journey to several internal responsibilities. The frontend controls the order in which information is entered and displayed. The backend controls validation and account access. The model component calculates the estimate, while the database preserves the result and its context.

## 4.2 System Design

The backend is created through an application factory. Configuration determines the database connection, session behaviour, allowed origins and deployment settings. Request schemas define the accepted fields. Model loading is separated from individual requests so that an estimator can be reused.

A successful valuation request follows six steps: identify the account, validate the schema, check the supported vehicle constraints, construct features, run the appropriate estimator and save the result. The response then allows the frontend to display the estimate without reconstructing its meaning from separate requests.

An unsuccessful request returns an error instead of saving a partial prediction. The browser displays the relevant feedback so that the user can correct the entry. The model should not receive a request that has already failed catalog validation.

Account access is checked again when a result is read or downloaded. A previous successful sign-in does not authorise access to every prediction identifier. This design keeps authentication, authorisation and prediction as distinct responsibilities.

The frontend organises the journey into pages for exploration, authentication, prediction, results, dashboard, history and profile. Shared components reduce repetition, while the API client centralises communication with the backend.

<!-- page -->
## 4.3 Database Design

The database uses the private smartsauda schema. The main tables are users, sessions, predictions and catalog. Two additional tables support image caching and rate limiting. The following summary reflects the database migrations.

| Table | Main Fields and Purpose |
| --- | --- |
| users | id (PK), email (unique), display_name, password_hash, role, active, created_at; account identity and status. |
| sessions | token_digest (PK), user_id (FK), expires_at; session ownership and expiry. |
| predictions | id (PK), user_id (FK), vehicle_type, brand, model, model_version, price, specifications, result, image, created_at; saved valuation snapshot. |
| catalog | id (PK), vehicle_type, brand, model, model_version, training_rows, min_year, max_year, constraints; supported inputs and fitting support. |
| image_cache | key (PK), value, expires_at; reusable image metadata. |
| rate_buckets | key (PK), count, expires_at; request counters for rate limiting. |

Table 4: Database Table Summary

The users table restricts roles to User and Admin. The predictions table requires a positive price and references an existing user. Session records are removed through a cascading relationship when their parent user is deleted. Prediction ownership has a foreign key without the same cascading rule.

An index on prediction owner and creation time supports account history queries. Expiry indexes support cleanup of sessions, image cache entries and rate buckets. JSONB fields preserve variable specifications and result data without requiring a new column for every display detail.

<!-- page -->
## 4.4 Interface Design
### 4.4.1 Explore Interface

The Explore page introduces the purpose of the application and presents the main action, Value your vehicle. The navigation remains visible on the left, allowing users to move to the garage, history and project information.

![Figure 7: SmartSauda Explore Interface](../Screenshot 2026-10-01 071139.png)

The supplied screenshot shows category choices for cars, bikes and scooters below the introduction. The large image and heading establish the vehicle context, while the form entry point appears in the same page.

The interface uses a dark background, orange action buttons and lighter text. The page introduces the estimation service and keeps the main valuation action visible alongside the navigation.

### 4.4.2 Authentication Interface

The sign-in page carries the same visual style into the account journey. It pairs the account form with an introductory image and text. The user enters an email address and password before accessing private saved estimates.

<!-- page -->
### 4.4.2 Authentication Interface (Continued)

![Figure 8: Sign-in Page with Application Navigation](../Screenshot 2026-10-01 071159.png)

The first view shows the sign-in area within the application layout. The second view provides a closer view of the complete form, including password visibility control and the link for creating an account.

![Figure 9: Sign-in Form and Account Creation Link](../Screenshot 2026-10-01 071227.png)

The form keeps field labels visible above the inputs. The message below it explains that prediction history remains within the account. This supports the private-garage design used throughout the application.

<!-- page -->
### 4.4.3 Garage Dashboard Interface

The garage dashboard gives the signed-in user an overview of saved estimates. It provides a New estimate action, summary cards and a recent-estimates list.

![Figure 10: Garage Dashboard Header](../Screenshot 2026-10-01 071309.png)

![Figure 11: Garage Summary and Recent Estimates](../Screenshot 2026-10-01 071327.png)

In the supplied account view, the dashboard shows 19 estimates: three cars, fifteen bikes and one scooter. The average estimated value is NPR 3,32,421. These figures summarise that account's saved records and are not statistics about the wider vehicle market.

<!-- page -->
### 4.4.4 Prediction History Interface

The history page provides a list of saved estimates with controls for searching by brand or model, choosing a vehicle type and limiting the date range. A New estimate action remains available above the filters.

![Figure 12: Prediction History and Search Filters](../Screenshot 2026-10-01 071350.png)

Each visible record identifies the vehicle, manufacture year, distance travelled, category, estimate date and price. Opening a record returns the user to its saved result. The history is attached to the current account rather than being a public search service.

The screenshot shows 19 saved results before a narrower filter is applied. The layout places search controls together, followed by the matching records. This arrangement supports repeated use when a user has estimated several vehicles.

<!-- page -->
### 4.4.5 Valuation Result Interface

The result page places the estimated resale value above the supporting details. The supplied example is a Bajaj Pulsar 150 manufactured in 2016 with 99,971 km entered. The displayed estimate is NPR 73,684, using an age of ten years on the fixed 2026 basis.

![Figure 13: Saved Valuation Result and PDF Download](../Screenshot 2026-10-01 071451.png)

The result includes a download action and a visible notice about historical prices and source limitations. The value shown is an example application output, not a verified sale price or a separate test of model accuracy.

## 4.5 Summary

The design connects guided entry, private storage and a result that preserves its context. The database stores the estimate and inputs together, while the interface gives users several ways to return to the same saved record.

<!-- page -->
# CHAPTER 5: IMPLEMENTATION AND TESTING
## 5.1 Implementation Approaches

The implementation is organised into frontend, backend, modelling and data preparation components. The React frontend uses TypeScript types for API data and separates pages from shared components. The FastAPI backend exposes account, catalog, prediction, dashboard and administration operations.

Database setup is handled through migrations. The initial migration creates the application tables and constraints. A later migration adds supported year ranges and structured constraints to the catalog. This allows the server and the frontend to use the same catalog limits.

The model code is kept outside the route definitions. Shared feature construction is used during both training and inference. Each exported release includes fitted estimators, per-category metadata and a manifest. The active-release selector determines which release the application loads.

Authentication uses a server-side session. The browser receives the session token in an HttpOnly cookie, while the database stores its digest. The cookie uses SameSite=Lax and is marked Secure in production. State-changing authenticated requests include a CSRF token derived from the session.

Prediction creation combines the accepted request, model output and account identity in a stored record. The report endpoint retrieves that record, checks ownership and generates a PDF. Image handling supplies a suitable illustration when available and uses fallback behaviour when a remote image cannot be obtained.

The application is therefore implemented as a connected service rather than as a standalone model demonstration. Input handling, saved records and account boundaries are part of the implemented prediction workflow.

<!-- page -->
## 5.2 Coding Details and Code Efficiency

| Component | Implementation Location | Responsibility |
| --- | --- | --- |
| API application | backend/app.py | Routes, request handling and account access checks |
| Request schemas | backend/schemas.py | Field types, accepted values and validation |
| Database models | backend/db.py | Table mappings and database operations |
| Security helpers | backend/security.py | Password hashing, session digests, CSRF and throttling |
| Valuation reports | backend/reports.py | PDF generation for saved predictions |
| Feature construction | ml/features.py | Consistent model input features |
| Model training | ml/train.py | Candidate comparison, tuning and export |
| Model inference | ml/predict.py | Artifact loading, feasibility checks and prediction |
| Frontend pages | frontend/src/pages | Account, valuation, garage and history screens |

Table 5: Implementation Modules

### 5.2.1 Code Efficiency

The design avoids training during a user request. It reuses fitted preprocessing and estimators, so online work consists of validation, feature transformation, prediction and persistence. This also prevents a user's request from altering the trained model.

Database queries use ownership and date information to restrict history results. Catalog lookups supply relevant selections instead of requiring users to type unsupported combinations. The image cache reduces repeated retrieval of the same metadata.

Rate limiting uses database-backed counters in fixed time windows. An atomic update increments the applicable bucket, making the count shared across API workers. Requests beyond the configured limit receive a response indicating when to retry.

<!-- page -->
### 5.2.2 Data Preparation and Feature Construction

The retained cohort has 3,316 rows. The configuration records the removal of four suspect records with a manufacture year of 1980 and the correction of eleven electric scooter engine-capacity values to zero using recorded motor-power evidence. Historical price labels are kept unchanged.

All categories use vehicle age, distance travelled, distance per year and engine capacity. Cars also use owner count and categorical fields for brand, model, region, fuel type, transmission, condition and body type. Bikes use brand and model as categorical inputs. Scooters include motor power in addition to the common numeric features and brand/model categories [9].

Vehicle age is calculated as 2026 minus manufacture year. Distance per year is distance travelled divided by age when age is greater than zero. A zero age does not trigger division by zero; the derived value is treated as missing for preprocessing.

Numeric fields use median imputation followed by standard scaling. Categorical values are normalised, missing categories receive a fixed label and one-hot encoding produces numerical model inputs. The transformations are fitted only on the appropriate fitting partition.

The target transformation uses the natural logarithm of price. Prediction applies the exponential inverse transformation to return NPR values. The saved estimator includes both directions, reducing the risk that an API response accidentally contains a logarithmic value.

Price, source identifiers and audit metadata are excluded from the feature list. Some accepted request fields do not influence every category's estimator. The prediction output reports ignored inputs so that users do not assume those fields changed the estimated value.

<!-- page -->
### 5.2.3 Model Selection and Evaluation Procedure

The grouped partition key combines vehicle category, normalised brand and model, manufacture year and odometer rounded to a 1,000 km bucket. Records with the same key remain together. This reduces the chance that likely repeated listings appear in different partitions, although it does not prove that two records refer to the same physical vehicle.

| Category | Training | Validation | Test | Total |
| --- | --- | --- | --- | --- |
| Car | 666 | 222 | 222 | 1,110 |
| Bike | 1,080 | 360 | 360 | 1,800 |
| Scooter | 243 | 82 | 81 | 406 |
| Total | 1,989 | 664 | 663 | 3,316 |

Table 6: Model Data Partitions

The training code compares a median baseline, ridge regression, random forest regression and gradient boosting regression. Candidate selection uses validation MAE in NPR. Tuning uses grouped folds within the training partition, retaining the earlier winning configuration if tuning worsens validation MAE.

The selected configuration is fitted again using training and validation records together. The test partition is then used for final evaluation. The exported estimator is this fitted model; it is not refitted on the test rows.

MAE is the mean of the absolute differences between recorded and estimated prices. RMSE gives more weight to larger errors. R-squared compares squared prediction error with variation around the mean recorded price. The report also includes median absolute percentage error and the proportion of predictions within 20 percent of their recorded prices.

<!-- page -->
## 5.3 Testing Approach
### 5.3.1 Unit Testing

Unit tests target individual behaviours such as feature construction, input cleaning, duplicate grouping and fitted preprocessing. For example, the feature tests check that vehicle age comes from the explicit reference year and that prediction rows do not alter the imputer statistics or learned categories.

The model tests examine exported artifacts and their associated partition records. They check that approved rows are accounted for and that a duplicate group does not cross data partitions. These checks support the evaluation process but cannot verify the original truth of a price label.

### 5.3.2 Integrated Testing

Backend tests exercise authentication, catalog access, real-model prediction, database persistence and PDF generation together. They also check owner isolation, password changes, account disabling, input errors, request limits and image fallback handling.

Browser tests cover user interactions at the frontend level. They provide a place to check that navigation, forms and result displays remain connected to the API contract. A passing API test alone would not establish that a user can complete the same task through the browser.

### 5.3.3 Beta Testing

Beta testing should ask intended users to complete a small set of tasks: sign in, estimate a supported vehicle, find a saved estimate and download its report. Feedback should record which steps were confusing and whether the limitations were understood.

Participant count: ______________    Test date: ______________
Observed difficulties: ___________________________________
Feedback summary: _____________________________________

<!-- page -->
## 5.4 Modifications and Improvements

The implementation includes feasibility rules in addition to broad field validation. A request may contain a numeric manufacture year and still fall outside the catalog's supported range. The additional check prevents the service from treating every syntactically valid vehicle as supported.

The model pipeline separates sources, groups and features. Source labels are retained for balancing and reporting but excluded from estimation inputs. Grouped splitting reduces overlap between related records, and the stored test predictions provide a record of the final evaluation.

The result retains warnings about historical data, reference year, sparse fitting support and values outside fitting ranges where applicable. This makes the estimate easier to interpret than a price displayed without any context. The warnings do not change the source data into a current-market sample.

Account isolation is enforced on detail, image and report retrieval. Changing a password or disabling an account also affects its sessions. These controls support the privacy of stored estimates across the available user journeys.

The application includes separate liveness and readiness checks. Liveness indicates whether the service responds, while readiness reflects the dependencies needed to serve application work. Deployment configuration also distinguishes development behaviour from production transport requirements.

Further improvements should be assessed through specific acceptance criteria. Proposed changes to prediction accuracy need independent vehicle observations, while interface changes need user feedback. These are different forms of evaluation and should be recorded separately.

<!-- page -->
## 5.5 Test Cases

The following cases describe the expected behaviour to verify during final acceptance. Actual outcomes are left blank for the team's execution record.

| ID | Scenario / Input | Expected Result | Actual / Status |
| --- | --- | --- | --- |
| TC-01 | Register with valid name, email and a password meeting the schema rules. | Account is created; password is stored as a hash. | __________ |
| TC-02 | Register an already-used email. | Duplicate registration is rejected. | __________ |
| TC-03 | Sign in with valid credentials. | Session cookie and account response are returned. | __________ |
| TC-04 | Submit incorrect sign-in credentials. | Generic authentication error; no session is created. | __________ |
| TC-05 | Submit an authenticated change without a valid CSRF token. | Request is rejected. | __________ |
| TC-06 | Request models for a supported category and brand. | Only the matching catalog entries are returned. | __________ |
| TC-07 | Estimate a supported vehicle with valid inputs. | Positive NPR result is saved under the current account. | __________ |
| TC-08 | Enter negative distance or an unsupported model/year combination. | Validation feedback; no prediction is saved. | __________ |

Table 7: Acceptance Test Cases - Accounts and Valuation

Executed by: __________________    Date: __________________

<!-- page -->
## 5.5 Test Cases (Continued)

| ID | Scenario / Input | Expected Result | Actual / Status |
| --- | --- | --- | --- |
| TC-09 | Open another user's prediction identifier. | Private record is not disclosed. | __________ |
| TC-10 | Search history by brand/model, category and dates. | Results are restricted to matching owned predictions. | __________ |
| TC-11 | Download an owned prediction report. | PDF contains the saved vehicle details, estimate and limitations. | __________ |
| TC-12 | Change the account password. | Old credentials cease to work and existing sessions are revoked. | __________ |
| TC-13 | Disable an account through an administrator operation. | Disabled account cannot continue using its sessions. | __________ |
| TC-14 | Make repeated requests beyond the configured limit. | Rate-limit response includes retry information. | __________ |
| TC-15 | Make the remote image source unavailable. | Fallback behaviour preserves the valuation journey. | __________ |
| TC-16 | Load a release with a missing or invalid model artifact. | Service reports a loading/readiness failure. | __________ |

Table 8: Acceptance Test Cases - History and Access Control

For failed cases, record the actual response, relevant input and steps required to reproduce the issue. A screenshot can support the record, but a screenshot alone does not show that all branches of the operation were tested.

Executed by: __________________    Date: __________________

<!-- page -->
# CHAPTER 6: RESULTS AND DISCUSSION
## 6.1 Test Reports
### 6.1.1 Stored Model Evaluation

The figures below are taken from the stored evaluation for model release v1.1.0. All three rows report held-out test results and describe agreement with the dataset's historical labels. Model selection was completed before these test records were evaluated [6].

| Category | Selected Model | Test Rows | MAE (NPR) | R-squared |
| --- | --- | --- | --- | --- |
| Car | Ridge, log price | 222 | 81,801.91 | 0.9866 |
| Bike | Random forest, log price | 360 | 41,948.30 | 0.7809 |
| Scooter | Random forest, log price | 81 | 26,932.60 | 0.6104 |

Table 9: Held-Out Model Test Results

The car model has the highest R-squared within its test partition. This should be interpreted cautiously because all car training records come from the local source with unverified provenance. A strong internal fit does not demonstrate accuracy on an independently collected sample.

Bike and scooter results show larger relative errors. The scooter test set contains only 81 rows, so conclusions about less common models are particularly limited. Absolute errors cannot be compared fairly across categories without also considering their price ranges.

The selected models improve on the category median baselines in stored test MAE. Baseline MAE is approximately NPR 751,396 for cars, NPR 107,281 for bikes and NPR 53,051 for scooters. The improvement shows that the available features contain useful information within this dataset; it does not resolve the source limitations.

<!-- page -->
### 6.1.2 Error Measures and Interpretation

| Category | RMSE (NPR) | Median APE | Within 20% |
| --- | --- | --- | --- |
| Car | 119,711.87 | 6.57% | 95.05% |
| Bike | 68,938.17 | 12.88% | 65.83% |
| Scooter | 41,078.62 | 15.11% | 66.67% |

Table 10: Additional Test Error Measures

RMSE is greater than MAE in each category, indicating that larger individual errors contribute more strongly to the squared-error measure. Median absolute percentage error gives the middle relative error, while the final column records the share of test predictions lying within 20 percent of the recorded price.

The evaluation also records intervals from 1,000 group bootstrap resamples. The 95 percent interval for mean absolute error is NPR 70,748.70 to 93,865.06 for cars, NPR 35,476.78 to 49,200.06 for bikes and NPR 20,364.34 to 34,141.37 for scooters. These intervals describe uncertainty in aggregate MAE. They are not price ranges for individual vehicles.

There is no chronological test partition because listing dates are unavailable. The fixed reference year keeps feature calculation consistent but does not adjust historical prices for current market conditions. Future evaluation should use dated, independently collected records with a clearly stated price basis.

The screenshot of the Bajaj Pulsar result demonstrates how a saved estimate is presented. It does not include a verified actual transaction price, so prediction error for that particular vehicle cannot be calculated from the screenshot.

<!-- page -->
### 6.1.3 Application Test Record

The repository contains tests for the areas listed below. This table reserves space for a signed execution record; it does not infer pass results from the presence of test files.

| Area | Available Test Material | Run Date | Result |
| --- | --- | --- | --- |
| Authentication, persistence and ownership | tests/test_backend.py | ______ | ______ |
| Feature construction and model artifacts | tests/test_ml.py | ______ | ______ |
| Vehicle feasibility and supported bounds | tests/test_feasibility.py | ______ | ______ |
| Dataset preparation | tests/test_prepare_data.py; tests/test_bikebazar.py | ______ | ______ |
| Vehicle images and fallback behaviour | tests/test_carimages.py; tests/test_vehicle_photos.py | ______ | ______ |
| Deployment settings | tests/test_deployment.py | ______ | ______ |
| Browser interaction | frontend/tests/frontend.spec.ts | ______ | ______ |

Table 11: Application Test Report Summary

The supplied screenshots provide interface evidence for exploration, authentication, garage summaries, history and result viewing. They do not establish browser compatibility, load capacity, accessibility compliance or successful completion of every acceptance case.

Final acceptance should record the environment, model version and database setup used. A change in these components may alter the behaviour being evaluated even when the interface appears unchanged.

Test environment: ______________________________________
Model version: _________________________________________
Reviewed by: __________________________________________

<!-- page -->
## 6.2 User Documentation
### 6.2.1 Account and Valuation Guide

1. Open SmartSauda and select Sign in. If an account has not been created, use Create an account and enter the requested details. The registration password must contain between 12 and 128 characters.

2. After signing in, choose Value your vehicle or New estimate. Select Car, Bike or Scooter, followed by a supported brand and model.

3. Enter the manufacture year and distance travelled. Complete the additional fields shown for that category. Use the vehicle's recorded specifications where available rather than guessing a value.

4. Submit the form. If the system reports an unsupported combination or an invalid field, correct the identified entry before submitting again. A missing model in the catalog should not be replaced with a different vehicle merely to obtain a result.

5. Read the estimated NPR value together with the submitted details, reference year and warnings. Check that the vehicle information is correct. Some optional fields may be recorded without influencing a particular category's model.

6. Use Download PDF report to retain a copy of the saved estimate. The document contains the application output and its limitations. It should be considered alongside inspection findings and other information relevant to the vehicle.

If the estimate seems unexpected, first check the selected model, manufacture year, odometer reading and units. A technically valid request can still be unusual compared with the fitting data. The result warnings identify some of these situations, but they cannot detect every error in information entered by a user.

<!-- page -->
### 6.2.2 Garage and History Guide

Open Your garage to see the number of saved estimates, their average value and their distribution across vehicle categories. Select a recent record to inspect its stored result. Use New estimate when starting a separate valuation.

Open Prediction history to search by brand or model. Select a vehicle category or date range when a narrower list is needed, then apply the filters. An empty result after filtering does not necessarily mean records were deleted; review the selected search terms and dates.

Profile settings allow a change to the displayed account name or password. A password change requires the current password. Sign out after using a shared device and avoid sharing session information or downloaded reports containing private details.

### 6.2.3 Local Setup Guide

Create the Python environment and install the project's backend and development requirements. Install frontend packages using npm ci in the frontend directory. Configure the database and other environment settings from the example configuration, then apply the database migrations. The repository's RUN.txt gives the complete setup sequence [7].

Start the backend from the project directory:

`python -m uvicorn backend.app:create_app --factory --host 127.0.0.1 --port 8000`

In a second terminal, run npm run dev from the frontend directory and open the local address shown by Vite. Keep both services running while using the development application. The configured remote database requires network access.

Keep environment secrets outside the report and source-control history. The active model artifacts and their manifest must be present before the prediction service can be used.

<!-- page -->
# CHAPTER 7: CONCLUSIONS
## 7.1 Conclusion

SmartSauda combines vehicle price estimation with the account and storage functions needed to use the estimates in a web application. It accepts supported vehicle information, produces an NPR estimate, preserves the result and makes it available through a garage, history page and PDF report.

The model release uses separate estimators for cars, bikes and scooters. Validation-based selection chooses ridge regression for cars and random forest regression for the two-wheeler categories. Stored test results show improvement over simple median baselines within the retained dataset.

The application also demonstrates the importance of controls around a prediction. Catalog validation limits unsupported combinations. Shared feature construction keeps training and inference consistent. Ownership checks protect saved records. Result warnings explain restrictions that cannot be conveyed by a price alone.

## 7.1.1 Significance of the System

The project provides a practical example of connecting frontend development, backend services, database design and model training. Each part supports the same user journey, from entering vehicle details to revisiting an estimate.

For users, the main value is a consistent starting point for discussion and comparison. For further development, the stored model version, input snapshot and evaluation artifacts provide a basis for checking changes. The system's usefulness for actual transactions still depends on better source verification and independent market evaluation.

<!-- page -->
## 7.2 Limitations of the System

Historical price labels: The model learns from recorded source prices. The system does not automatically adjust those values to current economic or market conditions, and it does not confirm that they are completed transaction prices.

Unverified source provenance: Part of the cohort comes from a local CSV whose collection and calibration methods are not independently verified. All car training records come from that source. High internal accuracy cannot remove this limitation.

Missing listing dates: A chronological evaluation cannot be established from the retained data. Vehicle age is calculated on a fixed 2026 basis for both training and prediction, rather than from a verified listing date.

Limited coverage: Only the supported catalog combinations can be estimated. Some models have few fitting records. A group based on brand, model, year and rounded distance is a heuristic for likely duplicates, not a verified vehicle identifier.

Incomplete physical information: The model cannot inspect a vehicle or confirm hidden faults, accident damage, service history, document status or odometer accuracy. These factors may materially affect a sale price.

Unequal model inputs: Features vary by category. A field present in the request does not necessarily affect every estimator. The result reports unused input fields where applicable.

Limited acceptance evidence: Screenshots show selected interface states. Formal user feedback, deployment capacity measurements and completed acceptance outcomes must be recorded separately. The blank fields in this report provide space for those project-specific records.

<!-- page -->
## 7.3 Future Scope of the Project

The most useful next step is to improve the dataset. Future collection should record listing dates, source permissions, vehicle identifiers where appropriate and whether a price is an asking price or a completed transaction value. Independent checks would make later evaluation more meaningful.

A larger and more balanced sample would improve coverage of less common models, regions and vehicle types. Dated observations would also allow chronological testing, where older records are used for training and later records are reserved for evaluation.

Prediction uncertainty could be developed and evaluated separately from average error. A displayed range would need evidence that it achieves the intended coverage for individual vehicles. The existing bootstrap intervals for MAE are not suitable for this purpose.

Interface improvements could be guided by task-based user feedback. Areas to examine include clarity of field labels, input units, mobile layouts, accessibility and whether users understand the historical-data notice before interpreting a result.

Further deployment work could add measured load targets, recovery exercises and monitoring of unusual request patterns. These changes should be verified in the intended hosting environment instead of being inferred from local development behaviour.

Finally, new model releases should be compared using a stable evaluation procedure. Keeping data versions, partition rules and result artifacts together would make it possible to distinguish a real improvement from a change in the evaluation sample.

<!-- page -->
# REFERENCES

[1] Scikit-learn developers. Linear Models: Ridge Regression and Classification. Official documentation. https://scikit-learn.org/stable/modules/linear_model.html

[2] React contributors. Quick Start. Official React documentation. https://react.dev/learn

[3] FastAPI contributors. FastAPI Documentation. https://fastapi.tiangolo.com/

[4] PostgreSQL Global Development Group. JSON Types. PostgreSQL documentation. https://www.postgresql.org/docs/current/datatype-json.html

[5] Scikit-learn developers. StratifiedGroupKFold. API documentation. https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html

[6] SmartSauda project team. Model Evaluation, Release v1.1.0. Project artifact: reports/phase2/v1.1.0/evaluation.json. Supporting artifacts: split_assignments.csv and test_predictions.csv in the same directory.

[7] SmartSauda project team. Local Setup and Operation Instructions. Project file: RUN.txt. Implementation sources: backend/, frontend/src/, ml/ and backend/sql/.

[8] Ghimire, Riwaj. Bike Dataset Nepal. Dataset attribution retained in data/external/NOTICE.txt. Publisher-declared licence: Apache License 2.0. The notice records the source as https://www.kaggle.com/datasets/riwajghimire61/bike-dataset-nepal.

[9] SmartSauda project team. Model Configuration and Feature Definitions. Project files: ml/config.json and ml/features.py. Source attribution and preprocessing records are retained under data/.

Online documentation access date: ________________________
