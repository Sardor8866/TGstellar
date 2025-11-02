import telebot
from telebot import types
import random
import json
import time
import logging

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

# Активные игры КНБ
active_rps_games = {}

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

def get_rps_bet_selection_keyboard():
    """Клавиатура выбора ставки для КНБ"""
    markup = types.InlineKeyboardMarkup(row_width=5)
    bets = ["0.2", "0.5", "1", "3", "5"]
    buttons = [types.InlineKeyboardButton(f"${bet}", callback_data=f"rps_bet_{bet}") for bet in bets]
    markup.row(*buttons)
    markup.row(types.InlineKeyboardButton("📝 Ввести вручную", callback_data="rps_custom_bet"))
    markup.row(types.InlineKeyboardButton("🎮 Правила игры", callback_data="rps_rules"))
    return markup

def get_rps_rules():
    """Правила игры в КНБ"""
    return """
🎮 <b>КАМЕНЬ-НОЖНИЦЫ-БУМАГА - ПРАВИЛА</b>

<blockquote>
🎯 <b>Как играть:</b>
• Выберите ставку
• Выберите свою фигуру: Камень 🪨, Ножницы ✂️ или Бумага 📄
• Бот одновременно выберет свою фигуру
• Определяем победителя по правилам:

🪨 Камень бьет ✂️ Ножницы
✂️ Ножницы бьют 📄 Бумагу
📄 Бумага бьет 🪨 Камень

💰 <b>Выигрыш:</b>
• Победа: 2x от ставки
• Ничья: возврат ставки
• Проигрыш: потеря ставки

⚡ <b>Ставки:</b>
• Минимальная: ${MIN_BET}
• Максимальная: ${MAX_BET}
</blockquote>

🎮 <i>Удачи в игре!</i>
"""

def get_rps_choice_keyboard():
    """Клавиатура выбора фигуры для КНБ"""
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.row(
        types.InlineKeyboardButton("✊ Камень", callback_data="rps_choice_rock"),
        types.InlineKeyboardButton("✌️ Ножницы", callback_data="rps_choice_scissors"),
        types.InlineKeyboardButton("✋ Бумага", callback_data="rps_choice_paper")
    )
    return markup

def determine_rps_winner(player_choice, bot_choice):
    """Определяет победителя в КНБ"""
    if player_choice == bot_choice:
        return "draw"

    winning_combinations = {
        "rock": "scissors",     # Камень бьет ножницы
        "scissors": "paper",    # Ножницы бьют бумагу
        "paper": "rock"         # Бумага бьет камень
    }

    if winning_combinations[player_choice] == bot_choice:
        return "player"
    else:
        return "bot"

def get_hand_animation_frames(choice):
    """Возвращает кадры анимации для жеста"""
    if choice == "rock":
        return ["✊", "✊", "✊"]  # Камень
    elif choice == "scissors":
        return ["✌️", "✌️", "✌️"]  # Ножницы
    elif choice == "paper":
        return ["✋", "✋", "✋"]  # Бумага
    return ["❓", "❓", "❓"]

def get_choice_emoji(choice):
    """Возвращает эмоджи предмета для выбора"""
    emojis = {
        "rock": "🪨",
        "scissors": "✂️",
        "paper": "📄"
    }
    return emojis.get(choice, "❓")

def get_choice_name(choice):
    """Возвращает название выбора"""
    names = {
        "rock": "Камень",
        "scissors": "Ножницы",
        "paper": "Бумага"
    }
    return names.get(choice, "Неизвестно")

def play_rps_game(bot, call, bet_amount, user_id):
    """Основная логика игры в КНБ"""
    try:
        users_data = load_users_data()
        current_balance = users_data[user_id].get('balance', 0)

        # Списываем ставку
        users_data[user_id]['balance'] = round(current_balance - bet_amount, 2)
        save_users_data(users_data)

        # Сохраняем состояние игры
        active_rps_games[user_id] = {
            'bet_amount': bet_amount,
            'chat_id': call.message.chat.id,
            'message_id': call.message.message_id
        }

        # Сразу показываем выбор фигуры (без кнопки "Начать игру")
        show_rps_choice_screen(bot, user_id)

    except Exception as e:
        logging.error(f"Ошибка запуска игры в КНБ: {e}")
        bot.edit_message_text(
            "❌ Произошла ошибка при запуске игры",
            call.message.chat.id,
            call.message.message_id
        )

