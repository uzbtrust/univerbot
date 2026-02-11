from aiogram.fsm.state import StatesGroup, State

class Channel(StatesGroup):
    ID = State()
    ADMIN_CONFIRM = State()
    POST_TIME = State()
    POST_THEME = State()
    IMAGE_TOGGLE = State()

class PremiumChannel(StatesGroup):
    ID = State()
    ADMIN_CONFIRM = State()
    POST_TIME = State()
    POST_THEME = State()
    IMAGE_TOGGLE = State()

class Payment(StatesGroup):
    CHEQUE_WEEKLY = State()
    CHEQUE_DAY15 = State()
    CHEQUE_MONTHLY = State()

class ChangeTimeState(StatesGroup):
    waiting_for_time = State()

class ChangeThemeState(StatesGroup):
    waiting_for_theme = State()

class ChangeTimePremiumState(StatesGroup):
    waiting_for_time = State()

class ChangeThemePremiumState(StatesGroup):
    waiting_for_theme = State()

class AdminPanel(StatesGroup):
    BROADCAST_MESSAGE = State()
    CONFIRM_BROADCAST = State()
    EDIT_CARD_NUMBER = State()
    EDIT_CARD_NAME = State()
    EDIT_CARD_SURNAME = State()
    EDIT_WEEKLY_PRICE = State()
    EDIT_DAY15_PRICE = State()
    EDIT_MONTHLY_PRICE = State()
    EDIT_MAX_POSTS_FREE = State()
    EDIT_MAX_POSTS_PREMIUM = State()
    EDIT_MAX_CHANNELS_FREE = State()
    EDIT_MAX_CHANNELS_PREMIUM = State()
    EDIT_MAX_THEME_WORDS_FREE = State()
    EDIT_MAX_THEME_WORDS_PREMIUM = State()
    EDIT_SUPER_ADMIN2 = State()
    WAITING_ADMIN2_FORWARD = State()

class DeleteChannel(StatesGroup):
    CONFIRM_DELETE = State()

class EditChannelPost(StatesGroup):
    EDIT_TIME = State()
    EDIT_THEME = State()
    ADD_POST_TIME = State()
    ADD_POST_THEME = State()
    ADD_POST_IMAGE = State()

class TechnicalSupport(StatesGroup):
    WAITING_MESSAGE = State()


class AddPost(StatesGroup):
    SELECT_CHANNEL = State()
    POST_TIME = State()
    POST_THEME = State()
    IMAGE_TOGGLE = State()
