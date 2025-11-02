import telebot
from telebot import types
import random
import json
import time

class TowerGame:
    def __init__(self, user_id, dragons_count, bet_amount):
        self.user_id = user_id
        self.dragons_count = dragons_count
        self.bet_amount = bet_amount
        self.floor = 0
        # Новые множители для 1,2,3,4 драконов
        self.multipliers = {
            1: [1.2, 1.6, 2.3, 4.7],
            2: [1.5, 2.4, 6.0, 24.0],
            3: [1.8, 4.2, 16.0, 120.0],
            4: [2.4, 7.0, 42.0, 400.0],
            5: [3.2, 12.5, 90.0, 1600.0],
            6: [3.9, 20.0, 160.0, 3000.0],
            7: [4.7, 37.0, 270.0, 7500.0],
            8: [5.8, 55.0, 450.0, 15000.0],
            9: [7.0, 90.0, 850.0, 45000.0],
            10: [8.9, 160.0, 1500.0, 100000.0]
        }
        self.dragon_floors = {}
        self.selected_cells = {}
        self.generate_dragons()

    def generate_dragons(self):
        # Генерируем драконов для каждого этажа (1-10)
        for floor in range(1, 11):
            # Случайно выбираем cells_count драконов на этом этаже из 5 возможных ячеек
            available_cells = list(range(5))
            random.shuffle(available_cells)
            self.dragon_floors[floor] = available_cells[:self.dragons_count]

    def climb_floor(self, selected_cell):
        self.floor += 1
        current_floor = self.floor

        # Проверяем, есть ли дракон в выбранной ячейке на текущем этаже
        if current_floor in self.dragon_floors and selected_cell in self.dragon_floors[current_floor]:
            return False
        return True

    def add_selected_cell(self, floor, cell):
        if floor not in self.selected_cells:
            self.selected_cells[floor] = []
        if cell not in self.selected_cells[floor]:
            self.selected_cells[floor].append(cell)

    def get_current_multiplier(self):
        if self.floor == 0:
            return 1.0
        # Получаем множитель в зависимости от этажа и количества драконов
        dragon_index = self.dragons_count - 1
        return self.multipliers[self.floor][dragon_index]

    def get_next_multiplier(self):
        if self.floor >= 10:
            dragon_index = self.dragons_count - 1
            return self.multipliers[10][dragon_index]
        dragon_index = self.dragons_count - 1
        return self.multipliers[self.floor + 1][dragon_index]

def load_users_data():
    try:
        with open('users_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users_data(data):
    with open('users_data.json', 'w') as f:
        json.dump(data, f)

active_tower_games = {}
user_temp_data_tower = {}
user_last_click_time_tower = {}

MIN_BET = 0.2
MAX_BET = 1000

def get_bet_selection_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=5)
    bets = ["0.2", "0.5", "1", "3", "5"]
    buttons = [types.InlineKeyboardButton(f"${bet}", callback_data=f"tower_bet_{bet}") for bet in bets]
    markup.row(*buttons)
    markup.row(types.InlineKeyboardButton("📝 Ввести вручную", callback_data="tower_custom_bet"))
    return markup

def get_dragons_selection_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=4)
    dragons_counts = ["1", "2", "3", "4"]
    buttons = [types.InlineKeyboardButton(f"{count}", callback_data=f"tower_dragons_{count}") for count in dragons_counts]
    markup.row(*buttons)
    return markup

