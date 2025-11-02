import telebot
from telebot import types
import json
from datetime import datetime
from types import SimpleNamespace

# Импортируем модули игр
import leaders
import mines
import tower
import gold
import games
from states import register_stats_handlers, stats_manager
from balloon import register_balloon_handlers
from knb import register_rps_handlers
from coin import register_coin_handlers
from crash import register_crash_handlers
from tomb import register_tomb_handlers
from roulette import register_roulette_handlers
import admin_commands

bot = telebot.TeleBot("8073627025:AAFOQnnP9UBrS3blo4MhgetJVwC9XYEbvWk")

# Регистрируем хендлеры из модулей
leaders.register_leaders_handlers(bot)
mines.register_mines_handlers(bot)
tower.register_tower_handlers(bot)
gold.register_gold_handlers(bot)
games.register_games_handlers(bot)
register_stats_handlers(bot, stats_manager)
register_balloon_handlers(bot)
register_rps_handlers(bot)
register_coin_handlers(bot)
register_crash_handlers(bot)
register_tomb_handlers(bot)
register_roulette_handlers(bot)
admin_commands.register_admin_handlers(bot)

def load_users_data():
    try:
        with open('users_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users_data(data):
    with open('users_data.json', 'w') as f:
        json.dump(data, f)

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("🎮 Игры"), types.KeyboardButton("👤 Профиль"))
    markup.row(types.KeyboardButton("📊 Статистика"), types.KeyboardButton("🏆 Лидерство"))
    markup.row(types.KeyboardButton("ℹ️ Информация"))
    return markup

def games_inline_menu():
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("   💣 Мины   ", callback_data="game_mines"),
        types.InlineKeyboardButton("   🏰 Башня   ", callback_data="game_tower")
    )
    markup.row(
        types.InlineKeyboardButton("   💰 Золото   ", callback_data="game_gold"),
        types.InlineKeyboardButton("   🎲 Кости   ", callback_data="game_dice"),
        types.InlineKeyboardButton("   🎯 Дартс   ", callback_data="game_darts")
    )
    markup.row(
        types.InlineKeyboardButton("   ⚽ Футбол   ", callback_data="game_football"),
        types.InlineKeyboardButton("   🏀 Баскетбол   ", callback_data="game_basketball")
    )
    markup.row(
        types.InlineKeyboardButton("   🎰 Рулетка   ", callback_data="game_roulette"),
        types.InlineKeyboardButton("   🪙 Орел-Решка   ", callback_data="game_coin")
    )
    markup.row(
        types.InlineKeyboardButton("   🚀 Краш   ", callback_data="game_crash"),
        types.InlineKeyboardButton("   ⚰️ Гробница   ", callback_data="game_tomb")
    )
    markup.row(
        types.InlineKeyboardButton("   🎈 Шарик   ", callback_data="game_balloon"),
        types.InlineKeyboardButton("   🎮 КНБ   ", callback_data="game_rps")
    )
    return markup

@bot.message_handler(commands=['start'])
def start_message(message):
    users_data = load_users_data()
    user_id = str(message.from_user.id)

    if user_id not in users_data:
        users_data[user_id] = {
            'first_seen': datetime.now().isoformat(),
            'balance': 0,
            'level': 1
        }
        save_users_data(users_data)

    bot.send_message(
        message.chat.id,
        f"👋 Добро пожаловать в казино бот!\n\n"
        f"💵 Баланс отображается в долларах ($)\n"
        f"🎯 Удачи в игре!",
        reply_markup=main_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('game_'))
