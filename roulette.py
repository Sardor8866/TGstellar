import telebot
from telebot import types
import random
import json
import time
import logging
import threading

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

# Активные игры Рулетка
active_roulette_games = {}

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

def get_roulette_bet_selection_keyboard():
    """Клавиатура выбора ставки для Рулетки"""
    markup = types.InlineKeyboardMarkup(row_width=5)
    bets = ["0.2", "0.5", "1", "3", "5"]
    buttons = [types.InlineKeyboardButton(f"${bet}", callback_data=f"roulette_bet_{bet}") for bet in bets]
    markup.row(*buttons)
    markup.row(types.InlineKeyboardButton("📝 Ввести вручную", callback_data="roulette_custom_bet"))
    markup.row(types.InlineKeyboardButton("🎮 Правила игры", callback_data="roulette_rules"))
    return markup

def get_roulette_rules():
    """Правила игры в Рулетку"""
    return """🎰 <b>Рулетка - Правила</b>

<blockquote>
🎯 <b>Как играть:</b>
• Выберите ставку
• Выберите тип ставки: Чет/Нечет, Красное/Черное или Конкретное число
• Крутим рулетку и определяем победителя

🎲 <b>Типы ставок и множители:</b>
• 🔴 Красное: 1.8x
• ⚫ Черное: 1.8x  
• 🔵 Четное: 1.8x
• 🔘 Нечетное: 1.8x
• 🎯 Конкретное число (0-36): 25x

📊 <b>Особенности:</b>
• Красные числа: 1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36
• Черные числа: 2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35
• Зеленое число: 0 (проигрыш для всех кроме ставки на 0)
• Четные: все четные числа (2,4,6,8...36)
• Нечетные: все нечетные числа (1,3,5,7...35)
</blockquote>

🎰 Удачи за рулеточным столом!"""

