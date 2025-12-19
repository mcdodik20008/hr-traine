import google.generativeai as genai
from app.config import config
import logging
import asyncio
from typing import Optional, Literal
import base64
import uuid

logger = logging.getLogger(__name__)

# Try to import GigaChat
try:
    from gigachat import GigaChat
    GIGACHAT_AVAILABLE = True
except ImportError:
    GIGACHAT_AVAILABLE = False
    logger.warning("GigaChat library not installed. Install with: pip install gigachat")

# For direct HTTP API calls
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger.warning("aiohttp not installed. GigaChat HTTP fallback will not work.")


class LLMClient:
    """
    LLM Client with fallback support:
    1. Try Gemini (primary)
    2. Fallback to GigaChat if Gemini unavailable
    """
    
    def __init__(self):
        self.provider: Optional[Literal["gemini", "gigachat"]] = None
        self.model = None  # Gemini model or GigaChat client
        self.model_name = None
        self._initialized = False
        self._init_error = None
        self._gigachat_token = None
        
        # Try to initialize
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the model - try Gemini first, then GigaChat as fallback"""
        if self._initialized:
            return
        
        # Step 1: Try Gemini
        if config.GEMINI_API_KEY:
            if self._try_initialize_gemini():
                self._initialized = True
                return
        
        # Step 2: Fallback to GigaChat
        if GIGACHAT_AVAILABLE and (config.GIGACHAT_API_KEY or (config.GIGACHAT_CLIENT_ID and config.GIGACHAT_CLIENT_SECRET)):
            if self._try_initialize_gigachat():
                self._initialized = True
                return
        
        # If all failed
        if not self._initialized:
            if not self._init_error:
                self._init_error = "Не удалось инициализировать ни одну модель LLM. Проверьте конфигурацию API."
            logger.error(f"❌ {self._init_error}")
            self._initialized = True  # Mark as attempted to avoid retrying
    
    def _try_initialize_gemini(self) -> bool:
        """Try to initialize Gemini model"""
        try:
            genai.configure(api_key=config.GEMINI_API_KEY)
            
            # Try different model names in order of preference
            model_names = [
                'gemini-1.5-flash',  # Fastest, recommended
                'gemini-1.5-pro',    # Better quality
                'gemini-pro',        # Original
            ]
            
            for model_name in model_names:
                try:
                    test_model = genai.GenerativeModel(model_name)
                    # Just create the model - real test will be on first use
                    # If it fails at runtime, fallback will handle it
                    self.model = test_model
                    self.model_name = model_name
                    self.provider = "gemini"
                    logger.info(f"✅ Successfully initialized Gemini model: {model_name}")
                    return True
                except Exception as e:
                    error_msg = str(e)
                    logger.warning(f"Failed to initialize Gemini {model_name}: {error_msg[:100]}")
                    if "location is not supported" in error_msg.lower():
                        self._init_error = "Gemini API недоступен в вашем регионе. Пробую GigaChat..."
                        logger.info(self._init_error)
                        return False
                    continue
            
            self._init_error = "Не удалось инициализировать ни одну модель Gemini."
            return False
            
        except Exception as e:
            logger.warning(f"Gemini initialization error: {e}")
            self._init_error = f"Ошибка инициализации Gemini: {str(e)[:100]}"
            return False
    
    def _try_initialize_gigachat(self) -> bool:
        """Try to initialize GigaChat model"""
        try:
            # Check if we have credentials
            if not (config.GIGACHAT_CLIENT_ID and config.GIGACHAT_CLIENT_SECRET) and not config.GIGACHAT_API_KEY:
                self._init_error = "GigaChat credentials not configured (need CLIENT_ID and CLIENT_SECRET or API_KEY)"
                return False
            
            # Store credentials for HTTP API calls (more reliable than library)
            # Option 1: готовый base64 "client_id:secret" -> GIGACHAT_AUTH_KEY
            # Option 2: сырые id/secret -> GIGACHAT_CLIENT_ID / GIGACHAT_CLIENT_SECRET
            self._gigachat_auth_key = config.GIGACHAT_AUTH_KEY.strip() if config.GIGACHAT_AUTH_KEY else None
            self._gigachat_client_id = config.GIGACHAT_CLIENT_ID.strip() if config.GIGACHAT_CLIENT_ID else None
            self._gigachat_client_secret = config.GIGACHAT_CLIENT_SECRET.strip() if config.GIGACHAT_CLIENT_SECRET else None
            self._gigachat_access_token = None  # Will be fetched on first use
            
            # Try library first, but we'll use HTTP API as fallback
            if GIGACHAT_AVAILABLE:
                try:
                    if config.GIGACHAT_CLIENT_ID and config.GIGACHAT_CLIENT_SECRET:
                        client = GigaChat(
                            credentials=config.GIGACHAT_CLIENT_ID,
                            scope="GIGACHAT_API_PERS",
                            verify_ssl_certs=False
                        )
                    elif config.GIGACHAT_API_KEY:
                        client = GigaChat(credentials=config.GIGACHAT_API_KEY, verify_ssl_certs=False)
                    else:
                        client = None
                    
                    if client:
                        self.model = client
                        self._use_gigachat_library = True
                except Exception as lib_error:
                    logger.warning(f"GigaChat library initialization failed: {lib_error}, will use HTTP API")
                    self._use_gigachat_library = False
            else:
                self._use_gigachat_library = False
            
            # Mark as initialized (will use HTTP API if library failed)
            self.model_name = "GigaChat"
            self.provider = "gigachat"
            logger.info("✅ Successfully initialized GigaChat model")
            return True
            
        except Exception as e:
            logger.warning(f"GigaChat initialization error: {e}")
            self._init_error = f"Ошибка инициализации GigaChat: {str(e)[:100]}"
            return False
    
    def _ensure_model_initialized(self):
        """Ensure model is initialized - for backward compatibility"""
        if not self._initialized:
            self._initialize_model()

    async def generate_response(self, prompt: str, history: list = None) -> str:
        """Generate response using current provider (Gemini or GigaChat)"""
        try:
            self._ensure_model_initialized()
            
            if self.model is None:
                if self._init_error:
                    return f"❌ {self._init_error}"
                return "❌ Модель LLM не инициализирована. Проверьте конфигурацию."
            
            # Use appropriate provider
            if self.provider == "gemini":
                return await self._generate_gemini(prompt, history)
            elif self.provider == "gigachat":
                return await self._generate_gigachat(prompt, history)
            else:
                return "❌ Неизвестный провайдер LLM"
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"LLM Error: {e}")
            logger.exception("Full error traceback:")
            
            # Try fallback if current provider failed
            if self.provider == "gemini" and GIGACHAT_AVAILABLE:
                logger.info("Gemini failed, trying GigaChat fallback...")
                if self._try_initialize_gigachat():
                    try:
                        return await self._generate_gigachat(prompt, history)
                    except Exception as fallback_error:
                        logger.error(f"GigaChat fallback also failed: {fallback_error}")
            
            # Try fallback if current provider failed with 404 or similar
            if self.provider == "gemini" and ("404" in error_msg or "not found" in error_msg.lower()):
                logger.info("Gemini model not found (404), trying GigaChat fallback...")
                if GIGACHAT_AVAILABLE and (config.GIGACHAT_API_KEY or (config.GIGACHAT_CLIENT_ID and config.GIGACHAT_CLIENT_SECRET)):
                    if self._try_initialize_gigachat():
                        try:
                            return await self._generate_gigachat(prompt, history)
                        except Exception as fallback_error:
                            logger.error(f"GigaChat fallback also failed: {fallback_error}")
                            return f"❌ Gemini модель не найдена, GigaChat также не сработал: {str(fallback_error)[:150]}"
            
            # Provide specific error messages
            if "location is not supported" in error_msg.lower() or "400" in error_msg:
                return "❌ API недоступен в вашем регионе. Пожалуйста, используйте VPN или обратитесь к администратору."
            elif "404" in error_msg or "not found" in error_msg.lower():
                return "❌ Модель LLM не найдена. Пожалуйста, проверьте конфигурацию API или используйте GigaChat fallback."
            elif "API key" in error_msg.lower() or "authentication" in error_msg.lower():
                return "❌ Ошибка аутентификации API. Проверьте API ключи в настройках."
            else:
                return f"❌ Ошибка обработки запроса: {error_msg[:150]}"
    
    async def _generate_gemini(self, prompt: str, history: list = None) -> str:
        """Generate response using Gemini"""
        if history:
            chat = self.model.start_chat(history=history)
            response = await chat.send_message_async(prompt)
            return response.text
        else:
            response = await self.model.generate_content_async(prompt)
            return response.text
    
    async def _get_gigachat_token(self) -> str:
        """Get GigaChat access token via OAuth2"""
        if self._gigachat_access_token:
            return self._gigachat_access_token
        
        if not AIOHTTP_AVAILABLE:
            raise Exception("aiohttp not available for GigaChat HTTP API")
        
        # Если дан готовый base64 ключ (Authorization key из кабинета) — используем его напрямую
        if self._gigachat_auth_key:
            auth_b64 = self._gigachat_auth_key
        else:
            # Иначе собираем из сырых id/secret
            client_id_raw = (self._gigachat_client_id or "").strip()
            client_secret_raw = (self._gigachat_client_secret or "").strip()
            auth_string = f"{client_id_raw}:{client_secret_raw}"
            auth_bytes = auth_string.encode('utf-8')
            auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
        
        # Generate RqUID
        rquid = str(uuid.uuid4())
        
        async with aiohttp.ClientSession() as session:
            url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json',
                'RqUID': rquid,
                'Authorization': f'Basic {auth_b64}'
            }
            data = {'scope': 'GIGACHAT_API_PERS'}
            
            async with session.post(url, headers=headers, data=data, ssl=False) as response:
                if response.status == 200:
                    result = await response.json()
                    self._gigachat_access_token = result.get('access_token')
                    if not self._gigachat_access_token:
                        error_text = await response.text()
                        raise Exception(f"No access_token in response: {error_text}")
                    return self._gigachat_access_token
                else:
                    error_text = await response.text()
                    logger.error(f"GigaChat OAuth error: {response.status} - {error_text}")
                    logger.error(f"Using credentials lengths: CLIENT_ID={len(client_id_raw)}, CLIENT_SECRET={len(client_secret_raw)}")
                    raise Exception(f"Failed to get GigaChat token: {response.status} - {error_text}")
    
    async def _generate_gigachat(self, prompt: str, history: list = None) -> str:
        """Generate response using GigaChat via HTTP API"""
        # Format history if provided
        messages = []
        if history:
            # Convert Gemini history format to GigaChat format
            for msg in history:
                if hasattr(msg, 'role') and hasattr(msg, 'parts'):
                    # Gemini format: object with role and parts
                    role = "user" if msg.role == "user" else "assistant"
                    content = msg.parts[0].text if msg.parts and len(msg.parts) > 0 else ""
                    if content:
                        messages.append({"role": role, "content": content})
                elif isinstance(msg, dict):
                    # Check if it's Gemini format dict (from interview handler)
                    if "role" in msg and "parts" in msg:
                        role = "user" if msg["role"] == "user" else "assistant"
                        if isinstance(msg["parts"], list) and len(msg["parts"]) > 0:
                            content = msg["parts"][0] if isinstance(msg["parts"][0], str) else str(msg["parts"][0])
                        else:
                            content = ""
                        if content:
                            messages.append({"role": role, "content": content})
                    elif "role" in msg and "content" in msg:
                        # Already in GigaChat format
                        messages.append(msg)
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        # Use HTTP API (more reliable than library)
        if AIOHTTP_AVAILABLE and self._gigachat_client_id and self._gigachat_client_secret:
            try:
                token = await self._get_gigachat_token()
                
                async with aiohttp.ClientSession() as session:
                    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
                    headers = {
                        'Accept': 'application/json',
                        'Authorization': f'Bearer {token}',
                        'Content-Type': 'application/json'
                    }
                    payload = {
                        "model": "GigaChat",
                        "messages": messages,
                        "temperature": 0.7
                    }
                    
                    async with session.post(url, headers=headers, json=payload, ssl=False) as response:
                        if response.status == 200:
                            result = await response.json()
                            # Extract response text
                            if 'choices' in result and len(result['choices']) > 0:
                                return result['choices'][0]['message']['content']
                            elif 'content' in result:
                                return result['content']
                            else:
                                return str(result)
                        else:
                            error_text = await response.text()
                            raise Exception(f"GigaChat API error: {response.status} - {error_text}")
            except Exception as e:
                logger.error(f"GigaChat HTTP API error: {e}")
                raise
        
        # Fallback to library if HTTP not available
        if hasattr(self, '_use_gigachat_library') and self._use_gigachat_library and self.model:
            loop = asyncio.get_event_loop()
            def _sync_generate():
                try:
                    response = self.model.chat(messages)
                except TypeError:
                    # Try positional argument
                    response = self.model.chat(*messages) if messages else self.model.chat(prompt)
                
                if hasattr(response, 'choices') and response.choices:
                    return response.choices[0].message.content
                elif hasattr(response, 'content'):
                    return response.content
                elif isinstance(response, str):
                    return response
                else:
                    return str(response)
            
            return await loop.run_in_executor(None, _sync_generate)
        
        raise Exception("GigaChat not properly configured")

    async def simulate_candidate(self, resume_text: str, user_message: str, conversation_history: list, psychotype: str = "Target") -> str:
        """
        Simulates a candidate response based on resume, conversation history, and psychotype.
        
        Args:
            resume_text: Candidate's resume
            user_message: Interviewer's question
            conversation_history: Previous conversation
            psychotype: One of "Target", "Toxic", "Silent", "Evasive"
        """
        # Define psychotype-specific behaviors
        psychotype_prompts = {
            "Target": """
