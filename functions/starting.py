import logging
from aiogram.types import Message, CallbackQuery

from utils.database import db
from keyboards.inline import non_premium, premium, superadmin_main, superadmin_premium_main
from config import STICKERS, MESSAGES, WEEKLY_PRICE, DAY15_PRICE, MONTHLY_PRICE

logger = logging.getLogger(__name__)


async def greating(event: Message | CallbackQuery):
    if isinstance(event, CallbackQuery):
        message = event.message
        user = event.from_user
        try:
            await event.message.delete()
        except:
            pass
    else:
        message = event
        user = event.from_user

    user_id = user.id
    full_name = user.full_name

    try:
        if db.is_superadmin(user_id):
            if db.is_premium_user(user_id):
                await message.answer(
                    f'SUPERADMIN PANEL\n\n'
                    f'Assalomu alaykum, {full_name}!\n\n'
                    f'Sizda barcha admin va premium huquqlar mavjud.',
                    reply_markup=superadmin_premium_main,
                    parse_mode='HTML'
                )
            else:
                await message.answer(
                    f'SUPERADMIN PANEL\n\n'
                    f'Assalomu alaykum, {full_name}!',
                    reply_markup=superadmin_main,
                    parse_mode='HTML'
                )
            logger.info(f"Superadmin {user_id} accessed the bot")
            return

        if not db.user_exists(user_id):
            db.add_user(user_id, subscription=False)

            welcome_text = (
                f"<b>Xush kelibsiz!</b>\n\n"
                f"Assalomu alaykum, {full_name}!\n\n"
                f"Siz muvaffaqiyatli ro'yxatdan o'tdingiz.\n\n"
                f"<b>Botimiz imkoniyatlari:</b>\n"
                f"- Avtomatik postlar yaratish\n"
                f"- Kanallarni boshqarish\n"
                f"- Vaqt rejalashtirish\n\n"
                f"<i>Premium obuna bilan ko'proq imkoniyatlar!</i>"
            )

            await message.answer(
                welcome_text,
                reply_markup=non_premium,
                parse_mode='HTML'
            )
            logger.info(f"New user registered: {user_id}")
        else:
            if db.is_premium_user(user_id):
                welcome_msg = MESSAGES["welcome_premium"].format(name=full_name)
                await message.answer(
                    welcome_msg,
                    reply_markup=premium,
                    parse_mode='HTML'
                )
            else:
                welcome_msg = MESSAGES["welcome_free"].format(name=full_name)
                await message.answer(
                    welcome_msg,
                    reply_markup=non_premium,
                    parse_mode='HTML'
                )
    except Exception as e:
        logger.error(f"Error in greating handler: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.")
