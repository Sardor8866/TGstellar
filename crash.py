import telebot
from telebot import types
import random
import json
import time
import logging
import threading
import math

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

# Активные игры Краш
active_crash_games = {}

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

def get_crash_bet_selection_keyboard():
    """Клавиатура выбора ставки для Краш"""
    markup = types.InlineKeyboardMarkup(row_width=5)
    bets = ["0.2", "0.5", "1", "3", "5"]
    buttons = [types.InlineKeyboardButton(f"${bet}", callback_data=f"crash_bet_{bet}") for bet in bets]
    markup.row(*buttons)
    markup.row(types.InlineKeyboardButton("📝 Ввести вручную", callback_data="crash_custom_bet"))
    markup.row(types.InlineKeyboardButton("🎮 Правила игры", callback_data="crash_rules"))
    return markup

def get_crash_rules():
    """Правила игры в Краш"""
    return """🚀 <b>Игра "Краш" - Правила</b>

<blockquote>
🎯 <b>Как играть:</b>
• Выберите ставку
• Нажмите "Запустить игру"
• Наблюдайте за растущим множителем
• Нажмите "Забрать" до того как график упадет
• Чем позже заберете - тем больше выигрыш!

⚡ <b>Особенности:</b>
• Множитель растет от 1.00x
• График может упасть в любой момент
• Максимальный множитель: 25.00x
• Если не успели забрать - проигрыш!

💰 <b>Выигрыш:</b>
• Выигрыш = Ставка × Текущий множитель
</blockquote>

🎲 Удачи!"""

def generate_crash_multiplier():
    """Реалистичный алгоритм генерации множителя для казино"""
    # House edge ~5%
    house_edge = 0.05
    
    # Используем криптографически безопасное распределение
    rand = random.SystemRandom().uniform(0, 1)
    
    # Формула для расчета точки краха (стандартная для crash игр)
    crash_point = (1 - house_edge) / (1 - rand)
    crash_point = max(1.00, crash_point)
    
    # Ограничиваем максимальный множитель 25x
    crash_point = min(crash_point, 25.00)
    
    # Округляем до 2 знаков
    crash_point = round(crash_point, 2)
    
    return crash_point

def play_crash_game(bot, call, bet_amount, user_id):
    """Основная логика игры в Краш"""
    try:
        users_data = load_users_data()
        current_balance = users_data[user_id].get('balance', 0)

        # Списываем ставку сразу
        users_data[user_id]['balance'] = round(current_balance - bet_amount, 2)
        save_users_data(users_data)

        # Генерируем множитель краха
        crash_point = generate_crash_multiplier()

        # Сохраняем состояние игры
        active_crash_games[user_id] = {
            'bet_amount': bet_amount,
            'crash_point': crash_point,
            'current_multiplier': 1.00,
            'crashed': False,
            'user_cashed_out': False,
            'chat_id': call.message.chat.id,
            'message_id': call.message.message_id,
            'win_amount': 0,
            'start_time': time.time()
        }

        # Показываем экран с кнопкой "Запустить игру"
        show_crash_start_screen(bot, user_id)

    except Exception as e:
        logging.error(f"Ошибка запуска игры в Краш: {e}")
        bot.edit_message_text(
            "❌ Произошла ошибка при запуске игры",
            call.message.chat.id,
            call.message.message_id
        )

def show_crash_start_screen(bot, user_id):
    """Показывает экран начала игры с кнопкой Запустить"""
    try:
        if user_id not in active_crash_games:
            return

        game_data = active_crash_games[user_id]
        bet_amount = game_data['bet_amount']

        display = f"""🚀 <b>КРАШ ИГРА</b>

<blockquote>💵 Сумма ставки: ${bet_amount}</blockquote>

⚠️ <b>Ставка списана! Успейте забрать до краха!</b>

Нажмите "Запустить игру" чтобы начать!"""

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🚀 Запустить игру", callback_data="crash_launch"))

        bot.edit_message_text(
            display,
            game_data['chat_id'],
            game_data['message_id'],
            parse_mode='HTML',
            reply_markup=keyboard
        )

    except Exception as e:
        logging.error(f"Ошибка показа стартового экрана краша: {e}")

