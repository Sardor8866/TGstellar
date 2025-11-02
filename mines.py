import telebot
from telebot import types
import random
import json
import time

class MinesGame:
    def __init__(self, user_id, mines_count, bet_amount):
        self.user_id = user_id
        self.mines_count = mines_count
        self.bet_amount = bet_amount
        self.grid_size = 5
        self.grid = [[0 for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        self.revealed = [[False for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        self.mines_positions = []
        self.multiplier = 1.0
        self.previous_multiplier = 1.0
        self.opened_cells = 0
        self.last_click_time = 0
        self.place_mines()

    def place_mines(self):
        positions = [(i, j) for i in range(self.grid_size) for j in range(self.grid_size)]
        self.mines_positions = random.sample(positions, self.mines_count)

    def get_multiplier_for_opened_cells(self, opened_safe_cells):
        # Множители для каждого количества мин (количество безопасных ячеек = 25 - mines_count)
        multipliers = {
            2: [1.10, 1.22, 1.36, 1.52, 1.71, 1.93, 2.19, 2.50, 2.87, 3.32, 3.87, 4.55, 5.39, 6.45, 7.80, 9.55, 11.85, 14.95, 19.25, 25.25, 33.75, 55.75, 83.25],
            3: [1.15, 1.33, 1.55, 1.82, 2.15, 2.56, 3.07, 3.72, 4.55, 5.62, 7.02, 8.87, 11.35, 14.70, 25.30, 36.70, 49.80, 79.10, 99.80, 137.50, 195.00, 415.00],
            4: [1.20, 1.44, 1.73, 2.07, 2.49, 3.00, 3.62, 4.38, 5.32, 6.50, 7.98, 9.85, 14.20, 19.20, 27.10, 35.20, 43.80, 59.50, 85.20, 235.80, 678.80],
            5: [1.25, 1.56, 1.95, 2.44, 3.05, 3.81, 4.77, 5.98, 7.50, 9.42, 11.85, 19.95, 28.90, 39.95, 55.40, 79.70, 123.40, 163.20, 281.10, 1004.00],
            6: [1.30, 1.69, 2.20, 3.86, 5.71, 8.83, 11.28, 16.17, 27.62, 46.81, 78.95, 135.34, 230.34, 339.44, 551.27, 966.65, 2386.65, 5112.64, 10046.43],
            7: [1.35, 1.82, 2.46, 3.82, 5.48, 8.05, 15.16, 26.02, 67.88, 120.08, 227.11, 536.60, 1049.41, 3366.70, 7090.05, 15121.57, 26004.12, 40021.56],
            8: [1.40, 2.16, 3.34, 4.84, 7.38, 12.53, 25.54, 74.76, 200.66, 528.93, 1740.50, 5756.70, 17979.38, 39911.13, 135655.58, 245617.82, 589204.94],
            9: [1.45, 2.90, 4.05, 7.42, 13.41, 23.29, 45.47, 145.53, 298.32, 741.06, 1959.54, 4786.33, 10125.18, 36181.51, 56263.19, 145381.62],
            10: [1.60, 3.10, 5.38, 8.06, 18.59, 38.39, 89.08, 295.62, 738.43, 2557.65, 9886.47, 29129.71, 75194.56, 126291.84, 353837.76],
            11: [1.80, 4.20, 7.10, 19.55, 60.49, 345.78, 1526.84, 5642.95, 12768.72, 45109.95, 156175.92, 287931.47, 478750.35, 778420.56],
            12: [1.85, 4.39, 8.91, 26.35, 84.20, 424.14, 2341.03, 9769.76, 21118.59, 86201.60, 256342.72, 647582.62, 2467990.46],
            13: [1.90, 5.24, 10.83, 35.50, 125.90, 834.02, 5661.23, 21110.22, 67198.39, 249357.10, 797642.78, 2671157.00],
            14: [2.10, 6.61, 15.86, 53.03, 284.76, 1447.04, 23889.38, 118769.82, 354622.66, 975613.05, 2771164.80],
            15: [2.30, 7.00, 23.00, 75.00, 432.00, 2634.00, 55128.00, 274256.00, 536512.00, 1000024.00],
            16: [2.70, 8.41, 31.26, 125.45, 340.84, 2685.77, 18860.12, 36378.25, 246794.33],
            17: [3.30, 13.84, 56.65, 230.43, 501.54, 1138.39, 12496.46, 146548.81],
            18: [3.70, 18.29, 77.17, 270.98, 1640.36, 14800.03, 35340.47],
            19: [4.70, 23.76, 136.82, 433.18, 2579.63, 19861.11],
            20: [6.50, 36.25, 215.63, 1239.06, 9787.66],
            21: [7.60, 45.76, 1317.58, 4500.70],
            22: [8.70, 177.29, 1999.68],
            23: [10.80, 287.84],
            24: [25.90]
        }

        if self.mines_count in multipliers:
            multipliers_list = multipliers[self.mines_count]
            if opened_safe_cells <= len(multipliers_list):
                return multipliers_list[opened_safe_cells - 1]
            else:
                return multipliers_list[-1]
        return 1.0

    def reveal_cell(self, x, y):
        if not (0 <= x < self.grid_size and 0 <= y < self.grid_size):
            return False

        if self.revealed[x][y]:
            return True

        self.revealed[x][y] = True

        self.previous_multiplier = self.multiplier

        if (x, y) in self.mines_positions:
            return False

        self.opened_cells += 1
        self.multiplier = self.get_multiplier_for_opened_cells(self.opened_cells)

        return True

    def get_next_multiplier(self):
        next_opened = self.opened_cells + 1
        return self.get_multiplier_for_opened_cells(next_opened)

def load_users_data():
    try:
        with open('users_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users_data(data):
    with open('users_data.json', 'w') as f:
        json.dump(data, f)

active_games = {}
user_temp_data = {}
user_last_click_time = {}

MIN_BET = 0.2
MAX_BET = 1000

def get_bet_selection_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=5)
    bets = ["0.2", "0.5", "1", "3", "5"]
    buttons = [types.InlineKeyboardButton(f"${bet}", callback_data=f"mine_bet_{bet}") for bet in bets]
    markup.row(*buttons)
    markup.row(types.InlineKeyboardButton("📝 Ввести вручную", callback_data="mine_custom_bet"))
    return markup

def get_mines_selection_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=5)
    mines_counts = ["3", "5", "10", "15", "18"]
    buttons = [types.InlineKeyboardButton(f"{count}", callback_data=f"mine_count_{count}") for count in mines_counts]
    markup.row(*buttons)
    markup.row(types.InlineKeyboardButton("📝 Ввести вручную", callback_data="mine_custom_count"))
    return markup

def get_game_keyboard(game, game_over=False):
    markup = types.InlineKeyboardMarkup(row_width=5)

    buttons = []
    for i in range(game.grid_size):
        row_buttons = []
        for j in range(game.grid_size):
            if game_over:
                if (i, j) in game.mines_positions:
                    if game.revealed[i][j]:
                        emoji = "💥"
                    else:
                        emoji = "💣"
                elif game.revealed[i][j]:
                    emoji = "💎"
                else:
                    emoji = "◾"
                callback_data = "mine_ignore"
            else:
                if game.revealed[i][j]:
                    if (i, j) in game.mines_positions:
                        emoji = "💥"
                    else:
                        emoji = "💎"
                    callback_data = "mine_ignore"
                else:
                    emoji = "◽"
                    callback_data = f"mine_cell_{i}_{j}"

            # БОЛЬШИЕ КНОПКИ с одним эмодзи
            button = types.InlineKeyboardButton(
                emoji,
                callback_data=callback_data
            )
            row_buttons.append(button)
        buttons.append(row_buttons)

    # Уменьшаем количество кнопок в ряду для большего размера
    for row in buttons:
        markup.row(*row)

    if not game_over and game.opened_cells > 0:
        markup.row(types.InlineKeyboardButton(
            f"💵 Забрать ${round(game.bet_amount * game.multiplier, 2)}",
            callback_data="mine_cashout"
        ))

    return markup

def register_mines_handlers(bot):
    @bot.message_handler(func=lambda message: message.text == "💣 Мины")
    def mines_start(message):
        users_data = load_users_data()
        user_id = str(message.from_user.id)

        if user_id not in users_data:
            users_data[user_id] = {'balance': 0}
            save_users_data(users_data)

        balance = users_data[user_id].get('balance', 0)
        balance_rounded = round(balance, 2)

        # ТОЧНО КАК В СКРИНЕ 1 - выбор ставки
        bot.send_message(
            message.chat.id,
            f"💣 Мины\n\n<blockquote>💎Баланс: ${balance_rounded}</blockquote>\nСумма ставки👇",
            parse_mode='HTML',
            reply_markup=get_bet_selection_keyboard()
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith('mine_'))
    def mines_callback_handler(call):
        user_id = str(call.from_user.id)
        users_data = load_users_data()

        # Проверка задержки между нажатиями
        current_time = time.time()
        if user_id in user_last_click_time:
            time_diff = current_time - user_last_click_time[user_id]
            if time_diff < 0.4:
                bot.answer_callback_query(call.id, "⏳ Не так быстро!", show_alert=False)
                return

        user_last_click_time[user_id] = current_time

        if call.data.startswith("mine_bet_"):
            bet_amount = float(call.data.split("_")[2])

            balance = users_data[user_id].get('balance', 0)
            if bet_amount > balance:
                bot.answer_callback_query(call.id, "❌ Недостаточно средств!")
                return

            user_temp_data[user_id] = {'bet_amount': bet_amount}

            # ТОЧНО КАК В СКРИНЕ 4 - выбор количества мин
            bot.edit_message_text(
                f"💣 Мины · ${bet_amount}\n\n<blockquote>Выберите количество мин💣 (2-24):</blockquote>",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=get_mines_selection_keyboard()
            )
            return

        elif call.data.startswith("mine_count_"):
            mines_count = int(call.data.split("_")[2])

            if user_id not in user_temp_data or 'bet_amount' not in user_temp_data[user_id]:
                bot.answer_callback_query(call.id, "❌ Ошибка данных!")
                return

            bet_amount = user_temp_data[user_id]['bet_amount']

            balance = users_data[user_id].get('balance', 0)
            if bet_amount > balance:
                bot.answer_callback_query(call.id, "❌ Недостаточно средств!")
                return

            game = MinesGame(user_id, mines_count, bet_amount)
            active_games[user_id] = game

            users_data[user_id]['balance'] = round(balance - bet_amount, 2)
            save_users_data(users_data)

            if user_id in user_temp_data:
                del user_temp_data[user_id]

            next_mult = game.get_next_multiplier()

            # ТОЧНО КАК В СКРИНЕ 2 - игровое поле
            bot.edit_message_text(
                f"💣 Мины · {mines_count} мин\n\n"
                f"<blockquote>          📊Прошлый: x{game.previous_multiplier:.2f}\n"
                f"          💰Текущий: x{game.multiplier:.2f}\n"
                f"          📈Следующий: x{next_mult:.2f}</blockquote>",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=get_game_keyboard(game)
            )
            return

        elif call.data == "mine_custom_bet":
            bot.send_message(call.message.chat.id, "📝 Введите сумму ставки:")
            bot.register_next_step_handler(call.message, process_custom_bet)
            return

        elif call.data == "mine_custom_count":
            message_text = call.message.text
            if "· $" in message_text:
                bet_amount = float(message_text.split("· $")[1].split("\n")[0])
                user_temp_data[user_id] = {'bet_amount': bet_amount}

            bot.send_message(call.message.chat.id, "📝 Введите количество мин (2-24):")
            bot.register_next_step_handler(call.message, process_custom_mines)
            return

        elif call.data == "mine_again":
            if user_id in active_games:
                del active_games[user_id]
            if user_id in user_temp_data:
                del user_temp_data[user_id]

            balance = users_data[user_id].get('balance', 0)
            balance_rounded = round(balance, 2)

            bot.edit_message_text(
                f"💣 Мины\n\n<blockquote>💎Баланс: ${balance_rounded}</blockquote>\nСумма ставки👇",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=get_bet_selection_keyboard()
            )
            return

        if user_id not in active_games:
            bot.answer_callback_query(call.id, "❌ Игра не найдена")
            return

        game = active_games[user_id]

        if call.data.startswith("mine_cell_"):
            parts = call.data.split("_")
            x, y = int(parts[2]), int(parts[3])

            if game.revealed[x][y]:
                bot.answer_callback_query(call.id, "❌ Уже открыто!")
                return

            success = game.reveal_cell(x, y)

            if not success:
                users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0), 2)
                save_users_data(users_data)

                # ТОЧНО КАК В СКРИНЕ 3 - проигрыш
                bot.edit_message_text(
                    f"💣 Мины · {game.mines_count} мин\n\n"
                    f"💥 Вы попали на мину!\n\n"
                    f"<blockquote>"
                    f"          💰Ставка: ${game.bet_amount}\n"
                    f"         📌Мог забрать: ${round(game.bet_amount * game.multiplier, 2)}\n"
                    f"          💎Баланс: ${users_data[user_id]['balance']}"
                    f"</blockquote>",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=get_game_keyboard(game, game_over=True)
                )
                return
            else:
                next_mult = game.get_next_multiplier()

                bot.edit_message_text(
                    f"💣 Мины · {game.mines_count} мин\n\n"
                    f"<blockquote>          📊Прошлый: x{game.previous_multiplier:.2f}\n"
                    f"          💰Текущий: x{game.multiplier:.2f}\n"
                    f"          📈Следующий: x{next_mult:.2f}</blockquote>",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=get_game_keyboard(game)
                )
                return

        elif call.data == "mine_cashout":
            win_amount = game.bet_amount * game.multiplier
            users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0) + win_amount, 2)
            save_users_data(users_data)

            # ТОЧНО КАК В СКРИНЕ 5 - победа
            bot.edit_message_text(
                f"💣 Мины · {game.mines_count} мин\n\n"
                f"Победа! 🎉\n\n"
                f"<blockquote>"
                f"          💰Ставка: ${game.bet_amount}\n"
                f"         🍀Выигрыш: ${round(win_amount, 2)}\n"
                f"          💎Баланс: ${users_data[user_id]['balance']}"
                f"</blockquote>",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=get_game_keyboard(game, game_over=True)
            )
            return

    def process_custom_bet(message):
        try:
            bet_amount = float(message.text)

            if bet_amount < MIN_BET:
                bot.send_message(message.chat.id, f"❌ Минимальная ставка: ${MIN_BET}")
                return

            if bet_amount > MAX_BET:
                bot.send_message(message.chat.id, f"❌ Максимальная ставка: ${MAX_BET}")
                return

            users_data = load_users_data()
            user_id = str(message.from_user.id)

            balance = users_data[user_id].get('balance', 0)
            balance_rounded = round(balance, 2)
            if bet_amount > balance:
                bot.send_message(message.chat.id, "❌ Недостаточно средств!")
                return

            user_temp_data[user_id] = {'bet_amount': bet_amount}

            bot.send_message(
                message.chat.id,
                f"💣 Мины · ${bet_amount}\n\n<blockquote>Выберите количество мин💣 (2-24):</blockquote>",
                parse_mode='HTML',
                reply_markup=get_mines_selection_keyboard()
            )
        except ValueError:
            bot.send_message(message.chat.id, "❌ Введите корректную сумму!")

    def process_custom_mines(message):
        try:
            mines_count = int(message.text)
            if not 2 <= mines_count <= 24:
                bot.send_message(message.chat.id, "❌ Введите число от 2 до 24!")
                return

            user_id = str(message.from_user.id)
            users_data = load_users_data()

            if user_id not in user_temp_data or 'bet_amount' not in user_temp_data[user_id]:
                bot.send_message(message.chat.id, "❌ Ошибка данных! Начните заново.")
                return

            bet_amount = user_temp_data[user_id]['bet_amount']

            balance = users_data[user_id].get('balance', 0)
            if bet_amount > balance:
                bot.send_message(message.chat.id, "❌ Недостаточно средств!")
                return

            game = MinesGame(user_id, mines_count, bet_amount)
            active_games[user_id] = game

            users_data[user_id]['balance'] = round(balance - bet_amount, 2)
            save_users_data(users_data)

            next_mult = game.get_next_multiplier()

            if user_id in user_temp_data:
                del user_temp_data[user_id]

            bot.send_message(
                message.chat.id,
                f"💣 Мины · {mines_count} мин\n\n"
                f"<blockquote>          📊Прошлый: x{game.previous_multiplier:.2f}\n"
                f"          💰Текущий: x{game.multiplier:.2f}\n"
                f"          📈Следующий: x{next_mult:.2f}</blockquote>",
                parse_mode='HTML',
                reply_markup=get_game_keyboard(game)
            )

        except ValueError:
            bot.send_message(message.chat.id, "❌ Введите корректное число!")

    register_mines_handlers.process_custom_bet = process_custom_bet
    register_mines_handlers.process_custom_mines = process_custom_mines