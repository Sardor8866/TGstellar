import telebot
from telebot import types
import random
import json
import time
import threading
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_users_data():
    try:
        with open('users_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        logging.error(f"Ошибка загрузки данных: {e}")
        return {}

def save_users_data(data):
    try:
        with open('users_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка сохранения данных: {e}")

# Потокобезопасный словарь для активных ставок и времени последнего нажатия
active_bets = {}
last_click_time = {}
bet_lock = threading.Lock()

# Минимальная и максимальная ставка
MIN_BET = 0.2
MAX_BET = 1000

def rate_limit(user_id):
    """Проверка ограничения по времени между нажатиями (0.4 секунды)"""
    current_time = time.time()
    with bet_lock:
        if user_id in last_click_time:
            if current_time - last_click_time[user_id] < 0.4:
                return False
        last_click_time[user_id] = current_time
    return True

def get_games_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎲 Кости", callback_data="games_dice"),
        types.InlineKeyboardButton("🏀 Баскетбол", callback_data="games_basketball"),
        types.InlineKeyboardButton("⚽ Футбол", callback_data="games_football"),
        types.InlineKeyboardButton("🎯 Дартс", callback_data="games_darts")
    )
    return markup

def get_bet_selection_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=5)
    bets = ["0.2", "0.5", "1", "3", "5"]
    buttons = [types.InlineKeyboardButton(f"${bet}", callback_data=f"games_bet_{bet}") for bet in bets]
    markup.row(*buttons)
    markup.row(types.InlineKeyboardButton("📝 Ввести вручную", callback_data="games_custom_bet"))
    return markup

# 🎲 КОСТИ
def get_dice_selection_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔴 Чет (1.8x)", callback_data="dice_even"),
        types.InlineKeyboardButton("⚫ Нечет (1.8x)", callback_data="dice_odd"),
        types.InlineKeyboardButton("📈 Больше 3 (1.8x)", callback_data="dice_high"),
        types.InlineKeyboardButton("📉 Меньше 4 (1.8x)", callback_data="dice_low")
    )
    return markup

def play_dice_game(bot, call, bet_type, bet_amount, user_id):
    try:
        # Показываем анимацию броска
        dice_msg = bot.send_dice(call.message.chat.id, emoji='🎲')

        # Ждем 3 секунды
        time.sleep(3)

        # Получаем результат
        dice_value = dice_msg.dice.value
        users_data = load_users_data()

        # Проверяем выигрыш с новой логикой
        win = False
        multiplier = 1.8

        if bet_type == "even" and dice_value in [2, 4, 6]:  # Четные: 2,4,6
            win = True
        elif bet_type == "odd" and dice_value in [1, 3, 5]:  # Нечетные: 1,3,5
            win = True
        elif bet_type == "high" and dice_value in [4, 5, 6]:  # Больше 3: 4,5,6
            win = True
        elif bet_type == "low" and dice_value in [1, 2, 3]:  # Меньше 4: 1,2,3
            win = True
        else:
            multiplier = 0

        # Обновляем баланс
        if win:
            win_amount = bet_amount * multiplier
            users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0) + win_amount, 2)
            result_text = f"""<b>🎲 Кости</b>

🎉 Победа!

<blockquote>🎯 Ставка: {get_dice_bet_name(bet_type)}
🎰 Выпало: {dice_value}
💰 Выигрыш: ${round(win_amount, 2)}</blockquote>"""
        else:
            users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0), 2)
            result_text = f"""<b>🎲 Кости</b>

❌ Проигрыш!

<blockquote>🎯 Ставка: {get_dice_bet_name(bet_type)}
🎰 Выпало: {dice_value}
💸 Ставка: ${bet_amount}</blockquote>"""

        save_users_data(users_data)

        # Удаляем сообщение с костями и показываем результат
        try:
            bot.delete_message(call.message.chat.id, dice_msg.message_id)
        except Exception as e:
            logging.warning(f"Не удалось удалить сообщение с dice: {e}")

        bot.edit_message_text(
            result_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("🔄 Играть снова", callback_data="games_again_dice")
            )
        )

        # Очищаем активную ставку
        with bet_lock:
            if user_id in active_bets:
                del active_bets[user_id]

    except Exception as e:
        logging.error(f"Ошибка в игре в кости: {e}")
        try:
            bot.edit_message_text(
                "❌ Произошла ошибка во время игры. Попробуйте еще раз.",
                call.message.chat.id,
                call.message.message_id
            )
        except Exception as e2:
            logging.error(f"Не удалось отправить сообщение об ошибке: {e2}")

