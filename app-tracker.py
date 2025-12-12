from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime, timedelta
import sqlite3
import json
import csv
import io
import os

app = Flask(__name__)

# ═══════════════════════════════════════════════════════════════
# ИНИЦИАЛИЗАЦИЯ БД
# ═══════════════════════════════════════════════════════════════

DATABASE = 'health_tracker.db'

def init_db():
    """Инициализирует БД с таблицами"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Таблица с записями веса
    c.execute('''
        CREATE TABLE IF NOT EXISTS weight_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            weight REAL NOT NULL,
            height REAL,
            bmi REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица с целями
    c.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_weight REAL NOT NULL,
            target_date TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица с заметками
    c.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Инициализируем БД при запуске
if not os.path.exists(DATABASE):
    init_db()

# ═══════════════════════════════════════════════════════════════
# ФУНКЦИИ РАСЧЁТОВ
# ═══════════════════════════════════════════════════════════════

def calculate_bmi(weight, height):
    """Расчёт ИМТ"""
    if height <= 0:
        return None
    height_m = height / 100
    bmi = round(weight / (height_m ** 2), 2)
    return bmi

def get_bmi_category(bmi):
    """Получить категорию ИМТ"""
    if bmi < 18.5:
        return "Недостаточная масса", "underweight", "#1976d2"
    elif 18.5 <= bmi < 25:
        return "Нормальная масса", "normal", "#388e3c"
    elif 25 <= bmi < 30:
        return "Избыточная масса", "overweight", "#f57c00"
    else:
        return "Ожирение", "obesity", "#c62828"

def get_recommendations(bmi_category, weight, height):
    """Получить рекомендации по питанию"""
    recommendations = {
        "underweight": {
            "title": "Недостаточная масса тела",
            "tips": [
                "🥛 Увеличь потребление калорийных продуктов",
                "🥜 Добавь больше белков в рацион (мясо, яйца, орехи)",
                "🍌 Ешь здоровые перекусы между основными приёмами пищи",
                "💪 Займись силовыми тренировками для набора мышечной массы",
                "🥛 Пей молочные напитки, каши с молоком"
            ]
        },
        "normal": {
            "title": "Нормальная масса тела",
            "tips": [
                "✅ Отлично! Ты в хорошей форме!",
                "🏃 Продолжай регулярные тренировки",
                "🥗 Соблюдай сбалансированную диету",
                "💧 Пей достаточно воды (8 стаканов в день)",
                "😴 Спи 7-8 часов в сутки"
            ]
        },
        "overweight": {
            "title": "Избыточная масса тела",
            "tips": [
                "🥗 Сократи количество углеводов",
                "🚶 Увеличь физическую активность (30 мин в день)",
                "💧 Пей больше воды вместо сладких напитков",
                "🥗 Ешь больше овощей и фруктов",
                "⏱️ Установи режим питания: 3 основных приёма + 2 перекуса"
            ]
        },
        "obesity": {
            "title": "Ожирение",
            "tips": [
                "👨‍⚕️ Обратись к врачу или диетологу",
                "📋 Создай план питания с помощью специалиста",
                "🏃 Начни с лёгких упражнений (пешие прогулки)",
                "🥗 Исключи быстрые углеводы и жирную пищу",
                "📊 Отслеживай прогресс еженедельно"
            ]
        }
    }
    return recommendations.get(bmi_category, {})

# ═══════════════════════════════════════════════════════════════
# ОСНОВНЫЕ МАРШРУТЫ
# ═══════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """Главная страница"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Получи последнюю запись
    c.execute('SELECT * FROM weight_records ORDER BY date DESC LIMIT 1')
    last_record = c.fetchone()
    
    # Получи статистику
    c.execute('SELECT COUNT(*) FROM weight_records')
    total_records = c.fetchone()[0]
    
    # Получи цель
    c.execute('SELECT * FROM goals WHERE id = 1 LIMIT 1')
    goal = c.fetchone()
    
    conn.close()
    
    last_bmi = None
    last_category = None
    progress = None
    
    if last_record:
        weight = last_record[2]
        height = last_record[3]
        last_bmi = last_record[4]
        if last_bmi:
            category, cat_key, color = get_bmi_category(last_bmi)
            last_category = category
        
        if goal:
            target_weight = goal[1]
            current_weight = weight
            progress = round(((current_weight - target_weight) / abs(current_weight - target_weight)) * 100) if current_weight != target_weight else 0
    
    return render_template('index.html',
                         last_record=last_record,
                         last_bmi=last_bmi,
                         last_category=last_category,
                         total_records=total_records,
                         goal=goal,
                         progress=progress)