Ты целевой кандидат — идеальный собеседник для интервью.
- Отвечай развёрнуто, но по существу
- Будь вежлив и конструктивен
- Приводи конкретные примеры из своего опыта
- Задавай уточняющие вопросы, если вопрос неясен
- Показывай заинтересованность в позиции
""",
            "Toxic": """
Ты токсичный кандидат — создаёшь конфликтные ситуации.
- Будь агрессивным и критичным
- Негативно отзывайся о прошлых работодателях
- Перебивай и не давай интервьюеру говорить (в рамках возможного)
- Задавай провокационные вопросы о компании
- Демонстрируй высокомерие и завышенное самомнение
- НО всё равно не нарушай роль кандидата
""",
            "Silent": """
Ты молчаливый кандидат — отвечаешь минимально.
- Используй односложные ответы: "Да", "Нет", "Не знаю"
- Отвечай максимально кратко, 1-2 предложения
- Не развивай мысли, даже если просят
- Показывай незаинтересованность
- Избегай зрительного контакта (упоминай это иногда)
""",
            "Evasive": """
Ты уклончивый кандидат — избегаешь прямых ответов.
- Отвечай расплывчато, без конкретики
- Уходи от неудобных вопросов
- Используй много общих фраз: "в целом", "как правило", "обычно"
- Не приводи конкретные примеры
- Переводи разговор на другие темы
- Будь вежливым, но неинформативным
"""
        }
        
        behavior = psychotype_prompts.get(psychotype, psychotype_prompts["Target"])
        
        system_prompt = f"""
{behavior}

