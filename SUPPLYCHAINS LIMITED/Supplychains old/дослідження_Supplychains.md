# Звіт дослідження: Supplychains Limited
Дата: 28 травня 2026  
Джерела: бриф_Supplychains.md, Fathom-транскрипт (28.05.2026), сайт supplychains.hk ✅, LinkedIn ✅ (часткові дані без авторизації)

---

## 🔑 Ключові знахідки

1. **Є Shanghai Branch — якого немає в брифі.** Адреса: Qingpu District, Shanghai. Телефон: +86 131 647 411 98. Це означає що компанія більша ніж здається: є фізична присутність у Китаї, ймовірно для роботи з постачальниками та відвантаженнями. Потрібно уточнити: хто там, яка роль, чи будуть вони користувачами Odoo.

2. **"Over 10 experienced logisticians" [сайт] ≠ "7 співробітників" [CRM].** Розбіжність. Або сайт перебільшує, або є підрядники/фрілансери, або Shanghai + HK разом дають 10+. Уточнити на кік-офі: реальна кількість людей і хто буде у системі.

3. **Сайт на 3 мовах: DE, ES, PT** — компанія активно таргетує Іспанію, Португалію, Південну Німеччину. LinkedIn підтверджує: публікації про Asia→Europe для іспанських та португальських імпортерів. Це окремий ринковий сегмент — клієнти в Європі, відправка з Азії.

4. **Warehouse блок дуже детальний і вже є** — IMEI scanning, serial numbers, фотофіксація, wooden crate, pallet operations. Це не майбутній план — це поточні операції. Складський блок Odoo потрібен вже в MVP, а не в Етапі 2.

5. **Прямі контракти з Maersk, MSC, CMA CGM, Emirates SkyCargo** — клієнт має серйозні carrier relationships. Можливо потрібна інтеграція з їхніми booking системами — уточнити.

---

## ✅ Підтверджено з брифу

- Послуги повного циклу: авіа, море, авто, залізниця, митне, страхування, склад — підтверджено на сайті
- Заснована 2017 — підтверджено
- Географія: Азія ↔ Європа, СНД, США — підтверджено
- Ключові хаби: Helsinki, Seoul, Dubai, Almaty — підтверджено на сайті
- WhatsApp присутній у комунікаціях — є навіть на сайті як контакт

---

## ⚠️ Розбіжності з брифом

| Питання | В брифі (CRM) | З сайту / LinkedIn | Пріоритет |
|---------|--------------|---------------------|-----------|
| Кількість людей | 7 співробітників | "Over 10 logisticians" | 🔴 Уточнити — впливає на кількість ліцензій Odoo |
| Локації | Тільки Гонконг | HK + Shanghai Branch | 🔴 Уточнити — можливі додаткові користувачі |
| Складські операції | "Етап 2" | Активні вже зараз (детальний блок на сайті) | 🟡 Переглянути пріоритет |
| Бюджет на впровадження | "від 40k EUR" (CRM) / "30–36k EUR" (слова клієнта) | — | 🔴 З попереднього аналізу |

---

## 🆕 Нова інформація

**Shanghai Branch (критично новий факт)**
- Адреса: L2B6081, Lane 1588, Zhuguang Road, Qingpu District, Shanghai 201106
- Телефон: +86 131 647 411 98
- Не згадувалась ні в брифі, ні на зустрічі
- Питання: хто там працює? Яка роль у бізнес-процесах? Чи потрібен їм доступ до Odoo?

**Активний European segment**
- Окремий маркетинг на DE, ES, PT ринки
- LinkedIn таргетує Spanish/Portuguese/German importers
- Можливо є клієнти і операції в Європі — уточнити чи це є окремий бізнес-потік

**Детальний warehouse блок (вже активний)**
- IMEI scanning (phones, headsets, smartwatches)
- Serial number tracking з фотофіксацією
- Wooden crate packaging
- Pallet loading into containers
- Gate Charge система
- Cargo sorting, short/long-term storage
→ Цей функціонал вже є і використовується. Odoo Inventory + serial tracking потрібен скоріш ніж Етап 2.

**Industries на сайті:** Electronics, Cars, Chemicals, Clothing, Furniture, Agricultural products — широкий спектр, не тільки drone components.

---

## 1. Профіль з відкритих джерел

- **Реальний розмір:** "Over 10 logisticians" [сайт] — можливо 10–15 разом з Shanghai
- **Динаміка:** зростає — є Shanghai branch, новий контракт, наймає асистента
- **Технологічний стек (видимий):** 1С (legacy), WhatsApp, контактні форми на сайті
- **Масштаб операцій:** міжнародний (Азія ↔ Європа / СНД / США / Близький Схід)
- **Веб-присутність:** активна — повноцінний сайт на 4 мовах, LinkedIn (7 followers — мінімальна активність)
- **HQ:** 16/F Kings Commercial Centre, 25 Kings Rd, Tin Hau, Hong Kong

---

## 2. Стейкхолдери — доповнення

| Особа | Що відомо | Джерело |
|-------|-----------|---------|
| Станіслав Редька | Власник, HK. Єдиний source of truth по процесах. 2–3 год/день | Зустріч |
| Новий асистент (жін.) | Нещодавно найнята, не знає процесів | Зустріч |
| Невідомий(і) — Shanghai | Хтось веде Shanghai branch. Невідомо хто | Сайт |

