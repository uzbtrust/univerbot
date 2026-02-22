import logging
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from states import ChangeTimeState, ChangeThemeState, ChangeTimePremiumState, ChangeThemePremiumState
from utils.database import db
from utils.validators import validate_time_format, validate_word_count
from config import MAX_THEME_WORDS_FREE, MAX_THEME_WORDS_PREMIUM
from keyboards.inline import back_to_main

logger = logging.getLogger(__name__)


async def _safe_delete(message) -> bool:
    """Xabarni o'chirish. Muvaffaqiyatsiz bo'lsa log yozadi."""
    try:
        await message.delete()
        return True
    except TelegramBadRequest:
        return False
    except Exception as e:
        logger.debug(f"Xabar o'chirib bo'lmadi: {e}")
        return False


def _build_channel_keyboard(channel_id: int, is_premium: bool = False):
    keyboard = []
    prefix = "change_time_premium" if is_premium else "change_time"
    theme_prefix = "change_theme_premium" if is_premium else "change_theme"

    max_posts = 15 if is_premium else 3
    channel_data = db.get_channel_by_id(channel_id, premium=is_premium)

    if not channel_data:
        return None

    posts_found = []
    for i in range(1, max_posts + 1):
        if is_premium:
            post_idx = 2 + (i - 1) * 2
            theme_idx = 3 + (i - 1) * 2
        else:
            post_idx = 2 + (i - 1) * 2
            theme_idx = 3 + (i - 1) * 2

        if post_idx < len(channel_data) and theme_idx < len(channel_data):
            if channel_data[post_idx] and channel_data[theme_idx]:
                posts_found.append(i)

    for i in posts_found[:3]:
        keyboard.append([
            InlineKeyboardButton(
                text=f"{i}-post vaqti",
                callback_data=f"{prefix}:{channel_id}:{i}"
            ),
            InlineKeyboardButton(
                text=f"{i}-post mavzusi",
                callback_data=f"{theme_prefix}:{channel_id}:{i}"
            )
        ])

        if is_premium:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{i}-post rasm",
                    callback_data=f"toggle_image_premium:{channel_id}:{i}"
                )
            ])

    keyboard.append([InlineKeyboardButton(text="Bosh menyu", callback_data="back")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def _format_channel_info(channel_data, is_premium: bool = False) -> str:
    if not channel_data:
        return "Kanal ma'lumotlari topilmadi."

    channel_id = channel_data[1]
    response = f"<b>Kanal ID:</b> <code>{channel_id}</code>\n\n"

    max_posts = 15 if is_premium else 3

    for i in range(1, max_posts + 1):
        post_idx = 2 + (i - 1) * 2
        theme_idx = 3 + (i - 1) * 2

        if post_idx < len(channel_data) and theme_idx < len(channel_data):
            post_time = channel_data[post_idx]
            post_theme = channel_data[theme_idx]

            if post_time and post_theme:
                response += f"<b>{i}-post:</b> {post_time} - {post_theme}\n"

    return response


async def is_premium(call: CallbackQuery):
    if db.is_premium_user(call.from_user.id):
        await premium_channel_list(call.message)
    else:
        await channel_list(call.message)


async def premium_channel_list(message: Message):
    user_id = message.from_user.id
    channels = db.get_user_channels(user_id, premium=True)

    if channels:
        for channel in channels:
            channel_id = channel[1]
            response = _format_channel_info(channel, is_premium=True)
            keyboard = _build_channel_keyboard(channel_id, is_premium=True)

            if keyboard:
                await message.answer(response, reply_markup=keyboard, parse_mode="HTML")
            else:
                await message.answer(response, reply_markup=back_to_main, parse_mode="HTML")
    else:
        await message.answer(
            "Siz hali hech qanday premium kanal biriktirmagansiz.",
            reply_markup=back_to_main
        )


async def channel_list(message: Message):
    user_id = message.from_user.id
    channels = db.get_user_channels(user_id, premium=False)

    if channels:
        for channel in channels:
            channel_id = channel[1]
            response = _format_channel_info(channel, is_premium=False)
            keyboard = _build_channel_keyboard(channel_id, is_premium=False)

            if keyboard:
                await message.answer(response, reply_markup=keyboard, parse_mode="HTML")
            else:
                await message.answer(response, reply_markup=back_to_main, parse_mode="HTML")
    else:
        await message.answer(
            "Siz hali hech qanday kanal biriktirmagansiz.",
            reply_markup=back_to_main
        )


async def change_time(call: CallbackQuery, state: FSMContext):
    try:
        await _safe_delete(call.message)

        _, channel_id, post_num = call.data.split(":")
        channel_id = int(channel_id)

        last_edit = db.get_last_edit_time(channel_id, premium=False)
        if last_edit:
            try:
                last_edit_datetime = datetime.fromisoformat(last_edit)
                time_since_edit = datetime.now() - last_edit_datetime
                if time_since_edit < timedelta(hours=24):
                    hours_left = 24 - int(time_since_edit.total_seconds() / 3600)
                    await call.answer(
                        f"Vaqtni o'zgartirish faqat 24 soatda bir marta mumkin.\n"
                        f"Yana {hours_left} soatdan keyin o'zgartirishingiz mumkin.",
                        show_alert=True
                    )
                    return
            except ValueError:
                pass

        await state.update_data(channel_id=channel_id, post_num=post_num, is_premium=False)
        await call.message.answer(
            f"<b>{post_num}-post uchun yangi vaqtni kiriting</b>\n\n"
            f"Format: HH:MM (masalan 09:30)",
            parse_mode="HTML"
        )
        await state.set_state(ChangeTimeState.waiting_for_time)
    except Exception as e:
        logger.error(f"Error in change_time: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def process_new_time(message: Message, state: FSMContext):
    try:
        # message.text None bo'lishi mumkin (rasm, stiker va h.k.)
        if not message.text:
            await message.answer(
                "Iltimos faqat matn kiriting.\nFormat: HH:MM (masalan 09:30)"
            )
            return

        data = await state.get_data()
        channel_id = data.get("channel_id")
        post_num = int(data.get("post_num"))
        new_time = message.text.strip()

        if not validate_time_format(new_time):
            await message.answer(
                "Vaqt noto'g'ri formatda. To'g'ri format: HH:MM (masalan 09:30)"
            )
            return

        db.update_single_post(channel_id, post_num, time=new_time, premium=False)

        channel = db.get_channel_by_id(channel_id, premium=False)
        if channel:
            response = _format_channel_info(channel, is_premium=False)
            keyboard = _build_channel_keyboard(channel_id, is_premium=False)
            await message.answer(
                f"Vaqt muvaffaqiyatli o'zgartirildi!\n\n{response}",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "Vaqt o'zgartirildi!",
                reply_markup=back_to_main
            )

        await state.clear()
        logger.info(f"Time updated for channel {channel_id}, post {post_num}")
    except ValueError as e:
        await message.answer(
            "Bu kanal post vaqti oxirgi tahrirdan 24 soat o'tmagani uchun o'zgartirib bo'lmaydi.",
            reply_markup=back_to_main
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Error in process_new_time: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi", reply_markup=back_to_main)
        await state.clear()


async def change_theme(call: CallbackQuery, state: FSMContext):
    try:
        await _safe_delete(call.message)

        _, channel_id, post_num = call.data.split(":")
        channel_id = int(channel_id)

        await state.update_data(channel_id=channel_id, post_num=post_num, is_premium=False)
        await call.message.answer(
            f"<b>{post_num}-post uchun yangi mavzuni kiriting</b>\n\n"
            f"Maksimal {MAX_THEME_WORDS_FREE} so'z",
            parse_mode="HTML"
        )
        await state.set_state(ChangeThemeState.waiting_for_theme)
    except Exception as e:
        logger.error(f"Error in change_theme: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def process_new_theme(message: Message, state: FSMContext):
    try:
        # message.text None bo'lishi mumkin (rasm, stiker va h.k.)
        if not message.text:
            await message.answer(
                f"Iltimos faqat matn kiriting.\nMavzu {MAX_THEME_WORDS_FREE} so'zdan oshmasligi kerak."
            )
            return

        data = await state.get_data()
        channel_id = data.get("channel_id")
        post_num = int(data.get("post_num"))
        new_theme = message.text.strip()

        is_valid, word_count = validate_word_count(new_theme, max_words=MAX_THEME_WORDS_FREE)
        if not is_valid:
            await message.answer(
                f"Mavzu {MAX_THEME_WORDS_FREE} so'zdan oshmasligi kerak. "
                f"Siz {word_count} so'z kiritdingiz. Qayta kiriting."
            )
            return

        db.update_single_post(channel_id, post_num, theme=new_theme, premium=False)

        channel = db.get_channel_by_id(channel_id, premium=False)
        if channel:
            response = _format_channel_info(channel, is_premium=False)
            keyboard = _build_channel_keyboard(channel_id, is_premium=False)
            await message.answer(
                f"Mavzu muvaffaqiyatli o'zgartirildi!\n\n{response}",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "Mavzu o'zgartirildi!",
                reply_markup=back_to_main
            )

        await state.clear()
        logger.info(f"Theme updated for channel {channel_id}, post {post_num}")
    except Exception as e:
        logger.error(f"Error in process_new_theme: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi", reply_markup=back_to_main)
        await state.clear()


async def change_premium_time(call: CallbackQuery, state: FSMContext):
    try:
        await _safe_delete(call.message)

        _, channel_id, post_num = call.data.split(":")
        channel_id = int(channel_id)

        last_edit = db.get_last_edit_time(channel_id, premium=True)
        if last_edit:
            try:
                last_edit_datetime = datetime.fromisoformat(last_edit)
                time_since_edit = datetime.now() - last_edit_datetime
                if time_since_edit < timedelta(hours=24):
                    hours_left = 24 - int(time_since_edit.total_seconds() / 3600)
                    await call.answer(
                        f"Vaqtni o'zgartirish faqat 24 soatda bir marta mumkin.\n"
                        f"Yana {hours_left} soatdan keyin o'zgartirishingiz mumkin.",
                        show_alert=True
                    )
                    return
            except ValueError:
                pass

        await state.update_data(channel_id=channel_id, post_num=post_num, is_premium=True)
        await call.message.answer(
            f"<b>{post_num}-post uchun yangi vaqtni kiriting</b>\n\n"
            f"Format: HH:MM (masalan 09:30)",
            parse_mode="HTML"
        )
        await state.set_state(ChangeTimePremiumState.waiting_for_time)
    except Exception as e:
        logger.error(f"Error in change_premium_time: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def process_new_premium_time(message: Message, state: FSMContext):
    try:
        # message.text None bo'lishi mumkin (rasm, stiker va h.k.)
        if not message.text:
            await message.answer(
                "Iltimos faqat matn kiriting.\nFormat: HH:MM (masalan 09:30)"
            )
            return

        data = await state.get_data()
        channel_id = data.get("channel_id")
        post_num = int(data.get("post_num"))
        new_time = message.text.strip()

        if not validate_time_format(new_time):
            await message.answer(
                "Vaqt noto'g'ri formatda. To'g'ri format: HH:MM (masalan 09:30)"
            )
            return

        db.update_single_post(channel_id, post_num, time=new_time, premium=True)

        channel = db.get_channel_by_id(channel_id, premium=True)
        if channel:
            response = _format_channel_info(channel, is_premium=True)
            keyboard = _build_channel_keyboard(channel_id, is_premium=True)
            await message.answer(
                f"Vaqt muvaffaqiyatli o'zgartirildi!\n\n{response}",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "Vaqt o'zgartirildi!",
                reply_markup=back_to_main
            )

        await state.clear()
        logger.info(f"Premium time updated for channel {channel_id}, post {post_num}")
    except ValueError as e:
        await message.answer(
            "Bu kanal post vaqti oxirgi tahrirdan 24 soat o'tmagani uchun o'zgartirib bo'lmaydi.",
            reply_markup=back_to_main
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Error in process_new_premium_time: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi", reply_markup=back_to_main)
        await state.clear()


async def change_premium_theme(call: CallbackQuery, state: FSMContext):
    try:
        await _safe_delete(call.message)

        _, channel_id, post_num = call.data.split(":")
        channel_id = int(channel_id)

        await state.update_data(channel_id=channel_id, post_num=post_num, is_premium=True)
        await call.message.answer(
            f"<b>{post_num}-post uchun yangi mavzuni kiriting</b>\n\n"
            f"Maksimal {MAX_THEME_WORDS_PREMIUM} so'z",
            parse_mode="HTML"
        )
        await state.set_state(ChangeThemePremiumState.waiting_for_theme)
    except Exception as e:
        logger.error(f"Error in change_premium_theme: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def process_new_premium_theme(message: Message, state: FSMContext):
    try:
        # message.text None bo'lishi mumkin (rasm, stiker va h.k.)
        if not message.text:
            await message.answer(
                f"Iltimos faqat matn kiriting.\nMavzu {MAX_THEME_WORDS_PREMIUM} so'zdan oshmasligi kerak."
            )
            return

        data = await state.get_data()
        channel_id = data.get("channel_id")
        post_num = int(data.get("post_num"))
        new_theme = message.text.strip()

        is_valid, word_count = validate_word_count(new_theme, max_words=MAX_THEME_WORDS_PREMIUM)
        if not is_valid:
            await message.answer(
                f"Mavzu {MAX_THEME_WORDS_PREMIUM} so'zdan oshmasligi kerak. "
                f"Siz {word_count} so'z kiritdingiz. Qayta kiriting."
            )
            return

        db.update_single_post(channel_id, post_num, theme=new_theme, premium=True)

        channel = db.get_channel_by_id(channel_id, premium=True)
        if channel:
            response = _format_channel_info(channel, is_premium=True)
            keyboard = _build_channel_keyboard(channel_id, is_premium=True)
            await message.answer(
                f"Mavzu muvaffaqiyatli o'zgartirildi!\n\n{response}",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "Mavzu o'zgartirildi!",
                reply_markup=back_to_main
            )

        await state.clear()
        logger.info(f"Premium theme updated for channel {channel_id}, post {post_num}")
    except Exception as e:
        logger.error(f"Error in process_new_premium_theme: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi", reply_markup=back_to_main)
        await state.clear()


async def toggle_image_premium(call: CallbackQuery):
    try:
        await _safe_delete(call.message)

        _, channel_id, post_num = call.data.split(":")
        channel_id = int(channel_id)
        post_num = int(post_num)

        channel = db.get_channel_by_id(channel_id, premium=True)

        if not channel:
            await call.message.answer(
                "Kanal topilmadi.",
                reply_markup=back_to_main
            )
            return

        image_col_idx = 34 + (post_num - 1)
        current_status = channel[image_col_idx] if image_col_idx < len(channel) else 'no'
        new_status = 'no' if current_status == 'yes' else 'yes'

        db.execute_query(
            f"UPDATE premium_channel SET image{post_num} = ? WHERE id = ?",
            (new_status, channel_id)
        )

        channel = db.get_channel_by_id(channel_id, premium=True)
        if channel:
            response = _format_channel_info(channel, is_premium=True)
            keyboard = _build_channel_keyboard(channel_id, is_premium=True)

            status_text = "yoqildi" if new_status == 'yes' else "o'chirildi"
            await call.message.answer(
                f"{post_num}-post uchun rasm {status_text}\n\n{response}",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await call.message.answer(
                "Rasm sozlamasi o'zgartirildi!",
                reply_markup=back_to_main
            )

        logger.info(f"Image toggled for channel {channel_id}, post {post_num}: {new_status}")
    except Exception as e:
        logger.error(f"Error in toggle_image_premium: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)
