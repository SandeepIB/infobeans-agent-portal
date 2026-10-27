"""Create or promote a user to administrator.

Usage:
    python scripts/create_admin.py user@infobeans.com
    python scripts/create_admin.py user@infobeans.com --name "First Last"
"""
from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Create or promote admin user")
    parser.add_argument("email", help="Email address of the admin user")
    parser.add_argument("--name", help="Display name", default=None)
    args = parser.parse_args()

    email = args.email.strip().lower()

    from app.database import db_session
    from app.models.user import User

    with db_session() as db:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.is_admin = True
            user.is_active = True
            if args.name:
                user.display_name = args.name
            print(f"Promoted existing user to admin: {email}")
        else:
            user = User(
                email=email,
                display_name=args.name or email.split("@")[0].replace(".", " ").title(),
                is_active=True,
                is_admin=True,
            )
            db.add(user)
            print(f"Created admin user: {email}")
    print("Done. The user must sign in via Google OAuth before the session is created.")


if __name__ == "__main__":
    main()
