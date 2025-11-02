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

# Активные игры Гробница
active_tomb_games = {}

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

def get_tomb_bet_selection_keyboard():
    """Клавиатура выбора ставки для Гробницы"""
    markup = types.InlineKeyboardMarkup(row_width=5)
    bets = ["0.2", "0.5", "1", "3", "5"]
    buttons = [types.InlineKeyboardButton(f"${bet}", callback_data=f"tomb_bet_{bet}") for bet in bets]
    markup.row(*buttons)
    markup.row(types.InlineKeyboardButton("📝 Ввести вручную", callback_data="tomb_custom_bet"))
    markup.row(types.InlineKeyboardButton("🎮 Правила игры", callback_data="tomb_rules"))
    return markup

def get_tomb_rules():
    """Правила игры в Гробницу"""
    return """
⚰️ <b>ИГРА \"ГРОБНИЦА\" - ПРАВИЛА</b>

<blockquote>
🎯 <b>Как играть:</b>
• Выберите ставку
• Перед вами 15 ячеек-гробниц
• В ячейках спрятаны множители от 0.01x до 5x
• У вас 2 попытки найти множители
• Можно забрать выигрыш в любой момент

💰 <b>Множители:</b>
• 5 ячеек с множителями > 1x: 1.5x, 1.9x, 2.5x, 3.6x, 3.9x
• Остальные ячейки: множители от 0.01x до 0.99x

🎲 <b>Особенности:</b>
• Выигрыш = Ставка × Множитель последней ячейки
• Можно забрать выигрыш после любого выбора
• После 2 выборов игра автоматически завершается

⚡ <b>Ставки:</b>
• Минимальная: ${MIN_BET}
• Максимальная: ${MAX_BET}
</blockquote>

⚰️ <i>Удачи в поисках сокровищ!</i>
"""

def create_tomb_multipliers():
    """Создает множители для гробницы"""
    # 5 ячеек с множителями выше 1x
    high_multipliers = [1.5, 1.9, 2.5, 3.6, 3.9]

    # 10 ячеек с множителями от 0.01x до 0.99x
    low_multipliers = [round(random.uniform(0.01, 0.99), 2) for _ in range(10)]

    # Объединяем и перемешиваем
    all_multipliers = high_multipliers + low_multipliers
    random.shuffle(all_multipliers)

    return all_multipliers

def get_tomb_keyboard(selected_positions, multipliers, can_take_win=False):
    """Клавиатура для выбора ячеек в гробнице"""
    markup = types.InlineKeyboardMarkup(row_width=5)

    # Первый ряд - 5 ячеек
    row1 = []
    for i in range(5):
        if i in selected_positions:
            multiplier = multipliers[i]
            if multiplier >= 1:
                row1.append(types.InlineKeyboardButton(f"🎯{multiplier}x", callback_data=f"tomb_selected_{i}"))
            else:
                row1.append(types.InlineKeyboardButton(f"💀{multiplier}x", callback_data=f"tomb_selected_{i}"))
        else:
            row1.append(types.InlineKeyboardButton("⚰️", callback_data=f"tomb_choose_{i}"))
    markup.row(*row1)

    # Второй ряд - 5 ячеек
    row2 = []
    for i in range(5, 10):
        if i in selected_positions:
            multiplier = multipliers[i]
            if multiplier >= 1:
                row2.append(types.InlineKeyboardButton(f"🎯{multiplier}x", callback_data=f"tomb_selected_{i}"))
            else:
                row2.append(types.InlineKeyboardButton(f"💀{multiplier}x", callback_data=f"tomb_selected_{i}"))
        else:
            row2.append(types.InlineKeyboardButton("⚰️", callback_data=f"tomb_choose_{i}"))
    markup.row(*row2)

    # Третий ряд - 5 ячеек
    row3 = []
    for i in range(10, 15):
        if i in selected_positions:
            multiplier = multipliers[i]
            if multiplier >= 1:
                row3.append(types.InlineKeyboardButton(f"🎯{multiplier}x", callback_data=f"tomb_selected_{i}"))
            else:
                row3.append(types.InlineKeyboardButton(f"💀{multiplier}x", callback_data=f"tomb_selected_{i}"))
        else:
            row3.append(types.InlineKeyboardButton("⚰️", callback_data=f"tomb_choose_{i}"))
    markup.row(*row3)

    # Кнопка забрать выигрыш
    if can_take_win:
        markup.row(types.InlineKeyboardButton("💰 ЗАБРАТЬ ВЫИГРЫШ", callback_data="tomb_take_win"))

    return markup

