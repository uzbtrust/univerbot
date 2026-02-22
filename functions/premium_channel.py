import logging
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from states import PremiumChannel
from keyboards.inline import p_make_bot_admin, p_make_bot_admin_back, p_back_to_main, premium_admin_confirm, premium_image_toggle
from keyboards.reply import premium_channel_button
from utils.database import db
from utils.validators import validate_time_format, validate_word_count
from utils.helpers import get_post_number_from_text
from utils.message_utils import safe_delete, send_prompt, send_final, send_error
from config import MAX_POSTS_PREMIUM, MAX_CHANNELS_PREMIUM, STICKERS, MESSAGES, IMAGE_MODE, MAX_THEME_WORDS_PREMIUM

logger = logging.getLogger(__name__)


async def requesting_id_again(call: CallbackQuery, state: FSMContext):
    try:
        await safe_delete(call.message)
        await send_prompt(
            call, state,
            'Iltimos kanalinggizdan biror bir postni bu yerga yuboring',
            reply_markup=p_back_to_main
        )
        await state.set_state(PremiumChannel.ID)
    except Exception as e:
        logger.error(f"Error in requesting_id_again: {e}", exc_info=True)


async def requesting_id(call: CallbackQuery, state: FSMContext):
    try:
        user_id = call.from_user.id

        await safe_delete(call.message)

        channel_count = db.count_user_channels(user_id, premium=True)
        if channel_count >= MAX_CHANNELS_PREMIUM:
            await send_error(
                call,
                f'Siz premium foydalanuvchi bo\'lsangiz ham, '
                f'faqat {MAX_CHANNELS_PREMIUM} ta kanal qo\'shishingiz mumkin.',
                reply_markup=p_back_to_main
            )
            return

        await send_prompt(
            call, state,
            "<b>Kanal qo'shish bo'yicha ko'rsatma:</b>\n\n"
            "1. Botni kanalingizga qo'shing\n"
            "2. Botni kanalda ADMIN qiling\n"
            "3. Kanalingizdan biror postni bu yerga forward qiling\n\n"
            "Bot admin bo'lmasa, kanal qo'shilmaydi!",
            reply_markup=p_back_to_main,
            parse_mode="HTML"
        )
        await state.set_state(PremiumChannel.ID)
    except Exception as e:
        logger.error(f"Error in requesting_id: {e}", exc_info=True)


async def getting_id(message: Message, state: FSMContext):
    try:
        await safe_delete(message)

        if not message.forward_from_chat:
            await send_error(
                message,
                "Iltimos kanalingizdan post forward qiling",
                reply_markup=p_back_to_main
            )
            return

        channel_id = message.forward_from_chat.id
        user_id = message.from_user.id

        await state.update_data(channel_id=channel_id)

        if db.channel_exists(channel_id, premium=True):
            await send_error(
                message,
                "Bu kanal allaqachon qo'shilgan",
                reply_markup=p_back_to_main
            )
            await state.clear()
            return

        await send_prompt(
            message, state,
            "Bot kanalda admin qilingizmi?",
            reply_markup=premium_admin_confirm
        )
        await state.set_state(PremiumChannel.ADMIN_CONFIRM)
    except Exception as e:
        logger.error(f"Error in getting_id: {e}", exc_info=True)
        await send_error(message, "Xatolik yuz berdi", reply_markup=p_back_to_main)
        await state.clear()