def start_crash_round(bot, user_id):
    """Запускает раунд краша"""
    try:
        if user_id not in active_crash_games:
            return

        # Запускаем поток для обновления множителя
        thread = threading.Thread(target=update_crash_multiplier, args=(bot, user_id))
        thread.daemon = True
        thread.start()

    except Exception as e:
        logging.error(f"Ошибка запуска раунда краша: {e}")

def update_crash_multiplier(bot, user_id):
    """Обновляет множитель в реальном времени"""
    try:
        if user_id not in active_crash_games:
            return

        game_data = active_crash_games[user_id]
        crash_point = game_data['crash_point']
        current_multiplier = 1.00

        # Начальная задержка перед стартом
        time.sleep(1)

        # Может упасть сразу на 1.00x
        if crash_point <= 1.00:
            game_data['crashed'] = True
            show_crash_result(bot, user_id)
            return

        while current_multiplier <= crash_point and user_id in active_crash_games:
            if game_data.get('user_cashed_out', False):
                break

            # Обновляем множитель
            current_multiplier += 0.01
            current_multiplier = round(current_multiplier, 2)
            game_data['current_multiplier'] = current_multiplier

            # Обновляем отображение
            update_crash_display(bot, user_id)

            # Ждем перед следующим обновлением
            time.sleep(0.1)  # 100ms между обновлениями

            # Проверяем достигли ли точки краха
            if current_multiplier >= crash_point:
                game_data['crashed'] = True
                break

        # Если не забрали вовремя - проигрыш
        if user_id in active_crash_games and not game_data.get('user_cashed_out', False):
            game_data['crashed'] = True
            show_crash_result(bot, user_id)

    except Exception as e:
        logging.error(f"Ошибка обновления множителя краша: {e}")

def update_crash_display(bot, user_id):
    """Обновляет отображение игры"""
    try:
        if user_id not in active_crash_games:
            return

        game_data = active_crash_games[user_id]
        current_multiplier = game_data['current_multiplier']
        bet_amount = game_data['bet_amount']

        # Создаем график множителя
        graph = create_crash_graph(current_multiplier)

        display = f"""🚀 <b>КРАШ ИГРА</b>

{graph}

<blockquote>
💰 Ставка: ${bet_amount}
📈 Текущий множитель: <code>{current_multiplier:.2f}x</code>
🏆 Можете забрать: ${bet_amount * current_multiplier:.2f}
</blockquote>"""

        if current_multiplier >= 10.00:
            display += "\n⚡ <b>Отличный множитель! Будьте осторожны!</b>"
        elif current_multiplier >= 5.00:
            display += "\n🔥 <b>Хороший рост! Рискуете потерять!</b>"
        elif current_multiplier >= 2.00:
            display += "\n📈 <b>Множитель растет! Может упасть в любой момент!</b>"
        else:
            display += "\n⚠️ <b>Осторожно! Может упасть на 1.00x!</b>"

        keyboard = get_crash_game_keyboard()

        try:
            bot.edit_message_text(
                display,
                game_data['chat_id'],
                game_data['message_id'],
                parse_mode='HTML',
                reply_markup=keyboard
            )
        except Exception as e:
            # Игнорируем ошибки редактирования сообщения
            pass

    except Exception as e:
        logging.error(f"Ошибка обновления отображения краша: {e}")

def create_crash_graph(current_multiplier):
    """Создает график множителя"""
    # Простой текстовый график
    max_multiplier = 25.0  # Максимум для отображения на графике
    graph_width = 20

    # Вычисляем позицию на графике
    position = min(int((current_multiplier / max_multiplier) * graph_width), graph_width)

    graph = "🟢" + "─" * position + "✈️" + "─" * (graph_width - position) + "🔴"

    # Добавляем шкалу множителей
    scale = f"\n1.0x{' ' * (graph_width-6)}25.0x"

    return graph + scale

def get_crash_game_keyboard():
    """Клавиатура во время игры"""
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("💰 Забрать выигрыш", callback_data="crash_cash_out")
    )
    return markup