def create_tomb_display(selected_positions, multipliers, bet_amount, attempts_left, last_multiplier=None):
    """Создает отображение игры"""
    display = f"<b>⚰️ ГРОБНИЦА</b>\n\n"

    # Показываем выбранные ячейки
    if selected_positions:
        display += "<b>🔍 Открытые ячейки:</b>\n"
        for pos in selected_positions:
            multiplier = multipliers[pos]
            if multiplier >= 1:
                display += f"🎯 Ячейка {pos+1}: <b>{multiplier}x</b>\n"
            else:
                display += f"💀 Ячейка {pos+1}: {multiplier}x\n"
        display += "\n"

    display += f"<b>💰 Ставка:</b> ${bet_amount}\n"
    display += f"<b>🎯 Попыток осталось:</b> {attempts_left}\n"

    if last_multiplier:
        current_win = bet_amount * last_multiplier
        display += f"<b>📈 Текущий множитель:</b> {last_multiplier}x\n"
        display += f"<b>🏆 Можете забрать:</b> ${current_win:.2f}\n"

    display += f"\n<b>⚰️ Выберите гробницу для открытия:</b>"

    return display

def play_tomb_game(bot, call, bet_amount, user_id):
    """Основная логика игры в Гробницу"""
    try:
        users_data = load_users_data()
        current_balance = users_data[user_id].get('balance', 0)

        # Списываем ставку
        users_data[user_id]['balance'] = round(current_balance - bet_amount, 2)
        save_users_data(users_data)

        # Создаем множители
        multipliers = create_tomb_multipliers()

        # Сохраняем состояние игры
        active_tomb_games[user_id] = {
            'bet_amount': bet_amount,
            'multipliers': multipliers,
            'selected_positions': [],
            'attempts_left': 2,
            'last_multiplier': None,
            'chat_id': call.message.chat.id,
            'message_id': call.message.message_id
        }

        # Сразу показываем игру (без кнопки "Начать игру")
        show_tomb_game_state(bot, user_id)

    except Exception as e:
        logging.error(f"Ошибка запуска игры в Гробницу: {e}")
        bot.edit_message_text(
            "❌ Произошла ошибка при запуске игры",
            call.message.chat.id,
            call.message.message_id
        )

def show_tomb_game_state(bot, user_id):
    """Показывает текущее состояние игры"""
    try:
        if user_id not in active_tomb_games:
            return

        game_data = active_tomb_games[user_id]
        multipliers = game_data['multipliers']
        selected_positions = game_data['selected_positions']
        bet_amount = game_data['bet_amount']
        attempts_left = game_data['attempts_left']
        last_multiplier = game_data['last_multiplier']

        # Создаем отображение игры
        display = create_tomb_display(selected_positions, multipliers, bet_amount, attempts_left, last_multiplier)

        # Можно забрать выигрыш если есть хотя бы один выбор
        can_take_win = len(selected_positions) > 0

        # Создаем клавиатуру
        keyboard = get_tomb_keyboard(selected_positions, multipliers, can_take_win)

        # Обновляем сообщение
        bot.edit_message_text(
            display,
            game_data['chat_id'],
            game_data['message_id'],
            parse_mode='HTML',
            reply_markup=keyboard
        )

    except Exception as e:
        logging.error(f"Ошибка показа состояния гробницы: {e}")

def process_tomb_choice(bot, call, choice_index, user_id):
    """Обрабатывает выбор ячейки в гробнице"""
    try:
        if user_id not in active_tomb_games:
            bot.answer_callback_query(call.id, "❌ Игра не найдена")
            return

        game_data = active_tomb_games[user_id]
        multipliers = game_data['multipliers']
        selected_positions = game_data['selected_positions']
        attempts_left = game_data['attempts_left']

        # Проверяем выбор
        if choice_index in selected_positions:
            bot.answer_callback_query(call.id, "❌ Эта ячейка уже открыта")
            return

        if attempts_left <= 0:
            bot.answer_callback_query(call.id, "❌ Попытки закончились")
            return

        # Добавляем позицию в выбранные
        selected_positions.append(choice_index)
        game_data['selected_positions'] = selected_positions

        # Уменьшаем количество попыток
        game_data['attempts_left'] -= 1

        # Сохраняем последний множитель
        last_multiplier = multipliers[choice_index]
        game_data['last_multiplier'] = last_multiplier

        # Показываем результат выбора
        if last_multiplier >= 1:
            bot.answer_callback_query(call.id, f"🎯 Нашли множитель {last_multiplier}x!")
        else:
            bot.answer_callback_query(call.id, f"💀 Множитель {last_multiplier}x")

        # Проверяем окончание игры
        if game_data['attempts_left'] <= 0:
            # Автоматически завершаем игру после 2 выборов
            show_tomb_final_result(bot, user_id)
        else:
            # Показываем обновленное состояние
            show_tomb_game_state(bot, user_id)

    except Exception as e:
        logging.error(f"Ошибка обработки выбора в гробнице: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка в игре")

