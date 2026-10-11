
import json
import re
import time
from datetime import date
from typing import Any

import requests

from config import (
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)


SYSTEM_PROMPT = """
تو یک دستیار هوشمند برای استخراج اطلاعات از گزارش‌های کاری فارسی هستی.

کاربر ممکن است گزارش خود را طبیعی، محاوره‌ای یا با غلط املایی بنویسد.
او را مجبور به استفاده از قالب خاصی نکن.

وظایف:
1. نام ثبت‌کننده را فقط وقتی استخراج کن که کاربر خودش را به‌وضوح معرفی کرده باشد.
2. نام پروژه، همکار یا شخص دیگری را به‌عنوان نام ثبت‌کننده ثبت نکن.
3. اگر نام کاربر مشخص نیست، employee_name را رشته خالی قرار بده.
4. کارهای انجام‌شده را در completed_tasks ثبت کن.
5. کارهای انجام‌نشده را در completed_tasks قرار نده.
6. مشکلات، موانع و دلایل ناتمام ماندن کارها را در problems ثبت کن.
7. اگر مشکلی ذکر نشده، problems آرایه خالی باشد.
8. اگر کار انجام‌شده‌ای ذکر نشده، completed_tasks آرایه خالی باشد.
9. اگر تاریخ در گزارش مشخص نیست، از تاریخ امروز ارائه‌شده استفاده کن.
10. تاریخ را به شکل YYYY-MM-DD برگردان.
11. اطلاعات جعل نکن و موارد تکراری را ادغام کن.
12. توضیحات هر مورد را دقیق و تا حد امکان مختصر بنویس.
13. فقط یک شیء JSON معتبر با چهار کلید زیر خروجی بده.

ساختار خروجی:
{
  "employee_name": "",
  "report_date": "YYYY-MM-DD",
  "completed_tasks": [],
  "problems": []
}
"""


class ExtractionError(Exception):
    """خطا در استخراج اطلاعات گزارش."""


def _clean_json(text: str) -> dict[str, Any]:
    """اعتبارسنجی و پاک‌سازی JSON دریافتی از مدل."""
    text = text.strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ExtractionError(
            "مدل خروجی JSON معتبر برنگرداند."
        ) from exc

    if not isinstance(data, dict):
        raise ExtractionError("ساختار خروجی مدل معتبر نیست.")

    name = data.get("employee_name", "")
    report_date = data.get(
        "report_date",
        date.today().isoformat(),
    )
    tasks = data.get("completed_tasks", [])
    problems = data.get("problems", [])

    if not isinstance(name, str):
        name = ""

    if not isinstance(tasks, list):
        tasks = []

    if not isinstance(problems, list):
        problems = []

    tasks = [
        str(item).strip()
        for item in tasks
        if str(item).strip()
    ]

    problems = [
        str(item).strip()
        for item in problems
        if str(item).strip()
    ]

    try:
        parsed_date = date.fromisoformat(str(report_date))
    except (TypeError, ValueError):
        parsed_date = date.today()

    return {
        "employee_name": name.strip(),
        "report_date": parsed_date.isoformat(),
        "completed_tasks": tasks,
        "problems": problems,
    }


def _extract_with_ollama(
    message: str,
    today: str,
) -> dict[str, Any]:
    """استخراج اطلاعات گزارش با مدل محلی Ollama."""

    url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": (
                    f"تاریخ امروز: {today}\n"
                    f"متن گزارش:\n{message}"
                ),
            },
        ],
        "stream": True,
        "think": False,
        "format": "json",
        "keep_alive": "10m",
        "options": {
            "temperature": 0,
            "num_predict": 384,
            "num_ctx": 2048,
        },
    }

    started_at = time.monotonic()
    content_parts: list[str] = []

    try:
        # در حالت streaming، پاسخ به‌تدریج دریافت می‌شود.
        # Timeout دریافت، به فاصله بین داده‌های دریافتی مربوط است،
        # نه الزاماً به کل زمان پردازش درخواست.
        with requests.post(
            url,
            json=payload,
            timeout=(10, 300),
            stream=True,
        ) as response:
            response.raise_for_status()

            for line in response.iter_lines():
                if not line:
                    continue

                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ExtractionError(
                        "یکی از بخش‌های پاسخ Ollama معتبر نبود."
                    ) from exc

                if not isinstance(chunk, dict):
                    continue

                if chunk.get("error"):
                    raise ExtractionError(
                        f"خطای Ollama: {chunk['error']}"
                    )

                message_data = chunk.get("message", {})

                if isinstance(message_data, dict):
                    part = message_data.get("content", "")
                    if isinstance(part, str) and part:
                        content_parts.append(part)

                if chunk.get("done"):
                    break

    except ExtractionError:
        raise

    except requests.Timeout as exc:
        elapsed = time.monotonic() - started_at
        print(
            f"Ollama timeout after {elapsed:.1f}s: "
            f"{type(exc).__name__}: {exc}"
        )
        raise ExtractionError(
            "زمان انتظار برای پاسخ Ollama به پایان رسید. "
            "مدل ممکن است به دلیل استفاده از CPU یا طولانی بودن "
            "گزارش، بیش از حد کند باشد."
        ) from exc

    except requests.RequestException as exc:
        print(
            "Ollama connection error: "
            f"{type(exc).__name__}: {exc}"
        )
        raise ExtractionError(
            f"خطا در ارتباط با Ollama: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    elapsed = time.monotonic() - started_at
    content = "".join(content_parts).strip()

    print(
        f"Ollama report extraction completed in {elapsed:.1f}s"
    )

    if not content:
        raise ExtractionError(
            "Ollama پاسخ متنی معتبری برنگرداند."
        )

    return _clean_json(content)


def _extract_with_openai(
    message: str,
    today: str,
) -> dict[str, Any]:
    """استخراج اطلاعات گزارش با OpenAI."""

    if not OPENAI_API_KEY:
        raise ExtractionError(
            "OPENAI_API_KEY در فایل .env تنظیم نشده است."
        )

    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        f"تاریخ امروز: {today}\n"
                        f"متن گزارش:\n{message}"
                    ),
                },
            ],
        )

        content = response.choices[0].message.content or "{}"
        return _clean_json(content)

    except ExtractionError:
        raise

    except Exception as exc:
        raise ExtractionError(
            f"خطا در ارتباط با OpenAI: "
            f"{type(exc).__name__}: {exc}"
        ) from exc


def extract_report(message: str) -> dict[str, Any]:
    """انتخاب مدل و استخراج اطلاعات گزارش."""

    today = date.today().isoformat()

    if not isinstance(message, str) or not message.strip():
        raise ExtractionError("متن گزارش خالی است.")

    if LLM_PROVIDER.strip().lower() == "openai":
        data = _extract_with_openai(message, today)
    else:
        data = _extract_with_ollama(message, today)

    if not data.get("report_date"):
        data["report_date"] = today

    return data
