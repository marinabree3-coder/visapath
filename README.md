# VisaPath — Render-ready MVP

## Deploy on Render
1. Create a GitHub repository named `visapath`.
2. Upload the **contents of this folder**, not this ZIP.
3. Go to https://render.com and sign in with GitHub.
4. Select **New + → Blueprint**.
5. Choose your `visapath` repository.
6. Render will read `render.yaml` and configure the Python service automatically.
7. Click **Apply/Create**.
8. Open the URL Render gives you, such as `https://visapath.onrender.com`.

The configuration uses:
- Free Render web service
- `pip install -r requirements.txt`
- `gunicorn app:app`
- `/health` health check
- Automatically generated `SECRET_KEY`

## Demo consultant
Email: consultant@visapath.local
Password: ChangeMe123!

Change this before real use.

## Important
This is a testing MVP. Payments are simulated, AI document analysis is a stub, SQLite/local file storage are for development only, and visa requirements are not yet connected to a verified official-source database.

Do not upload real passports, IDs, bank statements, or other sensitive client documents to the demo.

## Production work still required
PostgreSQL, encrypted private object storage, real M-Pesa/card payment verification, production AI/document extraction, official-source visa requirements database, authentication/security hardening, notifications, appointment integration, and privacy/legal review.
