from flask import Flask, render_template, request

app = Flask(__name__)

def calculate_bmi(weight, height):
    """Рассчитывает ИМТ и возвращает кортеж (значение ИМТ, категория)."""
    height_m = height / 100
    bmi = round(weight / (height_m ** 2), 2)
    
    if bmi < 18.5:
        category = "Недостаточная масса тела"
    elif 18.5 <= bmi < 25:
        category = "Нормальная масса тела"
    elif 25 <= bmi < 30:
        category = "Избыточная масса тела"
    else:
        category = "Ожирение"
    
    return bmi, category

@app.route('/', methods=['GET', 'POST'])
def index():
    bmi_result = None
    category_result = None
    play_music = False  # ← НОВОЕ: переменная для включения музыки
    
    if request.method == 'POST':
        try:
            weight = float(request.form.get('weight', 0))
            height = float(request.form.get('height', 0))
            
            if weight > 0 and height > 0:
                bmi_result, category_result = calculate_bmi(weight, height)
                
                # ← НОВОЕ: если избыточный вес или ожирение, включаем музыку
                if category_result in ["Избыточная масса тела", "Ожирение"]:
                    play_music = True
            else:
                bmi_result = "Ошибка"
                category_result = "Введите положительные значения для роста и веса."
        except ValueError:
            bmi_result = "Ошибка"
            category_result = "Пожалуйста, введите числовые значения."
    
    # ← НОВОЕ: передаём play_music в шаблон
    return render_template('index.html',
                          bmi=bmi_result,
                          category=category_result,
                          play_music=play_music)

if __name__ == '__main__':
    app.run(debug=True)