def process_crash_cash_out(bot, call, user_id):
    """Обрабатывает кнопку Забрать"""
    try:
        if user_id not in active_crash_games:
            bot.answer_callback_query(call.id, "❌ Игра не найдена")
            return

        game_data = active_crash_games[user_id]

        if game_data.get('user_cashed_out', False):
            bot.answer_callback_query(call.id, "❌ Уже забрали выигрыш")
            return

        if game_data.get('crashed', False):
            bot.answer_callback_query(call.id, "❌ Уже произошел крах")
            return

        # Отмечаем что игрок забрал выигрыш
        game_data['user_cashed_out'] = True
        current_multiplier = game_data['current_multiplier']
        bet_amount = game_data['bet_amount']

        # Вычисляем выигрыш
        win_amount = round(bet_amount * current_multiplier, 2)
        game_data['win_amount'] = win_amount

        # Начисляем выигрыш
        users_data = load_users_data()
        users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0) + win_amount, 2)
        save_users_data(users_data)

        bot.answer_callback_query(call.id, f"✅ Забрали на {current_multiplier:.2f}x! Выигрыш: ${win_amount:.2f}")

        # Показываем результат
        show_crash_result(bot, user_id)

    except Exception as e:
        logging.error(f"Ошибка обработки кнопки Забрать: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка")

def show_crash_result(bot, user_id):
    """Показывает результат игры"""
    try:
        if user_id not in active_crash_games:
            return

        game_data = active_crash_games[user_id]
        bet_amount = game_data['bet_amount']
        crashed = game_data.get('crashed', False)
        user_cashed_out = game_data.get('user_cashed_out', False)
        final_multiplier = game_data['current_multiplier']
        win_amount = game_data.get('win_amount', 0)
        crash_point = game_data['crash_point']

        users_data = load_users_data()
        current_balance = users_data[user_id].get('balance', 0)

        display = f"""🎯 <b>РЕЗУЛЬТАТ ИГРЫ</b>

<blockquote>
💰 Ставка: ${bet_amount}
📈 Точка краха: {crash_point:.2f}x
🎮 Ваш множитель: {final_multiplier:.2f}x
💎 Текущий баланс: ${current_balance:.2f}
</blockquote>"""

        if user_cashed_out:
            profit = win_amount - bet_amount
            display += f"""\n✅ <b>ВЫ ВЫИГРАЛИ!</b>

<blockquote>
🏆 Выигрыш: ${win_amount:.2f}
💰 Чистая прибыль: ${profit:.2f}
</blockquote>

🎉 Поздравляем с выигрышем!"""
        else:
            display += f"""\n💥 <b>ВЫ ПРОИГРАЛИ</b>

<blockquote>
💸 Потеряно: ${bet_amount}
📉 Не успели забрать вовремя
</blockquote>

😔 В следующий раз повезет!"""

        # Клавиатура после игры
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔄 Играть снова", callback_data="crash_play_again"),
            types.InlineKeyboardButton("🎮 Другие игры", callback_data="crash_other_games")
        )

        bot.edit_message_text(
            display,
            game_data['chat_id'],
            game_data['message_id'],
            parse_mode='HTML',
            reply_markup=markup
        )

        # Удаляем игру из активных
        if user_id in active_crash_games:
            del active_crash_games[user_id]

    except Exception as e:
        logging.error(f"Ошибка показа результата краша: {e}")