РЕЗЮМЕ КАНДИДАТА:
{resume_text}

ВАЖНЫЕ ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе своего резюме и заданной роли
2. НЕ нарушай характер — ты КАНДИДАТ на собеседовании, НЕ AI-помощник
3. НЕ давай советов интервьюеру, как лучше проводить интервью
4. НЕ говори фразы типа "как я могу помочь" или "чем могу быть полезен" от лица AI
5. Если вопрос выходит за рамки резюме, импровизируй в рамках роли или скажи "я не уверен"
6. Веди себя как настоящий человек на собеседовании

КРИТИЧЕСКИ ВАЖНО:
- Дай ТОЛЬКО ОДИН короткий ответ на последний вопрос интервьюера
- НЕ пиши весь диалог целиком
- НЕ повторяй предыдущие реплики
- Ответь ТОЛЬКО как кандидат на ЭТОТ конкретный вопрос
"""
        
        full_prompt = f"{system_prompt}\n\nИнтервьюер: {user_message}\nКандидат:"
        return await self.generate_response(full_prompt, conversation_history)
    
    async def detect_interview_farewell(self, user_message: str, conversation_history: list, resume_text: str, psychotype: str = "Target") -> dict:
        """
        Определяет, попрощался ли интервьюер с кандидатом.
        
        Args:
            user_message: Последнее сообщение от HR
            conversation_history: История диалога
            resume_text: Резюме кандидата для контекста
            psychotype: Психотип кандидата
            
        Returns:
            dict: {"is_farewell": bool, "farewell_message": str}
        """
        # Формируем контекст из последних 3 сообщений
        context_messages = []
        if conversation_history:
            recent = conversation_history[-6:]  # Последние 3 пары сообщений
            for msg in recent:
                if isinstance(msg, dict):
                    if "role" in msg and "parts" in msg:
                        role = "HR" if msg["role"] == "user" else "Кандидат"
                        content = msg["parts"][0] if isinstance(msg["parts"], list) else str(msg["parts"])
                        context_messages.append(f"{role}: {content}")
        
        context = "\n".join(context_messages[-6:]) if context_messages else "Начало интервью"
        
        prompt = f"""
