"""
Structured Input Handler
Обрабатывает диалоговый сбор структурированных данных для шагов онбординга
"""

import json
from typing import Dict, Any, Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import OnboardingStep, OnboardingSubmission
from app.core.llm_client import parse_structured_data, evaluate_submission


router = Router()


class StructuredInputState(StatesGroup):
    """Состояния для сбора структурированных данных"""
    collecting_data = State()
    awaiting_follow_up = State()
    reviewing_data = State()


class StructuredInputCollector:
    """Класс для управления процессом сбора структурированных данных"""
    
    def __init__(self, step: OnboardingStep):
        self.step = step
        self.collection_config = json.loads(step.collection_flow) if step.collection_flow else {}
        self.collected_data = {}
    
    async def start_collection(self, message: Message, state: FSMContext):
        """Начинает процесс сбора данных"""
        config_type = self.collection_config.get('type', 'text_parse')
        
        if config_type == 'text_parse':
            await self._handle_text_parse(message, state)
        elif config_type == 'sequential':
            await self._handle_sequential(message, state)
        elif config_type == 'sequential_dialogue':
            await self._handle_sequential_dialogue(message, state)
        else:
            await message.answer("⚠️ Неизвестный тип collection_flow")
    
    async def _handle_text_parse(self, message: Message, state: FSMContext):
        """Обработка типа text_parse - пользователь вводит текст, LLM парсит"""
        prompt = self.collection_config.get('prompt', 'Введите данные:')
        
        await message.answer(prompt)
        await state.set_state(StructuredInputState.collecting_data)
        await state.update_data(
            step_id=self.step.id,
            collection_type='text_parse',
            parse_instruction=self.collection_config.get('parse_instruction', '')
        )
    
    async def _handle_sequential(self, message: Message, state: FSMContext):
        """Обработка типа sequential - последовательный сбор нескольких вариантов"""
        variants = self.collection_config.get('variants', [])
        
        if not variants:
            await message.answer("⚠️ Нет вариантов для сбора")
            return
        
        # Начинаем с первого варианта
        first_variant = variants[0]
        await message.answer(first_variant.get('prompt', 'Введите данные:'))
        
        await state.set_state(StructuredInputState.collecting_data)
        await state.update_data(
            step_id=self.step.id,
            collection_type='sequential',
            variants=variants,
            current_variant_index=0,
            collected_variants={}
        )
    
    async def _handle_sequential_dialogue(self, message: Message, state: FSMContext):
        """Обработка типа sequential_dialogue - диалог с follow-up вопросами"""
        sections = self.collection_config.get('sections', [])
        
        if not sections:
            await message.answer("⚠️ Нет секций для сбора")
            return
        
        # Начинаем с первой секции
        first_section = sections[0]
        await message.answer(first_section.get('prompt', 'Введите данные:'))
        
        await state.set_state(StructuredInputState.collecting_data)
        await state.update_data(
            step_id=self.step.id,
            collection_type='sequential_dialogue',
            sections=sections,
            current_section_index=0,
            current_items=[],
            collected_sections={}
        )


@router.message(StructuredInputState.collecting_data)
async def process_structured_input(message: Message, state: FSMContext):
    """Обрабатывает ввод пользователя на этапе сбора данных"""
    from app.database.base import get_session
    
    data = await state.get_data()
    collection_type = data.get('collection_type')
    
    if collection_type == 'text_parse':
        async for session in get_session():
            await _process_text_parse(message, state, data, session)
    elif collection_type == 'sequential':
        await _process_sequential(message, state, data)
    elif collection_type == 'sequential_dialogue':
        await _process_sequential_dialogue(message, state, data)


async def _process_text_parse(message: Message, state: FSMContext, data: Dict, session: AsyncSession):
    """Обрабатывает text_parse тип"""
    user_text = message.text
    parse_instruction = data.get('parse_instruction', '')
    step_id = data.get('step_id')
    
    # Отправляем LLM для парсинга
    await message.answer("⏳ Обрабатываю ваш ответ...")
    
    try:
        # Вызов LLM для парсинга в structured JSON
        parsed_data = await parse_structured_data(user_text, parse_instruction)
        
        # Сохраняем в submission
        from app.database.models import OnboardingSubmission
        from sqlalchemy import select
        
        step = await session.get(OnboardingStep, step_id)
        
        # Создаем или обновляем submission
        submission = OnboardingSubmission(
            user_id=message.from_user.id,
            step_id=step_id,
            text_answer=user_text,
            structured_data=json.dumps(parsed_data, ensure_ascii=False),
            status='pending'
        )
        
        session.add(submission)
        await session.commit()
        
        # Оцениваем через LLM
        evaluation = await evaluate_submission(step, parsed_data)
        
        submission.evaluation_score = evaluation.get('score', 0)
        submission.llm_evaluation = json.dumps(evaluation, ensure_ascii=False)
        submission.feedback = evaluation.get('feedback', '')
        submission.status = 'approved' if evaluation.get('score', 0) >= step.passing_score else 'needs_improvement'
        
        await session.commit()
        
        # Показываем результат
        score_emoji = "✅" if submission.status == 'approved' else "⚠️"
        await message.answer(
            f"{score_emoji} **Оценка: {evaluation.get('score', 0):.1f}/5**\n\n"
            f"📊 Parsed data:\n```json\n{json.dumps(parsed_data, ensure_ascii=False, indent=2)}\n```\n\n"
            f"💬 Feedback:\n{evaluation.get('feedback', 'No feedback')}"
        )
        
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при обработке: {str(e)}\nПопробуйте еще раз.")


