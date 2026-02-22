import logging
import asyncio
import os
from datetime import datetime, timedelta
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram import Bot

from states import AdminPanel
from keyboards.inline import (
    admin_panel, confirm_broadcast, back_to_main,
    bot_settings_menu, payment_settings_menu, limits_settings_menu,
    back_to_settings
)
from utils.database import db
from utils.env_manager import update_env_value, get_current_settings
from utils.security import validate_broadcast_message
from utils.stats_chart import generate_stats_chart
from config import SUPER_ADMIN1, SUPER_ADMIN2

logger = logging.getLogger(__name__)

LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_FILE = os.getenv("LOG_FILE", "bot.log")


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

        # Bugungi statsni yozib qo'yamiz
        db.record_daily_stats()

        total_users = db.get_total_users()
        premium_users = db.get_premium_users_count()
        free_users = total_users - premium_users
        total_channels = db.get_total_channels()
        total_posts, posts_with_image = db.count_total_active_posts()

        stats_text = (
            "<b>📊 Bot Statistikasi</b>\n\n"
            f"👥 Jami foydalanuvchilar: <b>{total_users}</b>\n"
            f"⭐ Premium: <b>{premium_users}</b>\n"
            f"👤 Oddiy: <b>{free_users}</b>\n\n"
            f"📢 Jami kanallar: <b>{total_channels}</b>\n"
            f"📝 Jami postlar: <b>{total_posts}</b>\n"
            f"🖼 Rasmli postlar: <b>{posts_with_image}</b>\n"
        )

        # Grafik yaratish
        stats_history = db.get_stats_history(days=30)

        if stats_history and len(stats_history) >= 1:
            chart_bytes = generate_stats_chart(stats_history)
            if chart_bytes:
                photo = BufferedInputFile(chart_bytes, filename="stats.png")
                await call.message.delete()
                await call.message.answer_photo(
                    photo=photo,
                    caption=stats_text,
                    reply_markup=admin_panel,
                    parse_mode="HTML"
                )
                return

        # Grafik yo'q bo'lsa oddiy matn
        await call.message.edit_text(
            stats_text,
            reply_markup=admin_panel,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in show_statistics: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def download_logs(call: CallbackQuery):
    """24 soatlik loglarni txt fayl sifatida yuborish."""
    try:
        user_id = call.from_user.id

        if not db.is_superadmin(user_id):
            await call.answer("Sizda admin huquqi yo'q", show_alert=True)
            return

        await call.answer("Loglar tayyorlanmoqda...", show_alert=False)

        log_path = os.path.join(LOG_DIR, LOG_FILE)

        if not os.path.exists(log_path):
            await call.message.answer(
                "Log fayl topilmadi.",
                reply_markup=admin_panel
            )
            return

        # 24 soatlik loglarni filter qilish
        cutoff = datetime.now() - timedelta(hours=24)
        filtered_lines = []

        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        # Log format: "2024-12-25 10:30:45 - ..."
                        if len(line) >= 19:
                            ts_str = line[:19]
                            ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                            if ts >= cutoff:
                                filtered_lines.append(line)
                        else:
                            # Davomi (multiline traceback va h.k.)
                            if filtered_lines:
                                filtered_lines.append(line)
                    except ValueError:
                        # Timestamp parse qilib bo'lmasa - davomiy qator
                        if filtered_lines:
                            filtered_lines.append(line)
        except Exception as e:
            logger.error(f"Log o'qishda xatolik: {e}")
            await call.message.answer(
                "Log faylni o'qishda xatolik.",
                reply_markup=admin_panel
            )
            return

        if not filtered_lines:
            await call.message.answer(
                "Oxirgi 24 soatda log yozuvi topilmadi.",
                reply_markup=admin_panel
            )
            return

        # TXT fayl yaratish
        content = "".join(filtered_lines)
        # Telegram 50MB limit, lekin matnni 10MB gacha cheklaymiz
        if len(content) > 10 * 1024 * 1024:
            content = content[-(10 * 1024 * 1024):]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"logs_24h_{timestamp}.txt"
        doc = BufferedInputFile(content.encode('utf-8'), filename=filename)

        error_count = sum(1 for l in filtered_lines if ' - ERROR - ' in l)
        warn_count = sum(1 for l in filtered_lines if ' - WARNING - ' in l)

        caption = (
            f"📋 <b>24 soatlik loglar</b>\n\n"
            f"📄 Qatorlar: {len(filtered_lines)}\n"
            f"❌ Xatoliklar: {error_count}\n"
            f"⚠️ Ogohlantirishlar: {warn_count}\n"
            f"📅 Vaqt: {cutoff.strftime('%H:%M')} → {datetime.now().strftime('%H:%M')}"
        )

        await call.message.answer_document(
            document=doc,
            caption=caption,
            reply_markup=admin_panel,
            parse_mode="HTML"
        )

        logger.info(f"Admin {user_id} downloaded 24h logs ({len(filtered_lines)} lines)")
    except Exception as e:
        logger.error(f"Error in download_logs: {e}", exc_info=True)
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
            await asyncio.sleep(0.05)  # Telegram rate limit himoyasi

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
        image_mode = settings.get('IMAGE_MODE', 'OFF')
        image_status = "ON" if image_mode == 'ON' else "OFF"

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
        card_number = settings.get('CARD_NUMBER', '')
        card_name = settings.get('CARD_NAME', '')
        card_surname = settings.get('CARD_SURNAME', '')
        weekly_price = settings.get('WEEKLY_PRICE', '5000')
        day15_price = settings.get('DAY15_PRICE', '10000')
        monthly_price = settings.get('MONTHLY_PRICE', '20000')

        text = (
            "<b>To'lov Sozlamalari</b>\n\n"
            f"Karta: <code>{card_number}</code>\n"
            f"Ism: {card_name}\n"
            f"Familiya: {card_surname}\n\n"
            f"Haftalik: {weekly_price} so'm\n"
            f"15 kunlik: {day15_price} so'm\n"
            f"Oylik: {monthly_price} so'm\n\n"
            "O'zgartirish uchun tanlang:\n\n"
            "<i>Eslatma: O'zgarishlar kuchga kirishi uchun botni restart berish kerak.</i>"
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
        max_posts_free = settings.get('MAX_POSTS_FREE', '3')
        max_posts_premium = settings.get('MAX_POSTS_PREMIUM', '15')
        max_channels_free = settings.get('MAX_CHANNELS_FREE', '1')
        max_channels_premium = settings.get('MAX_CHANNELS_PREMIUM', '3')
        max_theme_words_free = settings.get('MAX_THEME_WORDS_FREE', '10')
        max_theme_words_premium = settings.get('MAX_THEME_WORDS_PREMIUM', '15')

        text = (
            "<b>Limitlar</b>\n\n"
            f"Free post limiti: {max_posts_free}\n"
            f"Premium post limiti: {max_posts_premium}\n"
            f"Free kanal limiti: {max_channels_free}\n"
            f"Premium kanal limiti: {max_channels_premium}\n"
            f"Free mavzu so'z limiti: {max_theme_words_free}\n"
            f"Premium mavzu so'z limiti: {max_theme_words_premium}\n\n"
            "O'zgartirish uchun tanlang:\n\n"
            "<i>Eslatma: O'zgarishlar kuchga kirishi uchun botni restart berish kerak.</i>"
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
        current_mode = settings.get('IMAGE_MODE', 'OFF')
        new_mode = 'OFF' if current_mode == 'ON' else 'ON'

        if update_env_value('IMAGE_MODE', new_mode):
            status = "yoqildi" if new_mode == 'ON' else "o'chirildi"
            await call.answer(f"Rasm rejimi {status}. Botni restart bering.", show_alert=True)

            image_status = "ON" if new_mode == 'ON' else "OFF"
            text = (
                "<b>Bot Sozlamalari</b>\n\n"
                f"Rasm rejimi: {image_status}\n\n"
                "Qaysi sozlamalarni o'zgartirmoqchisiz?\n\n"
                "<i>Eslatma: O'zgarishlar kuchga kirishi uchun botni restart berish kerak.</i>"
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

        prompts = {
            'edit_card_number': ('CARD_NUMBER', 'Yangi karta raqamini kiriting:', AdminPanel.EDIT_CARD_NUMBER),
            'edit_card_name': ('CARD_NAME', 'Karta egasining ismini kiriting:', AdminPanel.EDIT_CARD_NAME),
            'edit_card_surname': ('CARD_SURNAME', 'Karta egasining familiyasini kiriting:', AdminPanel.EDIT_CARD_SURNAME),
            'edit_weekly_price': ('WEEKLY_PRICE', 'Haftalik narxni kiriting (faqat raqam):', AdminPanel.EDIT_WEEKLY_PRICE),
            'edit_day15_price': ('DAY15_PRICE', '15 kunlik narxni kiriting (faqat raqam):', AdminPanel.EDIT_DAY15_PRICE),
            'edit_monthly_price': ('MONTHLY_PRICE', 'Oylik narxni kiriting (faqat raqam):', AdminPanel.EDIT_MONTHLY_PRICE),
            'edit_max_posts_free': ('MAX_POSTS_FREE', 'Free post limitini kiriting (1-15):', AdminPanel.EDIT_MAX_POSTS_FREE),
            'edit_max_posts_premium': ('MAX_POSTS_PREMIUM', 'Premium post limitini kiriting (1-15):', AdminPanel.EDIT_MAX_POSTS_PREMIUM),
            'edit_max_channels_free': ('MAX_CHANNELS_FREE', 'Free kanal limitini kiriting:', AdminPanel.EDIT_MAX_CHANNELS_FREE),
            'edit_max_channels_premium': ('MAX_CHANNELS_PREMIUM', 'Premium kanal limitini kiriting:', AdminPanel.EDIT_MAX_CHANNELS_PREMIUM),
            'edit_max_theme_words_free': ('MAX_THEME_WORDS_FREE', "Free mavzu so'z limitini kiriting:", AdminPanel.EDIT_MAX_THEME_WORDS_FREE),
            'edit_max_theme_words_premium': ('MAX_THEME_WORDS_PREMIUM', "Premium mavzu so'z limitini kiriting:", AdminPanel.EDIT_MAX_THEME_WORDS_PREMIUM),
        }

        if edit_type not in prompts:
            await call.answer("Noma'lum sozlama", show_alert=True)
            return

        env_key, prompt_text, next_state = prompts[edit_type]
        settings = get_current_settings()
        current_value = settings.get(env_key, '')

        await state.update_data(edit_env_key=env_key)

        text = f"{prompt_text}\n\nJoriy qiymat: <code>{current_value}</code>"
        await call.message.edit_text(text, reply_markup=back_to_settings, parse_mode="HTML")
        await state.set_state(next_state)
    except Exception as e:
        logger.error(f"Error in request_edit_value: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def process_edit_card_number(message: Message, state: FSMContext):
    try:
        # message.text None bo'lishi mumkin
        if not message.text:
            await message.answer("Iltimos faqat matn kiriting (karta raqami)")
            return

        value = message.text.strip().replace(" ", "")

        if not value.isdigit() or len(value) != 16:
            await message.answer("Karta raqami 16 ta raqamdan iborat bo'lishi kerak")
            return

        if update_env_value('CARD_NUMBER', value):
            await message.answer(
                f"Karta raqami yangilandi: <code>{value}</code>\n\n"
                "<i>Botni restart bering.</i>",
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
        # message.text None bo'lishi mumkin
        if not message.text:
            await message.answer("Iltimos faqat matn kiriting (ism)")
            return

        value = message.text.strip()

        if len(value) < 2 or len(value) > 50:
            await message.answer("Ism 2-50 belgi orasida bo'lishi kerak")
            return

        if update_env_value('CARD_NAME', value):
            await message.answer(
                f"Ism yangilandi: {value}\n\n<i>Botni restart bering.</i>",
                reply_markup=back_to_settings,
                parse_mode="HTML"
            )
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
        # message.text None bo'lishi mumkin
        if not message.text:
            await message.answer("Iltimos faqat matn kiriting (familiya)")
            return

        value = message.text.strip()

        if len(value) < 2 or len(value) > 50:
            await message.answer("Familiya 2-50 belgi orasida bo'lishi kerak")
            return

        if update_env_value('CARD_SURNAME', value):
            await message.answer(
                f"Familiya yangilandi: {value}\n\n<i>Botni restart bering.</i>",
                reply_markup=back_to_settings,
                parse_mode="HTML"
            )
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
        # message.text None bo'lishi mumkin
        if not message.text:
            await message.answer("Iltimos faqat raqam kiriting")
            return

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
            await message.answer(
                f"Narx yangilandi: {value} so'm\n\n<i>Botni restart bering.</i>",
                reply_markup=back_to_settings,
                parse_mode="HTML"
            )
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
        # message.text None bo'lishi mumkin
        if not message.text:
            await message.answer("Iltimos faqat raqam kiriting")
            return

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
            await message.answer(
                f"Post limiti yangilandi: {value}\n\n<i>Botni restart bering.</i>",
                reply_markup=back_to_settings,
                parse_mode="HTML"
            )
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
        # message.text None bo'lishi mumkin
        if not message.text:
            await message.answer("Iltimos faqat raqam kiriting")
            return

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
            await message.answer(
                f"Kanal limiti yangilandi: {value}\n\n<i>Botni restart bering.</i>",
                reply_markup=back_to_settings,
                parse_mode="HTML"
            )
            await state.clear()
        else:
            await message.answer("Xatolik yuz berdi", reply_markup=back_to_settings)
            await state.clear()
    except Exception as e:
        logger.error(f"Error in process_edit_channels_limit: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi", reply_markup=back_to_settings)
        await state.clear()


async def process_edit_theme_words_limit(message: Message, state: FSMContext):
    try:
        # message.text None bo'lishi mumkin
        if not message.text:
            await message.answer("Iltimos faqat raqam kiriting")
            return

        value = message.text.strip()

        if not value.isdigit():
            await message.answer("Faqat raqam kiriting")
            return

        limit = int(value)
        if limit < 1 or limit > 50:
            await message.answer("Limit 1 dan 50 gacha bo'lishi kerak")
            return

        data = await state.get_data()
        env_key = data.get('edit_env_key')

        if update_env_value(env_key, value):
            await message.answer(
                f"Mavzu so'z limiti yangilandi: {value}\n\n<i>Botni restart bering.</i>",
                reply_markup=back_to_settings,
                parse_mode="HTML"
            )
            await state.clear()
        else:
            await message.answer("Xatolik yuz berdi", reply_markup=back_to_settings)
            await state.clear()
    except Exception as e:
        logger.error(f"Error in process_edit_theme_words_limit: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi", reply_markup=back_to_settings)
        await state.clear()