Ты анализируешь диалог собеседования. Определи, попрощался ли интервьюер (HR) с кандидатом.

ПОСЛЕДНЕЕ СООБЩЕНИЕ HR: {user_message}

КОНТЕКСТ (последние сообщения):
{context}

Признаки прощания:
- Благодарность за интервью ("спасибо за интервью", "спасибо за время")
- Фразы "до свидания", "всего доброго", "на этом закончим"
- Сообщение о следующих шагах ("мы с вами свяжемся", "ждите нашего звонка")
- Завершающие формулировки ("это все вопросы", "интервью окончено")

ВАЖНО: 
- Вопрос "У вас есть вопросы ко мне?" - это НЕ прощание (это часть интервью)
- "Расскажите о себе" - это НЕ прощание
- "Почему вы хотите работать у нас?" - это НЕ прощание
- Только ЯВНОЕ завершение интервью считается прощанием

Если это прощание, сгенерируй КРАТКИЙ ответ кандидата (1-2 предложения) в характере психотипа "{psychotype}":
- Target: вежливое "Спасибо за интервью, было приятно пообщаться!"
- Toxic: слегка высокомерное "Ну наконец-то. Надеюсь, не зря потратил время."
- Silent: минималистичное "Спасибо. До свидания."
- Evasive: расплывчатое "Спасибо, было интересно. Всего доброго."

