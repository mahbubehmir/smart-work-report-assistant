
from datetime import date

from database import save_report, get_user_reports
from telegram import Update
from telegram.ext import ContextTypes

from services import extract_report, ExtractionError
from keyboards import (
    main_keyboard,
    BUTTON_REGISTER,
    BUTTON_MY_REPORTS,
    BUTTON_HELP,
)


HELP_TEXT = (
    "سلام! 👋\n\n"
    "به دستیار هوشمند ثبت و پیگیری گزارش‌های کاری خوش آمدی.\n\n"
    "گزارش کاری‌ات را با زبان معمولی فارسی بفرست؛ "
    "نیازی به فرم یا قالب خاصی نیست.\n\n"
    "مثال:\n"
    "«من سارا هستم. امروز داشبورد فروش را تکمیل کردم، "
    "اما به علت نداشتن دسترسی به دیتابیس نتوانستم "
    "تست نهایی را انجام بدهم.»\n\n"
    "امکانات ربات:\n"
    "✅ ثبت کارهای انجام‌شده\n"
    "✅ ثبت مشکلات و موانع کاری\n"
    "✅ استخراج نام و تاریخ گزارش\n"
    "📋 نمایش پنج گزارش اخیر خودت\n"
    "❓ راهنمای استفاده\n\n"
    "برای ثبت گزارش جدید، کافی است متن گزارش را بفرستی."
)


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """نمایش پیام شروع ربات."""

    if not update.message:
        return

    await update.message.reply_text(
        HELP_TEXT,
        reply_markup=main_keyboard(),
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """نمایش راهنمای ربات."""

    if not update.message:
        return

    await update.message.reply_text(
        HELP_TEXT,
        reply_markup=main_keyboard(),
    )


async def my_reports_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """نمایش پنج گزارش اخیر کاربر."""

    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id

    try:
        reports = get_user_reports(user_id, limit=5)

    except Exception as exc:
        print(
            f"Get reports error: "
            f"{type(exc).__name__}: {exc}"
        )

        await update.message.reply_text(
            "❌ هنگام دریافت گزارش‌های شما خطایی رخ داد.",
            reply_markup=main_keyboard(),
        )
        return

    if not reports:
        await update.message.reply_text(
            "هنوز گزارشی از طرف شما ثبت نشده است.",
            reply_markup=main_keyboard(),
        )
        return

    lines = ["📋 پنج گزارش اخیر شما:\n"]

    for report in reports:
        tasks = "، ".join(
            report.get("completed_tasks", [])
        ) or "ذکر نشده"

        problems = "، ".join(
            report.get("problems", [])
        ) or "مشکلی ثبت نشده"

        lines.append(
            f"🆔 شماره گزارش: {report['id']}\n"
            f"👤 ثبت‌کننده: "
            f"{report.get('employee_name') or 'ثبت نشده'}\n"
            f"📅 تاریخ: {report['report_date']}\n"
            f"🛠 کارها: {tasks}\n"
            f"⚠️ مشکلات: {problems}"
        )

    await update.message.reply_text(
        "\n\n".join(lines),
        reply_markup=main_keyboard(),
    )


async def handle_report_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """دریافت، پردازش و ذخیره گزارش کاری."""

    if (
        not update.message
        or not update.message.text
        or not update.effective_user
    ):
        return

    message = update.message.text.strip()

    # یکسان‌سازی متن برای تشخیص دکمه‌ها
    def normalize_text(text: str) -> str:
        translation = str.maketrans({
            "ي": "ی",
            "ى": "ی",
            "ك": "ک",
            "ۀ": "ه",
            "ة": "ه",
            "۰": "0",
            "۱": "1",
            "۲": "2",
            "۳": "3",
            "۴": "4",
            "۵": "5",
            "۶": "6",
            "۷": "7",
            "۸": "8",
            "۹": "9",
            "٠": "0",
            "١": "1",
            "٢": "2",
            "٣": "3",
            "٤": "4",
            "٥": "5",
            "٦": "6",
            "٧": "7",
            "٨": "8",
            "٩": "9",
        })

        text = text.translate(translation).casefold()

        # حذف فاصله‌ها، علائم و ایموجی‌ها
        return "".join(
            char for char in text if char.isalnum()
        )

    normalized = normalize_text(message)

    # ۱. دکمه ثبت گزارش روزانه
    if normalized == normalize_text(BUTTON_REGISTER):
        await update.message.reply_text(
            "📝 لطفاً گزارش روزانه‌ات را بنویس و ارسال کن.\n\n"
            "نیازی به قالب خاصی نیست؛ با زبان معمولی بنویس "
            "امروز چه کاری انجام دادی و با چه مشکلاتی "
            "روبه‌رو شدی.\n\n"
            "مثال:\n"
            "«امروز گزارش فروش را آماده کردم، اما برای "
            "اتصال به دیتابیس دسترسی نداشتم.»",
            reply_markup=main_keyboard(),
        )
        return

    # ۲. نمایش پنج گزارش اخیر
    if normalized == normalize_text(BUTTON_MY_REPORTS):
        await my_reports_command(update, context)
        return

    # ۳. نمایش راهنما
    if normalized == normalize_text(BUTTON_HELP):
        await help_command(update, context)
        return

    # از اینجا به بعد، پیام یک گزارش عادی است.
    if len(message) < 8:
        await update.message.reply_text(
            "لطفاً کمی بیشتر توضیح بده؛ مثلاً چه کاری "
            "انجام دادی و آیا مانعی داشتی؟",
            reply_markup=main_keyboard(),
        )
        return

    await update.message.reply_text(
        "⏳ گزارشت را بررسی می‌کنم...",
        reply_markup=main_keyboard(),
    )

    # ۴. استخراج اطلاعات گزارش با هوش مصنوعی
    try:
        # متغیر صحیح message است، نه message_text
        data = extract_report(message)

        # ابتدا نام استخراج‌شده از متن را بررسی کن.
        employee_name = str(
            data.get("employee_name") or ""
        ).strip()

        # اگر نام در متن پیدا نشد، از نام نمایشی
        # حساب تلگرام کاربر استفاده کن.
        if not employee_name:
            user = update.effective_user

            if user:
                profile_name = (
                    user.full_name or ""
                ).strip()

                if profile_name:
                    employee_name = profile_name
                    data["employee_name"] = profile_name

    except ExtractionError as exc:
        print(
            f"Report extraction error: "
            f"{type(exc).__name__}: {exc}"
        )

        await update.message.reply_text(
            "❌ نتوانستم گزارش را پردازش کنم.\n"
            f"جزئیات خطا: {exc}\n\n"
            "لطفاً دوباره تلاش کن.",
            reply_markup=main_keyboard(),
        )
        return

    # ۵. بررسی نهایی نام ثبت‌کننده
    employee_name = str(
        data.get("employee_name") or ""
    ).strip()

    if not employee_name:
        await update.message.reply_text(
            "نام ثبت‌کننده مشخص نشد.\n"
            "لطفاً نامت را در متن گزارش بنویس؛ "
            "مثلاً: «من سارا هستم و امروز گزارش فروش "
            "را آماده کردم.»",
            reply_markup=main_keyboard(),
        )
        return

    completed_tasks = data.get("completed_tasks", [])
    problems = data.get("problems", [])

    # ۶. بررسی وجود فعالیت یا مشکل قابل ثبت
    if not completed_tasks and not problems:
        await update.message.reply_text(
            "از متن، کار انجام‌شده یا مشکل مشخصی "
            "تشخیص داده نشد.\n\n"
            "لطفاً کمی بیشتر درباره فعالیت امروزت توضیح بده.",
            reply_markup=main_keyboard(),
        )
        return

    # ۷. ذخیره گزارش در پایگاه داده
    report_date = (
        data.get("report_date")
        or date.today().isoformat()
    )

    try:
        report_id = save_report(
            telegram_user_id=update.effective_user.id,
            employee_name=employee_name,
            report_date=report_date,
            completed_tasks=completed_tasks,
            problems=problems,
            original_message=message,
        )

    except Exception as exc:
        print(
            f"Report save error: "
            f"{type(exc).__name__}: {exc}"
        )

        await update.message.reply_text(
            "❌ اطلاعات گزارش استخراج شد، اما ذخیره آن "
            "با خطا مواجه شد. لطفاً دوباره تلاش کن.",
            reply_markup=main_keyboard(),
        )
        return

    # ۸. آماده‌سازی اطلاعات برای نمایش به کاربر
    tasks_text = "\n".join(
        f"• {task}" for task in completed_tasks
    ) or "• موردی ثبت نشده"

    problems_text = "\n".join(
        f"• {problem}" for problem in problems
    ) or "• مشکلی گزارش نشده"

    # ۹. نمایش نتیجه ثبت گزارش
    await update.message.reply_text(
        "✅ گزارش با موفقیت ثبت شد.\n\n"
        f"🆔 شماره گزارش: {report_id}\n"
        f"👤 ثبت‌کننده: {employee_name}\n"
        f"📅 تاریخ: {report_date}\n\n"
        f"🛠 کارهای انجام‌شده:\n{tasks_text}\n\n"
        f"⚠️ مشکلات و موانع:\n{problems_text}\n\n"
        "برای ثبت گزارش بعدی، متن جدیدی بفرست.\n"
        "برای مشاهده گزارش‌ها از دکمه‌های پایین استفاده کن.",
        reply_markup=main_keyboard(),
    )
