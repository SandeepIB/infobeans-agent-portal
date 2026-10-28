# AgentHub

AgentHub is a Django-based internal application portal that authenticates users through Google Sign-In and presents a curated dashboard of apps they are allowed to access. It is designed for organizations that want a simple launcher experience with access control based on users and groups.

## Features

- Google OAuth login with domain restriction support
- Django authentication with custom user model
- Dashboard of available internal apps
- App access control by user or group
- Active/inactive app visibility
- Redirect-based launch flow for approved applications
- SQLite database for local development

## Tech Stack

- Python 3
- Django 6.1.2
- Google Auth library
- SQLite
- HTML/CSS templates

## Project Structure

```text
.
├── accounts/                  # Authentication and Google login flow
│   ├── migrations/
│   ├── templates/
│   ├── models.py
│   ├── services.py
│   ├── urls.py
│   └── views.py
├── hub/                      # App catalog and launch dashboard
│   ├── migrations/
│   ├── static/
│   ├── templates/
│   ├── models.py
│   ├── urls.py
│   └── views.py
├── agenthub/                 # Django project settings and routing
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── db.sqlite3                # Local development database
├── manage.py
├── requirements.txt
├── home.html.html            # Project landing page placeholder
└── README.md
```

## App Flow

1. User visits the login page.
2. The app validates Google credentials and verifies the email domain if configured.
3. A user is created or updated in the custom `User` model.
4. The user is redirected to the dashboard.
5. The dashboard only displays apps accessible to the user.
6. Clicking an app redirects to its configured launch URL.

## Authentication and Access Model

The project uses a custom user model in `accounts/models.py` and a `hub/models.py` App model that supports:

- `allowed_users`: specific users that can access a given app
- `allowed_groups`: groups whose members can access a given app
- `is_active`: toggles whether an app is live in the portal
- `launch_url`: external URL to open when the app is selected

Users with `is_superuser` can access active apps without explicit entitlement.

## Prerequisites

- Python 3.10+
- pip
- A Google Cloud project with OAuth credentials

## Local Setup

1. Clone the repository and go to the project folder:

```bash
cd poc
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with the following values:

```env
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_ALLOWED_DOMAINS=yourdomain.com
```

5. Apply database migrations:

```bash
python manage.py migrate
```

6. Create an admin user if needed:

```bash
python manage.py createsuperuser
```

7. Run the development server:

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000/ in the browser.

## Google OAuth Setup

To enable Google sign-in:

1. Create a Google Cloud project.
2. Enable the Google Identity Services / OAuth flow.
3. Configure an OAuth client ID.
4. Add the callback URL used by the app, typically:

```text
http://localhost:8000/accounts/google/callback/
```

5. Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and optionally `GOOGLE_ALLOWED_DOMAINS` in your environment.

## Production Notes

This project includes some hardened settings for production, including:

- secure cookies when `DEBUG` is off
- SSL redirect handling
- strict referrer policy
- proxy SSL header support

For production deployment, you should also configure:

- a real secret key
- a secure database backend
- proper `ALLOWED_HOSTS`
- environment-based configuration management
- HTTPS termination and reverse proxy settings

## Useful Commands

Run the app:

```bash
python manage.py runserver
```

Check project status:

```bash
python manage.py check
```

Create migrations after modifying models:

```bash
python manage.py makemigrations
```

Apply migrations:

```bash
python manage.py migrate
```

## License

This project does not currently include a license file. Add one if you plan to distribute it publicly or within an organization.

## Notes

This repository is a small internal portal and is intended to be extended with additional app integrations, RBAC rules, or admin tooling depending on your deployment needs.