ФОРМАТ ОТВЕТА (строго JSON):
{{
  "is_farewell": true/false,
  "farewell_message": "ответ кандидата (если is_farewell=true, иначе пустая строка)"
}}
"""
        
        try:
            response = await self.generate_response(prompt)
            
            # Extract JSON from response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            import json
            result = json.loads(response)
            
            # Validate result
            if "is_farewell" not in result:
                result["is_farewell"] = False
            if "farewell_message" not in result:
                result["farewell_message"] = ""
            
            return result
            
        except Exception as e:
            logger.error(f"Error detecting farewell: {e}")
            # Default to not farewell on error
            return {"is_farewell": False, "farewell_message": ""}
    
    async def validate_search_map(self, excel_data: dict) -> dict:
        """
        Validates search map using LLM to check logical consistency.
        
        Args:
            excel_data: Dictionary with Excel content (keys: sheet names, values: data)
        
        Returns:
            dict with 'valid': bool, 'issues': list[str], 'suggestions': list[str]
        """
        try:
            if self.model is None:
                return {"valid": True, "issues": ["LLM validation unavailable - model not initialized"], "suggestions": []}
            
            # Convert excel_data to readable format
            data_description = self._format_excel_for_llm(excel_data)
            
            prompt = f"""
Ты эксперт по подбору персонала. Проанализируй заполненную карту поиска и найди логические несостыковки, ошибки или пропуски.

ДАННЫЕ КАРТЫ ПОИСКА:
{data_description}

ЗАДАЧА:
1. Проверь соответствие требований вакансии и описания должности
2. Проверь логичность hard skills и soft skills
3. Проверь корректность отсекающих факторов
4. Найди противоречия между разными полями
5. Оцени полноту заполнения

ФОРМАТ ОТВЕТА (строго JSON):
{{
    "valid": true/false,
    "issues": ["список найденных проблем"],
    "suggestions": ["рекомендации по улучшению"]
}}

Если всё заполнено корректно и логично, верни valid: true с пустыми списками.
"""
            
            response_text = await self.generate_response(prompt)
            
            # Extract JSON from response (might be wrapped in markdown)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            import json
            result = json.loads(response_text)
            return result
            
        except Exception as e:
            logger.error(f"LLM validation error: {e}")
            return {"valid": True, "issues": [f"Validation error: {str(e)}"], "suggestions": []}
    
    def _format_excel_for_llm(self, excel_data: dict) -> str:
        """Format Excel data into readable text for LLM"""
        formatted = []
        for sheet_name, data in excel_data.items():
            formatted.append(f"\n=== {sheet_name} ===")
            if isinstance(data, dict):
                for key, value in data.items():
                    formatted.append(f"{key}: {value}")
            elif isinstance(data, list):
                for item in data:
                    formatted.append(str(item))
            else:
                formatted.append(str(data))
        return "\n".join(formatted)
    
    async def parse_structured_data(self, user_text: str, parse_instruction: str) -> dict:
        """
        Парсит текстовый ввод пользователя в структурированный JSON
        
        Args:
            user_text: Текст, введенный пользователем
            parse_instruction: Инструкция по парсингу
        
        Returns:
            dict: Распарсенные структурированные данные
        """
        prompt = f"""
