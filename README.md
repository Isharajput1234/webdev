# 🚀 AI-Powered Resume Analyzer & Job Portal

An intelligent recruitment platform built using **Django, MySQL, Machine Learning, and Scikit-Learn** that connects job seekers and employers through AI-driven job recommendations and resume analysis.

---

## 📌 Project Overview

The AI-Powered Resume Analyzer & Job Portal is designed to simplify the recruitment process by automatically analyzing resumes, matching candidates with suitable job opportunities, and providing personalized recommendations.

Unlike traditional job portals that rely on manual searching, this platform uses Machine Learning algorithms to calculate a Match Score between a candidate's profile and job requirements, helping both recruiters and job seekers make faster and smarter decisions.

---

## ✨ Key Features

### 👤 User Management

* User Registration and Login
* Secure Authentication System
* Email-based OTP Verification
* Password Reset Functionality
* Profile Management

### 📄 Resume Analyzer

* Resume Upload Support
* Automatic Resume Parsing
* Skill Extraction
* Experience Analysis
* Education Detection
* Resume Match Scoring

### 🔄 Profile Management

Users can:

* Create Profile
* View Profile
* Update Profile Information
* Verify Account via OTP
* Upload and Update Resume
* Delete Profile Data
* Manage Personal Details

### 💼 Job Portal Features

* Browse Available Jobs
* Search Jobs by Keywords
* Apply for Jobs
* Track Application Status
* Save Relevant Opportunities
* AI-Based Job Recommendations

### 🏢 Employer Features

* Employer Registration
* Post New Jobs
* Update Job Listings
* Delete Job Listings
* Review Applications
* Manage Candidate Status

### 🤖 AI Recommendation Engine

* Resume and Job Description Analysis
* TF-IDF Vectorization
* Cosine Similarity Matching
* Match Score Generation
* Personalized Job Recommendations

### 📧 Automated Notification System

* Email Notifications
* Application Status Updates
* OTP Delivery
* Profile Verification Alerts
* Recommended Job Notifications

---

## 🏗️ System Architecture

The project follows Django's MVT (Model-View-Template) architecture.

### Models (Data Layer)

Managed using Django ORM.

#### Core Models

* User
* JobSeekerProfile
* EmployerProfile
* Resume
* Job
* Application
* OTPVerification

### Views (Business Logic)

#### Function-Based Views

* Registration
* Login
* Logout
* OTP Verification

#### Class-Based Views

* Dashboard
* Job Listings
* Profile Management
* Resume Management

### Templates (Presentation Layer)

Built using:

* HTML5
* CSS3
* Tailwind CSS
* Bootstrap
* JavaScript

---

## 🧠 AI Resume Analyzer Workflow

### Step 1: Resume Upload

Users upload their resumes in PDF format.

### Step 2: Resume Parsing

The system extracts:

* Skills
* Experience
* Education
* Certifications
* Projects

### Step 3: Text Processing

Resume content and job descriptions are converted into machine-readable vectors using:

* TF-IDF Vectorization

### Step 4: Similarity Analysis

Cosine Similarity compares resume content with job descriptions.

### Step 5: Match Score Calculation

Match Score Range:

* 100% → Excellent Match
* 80–99% → Strong Match
* 60–79% → Moderate Match
* Below 60% → Weak Match

### Step 6: Recommendation Generation

The system recommends jobs that best match the candidate’s profile.

---

## ⚙️ Technology Stack

### Frontend

* HTML5
* CSS3
* Tailwind CSS
* Bootstrap
* JavaScript

### Backend

* Python
* Django

### Database

* MySQL

### Machine Learning

* Scikit-Learn
* Pandas
* NumPy

### Resume Processing

* PyPDF2
* pdfplumber

### Email Services

* SMTP
* Django Email Backend

---

## 🔑 OTP Verification System

To ensure account authenticity:

1. User registers an account.
2. A 6-digit OTP is generated.
3. OTP is sent via email.
4. User verifies the OTP.
5. Account is activated.

---

## 📧 Email Automation

Django Signals automate communication:

### Application Updates

When an employer changes application status:

* Pending
* Accepted
* Rejected

The system automatically sends an email notification to the candidate.

---

## 🔐 Security Features

* Django ORM Protection Against SQL Injection
* CSRF Protection
* Secure Password Hashing
* Session Management
* OTP Verification
* Form Validation
* Authentication Middleware

---

## 📂 Project Modules

### Accounts Module

Handles:

* Registration
* Login
* OTP Verification
* Password Management

### Resume Module

Handles:

* Resume Upload
* Resume Update
* Resume Analysis
* Resume Deletion

### Jobs Module

Handles:

* Job Posting
* Job Search
* Job Applications
* Job Management

### Dashboard Module

Provides:

* Personalized Dashboard
* Match Scores
* Application History
* Recommended Jobs

### Notification Module

Handles:

* Emails
* OTP Messages
* Application Alerts

---

## 🚀 Future Enhancements

* AI-Based Skill Gap Analysis
* Resume Improvement Suggestions
* Interview Question Generator
* AI Career Guidance Assistant
* Job Recommendation Notifications
* LinkedIn Profile Integration
* Resume Ranking System
* Chatbot for Career Assistance

---

## 🎯 Project Highlights

✅ Full-Stack Django Application

✅ AI-Powered Resume Analysis

✅ Intelligent Job Recommendation System

✅ Resume Upload, Update, Verify & Delete Features

✅ OTP-Based Email Verification

✅ Automated Email Notifications

✅ Secure Authentication System

✅ Real-World Recruitment Workflow

✅ Machine Learning Integration

---

## 👨‍💻 Conclusion

The AI-Powered Resume Analyzer & Job Portal combines modern web development with machine learning techniques to provide an intelligent recruitment platform. By automating resume analysis, job matching, and candidate recommendations, the system improves recruitment efficiency and helps users discover opportunities that best align with their skills and experience.