async def premium_admin_confirm_yes(call: CallbackQuery, state: FSMContext, bot: Bot):
    try:
        user_id = call.from_user.id
        data = await state.get_data()
        channel_id = data.get("channel_id")

        if not channel_id:
            await call.answer("Iltimos avval kanal postini yuboring", show_alert=True)
            await state.clear()
            return

        if db.channel_exists(channel_id, premium=True):
            await call.answer("Bu kanal allaqachon qo'shilgan", show_alert=True)
            await state.clear()
            return

        bot_id = (await bot.me()).id

        try:
            member = await bot.get_chat_member(channel_id, bot_id)
            if member.status in ("administrator", "creator"):
                if db.channel_exists(channel_id, premium=True):
                    await call.answer("Bu kanal allaqachon qo'shilgan", show_alert=True)
                    await state.clear()
                    return

                db.add_channel(channel_id, user_id, premium=True)

                success_message = (
                    "KANAL QO'SHILDI!\n\n"
                    "<b>Tabriklaymiz!</b>\n\n"
                    "Premium kanalingiz tizimga muvaffaqiyatli qo'shildi.\n\n"
                    "<b>Keyingi qadam:</b>\n"
                    "Kanalinggizga bir kunda nechta post tashlamoqchisiz?"
                )

                await send_prompt(
                    call, state,
                    success_message,
                    reply_markup=premium_channel_button,
                    parse_mode='HTML'
                )
                await state.update_data(channel_id=channel_id)
                logger.info(f"Premium channel {channel_id} added for user {user_id}")
            else:
                await call.answer("Bot hali admin emas. Iltimos botni kanalda admin qiling.", show_alert=True)
        except Exception as e:
            logger.error(f"Error checking bot admin status: {e}")
            await call.answer("Iltimos botni kanalda admin qiling", show_alert=True)
    except Exception as e:
        logger.error(f"Error in premium_admin_confirm_yes: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def premium_admin_confirm_no(call: CallbackQuery, state: FSMContext):
    try:
        await call.message.edit_text(
            "Iltimos botni kanalinggizga qo'shib admin qiling.\n\n"
            "Admin qilganingizdan keyin \"Ha\" tugmasini bosing.",
            reply_markup=premium_admin_confirm
        )
    except Exception as e:
        logger.error(f"Error in premium_admin_confirm_no: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def select_post_number(message: Message, state: FSMContext):
    try:
        await safe_delete(message)

        post_count = get_post_number_from_text(message.text)

        if not post_count or post_count > MAX_POSTS_PREMIUM:
            await send_error(
                message,
                f"Iltimos 1 dan {MAX_POSTS_PREMIUM} gacha raqam tanlang"
            )
            return

        user_id = message.from_user.id
        data = await state.get_data()
        channel_id = data.get('channel_id')

        if not channel_id:
            channels = db.get_user_channels(user_id, premium=True)
            if channels:
                channel_id = channels[-1][1]
            else:
                await send_error(message, "Xatolik: Kanal topilmadi", reply_markup=p_back_to_main)
                await state.clear()
                return

        await state.update_data(post_count=post_count, current_post=1, channel_id=channel_id)
        await send_prompt(
            message, state,
            "Iltimos 1-post uchun vaqtni kiriting (HH:MM)",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(PremiumChannel.POST_TIME)
    except Exception as e:
        logger.error(f"Error in select_post_number: {e}", exc_info=True)
        await send_error(message, "Xatolik yuz berdi", reply_markup=p_back_to_main)
        await state.clear()


async def insert_time(message: Message, state: FSMContext):
    try:
        await safe_delete(message)

        data = await state.get_data()
        current_post = data.get("current_post", 1)

        if not message.text:
            await send_error(
                message,
                "Iltimos faqat matn kiriting.\nFormat: HH:MM (masalan 09:30)"
            )
            return

        if not validate_time_format(message.text):
            await send_error(
                message,
                "Vaqt noto'g'ri formatda. To'g'ri format: HH:MM (masalan 09:30)"
            )
            return

        user_id = message.from_user.id
        channel_id = data.get('channel_id')

        if not channel_id:
            channels = db.get_user_channels(user_id, premium=True)
            if channels:
                channel_id = channels[-1][1]
            else:
                await send_error(message, "Xatolik: Kanal topilmadi", reply_markup=p_back_to_main)
                await state.clear()
                return

        await state.update_data(**{f"post{current_post}_time": message.text, "channel_id": channel_id})
        await send_prompt(
            message, state,
            f"Endi {current_post}-post uchun mavzuni kiriting (maks {MAX_THEME_WORDS_PREMIUM} so'z)"
        )
        await state.set_state(PremiumChannel.POST_THEME)
    except Exception as e:
        logger.error(f"Error in insert_time: {e}", exc_info=True)
        await send_error(message, "Xatolik yuz berdi", reply_markup=p_back_to_main)
        await state.clear()


async def insert_theme(message: Message, state: FSMContext):
    try:
        await safe_delete(message)

        data = await state.get_data()
        current_post = data.get("current_post", 1)
        post_count = data.get("post_count", 1)

        if not message.text:
            await send_error(
                message,
                f"Iltimos faqat matn kiriting.\nMavzu {MAX_THEME_WORDS_PREMIUM} so'zdan oshmasligi kerak."
            )
            return

        is_valid, word_count = validate_word_count(message.text, max_words=MAX_THEME_WORDS_PREMIUM)
        if not is_valid:
            await send_error(
                message,
                f"Mavzu {MAX_THEME_WORDS_PREMIUM} so'zdan oshmasligi kerak. "
                f"Siz {word_count} so'z kiritdingiz. Qayta kiriting."
            )
            return

        user_id = message.from_user.id
        channel_id = data.get('channel_id')

        if not channel_id:
            channels = db.get_user_channels(user_id, premium=True)
            if channels:
                channel_id = channels[-1][1]
            else:
                await send_error(message, "Xatolik: Kanal topilmadi", reply_markup=p_back_to_main)
                await state.clear()
                return

        time_value = data.get(f"post{current_post}_time")
        theme_value = message.text

        logger.info(f"insert_theme: channel_id={channel_id}, current_post={current_post}, time_value={time_value}, theme_value={theme_value}")

        await state.update_data(**{f"post{current_post}_theme": theme_value, "channel_id": channel_id})

        if IMAGE_MODE:
            await send_prompt(
                message, state,
                f"{current_post}-post uchun rasm qo'shasizmi?",
                reply_markup=premium_image_toggle
            )
            await state.set_state(PremiumChannel.IMAGE_TOGGLE)
        else:
            db.update_channel_post(channel_id, current_post, time_value, theme_value, premium=True, with_image='no', skip_24h_check=True)

            if current_post < post_count:
                await state.update_data(current_post=current_post + 1, channel_id=channel_id)
                await send_prompt(
                    message, state,
                    f"Iltimos {current_post+1}-post uchun vaqtni kiriting (HH:MM)",
                    reply_markup=ReplyKeyboardRemove()
                )
                await state.set_state(PremiumChannel.POST_TIME)
            else:
                await send_final(
                    message, state,
                    "Barcha vaqt va mavzular muvaffaqiyatli saqlandi!",
                    reply_markup=p_back_to_main
                )
                await state.clear()
                logger.info(f"Premium channel {channel_id} fully configured with {post_count} posts")
    except Exception as e:
        logger.error(f"Error in insert_theme: {e}", exc_info=True)
        await send_error(message, "Xatolik yuz berdi", reply_markup=p_back_to_main)
        await state.clear()


async def handle_premium_image_toggle(call: CallbackQuery, state: FSMContext):
    try:
        await safe_delete(call.message)

        data = await state.get_data()
        current_post = data.get("current_post", 1)
        post_count = data.get("post_count", 1)
        user_id = call.from_user.id

        channel_id = data.get('channel_id')

        if not channel_id:
            channels = db.get_user_channels(user_id, premium=True)
            if channels:
                channel_id = channels[-1][1]
            else:
                await send_error(call, "Xatolik: Kanal topilmadi", reply_markup=p_back_to_main)
                await state.clear()
                return

        time_value = data.get(f"post{current_post}_time")
        theme_value = data.get(f"post{current_post}_theme")

        logger.info(f"handle_premium_image_toggle: channel_id={channel_id}, current_post={current_post}, time_value={time_value}, theme_value={theme_value}")

        if not time_value or not theme_value:
            logger.warning(f"handle_premium_image_toggle: Skipping - time_value or theme_value is None (duplicate callback?)")
            await call.answer("Allaqachon saqlangan", show_alert=False)
            return

        has_image = 'yes' if call.data == 'p_image_yes' else 'no'

        await state.update_data(**{f"post{current_post}_has_image": has_image})

        db.update_channel_post(channel_id, current_post, time_value, theme_value, premium=True, with_image=has_image, skip_24h_check=True)
        logger.info(f"handle_premium_image_toggle: Post saved successfully!")

        if current_post < post_count:
            await state.update_data(current_post=current_post + 1, channel_id=channel_id)
            await send_prompt(
                call, state,
                f"Iltimos {current_post+1}-post uchun vaqtni kiriting (HH:MM)",
                reply_markup=ReplyKeyboardRemove()
            )
            await state.set_state(PremiumChannel.POST_TIME)
        else:
            await send_final(
                call, state,
                "Barcha vaqt va mavzular muvaffaqiyatli saqlandi!",
                reply_markup=p_back_to_main
            )
            await state.clear()
            logger.info(f"Premium channel {channel_id} fully configured with {post_count} posts")
    except Exception as e:
        logger.error(f"Error in handle_premium_image_toggle: {e}", exc_info=True)
        await send_error(call, "Xatolik yuz berdi", reply_markup=p_back_to_main)
        await state.clear()
