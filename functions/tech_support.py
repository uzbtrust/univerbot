import logging
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram import Bot

from states import TechnicalSupport
from keyboards.inline import p_back_to_main
from utils.database import db
from config import ADMIN_GROUP_ID

logger = logging.getLogger(__name__)


async def request_support(call: CallbackQuery, state: FSMContext):
    try:
        user_id = call.from_user.id

        if not db.is_premium_user(user_id):
            await call.answer(
                "Texnik yordam faqat premium foydalanuvchilar uchun mavjud!",
                show_alert=True
            )
            return

        await call.message.delete()
        await call.message.answer(
            "<b>TEXNIK YORDAM</b>\n\n"
            "Assalomu alaykum!\n\n"
            "Sizning xabaringiz to'g'ridan-to'g'ri admin guruhiga yuboriladi.\n"
            "Iltimos muammoyingizni batafsil yozing:\n\n"
            "<i>Masalan:</i>\n"
            "- Post yuklanmayapti\n"
            "- Vaqt noto'g'ri ishlayapti\n"
            "- Kanal qo'sha olmayapman\n\n"
            "Admin javob berishi odatda 10-30 daqiqa ichida.",
            reply_markup=p_back_to_main,
            parse_mode='HTML'
        )
        await state.set_state(TechnicalSupport.WAITING_MESSAGE)

    except Exception as e:
        logger.error(f"Error in request_support: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def process_support_message(message: Message, state: FSMContext, bot: Bot):
    try:
        user_id = message.from_user.id
        user_name = message.from_user.full_name
        username = message.from_user.username or "Yo'q"

        if not db.is_premium_user(user_id):
            await message.answer(
                "Texnik yordam faqat premium foydalanuvchilar uchun mavjud!",
                reply_markup=p_back_to_main
            )
            await state.clear()
            return

        # message.text None bo'lishi mumkin (rasm, stiker va h.k.)
        if not message.text:
            await message.answer(
                "Iltimos muammoyingizni matn shaklida yozing.\n"
                "Rasm yoki stiker yuborish mumkin emas.",
                reply_markup=p_back_to_main
            )
            return

        admin_message = (
            f"<b>TEXNIK YORDAM SO'ROVI</b>\n\n"
            f"Foydalanuvchi: {user_name}\n"
            f"User ID: <code>{user_id}</code>\n"
            f"Username: @{username}\n"
            f"Status: Premium\n\n"
            f"<b>Muammo:</b>\n"
            f"{message.text}\n\n"
            f"Vaqt: {message.date.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        await bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=admin_message,
            parse_mode='HTML'
        )

        await message.answer(
            "<b>Xabar yuborildi!</b>\n\n"
            "Sizning muammoyingiz admin guruhiga yuborildi.\n"
            "Tez orada javob olasiz.\n\n"
            "Sabr qilganingiz uchun rahmat!",
            reply_markup=p_back_to_main,
            parse_mode='HTML'
        )

        await state.clear()
        logger.info(f"Support request from premium user {user_id} sent to admin")

    except Exception as e:
        logger.error(f"Error in process_support_message: {e}", exc_info=True)
        await message.answer(
            "Xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.",
            reply_markup=p_back_to_main
        )
        await state.clear()