@app.route('/api/add-weight', methods=['POST'])
def add_weight():
    """Добавить запись о весе"""
    data = request.json
    weight = data.get('weight')
    height = data.get('height')
    date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    if not weight or weight <= 0:
        return jsonify({'error': 'Введи положительное значение веса'}), 400
    
    height = height or 170  # Значение по умолчанию
    
    bmi = calculate_bmi(weight, height)
    
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Вставь или обнови запись
        c.execute('''
            INSERT OR REPLACE INTO weight_records (date, weight, height, bmi)
            VALUES (?, ?, ?, ?)
        ''', (date, weight, height, bmi))
        
        conn.commit()
        conn.close()
        
        category, cat_key, color = get_bmi_category(bmi)
        
        return jsonify({
            'success': True,
            'bmi': bmi,
            'category': category,
            'color': color
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history')
def get_history():
    """Получить историю записей"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    c.execute('SELECT date, weight, height, bmi FROM weight_records ORDER BY date DESC LIMIT 30')
    records = c.fetchall()
    conn.close()
    
    data = [{
        'date': r[0],
        'weight': r[1],
        'height': r[2],
        'bmi': r[3]
    } for r in records]
    
    return jsonify(data)

@app.route('/api/chart-data')
def get_chart_data():
    """Получить данные для графика"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    c.execute('SELECT date, weight FROM weight_records ORDER BY date ASC LIMIT 30')
    records = c.fetchall()
    conn.close()
    
    return jsonify({
        'labels': [r[0] for r in records],
        'weights': [r[1] for r in records]
    })

@app.route('/api/set-goal', methods=['POST'])
def set_goal():
    """Установить цель по весу"""
    data = request.json
    target_weight = data.get('target_weight')
    target_date = data.get('target_date')
    
    if not target_weight or target_weight <= 0:
        return jsonify({'error': 'Введи положительное значение'}), 400
    
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        c.execute('''
            INSERT OR REPLACE INTO goals (id, target_weight, target_date)
            VALUES (1, ?, ?)
        ''', (target_weight, target_date))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export-csv')
def export_csv():
    """Экспортировать данные в CSV"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    c.execute('SELECT date, weight, height, bmi FROM weight_records ORDER BY date ASC')
    records = c.fetchall()
    conn.close()
    
    # Создай CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Дата', 'Вес (кг)', 'Рост (см)', 'ИМТ'])
    
    for record in records:
        writer.writerow(record)
    
    # Отправь файл
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'health_tracker_{datetime.now().strftime("%Y-%m-%d")}.csv'
    )

@app.route('/statistics')
def statistics():
    """Страница со статистикой"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Получи статистику
    c.execute('SELECT COUNT(*) FROM weight_records')
    total = c.fetchone()[0]
    
    c.execute('SELECT MIN(weight), MAX(weight) FROM weight_records')
    min_weight, max_weight = c.fetchone()
    
    c.execute('SELECT weight FROM weight_records ORDER BY date DESC LIMIT 1')
    current = c.fetchone()
    current_weight = current[0] if current else None
    
    c.execute('SELECT weight FROM weight_records ORDER BY date ASC LIMIT 1')
    first = c.fetchone()
    first_weight = first[0] if first else None
    
    conn.close()
    
    weight_change = None
    if current_weight and first_weight:
        weight_change = round(current_weight - first_weight, 2)
    
    return render_template('statistics.html',
                         total_records=total,
                         min_weight=min_weight,
                         max_weight=max_weight,
                         current_weight=current_weight,
                         weight_change=weight_change)

if __name__ == '__main__':
    app.run(debug=True)
