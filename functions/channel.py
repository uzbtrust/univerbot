import logging
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram import Bot

from states import Channel
from keyboards.inline import make_bot_admin, make_bot_admin_back, back_to_main, admin_confirm
from keyboards.reply import channel_button
from utils.database import db
from utils.validators import validate_time_format, validate_word_count
from utils.helpers import get_post_number_from_text
from utils.message_utils import safe_delete, send_prompt, send_final, send_error
from config import MAX_POSTS_FREE, MAX_THEME_WORDS_FREE, MAX_CHANNELS_FREE

logger = logging.getLogger(__name__)


async def requesting_id_again(call: CallbackQuery, state: FSMContext):
    try:
        await safe_delete(call.message)
        await send_prompt(
            call, state,
            'Iltimos kanalinggizdan biror bir postni bu yerga yuboring',
            reply_markup=back_to_main
        )
        await state.set_state(Channel.ID)
    except Exception as e:
        logger.error(f"Error in requesting_id_again: {e}", exc_info=True)


async def requesting_id(call: CallbackQuery, state: FSMContext):
    try:
        user_id = call.from_user.id

        await safe_delete(call.message)

        channel_count = db.count_user_channels(user_id, premium=False)
        if channel_count >= MAX_CHANNELS_FREE:
            await send_error(
                call,
                f'⚠️ Siz maksimum {MAX_CHANNELS_FREE} ta kanal qo\'shishingiz mumkin.\n\n'
                f'Premium foydalanuvchi bo\'lsangiz, ko\'proq kanal qo\'shishingiz mumkin.',
                reply_markup=back_to_main
            )
            return

        await send_prompt(
            call, state,
            "<b>Kanal qo'shish bo'yicha ko'rsatma:</b>\n\n"
            "1. Botni kanalingizga qo'shing\n"
            "2. Botni kanalda ADMIN qiling\n"
            "3. Kanalingizdan biror postni bu yerga forward qiling\n\n"
            "Bot admin bo'lmasa, kanal qo'shilmaydi!",
            reply_markup=back_to_main,
            parse_mode="HTML"
        )
        await state.set_state(Channel.ID)
    except Exception as e:
        logger.error(f"Error in requesting_id: {e}", exc_info=True)


async def getting_id(message: Message, state: FSMContext):
    try:
        # Foydalanuvchi forward qilgan xabarni o'chirish (chat tozalik uchun)
        await safe_delete(message)

        if not message.forward_from_chat:
            # Xato xabar — o'chirilMAYDI
            await send_error(
                message,
                "Iltimos kanalingizdan post forward qiling",
                reply_markup=back_to_main
            )
            return

        channel_id = message.forward_from_chat.id
        user_id = message.from_user.id

        await state.update_data(channel_id=channel_id)

        if db.channel_exists(channel_id, premium=False):
            await send_error(
                message,
                "Bu kanal allaqachon qo'shilgan",
                reply_markup=back_to_main
            )
            await state.clear()
            return

        # Eski ko'rsatma xabarini o'chirib, yangi prompt yuborish
        await send_prompt(
            message, state,
            "Bot kanalda admin qilingizmi?",
            reply_markup=admin_confirm
        )
        await state.set_state(Channel.ADMIN_CONFIRM)
    except Exception as e:
        logger.error(f"Error in getting_id: {e}", exc_info=True)
        await send_error(message, "Xatolik yuz berdi", reply_markup=back_to_main)
        await state.clear()