async def _process_sequential(message: Message, state: FSMContext, data: Dict):
    """Обрабатывает sequential тип - последовательный сбор вариантов"""
    variants = data['variants']
    current_index = data['current_variant_index']
    collected_variants = data.get('collected_variants', {})
    
    # Сохраняем текущий вариант
    current_variant = variants[current_index]
    variant_name = current_variant.get('name')
    collected_variants[variant_name] = {
        'текст': message.text,
        'длина': len(message.text)
    }
    
    # Показываем длину
    await message.answer(f"✅ Длина: {len(message.text)} символов")
    
    # Переходим к следующему варианту
    next_index = current_index + 1
    
    if next_index < len(variants):
        # Есть еще варианты
        next_variant = variants[next_index]
        await message.answer(next_variant.get('prompt', 'Введите следующий вариант:'))
        
        await state.update_data(
            current_variant_index=next_index,
            collected_variants=collected_variants
        )
    else:
        # Все варианты собраны
        await message.answer(
            "✅ Все варианты собраны!\n\n" +
            "\n".join([
                f"• {name}: {data['длина']} символов"
                for name, data in collected_variants.items()
            ])
        )
        
        # TODO: Сохранить в БД и оценить через LLM
        await state.clear()


async def _process_sequential_dialogue(message: Message, state: FSMContext, data: Dict):
    """Обрабатывает sequential_dialogue - диалог с уточнениями"""
    sections = data['sections']
    current_section_index = data['current_section_index']
    current_items = data.get('current_items', [])
    collected_sections = data.get('collected_sections', {})
    
    current_section = sections[current_section_index]
    section_name = current_section.get('name')
    
    # Добавляем текущий ответ к списку items
    if not current_items:
        # Это первый ввод - список элементов
        items_list = [item.strip() for item in message.text.split(',') if item.strip()]
        current_items = [{'название': item} for item in items_list]
        
        # Спрашиваем follow-up для первого элемента
        if current_items and current_section.get('follow_up'):
            first_item = current_items[0]['название']
            follow_up_prompts = current_section.get('follow_up', [])
            
            if follow_up_prompts:
                await message.answer(f"Для '{first_item}' - {follow_up_prompts[0]}?")
                await state.update_data(
                    current_items=current_items,
                    current_item_index=0,
                    current_follow_up_index=0
                )
                await state.set_state(StructuredInputState.awaiting_follow_up)
                return
        
        # Нет follow-up, сохраняем секцию
        collected_sections[section_name] = items_list
        await _move_to_next_section(message, state, sections, current_section_index + 1, collected_sections)
    

@router.message(StructuredInputState.awaiting_follow_up)
async def process_follow_up(message: Message, state: FSMContext):
    """Обрабатывает follow-up ответы в sequential_dialogue"""
    data = await state.get_data()
    current_items = data['current_items']
    current_item_index = data.get('current_item_index', 0)
    current_follow_up_index = data.get('current_follow_up_index', 0)
    sections = data['sections']
    current_section_index = data['current_section_index']
    current_section = sections[current_section_index]
    follow_up_prompts = current_section.get('follow_up', [])
    
    # Сохраняем ответ
    follow_up_field = follow_up_prompts[current_follow_up_index]
    current_items[current_item_index][follow_up_field] = message.text
    
    # Проверяем, есть ли еще follow-up для этого item
    next_follow_up_index = current_follow_up_index + 1
    
    if next_follow_up_index < len(follow_up_prompts):
        # Еще есть follow-up вопросы для этого item
        item_name = current_items[current_item_index]['название']
        await message.answer(f"Для '{item_name}' - {follow_up_prompts[next_follow_up_index]}?")
        await state.update_data(current_follow_up_index=next_follow_up_index)
    else:
        # Закончили с этим item, переходим к следующему
        next_item_index = current_item_index + 1
        
        if next_item_index < len(current_items):
            # Есть еще items
            next_item_name = current_items[next_item_index]['название']
            await message.answer(f"Для '{next_item_name}' - {follow_up_prompts[0]}?")
            await state.update_data(
                current_item_index=next_item_index,
                current_follow_up_index=0,
                current_items=current_items
            )
        else:
            # Закончили со всеми items этой секции
            section_name = current_section.get('name')
            collected_sections = data.get('collected_sections', {})
            collected_sections[section_name] = current_items
            
            # Переходим к следующей секции
            await _move_to_next_section(message, state, sections, current_section_index + 1, collected_sections)


async def _move_to_next_section(message: Message, state: FSMContext, sections, next_index, collected_sections):
    """Переходит к следующей секции или завершает сбор"""
    if next_index < len(sections):
        next_section = sections[next_index]
        await message.answer(next_section.get('prompt', 'Введите данные:'))
        await state.update_data(
            current_section_index=next_index,
            current_items=[],
            collected_sections=collected_sections
        )
        await state.set_state(StructuredInputState.collecting_data)
    else:
        # Все секции собраны
        await message.answer(
            "✅ Все данные собраны!\n\n" +
            "\n".join([
                f"**{name}:** {len(items)} элементов"
                for name, items in collected_sections.items()
            ])
        )
        
        # TODO: Сохранить в БД и оценить
        await state.clear()