def get_tower_keyboard(game, show_all=False, show_current_dragons=False):
    markup = types.InlineKeyboardMarkup(row_width=6)

    # Создаем поле с множителями слева
    for floor_num in range(10, 0, -1):
        row_buttons = []

        # Кнопка множителя слева
        dragon_index = game.dragons_count - 1
        multiplier = game.multipliers[floor_num][dragon_index]
        # Форматируем множитель
        if multiplier < 10:
            mult_text = f"x{multiplier:.2f}"
        elif multiplier < 100:
            mult_text = f"x{multiplier:.1f}"
        else:
            mult_text = f"x{multiplier:.0f}"

        mult_button = types.InlineKeyboardButton(f"{mult_text}", callback_data="tower_ignore")
        row_buttons.append(mult_button)

        # 5 клеток этажа
        for cell in range(5):
            if show_all:
                # Показываем все поле после окончания игры
                if floor_num in game.dragon_floors and cell in game.dragon_floors[floor_num]:
                    emoji = "🐉"  # Дракон
                elif floor_num in game.selected_cells and cell in game.selected_cells[floor_num]:
                    emoji = "💎"  # Выбранная ячейка
                else:
                    emoji = "◾"  # Белый квадрат для всех ячеек
                callback_data = "tower_ignore"

            elif show_current_dragons and floor_num == game.floor:
                # Показываем драконов на текущем этаже после успешного подъема
                if cell in game.dragon_floors.get(floor_num, []):
                    emoji = "🐉"  # Дракон на этом этаже
                elif cell in game.selected_cells.get(floor_num, []):
                    emoji = "💎"  # Выбранная ячейка
                else:
                    emoji = "◾"  # Свободная ячейка
                callback_data = "tower_ignore"

            else:
                # Активная игра - ВСЕ ячейки белые
                if floor_num == game.floor + 1:
                    emoji = "☁️"  # Белый квадрат для следующего этажа
                    callback_data = f"tower_climb_{floor_num}_{cell}"
                elif floor_num <= game.floor:
                    # Пройденные этажи - показываем алмазы и драконы
                    if floor_num in game.dragon_floors and cell in game.dragon_floors[floor_num]:
                        emoji = "🐉"  # Дракон на пройденном этаже
                    elif floor_num in game.selected_cells and cell in game.selected_cells[floor_num]:
                        emoji = "💎"  # Выбранная ячейка на пройденном этаже
                    else:
                        emoji = "◾"  # Белый квадрат для непройденных ячеек
                    callback_data = "tower_ignore"
                else:
                    emoji = "◾"  # Белый квадрат для будущих этажей
                    callback_data = "tower_ignore"

            row_buttons.append(types.InlineKeyboardButton(emoji, callback_data=callback_data))

        markup.row(*row_buttons)

    # Кнопка забрать (во время активной игры и после показа драконов)
    if (not show_all and game.floor > 0) or show_current_dragons:
        current_mult = game.get_current_multiplier()
        markup.row(types.InlineKeyboardButton(
            f"💵 Забрать ${round(game.bet_amount * current_mult, 2)}",
            callback_data="tower_cashout"
        ))

    return markup