def show_rps_choice_screen(bot, user_id):
    """Показывает экран выбора фигуры"""
    try:
        if user_id not in active_rps_games:
            return

        game_data = active_rps_games[user_id]
        bet_amount = game_data['bet_amount']

        display = f"""<b>🎮 КАМЕНЬ-НОЖНИЦЫ-БУМАГА</b>

<blockquote>💰 Ставка: ${bet_amount}</blockquote>

<b>Выберите вашу фигуру:</b>"""

        keyboard = get_rps_choice_keyboard()

        bot.edit_message_text(
            display,
            game_data['chat_id'],
            game_data['message_id'],
            parse_mode='HTML',
            reply_markup=keyboard
        )

    except Exception as e:
        logging.error(f"Ошибка показа выбора КНБ: {e}")

def process_rps_choice(bot, call, player_choice, user_id):
    """Обрабатывает выбор игрока"""
    try:
        if user_id not in active_rps_games:
            bot.answer_callback_query(call.id, "❌ Игра не найдена")
            return

        game_data = active_rps_games[user_id]
        bet_amount = game_data['bet_amount']

        # Бот выбирает случайную фигуру
        choices = ["rock", "scissors", "paper"]
        bot_choice = random.choice(choices)

        # Определяем победителя
        result = determine_rps_winner(player_choice, bot_choice)

        # Показываем анимацию с двумя эмоджи одновременно
        show_rps_double_emoji_animation(bot, user_id, player_choice, bot_choice, result, bet_amount)

    except Exception as e:
        logging.error(f"Ошибка обработки выбора КНБ: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка в игре")

def show_rps_double_emoji_animation(bot, user_id, player_choice, bot_choice, result, bet_amount):
    """Показывает анимацию с двумя эмоджи одновременно"""
    try:
        if user_id not in active_rps_games:
            return

        game_data = active_rps_games[user_id]

        # Получаем анимационные кадры для обоих игроков
        player_frames = get_hand_animation_frames(player_choice)
        bot_frames = get_hand_animation_frames(bot_choice)

        # Этап 1: Обратный отсчет с анимацией
        countdown_texts = ["3...", "2...", "1..."]

        for i in range(3):
            display = f"""<b>🎮 КАМЕНЬ-НОЖНИЦЫ-БУМАГА</b>

<blockquote>💰 Ставка: ${bet_amount}</blockquote>

<b>Игра начинается через...</b>

🎯 {countdown_texts[i]}

👤 ВАШ ХОД          🤖 ХОД БОТА
{player_frames[i]}                            {bot_frames[i]}"""

            bot.edit_message_text(
                display,
                game_data['chat_id'],
                game_data['message_id'],
                parse_mode='HTML'
            )
            time.sleep(1)

        # Этап 2: Финальный показ с результатами
        player_hand = player_frames[-1]
        bot_hand = bot_frames[-1]
        player_item = get_choice_emoji(player_choice)
        bot_item = get_choice_emoji(bot_choice)
        player_name = get_choice_name(player_choice)
        bot_name = get_choice_name(bot_choice)

        display = f"""<b>🎮 КАМЕНЬ-НОЖНИЦЫ-БУМАГА</b>

<blockquote>💰 Ставка: ${bet_amount}</blockquote>

<b>ФИНАЛЬНЫЙ РАУНД!</b>

👤 <b>ВАШ ВЫБОР</b>          🤖 <b>ВЫБОР БОТА</b>
{player_hand}                                {bot_hand}
{player_item} <b>{player_name}</b>                {bot_item} <b>{bot_name}</b>

⏳ <i>Определяем победителя...</i>"""

        bot.edit_message_text(
            display,
            game_data['chat_id'],
            game_data['message_id'],
            parse_mode='HTML'
        )

        # Ждем 2 секунды для драматизма
        time.sleep(2)

        # Показываем финальный результат
        show_rps_final_result(bot, user_id, player_choice, bot_choice, result, bet_amount)

    except Exception as e:
        logging.error(f"Ошибка анимации КНБ: {e}")

