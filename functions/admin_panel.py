import logging
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram import Bot

from states import AdminPanel
from keyboards.inline import (
    admin_panel, confirm_broadcast, back_to_main,
    bot_settings_menu, payment_settings_menu, limits_settings_menu, back_to_settings
)
from utils.database import db
from utils.security import validate_broadcast_message
from utils.env_manager import get_current_settings, update_env_value
from config import SUPER_ADMIN1

logger = logging.getLogger(__name__)


async def show_admin_panel(call: CallbackQuery):
    try:
        user_id = call.from_user.id

        if not db.is_superadmin(user_id):
            await call.answer("Sizda admin huquqi yo'q", show_alert=True)
            return

        await call.message.edit_text(
            "<b>Admin Panel</b>\n\n"
            "Quyidagi funksiyalardan birini tanlang:",
            reply_markup=admin_panel,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in show_admin_panel: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def show_statistics(call: CallbackQuery):
    try:
        user_id = call.from_user.id

        if not db.is_superadmin(user_id):
            await call.answer("Sizda admin huquqi yo'q", show_alert=True)
            return

        total_users = db.get_total_users()
        premium_users = db.get_premium_users_count()
        free_users = total_users - premium_users
        total_channels = db.get_total_channels()

        stats_text = (
            "<b>Bot Statistikasi</b>\n\n"
            f"Jami foydalanuvchilar: <b>{total_users}</b>\n"
            f"Premium foydalanuvchilar: <b>{premium_users}</b>\n"
            f"Oddiy foydalanuvchilar: <b>{free_users}</b>\n"
            f"Jami kanallar: <b>{total_channels}</b>\n"
        )

        await call.message.edit_text(
            stats_text,
            reply_markup=admin_panel,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in show_statistics: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def request_broadcast_message(call: CallbackQuery, state: FSMContext):
    try:
        user_id = call.from_user.id

        if not db.is_superadmin(user_id):
            await call.answer("Sizda admin huquqi yo'q", show_alert=True)
            return

        await call.message.edit_text(
            "<b>Reklama yuborish</b>\n\n"
            "Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring.\n"
            "Xabar matn, rasm, video yoki boshqa formatda bo'lishi mumkin.",
            parse_mode="HTML"
        )
        await state.set_state(AdminPanel.BROADCAST_MESSAGE)
    except Exception as e:
        logger.error(f"Error in request_broadcast_message: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def receive_broadcast_message(message: Message, state: FSMContext):
    try:
        if message.text:
            is_valid, error_msg = validate_broadcast_message(message.text)
            if not is_valid:
                await message.answer(f"{error_msg}")
                return

        await state.update_data(
            message_id=message.message_id,
            chat_id=message.chat.id,
            content_type=message.content_type
        )

        await message.answer(
            "Xabar qabul qilindi.\n\n"
            "Barcha foydalanuvchilarga yuborishni tasdiqlaysizmi?",
            reply_markup=confirm_broadcast
        )
        await state.set_state(AdminPanel.CONFIRM_BROADCAST)
    except Exception as e:
        logger.error(f"Error in receive_broadcast_message: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi", reply_markup=back_to_main)
        await state.clear()


async def confirm_broadcast_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    try:
        user_id = call.from_user.id

        if not db.is_superadmin(user_id):
            await call.answer("Sizda admin huquqi yo'q", show_alert=True)
            return

        data = await state.get_data()
        message_id = data.get("message_id")
        chat_id = data.get("chat_id")

        if not message_id or not chat_id:
            await call.answer("Xatolik: Xabar topilmadi", show_alert=True)
            await state.clear()
            return

        users = db.get_all_user_ids()

        if not users:
            await call.message.edit_text(
                "Hech qanday foydalanuvchi topilmadi.",
                reply_markup=admin_panel
            )
            await state.clear()
            return

        await call.message.edit_text("Xabar yuborilmoqda...")

        success_count = 0
        failed_count = 0

        for user in users:
            try:
                await bot.copy_message(
                    chat_id=user[0],
                    from_chat_id=chat_id,
                    message_id=message_id
                )
                success_count += 1
            except Exception as e:
                logger.warning(f"Failed to send to user {user[0]}: {e}")
                failed_count += 1

        result_text = (
            "<b>Reklama yuborildi!</b>\n\n"
            f"Muvaffaqiyatli: <b>{success_count}</b>\n"
            f"Muvaffaqiyatsiz: <b>{failed_count}</b>\n"
            f"Jami: <b>{len(users)}</b>"
        )

        await call.message.edit_text(
            result_text,
            reply_markup=admin_panel,
            parse_mode="HTML"
        )
        await state.clear()

        logger.info(f"Broadcast completed: {success_count} success, {failed_count} failed")
    except Exception as e:
        logger.error(f"Error in confirm_broadcast_handler: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)
        await state.clear()


async def cancel_broadcast_handler(call: CallbackQuery, state: FSMContext):
    try:
        await call.message.edit_text(
            "Reklama bekor qilindi.",
            reply_markup=admin_panel
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Error in cancel_broadcast_handler: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def show_settings_menu(call: CallbackQuery):
    try:
        if not db.is_superadmin(call.from_user.id):
            await call.answer("Sizda admin huquqi yo'q", show_alert=True)
            return

        settings = get_current_settings()
        image_status = "ON" if settings['IMAGE_MODE'] == 'ON' else "OFF"

        text = (
            "<b>Bot Sozlamalari</b>\n\n"
            f"Rasm rejimi: {image_status}\n\n"
            "Qaysi sozlamalarni o'zgartirmoqchisiz?"
        )

        await call.message.edit_text(text, reply_markup=bot_settings_menu, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in show_settings_menu: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def show_payment_settings(call: CallbackQuery):
    try:
        if not db.is_superadmin(call.from_user.id):
            await call.answer("Sizda admin huquqi yo'q", show_alert=True)
            return

        settings = get_current_settings()

        text = (
            "<b>To'lov Sozlamalari</b>\n\n"
            f"Karta: <code>{settings['CARD_NUMBER']}</code>\n"
            f"Ism: {settings['CARD_NAME']}\n"
            f"Familiya: {settings['CARD_SURNAME']}\n\n"
            f"Haftalik: {settings['WEEKLY_PRICE']} so'm\n"
            f"15 kunlik: {settings['DAY15_PRICE']} so'm\n"
            f"Oylik: {settings['MONTHLY_PRICE']} so'm\n\n"
            "O'zgartirish uchun tanlang:"
        )

        await call.message.edit_text(text, reply_markup=payment_settings_menu, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in show_payment_settings: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def show_limits_settings(call: CallbackQuery):
    try:
        if not db.is_superadmin(call.from_user.id):
            await call.answer("Sizda admin huquqi yo'q", show_alert=True)
            return

        settings = get_current_settings()

        text = (
            "<b>Limitlar</b>\n\n"
            f"Free post limiti: {settings['MAX_POSTS_FREE']}\n"
            f"Premium post limiti: {settings['MAX_POSTS_PREMIUM']}\n"
            f"Free kanal limiti: {settings['MAX_CHANNELS_FREE']}\n"
            f"Premium kanal limiti: {settings['MAX_CHANNELS_PREMIUM']}\n\n"
            "O'zgartirish uchun tanlang:"
        )

        await call.message.edit_text(text, reply_markup=limits_settings_menu, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in show_limits_settings: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def toggle_image_mode(call: CallbackQuery):
    try:
        if not db.is_superadmin(call.from_user.id):
            await call.answer("Sizda admin huquqi yo'q", show_alert=True)
            return

        settings = get_current_settings()
        current_mode = settings['IMAGE_MODE']
        new_mode = 'OFF' if current_mode == 'ON' else 'ON'

        if update_env_value('IMAGE_MODE', new_mode):
            status = "yoqildi" if new_mode == 'ON' else "o'chirildi"
            await call.answer(f"Rasm rejimi {status}", show_alert=True)

            image_status = "ON" if new_mode == 'ON' else "OFF"
            text = (
                "<b>Bot Sozlamalari</b>\n\n"
                f"Rasm rejimi: {image_status}\n\n"
                "Qaysi sozlamalarni o'zgartirmoqchisiz?"
            )
            await call.message.edit_text(text, reply_markup=bot_settings_menu, parse_mode="HTML")
        else:
            await call.answer("Xatolik yuz berdi", show_alert=True)
    except Exception as e:
        logger.error(f"Error in toggle_image_mode: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def request_edit_value(call: CallbackQuery, state: FSMContext):
    try:
        if not db.is_superadmin(call.from_user.id):
            await call.answer("Sizda admin huquqi yo'q", show_alert=True)
            return

        edit_type = call.data
        settings = get_current_settings()

        prompts = {
            'edit_card_number': ('CARD_NUMBER', 'Yangi karta raqamini kiriting:', settings['CARD_NUMBER'], AdminPanel.EDIT_CARD_NUMBER),
            'edit_card_name': ('CARD_NAME', 'Karta egasining ismini kiriting:', settings['CARD_NAME'], AdminPanel.EDIT_CARD_NAME),
            'edit_card_surname': ('CARD_SURNAME', 'Karta egasining familiyasini kiriting:', settings['CARD_SURNAME'], AdminPanel.EDIT_CARD_SURNAME),
            'edit_weekly_price': ('WEEKLY_PRICE', 'Haftalik narxni kiriting (faqat raqam):', settings['WEEKLY_PRICE'], AdminPanel.EDIT_WEEKLY_PRICE),
            'edit_day15_price': ('DAY15_PRICE', '15 kunlik narxni kiriting (faqat raqam):', settings['DAY15_PRICE'], AdminPanel.EDIT_DAY15_PRICE),
            'edit_monthly_price': ('MONTHLY_PRICE', 'Oylik narxni kiriting (faqat raqam):', settings['MONTHLY_PRICE'], AdminPanel.EDIT_MONTHLY_PRICE),
            'edit_max_posts_free': ('MAX_POSTS_FREE', 'Free post limitini kiriting (1-15):', settings['MAX_POSTS_FREE'], AdminPanel.EDIT_MAX_POSTS_FREE),
            'edit_max_posts_premium': ('MAX_POSTS_PREMIUM', 'Premium post limitini kiriting (1-15):', settings['MAX_POSTS_PREMIUM'], AdminPanel.EDIT_MAX_POSTS_PREMIUM),
            'edit_max_channels_free': ('MAX_CHANNELS_FREE', 'Free kanal limitini kiriting:', settings['MAX_CHANNELS_FREE'], AdminPanel.EDIT_MAX_CHANNELS_FREE),
            'edit_max_channels_premium': ('MAX_CHANNELS_PREMIUM', 'Premium kanal limitini kiriting:', settings['MAX_CHANNELS_PREMIUM'], AdminPanel.EDIT_MAX_CHANNELS_PREMIUM),
        }

        if edit_type not in prompts:
            await call.answer("Noma'lum sozlama", show_alert=True)
            return

        env_key, prompt_text, current_value, next_state = prompts[edit_type]

        await state.update_data(edit_env_key=env_key)

        text = f"{prompt_text}\n\nJoriy qiymat: <code>{current_value}</code>"
        await call.message.edit_text(text, reply_markup=back_to_settings, parse_mode="HTML")
        await state.set_state(next_state)
    except Exception as e:
        logger.error(f"Error in request_edit_value: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def process_edit_card_number(message: Message, state: FSMContext):
    try:
        value = message.text.strip().replace(" ", "")

        if not value.isdigit() or len(value) != 16:
            await message.answer("Karta raqami 16 ta raqamdan iborat bo'lishi kerak")
            return

        if update_env_value('CARD_NUMBER', value):
            await message.answer(
                f"Karta raqami yangilandi: <code>{value}</code>",
                reply_markup=back_to_settings,
                parse_mode="HTML"
            )
            await state.clear()
        else:
            await message.answer("Xatolik yuz berdi", reply_markup=back_to_settings)
            await state.clear()
    except Exception as e:
        logger.error(f"Error in process_edit_card_number: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi", reply_markup=back_to_settings)
        await state.clear()


async def process_edit_card_name(message: Message, state: FSMContext):
    try:
        value = message.text.strip()

        if len(value) < 2 or len(value) > 50:
            await message.answer("Ism 2-50 belgi orasida bo'lishi kerak")
            return

        if update_env_value('CARD_NAME', value):
            await message.answer(f"Ism yangilandi: {value}", reply_markup=back_to_settings)
            await state.clear()
        else:
            await message.answer("Xatolik yuz berdi", reply_markup=back_to_settings)
            await state.clear()
    except Exception as e:
        logger.error(f"Error in process_edit_card_name: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi", reply_markup=back_to_settings)
        await state.clear()


async def process_edit_card_surname(message: Message, state: FSMContext):
    try:
        value = message.text.strip()

        if len(value) < 2 or len(value) > 50:
            await message.answer("Familiya 2-50 belgi orasida bo'lishi kerak")
            return

        if update_env_value('CARD_SURNAME', value):
            await message.answer(f"Familiya yangilandi: {value}", reply_markup=back_to_settings)
            await state.clear()
        else:
            await message.answer("Xatolik yuz berdi", reply_markup=back_to_settings)
            await state.clear()
    except Exception as e:
        logger.error(f"Error in process_edit_card_surname: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi", reply_markup=back_to_settings)
        await state.clear()


async def process_edit_price(message: Message, state: FSMContext):
    try:
        value = message.text.strip()

        if not value.isdigit():
            await message.answer("Faqat raqam kiriting")
            return

        price = int(value)
        if price < 1000 or price > 10000000:
            await message.answer("Narx 1000 dan 10000000 gacha bo'lishi kerak")
            return

        data = await state.get_data()
        env_key = data.get('edit_env_key')

        if update_env_value(env_key, value):
            await message.answer(f"Narx yangilandi: {value} so'm", reply_markup=back_to_settings)
            await state.clear()
        else:
            await message.answer("Xatolik yuz berdi", reply_markup=back_to_settings)
            await state.clear()
    except Exception as e:
        logger.error(f"Error in process_edit_price: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi", reply_markup=back_to_settings)
        await state.clear()


async def process_edit_posts_limit(message: Message, state: FSMContext):
    try:
        value = message.text.strip()

        if not value.isdigit():
            await message.answer("Faqat raqam kiriting")
            return

        limit = int(value)
        if limit < 1 or limit > 15:
            await message.answer("Limit 1 dan 15 gacha bo'lishi kerak")
            return

        data = await state.get_data()
        env_key = data.get('edit_env_key')

        if update_env_value(env_key, value):
            await message.answer(f"Post limiti yangilandi: {value}", reply_markup=back_to_settings)
            await state.clear()
        else:
            await message.answer("Xatolik yuz berdi", reply_markup=back_to_settings)
            await state.clear()
    except Exception as e:
        logger.error(f"Error in process_edit_posts_limit: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi", reply_markup=back_to_settings)
        await state.clear()


async def process_edit_channels_limit(message: Message, state: FSMContext):
    try:
        value = message.text.strip()

        if not value.isdigit():
            await message.answer("Faqat raqam kiriting")
            return

        limit = int(value)
        if limit < 1 or limit > 10:
            await message.answer("Limit 1 dan 10 gacha bo'lishi kerak")
            return

        data = await state.get_data()
        env_key = data.get('edit_env_key')

        if update_env_value(env_key, value):
            await message.answer(f"Kanal limiti yangilandi: {value}", reply_markup=back_to_settings)
            await state.clear()
        else:
            await message.answer("Xatolik yuz berdi", reply_markup=back_to_settings)
            await state.clear()
    except Exception as e:
        logger.error(f"Error in process_edit_channels_limit: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi", reply_markup=back_to_settings)
        await state.clear()
