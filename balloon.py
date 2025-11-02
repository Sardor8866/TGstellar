import telebot
from telebot import types
import random
import json
import logging
import time

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

# Активные игры шарика
active_balloon_games = {}

# Минимальная и максимальная ставка
MIN_BET = 0.2
MAX_BET = 1000

# Задержка между нажатиями
last_click_time = {}

def rate_limit(user_id):
    """Проверка ограничения по времени между нажатиями (0.4 секунды)"""
    current_time = time.time()
    if user_id in last_click_time:
        if current_time - last_click_time[user_id] < 0.4:
            return False
    last_click_time[user_id] = current_time
    return True

def get_balloon_bet_selection_keyboard():
    """Клавиатура выбора ставки для шарика"""
    markup = types.InlineKeyboardMarkup(row_width=5)
    bets = ["0.2", "0.5", "1", "3", "5"]
    buttons = [types.InlineKeyboardButton(f"${bet}", callback_data=f"balloon_bet_{bet}") for bet in bets]
    markup.row(*buttons)
    markup.row(types.InlineKeyboardButton("📝 Ввести вручную", callback_data="balloon_custom_bet"))
    markup.row(types.InlineKeyboardButton("🎮 Правила игры", callback_data="balloon_rules"))
    return markup

def get_balloon_rules():
    """Правила игры в шарик"""
    return """
🎈 <b>ИГРА "ШАРИК" - ПРАВИЛА</b>

<blockquote>
🎯 <b>Как играть:</b>
• Выберите ставку
• На каждом ходу выбирайте:
  - 🎈 Надуть (+0.2x к множителю)
  - 💰 Забрать (забрать текущий выигрыш)

📊 <b>Механика:</b>
• Начальный множитель: 1.0x
• Каждое надувание: +0.2x к множителю
• Шанс лопнуть: 15% при каждом надувании
• Максимальный множитель: 10.0x

⚠️ <b>Риски:</b>
• Если шарик лопнет - вы теряете ставку
• Чем выше множитель - тем выше риск

🎮 <b>Стратегия:</b>
• Надувайте осторожно!
• Вовремя забирайте выигрыш
• Не жадничайте!

⚡ <b>Ставки:</b>
• Минимальная: ${MIN_BET}
• Максимальная: ${MAX_BET}
</blockquote>

🎈 <i>Удачи в надувании!</i>
"""

def play_balloon_game(bot, call, bet_amount, user_id):
    """Запуск игры в шарик"""
    try:
        users_data = load_users_data()
        current_balance = users_data[user_id].get('balance', 0)

        # Списываем ставку
        users_data[user_id]['balance'] = round(current_balance - bet_amount, 2)
        save_users_data(users_data)

        # Создаем новую игру
        game_data = {
            'bet_amount': bet_amount,
            'multiplier': 1.0,
            'game_active': True,
            'chat_id': call.message.chat.id,
            'message_id': call.message.message_id
        }

        active_balloon_games[user_id] = game_data

        # Сразу показываем игру (без кнопки "Начать игру")
        show_balloon_game_state(bot, call, user_id)

    except Exception as e:
        logging.error(f"Ошибка запуска игры в шарик: {e}")
        bot.edit_message_text(
            "❌ Произошла ошибка при запуске игры",
            call.message.chat.id,
            call.message.message_id
        )

def show_balloon_game_state(bot, call, user_id):
    """Показывает текущее состояние игры"""
    try:
        if user_id not in active_balloon_games:
            return

        game_data = active_balloon_games[user_id]
        bet_amount = game_data['bet_amount']
        multiplier = game_data['multiplier']

        # Создаем визуализацию шарика
        balloon_visual = create_balloon_visual(multiplier)
        risk_level = calculate_risk_level(multiplier)

        # Текущий возможный выигрыш
        current_win = bet_amount * multiplier

        message_text = f"""
<b>🎈 ИГРА "ШАРИК"</b>

<blockquote>
💰 Ставка: ${bet_amount}
🎯 Текущий множитель: {multiplier:.1f}x
🏆 Текущий выигрыш: ${current_win:.2f}
⚠️ Уровень риска: {risk_level}
</blockquote>

{balloon_visual}

<b>🎮 Выберите действие:</b>
"""

        # Создаем клавиатуру (убрали кнопку "Выйти")
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("🎈 НАДУТЬ (+0.2x)", callback_data="balloon_inflate"),
            types.InlineKeyboardButton("💰 ЗАБРАТЬ", callback_data="balloon_cashout")
        )

        bot.edit_message_text(
            message_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='HTML'
        )

    except Exception as e:
        logging.error(f"Ошибка показа состояния шарика: {e}")

