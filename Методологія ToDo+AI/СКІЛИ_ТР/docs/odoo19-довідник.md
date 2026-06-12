# Довідник Odoo 19 (офіційна документація) — для написання ТР

Виведено з офіційної документації Odoo 19.0 (developer reference). Це джерело правди по технічних
механізмах: коли в ТР пишеш реалізацію, звіряйся тут, щоб синтаксис і назви були актуальні для v19.
Усі проекти ToDo на Odoo ≥18 (Elfa/ДЕМЗ — 19, Олімпіус/RSE — 18), тож правила v17+ діють скрізь.

## Зміст
1. Критичні зміни v17+/19 (часті анахронізми)
2. Моделі
3. Поля та їх атрибути
4. Computed / related / обмеження
5. Представлення (views)
6. Безпека (права + record rules)
7. Дії, меню, cron, послідовності
8. QWeb та друковані звіти
9. Домени
10. Mail / Activity / Chatter
11. Automation Rules (base.automation)
12. res.config.settings (налаштування)
13. Web / Portal / OWL
14. Окруження / контекст
15. Зовнішній API (v19)

---

## 1. Критичні зміни v17+/19 — НЕ писати по-старому
Це найчастіші анахронізми; у ТР під Odoo 19 використовуй лише правий стовпець:

