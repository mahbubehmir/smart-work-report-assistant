#os.chdir(r'd:\airoboreport')
import json
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any

from config import DATABASE_PATH


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                employee_name TEXT NOT NULL,
                report_date TEXT NOT NULL,
                completed_tasks TEXT NOT NULL,
                problems TEXT NOT NULL,
                original_message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_reports_date
            ON reports(report_date)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_reports_user_date
            ON reports(telegram_user_id, report_date)
        """)


def save_report(
    telegram_user_id: int,
    employee_name: str,
    report_date: str,
    completed_tasks: list[str],
    problems: list[str],
    original_message: str,
) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO reports
            (telegram_user_id, employee_name, report_date, completed_tasks,
             problems, original_message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                telegram_user_id,
                employee_name,
                report_date,
                json.dumps(completed_tasks, ensure_ascii=False),
                json.dumps(problems, ensure_ascii=False),
                original_message,
                now,
            ),
        )
        return int(cursor.lastrowid)


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "telegram_user_id": row["telegram_user_id"],
        "employee_name": row["employee_name"],
        "report_date": row["report_date"],
        "completed_tasks": json.loads(row["completed_tasks"]),
        "problems": json.loads(row["problems"]),
        "original_message": row["original_message"],
        "created_at": row["created_at"],
    }


def get_weekly_reports(reference_date: date | None = None) -> list[dict[str, Any]]:
    """Returns reports from Monday through Sunday of the week containing reference_date."""
    today = reference_date or date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM reports
               WHERE report_date >= ? AND report_date <= ?
               ORDER BY report_date ASC, id ASC""",
            (week_start.isoformat(), week_end.isoformat()),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]




def get_recent_reports(limit: int = 7) -> list[dict[str, Any]]:
    """دریافت آخرین گزارش‌های ثبت‌شده در سیستم."""
    limit = max(1, min(int(limit), 50))

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM reports
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [_row_to_dict(row) for row in rows]



def get_user_reports(telegram_user_id: int, limit: int = 5) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM reports WHERE telegram_user_id = ?
               ORDER BY report_date DESC, id DESC LIMIT ?""",
            (telegram_user_id, limit),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]
