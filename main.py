
import logging

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, LOG_LEVEL
from database import init_db
from handlers import (
    start,
    help_command,
    #weekly_command,
    my_reports_command,
    handle_report_message,
)


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
)

logger = logging.getLogger(__name__)


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN در فایل .env تنظیم نشده است."
        )

    init_db()

    app = Application.builder().token(
        TELEGRAM_BOT_TOKEN
    ).build()

    # دستورات اصلی تلگرام
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    #app.add_handler(CommandHandler("weekly", weekly_command))
    app.add_handler(
        CommandHandler("myreports", my_reports_command)
    )

    # تمام پیام‌های متنی عادی، از جمله دکمه‌های کیبورد،
    # فقط از یک مسیر برای تشخیص و پردازش عبور می‌کنند.
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_report_message,
        )
    )

    logger.info("ربات ثبت گزارش آماده اجراست.")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
