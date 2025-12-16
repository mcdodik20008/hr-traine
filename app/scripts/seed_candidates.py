"""
Script to seed candidate profiles with different psychotypes for testing.
"""
import asyncio
import sys
import os

sys.path.append(os.getcwd())

from app.database.base import get_session
from app.database.models import CandidateProfile
from sqlalchemy.future import select

CANDIDATES = [
    {
        "name": "Мария Петрова",
        "category": "HR",
        "psychotype": "Target",
        "resume": """
Менеджер по персоналу, 5 лет опыта.
Образование: МГУ, факультет психологии.
Опыт работы:
- HR-менеджер в IT-компании (3 года): подбор, адаптация, обучение
- Рекрутер в аутсорсинговом агентстве (2 года): массовый подбор
Навыки: интервьюирование, оценка персонала, работа с ATS, английский B2
Достижения: сократила time-to-hire на 30%, внедрила систему онбординга
"""
    },
    {
        "name": "Дмитрий Токсиков",
        "category": "Sales",
        "psychotype": "Toxic",
        "resume": """
Менеджер по продажам, 7 лет опыта.
Образование: финансовый техникум.
Опыт работы:
- Начальник отдела продаж в стартапе (1 год): уволился из-за конфликта с руководством
- Старший менеджер в дистрибьюторской компании (2 года): "некомпетентное руководство"
- Менеджер по продажам в ритейле (4 года): "недооценивали мой вклад"
Навыки: холодные звонки, переговоры, CRM
Комментарий: везде были проблемы с коллегами и начальством, но я всегда прав.
"""
    },
    {
        "name": "Иван Молчунов",
        "category": "IT",
        "psychotype": "Silent",
        "resume": """
Junior Python Developer, 1 год опыта.
Образование: курсы программирования.
Опыт: стажер в небольшой студии разработки.
Навыки: Python, Django, SQL.
Проекты: учебные веб-приложения.
Интроверт, предпочитает работать самостоятельно.
"""
    },
    {
        "name": "Ольга Туманная",
        "category": "Marketing",
        "psychotype": "Evasive",
        "resume": """
Специалист по маркетингу, 4 года опыта.
Образование: университет, маркетинг.
Опыт работы:
- Маркетолог в различных компаниях: в целом занималась продвижением
- Работала с разными инструментами: соцсети, контекстная реклама, в общем, всё
Навыки: SMM, контент-маркетинг, аналитика (в той или иной степени)
Достижения: как правило, выполняла планы, обычно результаты были неплохие
"""
    }
]

async def seed_candidates():
    print("Seeding candidate profiles...")
    async for session in get_session():
        for cand_data in CANDIDATES:
            # Check if exists
            result = await session.execute(
                select(CandidateProfile).where(CandidateProfile.name == cand_data["name"])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"Candidate '{cand_data['name']}' already exists, skipping.")
                continue
            
            candidate = CandidateProfile(
                name=cand_data["name"],
                resume_text=cand_data["resume"],
                category=cand_data["category"],
                psychotype=cand_data["psychotype"]
            )
            session.add(candidate)
            print(f"Added candidate: {cand_data['name']} ({cand_data['psychotype']})")
        
        await session.commit()
        print(f"Seed complete! Added {len(CANDIDATES)} candidates.")

if __name__ == "__main__":
    asyncio.run(seed_candidates())
