
from telegram import KeyboardButton, ReplyKeyboardMarkup


BUTTON_REGISTER = "📝 ثبت گزارش روزانه"
BUTTON_MY_REPORTS = "📋 پنج گزارش اخیر من"
BUTTON_HELP = "❓ راهنما"


def main_keyboard():
    keyboard = [
        [KeyboardButton(BUTTON_REGISTER)],
        [KeyboardButton(BUTTON_MY_REPORTS)],
        [KeyboardButton(BUTTON_HELP)],
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="گزارش روزانه‌ات را بنویس...",
    )
