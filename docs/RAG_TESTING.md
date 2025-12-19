# Testing RAG Real-Time Coach

## Test Cases

### ✅ Test 1: Prohibited Questions (Warning)

**Question:** "Сколько вам лет?"  
**Expected:** ⚠️ Warning about age discrimination (ТК РФ ст. 3)

**Question:** "Какие у вас планы на детей?"  
**Expected:** ⚠️ Warning about family status discrimination

**Question:** "Какая у вас национальность?"  
**Expected:** ⚠️ Warning about ethnicity discrimination

---

### 💡 Test 2: Best Practices (Tips)

**Question:** "Вы умеете работать в команде?"  
**Expected:** 💡 Tip to use open questions instead of closed

**Question:** "Расскажите о сложном проекте"  
**Expected:** 💡 Tip about STAR technique

---

### ℹ️ Test 3: Interview Techniques (Info)

**Question:** "Опишите ситуацию, когда вам пришлось принять непопулярное решение"  
**Expected:** ℹ️ Info about leadership assessment

---

### ❌ Test 4: No Feedback

**Question:** "Какой у вас опыт работы с Java?"  
**Expected:** No feedback (good technical question)

---

## Manual Testing Steps

1. **Initialize RAG:**
   ```bash
   python -m app.scripts.initialize_rag
   ```

2. **Start bot:**
   ```bash
   python -m app.bot.main
   ```

3. **Start interview:**
   - Send: `/interview`
   - Choose candidate
   - Say: "Здравствуйте!"

4. **Test questions:**
   - Try each test case above
   - Verify feedback appears BEFORE candidate response
   - Check that candidate still responds normally after feedback

---

## Expected Flow

```
👤 User: Сколько вам лет?

🤖 Bot (Coach): ⚠️ Вопросы о возрасте и дате рождения могут быть 
                дискриминационными по ст. 3 ТК РФ. Фокусируйтесь на 
                релевантном опыте работы и профессиональных навыках

🤖 Bot (Candidate): Мне 28 лет.

---

👤 User: Вы умеете работать в команде?

🤖 Bot (Coach): 💡 Используйте открытые вопросы вместо закрытых. 
                Вместо 'Вы умеете работать в команде?' спросите 
                'Расскажите о вашем опыте работы в команде'

🤖 Bot (Candidate): Да, умею работать в команде.

---

👤 User: Расскажите о сложном проекте, который вы реализовали

🤖 Bot (Coach): 💡 Техника STAR помогает получить структурированный ответ

🤖 Bot (Candidate): [Detailed response about project...]
```

---

## Troubleshooting

### RAG Coach not loading

Check logs for:
```
⚠️ RAG index not found. Run: python -m app.scripts.initialize_rag
```

Solution:
```bash
python -m app.scripts.initialize_rag
```

### No feedback appearing

1. Check that RAG initialized:
   ```
   ✅ RAG Coach loaded with 53 documents
   ```

2. Check question similarity - may not match knowledge base

3. Check score threshold in `coach.py` (default: 1.2)

### Import errors

Install dependencies:
```bash
pip install faiss-cpu sentence-transformers
```