def game_callback_handler(call):
    print(f"[DEBUG] Нажата игра: {call.data}")

    game_type = call.data.split('_')[1]
    chat_id = call.message.chat.id
    user = call.from_user
    bot.answer_callback_query(call.id)

    # создаем фейковое сообщение для запуска обработчиков игр
    fake_message = SimpleNamespace(
        chat=SimpleNamespace(id=chat_id),
        from_user=user,
        text=""
    )

    # ======== Игры ========
    mapping = {
        "mines": ("💣 Мины", "mines_start"),
        "tower": ("🏰 Башня", "tower_start"),
        "gold": ("💰 Золото", "gold_start"),
        "roulette": ("🎰 Рулетка", "roulette_start"),
        "coin": ("🪙 Орел-Решка", "coin_start"),
        "crash": ("🚀 Краш", "crash_start"),
        "tomb": ("⚰️ Гробница", "tomb_start"),
        "balloon": ("🎈 Шарик", "balloon_start"),
        "rps": ("🎮 КНБ", "rps_start"),
        # Игры из games модуля - используем правильные названия функций
        "dice": ("🎲 Кости", "games_start"),
        "darts": ("🎯 Дартс", "games_start"),
        "football": ("⚽ Футбол", "games_start"),
        "basketball": ("🏀 Баскетбол", "games_start")
    }

    if game_type in mapping:
        text, func_name = mapping[game_type]
        fake_message.text = text

        found = False
        for handler in bot.message_handlers:
            try:
                if handler['function'].__name__ == func_name:
                    handler['function'](fake_message)
                    found = True
                    break
            except Exception as e:
                print(f"[ERROR] Ошибка запуска {func_name}: {e}")

        if not found:
            # Если не нашли по имени функции, ищем по тексту сообщения
            fake_message.text = text
            for handler in bot.message_handlers:
                try:
                    if hasattr(handler, 'filters') and handler.filters and handler.filters(fake_message):
                        handler['function'](fake_message)
                        found = True
                        break
                except:
                    continue
            
            if not found:
                bot.send_message(chat_id, f"❌ Обработчик игры '{text}' не найден.")
    else:
        bot.send_message(chat_id, f"❌ Неизвестная игра '{game_type}'.")

@bot.message_handler(content_types=['text'])
def menu_handler(message):
    text = message.text
    user = message.from_user
    user_id = str(user.id)
    users_data = load_users_data()

    if text == "👤 Профиль":
        if user_id in users_data:
            user_info = users_data[user_id]
            username = user.username if user.username else user.first_name
            level = user_info.get('level', 1)
            balance = user_info.get('balance', 0)
            balance_rounded = round(balance, 2)
            first_seen = datetime.fromisoformat(user_info['first_seen'])
            days_in_project = (datetime.now() - first_seen).days

            profile_text = (
                "👤Ваш профиль⬇️:\n"
                "════════════════════\n"
                f"👥 Ник: @{username}\n"
                f"🆔 ID: {user_id}\n"
                f"🏅 Уровень: {level}\n"
                f"👛 Баланс: {balance_rounded}$\n"
                f"📅 В проекте: {days_in_project} дней\n"
                "════════════════════"
            )
        else:
            profile_text = "❌ Информация о вашем профиле не найдена."

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📥 Пополнить", callback_data="profile_deposit"),
            types.InlineKeyboardButton("📤 Вывести", callback_data="profile_withdraw")
        )
        bot.send_message(message.chat.id, profile_text, reply_markup=markup)

    elif text == "📊 Статистика":
        bot.send_message(message.chat.id, "📊 Твоя статистика: пока что пусто.")

    elif text == "ℹ️ Информация":
        bot.send_message(message.chat.id, "ℹ️ Это тестовая версия казино бота.")

    elif text == "🎮 Игры":
        bot.send_message(
            message.chat.id,
            "🎮 Меню игр:",
            reply_markup=games_inline_menu()
        )

    elif text == "⬅️ Назад":
        bot.send_message(message.chat.id, "⬅️ Возврат в главное меню.", reply_markup=main_menu())

    else:
        bot.send_message(message.chat.id, "❌ Неизвестная команда.", reply_markup=main_menu())

print("Бот запущен...")
bot.infinity_polling()