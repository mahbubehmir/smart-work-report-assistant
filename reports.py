
from collections import Counter
from typing import Any

from database import get_recent_reports


def shorten_text(value: Any, max_length: int = 70) -> str:
    """کوتاه کردن متن‌های طولانی برای خوانایی گزارش."""
    text = str(value).strip()

    if len(text) > max_length:
        return text[:max_length - 1].rstrip() + "…"

    return text


def format_items(items: list[str], max_items: int = 2) -> str:
    """نمایش تعداد محدودی از کارها یا مشکلات."""
    if not items:
        return "  • موردی ثبت نشده"

    lines = [
        f"  • {shorten_text(item)}"
        for item in items[:max_items]
        if str(item).strip()
    ]

    remaining = len(items) - max_items

    if remaining > 0:
        lines.append(f"  • و {remaining} مورد دیگر")

    return "\n".join(lines) if lines else "  • موردی ثبت نشده"


def build_weekly_summary() -> str:
    """نمایش جزئیات هفت گزارش اخیر ثبت‌شده در سیستم."""

    reports = get_recent_reports(limit=7)

    if not reports:
        return (
            "📊 گزارش هفتگی\n\n"
            "هنوز گزارشی در سیستم ثبت نشده است."
        )

    lines = [
        "📊 گزارش هفتگی | هفت گزارش اخیر",
        f"📝 تعداد گزارش‌های نمایش‌داده‌شده: {len(reports)}",
        "",
    ]

    problem_counter = Counter()
    total_problem_mentions = 0

    for index, report in enumerate(reports, start=1):
        employee_name = (
            report.get("employee_name") or "نامشخص"
        )
        report_date = report.get("report_date") or "نامشخص"

        tasks = report.get("completed_tasks") or []
        problems = report.get("problems") or []

        lines.extend([
            f"━━━━━━━━━━━━━━",
            f"📋 گزارش {index} | شماره #{report['id']}",
            f"👤 ثبت‌کننده: {shorten_text(employee_name, 60)}",
            f"📅 تاریخ: {report_date}",
            "🛠 کارهای انجام‌شده:",
            format_items(tasks),
            "⚠️ مشکلات و موانع:",
            format_items(problems),
            "",
        ])

        for problem in problems:
            normalized = " ".join(str(problem).casefold().split())

            if normalized:
                problem_counter[normalized] += 1
                total_problem_mentions += 1

    lines.extend([
        "━━━━━━━━━━━━━━",
        "📈 جمع‌بندی هفت گزارش اخیر",
        f"📝 تعداد گزارش‌ها: {len(reports)}",
        f"⚠️ مجموع موارد مشکل ثبت‌شده: {total_problem_mentions}",
    ])

    if problem_counter:
        most_common_problem, count = problem_counter.most_common(1)[0]

        lines.append(
            "🔴 پرتکرارترین مشکل: "
            f"{shorten_text(most_common_problem, 100)} "
            f"({count} بار)"
        )
    else:
        lines.append("✅ در این گزارش‌ها مشکلی ثبت نشده است.")

    return "\n".join(lines)
