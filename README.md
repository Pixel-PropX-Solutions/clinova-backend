# Clinic Management SaaS Backend

Production-ready backend application for a multi-tenant Clinic Management SaaS built with FastAPI and MongoDB.

## Requirements

- Python 3.11+
- uv
- MongoDB

## Setup Instructions

1. Clone the repository
2. From the project root, synchronize dependencies using `uv`:
   ```bash
   uv sync
   ```
3. Install Playwright browsers for HTML to PDF generation:
   ```bash
   uv run playwright install chromium
   ```

## Configuration

The application uses `pydantic-settings` to manage configuration parameters. You can set the following environment variables (or create a `.env` file in the root):

- `MONGODB_URL`: Default is `mongodb://localhost:27017`
- `DATABASE_NAME`: Default is `clinic_saas_db`
- `SECRET_KEY`: Used for JWT signing.

## Running the Server

Start the application with Uvicorn:

```bash
uv run uvicorn app.main:app --reload
```

## API Documentation

Once the server is running, visit:

- Swagger UI: `http://localhost:8000/docs`

## Initializing Data

Create your first admin user in MongoDB directly, or write a quick seeding script. Then you can use `/api/v1/auth/token` to login and use `/api/v1/clinics` to manage clinic accounts!







Variable	Value
${name}	Patient name
${phone} / ${mobile}	Phone number
${age}	Age
${gender} / ${sex}	Gender
${address}	Address
${fees}	Visit fees
${dr_name}	Doctor name
${disease}	Disease
${diagnosis}	Diagnosis
${specialization} / ${speciality}	Specialization
${payment_method}	Payment method
${date}	Visit date
${time}	Visit time
${datetime}	Full datetime
${medicines}	Comma-separated medicines
${clinic_name}	Clinic name
${clinic_phone}	Clinic phone
${clinic_email}	Clinic email