def get_roulette_choice_keyboard():
    """Клавиатура выбора типа ставки"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton("🔴 Красное", callback_data="roulette_choice_red"),
        types.InlineKeyboardButton("⚫ Черное", callback_data="roulette_choice_black")
    )
    markup.row(
        types.InlineKeyboardButton("🔵 Четное", callback_data="roulette_choice_even"),
        types.InlineKeyboardButton("🔘 Нечетное", callback_data="roulette_choice_odd")
    )
    markup.row(
        types.InlineKeyboardButton("🎯 Число (0-36)", callback_data="roulette_choice_number")
    )
    return markup

def get_roulette_number_keyboard():
    """Клавиатура для выбора конкретного числа"""
    markup = types.InlineKeyboardMarkup(row_width=6)
    
    # Первый ряд: 0-5
    row1 = [types.InlineKeyboardButton(str(i), callback_data=f"roulette_number_{i}") for i in range(0, 6)]
    markup.row(*row1)
    
    # Второй ряд: 6-11
    row2 = [types.InlineKeyboardButton(str(i), callback_data=f"roulette_number_{i}") for i in range(6, 12)]
    markup.row(*row2)
    
    # Третий ряд: 12-17
    row3 = [types.InlineKeyboardButton(str(i), callback_data=f"roulette_number_{i}") for i in range(12, 18)]
    markup.row(*row3)
    
    # Четвертый ряд: 18-23
    row4 = [types.InlineKeyboardButton(str(i), callback_data=f"roulette_number_{i}") for i in range(18, 24)]
    markup.row(*row4)
    
    # Пятый ряд: 24-29
    row5 = [types.InlineKeyboardButton(str(i), callback_data=f"roulette_number_{i}") for i in range(24, 30)]
    markup.row(*row5)
    
    # Шестой ряд: 30-36
    row6 = [types.InlineKeyboardButton(str(i), callback_data=f"roulette_number_{i}") for i in range(30, 37)]
    markup.row(*row6)
    
    markup.row(types.InlineKeyboardButton("⬅️ Назад", callback_data="roulette_back_to_choice"))
    
    return markup

# Цвета чисел в рулетке
RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
BLACK_NUMBERS = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]
GREEN_NUMBER = [0]

def get_number_color(number):
    """Определяет цвет числа в рулетке"""
    if number in RED_NUMBERS:
        return "red"
    elif number in BLACK_NUMBERS:
        return "black"
    else:
        return "green"

def get_number_emoji(number):
    """Возвращает эмоджи для числа"""
    color = get_number_color(number)
    if color == "red":
        return "🔴"
    elif color == "black":
        return "⚫"
    else:
        return "🟢"

def is_even(number):
    """Проверяет четное ли число"""
    return number % 2 == 0 and number != 0

def is_odd(number):
    """Проверяет нечетное ли число"""
    return number % 2 == 1

def spin_roulette():
    """Крутит рулетку и возвращает выпавшее число"""
    return random.randint(0, 36)

def determine_roulette_winner(player_choice, result_number):
    """Определяет победителя в рулетке"""
    result_color = get_number_color(result_number)
    
    if player_choice == "red":
        return result_color == "red"
    elif player_choice == "black":
        return result_color == "black"
    elif player_choice == "even":
        return is_even(result_number)
    elif player_choice == "odd":
        return is_odd(result_number)
    elif player_choice.startswith("number_"):
        chosen_number = int(player_choice.split("_")[1])
        return chosen_number == result_number
    
    return False

def get_choice_name(choice):
    """Возвращает название выбора"""
    names = {
        "red": "🔴 Красное",
        "black": "⚫ Черное",
        "even": "🔵 Четное", 
        "odd": "🔘 Нечетное"
    }
    if choice.startswith("number_"):
        number = int(choice.split("_")[1])
        return f"🎯 Число {number}"
    return names.get(choice, "Неизвестно")

def get_multiplier(choice):
    """Возвращает множитель для типа ставки"""
    if choice.startswith("number_"):
        return 25.0
    else:
        return 1.8

def play_roulette_game(bot, call, bet_amount, user_id):
    """Основная логика игры в Рулетку"""
    try:
        users_data = load_users_data()
        current_balance = users_data[user_id].get('balance', 0)

        # Списываем ставку
        users_data[user_id]['balance'] = round(current_balance - bet_amount, 2)
        save_users_data(users_data)

        # Сохраняем состояние игры
        active_roulette_games[user_id] = {
            'bet_amount': bet_amount,
            'chat_id': call.message.chat.id,
            'message_id': call.message.message_id
        }

        # Показываем выбор типа ставки
        show_roulette_choice_screen(bot, user_id)

    except Exception as e:
        logging.error(f"Ошибка запуска игры в Рулетку: {e}")
        bot.edit_message_text(
            "❌ Произошла ошибка при запуске игры",
            call.message.chat.id,
            call.message.message_id
        )

def show_roulette_choice_screen(bot, user_id):
    """Показывает экран выбора типа ставки"""
    try:
        if user_id not in active_roulette_games:
            return

        game_data = active_roulette_games[user_id]
        bet_amount = game_data['bet_amount']

        display = f"""🎰 <b>РУЛЕТКА</b>

<blockquote>💵 Сумма ставки: ${bet_amount}</blockquote>

Выберите тип ставки:"""

        keyboard = get_roulette_choice_keyboard()

        bot.edit_message_text(
            display,
            game_data['chat_id'],
            game_data['message_id'],
            parse_mode='HTML',
            reply_markup=keyboard
        )

    except Exception as e:
        logging.error(f"Ошибка показа выбора рулетки: {e}")

def show_roulette_number_screen(bot, user_id):
    """Показывает экран выбора числа"""
    try:
        if user_id not in active_roulette_games:
            return

        game_data = active_roulette_games[user_id]
        bet_amount = game_data['bet_amount']

        display = f"""🎰 <b>РУЛЕТКА</b>

<blockquote>💵 Сумма ставки: ${bet_amount}</blockquote>

