import json
import time
import sqlite3
from datetime import datetime, timedelta
import logging
from telebot import types

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BotStats:
    def __init__(self, db_path='bot_stats.db'):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """Инициализация базы данных для статистики"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Таблица общей статистики
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_users INTEGER DEFAULT 0,
                    total_games INTEGER DEFAULT 0,
                    total_bets REAL DEFAULT 0,
                    total_wins REAL DEFAULT 0,
                    project_start_date TEXT,
                    last_update TEXT
                )
            ''')
            
            # Таблица ежедневной статистики
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE,
                    new_users INTEGER DEFAULT 0,
                    games_played INTEGER DEFAULT 0,
                    bets_amount REAL DEFAULT 0,
                    wins_amount REAL DEFAULT 0
                )
            ''')
            
            # Инициализируем общую статистику если её нет
            cursor.execute('SELECT COUNT(*) FROM bot_stats')
            if cursor.fetchone()[0] == 0:
                cursor.execute('''
                    INSERT INTO bot_stats (project_start_date, last_update) 
                    VALUES (?, ?)
                ''', (datetime.now().isoformat(), datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            logging.info("База данных статистики инициализирована")
            
        except Exception as e:
            logging.error(f"Ошибка инициализации БД: {e}")

    def load_users_data(self):
        """Загрузка данных пользователей"""
        try:
            with open('users_data.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except Exception as e:
            logging.error(f"Ошибка загрузки users_data: {e}")
            return {}

    def get_project_days(self):
        """Получить количество дней с начала проекта"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT project_start_date FROM bot_stats WHERE id = 1')
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                start_date = datetime.fromisoformat(result[0])
                days = (datetime.now() - start_date).days
                return max(1, days)
            return 1
        except Exception as e:
            logging.error(f"Ошибка получения дней проекта: {e}")
            return 1

    def get_total_users(self):
        """Общее количество пользователей"""
        users_data = self.load_users_data()
        return len(users_data)

    def get_active_users_count(self, days=30):
        """Количество активных пользователей за период"""
        try:
            users_data = self.load_users_data()
            if not users_data:
                return 0
                
            cutoff_date = datetime.now() - timedelta(days=days)
            active_count = 0
            
            for user_id, user_data in users_data.items():
                # Если у пользователя есть баланс или он играл недавно
                if user_data.get('balance', 0) > 0:
                    active_count += 1
                # Можно добавить проверку по последней активности если будет такое поле
                
            return active_count
        except Exception as e:
            logging.error(f"Ошибка получения активных пользователей: {e}")
            return 0

    def get_daily_stats(self):
        """Статистика за сегодня"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT new_users, games_played, bets_amount, wins_amount 
                FROM daily_stats WHERE date = ?
            ''', (today,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'new_users': result[0],
                    'games_played': result[1],
                    'bets_amount': result[2],
                    'wins_amount': result[3]
                }
            else:
                return {
                    'new_users': 0,
                    'games_played': 0,
                    'bets_amount': 0,
                    'wins_amount': 0
                }
                
        except Exception as e:
            logging.error(f"Ошибка получения дневной статистики: {e}")
            return {'new_users': 0, 'games_played': 0, 'bets_amount': 0, 'wins_amount': 0}

    def get_weekly_stats(self):
        """Статистика за последние 7 дней"""
        try:
            week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    SUM(new_users) as new_users,
                    SUM(games_played) as games_played,
                    SUM(bets_amount) as bets_amount,
                    SUM(wins_amount) as wins_amount
                FROM daily_stats 
                WHERE date >= ?
            ''', (week_ago,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] is not None:
                return {
                    'new_users': result[0],
                    'games_played': result[1],
                    'bets_amount': result[2] or 0,
                    'wins_amount': result[3] or 0
                }
            else:
                return {
                    'new_users': 0,
                    'games_played': 0,
                    'bets_amount': 0,
                    'wins_amount': 0
                }
                
        except Exception as e:
            logging.error(f"Ошибка получения недельной статистики: {e}")
            return {'new_users': 0, 'games_played': 0, 'bets_amount': 0, 'wins_amount': 0}

    def get_monthly_stats(self):
        """Статистика за последние 30 дней"""
        try:
            month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    SUM(new_users) as new_users,
                    SUM(games_played) as games_played,
                    SUM(bets_amount) as bets_amount,
                    SUM(wins_amount) as wins_amount
                FROM daily_stats 
                WHERE date >= ?
            ''', (month_ago,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] is not None:
                return {
                    'new_users': result[0],
                    'games_played': result[1],
                    'bets_amount': result[2] or 0,
                    'wins_amount': result[3] or 0
                }
            else:
                return {
                    'new_users': 0,
                    'games_played': 0,
                    'bets_amount': 0,
                    'wins_amount': 0
                }
                
        except Exception as e:
            logging.error(f"Ошибка получения месячной статистики: {e}")
            return {'new_users': 0, 'games_played': 0, 'bets_amount': 0, 'wins_amount': 0}

    def update_daily_stats(self):
        """Обновление ежедневной статистики"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            users_data = self.load_users_data()
            
            # Простая логика для демонстрации
            new_users_today = 0
            # Здесь можно добавить логику подсчета новых пользователей за день
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Обновляем или создаем запись за сегодня
            cursor.execute('''
                INSERT OR REPLACE INTO daily_stats 
                (date, new_users, games_played, bets_amount, wins_amount)
                VALUES (?, ?, ?, ?, ?)
            ''', (today, new_users_today, 0, 0, 0))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Ошибка обновления дневной статистики: {e}")

    def get_stats_message(self):
        """Генерирует сообщение со статистикой"""
        project_days = self.get_project_days()
        total_users = self.get_total_users()
        daily_stats = self.get_daily_stats()
        weekly_stats = self.get_weekly_stats()
        monthly_stats = self.get_monthly_stats()
        
        message = f"""
📊 <b>Статистика бота</b>

📅 <b>Проекту:</b> {project_days} дней
👥 <b>Всего пользователей:</b> {total_users}

<b>📈 За сегодня:</b>
├ 👤 Новые пользователи: {daily_stats['new_users']}
├ 🎮 Игр сыграно: {daily_stats['games_played']}
├ 💰 Сумма ставок: ${daily_stats['bets_amount']:.2f}
└ 🏆 Выигрыши: ${daily_stats['wins_amount']:.2f}

<b>📈 За неделю:</b>
├ 👤 Новые пользователи: {weekly_stats['new_users']}
├ 🎮 Игр сыграно: {weekly_stats['games_played']}
├ 💰 Сумма ставок: ${weekly_stats['bets_amount']:.2f}
└ 🏆 Выигрыши: ${weekly_stats['wins_amount']:.2f}

<b>📈 За месяц:</b>
├ 👤 Новые пользователи: {monthly_stats['new_users']}
├ 🎮 Игр сыграно: {monthly_stats['games_played']}
├ 💰 Сумма ставок: ${monthly_stats['bets_amount']:.2f}
└ 🏆 Выигрыши: ${monthly_stats['wins_amount']:.2f}
        """
        
        return message.strip()

    def get_stats_keyboard(self):
        """Клавиатура для меню статистики"""
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔄 Обновить", callback_data="stats_refresh"),
            types.InlineKeyboardButton("📊 Подробная статистика", callback_data="stats_detailed")
        )
        markup.add(
            types.InlineKeyboardButton("👥 Пользователи", callback_data="stats_users"),
            types.InlineKeyboardButton("🎮 Игры", callback_data="stats_games")
        )
        markup.add(
            types.InlineKeyboardButton("💬 Поддержка", url="https://t.me/username_support")
        )
        return markup

