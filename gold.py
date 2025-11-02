import telebot
from telebot import types
import random
import json
import time

class GoldGame:
    def __init__(self, user_id, bet_amount):
        self.user_id = user_id
        self.bet_amount = bet_amount
        self.floor = 0
        # Множители для этапов: каждый этаж умножает на 1.9
        self.multipliers = [1.0, 1.9, 3.61, 6.86, 13.03, 24.76, 47.04, 89.38, 169.82, 322.66, 613.05]
        self.dynamite_positions = {}  # {floor: dynamite_cell}
        self.selected_cells = {}
        self.generate_dynamite()

    def generate_dynamite(self):
        # На каждом этаже 1 мина из 2 ячеек
        for floor in range(1, 11):
            # Случайно выбираем ячейку с динамитом (0 или 1)
            dynamite_cell = random.randint(0, 1)
            self.dynamite_positions[floor] = dynamite_cell

    def climb_floor(self, selected_cell):
        self.floor += 1
        # Проверяем, попали ли на динамит
        if self.floor in self.dynamite_positions and selected_cell == self.dynamite_positions[self.floor]:
            return False
        return True

    def add_selected_cell(self, floor, cell):
        if floor not in self.selected_cells:
            self.selected_cells[floor] = []
        if cell not in self.selected_cells[floor]:
            self.selected_cells[floor].append(cell)

    def get_current_multiplier(self):
        return self.multipliers[self.floor]

    def get_next_multiplier(self):
        if self.floor >= 10:
            return self.multipliers[10]
        return self.multipliers[self.floor + 1]

def load_users_data():
    try:
        with open('users_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users_data(data):
    with open('users_data.json', 'w') as f:
        json.dump(data, f)

active_gold_games = {}
user_temp_data_gold = {}
user_last_click_time_gold = {}

MIN_BET = 0.2
MAX_BET = 1000

def get_bet_selection_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=5)
    bets = ["0.2", "0.5", "1", "3", "5"]
    buttons = [types.InlineKeyboardButton(f"${bet}", callback_data=f"gold_bet_{bet}") for bet in bets]
    markup.row(*buttons)
    markup.row(types.InlineKeyboardButton("📝 Ввести вручную", callback_data="gold_custom_bet"))
    return markup

def get_gold_keyboard(game, show_dynamite=False):
    markup = types.InlineKeyboardMarkup(row_width=3)

    # Создаем поле с множителями слева
    for floor_num in range(10, 0, -1):
        row_buttons = []

        # Кнопка множителя слева (БЕЗ БЕЛЫХ КРУЖКОВ)
        multiplier = game.multipliers[floor_num]
        # Форматируем множитель
        if multiplier < 10:
            mult_text = f"x{multiplier:.2f}"
        elif multiplier < 100:
            mult_text = f"x{multiplier:.1f}"
        else:
            mult_text = f"x{multiplier:.0f}"

        mult_button = types.InlineKeyboardButton(f"{mult_text}", callback_data="gold_ignore")
        row_buttons.append(mult_button)

        # 2 клетки этажа
        for cell in range(2):
            if show_dynamite:
                # Показываем где был динамит
                if floor_num in game.dynamite_positions and cell == game.dynamite_positions[floor_num]:
                    emoji = "🧨"  # Динамит
                elif floor_num in game.selected_cells and cell in game.selected_cells[floor_num]:
                    emoji = "💰"  # Выбранная ячейка
                else:
                    emoji = "◾"  # Пустая ячейка
                callback_data = "gold_ignore"
            elif floor_num == game.floor + 1:
                # Следующий этаж - активные кнопки
                emoji = "◽"
                callback_data = f"gold_climb_{floor_num}_{cell}"
            elif floor_num <= game.floor:
                # Пройденные этажи
                if floor_num in game.selected_cells and cell in game.selected_cells[floor_num]:
                    emoji = "💰"
                else:
                    emoji = "◾"
                callback_data = "gold_ignore"
            else:
                # Будущие этажи
                emoji = "◾"
                callback_data = "gold_ignore"

            row_buttons.append(types.InlineKeyboardButton(emoji, callback_data=callback_data))

        markup.row(*row_buttons)

    # Кнопка забрать
    if game.floor > 0 and not show_dynamite:
        current_mult = game.get_current_multiplier()
        markup.row(types.InlineKeyboardButton(
            f"💵 Забрать ${round(game.bet_amount * current_mult, 2)}",
            callback_data="gold_cashout"
        ))

    return markup