def show_rps_final_result(bot, user_id, player_choice, bot_choice, result, bet_amount):
    """Показывает финальный результат"""
    try:
        if user_id not in active_rps_games:
            return

        game_data = active_rps_games[user_id]
        users_data = load_users_data()

        player_hand = get_hand_animation_frames(player_choice)[-1]
        bot_hand = get_hand_animation_frames(bot_choice)[-1]
        player_item = get_choice_emoji(player_choice)
        bot_item = get_choice_emoji(bot_choice)
        player_name = get_choice_name(player_choice)
        bot_name = get_choice_name(bot_choice)

        display = f"""<b>🎮 КАМЕНЬ-НОЖНИЦЫ-БУМАГА - РЕЗУЛЬТАТ</b>

<blockquote>💰 Ставка: ${bet_amount}</blockquote>

<b>ИТОГ РАУНДА:</b>

👤 <b>ВАШ ВЫБОР</b>          🤖 <b>ВЫБОР БОТА</b>
{player_hand}                                {bot_hand}
{player_item} <b>{player_name}</b>                {bot_item} <b>{bot_name}</b>

"""

        win_amount = 0
        result_emoji = ""
        result_text = ""

        if result == "player":
            # Победа игрока
            win_amount = round(bet_amount * 2, 2)
            users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0) + win_amount, 2)
            result_emoji = "🎉"
            result_text = f"<b>✅ ВЫ ПОБЕДИЛИ!</b>"
            display += f"\n{result_emoji} {result_text}\n\n<blockquote>💰 Ставка: ${bet_amount}\n🏆 Выигрыш: ${win_amount}\n💵 Прибыль: ${win_amount - bet_amount:.2f}</blockquote>"

        elif result == "bot":
            # Победа бота
            win_amount = 0
            result_emoji = "❌"
            result_text = f"<b>❌ ВЫ ПРОИГРАЛИ!</b>"
            display += f"\n{result_emoji} {result_text}\n\n<blockquote>💰 Ставка: ${bet_amount}\n💸 Потеряно: ${bet_amount}</blockquote>"

        else:
            # Ничья
            win_amount = bet_amount
            users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0) + win_amount, 2)
            result_emoji = "🤝"
            result_text = f"<b>🤝 НИЧЬЯ!</b>"
            display += f"\n{result_emoji} {result_text}\n\n<blockquote>💰 Ставка: ${bet_amount}\n↩️ Возврат: ${bet_amount}</blockquote>"

        # Показываем текущий баланс
        current_balance = users_data[user_id].get('balance', 0)
        display += f"\n💎 <b>Текущий баланс:</b> ${current_balance:.2f}"

        save_users_data(users_data)

        # Клавиатура после игры
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔄 ИГРАТЬ СНОВА", callback_data="rps_play_again"),
            types.InlineKeyboardButton("🎮 ДРУГИЕ ИГРЫ", callback_data="rps_other_games")
        )

        bot.edit_message_text(
            display,
            game_data['chat_id'],
            game_data['message_id'],
            parse_mode='HTML',
            reply_markup=markup
        )

        # Удаляем игру из активных
        if user_id in active_rps_games:
            del active_rps_games[user_id]

    except Exception as e:
        logging.error(f"Ошибка показа результата КНБ: {e}")

