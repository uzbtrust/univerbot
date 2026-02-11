import logging
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from functions import channel, premium_channel
from keyboards.inline import premium_buy, premium_back
from utils.database import db
from config import STICKERS, MESSAGES, WEEKLY_PRICE, DAY15_PRICE, MONTHLY_PRICE

logger = logging.getLogger(__name__)


async def chanelling(callback: CallbackQuery, state: FSMContext):
    try:
        try:
            await callback.message.delete()
        except Exception:
            pass

        user_id = callback.from_user.id

        if db.is_premium_user(user_id):
            await premium_channel.requesting_id(callback, state)
        else:
            await channel.requesting_id(callback, state)
    except Exception as e:
        logger.error(f"Error in chanelling callback: {e}", exc_info=True)
        await callback.answer("Xatolik yuz berdi", show_alert=True)


async def premium(callback: CallbackQuery):
    try:
        user_id = callback.from_user.id

        try:
            await callback.message.delete()
        except Exception:
            pass

        if db.is_premium_user(user_id):
            await callback.message.answer(
                '<b>Siz allaqachon premium foydalanuvchisiz!</b>\n\n'
                'Barcha premium imkoniyatlardan foydalanishingiz mumkin.',
                reply_markup=premium_back,
                parse_mode='HTML'
            )
        else:
            premium_msg = MESSAGES["premium_features"].format(
                weekly=WEEKLY_PRICE,
                day15=DAY15_PRICE,
                monthly=MONTHLY_PRICE
            )

            await callback.message.answer(
                premium_msg,
                reply_markup=premium_buy,
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error in premium callback: {e}", exc_info=True)
        await callback.answer("Xatolik yuz berdi", show_alert=True)


async def back(callback: CallbackQuery):
    try:
        from keyboards.inline import non_premium
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer('Orqaga qaytildi!', reply_markup=non_premium)
    except Exception as e:
        logger.error(f"Error in back callback: {e}", exc_info=True)
        await callback.answer("Xatolik yuz berdi", show_alert=True)
