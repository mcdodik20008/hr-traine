"""add_professional_candidates

Revision ID: 20251219_candidates
Revises: 20251215_collection_flow
Create Date: 2025-12-19 16:25:00

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '20251219_candidates'
down_revision = '20251215_collection_flow'
branch_labels = None
depends_on = None


def upgrade():
    """Add professional candidates with realistic resumes"""
    
    # Bind to connection
    connection = op.get_bind()
    
    # Define candidates with realistic resumes
    candidates = [
        {
            'name': 'Иван Петров',
            'resume_text': '''Опыт работы: 4 года
            
Текущая позиция: Senior Java Developer в ООО "ТехноСофт" (2022 - настоящее время)
- Разработка микросервисной архитектуры на Spring Boot
- Оптимизация производительности приложений, сокращение времени отклика на 40%
- Менторство junior разработчиков, проведение code review
- Участие в проектировании REST API для интеграции с внешними системами
- Стек: Java 17, Spring Boot 3.x, PostgreSQL, Docker, Kubernetes

Предыдущая позиция: Java Developer в АО "Банк Развития" (2020 - 2022)
- Разработка модулей банковской системы для обработки платежей
- Интеграция с платежными шлюзами и внешними API
- Написание unit и integration тестов (JUnit, Mockito)
- Работа в Agile команде по методологии Scrum
- Стек: Java 11, Spring Framework, Oracle DB, Maven, Git

Образование: Московский технический университет, бакалавр по направлению "Программная инженерия" (2016-2020)

Технические навыки:
- Языки: Java (expert), SQL (advanced), JavaScript (intermediate)
- Фреймворки: Spring Boot, Spring Cloud, Hibernate, JPA
- Базы данных: PostgreSQL, Oracle, MongoDB
- DevOps: Docker, Kubernetes, Jenkins, GitLab CI/CD
- Инструменты: IntelliJ IDEA, Maven, Gradle, Git

Сертификаты: Oracle Certified Professional Java SE 11 Developer

Личные качества: ответственный, коммуникабельный, стремлюсь к постоянному развитию, умею работать в команде.''',
            'category': 'IT',
            'psychotype': 'Target'
        },
        {
            'name': 'Наталья Смирнова',
            'resume_text': '''Опыт работы: 3.5 года

Текущая позиция: Frontend Developer (Angular) в ООО "Цифровые решения" (2023 - настоящее время)
- Разработка SPA приложений на Angular 16/17
- Внедрение state management с использованием NgRx
- Оптимизация производительности приложений, lazy loading, code splitting
- Интеграция с REST API и WebSocket для real-time обновлений
- Создание переиспользуемых UI компонентов на основе Material Design
- Стек: Angular 17, TypeScript, RxJS, NgRx, SCSS, Webpack

Предыдущая позиция: Junior Frontend Developer в ИП "ВебСтудия Альфа" (2021 - 2023)
- Верстка адаптивных интерфейсов по макетам Figma
- Разработка форм с валидацией на Angular Reactive Forms
- Работа с REST API, написание сервисов для HTTP запросов
- Участие в code review и рефакторинге legacy кода
- Стек: Angular 12-14, TypeScript, Bootstrap, HTML5, CSS3, Git

Образование: Санкт-Петербургский государственный университет, бакалавр по направлению "Информационные системы" (2017-2021)

Технические навыки:
- Языки: TypeScript (expert), JavaScript ES6+ (expert), HTML5/CSS3 (expert)
- Фреймворки: Angular 12-17, RxJS, NgRx, Jasmine, Karma
- UI библиотеки: Angular Material, PrimeNG, Bootstrap 5
- Инструменты: VS Code, Git, npm, Webpack, Chrome DevTools
- Методологии: Agile/Scrum, адаптивная верстка, Mobile First

Дополнительное образование: курсы "Продвинутый Angular" от Udemy (2022)

Личные качества: внимательна к деталям, креативна, быстро обучаюсь новым технологиям, хорошо работаю в команде.''',
            'category': 'IT',
            'psychotype': 'Evasive'
        },
        {
            'name': 'Екатерина Волкова',
            'resume_text': '''Опыт работы: 5 лет

Текущая позиция: Database Administrator (DBA) в ООО "ДатаЦентр" (2021 - настоящее время)
- Администрирование СУБД PostgreSQL и MySQL в production среде (50+ баз данных)
- Настройка репликации и кластеризации для обеспечения высокой доступности
- Мониторинг производительности БД, оптимизация медленных запросов
- Создание и поддержка резервного копирования (backup/restore стратегии)
- Планирование capacity и масштабирование БД под растущую нагрузку
- Автоматизация рутинных задач через bash скрипты и Python
- Стек: PostgreSQL 14-16, MySQL 8.x, pgAdmin, Zabbix, Prometheus

Предыдущая позиция: Junior DBA в АО "ИнфоТех" (2019 - 2021)
- Поддержка работы БД Oracle и MS SQL Server
- Выполнение миграций и обновлений схем баз данных
- Написание и оптимизация SQL запросов и хранимых процедур
- Участие в incident management при проблемах с БД
- Документирование процедур администрирования
- Стек: Oracle 12c, MS SQL Server 2016, T-SQL, PL/SQL

Образование: Московский государственный технический университет им. Баумана, специалист по направлению "Информационные системы и технологии" (2014-2019)

Технические навыки:
- СУБД: PostgreSQL (expert), MySQL (advanced), Oracle (intermediate), MS SQL Server (intermediate)
- Языки: SQL (expert), PL/pgSQL, PL/SQL, Python (для автоматизации)
- Технологии: репликация, шардирование, partitioning, индексирование
- Мониторинг: Zabbix, Prometheus, Grafana, pgBadger
- ОС: Linux (CentOS, Ubuntu), основы Windows Server
- Инструменты: pgAdmin, DBeaver, Git, Docker

Сертификаты: 
- PostgreSQL Certified Professional
- Oracle Database Administrator Certified Associate

Личные качества: ответственная, стрессоустойчивая, аналитический склад ума, быстро принимаю решения в критических ситуациях.''',
            'category': 'IT',
            'psychotype': 'Target'
        },
        {
            'name': 'Римма Козлова',
            'resume_text': '''Опыт работы: 4.5 года

Текущая позиция: Программист 1С в ООО "БизнесАвтоматика" (2022 - настоящее время)
- Разработка и доработка конфигураций 1С:Предприятие 8.3 (УТ, УПП, ЗУП)
- Внедрение 1С:Управление торговлей 11 на предприятиях розничной торговли
- Интеграция 1С с внешними системами через REST API и веб-сервисы
- Написание внешних обработок и отчетов по требованиям заказчика  
- Оптимизация медленных запросов и узких мест в конфигурациях
- Обучение пользователей работе с системой 1С
- Стек: 1С 8.3, Конфигуратор, Встроенный язык 1С, SQL, PostgreSQL

Предыдущая позиция: Младший программист 1С в ИП "Консалтинг Плюс" (2020 - 2022)
- Техническая поддержка пользователей 1С (УТ, Бухгалтерия 3.0)
- Выгрузка/загрузка данных, обмен между базами
- Настройка печатных форм и отчетов
- Обновление конфигураций до новых релизов
- Резервное копирование баз данных
- Стек: 1С 8.2/8.3, Конфигуратор, ЗУП 3.0, БП 3.0

Образование: Казанский федеральный университет, бакалавр по направлению "Прикладная информатика в экономике" (2016-2020)

Технические навыки:
- Платформа: 1С:Предприятие 8.3 (expert)
- Конфигурации: УТ 11, УПП, ЗУП 3.0, Бухгалтерия 3.0, ERP 2.0
- Языки: Встроенный язык 1С (expert), SQL (advanced), основы JavaScript
- СУБД: MS SQL Server, PostgreSQL (для 1С)
- Интеграция: REST API, SOAP, COM-соединения
- Инструменты: Конфигуратор 1С, EDT (Enterprise Development Tools), Git

Сертификаты:
- 1С:Профессионал по платформе 8.3
- 1С:Специалист по 1С:УТ 11

Дополнительное образование: Курсы "Разработчик 1С" от фирмы 1С (2020)

Личные качества: усидчивая, внимательная к деталям, хорошо коммуницирую с заказчиками, умею объяснять сложные вещи простым языком.''',
            'category': 'IT',
            'psychotype': 'Silent'
        },
        {
            'name': 'Дмитрий Соколов',
            'resume_text': '''Опыт работы: 3 года

Текущая позиция: Python Developer в ООО "АйТи Солюшнс" (2023 - настоящее время)
- Разработка backend сервисов на FastAPI и Django
- Создание RESTful API для мобильных и веб приложений
- Интеграция с внешними API (платежные системы, CRM, ERP)
- Работа с очередями сообщений (RabbitMQ, Celery) для асинхронной обработки
- Написание автотестов (pytest, unittest)
- Code review и менторство стажеров
- Стек: Python 3.11, FastAPI, Django, PostgreSQL, Redis, Docker

Предыдущая позиция: Junior Python Developer в Стартап "DataFlow" (2021 - 2023)
- Разработка парсеров и скрейперов данных (BeautifulSoup, Scrapy)
- Создание скриптов для автоматизации бизнес-процессов
- Работа с pandas и numpy для обработки данных
- Разработка Telegram ботов на aiogram
- Участие в разработке ML пайплайнов (scikit-learn)
- Стек: Python 3.8-3.9, Flask, SQLAlchemy, MongoDB, Git

Образование: Новосибирский государственный университет, бакалавр по направлению "Информатика и вычислительная техника" (2017-2021)

Технические навыки:
- Языки: Python (expert), SQL (advanced), JavaScript (basic)
- Фреймворки: FastAPI, Django, Flask, aiogram, Scrapy
- БД: PostgreSQL, MongoDB, Redis, SQLAlchemy ORM
- Async: asyncio, aiohttp, Celery, RabbitMQ
- Тестирование: pytest, unittest, coverage
- DevOps: Docker, Docker Compose, основы CI/CD
- Data Science: pandas, numpy, scikit-learn (базовые знания)
- Инструменты: PyCharm, VS Code, Git, Postman, Linux

Проекты на GitHub: 5+ open-source проектов (парсеры, боты, API сервисы)

Дополнительное образование:
- Курс "Погружение в Python" от Mail.ru (2020)
- Курс "Основы машинного обучения" от Coursera (2022)

Личные качества: любознательный, увлечен технологиями, хорошо работаю как самостоятельно, так и в команде, открыт к обратной связи.''',
            'category': 'IT',
            'psychotype': 'Toxic'
        }
    ]
    
    # Insert candidates
    for candidate in candidates:
        connection.execute(
            sa.text("""
                INSERT INTO candidate_profiles (name, resume_text, category, psychotype)
                VALUES (:name, :resume_text, :category, :psychotype)
            """),
            {
                'name': candidate['name'],
                'resume_text': candidate['resume_text'],
                'category': candidate['category'],
                'psychotype': candidate['psychotype']
            }
        )
    
    print(f"✅ Added {len(candidates)} professional candidates to database")


def downgrade():
    """Remove professional candidates"""
    connection = op.get_bind()
    
    candidate_names = [
        'Иван Петров',
        'Наталья Смирнова',
        'Екатерина Волкова',
        'Римма Козлова',
        'Дмитрий Соколов'
    ]
    
    for name in candidate_names:
        connection.execute(
            sa.text("DELETE FROM candidate_profiles WHERE name = :name"),
            {'name': name}
        )
    
    print(f"✅ Removed professional candidates from database")
