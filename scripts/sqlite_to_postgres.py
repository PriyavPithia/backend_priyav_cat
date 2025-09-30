#!/usr/bin/env python3
import os
import sys
import argparse
from typing import List, Type

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Allow imports from src
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


def normalize_pg_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://") and "+" not in url:
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def build_engine(url: str):
    return create_engine(url, pool_pre_ping=True)


def get_models_in_dependency_order() -> List[Type]:
    # Parents before children (so FKs resolve). Adjust if you add more models.
    from src.models import (
        Office,
        SessionSettings,
        User,
        ClientDetails,
        Case,
        Debt,
        Asset,
        Income,
        Expenditure,
        FileUpload,
        Notification,
        AuditLog,
    )
    return [Office, SessionSettings, User, ClientDetails, Case, Debt, Asset, Income, Expenditure, FileUpload, Notification, AuditLog]


def table_name(model: Type) -> str:
    return model.__table__.name


def copy_table(src_session, dst_session, model: Type):
    total_src = src_session.query(model).count()
    total_dst = dst_session.query(model).count()
    if total_src == 0:
        print(f"- {table_name(model)}: nothing to copy (source empty)")
        return
    if total_dst > 0:
        print(f"! {table_name(model)}: destination not empty ({total_dst} rows); skipping")
        return

    print(f"→ Copying {table_name(model)}: {total_src} rows…")

    # Stream in batches to avoid memory spikes
    batch_size = 500
    offset = 0
    while True:
        rows = (
            src_session.query(model)
            .order_by(model.__mapper__.primary_key[0])
            .offset(offset)
            .limit(batch_size)
            .all()
        )
        if not rows:
            break

        # Recreate objects preserving primary keys
        clones = []
        for row in rows:
            data = {}
            for col in model.__table__.columns:
                data[col.name] = getattr(row, col.name)
            clones.append(model(**data))

        dst_session.bulk_save_objects(clones, preserve_order=True)
        dst_session.commit()
        offset += len(rows)
        print(f"  - inserted {offset}/{total_src}")

    print(f"✓ {table_name(model)} done")


def disable_triggers_and_constraints(dst_engine):
    # Best-effort: disable constraints to ease FK ordering hiccups
    with dst_engine.begin() as conn:
        try:
            conn.execute(text("SET session_replication_role = 'replica';"))
        except Exception:
            pass


def enable_triggers_and_constraints(dst_engine):
    with dst_engine.begin() as conn:
        try:
            conn.execute(text("SET session_replication_role = 'origin';"))
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Migrate data from SQLite to PostgreSQL")
    parser.add_argument(
        "--sqlite-path",
        default=os.path.join(os.path.dirname(PROJECT_ROOT), "ca_tadley_debt_tool.db"),
        help="Path to the source SQLite .db file",
    )
    parser.add_argument(
        "--target-url",
        default=None,
        help="Target PostgreSQL DATABASE_URL (overrides env if provided)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Proceed even if destination tables are not empty (will append)",
    )

    args = parser.parse_args()

    # Build URLs
    src_url = f"sqlite:///{args.sqlite_path}"
    dst_url = normalize_pg_url(args.target_url or os.getenv("DATABASE_URL", ""))
    if not dst_url:
        raise SystemExit("Please provide --target-url or set DATABASE_URL to a valid Postgres URL")

    print("Source (SQLite):", src_url)
    print("Target (Postgres):", dst_url)

    # Important: ensure imports that evaluate settings.database_url happen with a safe value
    os.environ["DATABASE_URL"] = src_url
    # Now import settings and models
    from src.config.settings import settings  # noqa: F401
    from src.models import Base  # noqa: F401

    src_engine = build_engine(src_url)
    dst_engine = build_engine(dst_url)

    # Ensure destination has tables using destination engine
    print("Ensuring destination tables exist…")
    from src.models import Base as ModelsBase  # re-import to get metadata
    ModelsBase.metadata.create_all(bind=dst_engine)

    SrcSession = sessionmaker(bind=src_engine, autoflush=False, autocommit=False)
    DstSession = sessionmaker(bind=dst_engine, autoflush=False, autocommit=False)

    src_session = SrcSession()
    dst_session = DstSession()

    try:
        disable_triggers_and_constraints(dst_engine)

        for model in get_models_in_dependency_order():
            if not args.force:
                # If destination has any rows, skip table
                dst_count = dst_session.query(model).count()
                if dst_count > 0:
                    print(f"! Skipping {table_name(model)} (destination not empty: {dst_count})")
                    continue
            copy_table(src_session, dst_session, model)

        enable_triggers_and_constraints(dst_engine)
        print("\nAll done. Verify row counts on Postgres.")

    except Exception as exc:
        dst_session.rollback()
        print(f"ERROR: {exc}")
        raise
    finally:
        src_session.close()
        dst_session.close()


if __name__ == "__main__":
    main()
