import telebot
from telebot import types
import json
import re

# Функции для работы с данными пользователей (такие же как в main.py)
def load_users_data():
    try:
        with open('users_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users_data(data):
    with open('users_data.json', 'w') as f:
        json.dump(data, f)

# Список администраторов (добавьте сюда ID администраторов)
ADMIN_IDS = [8118184388,8118184388]  # Замените на реальные ID администраторов

def register_admin_handlers(bot):

    # Проверка прав администратора
    def is_admin(user_id):
        return user_id in ADMIN_IDS

    # Команда /admin
    @bot.message_handler(commands=['admin'])
    def admin_panel(message):
        user_id = message.from_user.id
        if not is_admin(user_id):
            bot.send_message(message.chat.id, "❌ У вас нет прав доступа к админ-панели.")
            return

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("💰 Выдать баланс", callback_data="admin_give_balance"),
            types.InlineKeyboardButton("📊 Статистика пользователя", callback_data="admin_user_stats"),
            types.InlineKeyboardButton("👥 Все пользователи", callback_data="admin_all_users")
        )

        bot.send_message(
            message.chat.id,
            "🛠️ *Админ-панель*\n\n"
            "Выберите действие:",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    # Обработка инлайн-кнопок админ-панели
    @bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
    def handle_admin_buttons(call):
        user_id = call.from_user.id
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ Нет прав доступа!")
            return

        if call.data == "admin_give_balance":
            msg = bot.send_message(
                call.message.chat.id,
                "💰 *Выдача баланса*\n\n"
                "Введите данные в формате:\n"
                "`ID_пользователя или @username сумма`\n\n"
                "*Примеры:*\n"
                "`123456789 100` - выдать 100$ пользователю с ID 123456789\n"
                "`@username 50` - выдать 50$ пользователю @username",
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(msg, process_give_balance)

        elif call.data == "admin_user_stats":
            msg = bot.send_message(
                call.message.chat.id,
                "📊 *Статистика пользователя*\n\n"
                "Введите ID пользователя или @username:",
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(msg, process_user_stats)

        elif call.data == "admin_all_users":
            show_all_users(call.message)

        bot.answer_callback_query(call.id)

    # Обработка выдачи баланса
    def process_give_balance(message):
        try:
            parts = message.text.split()
            if len(parts) < 2:
                bot.send_message(message.chat.id, "❌ Неверный формат. Используйте: `ID сумма` или `@username сумма`", parse_mode="Markdown")
                return

            user_identifier = parts[0]
            amount = float(parts[1])

            users_data = load_users_data()
            user_found = False

            # Поиск пользователя по ID или username
            for uid, user_data in users_data.items():
                if uid == user_identifier or (user_identifier.startswith('@') and user_data.get('username', '').lower() == user_identifier[1:].lower()):
                    # Обновляем баланс
                    current_balance = user_data.get('balance', 0)
                    users_data[uid]['balance'] = current_balance + amount
                    save_users_data(users_data)

                    username = user_data.get('username', 'Неизвестно')
                    bot.send_message(
                        message.chat.id,
                        f"✅ Баланс успешно обновлен!\n\n"
                        f"👤 Пользователь: @{username} (ID: {uid})\n"
                        f"💰 Выдано: {amount}$\n"
                        f"💳 Новый баланс: {users_data[uid]['balance']}$"
                    )

                    # Уведомляем пользователя (если возможно)
                    try:
                        bot.send_message(
                            uid,
                            f"🎉 Вам начислено {amount}$!\n\n"
                            f"💳 Ваш текущий баланс: {users_data[uid]['balance']}$"
                        )
                    except:
                        pass  # Не удалось отправить уведомление пользователю

                    user_found = True
                    break

            if not user_found:
                bot.send_message(message.chat.id, f"❌ Пользователь {user_identifier} не найден.")

        except ValueError:
            bot.send_message(message.chat.id, "❌ Неверная сумма. Введите число.")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

    # Обработка просмотра статистики пользователя
    def process_user_stats(message):
        user_identifier = message.text
        users_data = load_users_data()
        user_found = False

        for uid, user_data in users_data.items():
            if uid == user_identifier or (user_identifier.startswith('@') and user_data.get('username', '').lower() == user_identifier[1:].lower()):
                username = user_data.get('username', 'Неизвестно')
                balance = user_data.get('balance', 0)
                level = user_data.get('level', 1)
                first_seen = user_data.get('first_seen', 'Неизвестно')

                bot.send_message(
                    message.chat.id,
                    f"📊 *Статистика пользователя*\n\n"
                    f"👤 Username: @{username}\n"
                    f"🆔 ID: {uid}\n"
                    f"💰 Баланс: {balance}$\n"
                    f"🏅 Уровень: {level}\n"
                    f"📅 Первый вход: {first_seen}",
                    parse_mode="Markdown"
                )
                user_found = True
                break

        if not user_found:
            bot.send_message(message.chat.id, f"❌ Пользователь {user_identifier} не найден.")

    # Показать всех пользователей
    def show_all_users(message):
        users_data = load_users_data()

        if not users_data:
            bot.send_message(message.chat.id, "❌ Нет зарегистрированных пользователей.")
            return

        total_balance = sum(user_data.get('balance', 0) for user_data in users_data.values())
        total_users = len(users_data)

        stats_text = (
            f"👥 *Общая статистика*\n\n"
            f"📊 Всего пользователей: {total_users}\n"
            f"💰 Общий баланс: {total_balance}$\n\n"
            f"*Последние 10 пользователей:*\n"
        )

        # Берем последних 10 пользователей
        recent_users = list(users_data.items())[-10:]

        for i, (uid, user_data) in enumerate(recent_users, 1):
            username = user_data.get('username', 'Неизвестно')
            balance = user_data.get('balance', 0)
            stats_text += f"{i}. @{username} - {balance}$ (ID: {uid})\n"

        bot.send_message(message.chat.id, stats_text, parse_mode="Markdown")

    # Команда для снятия баланса
    @bot.message_handler(commands=['remove_balance'])
    def remove_balance_command(message):
        user_id = message.from_user.id
        if not is_admin(user_id):
            bot.send_message(message.chat.id, "❌ У вас нет прав доступа.")
            return

        msg = bot.send_message(
            message.chat.id,
            "➖ *Снятие баланса*\n\n"
            "Введите данные в формате:\n"
            "`ID_пользователя или @username сумма`\n\n"
            "*Пример:*\n"
            "`123456789 50` - снять 50$ у пользователя с ID 123456789",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_remove_balance)

    # Обработка снятия баланса
    def process_remove_balance(message):
        try:
            parts = message.text.split()
            if len(parts) < 2:
                bot.send_message(message.chat.id, "❌ Неверный формат. Используйте: `ID сумма` или `@username сумма`", parse_mode="Markdown")
                return

            user_identifier = parts[0]
            amount = float(parts[1])

            users_data = load_users_data()
            user_found = False

            for uid, user_data in users_data.items():
                if uid == user_identifier or (user_identifier.startswith('@') and user_data.get('username', '').lower() == user_identifier[1:].lower()):
                    current_balance = user_data.get('balance', 0)

                    if current_balance < amount:
                        bot.send_message(message.chat.id, f"❌ Недостаточно средств. У пользователя только {current_balance}$")
                        return

                    # Снимаем баланс
                    users_data[uid]['balance'] = current_balance - amount
                    save_users_data(users_data)

                    username = user_data.get('username', 'Неизвестно')
                    bot.send_message(
                        message.chat.id,
                        f"✅ Баланс успешно обновлен!\n\n"
                        f"👤 Пользователь: @{username} (ID: {uid})\n"
                        f"💰 Снято: {amount}$\n"
                        f"💳 Новый баланс: {users_data[uid]['balance']}$"
                    )
                    user_found = True
                    break

            if not user_found:
                bot.send_message(message.chat.id, f"❌ Пользователь {user_identifier} не найден.")

        except ValueError:
            bot.send_message(message.chat.id, "❌ Неверная сумма. Введите число.")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

    # Команда для установки конкретного баланса
    @bot.message_handler(commands=['set_balance'])
    def set_balance_command(message):
        user_id = message.from_user.id
        if not is_admin(user_id):
            bot.send_message(message.chat.id, "❌ У вас нет прав доступа.")
            return

        msg = bot.send_message(
            message.chat.id,
            "⚡ *Установка баланса*\n\n"
            "Введите данные в формате:\n"
            "`ID_пользователя или @username сумма`\n\n"
            "*Пример:*\n"
            "`123456789 200` - установить баланс 200$ пользователю с ID 123456789",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_set_balance)

    # Обработка установки баланса
    def process_set_balance(message):
        try:
            parts = message.text.split()
            if len(parts) < 2:
                bot.send_message(message.chat.id, "❌ Неверный формат. Используйте: `ID сумма` или `@username сумма`", parse_mode="Markdown")
                return

            user_identifier = parts[0]
            amount = float(parts[1])

            users_data = load_users_data()
            user_found = False

            for uid, user_data in users_data.items():
                if uid == user_identifier or (user_identifier.startswith('@') and user_data.get('username', '').lower() == user_identifier[1:].lower()):
                    # Устанавливаем баланс
                    users_data[uid]['balance'] = amount
                    save_users_data(users_data)

                    username = user_data.get('username', 'Неизвестно')
                    bot.send_message(
                        message.chat.id,
                        f"✅ Баланс успешно установлен!\n\n"
                        f"👤 Пользователь: @{username} (ID: {uid})\n"
                        f"💰 Новый баланс: {amount}$"
                    )
                    user_found = True
                    break

            if not user_found:
                bot.send_message(message.chat.id, f"❌ Пользователь {user_identifier} не найден.")

        except ValueError:
            bot.send_message(message.chat.id, "❌ Неверная сумма. Введите число.")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

    print("Админ-команды зарегистрированы!")