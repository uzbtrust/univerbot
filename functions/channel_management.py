import logging
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram import Bot

from states import DeleteChannel, EditChannelPost
from keyboards.inline import back_to_main
from utils.database import db
from utils.validators import validate_time_format

logger = logging.getLogger(__name__)


def create_channels_list_keyboard(channels, action_prefix):
    keyboard = []

    for channel in channels:
        channel_id = channel[1]

        try:
            channel_name = f"Kanal {channel_id}"
        except Exception:
            channel_name = f"Kanal {channel_id}"

        row = [
            InlineKeyboardButton(text=f"{channel_name}", callback_data=f"channel_info:{channel_id}"),
            InlineKeyboardButton(text="O'chirish", callback_data=f"delete_ch:{channel_id}:{action_prefix}"),
            InlineKeyboardButton(text="Tahrir", callback_data=f"edit_ch:{channel_id}:{action_prefix}")
        ]
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text="Orqaga", callback_data="back")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_edit_options_keyboard(channel_id, is_premium):
    prefix = "p" if is_premium else "f"

    keyboard = [
        [InlineKeyboardButton(text="Post qo'shish", callback_data=f"add_post:{channel_id}:{prefix}")],
        [InlineKeyboardButton(text="Vaqtni o'zgartirish", callback_data=f"edit_time:{channel_id}:{prefix}")],
        [InlineKeyboardButton(text="Mavzuni o'zgartirish", callback_data=f"edit_theme:{channel_id}:{prefix}")],
        [InlineKeyboardButton(text="Postni o'chirish", callback_data=f"delete_post:{channel_id}:{prefix}")],
        [InlineKeyboardButton(text="Orqaga", callback_data="manage_channels")]
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_posts_list_keyboard(posts, channel_id, action_type, is_premium):
    keyboard = []
    prefix = "p" if is_premium else "f"

    for post in posts:
        post_num = post['post_num']
        theme = post['theme']
        time = post['time']

        button_text = f"{theme} - {time}"
        callback_data = f"{action_type}:{channel_id}:{post_num}:{prefix}"

        keyboard.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])

    keyboard.append([InlineKeyboardButton(text="Orqaga", callback_data=f"edit_ch:{channel_id}:{prefix}")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def show_channels_list(call: CallbackQuery):
    try:
        user_id = call.from_user.id

        is_premium = db.is_premium_user(user_id)

        channels = db.get_user_channels(user_id, premium=is_premium)

        if not channels:
            await call.message.edit_text(
                "Sizda hech qanday kanal yo'q.",
                reply_markup=back_to_main
            )
            return

        prefix = "p" if is_premium else "f"
        keyboard = create_channels_list_keyboard(channels, prefix)

        await call.message.edit_text(
            "<b>Sizning kanallaringiz:</b>\n\n"
            "Kerakli amalni tanlang:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in show_channels_list: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def confirm_delete_channel(call: CallbackQuery, state: FSMContext):
    try:
        parts = call.data.split(":")
        channel_id = int(parts[1])
        is_premium = parts[2] == "p"

        await state.update_data(
            delete_channel_id=channel_id,
            delete_is_premium=is_premium
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Ha, o'chirish", callback_data="confirm_delete_yes"),
                InlineKeyboardButton(text="Yo'q", callback_data="confirm_delete_no")
            ]
        ])

        await call.message.edit_text(
            "<b>Diqqat!</b>\n\n"
            f"Kanalni o'chirishni tasdiqlaysizmi?\n"
            "Bu amalni bekor qilib bo'lmaydi.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await state.set_state(DeleteChannel.CONFIRM_DELETE)
    except Exception as e:
        logger.error(f"Error in confirm_delete_channel: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def delete_channel_confirmed(call: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        channel_id = data.get("delete_channel_id")
        is_premium = data.get("delete_is_premium")

        if not channel_id:
            await call.answer("Xatolik: Kanal topilmadi", show_alert=True)
            await state.clear()
            return

        db.delete_channel(channel_id, premium=is_premium)

        await call.message.edit_text(
            "Kanal muvaffaqiyatli o'chirildi!",
            reply_markup=back_to_main
        )
        await state.clear()

        logger.info(f"Channel {channel_id} deleted by user {call.from_user.id}")
    except Exception as e:
        logger.error(f"Error in delete_channel_confirmed: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)
        await state.clear()


async def cancel_delete_channel(call: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        await show_channels_list(call)
    except Exception as e:
        logger.error(f"Error in cancel_delete_channel: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def show_edit_options(call: CallbackQuery):
    try:
        parts = call.data.split(":")
        channel_id = int(parts[1])
        is_premium = parts[2] == "p"

        keyboard = create_edit_options_keyboard(channel_id, is_premium)

        await call.message.edit_text(
            "<b>Kanalni tahrirlash</b>\n\n"
            "Qaysi qismini tahrirlashni xohlaysiz?",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in show_edit_options: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def show_posts_for_time_edit(call: CallbackQuery):
    try:
        parts = call.data.split(":")
        channel_id = int(parts[1])
        is_premium = parts[2] == "p"

        posts = db.get_channel_posts(channel_id, premium=is_premium)

        if not posts:
            await call.answer("Hech qanday post topilmadi", show_alert=True)
            return

        keyboard = create_posts_list_keyboard(posts, channel_id, "select_time", is_premium)

        await call.message.edit_text(
            "<b>Vaqtni o'zgartirish</b>\n\n"
            "Qaysi postning vaqtini o'zgartirmoqchisiz?",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in show_posts_for_time_edit: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def show_posts_for_theme_edit(call: CallbackQuery):
    try:
        parts = call.data.split(":")
        channel_id = int(parts[1])
        is_premium = parts[2] == "p"

        posts = db.get_channel_posts(channel_id, premium=is_premium)

        if not posts:
            await call.answer("Hech qanday post topilmadi", show_alert=True)
            return

        keyboard = create_posts_list_keyboard(posts, channel_id, "select_theme", is_premium)

        await call.message.edit_text(
            "<b>Mavzuni o'zgartirish</b>\n\n"
            "Qaysi postning mavzusini o'zgartirmoqchisiz?",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in show_posts_for_theme_edit: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def show_posts_for_delete(call: CallbackQuery):
    try:
        parts = call.data.split(":")
        channel_id = int(parts[1])
        is_premium = parts[2] == "p"

        posts = db.get_channel_posts(channel_id, premium=is_premium)

        if not posts:
            await call.answer("Hech qanday post topilmadi", show_alert=True)
            return

        keyboard = create_posts_list_keyboard(posts, channel_id, "confirm_delete_post", is_premium)

        await call.message.edit_text(
            "<b>Postni o'chirish</b>\n\n"
            "Qaysi postni o'chirmoqchisiz?",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in show_posts_for_delete: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def request_new_time(call: CallbackQuery, state: FSMContext):
    try:
        parts = call.data.split(":")
        channel_id = int(parts[1])
        post_num = int(parts[2])
        is_premium = parts[3] == "p"

        await state.update_data(
            edit_channel_id=channel_id,
            edit_post_num=post_num,
            edit_is_premium=is_premium
        )

        await call.message.edit_text(
            "<b>Yangi vaqtni kiriting</b>\n\n"
            "Format: HH:MM (masalan 09:30)"
        )
        await state.set_state(EditChannelPost.EDIT_TIME)
    except Exception as e:
        logger.error(f"Error in request_new_time: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def process_new_time(message: Message, state: FSMContext):
    try:
        if not validate_time_format(message.text):
            await message.answer(
                "Vaqt noto'g'ri formatda. To'g'ri format: HH:MM (masalan 09:30)"
            )
            return

        data = await state.get_data()
        channel_id = data.get("edit_channel_id")
        post_num = data.get("edit_post_num")
        is_premium = data.get("edit_is_premium")

        try:
            db.update_single_post(channel_id, post_num, time=message.text, premium=is_premium)
        except ValueError:
            await message.answer(
                "Bu kanal post vaqti oxirgi tahrirdan 24 soat o'tmagani uchun o'zgartirib bo'lmaydi. Keyinroq urinib ko'ring.",
                reply_markup=back_to_main
            )
            await state.clear()
            return

        await message.answer(
            "Vaqt muvaffaqiyatli o'zgartirildi!",
            reply_markup=back_to_main
        )
        await state.clear()

        logger.info(f"Post {post_num} time updated for channel {channel_id}")
    except Exception as e:
        logger.error(f"Error in process_new_time: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi", reply_markup=back_to_main)
        await state.clear()


async def request_new_theme(call: CallbackQuery, state: FSMContext):
    try:
        from config import MAX_THEME_WORDS_FREE, MAX_THEME_WORDS_PREMIUM

        parts = call.data.split(":")
        channel_id = int(parts[1])
        post_num = int(parts[2])
        is_premium = parts[3] == "p"

        await state.update_data(
            edit_channel_id=channel_id,
            edit_post_num=post_num,
            edit_is_premium=is_premium
        )

        max_words = MAX_THEME_WORDS_PREMIUM if is_premium else MAX_THEME_WORDS_FREE
        await call.message.edit_text(
            f"<b>Yangi mavzuni kiriting</b>\n\n"
            f"Maksimal {max_words} so'z",
            parse_mode="HTML"
        )
        await state.set_state(EditChannelPost.EDIT_THEME)
    except Exception as e:
        logger.error(f"Error in request_new_theme: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def process_new_theme(message: Message, state: FSMContext):
    try:
        from utils.validators import validate_word_count
        from config import MAX_THEME_WORDS_FREE, MAX_THEME_WORDS_PREMIUM

        data = await state.get_data()
        channel_id = data.get("edit_channel_id")
        post_num = data.get("edit_post_num")
        is_premium = data.get("edit_is_premium")

        max_words = MAX_THEME_WORDS_PREMIUM if is_premium else MAX_THEME_WORDS_FREE
        is_valid, word_count = validate_word_count(message.text, max_words=max_words)
        if not is_valid:
            await message.answer(
                f"Mavzu {max_words} so'zdan oshmasligi kerak. "
                f"Siz {word_count} so'z kiritdingiz. Qayta kiriting."
            )
            return

        db.update_single_post(channel_id, post_num, theme=message.text, premium=is_premium)

        await message.answer(
            "Mavzu muvaffaqiyatli o'zgartirildi!",
            reply_markup=back_to_main
        )
        await state.clear()

        logger.info(f"Post {post_num} theme updated for channel {channel_id}")
    except Exception as e:
        logger.error(f"Error in process_new_theme: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi", reply_markup=back_to_main)
        await state.clear()


async def confirm_delete_post(call: CallbackQuery, state: FSMContext):
    try:
        parts = call.data.split(":")
        channel_id = int(parts[1])
        post_num = int(parts[2])
        is_premium = parts[3] == "p"

        await state.update_data(
            delete_post_channel_id=channel_id,
            delete_post_num=post_num,
            delete_post_is_premium=is_premium
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Ha, o'chirish", callback_data="delete_post_yes"),
                InlineKeyboardButton(text="Yo'q", callback_data="delete_post_no")
            ]
        ])

        await call.message.edit_text(
            "<b>Diqqat!</b>\n\n"
            f"Postni o'chirishni tasdiqlaysizmi?",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in confirm_delete_post: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def delete_post_confirmed(call: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        channel_id = data.get("delete_post_channel_id")
        post_num = data.get("delete_post_num")
        is_premium = data.get("delete_post_is_premium")

        db.delete_single_post(channel_id, post_num, premium=is_premium)

        await call.message.edit_text(
            "Post muvaffaqiyatli o'chirildi!",
            reply_markup=back_to_main
        )
        await state.clear()

        logger.info(f"Post {post_num} deleted from channel {channel_id}")
    except Exception as e:
        logger.error(f"Error in delete_post_confirmed: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)
        await state.clear()


async def cancel_delete_post(call: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        await call.message.edit_text(
            "Post o'chirish bekor qilindi.",
            reply_markup=back_to_main
        )
    except Exception as e:
        logger.error(f"Error in cancel_delete_post: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def add_post_start(call: CallbackQuery, state: FSMContext):
    from config import MAX_POSTS_FREE, MAX_POSTS_PREMIUM

    try:
        parts = call.data.split(":")
        channel_id = int(parts[1])
        is_premium = parts[2] == "p"

        max_posts = MAX_POSTS_PREMIUM if is_premium else MAX_POSTS_FREE
        current_posts = db.get_channel_posts(channel_id, premium=is_premium)

        if len(current_posts) >= max_posts:
            tier = "Premium" if is_premium else "Free"
            await call.answer(
                f"{tier} foydalanuvchi uchun maksimal {max_posts} ta post. Limitga yetdingiz!",
                show_alert=True
            )
            return

        next_post_num = db.get_next_available_post_num(channel_id, premium=is_premium)

        if next_post_num is None or next_post_num > max_posts:
            await call.answer("Bo'sh slot topilmadi!", show_alert=True)
            return

        await state.update_data(
            add_post_channel_id=channel_id,
            add_post_num=next_post_num,
            add_post_is_premium=is_premium
        )

        prefix = "p" if is_premium else "f"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Bekor qilish", callback_data=f"edit_ch:{channel_id}:{prefix}")]
        ])

        await call.message.edit_text(
            f"<b>Yangi post qo'shish</b>\n\n"
            f"Post raqami: {next_post_num}\n"
            f"Jami postlar: {len(current_posts)}/{max_posts}\n\n"
            f"<b>Post vaqtini kiriting</b>\n"
            f"Format: HH:MM (masalan 09:30)",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await state.set_state(EditChannelPost.ADD_POST_TIME)
    except Exception as e:
        logger.error(f"Error in add_post_start: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def process_add_post_time(message: Message, state: FSMContext):
    try:
        from config import MAX_THEME_WORDS_FREE, MAX_THEME_WORDS_PREMIUM

        if not validate_time_format(message.text):
            await message.answer(
                "Vaqt noto'g'ri formatda. To'g'ri format: HH:MM (masalan 09:30)"
            )
            return

        await state.update_data(add_post_time=message.text)

        data = await state.get_data()
        channel_id = data.get("add_post_channel_id")
        is_premium = data.get("add_post_is_premium")
        prefix = "p" if is_premium else "f"

        max_words = MAX_THEME_WORDS_PREMIUM if is_premium else MAX_THEME_WORDS_FREE

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Bekor qilish", callback_data=f"edit_ch:{channel_id}:{prefix}")]
        ])

        await message.answer(
            f"Vaqt qabul qilindi: <b>{message.text}</b>\n\n"
            f"<b>Endi post mavzusini kiriting</b>\n"
            f"Maksimal {max_words} so'z",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await state.set_state(EditChannelPost.ADD_POST_THEME)
    except Exception as e:
        logger.error(f"Error in process_add_post_time: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi", reply_markup=back_to_main)
        await state.clear()


async def process_add_post_theme(message: Message, state: FSMContext):
    try:
        from utils.validators import validate_word_count
        from config import IMAGE_MODE, MAX_THEME_WORDS_FREE, MAX_THEME_WORDS_PREMIUM
        from keyboards.inline import premium_image_toggle

        data = await state.get_data()
        channel_id = data.get("add_post_channel_id")
        post_num = data.get("add_post_num")
        post_time = data.get("add_post_time")
        is_premium = data.get("add_post_is_premium")

        max_words = MAX_THEME_WORDS_PREMIUM if is_premium else MAX_THEME_WORDS_FREE
        is_valid, word_count = validate_word_count(message.text, max_words=max_words)
        if not is_valid:
            await message.answer(
                f"Mavzu {max_words} so'zdan oshmasligi kerak. "
                f"Siz {word_count} so'z kiritdingiz. Qayta kiriting."
            )
            return

        await state.update_data(add_post_theme=message.text)

        if is_premium and IMAGE_MODE:
            await message.answer(
                f"Bu post uchun rasm qo'shasizmi?",
                reply_markup=premium_image_toggle
            )
            await state.set_state(EditChannelPost.ADD_POST_IMAGE)
        else:
            db.add_new_post(channel_id, post_num, post_time, message.text, premium=is_premium, with_image='no')

            await message.answer(
                f"<b>Post muvaffaqiyatli qo'shildi!</b>\n\n"
                f"Post raqami: {post_num}\n"
                f"Vaqt: {post_time}\n"
                f"Mavzu: {message.text}",
                reply_markup=back_to_main,
                parse_mode="HTML"
            )
            await state.clear()
            logger.info(f"New post {post_num} added to channel {channel_id}")
    except Exception as e:
        logger.error(f"Error in process_add_post_theme: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi", reply_markup=back_to_main)
        await state.clear()


async def process_add_post_image(call: CallbackQuery, state: FSMContext):
    try:
        await call.message.delete()

        data = await state.get_data()
        channel_id = data.get("add_post_channel_id")
        post_num = data.get("add_post_num")
        post_time = data.get("add_post_time")
        post_theme = data.get("add_post_theme")

        with_image = 'yes' if call.data == 'p_image_yes' else 'no'

        db.add_new_post(channel_id, post_num, post_time, post_theme, premium=True, with_image=with_image)

        image_text = "Rasm bilan" if with_image == 'yes' else "Rasmsiz"

        await call.message.answer(
            f"<b>Post muvaffaqiyatli qo'shildi!</b>\n\n"
            f"Post raqami: {post_num}\n"
            f"Vaqt: {post_time}\n"
            f"Mavzu: {post_theme}\n"
            f"Rasm: {image_text}",
            reply_markup=back_to_main,
            parse_mode="HTML"
        )
        await state.clear()
        logger.info(f"New post {post_num} added to channel {channel_id} (with_image={with_image})")
    except Exception as e:
        logger.error(f"Error in process_add_post_image: {e}", exc_info=True)
        await call.message.answer("Xatolik yuz berdi", reply_markup=back_to_main)
        await state.clear()