def register_rps_handlers(bot):
    """Регистрация обработчиков для игры в КНБ"""

    def process_custom_bet_rps(message):
        """Обработка ручного ввода ставки для КНБ"""
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
            play_rps_game(bot, types.CallbackQuery(message=message, data=f"rps_start_{bet_amount}", from_user=message.from_user, id=""), bet_amount, user_id)

        except ValueError:
            bot.send_message(message.chat.id, "❌ Введите корректную сумму!")
        except Exception as e:
            logging.error(f"Ошибка в process_custom_bet_rps: {e}")
            bot.send_message(message.chat.id, "❌ Произошла ошибка!")

    @bot.message_handler(func=lambda message: message.text == "🎮 КНБ")
    def rps_start(message):
        """Начало игры в КНБ"""
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
                f"""<b>🎮 КАМЕНЬ-НОЖНИЦЫ-БУМАГА</b>

<blockquote>💎 Баланс: ${balance_rounded}</blockquote>

<b>Выберите сумму ставки:</b>""",
                reply_markup=get_rps_bet_selection_keyboard(),
                parse_mode='HTML'
            )
        except Exception as e:
            logging.error(f"Ошибка в rps_start: {e}")
            bot.send_message(message.chat.id, "❌ Ошибка запуска игры")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('rps_'))
    def rps_callback_handler(call):
        """Обработчик колбэков КНБ"""
        try:
            user_id = str(call.from_user.id)

            # Проверяем задержку
            if not rate_limit(user_id):
                bot.answer_callback_query(call.id, "⏳ Не так быстро!", show_alert=False)
                return

            if call.data.startswith("rps_bet_"):
                bet_amount = float(call.data.split("_")[2])
                users_data = load_users_data()

                balance = users_data[user_id].get('balance', 0)
                if bet_amount > balance:
                    bot.answer_callback_query(call.id, "❌ Недостаточно средств!")
                    return

                # Сразу запускаем игру (без кнопки "Начать игру")
                play_rps_game(bot, call, bet_amount, user_id)

            elif call.data == "rps_custom_bet":
                bot.send_message(call.message.chat.id, "📝 Введите сумму ставки:")
                bot.register_next_step_handler(call.message, process_custom_bet_rps)

            elif call.data == "rps_rules":
                bot.edit_message_text(
                    get_rps_rules(),
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🎮 ВЫБРАТЬ СТАВКУ", callback_data="rps_back_to_bet")
                    )
                )

            elif call.data == "rps_back_to_bet":
                users_data = load_users_data()
                balance = users_data[user_id].get('balance', 0)
                balance_rounded = round(balance, 2)

                bot.edit_message_text(
                    f"""<b>🎮 КАМЕНЬ-НОЖНИЦЫ-БУМАГА</b>

<blockquote>💎 Баланс: ${balance_rounded}</blockquote>

<b>Выберите сумму ставки:</b>""",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=get_rps_bet_selection_keyboard(),
                    parse_mode='HTML'
                )

            elif call.data.startswith("rps_choice_"):
                choice = call.data.split("_")[2]  # rock, scissors, paper
                process_rps_choice(bot, call, choice, user_id)

            elif call.data == "rps_play_again":
                # Очищаем предыдущую игру
                if user_id in active_rps_games:
                    del active_rps_games[user_id]

                users_data = load_users_data()
                balance = users_data[user_id].get('balance', 0)
                balance_rounded = round(balance, 2)

                bot.edit_message_text(
                    f"""<b>🎮 КАМЕНЬ-НОЖНИЦЫ-БУМАГА</b>

<blockquote>💎 Баланс: ${balance_rounded}</blockquote>

<b>Выберите сумму ставки:</b>""",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=get_rps_bet_selection_keyboard(),
                    parse_mode='HTML'
                )

            elif call.data == "rps_other_games":
                # Возврат к основным играм
                if user_id in active_rps_games:
                    del active_rps_games[user_id]

                bot.edit_message_text(
                    "🎮 <b>Выберите игру:</b>",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML'
                )

        except Exception as e:
            logging.error(f"Ошибка в rps_callback_handler: {e}")
            try:
                bot.answer_callback_query(call.id, "❌ Ошибка в игре")
            except:
                pass