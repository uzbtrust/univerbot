import logging
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, BotCommand
from aiogram.fsm.context import FSMContext

from config import BOT_TOKEN, SUPER_ADMINS, ADMIN_GROUP_ID, TIMEZONE, LOG_LEVEL, LOG_FORMAT, MAX_POSTS_FREE, MAX_POSTS_PREMIUM
from logging_config import configure_logging
from functions.starting import greating
from functions.callback_functions import chanelling, premium, back
from functions import channel
from functions import premium_channel
from functions import premium_sub
from functions import my_chann
from functions import admin_panel
from functions import channel_management
from functions import tech_support
from functions import referral
from states import (
    Channel, PremiumChannel, Payment,
    ChangeTimeState, ChangeThemeState,
    ChangeTimePremiumState, ChangeThemePremiumState,
    AdminPanel, DeleteChannel, EditChannelPost, TechnicalSupport,
    RejectReason
)
from utils.database import db
from utils.backup import create_backup, cleanup_old_backups
from services.post_scheduler import PostScheduler

configure_logging(LOG_LEVEL)
logger = logging.getLogger("bot")


class BotManager:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.scheduler = None
        self._stop_event = asyncio.Event()
        self._tz = ZoneInfo(TIMEZONE)

    async def _daily_tasks_loop(self):
        """Har kuni 00:00 da backup + statistika yozish."""
        while not self._stop_event.is_set():
            try:
                now = datetime.now(self._tz)
                # Keyingi 00:00 gacha qancha vaqt qolganini hisoblash
                tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0)
                if now.hour > 0 or now.minute > 0 or now.second > 0:
                    tomorrow += timedelta(days=1)
                sleep_seconds = (tomorrow - now).total_seconds()
                logger.info(f"Keyingi kunlik vazifalar: {sleep_seconds:.0f}s qoldi (00:00)")

                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=sleep_seconds)
                    break  # stop_event set bo'ldi
                except asyncio.TimeoutError:
                    pass  # Vaqt keldi, davom etamiz

                # 00:00 — Kunlik vazifalar
                logger.info("Kunlik vazifalar boshlanmoqda (00:00)...")

                # 1. Statistikani yozish
                try:
                    await db.record_daily_stats()
                    logger.info("Kunlik statistika yozildi")
                except Exception as e:
                    logger.error(f"Kunlik statistika xatolik: {e}")

                # 2. Backup yaratish
                try:
                    today_str = datetime.now(self._tz).strftime("%Y-%m-%d")
                    backup_path = await create_backup(f"backup_{today_str}.sql")
                    if backup_path:
                        logger.info(f"Kunlik backup tayyor: {backup_path}")
                    cleanup_old_backups(keep_last=7)
                except Exception as e:
                    logger.error(f"Kunlik backup xatolik: {e}")

            except Exception as e:
                logger.error(f"Daily tasks loop xatolik: {e}", exc_info=True)
                await asyncio.sleep(60)

    async def on_startup(self, bot: Bot):
        await db.initialize()

        for admin_id in SUPER_ADMINS:
            await db.add_superadmin(admin_id)

        commands = [
            BotCommand(command="start", description="Botni ishga tushirish"),
            BotCommand(command="channels", description="Kanallarni boshqarish"),
            BotCommand(command="premium", description="Premium sotib olish"),
            BotCommand(command="referral", description="Ramazon sovg'asi 🎁"),
            BotCommand(command="help", description="Yordam"),
        ]
        await bot.set_my_commands(commands)

        self.scheduler = PostScheduler(bot)
        asyncio.create_task(self.scheduler.run(stop_event=self._stop_event))

        # Kunlik vazifalar loopini ishga tushirish (00:00 da backup + stats)
        asyncio.create_task(self._daily_tasks_loop())

        # Boshlang'ich statistikani yozish
        try:
            await db.record_daily_stats()
        except Exception as e:
            logger.warning(f"Daily stats record failed: {e}")

        try:
            await bot.send_message(chat_id=ADMIN_GROUP_ID, text="🚀 Bot va Post Scheduler ishga tushdi")
        except Exception as e:
            logger.warning(f"Startup notification failed: {e}")
        logger.info("Bot and Post Scheduler started successfully")

    async def on_shutdown(self, bot: Bot):
        if self.scheduler:
            self._stop_event.set()
            self.scheduler.stop()

        await db.close_all()

        try:
            await bot.send_message(chat_id=ADMIN_GROUP_ID, text="🛑 Bot to'xtatildi")
        except Exception as e:
            logger.warning(f"Shutdown notification failed: {e}")
        logger.info("Bot shutdown")

    def register_handlers(self):
        self.dp.startup.register(self.on_startup)
        self.dp.shutdown.register(self.on_shutdown)

        # Guruhda admin reply handler (texnik yordam + chek suhbat) — BIRINCHI
        async def handle_admin_group_reply(message: Message):
            await tech_support.handle_group_reply(message, self.bot, self.dp.storage)

        self.dp.message.register(
            handle_admin_group_reply,
            F.chat.id == ADMIN_GROUP_ID,
            F.reply_to_message
        )

        self.dp.message.register(greating, CommandStart())
        self.dp.message.register(channel_management.show_channels_list_cmd, Command("channels"))
        self.dp.message.register(premium_sub.show_premium_cmd, Command("premium"))
        self.dp.message.register(self.help_command, Command("help"))

        self.dp.callback_query.register(chanelling, F.data == "channel")
        self.dp.callback_query.register(premium, F.data == "premium")
        self.dp.callback_query.register(back, F.data == "sub_back")
        self.dp.callback_query.register(greating, F.data.in_(["back", "p_back"]))

        self.dp.callback_query.register(channel_management.show_channels_for_add_post, F.data == "add_post")

        self.dp.callback_query.register(premium_sub.weekly, F.data == "weekly")
        self.dp.callback_query.register(premium_sub.day15, F.data == "day15")
        self.dp.callback_query.register(premium_sub.monthly, F.data == "monthly")
        self.dp.callback_query.register(premium_sub.approving, F.data.startswith("approve"))
        self.dp.callback_query.register(premium_sub.rejecting, F.data.startswith("reject"))

        self.dp.callback_query.register(channel.admin_confirm_yes, F.data == "admin_yes")
        self.dp.callback_query.register(channel.admin_confirm_no, F.data == "admin_no")
        self.dp.callback_query.register(channel.requesting_id_again, F.data == "another")
        self.dp.callback_query.register(premium_channel.premium_admin_confirm_yes, F.data == "p_admin_yes")
        self.dp.callback_query.register(premium_channel.premium_admin_confirm_no, F.data == "p_admin_no")
        self.dp.callback_query.register(premium_channel.requesting_id_again, F.data == "p_another")
        self.dp.callback_query.register(premium_channel.handle_premium_image_toggle, PremiumChannel.IMAGE_TOGGLE, F.data.in_(["p_image_yes", "p_image_no"]))

        self.dp.callback_query.register(my_chann.change_time, F.data.startswith("change_time:"))
        self.dp.callback_query.register(my_chann.change_theme, F.data.startswith("change_theme:"))
        self.dp.callback_query.register(my_chann.change_premium_time, F.data.startswith("change_time_premium:"))
        self.dp.callback_query.register(my_chann.change_premium_theme, F.data.startswith("change_theme_premium:"))
        self.dp.callback_query.register(my_chann.toggle_image_premium, F.data.startswith("toggle_image_premium:"))

        self.dp.callback_query.register(admin_panel.show_admin_panel, F.data == "admin_panel")
        self.dp.callback_query.register(admin_panel.show_statistics, F.data == "admin_stats")
        self.dp.callback_query.register(admin_panel.request_broadcast_message, F.data == "admin_broadcast")
        self.dp.callback_query.register(admin_panel.confirm_broadcast_handler, F.data == "confirm_broadcast")
        self.dp.callback_query.register(admin_panel.cancel_broadcast_handler, F.data == "cancel_broadcast")
        self.dp.callback_query.register(admin_panel.download_logs, F.data == "admin_logs")
        self.dp.callback_query.register(admin_panel.download_backup, F.data == "admin_backups")

        self.dp.callback_query.register(admin_panel.show_settings_menu, F.data == "admin_settings")
        self.dp.callback_query.register(admin_panel.show_payment_settings, F.data == "settings_payment")
        self.dp.callback_query.register(admin_panel.show_limits_settings, F.data == "settings_limits")
        self.dp.callback_query.register(admin_panel.toggle_image_mode, F.data == "settings_image")
        self.dp.callback_query.register(admin_panel.request_edit_value, F.data.in_([
            "edit_card_number", "edit_card_name", "edit_card_surname",
            "edit_weekly_price", "edit_day15_price", "edit_monthly_price",
            "edit_max_posts_free", "edit_max_posts_premium",
            "edit_max_channels_free", "edit_max_channels_premium",
            "edit_max_theme_words_free", "edit_max_theme_words_premium"
        ]))


        self.dp.callback_query.register(channel_management.show_channels_list, F.data == "manage_channels")
        self.dp.callback_query.register(channel_management.confirm_delete_channel, F.data.startswith("delete_ch:"))
        self.dp.callback_query.register(channel_management.delete_channel_confirmed, F.data == "confirm_delete_yes")
        self.dp.callback_query.register(channel_management.cancel_delete_channel, F.data == "confirm_delete_no")
        self.dp.callback_query.register(channel_management.show_edit_options, F.data.startswith("edit_ch:"))
        self.dp.callback_query.register(channel_management.show_posts_for_time_edit, F.data.startswith("edit_time:"))
        self.dp.callback_query.register(channel_management.show_posts_for_theme_edit, F.data.startswith("edit_theme:"))
        self.dp.callback_query.register(channel_management.show_posts_for_delete, F.data.startswith("delete_post:"))
        self.dp.callback_query.register(channel_management.add_post_start, F.data.startswith("add_post:"))
        self.dp.callback_query.register(channel_management.request_new_time, F.data.startswith("select_time:"))

        self.dp.callback_query.register(tech_support.request_support, F.data == "tech_support")

        # Referral handlers (Ramazon)
        self.dp.message.register(referral.show_ramadan_gift_cmd, Command("referral"))
        self.dp.callback_query.register(referral.show_ramadan_gift, F.data == "ramadan_gift")
        self.dp.callback_query.register(referral.show_referral_stats, F.data == "referral_stats")
        self.dp.callback_query.register(referral.show_admin_referral_stats, F.data == "admin_referral")

        self.dp.callback_query.register(channel_management.request_new_theme, F.data.startswith("select_theme:"))
        self.dp.callback_query.register(channel_management.confirm_delete_post, F.data.startswith("confirm_delete_post:"))
        self.dp.callback_query.register(channel_management.delete_post_confirmed, F.data == "delete_post_yes")
        self.dp.callback_query.register(channel_management.cancel_delete_post, F.data == "delete_post_no")

        self.dp.message.register(premium_channel.getting_id, PremiumChannel.ID)
        self.dp.message.register(premium_channel.insert_time, PremiumChannel.POST_TIME)
        self.dp.message.register(premium_channel.insert_theme, PremiumChannel.POST_THEME)
        self.dp.message.register(
            premium_channel.select_post_number,
            PremiumChannel.ADMIN_CONFIRM,
            F.text.in_([f"{i} marta" for i in range(1, MAX_POSTS_PREMIUM + 1)])
        )

        self.dp.message.register(channel.getting_id, Channel.ID)
        self.dp.message.register(channel.insert_time, Channel.POST_TIME)
        self.dp.message.register(channel.insert_theme, Channel.POST_THEME)
        self.dp.message.register(
            channel.select_post_number,
            Channel.ADMIN_CONFIRM,
            F.text.in_([f"{i} marta" for i in range(1, MAX_POSTS_FREE + 1)])
        )

        self.dp.message.register(premium_sub.weekly_check, Payment.CHEQUE_WEEKLY)
        self.dp.message.register(premium_sub.day15_check, Payment.CHEQUE_DAY15)
        self.dp.message.register(premium_sub.monthly_check, Payment.CHEQUE_MONTHLY)

        self.dp.message.register(my_chann.process_new_time, ChangeTimeState.waiting_for_time)
        self.dp.message.register(my_chann.process_new_theme, ChangeThemeState.waiting_for_theme)
        self.dp.message.register(my_chann.process_new_premium_time, ChangeTimePremiumState.waiting_for_time)
        self.dp.message.register(my_chann.process_new_premium_theme, ChangeThemePremiumState.waiting_for_theme)

        self.dp.message.register(admin_panel.receive_broadcast_message, AdminPanel.BROADCAST_MESSAGE)

        self.dp.message.register(admin_panel.process_edit_card_number, AdminPanel.EDIT_CARD_NUMBER)
        self.dp.message.register(admin_panel.process_edit_card_name, AdminPanel.EDIT_CARD_NAME)
        self.dp.message.register(admin_panel.process_edit_card_surname, AdminPanel.EDIT_CARD_SURNAME)
        self.dp.message.register(admin_panel.process_edit_price, AdminPanel.EDIT_WEEKLY_PRICE)
        self.dp.message.register(admin_panel.process_edit_price, AdminPanel.EDIT_DAY15_PRICE)
        self.dp.message.register(admin_panel.process_edit_price, AdminPanel.EDIT_MONTHLY_PRICE)
        self.dp.message.register(admin_panel.process_edit_posts_limit, AdminPanel.EDIT_MAX_POSTS_FREE)
        self.dp.message.register(admin_panel.process_edit_posts_limit, AdminPanel.EDIT_MAX_POSTS_PREMIUM)
        self.dp.message.register(admin_panel.process_edit_channels_limit, AdminPanel.EDIT_MAX_CHANNELS_FREE)
        self.dp.message.register(admin_panel.process_edit_channels_limit, AdminPanel.EDIT_MAX_CHANNELS_PREMIUM)
        self.dp.message.register(admin_panel.process_edit_theme_words_limit, AdminPanel.EDIT_MAX_THEME_WORDS_FREE)
        self.dp.message.register(admin_panel.process_edit_theme_words_limit, AdminPanel.EDIT_MAX_THEME_WORDS_PREMIUM)

        self.dp.message.register(channel_management.process_new_time, EditChannelPost.EDIT_TIME)
        self.dp.message.register(channel_management.process_new_theme, EditChannelPost.EDIT_THEME)
        self.dp.message.register(channel_management.process_add_post_time, EditChannelPost.ADD_POST_TIME)
        self.dp.message.register(channel_management.process_add_post_theme, EditChannelPost.ADD_POST_THEME)

        self.dp.callback_query.register(
            channel_management.process_add_post_image,
            EditChannelPost.ADD_POST_IMAGE,
            F.data.in_(["p_image_yes", "p_image_no"])
        )

        async def handle_support_message(message: Message, state: FSMContext):
            await tech_support.process_support_message(message, state, self.bot)

        self.dp.message.register(
            handle_support_message,
            TechnicalSupport.WAITING_MESSAGE
        )

        # User suhbat davomi (admin javobiga reply)
        async def handle_support_reply(message: Message, state: FSMContext):
            await tech_support.process_support_reply(message, state, self.bot)

        self.dp.message.register(
            handle_support_reply,
            TechnicalSupport.WAITING_REPLY
        )

        # Chek rad etish sababini yozish
        async def handle_reject_reason(message: Message, state: FSMContext):
            await premium_sub.process_reject_reason(message, state, self.bot)

        self.dp.message.register(
            handle_reject_reason,
            RejectReason.WAITING_REASON
        )

        logger.info("All handlers registered successfully")

    async def help_command(self, message: Message):
        help_text = (
            "<b>Yordam</b>\n\n"
            "<b>Asosiy buyruqlar:</b>\n"
            "/start - Botni ishga tushirish\n"
            "/channels - Kanallarni boshqarish\n"
            "/premium - Premium sotib olish\n"
            "/help - Yordam\n\n"
            "<b>Bot haqida:</b>\n"
            "Bu bot orqali siz kanallaringizga avtomatik post yuborishingiz mumkin.\n\n"
            "<b>Qanday ishlaydi:</b>\n"
            "1. Kanalni botga biriktiring\n"
            "2. Post vaqtini va mavzusini belgilang\n"
            "3. Bot avtomatik ravishda post yaratib yuboradi\n\n"
            "<b>Premium imkoniyatlari:</b>\n"
            "• 15 tagacha post\n"
            "• 3 ta kanal\n"
            "• AI rasm yaratish\n"
            "• Tezkor yordam"
        )
        await message.answer(help_text, parse_mode="HTML")

    async def start(self):
        try:
            self.register_handlers()
            logger.info("Starting bot polling...")
            await self.dp.start_polling(self.bot, polling_timeout=30)
        except Exception as e:
            logger.error(f"Error during bot operation: {e}", exc_info=True)
        finally:
            await self.bot.session.close()


async def main():
    bot_manager = BotManager()
    await bot_manager.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
