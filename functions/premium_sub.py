import logging
from datetime import datetime, timedelta
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram import Bot

from states import Payment
from keyboards.inline import non_premium, premium, build_cheque_keyboard
from utils.database import db
from utils.helpers import format_payment_message, extract_user_id_from_caption
from config import MESSAGES

logger = logging.getLogger(__name__)


def _get_payment_message(price: str) -> str:
    card_number = db.get_setting('CARD_NUMBER', '')
    card_name = db.get_setting('CARD_NAME', '')
    card_surname = db.get_setting('CARD_SURNAME', '')

    return MESSAGES["payment_instruction"].format(
        price=price,
        card_number=card_number,
        card_name=card_name,
        card_surname=card_surname
    )


async def _send_cheque_to_admins(
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

        active_admins = db.get_active_admins()

        if not active_admins:
            logger.error("No active admins found")
            return False

        cheque_id = db.add_pending_cheque(
            user_id=user_id,
            subscription_type=subscription_type
        )

        keyboard = build_cheque_keyboard(cheque_id)

        msg_id_admin1 = None
        msg_id_admin2 = None
        chat_id_admin1 = None
        chat_id_admin2 = None

        admin1_id = db.get_setting_int('SUPER_ADMIN1')
        admin2_id = db.get_setting_int('SUPER_ADMIN2')

        for admin_id in active_admins:
            try:
                if message.photo:
                    sent_msg = await bot.send_photo(
                        chat_id=admin_id,
                        photo=message.photo[-1].file_id,
                        caption=caption,
                        reply_markup=keyboard
                    )
                elif message.document:
                    sent_msg = await bot.send_document(
                        chat_id=admin_id,
                        document=message.document.file_id,
                        caption=caption,
                        reply_markup=keyboard
                    )
                else:
                    continue

                if admin_id == admin1_id:
                    msg_id_admin1 = sent_msg.message_id
                    chat_id_admin1 = admin_id
                elif admin_id == admin2_id:
                    msg_id_admin2 = sent_msg.message_id
                    chat_id_admin2 = admin_id

            except Exception as e:
                logger.error(f"Failed to send cheque to admin {admin_id}: {e}")

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE pending_cheques
                   SET message_id_admin1 = ?, message_id_admin2 = ?,
                       chat_id_admin1 = ?, chat_id_admin2 = ?
                   WHERE id = ?""",
                (msg_id_admin1, msg_id_admin2, chat_id_admin1, chat_id_admin2, cheque_id)
            )
            conn.commit()

        return msg_id_admin1 is not None or msg_id_admin2 is not None

    except Exception as e:
        logger.error(f"Error sending cheque to admins: {e}", exc_info=True)
        return False


async def weekly(call: CallbackQuery, state: FSMContext):
    try:
        try:
            await call.message.delete()
        except Exception:
            pass
        await state.set_state(Payment.CHEQUE_WEEKLY)

        weekly_price = db.get_setting('WEEKLY_PRICE', '5000')
        await call.message.answer(
            _get_payment_message(weekly_price),
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

        day15_price = db.get_setting('DAY15_PRICE', '10000')
        await call.message.answer(
            _get_payment_message(day15_price),
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

        monthly_price = db.get_setting('MONTHLY_PRICE', '20000')
        await call.message.answer(
            _get_payment_message(monthly_price),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in monthly subscription: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def weekly_check(message: Message, bot: Bot, state: FSMContext):
    try:
        if await _send_cheque_to_admins(message, bot, "1 haftalik"):
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
        if await _send_cheque_to_admins(message, bot, "15 kunlik"):
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
        if await _send_cheque_to_admins(message, bot, "1 oylik"):
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


async def _delete_cheque_from_other_admin(bot: Bot, cheque_data, current_admin_id: int):
    try:
        admin1_id = db.get_setting_int('SUPER_ADMIN1')
        admin2_id = db.get_setting_int('SUPER_ADMIN2')

        if current_admin_id == admin1_id:
            other_msg_id = cheque_data['message_id_admin2']
            other_chat_id = cheque_data['chat_id_admin2']
        else:
            other_msg_id = cheque_data['message_id_admin1']
            other_chat_id = cheque_data['chat_id_admin1']

        if other_msg_id and other_chat_id:
            try:
                await bot.delete_message(chat_id=other_chat_id, message_id=other_msg_id)
            except Exception as e:
                logger.warning(f"Could not delete cheque from other admin: {e}")
    except Exception as e:
        logger.error(f"Error deleting cheque from other admin: {e}")


async def approving(call: CallbackQuery):
    try:
        cheque_id = None
        if call.data.startswith('approve:'):
            cheque_id = int(call.data.split(':')[1])

        if cheque_id:
            cheque = db.get_cheque_by_id(cheque_id)
            if not cheque:
                await call.answer("Chek topilmadi", show_alert=True)
                return

            if cheque['status'] != 'pending':
                await call.answer("Bu chek allaqachon ko'rib chiqilgan", show_alert=True)
                try:
                    await call.message.delete()
                except Exception:
                    pass
                return

            user_id = cheque['user_id']
            subscription_type = cheque['subscription_type']

            premium_type = None
            days = 0

            if "haftalik" in subscription_type:
                premium_type = "weekly"
                days = 7
            elif "15 kunlik" in subscription_type:
                premium_type = "15days"
                days = 15
            elif "oylik" in subscription_type:
                premium_type = "monthly"
                days = 30

            db.update_cheque_status(cheque_id, 'approved')

            await _delete_cheque_from_other_admin(call.bot, cheque, call.from_user.id)

        else:
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

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET start_date = ?, end_date = ? WHERE id = ?",
                (start_date.isoformat(), end_date.isoformat(), user_id)
            )
            conn.commit()

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
        cheque_id = None
        if call.data.startswith('reject:'):
            cheque_id = int(call.data.split(':')[1])

        if cheque_id:
            cheque = db.get_cheque_by_id(cheque_id)
            if not cheque:
                await call.answer("Chek topilmadi", show_alert=True)
                return

            if cheque['status'] != 'pending':
                await call.answer("Bu chek allaqachon ko'rib chiqilgan", show_alert=True)
                try:
                    await call.message.delete()
                except Exception:
                    pass
                return

            user_id = cheque['user_id']

            db.update_cheque_status(cheque_id, 'rejected')

            await _delete_cheque_from_other_admin(call.bot, cheque, call.from_user.id)

        else:
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