def register_gold_handlers(bot):

    def process_custom_bet_gold(message):
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

            user_temp_data_gold[user_id] = {'bet_amount': bet_amount}

            # Создаем игру
            game = GoldGame(user_id, bet_amount)
            active_gold_games[user_id] = game

            # Списываем ставку
            users_data[user_id]['balance'] = round(balance - bet_amount, 2)
            save_users_data(users_data)

            if user_id in user_temp_data_gold:
                del user_temp_data_gold[user_id]

            # ТОЧНО КАК В СКРИНЕ 2 - ход игры
            bot.send_message(
                message.chat.id,
                f"💰 Золото\n\n<blockquote>📌Текущий этаж: 0/10\n🌿Множитель: x1.00\n📈Следующий: x1.90</blockquote>",
                parse_mode='HTML',
                reply_markup=get_gold_keyboard(game)
            )
        except ValueError:
            bot.send_message(message.chat.id, "❌ Введите корректную сумму!")

    @bot.message_handler(func=lambda message: message.text == "💰 Золото")
    def gold_start(message):
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
            f"💰 Золото\n\n<blockquote>💎Баланс: ${balance_rounded}\nСумма ставки👇</blockquote>",
            parse_mode='HTML',
            reply_markup=get_bet_selection_keyboard()
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith('gold_'))
    def gold_callback_handler(call):
        user_id = str(call.from_user.id)
        users_data = load_users_data()

        # Проверка задержки между нажатиями
        current_time = time.time()
        if user_id in user_last_click_time_gold:
            time_diff = current_time - user_last_click_time_gold[user_id]
            if time_diff < 0.4:
                bot.answer_callback_query(call.id, "⏳ Не так быстро!", show_alert=False)
                return

        user_last_click_time_gold[user_id] = current_time

        if call.data.startswith("gold_bet_"):
            bet_amount = float(call.data.split("_")[2])

            balance = users_data[user_id].get('balance', 0)
            if bet_amount > balance:
                bot.answer_callback_query(call.id, "❌ Недостаточно средств!")
                return

            user_temp_data_gold[user_id] = {'bet_amount': bet_amount}

            # Создаем игру
            game = GoldGame(user_id, bet_amount)
            active_gold_games[user_id] = game

            # Списываем ставку
            users_data[user_id]['balance'] = round(balance - bet_amount, 2)
            save_users_data(users_data)

            if user_id in user_temp_data_gold:
                del user_temp_data_gold[user_id]

            # ТОЧНО КАК В СКРИНЕ 2 - ход игры
            bot.edit_message_text(
                f"💰 Золото\n\n<blockquote>📌Текущий этаж: 0/10\n🌿Множитель: x1.00\n📈Следующий: x1.90</blockquote>",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=get_gold_keyboard(game)
            )
            return

        elif call.data == "gold_custom_bet":
            msg = bot.send_message(call.message.chat.id, "📝 Введите сумму ставки:")
            bot.register_next_step_handler(msg, process_custom_bet_gold)
            return

        elif call.data.startswith("gold_climb_"):
            if user_id not in active_gold_games:
                bot.answer_callback_query(call.id, "❌ Игра не найдена")
                return

            game = active_gold_games[user_id]

            # Получаем номер этажа и ячейки
            parts = call.data.split('_')
            floor_num = int(parts[2])
            cell_num = int(parts[3])

            # Сохраняем выбранную ячейку
            game.add_selected_cell(floor_num, cell_num)

            success = game.climb_floor(cell_num)

            if not success:
                users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0), 2)
                save_users_data(users_data)

                # ТОЧНО КАК В СКРИНЕ 4 - проигрыш
                bot.edit_message_text(
                    f"💰 Золото\n\n"
                    f"<blockquote><b>Проигрыш..❌ Динамит 🧨на {game.floor} этаже!</b>\n\n"
                    f"💰Ставка: ${game.bet_amount}\n"
                    f"📌Мог забрать: ${round(game.bet_amount * game.get_current_multiplier(), 2)}\n"
                    f"💎Баланс: ${users_data[user_id]['balance']}</blockquote>",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=get_gold_keyboard(game, show_dynamite=True)
                )
                # Не удаляем игру сразу, показываем где был динамит
                return
            else:
                if game.floor == 10:
                    win_amount = game.bet_amount * game.get_current_multiplier()
                    users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0) + win_amount, 2)
                    save_users_data(users_data)

                    # ТОЧНО КАК В СКРИНЕ 3 - победа
                    bot.edit_message_text(
                        f"💰 Золото\n\n"
                        f"<blockquote><b>Победа!🥳 Забрали выигрыш!</b>\n\n"
                        f"💰Ставка: ${game.bet_amount}\n"
                        f"🍀Выигрыш: ${round(win_amount, 2)}\n"
                        f"💎Баланс: ${users_data[user_id]['balance']}</blockquote>",
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode='HTML',
                        reply_markup=get_gold_keyboard(game, show_dynamite=True)
                    )
                else:
                    # ТОЧНО КАК В СКРИНЕ 2 - ход игры
                    bot.edit_message_text(
                        f"💰 Золото\n\n"
                        f"<blockquote>📌Текущий этаж: {game.floor}/10\n"
                        f"🌿Множитель: x{game.get_current_multiplier():.2f}\n"
                        f"📈Следующий: x{game.get_next_multiplier():.2f}</blockquote>",
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode='HTML',
                        reply_markup=get_gold_keyboard(game)
                    )
                return

        elif call.data == "gold_cashout":
            if user_id not in active_gold_games:
                bot.answer_callback_query(call.id, "❌ Игра не найдена")
                return

            game = active_gold_games[user_id]

            win_amount = game.bet_amount * game.get_current_multiplier()
            users_data[user_id]['balance'] = round(users_data[user_id].get('balance', 0) + win_amount, 2)
            save_users_data(users_data)

            # ТОЧНО КАК В СКРИНЕ 3 - победа
            bot.edit_message_text(
                f"💰 Золото\n\n"
                f"<blockquote><b>Победа!🥳 Забрали выигрыш!</b>\n\n"
                f"💰Ставка: ${game.bet_amount}\n"
                f"🍀Выигрыш: ${round(win_amount, 2)}\n"
                f"💎Баланс: ${users_data[user_id]['balance']}</blockquote>",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=get_gold_keyboard(game, show_dynamite=True)
            )
            return

        elif call.data == "gold_again":
            if user_id in active_gold_games:
                del active_gold_games[user_id]
            if user_id in user_temp_data_gold:
                del user_temp_data_gold[user_id]

            balance = users_data[user_id].get('balance', 0)
            balance_rounded = round(balance, 2)

            bot.edit_message_text(
                f"💰 Золото\n\n<blockquote>💎Баланс: ${balance_rounded}\nСумма ставки👇</blockquote>",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=get_bet_selection_keyboard()
            )
            return

        elif call.data == "gold_ignore":
            bot.answer_callback_query(call.id)
            return