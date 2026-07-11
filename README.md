# ICTA Attachées Portal

## Local setup

1. Copy `.env.example` to `.env` and set a unique `SECRET_KEY`.
2. Install dependencies: `python -m pip install -r requirements.txt`
3. Run migrations: `python manage.py migrate`
4. Create an administrator: `python manage.py createsuperuser`
5. Start the app: `python manage.py runserver`

## Deploy to Render

The repository includes `render.yaml`, which provisions a web service and PostgreSQL database.

1. Push this repository to GitHub.
2. In Render, select **New → Blueprint** and select the GitHub repository.
3. Confirm the generated services, then deploy.
4. In the Render web-service environment settings, add `ADMIN_USERNAME`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD`. The next deploy creates this account automatically.
5. Add `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `DEFAULT_FROM_EMAIL` in the Render web-service environment settings if email/password resets are required.

Do not commit `.env`, `db.sqlite3`, uploaded reports, or real email credentials.