def register_tower_handlers(bot):
    @bot.message_handler(func=lambda message: message.text == "🏰 Башня")
    def tower_start(message):
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
            f"🏰 Башня\n\n<blockquote>💎Баланс: ${balance_rounded}\nСумма ставки👇</blockquote>",
            parse_mode='HTML',
            reply_markup=get_bet_selection_keyboard()
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tower_'))
    def tower_callback_handler(call):
        user_id = str(call.from_user.id)
        users_data = load_users_data()

        # Проверка задержки между нажатиями
        current_time = time.time()
        if user_id in user_last_click_time_tower:
            time_diff = current_time - user_last_click_time_tower[user_id]
            if time_diff < 0.4:
                bot.answer_callback_query(call.id, "⏳ Не так быстро!", show_alert=False)
                return

        user_last_click_time_tower[user_id] = current_time

        if call.data.startswith("tower_bet_"):
            bet_amount = float(call.data.split("_")[2])

            balance = users_data[user_id].get('balance', 0)
            if bet_amount > balance:
                bot.answer_callback_query(call.id, "❌ Недостаточно средств!")
                return

            user_temp_data_tower[user_id] = {'bet_amount': bet_amount}

            # ТОЧНО КАК В СКРИНЕ 2 - выбор драконов
            bot.edit_message_text(
                f"🏰 Башня · ${bet_amount}\n\n<blockquote>Выберите количество драконов🐉 на каждом этаже👇:</blockquote>",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=get_dragons_selection_keyboard()
            )
            return

        elif call.data.startswith("tower_dragons_"):
            dragons_count = int(call.data.split("_")[2])

            if user_id not in user_temp_data_tower or 'bet_amount' not in user_temp_data_tower[user_id]:
                bot.answer_callback_query(call.id, "❌ Ошибка данных!")
                return

            bet_amount = user_temp_data_tower[user_id]['bet_amount']

            balance = users_data[user_id].get('balance', 0)
            if bet_amount > balance:
                bot.answer_callback_query(call.id, "❌ Недостаточно средств!")
                return

            game = TowerGame(user_id, dragons_count, bet_amount)
            active_tower_games[user_id] = game

            users_data[user_id]['balance'] = round(balance - bet_amount, 2)
            save_users_data(users_data)

            if user_id in user_temp_data_tower:
                del user_temp_data_tower[user_id]

            # ТОЧНО КАК В СКРИНЕ 3 - начало игры
            bot.edit_message_text(
                f"🏰 Башня · {dragons_count} драконов🐉 на этаж\n\n"
                f"<blockquote>📌Текущий этаж: 0/10\n"
                f"💰Множитель: x1.00\n"
                f"📈Следующий: x1.20</blockquote>",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=get_tower_keyboard(game)
            )
            return

        elif call.data == "tower_custom_bet":
            bot.send_message(call.message.chat.id, "📝 Введите сумму ставки:")
            bot.register_next_step_handler(call.message, process_custom_bet)
            return

        elif call.data.startswith("tower_climb_"):
            if user_id not in active_tower_games:
                bot.answer_callback_query(call.id, "❌ Игра не найдена")
                return

            game = active_tower_games[user_id]

            parts = call.data.split('_')
            floor_num = int(parts[2])
            cell_num = int(parts[3])

            # Добавляем выбранную ячейку
            game.add_selected_cell(floor_num, cell_num)

            # Поднимаемся на этаж и проверяем результат
            success = game.climb_floor(cell_num)

            if not success:
                users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0), 2)
                save_users_data(users_data)

                # ТОЧНО КАК В СКРИНЕ 5 - проигрыш
                bot.edit_message_text(
                    f"🏰 Башня · {game.dragons_count} драконов🐉 на этаж\n\n"
                    f"<blockquote><b>❌Проигрыш</b>\n\n"
                    f"Вы разбудили дракона🐉..\n\n"
                    f"💰Ставка: ${game.bet_amount}\n"
                    f"📌Мог забрать: ${round(game.bet_amount * game.get_current_multiplier(), 2)}\n"
                    f"💎Баланс: ${users_data[user_id]['balance']}</blockquote>",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=get_tower_keyboard(game, show_all=True)
                )
                return
            else:
                # ТОЧНО КАК В СКРИНЕ 4 - успешный подъем
                bot.edit_message_text(
                    f"🏰 Башня · {game.dragons_count} драконов на этаж\n\n"
                    f"<blockquote>📌Текущий этаж: {game.floor}/10\n"
                    f"💰Множитель: x{game.get_current_multiplier():.2f}\n"
                    f"📈Следующий: x{game.get_next_multiplier():.2f}\n\n"
                    f"✅Успешный подъем на этаж {game.floor}!\n"
                    f"🐉Дракон ещё не найден</blockquote>",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=get_tower_keyboard(game, show_current_dragons=True)
                )
                return

        elif call.data == "tower_cashout":
            if user_id not in active_tower_games:
                bot.answer_callback_query(call.id, "❌ Игра не найдена")
                return

            game = active_tower_games[user_id]

            win_amount = game.bet_amount * game.get_current_multiplier()
            users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0) + win_amount, 2)
            save_users_data(users_data)

            # ТОЧНО КАК В СКРИНЕ 6 - победа
            bot.edit_message_text(
                f"🏰 Башня · ПОБЕДА🥳\n\n"
                f"<blockquote><b>Победа!🥳</b>\n\n"
                f"Вы не разбудили дракона🐉\n\n"
                f"💰Ставка: ${game.bet_amount}\n"
                f"🍀Выигрыш: ${round(win_amount, 2)}\n"
                f"💎Баланс: ${users_data[user_id]['balance']}</blockquote>",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=get_tower_keyboard(game, show_all=True)
            )
            return

        elif call.data == "tower_again":
            if user_id in active_tower_games:
                del active_tower_games[user_id]
            if user_id in user_temp_data_tower:
                del user_temp_data_tower[user_id]

            balance = users_data[user_id].get('balance', 0)
            balance_rounded = round(balance, 2)

            bot.edit_message_text(
                f"🏰 Башня\n\n<blockquote>💎Баланс: ${balance_rounded}\nСумма ставки👇</blockquote>",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=get_bet_selection_keyboard()
            )
            return

        elif call.data == "tower_ignore":
            bot.answer_callback_query(call.id)
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
            if bet_amount > balance:
                bot.send_message(message.chat.id, "❌ Недостаточно средств!")
                return

            user_temp_data_tower[user_id] = {'bet_amount': bet_amount}

            bot.send_message(
                message.chat.id,
                f"🏰 Башня · ${bet_amount}\n\n<blockquote>Выберите количество драконов🐉 на каждом этаже👇:</blockquote>",
                parse_mode='HTML',
                reply_markup=get_dragons_selection_keyboard()
            )
        except ValueError:
            bot.send_message(message.chat.id, "❌ Введите корректную сумму!")

    register_tower_handlers.process_custom_bet = process_custom_bet