import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.database.base import get_session
from app.database.models import OnboardingStep, StepType
from sqlalchemy.future import select

CURRICULUM = [
    {
        "order": 1,
        "title": "Вводная встреча с руководителем и наставником",
        "description": "Проведена вводная встреча с руководителем и наставником компании (ссылку на встречу отправят в чате в telegram)",
        "duration": 15,
        "type": StepType.OFFLINE,
        "url": None,
    },
    {
        "order": 2,
        "title": "Изучить бизнес-процесс по подбору персонала",
        "description": "Изучить бизнес-процесс по подбору персонала",
        "duration": 15,
        "type": StepType.CONTENT,
        "url": "https://disk.yandex.ru/i/u34x-7wgFKBAbA",
    },
    {
        "order": 3,
        "title": "Задание: План подбора в карте поиска",
        "description": "В карте поиска во вкладке \"план подбора\" расписать этапы бизнес-процесса по работе с вакансией",
        "duration": 15,
        "type": StepType.TEXT_INPUT,  # Changed from FILE_UPLOAD - users describe their plan, not upload file yet
        "url": None,
        # Для будущей реализации структурированного ввода
        "collection_flow": """{
            "type": "text_parse",
            "prompt": "Распишите этапы работы с вакансией.\\nУкажите для каждого этапа название и план действий.",
            "parse_instruction": "Извлеките JSON: {'этапы': [{'номер': N, 'название': '...', 'план': '...'}]}"
        }""",
        "excel_sheet": "План подбора",
    },
    {
        "order": 4,
        "title": "Изучить бриф и проф стандарт должности",
        "description": "Изучить бриф и проф стандарт должности (бриф предоставляет наставник, проф стандарт должности посмотреть в интернете и отправить ссылку наставнику)",
        "duration": 30,
        "type": StepType.TEXT_INPUT,
        "url": None,
    },
    {
        "order": 5,
        "title": "Изучить видео-инструкцию по работе с картой поиска",
        "description": "Изучить видео-инструкцию по работе с картой поиска (оценочный лист - требования заказчика и индикаторы, и второй лист карты)",
        "duration": 20,
        "type": StepType.CONTENT,
        "url": "https://disk.yandex.ru/i/EgA9341QC0mMKw",
    },
    {
        "order": 6,
        "title": "Задание: Заполнить Оценочный лист в карте поиска",
        "description": "Заполнить в первом листе карты поиска \"Оценочный лист\" разделы soft, hard skill, отсекающие факторы в столбцах требования и искомые индикаторы",
        "duration": 15,
        "type": StepType.TEXT_INPUT,  # Changed from FILE_UPLOAD - users describe their work, not upload file yet
        "url": None,
        "collection_flow": """{
            "type": "sequential_dialogue",
            "sections": [
                {"name": "soft_skills", "prompt": "Перечислите 3-5 soft skills для должности", "follow_up": ["индикаторы", "вопрос"]},
                {"name": "hard_skills", "prompt": "Перечислите 3-5 hard skills", "follow_up": ["индикаторы", "вопрос"]},
                {"name": "отсекающие_факторы", "prompt": "Что ТОЧНО недопустимо у кандидата?"}
            ]
        }""",
        "excel_sheet": "ОЦЕНОЧНЫЙ ЛИСТ",
    },
    {
        "order": 7,
        "title": "Изучить методичку по написанию вакансии",
        "description": "Изучить методичку по написанию вакансии",
        "duration": 30,
        "type": StepType.CONTENT,
        "url": "https://disk.yandex.ru/i/XMaL-V_1IBTBhA",
    },
    {
        "order": 8,
        "title": "Просмотреть видео-инструкцию по написанию вакансии",
        "description": "Просмотреть видео-инструкцию по написанию вакансии",
        "duration": 90,
        "type": StepType.CONTENT,
        "url": "https://disk.yandex.ru/i/bY-sCWIzxEVyAw",
    },
    {
        "order": 9,
        "title": "Задание: Зачем нужен продающий анонс?",
        "description": "Напишите зачем нужен \"продающий\" анонс?",
        "duration": 5,
        "type": StepType.TEXT_INPUT,
        "url": None,
    },
    {
        "order": 10,
        "title": "Задание: Почему некруглые числа?",
        "description": "Напишите почему лучше использовать некруглые числа при описании компании, кол-ва филиалов и т.д.?",
        "duration": 10,
        "type": StepType.TEXT_INPUT,
        "url": None,
    },
    {
        "order": 11,
        "title": "Задание: Формулировки, отталкивающие кандидата",
        "description": "Какие формулировки могут оттолкнуть кандидата откликнуться на вакансию?",
        "duration": 10,
        "type": StepType.TEXT_INPUT,
        "url": None,
    },
    {
        "order": 12,
        "title": "Задание: Заполнить описания вакансии в карте поиска",
        "description": "Заполнить второй лист карты поиска \"Объявления на вакансию\" пункт в столбце \"Описание вакансии для работного сайта\", \"Описание для отправки вакансии через сообщения\", \"Описание для презентации вакансии по телефону\" и согласовать данный текст с наставником.",
        "duration": 40,
        "type": StepType.TEXT_INPUT,  # Changed from FILE_UPLOAD - users describe their work, not upload file yet
        "url": None,
    },
    {
        "order": 13,
        "title": "Встреча с наставником - итоги дня",
        "description": "Проведена встреча с наставником, обсуждены итоги дня (ссылку на встречу отправит наставник в telegram чате)",
        "duration": 30,
        "type": StepType.OFFLINE,
        "url": None,
    },
    # ========================
    # ДЕНЬ 2: Поиск и анализ рынка
    # ========================
    {
        "order": 14,
        "title": "Изучить методичку по каналам поиска",
        "description": "Изучить методичку по каналам поиска",
        "duration": 30,
        "type": StepType.CONTENT,
        "url": "https://disk.yandex.ru/i/Iiae9Uv5A9AG_A",
    },
    {
        "order": 15,
        "title": "Задание: Выбор каналов поиска для вакансии",
        "description": "Напишите какие каналы поиска подходят для вашей вакансии и аргументируйте свой выбор",
        "duration": 20,
        "type": StepType.TEXT_INPUT,
        "url": None,
    },
    {
        "order": 16,
        "title": "Изучить методичку по сорсингу",
        "description": "Изучить методичку по сорсингу",
        "duration": 120,  # 2 часа
        "type": StepType.CONTENT,
        "url": "https://disk.yandex.ru/i/XAW2A5lJdWpwqQ",
    },
    {
        "order": 17,
        "title": "Задание: Зачем кавычки в Google поиске?",
        "description": "Напишите зачем при поиске в Google нужно взять слово в кавычки (\"\"), что будет если не сделать это?",
        "duration": 5,
        "type": StepType.TEXT_INPUT,
        "url": None,
    },
    {
        "order": 18,
        "title": "Задание: Зачем оператор site?",
        "description": "Напишите зачем используют оператор site?",
        "duration": 5,
        "type": StepType.TEXT_INPUT,
        "url": None,
    },
    {
        "order": 19,
        "title": "Задание: Запрос для Google с операторами",
        "description": "Напишите запрос по вакансии для поиска через Google, используя 2 и более операторов. Запрос будет добавлен в карту поиска раздел 'Карта активного поиска'",
        "duration": 30,
        "type": StepType.TEXT_INPUT,
        "url": None,
    },
    {
        "order": 20,
        "title": "Изучить поиск в социальных сетях",
        "description": "Изучить поиск в социальных сетях",
        "duration": 10,
        "type": StepType.CONTENT,
        "url": "https://disk.yandex.ru/i/ubRl1NeT00SB5g",
    },
    {
        "order": 21,
        "title": "Задание: Каналы поиска в соцсетях",
        "description": "Напишите каналы поиска, подходящие для вашей вакансии. Аргументируйте почему они наиболее эффективны",
        "duration": 15,
        "type": StepType.TEXT_INPUT,
        "url": None,
    },
    {
        "order": 22,
        "title": "Задание: Запрос для социальных сетей",
        "description": "Составьте запрос по вакансии для поиска в социальных сетях. Результаты запроса и найденные соцсети будут добавлены в карту поиска в раздел 'Карта пассивного поиска'",
        "duration": 15,
        "type": StepType.TEXT_INPUT,
        "url": None,
    },
    {
        "order": 23,
        "title": "Изучить методичку по анализу рынка",
        "description": "Изучить методичку по анализу рынка",
        "duration": 40,
        "type": StepType.CONTENT,
        "url": "https://disk.yandex.ru/i/7jZZ006W4iwLWg",
    },
    {
        "order": 24,
        "title": "Задание: Отобрать 50 резюме",
        "description": "Отобрать 50 подходящих резюме различными способами сорсинга (из них как минимум 10 резюме найдены не через HH)",
        "duration": 50,
        "type": StepType.TEXT_INPUT,
        "url": None,
    },
    {
        "order": 25,
        "title": "Задание: Анализ рынка",
        "description": "Сделать анализ рынка, на основе которого выбраны минимум 10 резюме и отправлены наставнику на проверку. Данные анализа будут добавлены в карту поиска лист 'Анализ рынка'",
        "duration": 70,  # 1 час 10 минут
        "type": StepType.TEXT_INPUT,
        "url": None,
    },
    {
        "order": 26,
        "title": "Встреча с наставником - итоги дня 2",
        "description": "Проведена встреча с наставником, обсуждены итоги дня (ссылку на встречу отправит наставник в telegram чате)",
        "duration": 30,
        "type": StepType.OFFLINE,
        "url": None,
    },
    # ========================
    # ДЕНЬ 3: Звонки и интервью
    # ========================
    {
        "order": 27,
        "title": "Изучить методичку по звонкам",
        "description": "Изучить методичку по звонкам",
        "duration": 40,
        "type": StepType.CONTENT,
        "url": "https://disk.yandex.ru/i/f8iIiPYbsB8tag",
    },
    {
        "order": 28,
        "title": "Задание: Шаблон сообщения для недозвона",
        "description": "Составить шаблон сообщения для недозвона. Шаблон будет добавлен в карту поиска в лист 'Речевые модули'",
        "duration": 10,
        "type": StepType.TEXT_INPUT,
        "url": None,
    },
    {
        "order": 29,
        "title": "Задание: Скрипт телефонного звонка",
        "description": "В карте поиска заполнить лист 'Речевые модули' - прописать скрипт телефонного звонка",
        "duration": 20,
        "type": StepType.TEXT_INPUT,
        "url": None,
    },
    {
        "order": 30,
        "title": "Изучить методичку по обработке возражений",
        "description": "Изучить методичку по обработке возражений при звонке",
        "duration": 40,
        "type": StepType.CONTENT,
        "url": "https://disk.yandex.ru/i/7v6r400rnGDwXA",
    },
    {
        "order": 31,
        "title": "Задание: Обработка возражений",
        "description": "В карте поиска заполнить лист 'Возражения' - прописать основные возражения на основе вакансии",
        "duration": 15,
        "type": StepType.TEXT_INPUT,
        "url": None,
    },
    {
        "order": 32,
        "title": "Установить телефонию и E-staff",
        "description": "Установлена телефония и E-staff на компьютер, проверена работа программ",
        "duration": 10,
        "type": StepType.CONFIRMATION,
        "url": "https://disk.yandex.ru/i/EnCJEJ_BCy2hkg",
    },
    {
        "order": 33,
        "title": "Изучить инструкцию по работе с недозвонами",
        "description": "Изучить инструкцию по работе с недозвонами",
        "duration": 10,
        "type": StepType.CONTENT,
        "url": "https://disk.yandex.ru/i/nF7pTZu9vTBL7Q",
    },
    {
        "order": 34,
        "title": "Изучить стоп-лист",
        "description": "Изучен стоп-лист. В него вносятся все кандидаты, которых мы хотим закрепить за собой. В случае, если кандидат ранее связывался с нами, но минуя нас вышел на работу к заказчику, имея его ФИО в стоп-листе мы можем доказать, что первоначально установили с ним контакт и этот кандидат засчитается рекрутеру в работу. Стоп-листы заполняются каждую неделю (лучше вносить кандидатов сразу, как проработали с ними) и в пятницу отправляются заказчику. Задача за день внести всех кандидатов, с которыми были касания в стоп-лист",
        "duration": 10,
        "type": StepType.CONTENT,
        "url": None,
    },
    {
        "order": 35,
        "title": "Задание: Результативные звонки",
        "description": "Сделать минимум 20 результативных звонков и назначить 2 интервью (третий день обучения идет до тех пор, пока не будет назначено 2 интервью)",
        "duration": 240,  # оставшаяся часть дня (~4 часа)
        "type": StepType.TEXT_INPUT,
        "url": None,
    },
    {
        "order": 36,
        "title": "Встреча с наставником - итоги дня 3",
        "description": "Проведена встреча с наставником, обсуждены итоги дня (ссылку на встречу отправит наставник в telegram чате)",
        "duration": 30,
        "type": StepType.OFFLINE,
        "url": None,
    },
]

async def seed():
    print("Seeding database...")
    async for session in get_session():
        # Delete existing steps if any
        result = await session.execute(select(OnboardingStep))
        existing = result.scalars().all()
        if existing:
            print(f"Found {len(existing)} existing steps. Deleting them...")
            for step in existing:
                await session.delete(step)
            await session.commit()
            print("Existing steps deleted.")

        # Add new steps
        for item in CURRICULUM:
            step = OnboardingStep(
                order=item["order"],
                title=item["title"],
                description=item["description"],
                estimated_duration=item["duration"],
                step_type=item["type"],
                content_url=item["url"]
            )
            session.add(step)
        
        await session.commit()
        print(f"Added {len(CURRICULUM)} steps.")

if __name__ == "__main__":
    asyncio.run(seed())
