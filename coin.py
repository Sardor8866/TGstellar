import telebot
from telebot import types
import random
import json
import time
import logging
import threading
import secrets  # Добавляем для лучшей случайности

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

# Активные игры Орел-Решка
active_coin_games = {}

# Минимальная и максимальная ставка
MIN_BET = 0.2
MAX_BET = 1000

# Задержка между нажатиями
last_click_time = {}
click_lock = threading.Lock()

def rate_limit(user_id):
    """Проверка ограничения по времени между нажатиями (0.4 секунды)"""
    current_time = time.time()
    with click_lock:
        if user_id in last_click_time:
            if current_time - last_click_time[user_id] < 0.4:
                return False
        last_click_time[user_id] = current_time
    return True

def get_coin_flip():
    """Справедливый бросок монеты с использованием системного энтропийного источника"""
    # Используем secrets для криптографически безопасного случайного выбора
    return "eagle" if secrets.randbelow(2) == 0 else "tails"

def get_coin_bet_selection_keyboard():
    """Клавиатура выбора ставки для Орел-Решка"""
    markup = types.InlineKeyboardMarkup(row_width=5)
    bets = ["0.2", "0.5", "1", "3", "5"]
    buttons = [types.InlineKeyboardButton(f"${bet}", callback_data=f"coin_bet_{bet}") for bet in bets]
    markup.row(*buttons)
    markup.row(types.InlineKeyboardButton("📝 Ввести вручную", callback_data="coin_custom_bet"))
    markup.row(types.InlineKeyboardButton("🎮 Правила игры", callback_data="coin_rules"))
    return markup

def get_coin_rules():
    """Правила игры в Орел-Решка"""
    return """🪙 <b>Орел-Решка - Правила</b>

<blockquote>
🎯 <b>Как играть:</b>
• Выберите ставку
• Выберите сторону монеты: Орел 🦅 или Решка 🪙
• Бот подбрасывает монету
• Если угадали сторону - победа!

💰 <b>Выигрыш:</b>
• Победа: 2x от ставки
• Проигрыш: потеря ставки

🎲 <b>Справедливость:</b>
• Используется криптографически безопасный генератор
• Шансы: 50/50 для каждой стороны
</blockquote>

🎲 Удачи!"""

def get_coin_choice_keyboard():
    """Клавиатура выбора стороны монеты"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton("🦅 Орел", callback_data="coin_choice_eagle"),
        types.InlineKeyboardButton("🪙 Решка", callback_data="coin_choice_tails")
    )
    return markup

def play_coin_game(bot, call, bet_amount, user_id):
    """Основная логика игры в Орел-Решку"""
    try:
        users_data = load_users_data()
        current_balance = users_data[user_id].get('balance', 0)

        # Списываем ставку
        users_data[user_id]['balance'] = round(current_balance - bet_amount, 2)
        save_users_data(users_data)

        # Сохраняем состояние игры
        active_coin_games[user_id] = {
            'bet_amount': bet_amount,
            'chat_id': call.message.chat.id,
            'message_id': call.message.message_id
        }

        # Показываем выбор стороны
        show_coin_choice_screen(bot, user_id)

    except Exception as e:
        logging.error(f"Ошибка запуска игры в Орел-Решку: {e}")
        bot.edit_message_text(
            "❌ Произошла ошибка при запуске игры",
            call.message.chat.id,
            call.message.message_id
        )

def show_coin_choice_screen(bot, user_id):
    """Показывает экран выбора стороны монеты"""
    try:
        if user_id not in active_coin_games:
            return

        game_data = active_coin_games[user_id]
        bet_amount = game_data['bet_amount']

        display = f"""🪙 <b>Орел-Решка</b>

<blockquote>💵 Сумма ставки: ${bet_amount}</blockquote>