def create_balloon_visual(multiplier):
    """Создает визуализацию шарика в зависимости от множителя"""
    if multiplier < 2.0:
        return "🔴 ━━━━━━━━━━ 10.0x\n🟢 ██████████"  # Маленький шарик
    elif multiplier < 4.0:
        return "🟠 ━━━━━━━━━━ 10.0x\n🟢 ████░░░░░░"  # Средний шарик
    elif multiplier < 6.0:
        return "🟡 ━━━━━━━━━━ 10.0x\n🟢 ██████░░░░"  # Большой шарик
    elif multiplier < 8.0:
        return "🟣 ━━━━━━━━━━ 10.0x\n🟢 ████████░░"  # Очень большой шарик
    else:
        return "💥 ━━━━━━━━━━ 10.0x\n🟢 █████████░"  # Опасный размер

def calculate_risk_level(multiplier):
    """Рассчитывает уровень риска"""
    if multiplier < 2.0:
        return "🟢 Низкий"
    elif multiplier < 4.0:
        return "🟡 Средний"
    elif multiplier < 6.0:
        return "🟠 Высокий"
    elif multiplier < 8.0:
        return "🔴 Очень высокий"
    else:
        return "💥 КРИТИЧЕСКИЙ"

def process_balloon_inflate(bot, call, user_id):
    """Обработка надувания шарика"""
    try:
        if user_id not in active_balloon_games:
            bot.answer_callback_query(call.id, "❌ Игра не найдена")
            return

        game_data = active_balloon_games[user_id]

        # Проверяем шанс лопнуть (15%)
        if random.random() < 0.15:
            # Шарик лопнул
            game_data['game_active'] = False
            show_balloon_burst_result(bot, call, user_id)
            return

        # Увеличиваем множитель
        game_data['multiplier'] = round(game_data['multiplier'] + 0.2, 1)

        # Проверяем максимальный множитель
        if game_data['multiplier'] >= 10.0:
            game_data['multiplier'] = 10.0
            bot.answer_callback_query(call.id, "🎉 Достигнут максимальный множитель 10.0x!")
        else:
            bot.answer_callback_query(call.id, "✅ Шарик надут! +0.2x")

        # Показываем обновленное состояние
        show_balloon_game_state(bot, call, user_id)

    except Exception as e:
        logging.error(f"Ошибка надувания шарика: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка в игре")

def process_balloon_cashout(bot, call, user_id):
    """Обработка вывода выигрыша"""
    try:
        if user_id not in active_balloon_games:
            bot.answer_callback_query(call.id, "❌ Игра не найдена")
            return

        game_data = active_balloon_games[user_id]
        bet_amount = game_data['bet_amount']
        multiplier = game_data['multiplier']

        # Вычисляем выигрыш
        win_amount = round(bet_amount * multiplier, 2)

        # Обновляем баланс
        users_data = load_users_data()
        users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0) + win_amount, 2)
        save_users_data(users_data)

        # Завершаем игру
        game_data['game_active'] = False

        # Показываем результат
        show_balloon_win_result(bot, call, user_id, win_amount)

    except Exception as e:
        logging.error(f"Ошибка вывода в шарике: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка в игре")

def show_balloon_win_result(bot, call, user_id, win_amount):
    """Показывает результат победы"""
    try:
        if user_id not in active_balloon_games:
            return

        game_data = active_balloon_games[user_id]
        bet_amount = game_data['bet_amount']
        multiplier = game_data['multiplier']
        
        users_data = load_users_data()
        current_balance = users_data[user_id].get('balance', 0)
        profit = win_amount - bet_amount

        message_text = f"""
<b>🎉 ПОБЕДА!</b>

<blockquote>
💰 Ставка: ${bet_amount}
🎯 Финальный множитель: {multiplier:.1f}x
🏆 Выигрыш: ${win_amount:.2f}
💵 Прибыль: ${profit:.2f}
💎 Текущий баланс: ${current_balance:.2f}
</blockquote>

🎈 <i>Вы успешно забрали выигрыш!</i>
"""

        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("🔄 ИГРАТЬ СНОВА", callback_data="balloon_play_again"),
            types.InlineKeyboardButton("🎮 ДРУГИЕ ИГРЫ", callback_data="balloon_other_games")
        )

        bot.edit_message_text(
            message_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='HTML'
        )

        # Удаляем игру из активных
        del active_balloon_games[user_id]

    except Exception as e:
        logging.error(f"Ошибка показа победы: {e}")