⚠️ LinkedIn доступний частково (без авторизації). Рекомендується перевірити вручну хто вказаний як співробітник Supplychains Limited на LinkedIn — особливо хто в Shanghai.

---

## 3. Сигнали для scope проекту

| Сигнал | Що означає для scope |
|--------|---------------------|
| Shanghai Branch | Можливі додаткові користувачі Odoo, multi-location setup, валюти CNY + HKD + USD + EUR |
| 3 мови сайту (DE/ES/PT) | Multi-language interface в Odoo може бути потрібен; уточнити |
| Детальний warehouse вже активний | Inventory + serial tracking в MVP, не в Етапі 2 |
| IMEI scanning | Odoo Inventory serial number tracking — стандартний функціонал |
| Carrier contracts (Maersk, MSC тощо) | Можлива інтеграція з booking API — уточнити потребу |
| Drone components | Compliance-документи, end-user certs — уточнити |

---

## 4. Рекомендовані модулі Odoo (оновлено)

| Модуль | Статус | Примітка |
|--------|--------|---------|
| CRM | ✓ MVP | Ліди, воронка, менеджери |
| Sales | ✓ MVP | Quotation, invoice, КП |
| Project / Tasks | ✓ MVP | Операційні задачі по shipment |
| Documents | ✓ MVP | Документообіг |
| Accounting (basic) | ✓ MVP | Оплати, витрати, маржа |
| Custom: Shipment Card | ✓ MVP (кастом) | Центральна сутність |
| Inventory + Serial tracking | ✓ **MVP (переглянути)** | IMEI, serial numbers — вже активна операція |
| Multi-currency | ✓ MVP | HKD, USD, EUR мінімум; CNY якщо Shanghai в scope |
| WhatsApp Business | ✓ Base | Базова інтеграція є |
| Portal (клієнтський кабінет) | ~ Етап 2 | |
| Multi-language interface | уточнити | DE/ES/PT clients — чи потрібно |
| HR / Payroll | ✗ | Не потрібно |
| Manufacturing | ✗ | Немає виробництва |

---

## 5. Конкуренти клієнта

Freight forwarders з HK/Азії на аналогічних маршрутах:

| Компанія | Характеристика | Система |
|----------|---------------|---------|
| Sinoair Group (sinoair.com.hk) | HK-based, air & sea, схожі маршрути | невідомо |
| Kerry Logistics | Великий гравець HK, 35k+ людей | SAP/власна |
| Scan Global Logistics | Boutique forwarder | невідомо |
| Zammler / Artex (UA) | Конкурують за Азія→Україна напрямок | 1С / власне |
| DHL Global Forwarding | Великий гравець, прямий конкурент по нішах | SAP |

Жоден з основних конкурентів у цій ніші (boutique freight forwarder Азія→Схід Європи) публічно не використовує Odoo. **Перша автоматизована компанія цієї ніші на Odoo = конкурентна перевага.**

---

## 6. Галузевий контекст

**Freight forwarding — специфіка:**

Бізнес-модель: forwarder координує ланцюжок, не перевозить сам. Заробіток — на різниці між freight cost і price to client + service fees.

**Типовий операційний процес:**
1. Inquiry → Quotation → Booking confirmation
2. Pre-shipment: commercial invoice, packing list, shipper's letter of instruction
3. Cargo pickup + warehouse (якщо consolidation)
4. Customs export (країна відправки)
5. Main carriage (авіа / море / залізниця)
6. Customs import (країна призначення)
7. Last-mile delivery
8. Final invoice, документи клієнту, архів

**Специфіка drone components:**
- Dual-use items — можливі export licenses
- Lithium batteries (IATA DGR Section II/IA) — спеціальні документи для авіа
- End-user statement або certificate можуть вимагатись

**Регуляторика Гонконгу:**
- Import/Export Ordinance (Cap. 60)
- Trade and Industry Department ліцензування
- Customs & Excise Department

**Типові болі freight forwarders:**
- Розрізнені системи: немає єдиної картки shipment
- Ручний документообіг
- Залежність від email/WhatsApp для координації
- Відсутність прозорості для клієнта
- Складний розрахунок реальної маржі (багато surcharges)

---

## 7. Ризики з відкритих джерел

| Ризик | Рівень | Джерело | Рекомендація |
|-------|--------|---------|--------------|
| Shanghai Branch невідома в брифі | 🟡 Середній | Сайт | Уточнити scope: чи входить Shanghai в проект |
| "10+ logisticians" ≠ "7 employees" | 🟡 Середній | Сайт vs CRM | Уточнити реальну кількість користувачів Odoo |
| Drone components — export controls | 🟡 Середній | Загальні знання | Уточнити compliance-процедури |
| Готівковий другий платіж | 🔴 Фінансовий | Зустріч | Не здавати звіт до оплати |

---

## Питання для кік-офу на основі дослідження

1. **Shanghai Branch** — хто там, що вони роблять, чи входять у scope Odoo?
2. **Реальна кількість людей** — "10+ logisticians" на сайті vs 7 у CRM. Скільки буде в системі?
3. **Warehouse — вже зараз чи планується?** Сайт дає детальний опис поточних складських операцій — це означає вже активний бізнес, а не майбутній план?
4. **European clients (DE/ES/PT)** — окремий бізнес-потік чи разовий? Чи потрібна multi-language підтримка в Odoo?
5. **Carrier integrations** — чи є потреба інтегруватись з booking-системами Maersk, MSC тощо?
6. **1С** — що конкретно там ведеться, скільки записів, чи потрібна міграція?