Выберите сторону монеты:"""

        keyboard = get_coin_choice_keyboard()

        bot.edit_message_text(
            display,
            game_data['chat_id'],
            game_data['message_id'],
            parse_mode='HTML',
            reply_markup=keyboard
        )

    except Exception as e:
        logging.error(f"Ошибка показа выбора монеты: {e}")

def process_coin_choice(bot, call, player_choice, user_id):
    """Обрабатывает выбор игрока"""
    try:
        if user_id not in active_coin_games:
            bot.answer_callback_query(call.id, "❌ Игра не найдена")
            return

        game_data = active_coin_games[user_id]
        bet_amount = game_data['bet_amount']

        # Используем улучшенный бросок монеты
        bot_choice = get_coin_flip()

        # Определяем победителя
        result = "player" if player_choice == bot_choice else "bot"

        # Показываем анимацию броска
        show_coin_animation(bot, user_id, player_choice, bot_choice, result, bet_amount)

    except Exception as e:
        logging.error(f"Ошибка обработки выбора монеты: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка в игре")

def show_coin_animation(bot, user_id, player_choice, bot_choice, result, bet_amount):
    """Показывает анимацию броска монеты"""
    try:
        if user_id not in active_coin_games:
            return

        game_data = active_coin_games[user_id]

        # Первый этап - показываем анимацию броска
        display = f"""🪙 <b>Орел-Решка</b>

<blockquote>🎯 Ваш выбор: {'🦅 Орел' if player_choice == 'eagle' else '🪙 Решка'}</blockquote>

🌀 <b>Бросаем монетку...</b>

⚪ Монета крутится..."""

        bot.edit_message_text(
            display,
            game_data['chat_id'],
            game_data['message_id'],
            parse_mode='HTML'
        )

        # Ждем 1 секунду
        time.sleep(1)

        # Второй этап - монета в воздухе
        display = f"""🪙 <b>Орел-Решка</b>

<blockquote>🎯 Ваш выбор: {'🦅 Орел' if player_choice == 'eagle' else '🪙 Решка'}</blockquote>

🌀 <b>Бросаем монетку...</b>

🔄 Монета в воздухе..."""

        bot.edit_message_text(
            display,
            game_data['chat_id'],
            game_data['message_id'],
            parse_mode='HTML'
        )

        # Ждем 1 секунду
        time.sleep(1)

        # Показываем финальный результат
        show_coin_final_result(bot, user_id, player_choice, bot_choice, result, bet_amount)

    except Exception as e:
        logging.error(f"Ошибка анимации монеты: {e}")

def show_coin_final_result(bot, user_id, player_choice, bot_choice, result, bet_amount):
    """Показывает финальный результат"""
    try:
        if user_id not in active_coin_games:
            return

        game_data = active_coin_games[user_id]
        users_data = load_users_data()

        player_side = "🦅 Орел" if player_choice == "eagle" else "🪙 Решка"
        bot_side = "🦅 Орел" if bot_choice == "eagle" else "🪙 Решка"

        display = f"""🪙 <b>Орел-Решка - РЕЗУЛЬТАТ</b>

<blockquote>
🎯 Ваш выбор: {player_side}
🎲 Выпало: {bot_side}
</blockquote>"""

        win_amount = 0
        result_text = ""

        if result == "player":
            # Победа игрока
            win_amount = round(bet_amount * 2, 2)
            users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0) + win_amount, 2)
            result_text = f"""🎉 <b>ВЫ ВЫИГРАЛИ!</b>

<blockquote>
💰 Ставка: ${bet_amount}
🎯 Множитель: 2x
🏆 Выигрыш: ${win_amount:.2f}
</blockquote>"""
            display += "\n✅ <b>Результат: ПОБЕДА!</b>"

        else:
            # Проигрыш
            win_amount = 0
            result_text = f"""❌ <b>ВЫ ПРОИГРАЛИ!</b>

