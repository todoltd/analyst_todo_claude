# Галузевий брифінг: Freight Forwarding / Міжнародна логістика
Дата: 28 травня 2026
Географія: Hong Kong / міжнародний
Модель: B2B послуги
Клієнт: SUPPLYCHAINS LIMITED

---

## Головне для команди

1. **Shipment — це центральний об'єкт бізнесу, якого немає в стандартному Odoo.** Весь бізнес freight forwarder крутиться навколо «відправки» (shipment job/file): у ній живуть документи, коости, виручка, підрядники, терміни. У Odoo такого об'єкта немає з коробки — його потрібно кастомізувати або будувати як Project + Sale Order + набір custom полів. Це ключове архітектурне рішення проекту, яке треба закрити на кік-офі.

2. **Dual-use / drone components — це compliance-ризик, не просто довідник товарів.** Дрони та їхні компоненти підпадають під export controls (Wassenaar Arrangement, US EAR/ITAR, EU Dual-Use Regulation, HK import/export ordinance). Система має підтримувати скринінг отримувача проти санкційних списків, зберігати End-User Certificates (EUC), фіксувати HS-коди з DG-класифікацією. Якщо клієнт не думав про це системно — він або вже вирішує вручну, або не вирішує взагалі.

3. **Маржа у freight forwarder'а вузька і нестабільна; фінансова аналітика по шипменту — критична.** Заробіток — різниця між тим, що виставили клієнту (selling rate), і тим, що заплатили перевізнику/агенту (buying rate). Відстежується per-shipment P&L. Відсутність цього в системі означає, що компанія веде P&L у Excel — і це майже завжди правда для SMB на 1С.

---

## Типова бізнес-модель

