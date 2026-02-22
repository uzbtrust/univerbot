import logging
from datetime import datetime, timedelta
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram import Bot

from states import Payment
from keyboards.inline import non_premium, premium, cheque_check, premium_buy
from utils.database import db
from utils.helpers import format_payment_message, extract_user_id_from_caption
from config import (
    MESSAGES, CARD_NUMBER, CARD_NAME, CARD_SURNAME,
    WEEKLY_PRICE, DAY15_PRICE, MONTHLY_PRICE,
    ADMIN_GROUP_ID
)

logger = logging.getLogger(__name__)


def _get_payment_message(price: str) -> str:
    return MESSAGES["payment_instruction"].format(
        price=price,
        card_number=CARD_NUMBER,
        card_name=CARD_NAME,
        card_surname=CARD_SURNAME
    )


async def show_premium_cmd(message: Message):
    try:
        user_id = message.from_user.id

        if db.is_premium_user(user_id):
            await message.answer(
                "Siz allaqachon premium foydalanuvchisiz! 👑",
                parse_mode="HTML"
            )
            return

        premium_text = MESSAGES["premium_features"].format(
            weekly=WEEKLY_PRICE,
            day15=DAY15_PRICE,
            monthly=MONTHLY_PRICE
        )

        await message.answer(
            premium_text,
            reply_markup=premium_buy,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in show_premium_cmd: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi")


async def _send_cheque_to_admin(
    message: Message,
    bot: Bot,
    subscription_type: str
) -> bool:
    try:
        user_id = message.from_user.id
        caption = format_payment_message(
            message.from_user.full_name,
            user_id,
            subscription_type
        )

        try:
            if message.photo:
                await bot.send_photo(
                    chat_id=ADMIN_GROUP_ID,
                    photo=message.photo[-1].file_id,
                    caption=caption,
                    reply_markup=cheque_check
                )
                return True
            elif message.document:
                await bot.send_document(
                    chat_id=ADMIN_GROUP_ID,
                    document=message.document.file_id,
                    caption=caption,
                    reply_markup=cheque_check
                )
                return True
        except Exception as e:
            logger.error(f"Failed to send cheque to admin group: {e}")

        return False

    except Exception as e:
        logger.error(f"Error sending cheque to admin: {e}", exc_info=True)
        return False


async def weekly(call: CallbackQuery, state: FSMContext):
    try:
        try:
            await call.message.delete()
        except Exception:
            pass
        await state.set_state(Payment.CHEQUE_WEEKLY)

        await call.message.answer(
            _get_payment_message(WEEKLY_PRICE),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in weekly subscription: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def day15(call: CallbackQuery, state: FSMContext):
    try:
        try:
            await call.message.delete()
        except Exception:
            pass
        await state.set_state(Payment.CHEQUE_DAY15)

        await call.message.answer(
            _get_payment_message(DAY15_PRICE),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in 15-day subscription: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def monthly(call: CallbackQuery, state: FSMContext):
    try:
        try:
            await call.message.delete()
        except Exception:
            pass
        await state.set_state(Payment.CHEQUE_MONTHLY)

        await call.message.answer(
            _get_payment_message(MONTHLY_PRICE),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in monthly subscription: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def weekly_check(message: Message, bot: Bot, state: FSMContext):
    try:
        if await _send_cheque_to_admin(message, bot, "1 haftalik"):
            await message.answer(
                "<b>Chek qabul qilindi!</b>\n\n"
                "To'lovinggiz haqida habar adminga yuborildi.\n"
                "Admindan javobni kuting.\n\n"
                "Xaridingiz uchun rahmat!",
                parse_mode='HTML'
            )
            await state.clear()
        else:
            await message.answer(
                "<b>To'lov formati noto'g'ri</b>\n\n"
                "Iltimos to'lov tushgani haqida:\n"
                "Rasmli chek yoki\n"
                "PDF file ko'rinishida yuboring.\n\n"
                "Qaytadan yuboring!",
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error in weekly_check: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi. Qaytadan urinib ko'ring.")


async def day15_check(message: Message, bot: Bot, state: FSMContext):
    try:
        if await _send_cheque_to_admin(message, bot, "15 kunlik"):
            await message.answer(
                "<b>Chek qabul qilindi!</b>\n\n"
                "To'lovinggiz haqida habar adminga yuborildi.\n"
                "Admindan javobni kuting.\n\n"
                "Xaridingiz uchun rahmat!",
                parse_mode='HTML'
            )
            await state.clear()
        else:
            await message.answer(
                "<b>To'lov formati noto'g'ri</b>\n\n"
                "Iltimos to'lov tushgani haqida:\n"
                "Rasmli chek yoki\n"
                "PDF file ko'rinishida yuboring.\n\n"
                "Qaytadan yuboring!",
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error in day15_check: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi. Qaytadan urinib ko'ring.")


async def monthly_check(message: Message, bot: Bot, state: FSMContext):
    try:
        if await _send_cheque_to_admin(message, bot, "1 oylik"):
            await message.answer(
                "<b>Chek qabul qilindi!</b>\n\n"
                "To'lovinggiz haqida habar adminga yuborildi.\n"
                "Admindan javobni kuting.\n\n"
                "Xaridingiz uchun rahmat!",
                parse_mode='HTML'
            )
            await state.clear()
        else:
            await message.answer(
                "<b>To'lov formati noto'g'ri</b>\n\n"
                "Iltimos to'lov tushgani haqida:\n"
                "Rasmli chek yoki\n"
                "PDF file ko'rinishida yuboring.\n\n"
                "Qaytadan yuboring!",
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error in monthly_check: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi. Qaytadan urinib ko'ring.")


async def approving(call: CallbackQuery):
    try:
        user_id = extract_user_id_from_caption(call.message.caption)
        if not user_id:
            logger.error("Could not extract user ID from caption")
            await call.answer("Xatolik: Foydalanuvchi topilmadi", show_alert=True)
            return

        caption = call.message.caption or ""
        premium_type = None
        days = 0

        if "1 haftalik" in caption or "haftalik" in caption:
            premium_type = "weekly"
            days = 7
        elif "15 kunlik" in caption:
            premium_type = "15days"
            days = 15
        elif "1 oylik" in caption or "oylik" in caption:
            premium_type = "monthly"
            days = 30

        start_date = datetime.now()
        end_date = start_date + timedelta(days=days) if days > 0 else start_date + timedelta(days=30)

        db.update_user_subscription(
            user_id,
            subscription=True,
            premium_type=premium_type or "unknown"
        )

        db.execute_query(
            "UPDATE users SET start_date = ?, end_date = ? WHERE id = ?",
            (start_date.isoformat(), end_date.isoformat(), user_id)
        )

        await call.message.delete()
        await call.message.answer(f"Obuna tasdiqlandi! ({premium_type}, {days} kun)")

        await call.bot.send_message(
            chat_id=user_id,
            text=f"Tabriklaymiz! Sizning {premium_type} obunangiz tasdiqlandi.\n"
                 f"Amal qilish muddati: {days} kun\n"
                 f"Tugash sanasi: {end_date.strftime('%Y-%m-%d %H:%M')}\n\n"
                 f"Endi siz premium foydalanuvchisiz!",
            reply_markup=premium
        )
        logger.info(f"Subscription approved for user {user_id}: {premium_type} ({days} days)")
    except Exception as e:
        logger.error(f"Error in approving: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def rejecting(call: CallbackQuery):
    try:
        user_id = extract_user_id_from_caption(call.message.caption)
        if not user_id:
            logger.error("Could not extract user ID from caption")
            await call.answer("Xatolik: Foydalanuvchi topilmadi", show_alert=True)
            return

        await call.message.delete()
        await call.message.answer("Obuna rad etildi!")

        db.update_user_subscription(user_id, subscription=False)

        await call.bot.send_message(
            chat_id=user_id,
            text="Kechirasiz, sizning obunangiz rad etildi. "
                 "Iltimos to'lovni qayta tekshiring.",
            reply_markup=non_premium
        )
        logger.info(f"Subscription rejected for user {user_id}")
    except Exception as e:
        logger.error(f"Error in rejecting: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)