| Було (≤16) | Odoo 17+/19 (писати так) |
| :-- | :-- |
| `<tree>` | **`<list>`** (tree лишився для сумісності, але не використовувати) |
| `attrs="{'invisible': [domain]}"` | пряме `invisible="<python-вираз>"` |
| `attrs="{'required': [...]}", `states="..."` | `required="<вираз>"`, `readonly="<вираз>"`, видимість по статусу — `invisible="state not in (...)"` |
| (немає) приховати колонку списку | `column_invisible="<вираз>"` (тільки в `<list>`) |
| `t-raw` | **`t-out`** (`t-raw` deprecated з 15.0; для HTML — `t-out` зі значенням `markupsafe.Markup`) |
| `t-esc` | працює як аліас `t-out`; пиши `t-out` |
| `group_operator` | **`aggregator`** (перейменовано в 17.2) |
| `name_get()` | читати `display_name` (name_get deprecated) |
| `_sql_constraints` (кортежі) | працює; але v18.1+ — декларативні `models.Constraint`/`models.Index`/`models.UniqueIndex` |
| `read_group` | `_read_group` (backend) / `formatted_read_group` (публічний) |

## 2. Моделі
- Типи: `models.Model` (постійна), `models.AbstractModel` (mixin), `models.TransientModel` (wizard,
  автоочистка).
- Атрибути: `_name`, `_description`, `_inherit`, `_inherits` ({model: field_id} — делегування,
  методи НЕ наслідуються), `_order`, `_rec_name` (за замовч. `name`), `_table`, `_parent_name`
  (за замовч. `parent_id`), `_parent_store` (для child_of/parent_of), `_check_company_auto`.
- Наслідування: класичне (`_name`+`_inherit`), extension/in-place (`_inherit` без `_name` — розширює
  модель на місці), delegation (`_inherits`). У ТР для кастомних моделей — префікс `td.` (`td.listing`).
- Авто-поля: `id`, `display_name`, `create_date/uid`, `write_date/uid`. Зарезервовані зі спецповедінкою:
  `name`, `active` (False → приховано), `state`, `parent_id`, `company_id`.

## 3. Поля та їх атрибути
**Типи:** Char (`size`,`trim`,`translate`), Text, Html (`sanitize`), Boolean, Integer, Float
(`digits`), Monetary (`currency_field`, за замовч. `currency_id`), Date, Datetime (UTC), Binary
(`attachment`), Image (`max_width/height`), Selection (`selection`, `selection_add` при `_inherit`),
Many2one (`comodel_name`, `ondelete` set null/restrict/cascade), One2many (`comodel_name`,
`inverse_name`), Many2many (`relation`,`column1/2`), Reference, Json.
**Запис у O2m/M2m через `Command`:** `Command.create/update/delete/unlink/link/set/clear`.
**Атрибути:** `string`, `required`, `readonly`, `default` (скаляр або callable), `help`, `index`,
`copy`, `groups` (field-level доступ), `tracking` (чатер), `compute`, `inverse`, `search`, `related`,
`store`, `depends`, `compute_sudo`, `aggregator` (sum/avg/min/max/count…), `domain`, `context`.

## 4. Computed / related / обмеження
- **Computed:** `compute='_method'` + `@api.depends(...)`; за замовч. не зберігається і readonly;
  `store=True` — зберігати+шукати+групувати; `inverse=` — дозволити запис; кілька полів — один метод.
- **Related:** `related='a.b.c'`; автокопіює string/help/required/… ; `store=True` за потреби.
- **Обмеження:** `@api.constrains('field')` → `ValidationError`; SQL — `models.Constraint("CHECK(...)","msg")`
  або (старе) `_sql_constraints`; унікальність — `models.UniqueIndex`/`models.Index`.
- **Onchange (тільки UI):** `@api.onchange('field')`; може повертати `{'warning': {...}}`.
- **Create:** перевизначай через `@api.model_create_multi` (vals_list — список).
- **Помилки:** `ValidationError`, `UserError`, `AccessError`, `MissingError`, `RedirectWarning`.

## 5. Представлення (views)
- Типи: `<form>`, **`<list>`** (не `<tree>`!), `<kanban>`, `<search>`, `<pivot>`, `<graph>`,
  `<calendar>`, `<activity>`, `<gantt>` (Ent), `<map>` (Ent), `<cohort>` (Ent), `<qweb>`.
- **Умовна логіка — прямими атрибутами з Python-виразом** (НЕ `attrs`/`states`):
  `invisible="state == 'done'"`, `required="product_type == 'service'"`,
  `readonly="state in ('sale','done')"`, `column_invisible="parent.x != y"` (лише в `<list>`).
  У виразі доступні поля поточного запису, `uid`, `context`.
- Віджети: `widget="..."` (monetary, many2many_tags, statusbar+`statusbar_visible`, image, priority,
  handle, html, badge…).
- Декорації рядків списку: `decoration-danger/warning/success/info/muted/primary="<вираз>"`;
  `<list editable="top|bottom">`.
- Search: `<filter domain=... />`, `<separator/>` (OR), `group_by` через `context`, `<searchpanel>`;
  дефолти — `search_default_<name>` у контексті дії.
- Наслідування: `inherit_id` + `<xpath expr=".." position="after|before|inside|replace|attributes"/>`
  або `<field name=".." position="..">`; зміна атрибутів — `position="attributes"` +
  `<attribute name="readonly">expr</attribute>`.

## 6. Безпека (права + record rules)
- **Групи `res.groups`:** `category_id`, `implied_ids` (псевдо-наслідування). Уся безпека — на групах.
- **ACL `ir.model.access`** (CSV у `security/`): `model_id:id`, `group_id:id` (порожня → усім),
  `perm_read/write/create/unlink` (0/1). Аддитивні (union по групах).
- **Record rules `ir.rule`:** `domain_force`, `groups` (порожні → глобальне правило), `perm_*` (при
  яких операціях правило перевіряється). Комбінування: **глобальні правила — AND (звужують);
  правила груп — OR (розширюють); глобальний і груповий набори між собою — AND.** Змінні в домені:
  `user`, `company_id`, `company_ids`, `time`. (Архетип #28 — приклади.)
- **Field-level:** атрибут поля `groups="mod.group_a,mod.group_b"` — інакше поле прибирається з UI/API.

## 7. Дії, меню, cron, послідовності
- **`ir.actions.act_window`:** `res_model`, `view_mode` (`list,form,…`), `views`, `domain`, `context`,
  `target` (current/new/fullscreen/main), `search_view_id`, `limit`. Прив'язка в меню моделі —
  `binding_model_id` + `binding_type` (action/report) + `binding_view_types` (list,form).
- **`ir.actions.server`:** `state` = code/object_create/object_write/multi; у `code` доступні
  `model`,`record(s)`,`env`,`log`; якщо задано `action` — повертається клієнту.
- **`ir.actions.client`** (`tag`,`params`), **`ir.actions.act_url`** (`url`,`target`).
- **Меню `<menuitem>`:** `parent`, `action`, `sequence`, `groups` (префікс `-` прибирає групу).
- **`ir.cron`:** `model_id`+`code` (`model.method()`), `interval_number/type`, `nextcall`. v19:
  батч-прогрес `IrCron._commit_progress(processed, remaining=...)` — фреймворк сам повторює виклик;
  політика: 3 помилки поспіль → пропуск, 5 за 7 днів → деактивація. (Архетипи ir.cron — #2,18,etc.)
- **`ir.sequence`:** `prefix`/`suffix`/`padding`/`number_increment`; напр. `INV/%(year)s/` + padding 4.

## 8. QWeb та друковані звіти
- **Директиви:** `t-out` (вивід, екранує; для HTML — Markup), `t-field` (поле smart-record,
  `t-options='{"widget":"monetary","display_currency":o.currency_id}'`), `t-if/t-elif/t-else`,
  `t-foreach="…" t-as="o"` (+ `o_index/o_first/o_last/o_size`), `t-att-x`/`t-attf-x`/`t-att="{...}"`,
  `t-call="tmpl"` (тіло → змінна `0`), `t-set`/`t-value`. **Не використовувати `t-raw`.**
- **Звіт `ir.actions.report`:** `report_name` (external id шаблону), `report_type` (`qweb-pdf`/`qweb-text`),
  `model`, `paperformat_id`, `print_report_name` (python), `binding_model_id` (→ кнопка «Друк»),
  `attachment`/`attachment_use`. Shorthand — тег `<report .../>`.
- **Структура шаблону:** `t-call="web.html_container"` → `t-foreach="docs" t-as="o"` →
  `t-call="web.external_layout"` (шапка/підвал компанії) → `<div class="page">…</div>`. Контекст:
  `docs`, `doc_ids`, `doc_model`, `user`, `res_company`, `web_base_url`.
- **Мова партнера:** `t-lang="doc.partner_id.lang"` на `t-call` + у шаблоні
  `t-set="doc" t-value="doc.with_context(lang=…)"`.
- **`report.paperformat`:** `format` (A4/custom…), `orientation`, `margin_*`, `dpi`, `header_line`.
- **Кастомний звіт:** `AbstractModel` `report.<module>.<name>` з `_get_report_values(docids, data)`.
- Штрих-код у звіті: `<img t-att-src="'/report/barcode/QR/%s' % value"/>`.
(Структура спеца друкованої форми — `друковані-форми.md`.)

## 9. Домени
- Класична форма: `[('field','op',value), …]` з префіксами `'&' '|' '!'`. Новий API (v18.1+):
  `from odoo.fields import Domain` → `Domain('a','=',1) & Domain('b','ilike','x')`, `~d`, `Domain.AND/OR`.
- Оператори: `= != > >= < <= =? like ilike =like in not in child_of parent_of any not any`.
- Гранулярність дат (17.3+): `field.month_number`, `year_number`, `day_of_week`… .
- **Динамічні дати (v19):** `Domain('date','<','now')`, `'today'`, `'-3d +1H'`, `'=monday -1w'`
  (одиниці d/w/m/y/H/M/S; операції + - =).

## 10. Mail / Activity / Chatter
- **`mail.thread`** (mixin): `_inherit=['mail.thread']`; у form — `<chatter/>`. Методи: `message_post(body,
  subject, message_type, attachments, …)` (body = str або `markupsafe.Markup` для HTML),
  `message_subscribe/unsubscribe(partner_ids)`, `message_post_with_template(template_id)`, `_track_subtype`.
- **Tracking:** `field = fields.X(tracking=True)` → зміна пишеться нотаткою в чатер.
- **Контекст-ключі:** `mail_create_nosubscribe`, `mail_create_nolog`, `mail_notrack`, `tracking_disable`.
- **`mail.activity.mixin`:** `_inherit=['mail.thread','mail.activity.mixin']`; поле `activity_ids`; метод
  **`activity_schedule(act_type_xmlid, date_deadline, summary, user_id=…)`**. Модель `mail.activity`:
  `activity_type_id`, `summary`, `date_deadline`, `user_id`, `res_model`/`res_id`, `note`. Віджети
  `mail_activity`/`kanban_activity`. (Архетипи #11, #18.)
- **`mail.template`:** `model_id`, `subject`/`body_html` (QWeb-рендер, доступний об'єкт `object`),
  `email_from/to`, `partner_to`, `attachment_ids`, `report_template_ids` (динамічні звіти-вкладення),
  `scheduled_date`, `email_layout_xmlid`; методи `send_mail(res_id)`/`send_mail_batch(res_ids)`. (Архетип #19.)

## 11. Automation Rules (`base.automation`) — no-code автоматизації
Часто простіша альтернатива кастному коду для автоматизацій стадій/CRM (#16, #32). У ТР вкажи: модель,
тригер, домен, дію.
- **Поля:** `model_id`, `trigger`, `filter_pre_domain` (умова ДО запису), `filter_domain` (умова ПІСЛЯ),
  `action_server_ids` (O2m → `ir.actions.server`), `trigger_field_ids`, `trg_date_*` (time-based), `active`.
- **Тригери:** `on_create` / `on_create_or_write` / `on_unlink` / `on_change` (тільки дія-code) /
  `on_stage_set` / `on_state_set` / `on_user_set` / `on_tag_set` / `on_priority_set` / `on_archive` /
  `on_time` / `on_time_created` / `on_time_updated` / `on_message_received` / `on_message_sent` /
  `on_webhook` (POST на `/web/hook/<uuid>`). `on_write` — **deprecated → `on_create_or_write`**.
- **Дії (`ir.actions.server.state`):** `code`, `object_write`, `object_create`, `mail_post`, `followers`,
  `next_activity`, webhook; v19 додано AI/Sequence/WhatsApp.
- **Time-based:** працює через cron; після створення правила запусти cron, щоб ініціалізувати `last_run`
  (інакше обробить ретроспективні записи).

## 12. `res.config.settings` — сторінки налаштувань
- TransientModel. Конвенції полів: `default_X` (+атрибут `default_model='my.model'`) → дефолт через
  `ir.default`; `group_X` (Boolean/selection, +`implied_group='xmlid'`) → додає/прибирає групу;
  `module_X` → встановлює модуль; будь-яке поле + **`config_parameter='ключ'`** → `ir.config_parameter`;
  інші — обробляй у `set_values()`/`get_values()`. Пер-компанійні — `related='company_id.field'`. Зберігає
  лише адмін. (Архетип #33 і будь-яке «Налаштування модуля».)
- **`ir.config_parameter`:** `sudo().get_param('key', default)` / `set_param('key', value)` (значення — рядок).
- **`ir.default`:** глобальні дефолти полів моделей.

## 13. Web / Portal / OWL
- **Контролери:** `class C(http.Controller)` + `@http.route(route, auth='user|public|none|bearer',
  type='http|jsonrpc', methods=[…], website=True, csrf=True)`. Об'єкт `request`: `env`, `params`,
  `render(tmpl, vals)`, `redirect`, `make_response`, `session`. **v19:** `type='json'`→**`'jsonrpc'`**;
  новий `auth='bearer'`. Перевизначення контролера — обов'язковий `@route()`, інакше маршрут знімається.
- **Portal (#13):** базовий `CustomerPortal` (`portal.controllers.portal`), маршрути `/my/...`
  (`auth='user'`, `website=True`), `_prepare_portal_layout_values()`, контроль доступу
  (`record.partner_id == request.env.user.partner_id` або `sudo()` з явною перевіркою); шаблони наслідують
  `portal.portal_layout`.
- **OWL/JS (рівень ТР, #30):** веб-клієнт на OWL; компоненти реєструються в `registry` (категорії
  `actions`/`fields`/`views`/`services`); сервіси через `useService('orm'|'rpc'|'notification'|'action'|'user')`.
  Barcode App — окремий OWL-клієнт (`@stock_barcode`); кастомізація через `patch()` або нові компоненти.

## 14. Окруження / контекст
- `env`: `env.user/uid/company/companies/context/lang/cr`; `env.ref('module.xmlid')`; `env['model'].browse/search`.
- Зміна середовища: `with_context(**)`, `sudo()` / `sudo(False)`, `with_company(c)`, `with_user(u)`, `with_env`.
- `env.is_admin()/is_system()/is_superuser()`; raw SQL — `env.execute_query(SQL(...))` + `flush_model`/`invalidate_model`.

## 15. Зовнішній API (v19 — велика зміна)
- **v19: новий endpoint `/json/2/<model>/<method>`** + аутентифікація через **API Key (Bearer)** —
  без login/uid/password. Старі `/xmlrpc`, `/xmlrpc/2`, `/jsonrpc` — **deprecated** (видалення у v22).
- Запит: `POST`, header `Authorization: bearer <KEY>`, тіло — JSON з **іменованими** параметрами
  (`domain`, `fields`, `ids`, `context`); за потреби header `X-Odoo-Database`.
- Методи: `search`→ids; `read`/`search_read`→list[dict]; `create`/`write`/`unlink`; бізнес-методи
  (`action_confirm`). Кожен виклик = окрема транзакція. ACL/record rules/field access діють повністю —
  для інтеграцій створюй bot-користувача з мінімальними правами.
- Внутрішні контролери `type='jsonrpc'` (колишній `'json'`) під це deprecation НЕ підпадають.
- **Для нових інтеграцій/обмінів у v19 (див. `звіти-та-обміни.md`) — `/json/2` + Bearer.**
