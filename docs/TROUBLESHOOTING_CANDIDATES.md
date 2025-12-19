# Инструкция: Как добавить кандидатов в Telegram бот

## Проблема
После команды `/interview` не видно профессиональных кандидатов (Иван Петров, Наталья Смирнова и т.д.)

## Причина
Миграция `20251219_candidates` не применена к базе данных.

## Решение

### Вариант 1: Накатить миграцию (рекомендуется)

```bash
# Шаг 1: Остановить бота (если запущен)
docker-compose stop bot

# Шаг 2: Применить миграцию
python -m alembic upgrade head

# Ожидаемый вывод:
# INFO  [alembic.runtime.migration] Running upgrade 20251215_collection_flow -> 20251219_candidates
# ✅ Added 5 professional candidates to database

# Шаг 3: Перезапустить бота
docker-compose up -d bot
# или локально:
# python -m app.bot.main
```

### Вариант 2: Полный сброс БД с нуля

```bash
# Шаг 1: Удалить все данные
docker-compose down -v

# Шаг 2: Пересоздать БД
docker-compose up -d db

# Шаг 3: Подождать запуска PostgreSQL
sleep 10

# Шаг 4: Накатить ВСЕ миграции (включая кандидатов)
python -m alembic upgrade head

# Шаг 5: Загрузить шаги онбординга
python -m app.scripts.seed_labs

# Шаг 6: Запустить бота
docker-compose up -d bot
```

### Вариант 3: Проверить текущее состояние

```bash
# Проверить текущую версию БД
python -m alembic current

# Если версия НЕ 20251219_candidates, значит нужно накатить:
python -m alembic upgrade head

# Проверить кандидатов в БД напрямую
docker exec -it hr_traine_db psql -U postgres -d hr_traine -c "SELECT name, psychotype FROM candidate_profiles;"
```

## Как работает выбор кандидатов

### Код (interview.py, строки 12-35):

```python
@router.message(F.text == "/interview")
async def cmd_interview(message: types.Message, state: FSMContext):
    # Получаем ВСЕХ кандидатов из БД
    async for session in get_session():
        result = await session.execute(select(CandidateProfile))
        candidates = result.scalars().all()
        
        if not candidates:
            # Если кандидатов нет - создает dummy
            dummy = CandidateProfile(
                name="John Doe", 
                resume_text="Experienced Sales Manager...",
                category="Sales",
                psychotype="Target"
            )
            session.add(dummy)
            await session.commit()
            candidates = [dummy]
        
        # Создает кнопки из имен кандидатов
        buttons = [[types.KeyboardButton(text=c.name)] for c in candidates]
        keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, one_time_keyboard=True)
        
        await message.answer("Choose a candidate to interview:", reply_markup=keyboard)
        await state.set_state(InterviewStates.choosing_candidate)
```

### Что должно быть в Telegram:

После `/interview` появляются кнопки:
```
Choose a candidate to interview:

[Иван Петров]
[Наталья Смирнова]  
[Екатерина Волкова]
[Римма Козлова]
[Дмитрий Соколов]
```

### Если видите только "John Doe":

Это означает, что в БД нет кандидатов → миграция не применена.

## Что добавляет миграция 20251219_candidates

```python
# Из файла alembic/versions/20251219_candidates.py

def upgrade():
    """Добавляет 5 профессиональных кандидатов"""
    
    candidates = [
        {
            'name': 'Иван Петров',
            'psychotype': 'Target',
            'category': 'IT',
            'resume_text': 'Senior Java Developer...'
        },
        {
            'name': 'Наталья Смирнова',
            'psychotype': 'Evasive',
            'category': 'IT',
            'resume_text': 'Frontend Angular Developer...'
        },
        # ... еще 3 кандидата
    ]
    
    for candidate in candidates:
        connection.execute(
            sa.text("""
                INSERT INTO candidate_profiles (name, resume_text, category, psychotype)
                VALUES (:name, :resume_text, :category, :psychotype)
            """),
            candidate
        )
```

## Проверка после применения

```bash
# 1. Проверить версию миграции
python -m alembic current
# Должно быть: 20251219_candidates

# 2. Проверить кандидатов в БД
docker exec -it hr_traine_db psql -U postgres -d hr_traine -c \
"SELECT id, name, psychotype, LENGTH(resume_text) as resume_length FROM candidate_profiles;"

# Ожидаемый результат:
#  id |        name         | psychotype | resume_length 
# ----+---------------------+------------+---------------
#   1 | Иван Петров         | Target     |          1234
#   2 | Наталья Смирнова    | Evasive    |          1156
#   3 | Екатерина Волкова   | Target     |          1312
#   4 | Римма Козлова       | Silent     |          1198
#   5 | Дмитрий Соколов     | Toxic      |          1087

# 3. Перезапустить бота
docker-compose restart bot

# 4. Проверить в Telegram
# /interview → должны появиться 5 кнопок с именами
```

## Важно!

⚠️ Если бот работает в Docker, обязательно **перезапустите контейнер** после применения миграции:
```bash
docker-compose restart bot
```

✅ После этого кандидаты появятся в списке!