def take_tomb_win(bot, user_id):
    """Забрать выигрыш досрочно"""
    try:
        if user_id not in active_tomb_games:
            return

        game_data = active_tomb_games[user_id]
        users_data = load_users_data()
        bet_amount = game_data['bet_amount']
        last_multiplier = game_data['last_multiplier']

        if last_multiplier is None:
            # Если еще не выбирали ячейки, возвращаем ставку
            win_amount = bet_amount
        else:
            # Вычисляем выигрыш по последнему множителю
            win_amount = round(bet_amount * last_multiplier, 2)

        # Начисляем выигрыш
        users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0) + win_amount, 2)
        save_users_data(users_data)

        # Показываем результат
        show_tomb_final_result(bot, user_id, manual_take=True)

    except Exception as e:
        logging.error(f"Ошибка при взятии выигрыша гробницы: {e}")

def show_tomb_final_result(bot, user_id, manual_take=False):
    """Показывает финальный результат"""
    try:
        if user_id not in active_tomb_games:
            return

        game_data = active_tomb_games[user_id]
        users_data = load_users_data()
        bet_amount = game_data['bet_amount']
        multipliers = game_data['multipliers']
        selected_positions = game_data['selected_positions']
        last_multiplier = game_data['last_multiplier']

        display = f"<b>⚰️ ГРОБНИЦА - РЕЗУЛЬТАТ</b>\n\n"

        # Показываем все открытые ячейки
        if selected_positions:
            display += "<b>🔍 Открытые ячейки:</b>\n"
            for pos in selected_positions:
                multiplier = multipliers[pos]
                if multiplier >= 1:
                    display += f"🎯 Ячейка {pos+1}: <b>{multiplier}x</b>\n"
                else:
                    display += f"💀 Ячейка {pos+1}: {multiplier}x\n"
            display += "\n"

        win_amount = 0
        result_text = ""

        if manual_take:
            # Игрок забрал досрочно
            if last_multiplier is None:
                win_amount = bet_amount
                result_text = f"<b>💰 ВЫ ЗАБРАЛИ СТАВКУ!</b>\n\n<blockquote>💰 Ставка: ${bet_amount}\n↩️ Возврат: ${bet_amount}</blockquote>"
            else:
                win_amount = round(bet_amount * last_multiplier, 2)
                profit = win_amount - bet_amount
                result_text = f"<b>💰 ВЫ ЗАБРАЛИ ВЫИГРЫШ!</b>\n\n<blockquote>💰 Ставка: ${bet_amount}\n🎯 Множитель: {last_multiplier}x\n🏆 Выигрыш: ${win_amount:.2f}\n💵 Прибыль: ${profit:.2f}</blockquote>"
        else:
            # Автоматическое завершение после 2 выборов
            if last_multiplier is None:
                win_amount = 0
                result_text = f"<b>❌ ИГРА ЗАВЕРШЕНА!</b>\n\n<blockquote>💰 Ставка: ${bet_amount}\n💸 Потеряно: ${bet_amount}</blockquote>"
            else:
                win_amount = round(bet_amount * last_multiplier, 2)
                users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0) + win_amount, 2)
                profit = win_amount - bet_amount
                if profit >= 0:
                    result_text = f"<b>🎯 ИГРА ЗАВЕРШЕНА!</b>\n\n<blockquote>💰 Ставка: ${bet_amount}\n🎯 Множитель: {last_multiplier}x\n🏆 Выигрыш: ${win_amount:.2f}\n💵 Прибыль: ${profit:.2f}</blockquote>"
                else:
                    result_text = f"<b>🎯 ИГРА ЗАВЕРШЕНА!</b>\n\n<blockquote>💰 Ставка: ${bet_amount}\n🎯 Множитель: {last_multiplier}x\n🏆 Выигрыш: ${win_amount:.2f}\n💸 Убыток: ${-profit:.2f}</blockquote>"

        save_users_data(users_data)

        display += result_text

        # Клавиатура после игры
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔄 ИГРАТЬ СНОВА", callback_data="tomb_play_again"),
            types.InlineKeyboardButton("🎮 ДРУГИЕ ИГРЫ", callback_data="tomb_other_games")
        )

        bot.edit_message_text(
            display,
            game_data['chat_id'],
            game_data['message_id'],
            parse_mode='HTML',
            reply_markup=markup
        )

        # Удаляем игру из активных
        if user_id in active_tomb_games:
            del active_tomb_games[user_id]

    except Exception as e:
        logging.error(f"Ошибка показа результата гробницы: {e}")

