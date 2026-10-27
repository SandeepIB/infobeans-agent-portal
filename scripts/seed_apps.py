"""Seed initial application records into the database."""
from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.database import db_session
from app.models.application import Application

APPS = [
    {
        "slug": "ppt-validator",
        "name": "Proposal Validator",
        "description": "Review presentations and materials for compliance with InfoBeans brand guidelines.",
        "route_path": "/ppt-validator/app",
        "icon_svg": '<path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6z"/><path d="M9 12l2 2 4-4"/>',
        "is_active": True,
    },
    {
        "slug": "case-study-creation",
        "name": "Case Study Creation",
        "description": "Accelerate the creation of structured and compelling project case studies.",
        "route_path": "",
        "icon_svg": '<path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5M9 13h7M9 17h5"/>',
        "is_active": True,
    },
    {
        "slug": "client-account-analysis",
        "name": "Client and Account Analysis",
        "description": "Consolidate relevant information to provide a comprehensive overview of clients and accounts.",
        "route_path": "",
        "icon_svg": '<path d="M4 20V9l8-5 8 5v11"/><path d="M9 20v-6h6v6M4 20h16"/>',
        "is_active": True,
    },
    {
        "slug": "stakeholder-analysis",
        "name": "Stakeholder Analysis",
        "description": "Help customer-facing teams understand key stakeholders, their interests and priorities.",
        "route_path": "",
        "icon_svg": '<circle cx="8" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M2.5 20c0-3.5 2.5-6 5.5-6s5.5 2.5 5.5 6M15 14.5c3 0 6 1.5 6 5.5"/>',
        "is_active": True,
    },
]


def main():
    with db_session() as db:
        for app_data in APPS:
            existing = db.query(Application).filter(Application.slug == app_data["slug"]).first()
            if existing:
                print(f"  Skip (exists): {app_data['slug']}")
                continue
            app = Application(**app_data)
            db.add(app)
            print(f"  Created: {app_data['slug']}")
    print("Done.")


if __name__ == "__main__":
    main()
