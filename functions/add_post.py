import logging
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from states import AddPost
from keyboards.inline import p_back_to_main, back_to_main, premium_image_toggle
from utils.database import db
from utils.validators import validate_time_format, validate_word_count
from config import MAX_POSTS_FREE, MAX_POSTS_PREMIUM, MAX_THEME_WORDS_FREE, MAX_THEME_WORDS_PREMIUM, IMAGE_MODE

logger = logging.getLogger(__name__)


def build_channels_keyboard(channels, is_premium: bool):
    """Kanal tanlash uchun keyboard yaratish"""
    keyboard = []
    for ch in channels:
        channel_id = ch[1]
        keyboard.append([
            InlineKeyboardButton(
                text=f"📢 Kanal {channel_id}",
                callback_data=f"select_ch:{channel_id}:{'p' if is_premium else 'f'}"
            )
        ])

    back_data = "p_back" if is_premium else "back"
    keyboard.append([InlineKeyboardButton(text='🏠 Bosh menyu', callback_data=back_data)])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def show_channels_for_post(call: CallbackQuery, state: FSMContext):
    """
    Post qo'shish tugmasi bosilganda kanallar ro'yxatini ko'rsatish.
    Foydalanuvchining premium yoki oddiy kanallarini tekshiradi.
    """
    try:
        try:
            await call.message.delete()
        except Exception:
            pass

        user_id = call.from_user.id

        # Foydalanuvchi premium yoki oddiy ekanligini tekshirish
        is_premium = db.is_premium(user_id)

        # Kanallarni olish
        if is_premium:
            channels = db.get_user_channels(user_id, premium=True)
            back_kb = p_back_to_main
        else:
            channels = db.get_user_channels(user_id, premium=False)
            back_kb = back_to_main

        if not channels:
            await call.message.answer(
                "⚠️ Sizda hali kanal yo'q.\n\n"
                "Avval kanal biriktiring, keyin post qo'shishingiz mumkin.",
                reply_markup=back_kb
            )
            return

        keyboard = build_channels_keyboard(channels, is_premium)

        await call.message.answer(
            "📝 <b>Post qo'shish</b>\n\n"
            "Qaysi kanalga post qo'shmoqchisiz?",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await state.set_state(AddPost.SELECT_CHANNEL)
        await state.update_data(is_premium=is_premium)

    except Exception as e:
        logger.error(f"Error in show_channels_for_post: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def select_channel_for_post(call: CallbackQuery, state: FSMContext):
    """
    Kanal tanlangandan keyin limitni tekshirish va vaqt so'rash.
    callback_data format: select_ch:{channel_id}:{p|f}
    """
    try:
        try:
            await call.message.delete()
        except Exception:
            pass

        # Callback data ni parse qilish
        parts = call.data.split(":")
        if len(parts) < 3:
            await call.answer("Xatolik", show_alert=True)
            return

        channel_id = int(parts[1])
        is_premium_str = parts[2]
        is_premium = is_premium_str == 'p'

        user_id = call.from_user.id
        back_kb = p_back_to_main if is_premium else back_to_main

        # Post limitni tekshirish
        if is_premium:
            max_posts = MAX_POSTS_PREMIUM
            current_posts = db.count_channel_posts(channel_id, premium=True)
            max_theme_words = MAX_THEME_WORDS_PREMIUM
        else:
            max_posts = MAX_POSTS_FREE
            current_posts = db.count_channel_posts(channel_id, premium=False)
            max_theme_words = MAX_THEME_WORDS_FREE

        if current_posts >= max_posts:
            await call.message.answer(
                f"⚠️ <b>Limitga yetdingiz!</b>\n\n"
                f"Siz bu kanalga maksimum {max_posts} ta post qo'shishingiz mumkin.\n"
                f"Hozirda: {current_posts} ta post mavjud.\n\n"
                f"{'Premium foydalanuvchi sifatida 15 tagacha post qo\'shishingiz mumkin edi.' if not is_premium else 'Eski postlarni o\'chirib yangilarini qo\'shing.'}",
                reply_markup=back_kb,
                parse_mode="HTML"
            )
            await state.clear()
            return

        # State ga ma'lumotlarni saqlash
        await state.update_data(
            channel_id=channel_id,
            is_premium=is_premium,
            max_theme_words=max_theme_words,
            post_number=current_posts + 1  # Yangi post raqami
        )

        await call.message.answer(
            f"📢 <b>Kanal tanlandi</b>\n\n"
            f"Kanal ID: <code>{channel_id}</code>\n"
            f"Mavjud postlar: {current_posts}/{max_posts}\n\n"
            f"Iltimos {current_posts + 1}-post uchun vaqtni kiriting.\n"
            f"Format: <b>HH:MM</b> (masalan: 09:30)",
            reply_markup=back_kb,
            parse_mode="HTML"
        )
        await state.set_state(AddPost.POST_TIME)

    except Exception as e:
        logger.error(f"Error in select_channel_for_post: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)
        await state.clear()


async def insert_post_time(message: Message, state: FSMContext):
    """Post vaqtini qabul qilish va mavzuni so'rash"""
    try:
        try:
            await message.delete()
        except Exception:
            pass

        data = await state.get_data()
        is_premium = data.get('is_premium', False)
        back_kb = p_back_to_main if is_premium else back_to_main
        max_theme_words = data.get('max_theme_words', MAX_THEME_WORDS_FREE)
        post_number = data.get('post_number', 1)

        # Vaqt formatini tekshirish
        if not validate_time_format(message.text):
            await message.answer(
                "❌ Vaqt noto'g'ri formatda.\n\n"
                "To'g'ri format: <b>HH:MM</b>\n"
                "Masalan: 09:30, 14:00, 23:45",
                parse_mode="HTML"
            )
            return

        await state.update_data(post_time=message.text)

        await message.answer(
            f"⏰ Vaqt saqlandi: <b>{message.text}</b>\n\n"
            f"Endi {post_number}-post uchun mavzuni kiriting.\n"
            f"Maksimum: <b>{max_theme_words}</b> so'z",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )
        await state.set_state(AddPost.POST_THEME)

    except Exception as e:
        logger.error(f"Error in insert_post_time: {e}", exc_info=True)
        data = await state.get_data()
        is_premium = data.get('is_premium', False)
        back_kb = p_back_to_main if is_premium else back_to_main
        await message.answer("Xatolik yuz berdi", reply_markup=back_kb)
        await state.clear()


async def insert_post_theme(message: Message, state: FSMContext):
    """Post mavzusini qabul qilish"""
    try:
        try:
            await message.delete()
        except Exception:
            pass

        data = await state.get_data()
        is_premium = data.get('is_premium', False)
        back_kb = p_back_to_main if is_premium else back_to_main
        max_theme_words = data.get('max_theme_words', MAX_THEME_WORDS_FREE)
        channel_id = data.get('channel_id')
        post_time = data.get('post_time')
        post_number = data.get('post_number', 1)

        if not channel_id:
            await message.answer("Xatolik: Kanal topilmadi", reply_markup=back_kb)
            await state.clear()
            return

        # So'z sonini tekshirish
        is_valid, word_count = validate_word_count(message.text, max_words=max_theme_words)
        if not is_valid:
            await message.answer(
                f"❌ Mavzu {max_theme_words} so'zdan oshmasligi kerak.\n"
                f"Siz {word_count} so'z kiritdingiz.\n\n"
                f"Qayta kiriting."
            )
            return

        await state.update_data(post_theme=message.text)

        # Agar IMAGE_MODE yoqiq va premium bo'lsa rasm so'rash
        if IMAGE_MODE and is_premium:
            await message.answer(
                f"📝 Mavzu saqlandi!\n\n"
                f"<b>Vaqt:</b> {post_time}\n"
                f"<b>Mavzu:</b> {message.text}\n\n"
                f"Bu post uchun rasm qo'shasizmi?",
                reply_markup=premium_image_toggle,
                parse_mode="HTML"
            )
            await state.set_state(AddPost.IMAGE_TOGGLE)
        else:
            # Rasm so'ramasdan saqlash
            await save_post_to_database(message, state, with_image='no')

    except Exception as e:
        logger.error(f"Error in insert_post_theme: {e}", exc_info=True)
        data = await state.get_data()
        is_premium = data.get('is_premium', False)
        back_kb = p_back_to_main if is_premium else back_to_main
        await message.answer("Xatolik yuz berdi", reply_markup=back_kb)
        await state.clear()


async def handle_image_toggle(call: CallbackQuery, state: FSMContext):
    """Rasm qo'shish yoki qo'shmaslik tanlovini qayta ishlash"""
    try:
        try:
            await call.message.delete()
        except Exception:
            pass

        with_image = 'yes' if call.data == 'p_image_yes' else 'no'
        await save_post_to_database(call, state, with_image=with_image)

    except Exception as e:
        logger.error(f"Error in handle_image_toggle: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)
        await state.clear()


async def save_post_to_database(event, state: FSMContext, with_image: str = 'no'):
    """Postni database ga saqlash"""
    try:
        data = await state.get_data()
        is_premium = data.get('is_premium', False)
        back_kb = p_back_to_main if is_premium else back_to_main
        channel_id = data.get('channel_id')
        post_time = data.get('post_time')
        post_theme = data.get('post_theme')
        post_number = data.get('post_number', 1)

        if not all([channel_id, post_time, post_theme]):
            if isinstance(event, CallbackQuery):
                await event.message.answer("Xatolik: Ma'lumotlar to'liq emas", reply_markup=back_kb)
            else:
                await event.answer("Xatolik: Ma'lumotlar to'liq emas", reply_markup=back_kb)
            await state.clear()
            return

        try:
            # Database ga saqlash
            db.update_channel_post(
                channel_id=channel_id,
                post_number=post_number,
                post_time=post_time,
                theme=post_theme,
                premium=is_premium,
                with_image=with_image
            )

            success_msg = (
                f"✅ <b>Post muvaffaqiyatli qo'shildi!</b>\n\n"
                f"📢 Kanal: <code>{channel_id}</code>\n"
                f"📋 Post raqami: {post_number}\n"
                f"⏰ Vaqt: {post_time}\n"
                f"📝 Mavzu: {post_theme}\n"
                f"🖼 Rasm: {'Ha' if with_image == 'yes' else 'Yo\\'q'}"
            )

            if isinstance(event, CallbackQuery):
                await event.message.answer(success_msg, reply_markup=back_kb, parse_mode="HTML")
            else:
                await event.answer(success_msg, reply_markup=back_kb, parse_mode="HTML")

            logger.info(f"Post added: channel={channel_id}, post={post_number}, time={post_time}")

        except ValueError as ve:
            # 24 soat cheklovi yoki boshqa xatolik
            error_msg = str(ve)
            if isinstance(event, CallbackQuery):
                await event.message.answer(f"⚠️ {error_msg}", reply_markup=back_kb)
            else:
                await event.answer(f"⚠️ {error_msg}", reply_markup=back_kb)

        await state.clear()

    except Exception as e:
        logger.error(f"Error in save_post_to_database: {e}", exc_info=True)
        data = await state.get_data()
        is_premium = data.get('is_premium', False)
        back_kb = p_back_to_main if is_premium else back_to_main
        if isinstance(event, CallbackQuery):
            await event.message.answer("Xatolik yuz berdi", reply_markup=back_kb)
        else:
            await event.answer("Xatolik yuz berdi", reply_markup=back_kb)
        await state.clear()