def get_dice_bet_name(bet_type):
    names = {
        "even": "🔴 Чет",
        "odd": "⚫ Нечет",
        "high": "📈 Больше 3",
        "low": "📉 Меньше 4"
    }
    return names.get(bet_type, bet_type)

# 🏀 БАСКЕТБОЛ
def get_basketball_selection_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("❌ Мимо (2x)", callback_data="basketball_miss"),
        types.InlineKeyboardButton("🟢 Гол (2x)", callback_data="basketball_goal"),
        types.InlineKeyboardButton("🎯 3-очковый (3x)", callback_data="basketball_three")
    )
    return markup

def play_basketball_game(bot, call, bet_type, bet_amount, user_id):
    try:
        # Показываем анимацию броска
        basketball_msg = bot.send_dice(call.message.chat.id, emoji='🏀')

        # Ждем 3 секунды
        time.sleep(3)

        # Получаем результат (значение кости баскетбола)
        dice_value = basketball_msg.dice.value
        users_data = load_users_data()

        # Определяем результат по значению кости
        # В баскетболе: 1-2 = мимо, 3-4 = гол, 5 = 3-очковый
        result = ""
        win = False

        if dice_value <= 2:
            result = "miss"
        elif dice_value <= 4:
            result = "goal"
        else:
            result = "three"

        # Проверяем выигрыш
        if bet_type == "miss" and result == "miss":
            win = True
            multiplier = 2.0
        elif bet_type == "goal" and result == "goal":
            win = True
            multiplier = 2.0
        elif bet_type == "three" and result == "three":
            win = True
            multiplier = 3.0
        else:
            multiplier = 0

        # Обновляем баланс
        if win:
            win_amount = bet_amount * multiplier
            users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0) + win_amount, 2)
            result_text = f"""<b>🏀 Баскетбол</b>

🎉 Победа!

<blockquote>🎯 Ставка: {get_basketball_bet_name(bet_type)}
🏀 Результат: {get_basketball_result_name(result)}
💰 Выигрыш: ${round(win_amount, 2)}</blockquote>"""
        else:
            users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0), 2)
            result_text = f"""<b>🏀 Баскетбол</b>

❌ Проигрыш!

<blockquote>🎯 Ставка: {get_basketball_bet_name(bet_type)}
🏀 Результат: {get_basketball_result_name(result)}
💸 Ставка: ${bet_amount}</blockquote>"""

        save_users_data(users_data)

        # Удаляем сообщение с броском и показываем результат
        try:
            bot.delete_message(call.message.chat.id, basketball_msg.message_id)
        except Exception as e:
            logging.warning(f"Не удалось удалить сообщение с баскетболом: {e}")

        bot.edit_message_text(
            result_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("🔄 Играть снова", callback_data="games_again_basketball")
            )
        )

        # Очищаем активную ставку
        with bet_lock:
            if user_id in active_bets:
                del active_bets[user_id]

    except Exception as e:
        logging.error(f"Ошибка в игре в баскетбол: {e}")
        try:
            bot.edit_message_text(
                "❌ Произошла ошибка во время игры. Попробуйте еще раз.",
                call.message.chat.id,
                call.message.message_id
            )
        except Exception as e2:
            logging.error(f"Не удалось отправить сообщение об ошибке: {e2}")

def get_basketball_bet_name(bet_type):
    names = {
        "miss": "❌ Мимо",
        "goal": "🟢 Гол",
        "three": "🎯 3-очковый"
    }
    return names.get(bet_type, bet_type)

def get_basketball_result_name(result):
    names = {
        "miss": "❌ Мимо",
        "goal": "🟢 Гол",
        "three": "🎯 3-очковый"
    }
    return names.get(result, result)

# ⚽ ФУТБОЛ
def get_football_selection_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("❌ Мимо (1.8x)", callback_data="football_miss"),
        types.InlineKeyboardButton("🟢 Гол (1.4x)", callback_data="football_goal")
    )
    return markup