**Хто клієнти:** Імпортери/експортери (промислові підприємства, дистриб'ютори, e-commerce гравці, виробники дронів та електроніки), які не хочуть або не можуть самостійно організовувати міжнародну доставку. Для SUPPLYCHAINS — скоріш за все B2B клієнти у Польщі, Іспанії, Португалії, Україні, які закуповують компоненти в Азії.

**Хто постачальники (vendors):** Ocean carriers (COSCO, MSC, Evergreen, Hapag-Lloyd), авіакомпанії та GSSA-агенти (Cathay Cargo, Emirates SkyCargo), trucking companies у кожній країні, митні брокери (інколи in-house, інколи outsourced), склади (CFS — Container Freight Station), страхові компанії вантажів, агенти-кореспонденти в країнах призначення/відправлення (так звані overseas agents або co-loaders).

**Де заробіток (revenue streams):**
- Freight margin: різниця між buying і selling rate на ocean/air freight
- Handling fees: origin charges, destination charges, documentation fees
- Customs brokerage fees: за митне оформлення в країні призначення або відправлення
- Cargo insurance premium margin: клієнту виставляється з надбавкою
- Procurement service fee: за закупівлі товарів в Азії на замовлення клієнта
- Storage/warehousing fees: якщо є власний або орендований склад
- Consulting/advisory: для нових клієнтів по Incoterms, документації

**Операційна модель:** Кожна відправка — це «file» або «job», яким керує один операційний менеджер (або team). Типовий lifecycle: Запит → Котирування → Підтвердження → Буккінг у перевізника → Збір документів → Відправка → Трекінг → Доставка → Виставлення рахунку → Закриття файлу. Мікрокоманда 7-10 осіб — кожен менеджер веде 20-80 активних шипментів одночасно.

---

## Типові больові точки галузі

**1. Shipment tracking у Excel або WhatsApp**
Більшість SMB freight forwarders відстежують статуси вантажів у Google Sheets або Excel. Немає єдиної системи статусів, немає автоматичних нотифікацій клієнту. Коли B/L випущено — менеджер надсилає PDF вручну у WhatsApp.

**2. Per-shipment P&L невидимий до закриття рахунку**
Buying rates вводяться коли приходить інвойс від перевізника (2-4 тижні після відправки). До цього моменту менеджмент не знає, чи прибуткова відправка. Margin leakage — типова проблема.

**3. Ручна підготовка документів**
Commercial Invoice, Packing List, Bill of Lading, Air Waybill, Certificate of Origin, Customs Declaration — всі готуються вручну або copy-paste з попередніх відправок. Помилки в документах → затримки на митниці → штрафи/demurrage.

**4. Vendor invoice matching — кошмар**
Рахунки від 10-15 vendors на одну відправку (перевізник, агент, склад, митник, страховик). Зіставлення з буккінгом і P&L — ручний процес у 1С або Excel. Переплати та дублі — звичайне явище.

**5. Мультивалютність без автокурсу**
Buying у USD або CNY, selling у EUR/USD/UAH. Курсові різниці вливаються у P&L непрозоро. У 1С мультивалюта є, але налаштована погано або не автоматизована.

**6. Відсутність клієнтського порталу / видимості**
Клієнти постійно питають: «Де мій вантаж?» Без автоматичного трекінгу менеджери витрачають 30-40% часу на статусні апдейти. Це гостро для клієнтів у Європі (інший часовий пояс).

**7. Compliance документація для drone components — не систематизована**
End-User Certificates, export licenses, dual-use classifications — зберігаються у папках на диску, не прив'язані до відправки в системі. При аудиті або запиті — пошук займає години.

**8. Відсутність систематизації закупівельних маршрутів (Procurement)**
Якщо SUPPLYCHAINS виступає як sourcing agent (закупівлі в Азії) — є invoicing від азійських постачальників, QC-контроль, консолідація на складі в HK/Shanghai, і лише потім відправка. Цей procurement цикл зазвичай веде менеджер у Excel окремо від операційного трекінгу.

---

## Сезонність та ключові події

**Chinese New Year (Lunar New Year) — лютий (±2 тижні)**
Найбільш критична пауза в році. Фабрики в Китаї закриті 2-4 тижні. Попит на freight стрибає перед святами (rush shipments), потім — «голод» протягом свят і backlog після. Для клієнтів у Європі — обов'язково планувати запаси. Для freight forwarder — пік операційного навантаження у грудні-січні, потім провал.

**Golden Week (жовтень, 1-7 жовтня)**
Ще одна пауза в Китаї. Менший вплив, ніж CNY, але порушує routing і буккінги.

**Pre-Christmas rush (жовтень-листопад)**
Пік попиту на air freight з Азії до Європи/США для e-commerce та retail. Ставки на air cargo злітають у 2-3 рази. Для клієнтів з drone components — якщо є B2C або retail кінцевий ринок, це критично.

**Peak season ocean freight (серпень-жовтень)**
Традиційно найдорожчий період для ocean freight перед різдвяним сезоном. Space allocation стає проблемою на популярних маршрутах Азія-Європа.

**Геополітичні disruptions (постійний фактор)**
Червоне море/Суецький канал — з 2024 року суттєвий detour через мис Доброї Надії (+10-14 днів, +20-30% вартість). Війна в Україні → відсутність авіатранзиту через РФ (актуально для маршрутів Азія-Україна/Польща). Для SUPPLYCHAINS — це operational reality, яку система має відображати у transit time estimates та routing варіантах.

---

## Рівень цифрової зрілості

**Що використовує enterprise / mid-market:**
- **CargoWise One (WiseTech Global)** — де-факто стандарт для mid-large freight forwarders. Має власний TMS, customs module, accounting, tracking. Дорого, складно, але глибоко заточено під галузь.
- **Magaya** — популярний у США та Latam SMB ринку. Має shipment management, warehouse, accounting.
- **Freight2020 / Softlink Logi-Sys** — популярні в Азії та Близькому Сході.
- **GoFreight** — хмарний SaaS для SMB freight forwarders, набирає популярність в Азії.
- **iCargoSoft, Cargolink** — нішеві HK/China-орієнтовані рішення.

**Що домінує у SMB (таких як SUPPLYCHAINS):**
- **1С (1C:Підприємство)** — типово для пострадянських ринків та компаній з українськими/CIS засновниками або клієнтами. Закрита архітектура, погана підтримка multi-currency автоматизації, немає нативного shipment tracking.
- **Microsoft Excel / Google Sheets** — паралельно з будь-якою системою. Ніколи повністю не зникає.
- **WhatsApp / WeChat** — для координації з агентами в Азії. Де-факто операційний інструмент.
- **QuickBooks / Xero** — у деяких HK-орієнтованих компаніях для бухгалтерії.

**Висновок по SUPPLYCHAINS:** Класичний кейс: 1С для фінансів, Excel для операцій, WhatsApp для комунікації. Odoo — реалістична альтернатива, якщо правильно побудувати shipment management layer.

---

## Модулі Odoo для галузі

| Процес | Модуль Odoo | Пріоритет |
|--------|-------------|-----------|
| Управління продажами / котирування клієнтам | Sales (+ custom pricelist по маршрутах) | Критичний |
| Управління закупівлями у vendors (freight, handling) | Purchase | Критичний |
| Фінансовий облік, multi-currency, AP/AR | Accounting / Invoicing | Критичний |
| Управління контактами (клієнти, vendors, агенти, перевізники) | CRM / Contacts | Критичний |
| Трекінг відправок (custom shipment job/file) | Project або Custom Module | Критичний |
| Складська обробка (receiving, consolidation, release) | Inventory / WMS | Середній |
| Документообіг (B/L, AWB, C/O, packing lists) | Documents + custom templates | Середній |
| Закупівлі товарів в Азії для клієнтів (sourcing) | Purchase + Inventory | Середній |
| Страхування вантажів (полісоутворення, claims) | Custom або підключення до страхового API | Низький |
| HR / timesheet для команди | HR / Timesheets | Низький |
| Аналітика per-shipment P&L, margin reporting | Reporting / BI (Odoo Studio або зовнішній BI) | Критичний |
| Клієнтський портал / трекінг для клієнтів | Website Portal / Custom | Середній |

### Специфічні модулі та кастомізації

**Shipment Card (Custom Object) — архітектурний must-have:**
У Odoo немає нативного «shipment job». Найпоширеніший підхід — кастомна модель `freight.shipment` (або адаптація `project.project` + `project.task`) з полями: mode (air/ocean/road/rail), origin/destination port, carrier, MAWB/HAWB або MBL/HBL номери, Incoterms, commodity, gross weight, volume (CBM), ETD/ETA, customs status, documents checklist. Одна відправка = один record, до якого прив'язані Sale Order (selling side) і Purchase Orders (buying side від кожного vendor).

**Freight Rate Management:**
Ставки перевізників — динамічні, термінові (зазвичай 30-90 днів). Потрібен або custom pricelist mechanism, або окрема модель `freight.rate` з carrier, origin, destination, validity, surcharges (BAF, CAF, PSS, THC). Без цього менеджери продовжать вести ставки в Excel.

**Multi-leg Shipment Support:**
Реальна відправка може мати кілька плечей: truck pickup → CFS → ocean vessel → transhipment port → destination port → local delivery. Архітектура має це враховувати (або як sub-tasks, або як окремі leg-записи).

**Carrier Integrations:**
Автоматичний трекінг через carrier API (наприклад, SeaRates, project44, CargoX) або EDI-повідомлення від перевізників. З коробки Odoo цього не має — потрібна інтеграція або custom cron job для парсингу tracking updates.

**Customs Documentation Templates:**
Автогенерація Packing List, Commercial Invoice, Certificate of Origin з даних відправки через QWeb-шаблони Odoo. Зменшує час підготовки документів з 1-2 годин до 10-15 хвилин.

**Sanctions Screening:**
Custom check при створенні/зміні контрагента або відправки проти OFAC SDN, EU consolidated list, UN sanctions. Може бути або manual checklist, або інтеграція з compliance API (наприклад, Dow Jones, Refinitiv World-Check).

### Червоні прапорці scope

- **«Нам потрібен трекінг-портал для клієнтів»** → Це окремий модуль розробки (customer portal + real-time tracking API). Може подвоїти бюджет фронт-енд частини.
- **«У нас є склад у Shanghai/HK»** → Повноцінний WMS (Barcode scanning, lot/serial tracking, putaway rules) — окремий scope, не включений у базовий freight forwarder setup.
- **«Ми хочемо EDI з нашими перевізниками»** → EDI (EDIFACT IFTMIN/IFTSTA або CargoWise XML) — окрема інтеграційна робота.
- **«Customs module для HK/UA/PL/ES»** → Кожна країна — окрема кастомізація декларацій. Зазвичай краще інтегруватися з existing customs software ніж будувати в Odoo.
- **«Ми виставляємо консолідовані рахунки раз на місяць»** → Billing consolidation logic — нестандартна для Odoo і потребує custom module.
- **«Нам потрібна мультикомпанійна структура» (HK + Shanghai entity)** → Odoo Multi-company є, але inter-company transactions у logistics (shared shipments, cost allocation між юрисдикціями) — складний кейс.
- **«Хочемо аналітику по маршрутах, перевізниках, commodity»** → Стандартний Odoo reporting слабкий для logistics BI. Може знадобитися Metabase, Power BI або Odoo Studio dashboards як окрема робота.

---

## Регуляторні вимоги

### Локалізація Odoo для Hong Kong

Hong Kong не має складної бухгалтерської локалізації (немає VAT у класичному розумінні, хоча є GST для деяких операцій). Основні вимоги:
- **Multi-currency** — обов'язково (HKD, USD, CNY, EUR, UAH, PLN). Odoo підтримує нативно, але потрібно налаштувати auto-rate update (ECB, fixer.io або bank feed).
- **Multi-language** — English (офіційна) + Спрощений китайський (для Shanghai office та комунікації з китайськими партнерами).
- **Hong Kong Companies Ordinance** — базові вимоги до фінансової звітності, які Odoo Accounting покриває стандартно.
- **Profits Tax** — 16.5% для юридичних осіб. Odoo Accounting стандартно підтримує, не потрібна специфічна локалізація.
- **Stamp Duty** — для певних документів (не критично для freight операцій).

### Галузева регуляторика

**Incoterms 2020:**
Умови постачання (EXW, FOB, CIF, DAP, DDP тощо) визначають відповідальність сторін і страховий ризик. Мають бути полем у кожній відправці та впливати на документи (Commercial Invoice обов'язково містить Incoterms). Odoo Sales має поле Incoterms — переконайтеся, що воно пов'язане з shipment card.

**IATA Dangerous Goods Regulations (DGR) — для air freight:**
Якщо SUPPLYCHAINS перевозить drone batteries (LiPo/Li-Ion) авіа — це клас 9 небезпечних вантажів (UN3480, UN3481). Потрібні: Shipper's Declaration for Dangerous Goods, спеціальне пакування за PI 965/966/967, обмеження по State of Charge (SOC ≤30%). Авіакомпанії можуть відмовити у прийманні без правильної документації. Система має мати DG flag та checklist.

**IATA Air Waybill (AWB) та HAWB:**
AWB є юридичним документом на перевезення. Для House AWB (HAWB) freight forwarder виступає як NVOCC (Non-Vessel Operating Common Carrier) або freight forwarder. Потрібне правильне оформлення — система має генерувати або зберігати AWB номери.

**Bill of Lading (B/L) для ocean:**
Master B/L (від ocean carrier) vs. House B/L (від freight forwarder). Negotiable vs. Surrendered B/L — критично для payment terms клієнта. Система має відстежувати тип і статус B/L.

**Export Controls:**
- **Wassenaar Arrangement** — міжнародний режим контролю за товарами подвійного використання. Drone components часто підпадають.
- **US Export Administration Regulations (EAR)** — якщо товар містить US-origin technology або software >25% de minimis, EAR застосовується навіть для re-export з HK.
- **EU Dual-Use Regulation (EU 428/2009, оновлення 2021)** — для відправок до/через ЄС.
- **Hong Kong Import and Export Ordinance (Cap. 60)** — стратегічні товари потребують export licence від HKEC (Hong Kong Export Controls).

**Sanctions Compliance:**
OFAC (США), EU Consolidated Sanctions List, UN Security Council, UK OFSI. Для маршруту Азія → Україна — особлива увага до RU/BY sanctions у транзитних сценаріях.

### Специфіка drone components / dual-use items

**Класифікація товарів:**
Drone components можуть підпадати під різні export control classifications:
- ECCN (Export Control Classification Number) для US EAR: наприклад, 7A994 (інерціальні системи навігації), 7E994 (software для UAV), 3A001 (електронні компоненти)
- EU CCN (Combined Nomenclature): 8806 (UAV та їхні частини)
- HS codes мають бути правильно класифіковані — помилкова класифікація = митні проблеми

**End-User Certificate (EUC / EUS):**
Для товарів подвійного використання перевізник/експортер зобов'язаний отримати від кінцевого покупця письмове підтвердження цільового використання та зобов'язання не re-export без дозволу. Система має зберігати EUC як attachment до shipment або контрагента.

**Red Flag Indicators (що система має допомагати відстежувати):**
- Кінцевий покупець відмовляється вказувати end-use
- Незвичайні умови оплати або anonym payment routing
- Destination країни з обмеженим експортним режимом
- Прохання не вказувати реальний опис товару в документах

**Практичне рішення в Odoo:**
- Поле `dual_use_flag` на product та на shipment
- Checklist at shipment closing: EUC received? Export license required? Sanctions screening done?
- Document attachment для export licenses та EUC
- Audit trail: хто і коли виконав compliance check

---

## Питання для кік-офу

→ **Як зараз влаштований «файл відправки» у вашій роботі — де живе вся інформація по конкретному shipment?**
Навіщо: Розуміємо поточний операційний процес і де саме болить. Більшість скаже: «частково в 1С, частково в Excel, частково в голові менеджера».

→ **Скільки активних відправок одночасно веде один менеджер і скільки відправок на місяць загалом?**
Навіщо: Визначаємо навантаження на систему і складність трекінгу. Від цього залежить, чи потрібен full TMS чи достатньо lightweight shipment module.

→ **Як ви зараз розраховуєте прибутковість по конкретній відправці? Коли ви дізнаєтесь, що відправка була збитковою?**
Навіщо: Ключова pain point. Якщо відповідь «коли закриємо всі інвойси від vendors» — значить per-shipment P&L в реальному часі відсутній, і це один з головних business cases для системи.

→ **Які операції ви виконуєте як sourcing/procurement agent (закупівлі в Азії)? Чи є консолідація вантажу на вашому складі в HK або Shanghai?**
Навіщо: Визначаємо scope: чи потрібен повноцінний Inventory/WMS модуль, чи лише трекінг freight без фізичного складу.

→ **Як зараз обробляється compliance для drone components: хто перевіряє санкційні списки, де зберігаються End-User Certificates, чи є процедура для dual-use screening?**
Навіщо: Критично для scope. Якщо відповідь «вручну» або «не знаємо» — compliance module обов'язковий і потенційно розширює scope. Також виявляємо compliance ризики, які клієнт може не усвідомлювати.

→ **Хто ваші основні клієнти зараз — це одні й ті ж компанії (regular accounts) чи mix регулярних та spot shipments?**
Навіщо: Визначаємо, чи потрібна повноцінна CRM-воронка, чи достатньо account management. Regular accounts → contract rates у системі. Spot → потрібен flow для quick quoting.

→ **Скільки різних vendors (carriers, agents, brokers) ви використовуєте регулярно і по яких маршрутах?**
Навіщо: Розуміємо складність vendor management і потребу в rate cards. Якщо 50+ vendors — потрібна vendor portal або інтеграція. Якщо 10-15 — достатньо manual entry.

→ **Яка структура компанії з юридичної точки зору: одна HK entity, чи є Shanghai entity, і як між ними проходять транзакції?**
Навіщо: Multi-company setup у Odoo — значно складніший і дорожчий. Якщо Shanghai — окрема юрособа з окремим P&L, scope збільшується суттєво.

→ **Які країни і митні режими ви обробляєте: де ви виступаєте як customs broker, а де передаєте митне оформлення місцевому агенту?**
Навіщо: Визначаємо, чи потрібна customs declaration functionality в Odoo чи лише документальний трекінг. Customs software (e.g., ASM Sequoia для UA, KUSAM для PL) зазвичай окрема система.

→ **Яка пріоритетність для вас: фінансовий облік (замінити 1С як бухгалтерію) чи операційний трекінг відправок, чи обидва завдання рівнозначні?**
Навіщо: Визначаємо MVP scope. Якщо пріоритет — бухгалтерія, починаємо з Accounting + Purchase + Sales. Якщо операції — починаємо з shipment management. Спроба зробити все одразу в SMB-бюджеті → провал проекту.

---

## Чого НЕ чекати від цього брифінгу

- **Це не технічне завдання і не пропозиція.** Брифінг описує галузь і типові сценарії — реальні вимоги SUPPLYCHAINS з'ясовуються на кік-офі та в процесі discovery.
- **Процеси SUPPLYCHAINS можуть суттєво відрізнятися від типових.** Компанія спеціалізується на специфічній нішевій комбінації (drone components + Азія-Схід Европа). Це може означати унікальні workflow, яких немає в галузевих шаблонах.
- **Брифінг не замінює технічний аудит 1С.** Перед міграцією потрібно зрозуміти, що саме зберігається в 1С: дані клієнтів, фінансова історія, відкриті зобов'язання. Міграція даних — окремий workstream.
- **Оцінки модулів і складності — орієнтовні.** Реальна трудомісткість кастомізацій (особливо shipment card і compliance) залежить від глибини вимог, яку визначить discovery.
- **Regulatory landscape змінюється швидко.** Export controls для drone technology активно оновлювалися у 2023-2026. Конкретні вимоги потрібно верифікувати з compliance-спеціалістом або юристом, а не покладатися лише на цей брифінг.
- **Одoo не є прямою заміною CargoWise або Magaya.** Odoo — це ERP з можливістю кастомізації під logistics. Для компанії, яка росте понад 20-30 осіб, може знадобитися перехід на dedicated TMS. Це треба відверто проговорити з клієнтом як частину довгострокової roadmap.