Выберите число от 0 до 36:"""

        keyboard = get_roulette_number_keyboard()

        bot.edit_message_text(
            display,
            game_data['chat_id'],
            game_data['message_id'],
            parse_mode='HTML',
            reply_markup=keyboard
        )

    except Exception as e:
        logging.error(f"Ошибка показа выбора числа: {e}")

def process_roulette_choice(bot, call, player_choice, user_id):
    """Обрабатывает выбор игрока"""
    try:
        if user_id not in active_roulette_games:
            bot.answer_callback_query(call.id, "❌ Игра не найдена")
            return

        game_data = active_roulette_games[user_id]
        bet_amount = game_data['bet_amount']

        # Крутим рулетку
        result_number = spin_roulette()

        # Определяем победителя
        is_winner = determine_roulette_winner(player_choice, result_number)

        # Показываем анимацию вращения
        show_roulette_animation(bot, user_id, player_choice, result_number, is_winner, bet_amount)

    except Exception as e:
        logging.error(f"Ошибка обработки выбора рулетки: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка в игре")

def show_roulette_animation(bot, user_id, player_choice, result_number, is_winner, bet_amount):
    """Показывает анимацию вращения рулетки"""
    try:
        if user_id not in active_roulette_games:
            return

        game_data = active_roulette_games[user_id]

        # Первый этап - начало вращения
        display = f"""🎰 <b>РУЛЕТКА</b>

<blockquote>🎯 Ваша ставка: {get_choice_name(player_choice)}</blockquote>

🌀 <b>Крутим рулетку...</b>

⚪ Шар запущен..."""

        bot.edit_message_text(
            display,
            game_data['chat_id'],
            game_data['message_id'],
            parse_mode='HTML'
        )

        # Ждем 1.5 секунды
        time.sleep(1.5)

        # Второй этап - шар крутится
        display = f"""🎰 <b>РУЛЕТКА</b>

<blockquote>🎯 Ваша ставка: {get_choice_name(player_choice)}</blockquote>

🌀 <b>Крутим рулетку...</b>

🔄 Шар крутится..."""

        bot.edit_message_text(
            display,
            game_data['chat_id'],
            game_data['message_id'],
            parse_mode='HTML'
        )

        # Ждем 1.5 секунды
        time.sleep(1.5)

        # Показываем финальный результат
        show_roulette_final_result(bot, user_id, player_choice, result_number, is_winner, bet_amount)

    except Exception as e:
        logging.error(f"Ошибка анимации рулетки: {e}")

def show_roulette_final_result(bot, user_id, player_choice, result_number, is_winner, bet_amount):
    """Показывает финальный результат"""
    try:
        if user_id not in active_roulette_games:
            return

        game_data = active_roulette_games[user_id]
        users_data = load_users_data()

        result_color = get_number_color(result_number)
        result_emoji = get_number_emoji(result_number)
        choice_name = get_choice_name(player_choice)

        display = f"""🎰 <b>РУЛЕТКА - РЕЗУЛЬТАТ</b>

<blockquote>
🎯 Ваша ставка: {choice_name}
🎲 Выпало: {result_emoji} {result_number}
</blockquote>"""

        win_amount = 0
        result_text = ""

        if is_winner:
            # Победа
            multiplier = get_multiplier(player_choice)
            win_amount = round(bet_amount * multiplier, 2)
            users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0) + win_amount, 2)
            
            result_text = f"""🎉 <b>ВЫ ВЫИГРАЛИ!</b>

<blockquote>
💰 Ставка: ${bet_amount}
🎯 Множитель: {multiplier}x
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
            types.InlineKeyboardButton("🔄 Играть снова", callback_data="roulette_play_again"),
            types.InlineKeyboardButton("🎮 Другие игры", callback_data="roulette_other_games")
        )

        bot.edit_message_text(
            display,
            game_data['chat_id'],
            game_data['message_id'],
            parse_mode='HTML',
            reply_markup=markup
        )

        # Удаляем игру из активных
        if user_id in active_roulette_games:
            del active_roulette_games[user_id]

    except Exception as e:
        logging.error(f"Ошибка показа результата рулетки: {e}")