def play_football_game(bot, call, bet_type, bet_amount, user_id):
    try:
        # Показываем анимацию удара
        football_msg = bot.send_dice(call.message.chat.id, emoji='⚽')

        # Ждем 3 секунды
        time.sleep(3)

        # Получаем результат (значение кости футбола)
        dice_value = football_msg.dice.value
        users_data = load_users_data()

        # В футболе: 1-3 = мимо, 4-5 = гол
        result = "goal" if dice_value >= 4 else "miss"
        win = False

        # Проверяем выигрыш с новыми множителями
        if bet_type == "miss" and result == "miss":
            win = True
            multiplier = 1.8
        elif bet_type == "goal" and result == "goal":
            win = True
            multiplier = 1.4
        else:
            multiplier = 0

        # Обновляем баланс
        if win:
            win_amount = bet_amount * multiplier
            users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0) + win_amount, 2)
            result_text = f"""<b>⚽ Футбол</b>

🎉 Победа!

<blockquote>🎯 Ставка: {get_football_bet_name(bet_type)}
⚽ Результат: {get_football_result_name(result)}
💰 Выигрыш: ${round(win_amount, 2)}</blockquote>"""
        else:
            users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0), 2)
            result_text = f"""<b>⚽ Футбол</b>

❌ Проигрыш!

<blockquote>🎯 Ставка: {get_football_bet_name(bet_type)}
⚽ Результат: {get_football_result_name(result)}
💸 Ставка: ${bet_amount}</blockquote>"""

        save_users_data(users_data)

        # Удаляем сообщение с ударом и показываем результат
        try:
            bot.delete_message(call.message.chat.id, football_msg.message_id)
        except Exception as e:
            logging.warning(f"Не удалось удалить сообщение с футболом: {e}")

        bot.edit_message_text(
            result_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("🔄 Играть снова", callback_data="games_again_football")
            )
        )

        # Очищаем активную ставку
        with bet_lock:
            if user_id in active_bets:
                del active_bets[user_id]

    except Exception as e:
        logging.error(f"Ошибка в игре в футбол: {e}")
        try:
            bot.edit_message_text(
                "❌ Произошла ошибка во время игры. Попробуйте еще раз.",
                call.message.chat.id,
                call.message.message_id
            )
        except Exception as e2:
            logging.error(f"Не удалось отправить сообщение об ошибке: {e2}")

def get_football_bet_name(bet_type):
    names = {
        "miss": "❌ Мимо",
        "goal": "🟢 Гол"
    }
    return names.get(bet_type, bet_type)

def get_football_result_name(result):
    names = {
        "miss": "❌ Мимо",
        "goal": "🟢 Гол"
    }
    return names.get(result, result)

# 🎯 ДАРТС
def get_darts_selection_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("❌ Мимо (2.5x)", callback_data="darts_miss"),
        types.InlineKeyboardButton("🔴 Красное (1.8x)", callback_data="darts_red"),
        types.InlineKeyboardButton("⚪ Белое (1.8x)", callback_data="darts_white"),
        types.InlineKeyboardButton("🎯 Центр (4.3x)", callback_data="darts_bullseye")
    )
    return markup