def show_balloon_burst_result(bot, call, user_id):
    """Показывает результат лопнувшего шарика"""
    try:
        if user_id not in active_balloon_games:
            return

        game_data = active_balloon_games[user_id]
        bet_amount = game_data['bet_amount']
        multiplier = game_data['multiplier']
        
        users_data = load_users_data()
        current_balance = users_data[user_id].get('balance', 0)

        message_text = f"""
<b>💥 ШАРИК ЛОПНУЛ!</b>

<blockquote>
💰 Ставка: ${bet_amount}
🎯 Достигнутый множитель: {multiplier:.1f}x
💸 Потеряно: ${bet_amount}
💎 Текущий баланс: ${current_balance:.2f}
</blockquote>

😞 <i>Шарик не выдержал давления...</i>
"""

        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("🔄 ИГРАТЬ СНОВА", callback_data="balloon_play_again"),
            types.InlineKeyboardButton("🎮 ДРУГИЕ ИГРЫ", callback_data="balloon_other_games")
        )

        bot.edit_message_text(
            message_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='HTML'
        )

        # Удаляем игру из активных
        del active_balloon_games[user_id]

    except Exception as e:
        logging.error(f"Ошибка показа проигрыша: {e}")

def register_balloon_handlers(bot):
    """Регистрация обработчиков для игры в шарик"""

    def process_custom_bet_balloon(message):
        """Обработка ручного ввода ставки для шарика"""
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

            # Сразу запускаем игру (без кнопки "Начать игру")
            play_balloon_game(bot, types.CallbackQuery(message=message, data=f"balloon_start_{bet_amount}", from_user=message.from_user, id=""), bet_amount, user_id)

        except ValueError:
            bot.send_message(message.chat.id, "❌ Введите корректную сумму!")
        except Exception as e:
            logging.error(f"Ошибка в process_custom_bet_balloon: {e}")
            bot.send_message(message.chat.id, "❌ Произошла ошибка!")

    @bot.message_handler(func=lambda message: message.text == "🎈 Шарик")
    def balloon_start(message):
        """Начало игры в шарик"""
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
                f"""<b>🎈 ИГРА "ШАРИК"</b>

<blockquote>💎 Баланс: ${balance_rounded}</blockquote>

<b>Выберите сумму ставки:</b>""",
                reply_markup=get_balloon_bet_selection_keyboard(),
                parse_mode='HTML'
            )
        except Exception as e:
            logging.error(f"Ошибка в balloon_start: {e}")
            bot.send_message(message.chat.id, "❌ Ошибка запуска игры")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('balloon_'))
    def balloon_callback_handler(call):
        """Обработчик колбэков шарика"""
        try:
            user_id = str(call.from_user.id)

            # Проверяем задержку
            if not rate_limit(user_id):
                bot.answer_callback_query(call.id, "⏳ Не так быстро!", show_alert=False)
                return

            if call.data.startswith("balloon_bet_"):
                bet_amount = float(call.data.split("_")[2])
                users_data = load_users_data()

                balance = users_data[user_id].get('balance', 0)
                if bet_amount > balance:
                    bot.answer_callback_query(call.id, "❌ Недостаточно средств!")
                    return

                # Сразу запускаем игру (без кнопки "Начать игру")
                play_balloon_game(bot, call, bet_amount, user_id)

            elif call.data == "balloon_custom_bet":
                bot.send_message(call.message.chat.id, "📝 Введите сумму ставки:")
                bot.register_next_step_handler(call.message, process_custom_bet_balloon)

            elif call.data == "balloon_rules":
                bot.edit_message_text(
                    get_balloon_rules(),
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🎮 ВЫБРАТЬ СТАВКУ", callback_data="balloon_back_to_bet")
                    )
                )

            elif call.data == "balloon_back_to_bet":
                users_data = load_users_data()
                balance = users_data[user_id].get('balance', 0)
                balance_rounded = round(balance, 2)

                bot.edit_message_text(
                    f"""<b>🎈 ИГРА "ШАРИК"</b>

<blockquote>💎 Баланс: ${balance_rounded}</blockquote>

<b>Выберите сумму ставки:</b>""",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=get_balloon_bet_selection_keyboard(),
                    parse_mode='HTML'
                )

            elif call.data == "balloon_inflate":
                process_balloon_inflate(bot, call, user_id)

            elif call.data == "balloon_cashout":
                process_balloon_cashout(bot, call, user_id)

            elif call.data == "balloon_play_again":
                # Очищаем предыдущую игру
                if user_id in active_balloon_games:
                    del active_balloon_games[user_id]

                users_data = load_users_data()
                balance = users_data[user_id].get('balance', 0)
                balance_rounded = round(balance, 2)

                bot.edit_message_text(
                    f"""<b>🎈 ИГРА "ШАРИК"</b>

<blockquote>💎 Баланс: ${balance_rounded}</blockquote>

<b>Выберите сумму ставки:</b>""",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=get_balloon_bet_selection_keyboard(),
                    parse_mode='HTML'
                )

            elif call.data == "balloon_other_games":
                # Возврат к основным играм
                if user_id in active_balloon_games:
                    del active_balloon_games[user_id]

                bot.edit_message_text(
                    "🎮 <b>Выберите игру:</b>",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML'
                )

        except Exception as e:
            logging.error(f"Ошибка в balloon_callback_handler: {e}")
            try:
                bot.answer_callback_query(call.id, "❌ Ошибка в игре")
            except:
                pass