# Clinova Backend

Backend API for a multi-tenant clinic management system, built with FastAPI and MongoDB.

## Tech Stack

- FastAPI (async API framework)
- Motor (async MongoDB driver)
- Pydantic v2 + pydantic-settings
- JWT auth (python-jose)
- Pandas + OpenPyXL (CSV/XLSX exports)
- Cloudinary (clinic logo uploads)

## Features

- Multi-tenant data isolation using `clinic_id`
- Admin and clinic-user authentication/authorization
- Clinic onboarding with optional auto user creation + welcome email
- Patient registration, search, profile, and visit history
- Visit management with embedded visit summaries on patient records
- HTML template management (clinic + global templates)
- HTML content generation endpoint for printing/PDF flows
- Dashboard analytics (revenue, payment mix, demographics)
- CSV/XLSX exports for patients and bills (visits)
- Clinic self-service settings (profile, password, default template, logo)

## Project Structure

```text
app/
   auth/         # JWT, dependencies, login/admin/password reset routes
   clinics/      # Clinic CRUD + admin stats + logo upload
   patients/     # Patient create/list/search/profile
   visits/       # Visit create/list/delete
   templates/    # Clinic/admin template management
   pdf/          # Render-ready HTML content from visit/template data
   exports/      # CSV/XLSX exports
   dashboard/    # KPI and analytics APIs
   settings/     # Clinic self-service profile/settings APIs
   utils/        # Logger, email sender, pagination, common query params
```

## Requirements

- Python 3.12+
- MongoDB (local or hosted)
- `uv` (recommended) or `pip`

## Quick Start

### 1. Install dependencies

Using `uv`:

```bash
uv sync
```

Using `pip`:

```bash
pip install -r requirement.txt
```

### 2. Configure environment

Create a `.env` file in the project root:

```env
PROJECT_NAME=Clinova
API_V1_STR=/api/v1

MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=clinic_saas_db

SECRET_KEY=replace-with-a-strong-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Optional: Cloudinary (logo uploads)
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# Optional: SMTP (forgot-password + onboarding email)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
```

If SMTP credentials are not set, email sending falls back to console output.

### 3. Run the app

```bash
uv run uvicorn app.main:app --reload
```

Alternative:

```bash
python start.py
```

API docs:

- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health: `http://localhost:8000/health`

## Authentication and Roles

- Roles:
  - `admin`: manage clinics and admin template operations
  - `clinic_user`: clinic operations (patients, visits, templates, dashboard, exports, settings)
- Tokens are returned from login endpoints and also set as HTTP-only cookies.
- Authorization header format: `Authorization: Bearer <access_token>`

Bootstrap admin user:

1. Call `POST /api/v1/auth/create-admin` with email/password.
2. Login with `POST /api/v1/auth/login` or `POST /api/v1/auth/token`.

## API Summary

All routes are prefixed by `/api/v1`.

### Auth (`/auth`)

- `POST /token` - OAuth2-style login
- `POST /login` - JSON login
- `POST /refresh` - refresh access token
- `POST /logout` - clear cookies
- `POST /create-admin` - create initial admin user
- `POST /forgot-password` - reset password + send temporary credentials

### Clinics (`/clinics`) - admin

- `POST /` - create clinic (optionally creates clinic user from clinic email)
- `GET /` - list clinics
- `PATCH /{clinic_id}` - update clinic
- `GET /{clinic_id}/stats` - clinic-level usage/revenue metrics
- `POST /{clinic_id}/upload-logo` - upload clinic logo

### Patients (`/patients`) - clinic/admin

- `POST /` - create patient
- `GET /` - paginated list
- `GET /search?phone=...` - phone search
- `GET /{id}` - get patient by id
- `GET /{id}/profile` - patient + visit timeline + total fees

### Visits (`/visits`) - clinic/admin

- `POST /` - create visit
- `GET /{patient_id}` - list visits for patient
- `DELETE /{visit_id}` - delete visit and sync patient summary fields

### Templates (`/templates`) - clinic/admin

- Clinic routes:
  - `POST /`
  - `GET /` (clinic templates + global templates)
  - `PATCH /{id}`
  - `DELETE /{id}`
- Admin routes:
  - `POST /admin`
  - `GET /admin`
  - `PATCH /admin/{id}`
  - `DELETE /admin/{id}`

### PDF Content (`/pdf`) - clinic/admin

- `GET /content/{visit_id}/{template_id}`

Returns template HTML with placeholders replaced from patient/visit/clinic data.
`template_id` can be `default` to use clinic default template.

### Dashboard (`/dashboard`) - clinic/admin

- `GET /stats` - summary metrics, payment breakdown, monthly and daily revenue, demographics

Supports optional query params: `start_date`, `end_date`.

### Exports (`/export`) - clinic/admin

- `GET /patients?format=csv|xlsx`
- `GET /bills?format=csv|xlsx`

Supports optional query params: `start_date`, `end_date`.

### Settings (`/settings`) - clinic/admin

- `GET /profile`
- `PATCH /profile`
- `POST /upload-logo`
- `POST /change-password`
- `POST /default-template`

## Template Placeholders

The PDF content endpoint supports placeholders in `${var}` and `{{var}}` styles.

| Placeholder                          | Meaning                   |
| ------------------------------------ | ------------------------- |
| `${name}`                            | Patient name              |
| `${phone}`, `${mobile}`              | Phone number              |
| `${age}`                             | Age                       |
| `${gender}`, `${sex}`                | Gender                    |
| `${address}`                         | Address                   |
| `${fees}`                            | Visit fees                |
| `${dr_name}`                         | Doctor name               |
| `${disease}`                         | Disease                   |
| `${diagnosis}`                       | Diagnosis                 |
| `${specialization}`, `${speciality}` | Specialization            |
| `${payment_method}`                  | Payment method            |
| `${date}`                            | Visit date                |
| `${time}`                            | Visit time                |
| `${datetime}`                        | Full datetime             |
| `${medicines}`                       | Comma-separated medicines |
| `${clinic_name}`                     | Clinic name               |
| `${clinic_phone}`                    | Clinic phone              |
| `${clinic_email}`                    | Clinic email              |
| `${clinic_logo}`                     | Clinic logo URL           |
| `${clinic_address}`                  | Clinic address            |

## Notes for Production

- Replace `SECRET_KEY` with a strong secret.
- Consider moving from SHA-256 password hashing to bcrypt/argon2.
- Review CORS origins in `app/main.py` to match your frontend domains.
- Ensure MongoDB backups and index monitoring are configured.

## Deployment

The repository includes `vercel.json` for Vercel Python runtime.

Important:

- Keep Python version at 3.12+ (see `pyproject.toml`).
- Ensure `pyproject.toml` remains valid for `uv` parsing in CI/CD.
