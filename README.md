# VisaPath — Full-stack MVP

A runnable Flask + SQLite prototype for the VisaPath global visa consultation platform.

## Included
- Public international-facing website
- Free pre-assessment
- User registration/login
- Paid-assessment workflow (payment is MOCKED)
- Client dashboard
- Secure-ish server-side document upload with extension/size controls
- Document classification/review stub ready to replace with an AI provider
- Human consultant portal
- Client/consultant messaging
- USD pricing + local currency display
- Company profile identifying the business as Kenya-based
- Health check endpoint

## Run locally
1. Install Python 3.10+
2. `python -m venv .venv`
3. Activate it
4. `pip install -r requirements.txt`
5. `python app.py`
6. Open http://localhost:5000

Demo consultant:
- Email: consultant@visapath.local
- Password: ChangeMe123!

Change the demo password and SECRET_KEY before any real deployment.

## Production integrations still required
- Real payment provider (M-Pesa/card) with server-to-server webhook verification
- Production database (PostgreSQL recommended)
- Object storage with encryption + signed URLs
- Authentication hardening, CSRF protection, rate limiting, audit logging
- AI provider integration for document extraction/analysis
- A curated visa requirements database with official-source URLs and verification dates
- Email/SMS/WhatsApp provider
- Calendar/video consultation integration
- Business/legal/privacy review for the jurisdictions served

## Safety/accuracy
The AI should provide preliminary guidance and document-readiness analysis, never guarantee approval or impersonate immigration authorities. Requirements must be sourced from current official immigration authorities and reviewed when changed.