Ты парсер текстовых данных в JSON.

ЗАДАЧА:
{parse_instruction}

ТЕКСТ ПОЛЬЗОВАТЕЛЯ:
{user_text}

ВАЖНО:
1. Извлеки все ключевые данные из текста
2. Верни ТОЛЬКО валидный JSON, без дополнительного текста
3. Если данные неясны, делай разумные предположения
4. Сохраняй исходные формулировки пользователя

ФОРМАТ ОТВЕТА: только JSON объект, без markdown кодблоков.
"""
        
        response = await self.generate_response(prompt)
        
        # Очистка ответа от markdown
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
        
        import json
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {response}")
            # Возвращаем исходный текст как fallback
            return {"raw_text": user_text, "parse_error": str(e)}
    
    async def evaluate_submission(self, step, user_data: dict) -> dict:
        """
        Оценивает submission пользователя по критериям шага
        
        Args:
            step: OnboardingStep с evaluation_prompt и evaluation_criteria
            user_data: Данные пользователя (parsed JSON)
        
        Returns:
            dict: {"score": float, "feedback": str, "criteria_scores": dict}
        """
        if not step.evaluation_prompt or not step.evaluation_criteria:
            # Нет кр итериев - дефолтная оценка
            return {
                "score": 5.0,
                "feedback": "Задание принято. Оценка не требуется.",
                "criteria_scores": {}
            }
        
        import json
        try:
            criteria = json.loads(step.evaluation_criteria)
        except:
            criteria = {}
        
        # Формируем промпт для evaluation
        criteria_text = "\n".join([f"- {name}: {description}" for name, description in criteria.items()])
        
        prompt = f"""
Ты эксперт по оценке заданий онбординга.

ЗАДАНИЕ: {step.title}
{step.description}

КРИТЕРИИ ОЦЕНКИ:
{criteria_text}

ОТВЕТ ПОЛЬЗОВАТЕЛЯ:
{json.dumps(user_data, ensure_ascii=False, indent=2)}

ЗАДАЧА:
1. Оцени ответ по каждому критерию (шкала 1-5)
2. Вычисли общую оценку (среднее)
3. Дай развернутый feedback с рекомендациями

ФОРМАТ ОТВЕТА (строго JSON):
{{
    "score": 4.2,
    "criteria_scores": {{
        "критерий1": 5,
        "критерий2": 4,
        "критерий3": 4
    }},
    "feedback": "Подробный feedback с тем, что хорошо и что можно улучшить"
}}
"""
        
        response = await self.generate_response(prompt)
        
        # Очистка от markdown
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
        
        try:
            result = json.loads(response)
            # Валидация результата
            if "score" not in result:
                result["score"] = 3.0
            if "feedback" not in result:
                result["feedback"] = "Evaluation completed."
            if "criteria_scores" not in result:
                result["criteria_scores"] = {}
            
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse evaluation response: {response}")
            return {
                "score": 3.0,
                "feedback": f"Оценка обработана. {response[:200]}",
                "criteria_scores": {}
            }


    async def generate_interview_report(self, conversation_history: list, candidate_resume: str, psychotype: str = "Target") -> dict:
        """
        Генерирует отчет о проведенном интервью с оценками и рекомендациями.
        
        Args:
            conversation_history: Полная история диалога интервью
            candidate_resume: Резюме кандидата
            psychotype: Психотип кандидата
            
        Returns:
            dict: {
                "overall_score": float,
                "category_scores": dict,
                "strengths": list,
                "weaknesses": list,
                "key_moments": list,
                "recommendations": list,
                "detailed_feedback": str
            }
        """
        # Форматируем историю диалога
        dialogue = []
        for msg in conversation_history:
            if isinstance(msg, dict):
                if "role" in msg and "parts" in msg:
                    role = "HR" if msg["role"] == "user" else "Кандидат"
                    content = msg["parts"][0] if isinstance(msg["parts"], list) else str(msg["parts"])
                    dialogue.append(f"{role}: {content}")
        
        dialogue_text = "\n".join(dialogue)
        
        prompt = f"""