def register_stats_handlers(bot, stats_manager):
    """Регистрация обработчиков для статистики"""
    
    @bot.message_handler(func=lambda message: message.text == "📊 Статистика")
    def stats_command(message):
        """Обработчик команды статистики"""
        try:
            stats_message = stats_manager.get_stats_message()
            keyboard = stats_manager.get_stats_keyboard()
            
            bot.send_message(
                message.chat.id,
                stats_message,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        except Exception as e:
            logging.error(f"Ошибка в stats_command: {e}")
            bot.send_message(message.chat.id, "❌ Ошибка загрузки статистики")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('stats_'))
    def stats_callback_handler(call):
        """Обработчик колбэков статистики"""
        try:
            if call.data == "stats_refresh":
                stats_message = stats_manager.get_stats_message()
                keyboard = stats_manager.get_stats_keyboard()
                
                bot.edit_message_text(
                    stats_message,
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
                bot.answer_callback_query(call.id, "✅ Статистика обновлена")
                
            elif call.data == "stats_detailed":
                # Здесь можно добавить подробную статистику
                bot.answer_callback_query(call.id, "📊 Подробная статистика в разработке")
                
            elif call.data == "stats_users":
                total_users = stats_manager.get_total_users()
                active_monthly = stats_manager.get_active_users_count(30)
                active_weekly = stats_manager.get_active_users_count(7)
                
                users_message = f"""
👥 <b>Статистика пользователей</b>

📊 Всего пользователей: <b>{total_users}</b>
📈 Активных за месяц: <b>{active_monthly}</b>
📈 Активных за неделю: <b>{active_weekly}</b>
📅 Проекту: <b>{stats_manager.get_project_days()}</b> дней
                """
                
                bot.edit_message_text(
                    users_message.strip(),
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=stats_manager.get_stats_keyboard(),
                    parse_mode='HTML'
                )
                
            elif call.data == "stats_games":
                # Здесь можно добавить статистику по играм
                bot.answer_callback_query(call.id, "🎮 Статистика игр в разработке")
                
        except Exception as e:
            logging.error(f"Ошибка в stats_callback_handler: {e}")
            try:
                bot.answer_callback_query(call.id, "❌ Ошибка обновления статистики")
            except:
                pass

# Создаем глобальный экземпляр менеджера статистики
stats_manager = BotStats()