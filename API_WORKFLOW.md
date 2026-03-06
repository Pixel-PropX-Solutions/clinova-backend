# Medical Dashboard Backend - API Workflow Guide

This document outlines the complete end-to-end workflow for the Clinic Management SaaS API. It describes the sequence of API calls needed to navigate through the entire system, from clinic creation to generating bills and PDFs.

---

## 🏗️ 1. Initial Setup & SuperAdmin

Before clinic users can use the system, an `admin` must create the clinic and initial users.

_Note: In this boilerplate, you may need to insert the first `admin` user directly into the MongoDB `users` collection or create a seed script._

### Create a Clinic (Admin Only)

- **Endpoint:** `POST /api/v1/clinics/`
- **Auth required:** `admin` JWT Token
- **Payload:**
   ```json
   {
      "name": "Healthy Life Clinic",
      "phone": "9876543210",
      "email": "contact@healthylife.com",
      "plan": "premium"
   }
   ```
- **Action:** Creates a new tenant (`clinic_id`) in the system.

---

## 🔐 2. Authentication

Clinic staff need to authenticate to receive a JWT access token, which must be passed in the `Authorization: Bearer <token>` header for all subsequent requests.

### Login

- **Endpoint:** `POST /api/v1/auth/token`
- **Payload (Form Data):**
   - `username`: "dr_smith"
   - `password`: "securepassword"
- **Returns:** Let's say we receive an `access_token`. This token encodes the user's `clinic_id`, isolating all their data.

---

## ⚙️ 3. Setup Clinic Master Data

Once logged in, the clinic user must set up their offerings and templates.

### A. Create Services

Doctors offer various services (e.g., Consultation, X-Ray, Blood Test).

- **Endpoint:** `POST /api/v1/services/`
- **Auth required:** `clinic_user`
- **Payload:**
   ```json
   {
      "service_name": "General Consultation",
      "price": 500.0,
      "active": true
   }
   ```

### B. Create HTML Templates for PDF

The system uses Playwright to render HTML into PDFs. Clinics must define their templates.

- **Endpoint:** `POST /api/v1/templates/`
- **Auth required:** `clinic_user`
- **Payload:**
   ```json
   {
      "template_name": "Standard Invoice",
      "template_type": "invoice",
      "html_content": "<h1>{{clinic_name}}</h1><h2>Invoice for {{patient_name}}</h2><p>Total: ${{total}}</p><table>{{services}}</table>"
   }
   ```
   _(Available types: `invoice`, `medical_parchi`, `receipt`)_

---

## 👩‍⚕️ 4. Daily Clinic Operations (The Core Flow)

This is the standard day-to-day workflow when a patient walks into the clinic.

### Step 1: Register or Search Patient

When a patient arrives, the receptionist searches by phone number. If not found, they register the patient.

- **Search Endpoint:** `GET /api/v1/patients/search?phone=9876`
- **Create Endpoint:** `POST /api/v1/patients/`
- **Payload:**
   ```json
   {
      "name": "John Doe",
      "phone": "9876543210",
      "gender": "Male",
      "age": 45,
      "notes": "Allergic to penicillin"
   }
   ```
- **Returns:** Obtains `patient_id`.

### Step 2: Create a Medical Visit (Parchi)

The doctor examines the patient and generates a visit record.

- **Endpoint:** `POST /api/v1/visits/`
- **Payload:**
   ```json
   {
      "patient_id": "<patient_id_here>",
      "doctor_notes": "Patient complains of headache and fever.",
      "diagnosis": "Viral Fever",
      "medicines": ["Paracetamol 500mg (1-1-1)", "Vitamin C"],
      "services_used": [
         {
            "service_id": "<service_id_here>",
            "service_name": "General Consultation",
            "price": 500.0
         }
      ]
   }
   ```
- **Returns:** Obtains `visit_id`.
- **Side-effect:** Auto-increments the patient's `visit_count` and updates `last_visit_date`.

### Step 3: Schedule a Follow-up (Optional)

If the doctor wants to see the patient again next week.

- **Endpoint:** `POST /api/v1/followups/`
- **Payload:**
   ```json
   {
      "patient_id": "<patient_id_here>",
      "next_visit_date": "2024-12-01T10:00:00Z",
      "notes": "Check fever status"
   }
   ```

### Step 4: Generate Bill / Invoice

The receptionist creates a financial bill linking the visit and the services rendered.

- **Endpoint:** `POST /api/v1/bills/`
- **Payload:**
   ```json
   {
      "patient_id": "<patient_id_here>",
      "visit_id": "<visit_id_here>",
      "payment_mode": "upi",
      "services": [
         {
            "service_id": "<service_id_here>",
            "service_name": "General Consultation",
            "price": 500.0,
            "quantity": 1
         }
      ]
   }
   ```
- **Returns:** Obtains `bill_id`.
  _(Note: `total_amount` must NOT be passed in the payload. It is strictly auto-calculated by the backend server for security)._

---

## 🖨️ 5. Printing & PDF Generation

Instantly generate printable PDFs for the patient to take home.

### Print Medical Parchi (Prescription)

- **Endpoint:** `GET /api/v1/pdf/parchi/{visit_id}`
- **Action:** Fetches the `medical_parchi` HTML template, injects diagnosis/medicines, and returns an 80mm thermal receipt PDF file.

### Print Invoice

- **Endpoint:** `GET /api/v1/pdf/bill/{bill_id}`
- **Action:** Fetches the `invoice` HTML template, injects bill totals and services, and returns an A4 PDF file.

---

## 📊 6. Analytics & Administrative

At the end of the day or month, the clinic owner reviews performance.

### View Daily Dashboard

- **Endpoint:** `GET /api/v1/dashboard/stats`
- **Returns:** Aggregated metrics for _today_:
   ```json
   {
      "patients_today": 12,
      "total_revenue": 6500.0,
      "repeat_patients": 45,
      "total_visits": 15
   }
   ```

### Export Data (Excel / CSV)

Download structural data for accounting or offline backups.

- **Export Patients:** `GET /api/v1/export/patients?format=xlsx` (or `csv`)
- **Export Bills:** `GET /api/v1/export/bills?format=csv`
- **Action:** Streams a downloadable Pandas-generated Excel/CSV file directly to the browser.