def register_tomb_handlers(bot):
    """Регистрация обработчиков для игры в Гробницу"""

    def process_custom_bet_tomb(message):
        """Обработка ручного ввода ставки для Гробницы"""
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
            play_tomb_game(bot, types.CallbackQuery(message=message, data=f"tomb_start_{bet_amount}", from_user=message.from_user, id=""), bet_amount, user_id)

        except ValueError:
            bot.send_message(message.chat.id, "❌ Введите корректную сумму!")
        except Exception as e:
            logging.error(f"Ошибка в process_custom_bet_tomb: {e}")
            bot.send_message(message.chat.id, "❌ Произошла ошибка!")

    @bot.message_handler(func=lambda message: message.text == "⚰️ Гробница")
    def tomb_start(message):
        """Начало игры в Гробницу"""
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
                f"""<b>⚰️ ИГРА "ГРОБНИЦА"</b>

<blockquote>💎 Баланс: ${balance_rounded}</blockquote>

<b>Выберите сумму ставки:</b>""",
                reply_markup=get_tomb_bet_selection_keyboard(),
                parse_mode='HTML'
            )
        except Exception as e:
            logging.error(f"Ошибка в tomb_start: {e}")
            bot.send_message(message.chat.id, "❌ Ошибка запуска игры")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tomb_'))
    def tomb_callback_handler(call):
        """Обработчик колбэков Гробницы"""
        try:
            user_id = str(call.from_user.id)

            # Проверяем задержку
            if not rate_limit(user_id):
                bot.answer_callback_query(call.id, "⏳ Не так быстро!", show_alert=False)
                return

            if call.data.startswith("tomb_bet_"):
                bet_amount = float(call.data.split("_")[2])
                users_data = load_users_data()

                balance = users_data[user_id].get('balance', 0)
                if bet_amount > balance:
                    bot.answer_callback_query(call.id, "❌ Недостаточно средств!")
                    return

                # Сразу запускаем игру (без кнопки "Начать игру")
                play_tomb_game(bot, call, bet_amount, user_id)

            elif call.data == "tomb_custom_bet":
                bot.send_message(call.message.chat.id, "📝 Введите сумму ставки:")
                bot.register_next_step_handler(call.message, process_custom_bet_tomb)

            elif call.data == "tomb_rules":
                bot.edit_message_text(
                    get_tomb_rules(),
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🎮 ВЫБРАТЬ СТАВКУ", callback_data="tomb_back_to_bet")
                    )
                )

            elif call.data == "tomb_back_to_bet":
                users_data = load_users_data()
                balance = users_data[user_id].get('balance', 0)
                balance_rounded = round(balance, 2)

                bot.edit_message_text(
                    f"""<b>⚰️ ИГРА "ГРОБНИЦА"</b>

<blockquote>💎 Баланс: ${balance_rounded}</blockquote>

<b>Выберите сумму ставки:</b>""",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=get_tomb_bet_selection_keyboard(),
                    parse_mode='HTML'
                )

            elif call.data.startswith("tomb_choose_"):
                choice_index = int(call.data.split("_")[2])
                process_tomb_choice(bot, call, choice_index, user_id)

            elif call.data == "tomb_take_win":
                take_tomb_win(bot, user_id)

            elif call.data == "tomb_play_again":
                # Очищаем предыдущую игру
                if user_id in active_tomb_games:
                    del active_tomb_games[user_id]

                users_data = load_users_data()
                balance = users_data[user_id].get('balance', 0)
                balance_rounded = round(balance, 2)

                bot.edit_message_text(
                    f"""<b>⚰️ ИГРА "ГРОБНИЦА"</b>

<blockquote>💎 Баланс: ${balance_rounded}</blockquote>

<b>Выберите сумму ставки:</b>""",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=get_tomb_bet_selection_keyboard(),
                    parse_mode='HTML'
                )

            elif call.data == "tomb_other_games":
                # Возврат к основным играм
                if user_id in active_tomb_games:
                    del active_tomb_games[user_id]

                bot.edit_message_text(
                    "🎮 <b>Выберите игру:</b>",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML'
                )

        except Exception as e:
            logging.error(f"Ошибка в tomb_callback_handler: {e}")
            try:
                bot.answer_callback_query(call.id, "❌ Ошибка в игре")
            except:
                pass