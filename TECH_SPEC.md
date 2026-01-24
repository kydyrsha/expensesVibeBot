---

## 5. Data Storage

### 5.1 Database
- Online database: PostgreSQL
- Supabase used as backend-as-a-service

---

### 5.2 `expenses` Table

| Field | Type | Description |
|---|---|---|
| id | uuid | Primary key |
| user_id | bigint | Telegram user id |
| amount | integer | Expense amount |
| category | text | Expense category |
| created_at | timestamp | Creation date |

---

## 6. Non-Functional Requirements
- Simple and clean architecture
- Minimal dependencies
- Asynchronous processing
- No overengineering
- Easy to extend in the future

---

## 7. Technical Requirements
- Programming language: Python 3.11
- Telegram API framework: aiogram
- Database: Supabase (PostgreSQL)
- Scheduler: APScheduler or asyncio-based scheduler
- No ORM
- No NoSQL databases

---

## 8. Limitations (MVP)
- No expense editing
- No expense deletion
- No category management via bot
- No multi-currency support
- No charts or analytics

---

## 9. Acceptance Criteria
- Expense is saved only after category selection
- Data is stored in an online database
- `/week` command returns correct weekly report
- Weekly report is sent automatically
- Bot works reliably without manual intervention

---