async def admin_confirm_yes(call: CallbackQuery, state: FSMContext, bot: Bot):
    try:
        user_id = call.from_user.id
        data = await state.get_data()
        channel_id = data.get("channel_id")

        if not channel_id:
            await call.answer("Iltimos avval kanal postini yuboring", show_alert=True)
            await state.clear()
            return

        if db.channel_exists(channel_id, premium=False):
            await call.answer("Bu kanal allaqachon qo'shilgan", show_alert=True)
            await state.clear()
            return

        bot_id = (await bot.me()).id

        try:
            member = await bot.get_chat_member(channel_id, bot_id)
            if member.status in ("administrator", "creator"):
                if db.channel_exists(channel_id, premium=False):
                    await call.answer("Bu kanal allaqachon qo'shilgan", show_alert=True)
                    await state.clear()
                    return

                db.add_channel(channel_id, user_id, premium=False)

                # "Admin qilingizmi?" xabarini o'chirish + prompt
                await send_prompt(
                    call, state,
                    "Kanal qo'shildi!\n\nKanalinggizga bir kunda nechta post tashlamoqchisiz?",
                    reply_markup=channel_button
                )
                await state.update_data(channel_id=channel_id)
                logger.info(f"Channel {channel_id} added for user {user_id}")
            else:
                await call.answer("Bot hali admin emas. Iltimos botni kanalda admin qiling.", show_alert=True)
        except Exception as e:
            logger.error(f"Error checking bot admin status: {e}")
            await call.answer("Iltimos botni kanalda admin qiling", show_alert=True)
    except Exception as e:
        logger.error(f"Error in admin_confirm_yes: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def admin_confirm_no(call: CallbackQuery, state: FSMContext):
    try:
        await call.message.edit_text(
            "Iltimos botni kanalinggizga qo'shib admin qiling.\n\n"
            "Admin qilganingizdan keyin \"Ha\" tugmasini bosing.",
            reply_markup=admin_confirm
        )
    except Exception as e:
        logger.error(f"Error in admin_confirm_no: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def select_post_number(message: Message, state: FSMContext):
    try:
        # Foydalanuvchi "1 marta" matnini o'chirish
        await safe_delete(message)

        post_count = get_post_number_from_text(message.text)

        if not post_count or post_count > MAX_POSTS_FREE:
            await send_error(
                message,
                f"Iltimos 1 dan {MAX_POSTS_FREE} gacha raqam tanlang"
            )
            return

        user_id = message.from_user.id
        data = await state.get_data()
        channel_id = data.get('channel_id')

        if not channel_id:
            channels = db.get_user_channels(user_id, premium=False)
            if channels:
                channel_id = channels[0][1]
            else:
                await send_error(message, "Xatolik: Kanal topilmadi", reply_markup=back_to_main)
                await state.clear()
                return

        await state.update_data(post_count=post_count, current_post=1, channel_id=channel_id)
        # Eski "Kanal qo'shildi" xabarini o'chirish + yangi prompt
        await send_prompt(
            message, state,
            "Iltimos 1-post uchun vaqtni kiriting (HH:MM)",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(Channel.POST_TIME)
    except Exception as e:
        logger.error(f"Error in select_post_number: {e}", exc_info=True)
        await send_error(message, "Xatolik yuz berdi", reply_markup=back_to_main)
        await state.clear()


async def insert_time(message: Message, state: FSMContext):
    try:
        # Foydalanuvchi kiritgan vaqtni o'chirish
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
            # Xato — o'chirilmaydi
            await send_error(
                message,
                "Vaqt noto'g'ri formatda. To'g'ri format: HH:MM (masalan 09:30)"
            )
            return

        user_id = message.from_user.id
        channel_id = data.get('channel_id')

        if not channel_id:
            channels = db.get_user_channels(user_id, premium=False)
            if channels:
                channel_id = channels[0][1]
            else:
                await send_error(message, "Xatolik: Kanal topilmadi", reply_markup=back_to_main)
                await state.clear()
                return

        await state.update_data(**{f"post{current_post}_time": message.text, "channel_id": channel_id})
        # Eski "vaqtni kiriting" promptini o'chirib, yangi prompt
        await send_prompt(
            message, state,
            f"Endi {current_post}-post uchun mavzuni kiriting (maks {MAX_THEME_WORDS_FREE} so'z)"
        )
        await state.set_state(Channel.POST_THEME)
    except Exception as e:
        logger.error(f"Error in insert_time: {e}", exc_info=True)
        await send_error(message, "Xatolik yuz berdi", reply_markup=back_to_main)
        await state.clear()


async def insert_theme(message: Message, state: FSMContext):
    try:
        # Foydalanuvchi kiritgan mavzuni o'chirish
        await safe_delete(message)

        data = await state.get_data()
        current_post = data.get("current_post", 1)
        post_count = data.get("post_count", 1)

        if not message.text:
            await send_error(
                message,
                f"Iltimos faqat matn kiriting.\nMavzu {MAX_THEME_WORDS_FREE} so'zdan oshmasligi kerak."
            )
            return

        is_valid, word_count = validate_word_count(message.text, max_words=MAX_THEME_WORDS_FREE)
        if not is_valid:
            await send_error(
                message,
                f"Mavzu {MAX_THEME_WORDS_FREE} so'zdan oshmasligi kerak. "
                f"Siz {word_count} so'z kiritdingiz. Qayta kiriting."
            )
            return

        user_id = message.from_user.id
        channel_id = data.get('channel_id')

        if not channel_id:
            channels = db.get_user_channels(user_id, premium=False)
            if channels:
                channel_id = channels[0][1]
            else:
                await send_error(message, "Xatolik: Kanal topilmadi", reply_markup=back_to_main)
                await state.clear()
                return

        time_value = data.get(f"post{current_post}_time")
        theme_value = message.text

        await state.update_data(**{f"post{current_post}_theme": theme_value, "channel_id": channel_id})

        db.update_channel_post(channel_id, current_post, time_value, theme_value, premium=False, skip_24h_check=True)

        if current_post < post_count:
            await state.update_data(current_post=current_post + 1, channel_id=channel_id)
            # Eski "mavzuni kiriting" promptini o'chirish + yangi prompt
            await send_prompt(
                message, state,
                f"Iltimos {current_post+1}-post uchun vaqtni kiriting (HH:MM)"
            )
            await state.set_state(Channel.POST_TIME)
        else:
            # Yakuniy muvaffaqiyat xabari — o'chirilMAYDI
            await send_final(
                message, state,
                "Barcha vaqt va mavzular muvaffaqiyatli saqlandi!",
                reply_markup=back_to_main
            )
            await state.clear()
            logger.info(f"Channel {channel_id} fully configured with {post_count} posts")
    except Exception as e:
        logger.error(f"Error in insert_theme: {e}", exc_info=True)
        await send_error(message, "Xatolik yuz berdi", reply_markup=back_to_main)
        await state.clear()


async def handle_image_toggle(call: CallbackQuery, state: FSMContext):
    try:
        await safe_delete(call.message)

        data = await state.get_data()
        current_post = data.get("current_post", 1)
        post_count = data.get("post_count", 1)
        user_id = call.from_user.id

        channel_id = data.get('channel_id')

        if not channel_id:
            await send_error(call, "Xatolik: Kanal topilmadi", reply_markup=back_to_main)
            await state.clear()
            return

        time_value = data.get(f"post{current_post}_time")
        theme_value = data.get(f"post{current_post}_theme")

        has_image = call.data == 'image_yes'

        await state.update_data(**{f"post{current_post}_has_image": has_image})

        db.update_channel_post(channel_id, current_post, time_value, theme_value, premium=False, skip_24h_check=True)

        if current_post < post_count:
            await state.update_data(current_post=current_post + 1, channel_id=channel_id)
            await send_prompt(
                call, state,
                f"Iltimos {current_post+1}-post uchun vaqtni kiriting (HH:MM)",
                reply_markup=ReplyKeyboardRemove()
            )
            await state.set_state(Channel.POST_TIME)
        else:
            await send_final(
                call, state,
                "Barcha vaqt va mavzular muvaffaqiyatli saqlandi!",
                reply_markup=back_to_main
            )
            await state.clear()
            logger.info(f"Channel {channel_id} fully configured with {post_count} posts")
    except Exception as e:
        logger.error(f"Error in handle_image_toggle: {e}", exc_info=True)
        await send_error(call, "Xatolik yuz berdi", reply_markup=back_to_main)
        await state.clear()