<blockquote>
💰 Ставка: ${bet_amount}
💸 Потеряно: ${bet_amount}
</blockquote>"""
            display += "\n❌ <b>Результат: ПРОИГРЫШ</b>"

        save_users_data(users_data)

        display += f"\n\n{result_text}"

        # Клавиатура после игры
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔄 Играть снова", callback_data="coin_play_again"),
            types.InlineKeyboardButton("🎮 Другие игры", callback_data="coin_other_games")
        )

        bot.edit_message_text(
            display,
            game_data['chat_id'],
            game_data['message_id'],
            parse_mode='HTML',
            reply_markup=markup
        )

        # Удаляем игру из активных
        if user_id in active_coin_games:
            del active_coin_games[user_id]

    except Exception as e:
        logging.error(f"Ошибка показа результата монеты: {e}")

def register_coin_handlers(bot):
    """Регистрация обработчиков для игры в Орел-Решку"""

    def process_custom_bet_coin(message):
        """Обработка ручного ввода ставки для Орел-Решки"""
        try:
            bet_amount = float(message.text)
            users_data = load_users_data()
            user_id = str(message.from_user.id)

            if user_id not in users_data:
                users_data[user_id] = {'balance': 0}
                save_users_data(users_data)

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

            # Сразу запускаем игру без кнопки "Начать игру"
            play_coin_game(bot, message, bet_amount, user_id)

        except ValueError:
            bot.send_message(message.chat.id, "❌ Введите корректную сумму!")
        except Exception as e:
            logging.error(f"Ошибка в process_custom_bet_coin: {e}")
            bot.send_message(message.chat.id, "❌ Произошла ошибка!")

    @bot.message_handler(func=lambda message: message.text == "🪙 Орел-Решка")
    def coin_start(message):
        """Начало игры в Орел-Решку"""
        try:
            # Проверяем задержку
            if not rate_limit(str(message.from_user.id)):
                return

            users_data = load_users_data()
            user_id = str(message.from_user.id)

            if user_id not in users_data:
                users_data[user_id] = {'balance': 0}
                save_users_data(users_data)

            balance = users_data[user_id].get('balance', 0)
            balance_rounded = round(balance, 2)

            bot.send_message(
                message.chat.id,
                f"""🪙 <b>Орел-Решка</b>

<blockquote>💎 Баланс: ${balance_rounded}</blockquote>

Выберите сумму ставки:""",
                reply_markup=get_coin_bet_selection_keyboard(),
                parse_mode='HTML'
            )
        except Exception as e:
            logging.error(f"Ошибка в coin_start: {e}")
            bot.send_message(message.chat.id, "❌ Ошибка запуска игры")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('coin_'))
    def coin_callback_handler(call):
        """Обработчик колбэков Орел-Решки"""
        try:
            user_id = str(call.from_user.id)

            # Проверяем задержку
            if not rate_limit(user_id):
                bot.answer_callback_query(call.id, "⏳ Не так быстро!", show_alert=False)
                return

            if call.data.startswith("coin_bet_"):
                bet_amount = float(call.data.split("_")[2])
                users_data = load_users_data()

                balance = users_data[user_id].get('balance', 0)
                if bet_amount > balance:
                    bot.answer_callback_query(call.id, "❌ Недостаточно средств!")
                    return

                # Сразу запускаем игру без кнопки "Начать игру"
                play_coin_game(bot, call, bet_amount, user_id)

            elif call.data == "coin_custom_bet":
                bot.send_message(call.message.chat.id, "📝 Введите сумму ставки:")
                bot.register_next_step_handler(call.message, process_custom_bet_coin)

            elif call.data == "coin_rules":
                bot.edit_message_text(
                    get_coin_rules(),
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🎮 Начать игру", callback_data="coin_back_to_bet")
                    )
                )

            elif call.data == "coin_back_to_bet":
                users_data = load_users_data()
                balance = users_data[user_id].get('balance', 0)
                balance_rounded = round(balance, 2)

                bot.edit_message_text(
                    f"""🪙 <b>Орел-Решка</b>

<blockquote>💎 Баланс: ${balance_rounded}</blockquote>

Выберите сумму ставки:""",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=get_coin_bet_selection_keyboard(),
                    parse_mode='HTML'
                )

            elif call.data.startswith("coin_choice_"):
                choice = call.data.split("_")[2]  # eagle, tails
                process_coin_choice(bot, call, choice, user_id)

            elif call.data == "coin_play_again":
                # Очищаем предыдущую игру
                if user_id in active_coin_games:
                    del active_coin_games[user_id]

                users_data = load_users_data()
                balance = users_data[user_id].get('balance', 0)
                balance_rounded = round(balance, 2)

                bot.edit_message_text(
                    f"""🪙 <b>Орел-Решка</b>

<blockquote>💎 Баланс: ${balance_rounded}</blockquote>

Выберите сумму ставки:""",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=get_coin_bet_selection_keyboard(),
                    parse_mode='HTML'
                )

            elif call.data == "coin_other_games":
                # Возврат к основным играм
                if user_id in active_coin_games:
                    del active_coin_games[user_id]

                bot.edit_message_text(
                    "🎮 <b>Выберите игру:</b>",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML'
                )

        except Exception as e:
            logging.error(f"Ошибка в coin_callback_handler: {e}")
            try:
                bot.answer_callback_query(call.id, "❌ Ошибка в игре")
            except:
                pass