def register_crash_handlers(bot):
    """Регистрация обработчиков для игры в Краш"""

    def process_custom_bet_crash(message):
        """Обработка ручного ввода ставки для Краш"""
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

            # Показываем экран с кнопкой "Запустить игру"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🚀 Запустить игру", callback_data=f"crash_start_{bet_amount}"))

            bot.send_message(
                message.chat.id,
                f"""🚀 <b>Игра "Краш"</b>

<blockquote>💵 Сумма ставки: ${bet_amount}</blockquote>

⚠️ <b>Ставка будет списана при запуске игры!</b>

Нажмите "Запустить игру" чтобы начать!""",
                reply_markup=markup,
                parse_mode='HTML'
            )

        except ValueError:
            bot.send_message(message.chat.id, "❌ Введите корректную сумму!")
        except Exception as e:
            logging.error(f"Ошибка в process_custom_bet_crash: {e}")
            bot.send_message(message.chat.id, "❌ Произошла ошибка!")

    @bot.message_handler(func=lambda message: message.text == "🚀 Краш")
    def crash_start(message):
        """Начало игры в Краш"""
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
                f"""🚀 <b>Игра "Краш"</b>

<blockquote>💎 Баланс: ${balance_rounded}</blockquote>

Выберите сумму ставки:""",
                reply_markup=get_crash_bet_selection_keyboard(),
                parse_mode='HTML'
            )
        except Exception as e:
            logging.error(f"Ошибка в crash_start: {e}")
            bot.send_message(message.chat.id, "❌ Ошибка запуска игры")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('crash_'))
    def crash_callback_handler(call):
        """Обработчик колбэков Краш"""
        try:
            user_id = str(call.from_user.id)

            # Проверяем задержку
            if not rate_limit(user_id):
                bot.answer_callback_query(call.id, "⏳ Не так быстро!", show_alert=False)
                return

            if call.data.startswith("crash_bet_"):
                bet_amount = float(call.data.split("_")[2])
                users_data = load_users_data()

                balance = users_data[user_id].get('balance', 0)
                if bet_amount > balance:
                    bot.answer_callback_query(call.id, "❌ Недостаточно средств!")
                    return

                # Показываем экран с кнопкой "Запустить игру"
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🚀 Запустить игру", callback_data=f"crash_start_{bet_amount}"))

                bot.edit_message_text(
                    f"""🚀 <b>Игра "Краш"</b>

<blockquote>💵 Сумма ставки: ${bet_amount}</blockquote>

⚠️ <b>Ставка будет списана при запуске игры!</b>

Нажмите "Запустить игру" чтобы начать!""",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=markup,
                    parse_mode='HTML'
                )

            elif call.data == "crash_custom_bet":
                bot.send_message(call.message.chat.id, "📝 Введите сумму ставки:")
                bot.register_next_step_handler(call.message, process_custom_bet_crash)

            elif call.data == "crash_rules":
                bot.edit_message_text(
                    get_crash_rules(),
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🎮 Начать игру", callback_data="crash_back_to_bet")
                    )
                )

            elif call.data == "crash_back_to_bet":
                users_data = load_users_data()
                balance = users_data[user_id].get('balance', 0)
                balance_rounded = round(balance, 2)

                bot.edit_message_text(
                    f"""🚀 <b>Игра "Краш"</b>

<blockquote>💎 Баланс: ${balance_rounded}</blockquote>

Выберите сумму ставки:""",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=get_crash_bet_selection_keyboard(),
                    parse_mode='HTML'
                )

            elif call.data.startswith("crash_start_"):
                bet_amount = float(call.data.split("_")[2])
                play_crash_game(bot, call, bet_amount, user_id)

            elif call.data == "crash_launch":
                start_crash_round(bot, user_id)

            elif call.data == "crash_cash_out":
                process_crash_cash_out(bot, call, user_id)

            elif call.data == "crash_play_again":
                # Очищаем предыдущую игру
                if user_id in active_crash_games:
                    del active_crash_games[user_id]

                users_data = load_users_data()
                balance = users_data[user_id].get('balance', 0)
                balance_rounded = round(balance, 2)

                bot.edit_message_text(
                    f"""🚀 <b>Игра "Краш"</b>

<blockquote>💎 Баланс: ${balance_rounded}</blockquote>

Выберите сумму ставки:""",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=get_crash_bet_selection_keyboard(),
                    parse_mode='HTML'
                )

            elif call.data == "crash_other_games":
                # Возврат к основным играм
                if user_id in active_crash_games:
                    del active_crash_games[user_id]

                bot.edit_message_text(
                    "🎮 <b>Выберите игру:</b>",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML'
                )

        except Exception as e:
            logging.error(f"Ошибка в crash_callback_handler: {e}")
            try:
                bot.answer_callback_query(call.id, "❌ Ошибка в игре")
            except:
                pass