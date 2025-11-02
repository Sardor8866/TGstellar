from telebot import types
import json

def load_users_data():
    try:
        with open('users_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def register_leaders_handlers(bot):
    # Клавиатура с кнопками переключения
    def leaders_keyboard(selected: str = 'deposit'):
        buttons = [
            types.InlineKeyboardButton("📥 Депозит", callback_data="leader_deposit"),
            types.InlineKeyboardButton("💱 Оборот", callback_data="leader_turnover"),
            types.InlineKeyboardButton("🥳 Выигрыши", callback_data="leader_wins"),
        ]
        keyboard = types.InlineKeyboardMarkup(row_width=3)
        for btn in buttons:
            if btn.callback_data == f"leader_{selected}":
                btn.text = "✅ " + btn.text
            keyboard.add(btn)
        return keyboard

    def format_leaderboard(users_data, key):
        sorted_leaders = sorted(
            users_data.items(),
            key=lambda item: item[1].get(key, 0),
            reverse=True
        )[:10]

        if not sorted_leaders:
            return "Данные отсутствуют."

        titles = {
            'deposit': "🏆Топ 10 по депозиту📥",
            'turnover': "🏆Топ 10 по обороту💱",
            'wins': "🏆Топ 10 по выигрышам🥳"
        }

        text = f"{titles.get(key, '')}:\n\n"
        for i, (user_id, data) in enumerate(sorted_leaders, 1):
            username = data.get('username') or f"User {user_id}"
            value = data.get(key, 0)
            text += f"{i}. @{username} — {value}\n"

        return text

    @bot.message_handler(func=lambda m: m.text == "🏆 Лидерство")
    def show_leaders(message):
        users_data = load_users_data()
        text = format_leaderboard(users_data, 'deposit')
        bot.send_message(message.chat.id, text, reply_markup=leaders_keyboard('deposit'))

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("leader_"))
    def callback_leaders(call):
        users_data = load_users_data()
        key = call.data.replace("leader_", "")
        text = format_leaderboard(users_data, key)
        bot.edit_message_text(chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              text=text,
                              reply_markup=leaders_keyboard(key))
        bot.answer_callback_query(call.id)