Ты эксперт-HR, оцениваешь качество проведенного собеседования.

ИНФОРМАЦИЯ О КАНДИДАТЕ:
- Психотип: {psychotype}
- Резюме: {candidate_resume}

ПОЛНАЯ ИСТОРИЯ ДИАЛОГА ИНТЕРВЬЮ:
{dialogue_text}

ЗАДАЧА:
Оцени, насколько хорошо тренируемый HR провел интервью с этим кандидатом.

КРИТЕРИИ ОЦЕНКИ (шкала 1-10):
1. **Структура интервью** - есть ли вступление, основные вопросы, заключение
2. **Качество вопросов** - использует ли открытые, зондирующие, релевантные вопросы
3. **Активное слушание** - задает ли follow-up вопросы, уточнения
4. **Работа с психотипом** - адаптирует ли стиль под особенности кандидата
5. **Профессионализм** - вежливость, управление временем, корректное завершение

ВАЖНО:
- Оценивай РЕАЛЬНО, не завышай оценки
- Укажи 2-3 конкретных сильных момента из диалога
- Укажи 2-3 конкретных слабых момента из диалога
- Дай 3-5 практических рекомендаций по улучшению

ФОРМАТ ОТВЕТА (строго JSON):
{{
  "overall_score": 7.5,
  "category_scores": {{
    "structure": 8,
    "questions_quality": 7,
    "active_listening": 6,
    "psychotype_handling": 8,
    "professionalism": 9
  }},
  "strengths": [
    "конкретный пример хорошего момента из диалога с цитатой",
    "еще один сильный момент"
  ],
  "weaknesses": [
    "конкретный пример слабого момента из диалога",
    "еще одна слабость"
  ],
  "key_moments": [
    {{
      "moment": "краткое описание момента из диалога",
      "rating": "good",
      "comment": "почему это было хорошо"
    }},
    {{
      "moment": "другой момент",
      "rating": "bad",
      "comment": "что можно было сделать лучше"
    }}
  ],
  "recommendations": [
    "конкретный совет по улучшению",
    "еще одна рекомендация",
    "третья рекомендация"
  ],
  "detailed_feedback": "Развернутый feedback на 2-3 параграфа о том, как прошло интервью в целом"
}}
"""
        
        try:
            response = await self.generate_response(prompt)
            
            # Extract JSON from response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            import json
            result = json.loads(response)
            
            # Validate and set defaults
            if "overall_score" not in result:
                result["overall_score"] = 5.0
            if "category_scores" not in result:
                result["category_scores"] = {}
            if "strengths" not in result:
                result["strengths"] = []
            if "weaknesses" not in result:
                result["weaknesses"] = []
            if "key_moments" not in result:
                result["key_moments"] = []
            if "recommendations" not in result:
                result["recommendations"] = []
            if "detailed_feedback" not in result:
                result["detailed_feedback"] = "Интервью проведено."
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating interview report: {e}")
            logger.exception("Full error traceback:")
            # Return default report on error
            return {
                "overall_score": 5.0,
                "category_scores": {
                    "structure": 5,
                    "questions_quality": 5,
                    "active_listening": 5,
                    "psychotype_handling": 5,
                    "professionalism": 5
                },
                "strengths": ["Интервью было проведено"],
                "weaknesses": ["Требуется больше практики"],
                "key_moments": [],
                "recommendations": [
                    "Продолжайте практиковаться в проведении интервью",
                    "Изучите техники активного слушания",
                    "Подготовьте список вопросов заранее"
                ],
                "detailed_feedback": f"Не удалось сгенерировать подробный отчет из-за ошибки: {str(e)[:100]}"
            }



# Global instance
llm_client = LLMClient()


# Helper functions for easy import
async def parse_structured_data(user_text: str, parse_instruction: str) -> dict:
    """Helper function to parse structured data"""
    return await llm_client.parse_structured_data(user_text, parse_instruction)


async def evaluate_submission(step, user_data: dict) -> dict:
    """Helper function to evaluate submission"""
    return await llm_client.evaluate_submission(step, user_data)