def play_darts_game(bot, call, bet_type, bet_amount, user_id):
    try:
        # Показываем анимацию броска
        darts_msg = bot.send_dice(call.message.chat.id, emoji='🎯')

        # Ждем 3 секунды
        time.sleep(3)

        # Получаем результат (значение кости дартса)
        dice_value = darts_msg.dice.value
        users_data = load_users_data()

        # ПРАВИЛЬНАЯ СТРУКТУРА МИШЕНИ ДАРТСА:
        # Центр (красный) -> Белое кольцо -> Красное кольцо -> Белое кольцо -> Красное кольцо (внешнее)
        # dice_value:
        # 1 = мимо доски
        # 2 = внешнее красное кольцо (самый большой)
        # 3 = белое кольцо (второе по размеру)
        # 4 = красное кольцо (третье по размеру)
        # 5 = белое кольцо (четвертое по размеру)
        # 6 = центр (красный, самый маленький)

        if dice_value == 1:
            result = "miss"      # ❌ Мимо
        elif dice_value == 6:
            result = "bullseye"  # 🎯 Центр (красный)
        elif dice_value in [2, 4]:
            result = "red"       # 🔴 Красное кольцо
        else:  # 3, 5
            result = "white"     # ⚪ Белое кольцо

        win = False
        # Множители для дартса
        multipliers = {
            "miss": 2.5,
            "red": 1.8,
            "white": 1.8,
            "bullseye": 4.3
        }

        # Проверяем выигрыш
        if bet_type == "red" and result in ["red", "bullseye"]:
            win = True
            multiplier = multipliers["red"]
        elif bet_type == "white" and result == "white":
            win = True
            multiplier = multipliers["white"]
        elif bet_type == "miss" and result == "miss":
            win = True
            multiplier = multipliers["miss"]
        elif bet_type == "bullseye" and result == "bullseye":
            win = True
            multiplier = multipliers["bullseye"]
        else:
            multiplier = 0

        # Обновляем баланс
        if win:
            win_amount = bet_amount * multiplier
            users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0) + win_amount, 2)
            result_text = f"""<b>🎯 Дартс</b>

🎉 Победа!

<blockquote>🎯 Ставка: {get_darts_bet_name(bet_type)}
🎯 Результат: {get_darts_result_name(result)}
💰 Выигрыш: ${round(win_amount, 2)}</blockquote>"""
        else:
            users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0), 2)
            result_text = f"""<b>🎯 Дартс</b>

❌ Проигрыш!

<blockquote>🎯 Ставка: {get_darts_bet_name(bet_type)}
🎯 Результат: {get_darts_result_name(result)}
💸 Ставка: ${bet_amount}</blockquote>"""

        save_users_data(users_data)

        # Удаляем сообщение с броском и показываем результат
        try:
            bot.delete_message(call.message.chat.id, darts_msg.message_id)
        except Exception as e:
            logging.warning(f"Не удалось удалить сообщение с дартсом: {e}")

        bot.edit_message_text(
            result_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("🔄 Играть снова", callback_data="games_again_darts")
            )
        )

        # Очищаем активную ставку
        with bet_lock:
            if user_id in active_bets:
                del active_bets[user_id]

    except Exception as e:
        logging.error(f"Ошибка в игре в дартс: {e}")
        try:
            bot.edit_message_text(
                "❌ Произошла ошибка во время игры. Попробуйте еще раз.",
                call.message.chat.id,
                call.message.message_id
            )
        except Exception as e2:
            logging.error(f"Не удалось отправить сообщение об ошибке: {e2}")

def get_darts_bet_name(bet_type):
    names = {
        "miss": "❌ Мимо",
        "red": "🔴 Красное",
        "white": "⚪ Белое",
        "bullseye": "🎯 Центр"
    }
    return names.get(bet_type, bet_type)

def get_darts_result_name(result):
    names = {
        "miss": "❌ Мимо",
        "red": "🔴 Красное",
        "white": "⚪ Белое",
        "bullseye": "🎯 Центр"
    }
    return names.get(result, result)