def register_roulette_handlers(bot):
    """Регистрация обработчиков для игры в Рулетку"""

    def process_custom_bet_roulette(message):
        """Обработка ручного ввода ставки для Рулетки"""
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
            play_roulette_game(bot, message, bet_amount, user_id)

        except ValueError:
            bot.send_message(message.chat.id, "❌ Введите корректную сумму!")
        except Exception as e:
            logging.error(f"Ошибка в process_custom_bet_roulette: {e}")
            bot.send_message(message.chat.id, "❌ Произошла ошибка!")

    @bot.message_handler(func=lambda message: message.text == "🎰 Рулетка")
    def roulette_start(message):
        """Начало игры в Рулетку"""
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
                f"""🎰 <b>Игра "Рулетка"</b>

<blockquote>💎 Баланс: ${balance_rounded}</blockquote>

Выберите сумму ставки:""",
                reply_markup=get_roulette_bet_selection_keyboard(),
                parse_mode='HTML'
            )
        except Exception as e:
            logging.error(f"Ошибка в roulette_start: {e}")
            bot.send_message(message.chat.id, "❌ Ошибка запуска игры")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('roulette_'))
    def roulette_callback_handler(call):
        """Обработчик колбэков Рулетки"""
        try:
            user_id = str(call.from_user.id)

            # Проверяем задержку
            if not rate_limit(user_id):
                bot.answer_callback_query(call.id, "⏳ Не так быстро!", show_alert=False)
                return

            if call.data.startswith("roulette_bet_"):
                bet_amount = float(call.data.split("_")[2])
                users_data = load_users_data()

                balance = users_data[user_id].get('balance', 0)
                if bet_amount > balance:
                    bot.answer_callback_query(call.id, "❌ Недостаточно средств!")
                    return

                # Сразу запускаем игру без кнопки "Начать игру"
                play_roulette_game(bot, call, bet_amount, user_id)

            elif call.data == "roulette_custom_bet":
                bot.send_message(call.message.chat.id, "📝 Введите сумму ставки:")
                bot.register_next_step_handler(call.message, process_custom_bet_roulette)

            elif call.data == "roulette_rules":
                bot.edit_message_text(
                    get_roulette_rules(),
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🎮 Начать игру", callback_data="roulette_back_to_bet")
                    )
                )

            elif call.data == "roulette_back_to_bet":
                users_data = load_users_data()
                balance = users_data[user_id].get('balance', 0)
                balance_rounded = round(balance, 2)

                bot.edit_message_text(
                    f"""🎰 <b>Игра "Рулетка"</b>

<blockquote>💎 Баланс: ${balance_rounded}</blockquote>

Выберите сумму ставки:""",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=get_roulette_bet_selection_keyboard(),
                    parse_mode='HTML'
                )

            elif call.data == "roulette_back_to_choice":
                show_roulette_choice_screen(bot, user_id)

            elif call.data.startswith("roulette_choice_"):
                choice = call.data.split("_")[2]  # red, black, even, odd, number
                if choice == "number":
                    show_roulette_number_screen(bot, user_id)
                else:
                    process_roulette_choice(bot, call, choice, user_id)

            elif call.data.startswith("roulette_number_"):
                number = int(call.data.split("_")[2])
                process_roulette_choice(bot, call, f"number_{number}", user_id)

            elif call.data == "roulette_play_again":
                # Очищаем предыдущую игру
                if user_id in active_roulette_games:
                    del active_roulette_games[user_id]

                users_data = load_users_data()
                balance = users_data[user_id].get('balance', 0)
                balance_rounded = round(balance, 2)

                bot.edit_message_text(
                    f"""🎰 <b>Игра "Рулетка"</b>

<blockquote>💎 Баланс: ${balance_rounded}</blockquote>

Выберите сумму ставки:""",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=get_roulette_bet_selection_keyboard(),
                    parse_mode='HTML'
                )

            elif call.data == "roulette_other_games":
                # Возврат к основным играм
                if user_id in active_roulette_games:
                    del active_roulette_games[user_id]

                bot.edit_message_text(
                    "🎮 <b>Выберите игру:</b>",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML'
                )

        except Exception as e:
            logging.error(f"Ошибка в roulette_callback_handler: {e}")
            try:
                bot.answer_callback_query(call.id, "❌ Ошибка в игре")
            except:
                pass