def register_games_handlers(bot):

    def process_custom_bet_games(message):
        try:
            user_id = str(message.from_user.id)

            # Проверяем ограничение по времени
            if not rate_limit(user_id):
                bot.send_message(message.chat.id, "❌ Слишком быстро! Подождите 0.4 секунды.")
                return

            bet_amount = float(message.text)
            users_data = load_users_data()

            if user_id not in users_data:
                users_data[user_id] = {'balance': 0}

            balance = users_data[user_id].get('balance', 0)

            # Проверяем минимальную и максимальную ставку
            if bet_amount < MIN_BET:
                bot.send_message(message.chat.id, f"❌ Минимальная ставка: ${MIN_BET}!")
                return
            if bet_amount > MAX_BET:
                bot.send_message(message.chat.id, f"❌ Максимальная ставка: ${MAX_BET}!")
                return
            if bet_amount > balance:
                bot.send_message(message.chat.id, "❌ Недостаточно средств!")
                return

            # Списываем ставку
            users_data[user_id]['balance'] = round(balance - bet_amount, 2)
            save_users_data(users_data)

            # Показываем выбор для выбранной игры
            with bet_lock:
                if user_id in active_bets:
                    game_type = active_bets[user_id]['game_type']
                    active_bets[user_id]['bet_amount'] = bet_amount

                    if game_type == "dice":
                        bot.send_message(message.chat.id,
                                       f"""<b>🎲 Кости</b>

<blockquote>💵 Сумма ставки: ${bet_amount}</blockquote>

Выберите исход:""",
                                       parse_mode='HTML', reply_markup=get_dice_selection_keyboard())
                    elif game_type == "basketball":
                        bot.send_message(message.chat.id,
                                       f"""<b>🏀 Баскетбол</b>

<blockquote>💵 Сумма ставки: ${bet_amount}</blockquote>

Выберите исход:""",
                                       parse_mode='HTML', reply_markup=get_basketball_selection_keyboard())
                    elif game_type == "football":
                        bot.send_message(message.chat.id,
                                       f"""<b>⚽ Футбол</b>

<blockquote>💵 Сумма ставки: ${bet_amount}</blockquote>

Выберите исход:""",
                                       parse_mode='HTML', reply_markup=get_football_selection_keyboard())
                    elif game_type == "darts":
                        bot.send_message(message.chat.id,
                                       f"""<b>🎯 Дартс</b>

<blockquote>💵 Сумма ставки: ${bet_amount}</blockquote>

Выберите исход:""",
                                       parse_mode='HTML', reply_markup=get_darts_selection_keyboard())

        except ValueError:
            bot.send_message(message.chat.id, "❌ Введите корректную сумму!")
        except Exception as e:
            logging.error(f"Ошибка в process_custom_bet_games: {e}")
            bot.send_message(message.chat.id, "❌ Произошла ошибка!")

    @bot.message_handler(func=lambda message: message.text in ["🎲 Кости", "🏀 Баскетбол", "🎯 Дартс", "⚽ Футбол"])
    def games_start(message):
        try:
            user_id = str(message.from_user.id)

            # Проверяем ограничение по времени
            if not rate_limit(user_id):
                bot.send_message(message.chat.id, "❌ Слишком быстро! Подождите 0.4 секунды.")
                return

            users_data = load_users_data()

            if user_id not in users_data:
                users_data[user_id] = {'balance': 0}
                save_users_data(users_data)

            balance = users_data[user_id].get('balance', 0)
            balance_rounded = round(balance, 2)

            with bet_lock:
                if message.text == "🎲 Кости":
                    active_bets[user_id] = {'game_type': 'dice'}
                    game_name = "🎲 Кости"
                elif message.text == "🏀 Баскетбол":
                    active_bets[user_id] = {'game_type': 'basketball'}
                    game_name = "🏀 Баскетбол"
                elif message.text == "⚽ Футбол":
                    active_bets[user_id] = {'game_type': 'football'}
                    game_name = "⚽ Футбол"
                elif message.text == "🎯 Дартс":
                    active_bets[user_id] = {'game_type': 'darts'}
                    game_name = "🎯 Дартс"

            bot.send_message(
                message.chat.id,
                f"""<b>{game_name}</b>

<blockquote>💵 Баланс: ${balance_rounded}</blockquote>

Выберите сумму ставки:""",
                parse_mode='HTML',
                reply_markup=get_bet_selection_keyboard()
            )
        except Exception as e:
            logging.error(f"Ошибка в games_start: {e}")
            bot.send_message(message.chat.id, "❌ Произошла ошибка при запуске игры!")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('games_'))
    def games_callback_handler(call):
        try:
            user_id = str(call.from_user.id)

            # Проверяем ограничение по времени
            if not rate_limit(user_id):
                bot.answer_callback_query(call.id, "❌ Слишком быстро! Подождите 0.4 секунды.", show_alert=True)
                return

            users_data = load_users_data()

            if call.data.startswith("games_bet_"):
                bet_amount = float(call.data.split("_")[2])

                balance = users_data[user_id].get('balance', 0)
                if bet_amount > balance:
                    bot.answer_callback_query(call.id, "❌ Недостаточно средств!")
                    return

                # Сохраняем сумму ставки
                with bet_lock:
                    active_bets[user_id]['bet_amount'] = bet_amount

                # Списываем ставку
                users_data[user_id]['balance'] = round(balance - bet_amount, 2)
                save_users_data(users_data)

                # Показываем выбор для выбранной игры
                with bet_lock:
                    game_type = active_bets[user_id]['game_type']

                if game_type == "dice":
                    bot.edit_message_text(
                        f"""<b>🎲 Кости</b>

<blockquote>💵 Сумма ставки: ${bet_amount}</blockquote>

Выберите исход:""",
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode='HTML',
                        reply_markup=get_dice_selection_keyboard()
                    )
                elif game_type == "basketball":
                    bot.edit_message_text(
                        f"""<b>🏀 Баскетбол</b>

<blockquote>💵 Сумма ставки: ${bet_amount}</blockquote>

Выберите исход:""",
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode='HTML',
                        reply_markup=get_basketball_selection_keyboard()
                    )
                elif game_type == "football":
                    bot.edit_message_text(
                        f"""<b>⚽ Футбол</b>

<blockquote>💵 Сумма ставки: ${bet_amount}</blockquote>

Выберите исход:""",
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode='HTML',
                        reply_markup=get_football_selection_keyboard()
                    )
                elif game_type == "darts":
                    bot.edit_message_text(
                        f"""<b>🎯 Дартс</b>

<blockquote>💵 Сумма ставки: ${bet_amount}</blockquote>

Выберите исход:""",
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode='HTML',
                        reply_markup=get_darts_selection_keyboard()
                    )
                return

            elif call.data == "games_custom_bet":
                bot.send_message(call.message.chat.id,
                               """<b>📝 Ввод суммы</b>

<blockquote>Введите сумму ставки:</blockquote>""",
                               parse_mode='HTML')
                bot.register_next_step_handler(call.message, process_custom_bet_games)
                return

            elif call.data.startswith("games_again_"):
                # Играть снова - возвращаем к выбору суммы ставки для конкретной игры
                game_type = call.data.split("_")[2]

                with bet_lock:
                    active_bets[user_id] = {'game_type': game_type}

                balance = users_data[user_id].get('balance', 0)
                balance_rounded = round(balance, 2)

                if game_type == "dice":
                    game_name = "🎲 Кости"
                elif game_type == "basketball":
                    game_name = "🏀 Баскетбол"
                elif game_type == "football":
                    game_name = "⚽ Футбол"
                elif game_type == "darts":
                    game_name = "🎯 Дартс"

                bot.edit_message_text(
                    f"""<b>{game_name}</b>

<blockquote>💵 Баланс: ${balance_rounded}</blockquote>

Выберите сумму ставки:""",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=get_bet_selection_keyboard()
                )
                return

        except Exception as e:
            logging.error(f"Ошибка в games_callback_handler: {e}")
            try:
                bot.answer_callback_query(call.id, "❌ Произошла ошибка!")
            except:
                pass

    # ОБРАБОТЧИКИ ДЛЯ ВЫБОРА РЕЖИМОВ В ИГРАХ
    @bot.callback_query_handler(func=lambda call: call.data.startswith(('dice_', 'basketball_', 'football_', 'darts_')))
    def games_mode_callback_handler(call):
        try:
            user_id = str(call.from_user.id)

            # Проверяем ограничение по времени
            if not rate_limit(user_id):
                bot.answer_callback_query(call.id, "❌ Слишком быстро! Подождите 0.4 секунды.", show_alert=True)
                return

            with bet_lock:
                if user_id not in active_bets or 'bet_amount' not in active_bets[user_id]:
                    bot.answer_callback_query(call.id, "❌ Сначала сделайте ставку!")
                    return

                bet_amount = active_bets[user_id]['bet_amount']

            # Обработка выбора в играх
            if call.data.startswith("dice_"):
                bet_type = call.data.split("_")[1]
                threading.Thread(target=play_dice_game, args=(bot, call, bet_type, bet_amount, user_id), daemon=True).start()

            elif call.data.startswith("basketball_"):
                bet_type = call.data.split("_")[1]
                threading.Thread(target=play_basketball_game, args=(bot, call, bet_type, bet_amount, user_id), daemon=True).start()

            elif call.data.startswith("football_"):
                bet_type = call.data.split("_")[1]
                threading.Thread(target=play_football_game, args=(bot, call, bet_type, bet_amount, user_id), daemon=True).start()

            elif call.data.startswith("darts_"):
                bet_type = call.data.split("_")[1]
                threading.Thread(target=play_darts_game, args=(bot, call, bet_type, bet_amount, user_id), daemon=True).start()

            # Показываем загрузку
            bot.answer_callback_query(call.id, "🎮 Запускаем игру...")

        except Exception as e:
            logging.error(f"Ошибка в games_mode_callback_handler: {e}")
            try:
                bot.answer_callback_query(call.id, "❌ Ошибка запуска игры")
            except:
                pass