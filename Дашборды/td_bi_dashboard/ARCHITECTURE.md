# Architecture: td_bi_dashboard   (Odoo 19, моделі td.*)
Generated from SPEC.md (approved) — 2026-06-13

## File structure

Повне дерево каталогів модуля `td_bi_dashboard` (Odoo 19, автор ToDo, Since 19.0.1.0.0). Один `.py` на кожну з 24 моделей `td.bi.*` + окремий файл адаптера `td.bi.query.compiler`. Усі шляхи відносні до кореня модуля.

```
td_bi_dashboard/
├── __init__.py                              # from . import models, controllers
├── __manifest__.py                          # depends/assets/data/demo (див. Dependencies)
│
├── models/
│   ├── __init__.py                          # імпорт усіх 26 .py нижче (порядок: спочатку dataset/field, далі залежні)
│   ├── bi_dataset.py                        # td.bi.dataset  (run_query, get_fields_tree, validate_integrity, version)
│   ├── bi_dataset_field.py                  # td.bi.dataset.field  (_compute_formula_compiled, _sql_constraints name_uniq_per_dataset)
│   ├── bi_dataset_join.py                   # td.bi.dataset.join  (бленд: source_dataset_id/source_model_id, join_type)
│   ├── bi_dataset_join_key.py               # td.bi.dataset.join.key  (пари left_field=right_field)
│   ├── bi_measure.py                        # td.bi.measure  (expression / field_id+aggregator, show_as, time_intelligence)
│   ├── bi_parameter.py                      # td.bi.parameter  (_sql_constraints one_owner — dataset XOR dashboard)
│   ├── bi_dashboard.py                      # td.bi.dashboard  (mail.thread; action_publish, get_runtime_config, action_open, copy, render_snapshot)
│   ├── bi_dashboard_access.py               # td.bi.dashboard.access  (viewer/editor/manager; exactly_one_subject)
│   ├── bi_dashboard_page.py                 # td.bi.dashboard.page  (вкладки, drill-through)
│   ├── bi_widget.py                         # td.bi.widget  (~28 widget_type; config data/style/interactions)
│   ├── bi_control.py                        # td.bi.control  (control_type, scope dashboard/page/group, cascade)
│   ├── bi_control_mapping.py                # td.bi.control.mapping  (field_path per-датасет, enabled)
│   ├── bi_theme.py                          # td.bi.theme  (config палітра/шрифти; company_id; logo)
│   ├── bi_dashboard_state.py                # td.bi.dashboard.state  (bookmark/autosave/personal_default)
│   ├── bi_dashboard_version.py              # td.bi.dashboard.version  (config_snapshot; action_restore_to_draft, action_publish_this)
│   ├── bi_dashboard_tag.py                  # td.bi.dashboard.tag
│   ├── bi_dashboard_group.py                # td.bi.dashboard.group  (розділи каталогу)
│   ├── bi_dashboard_share.py                # td.bi.dashboard.share  (access_token, _compute_full_url, action_revoke)
│   ├── bi_subscription.py                   # td.bi.subscription  (action_send_now, _cron_run_subscriptions)
│   ├── bi_alert.py                          # td.bi.alert  (_cron_check_alerts, action_view_trigger_log)
│   ├── bi_alert_log.py                      # td.bi.alert.log  (журнал спрацювань)
│   ├── bi_cache.py                          # td.bi.cache  (cache_key_uniq; _cron_clear_expired, _build_cache_key)
│   ├── bi_audit_log.py                      # td.bi.audit.log  (event_type; запис системою)
│   ├── bi_materialization.py                # td.bi.materialization  (_auto=False; init, _compute_is_rls_safe, action_refresh/_cron_refresh)
│   ├── bi_query_compiler.py                 # td.bi.query.compiler  (AbstractModel-адаптер; CTE-генератор бленду, formatted_read_group/_grouping_sets, Model._search-обгортка, роутер run_query, DSL-валідація, Domain.AND-склейка)
│   └── res_config_settings.py               # res.config.settings (inherit) — statement_timeout, дефолтні ліміти, CSP frame-ancestors
│
├── security/
│   ├── td_bi_dashboard_security.xml         # 3 групи (group_bi_user→designer→admin, implied-ланцюг) + record rules (§Security SPEC)
│   └── ir.model.access.csv                  # ACL R/W/C/D для 24 моделей × 3 групи (матриця §Security)
│
├── views/
│   ├── bi_dataset_views.xml                 # td.bi.dataset / .field / .join / .join.key / measure / parameter (list+form, вкладки Поля/Бленд/Параметри)
│   ├── bi_dashboard_views.xml               # td.bi.dashboard kanban-каталог + form; .page / .access / .version / .tag / .group; share/subscription/alert
│   ├── bi_dashboard_action.xml              # ir.actions.client (dashboard_action, реєстр actions) для OWL-рендера дашборда
│   ├── bi_subscription_alert_views.xml      # td.bi.subscription / td.bi.alert / td.bi.alert.log (list+form, smart-кнопки)
│   ├── bi_admin_views.xml                   # td.bi.cache / td.bi.audit.log / td.bi.materialization (тільки-читання/адмін)
│   ├── res_config_settings_views.xml        # сторінка налаштувань BI (statement_timeout, ліміти, CSP)
│   └── bi_menus.xml                          # коренева дія/меню BI → Каталог / Датасети / (Налаштування, Аудит)
│
├── data/
│   ├── bi_cron.xml                          # 4× ir.cron: clear_expired_cache(~15хв) / run_subscriptions / check_alerts / refresh_materialization
│   ├── bi_paperformat.xml                   # report.paperformat для PDF-дашборда
│   ├── mail_template_data.xml               # mail.template тіла розсилки підписки/алерта
│   └── bi_theme_data.xml                    # системна тема is_default=True (дефолтна палітра)
│
├── demo/
│   └── bi_demo.xml                          # 2 датасети + 1 дашборд (demo-поставка, §Data & demo)
│
├── controllers/
│   ├── __init__.py                          # from . import main
│   └── main.py                              # /bi/share/<id>/<token>(+/data,/export) auth=public; /bi/embed/<id> auth=public (CSP frame-ancestors); /bi/export/xlsx auth=user readonly; /bi/export/pdf auth=user readonly
│
├── report/
│   ├── bi_dashboard_report.xml              # ir.actions.report (PDF дашборда/сторінки)
│   └── bi_dashboard_templates.xml           # QWeb-шаблони PDF (графіки растром, колонтитул з фільтрами)
│
└── static/
    ├── description/
    │   └── icon.png
    ├── src/
    │   ├── js/
    │   │   ├── components/
    │   │   │   ├── bi_dashboard_action/        # BiDashboardAction (root client action, реєстр actions)
    │   │   │   ├── dashboard_canvas/           # DashboardCanvas (сітка 24 колонки, сторінки/вкладки)
    │   │   │   ├── widget_container/           # WidgetContainer (картка віджета, картка-помилки «повторити», деградація per-віджет)
    │   │   │   ├── widget_renderer/            # WidgetRenderer* — диспетчер + рендерери: KpiCard, TableWidget, PivotWidget (OWL); ChartWidget (Chart.js); GeoWidget/TreemapWidget/MatrixWidget (chart-плагіни)
    │   │   │   ├── control_bar/                # ControlBar + Control* (ControlDateRange, ControlDropdown, ControlHierarchical, ControlNumericRange, ControlParameter…)
    │   │   │   ├── dataset_builder/            # DatasetBuilder (ліниве дерево полів, глибина ≤5, маркер рекурсії, preview)
    │   │   │   ├── blend_editor/               # BlendEditor (таблиці бленду ≤5, join_type left/inner, ключі, попередження ключа)
    │   │   │   ├── formula_editor/             # FormulaEditor (DSL з [псевдонімами], підсвічування помилок валідації)
    │   │   │   ├── domain_editor/              # DomainEditor (DomainSelector/TreeEditor; склейка через Domain.and)
    │   │   │   ├── measure_panel/              # MeasurePanel + QuickMeasureWizard (швидкі міри «% від підсумку», YoY)
    │   │   │   ├── interaction_matrix/         # InteractionMatrix (cross-filter «джерело × приймач»)
    │   │   │   ├── theme_editor/               # ThemeEditor
    │   │   │   ├── share_dialog/               # ShareDialog (viewer/editor/manager, «для всіх співробітників», frozen-посилання)
    │   │   │   ├── subscription_dialog/        # SubscriptionDialog
    │   │   │   ├── version_history/            # VersionHistory (відкат/повторна публікація)
    │   │   │   └── bookmark_bar/               # BookmarkBar (особисті/авторські закладки)
    │   │   ├── services/
    │   │   │   ├── bi_page_state.js            # biPageState (контроли, cross-filter, drill-стек, сторінка, overrides)
    │   │   │   └── bi_data_service.js          # biDataService (черга ≤6 RPC, дебаунс 400мс, скасування, run_query)
    │   │   └── utils/                          # bi_domain.js (Domain.and-склейка), bi_format.js (format_spec), bi_chart_config.js
    │   ├── scss/
    │   │   ├── bi_dashboard.scss               # канва, сітка, картки, ControlBar
    │   │   └── bi_dashboard_print.scss         # стилі PDF/print
    │   └── xml/
    │       ├── bi_dashboard.xml                # OWL-шаблони action/canvas/container/control_bar
    │       ├── bi_widgets.xml                  # OWL-шаблони рендерерів (kpi/table/pivot/text/image)
    │       └── bi_builder.xml                  # OWL-шаблони builder/blend/formula/measure/dialogs
    ├── lib/                                    # вендорені chart-плагіни (ОВ-5; не з npm)
    │   ├── chartjs-chart-geo/                  # хороплет/гео-бульбашки (TopoJSON)
    │   ├── chartjs-chart-treemap/              # treemap
    │   └── chartjs-chart-matrix/              # heatmap (matrix)
    └── tests/
        └── tours/
            └── bi_dashboard_tour.js            # tour-тест UI (стабілізація етапу 1, §Data & demo)
```

**Assets-бандли** (`__manifest__.py` → `assets`):
- `td_bi_dashboard.assets_dashboard` — додається у `web.assets_backend` (lazy-під-бандл): усі OWL-компоненти, services, scss, xml, базовий Chart.js (його тягне `web` — НЕ вендоримо). Завантажується для backend-дій дашборда.
- `td_bi_dashboard.assets_charts_extra` — **lazy** окремий бандл лише з вендореними плагінами `static/lib/*` (geo/treemap/matrix). Підвантажується динамічно (`loadBundle`/`assets.loadBundle`) тільки коли на сторінці є віджет, що його потребує (choropleth/treemap/heatmap/geo_bubble) — щоб не роздувати початковий бандл (бюджет пам'яті ≤300 МБ, AC-47). Джерело: Odoo 19 lazy asset bundles (довідник: web/assets).
- `td_bi_dashboard.assets_public` — для `/bi/share` та `/bi/embed` (`auth='public'`): мінімальний рендер frozen-знімка (рендерери без builder-компонентів), додається у `web.assets_frontend` / окремий public-бандл.
- `td_bi_dashboard.assets_print` — `bi_dashboard_print.scss` для PDF-звіту (бандл звіту).
- `web.assets_tests` — `static/tests/tours/*` (tour).

## Data flows

### (1) Відрисовка віджета — конвеєр `run_query` (§2.4.1 SPEC, ВИМ-46)
1. `WidgetContainer` (OWL) монтується → запитує дані через `biDataService`.
2. `biPageState` віддає поточний стан; `biDataService` будує `query_spec` і **ефективний домен** = `Domain.and([dataset_domain, audience_domain, control_values, cross_filter_domains, widget_domain])`. Record rules у домен **не включаються** (їх додасть ORM). Domain-склейка лише через `Domain.and(...)`, без конкатенації списків (AC-64).
3. `biDataService` ставить запит у чергу (≤6 паралельних RPC, дебаунс 400 мс, скасування незавершених) → RPC `run_query(dataset_id, query_spec)` з контекстом `tz`/`lang`/`allowed_company_ids`.
4. Сервер `td.bi.dataset.run_query`: валідує `query_spec` за JSON-схемою → перевіряє `has_access('read')` → `_build_cache_key()` (SHA-256 з `dataset.version`, нормалізований домен, groupby/aggregates/having/order/limit, **uid-маркер прав**, lang, tz, company_ids) → пошук у `td.bi.cache` (якщо `cache_ttl>0`).
5. Кеш-промах → `td.bi.query.compiler` компілює модель → `formatted_read_group(domain, groupby, aggregates, having, order, limit, offset)` від імені користувача (кілька віджетів одного датасету батчуються в один `formatted_read_grouping_sets`). `statement_timeout` (30 с) ставиться на курсор перед виконанням, скидається після. `formatted_read_group` сам викликає `check_access('read')` і вбудовує домени `ir.rule` у WHERE/підзапити; поля з `groups=` → `AccessError`; **жодного `sudo()`**.
6. Пост-обробка: формули над агрегатами, часовий інтелект (YoY/PoP/rolling), «% від підсумку»/ранги (через GROUPING SETS), мультивалютність (`_convert` для `historical`). Запис у `td.bi.cache` (gzip payload, `expires_at = now + cache_ttl`, `hit_count`).
7. Відповідь повертає точки даних + `__extra_domain` на кожній (для drill/cross-filter). Помилка/таймаут → `UserError` → `WidgetContainer` рендерить картку «повторити» (деградація per-віджет, сторінка живе — AC-49, AC-52).
8. Джерело: Odoo 19 ORM `formatted_read_group`/record rules — довідник: ORM `_read_group`/aggregates; deviation-перевірка точної назви `formatted_read_grouping_sets` на цільовій збірці (SPEC §Build-time confirmations).

### (2) `action_publish` — знімок версії → state (ВИМ-41, AC-25/28)
1. Редактор (`editor`/`manager`) натискає «Опублікувати» (видима за `state=='draft'`).
2. `td.bi.dashboard.action_publish`: серіалізує повну конфігурацію (сторінки/віджети/контроли/тема/`default_state`) у JSON → `create` запис `td.bi.dashboard.version` (`config_snapshot`, `is_published_snapshot=True`, автор/дата = `create_uid`/`create_date`).
3. Знімає `is_published_snapshot` з попереднього, ставить `published_version_id` на новий, перемикає `state='published'`.
4. `viewer` бачить опубліковану версію без кнопки редагування; `editor` далі бачить чернетку. Відкат: `td.bi.dashboard.version.action_restore_to_draft` / `action_publish_this` (повторна публікація старого знімка) — глядач після refresh бачить відкочену версію.

### (3) Frozen-посилання `/bi/share` (consteq → render_snapshot, ВИМ-42a, AC-26/27/30, ОВ-4)
1. Анонім відкриває `/bi/share/<int:share_id>/<token>` (контролер `main.py`, `auth='public'`).
2. Контролер читає `td.bi.dashboard.share` (sudo лише для службового читання запису-посилання, не бізнес-даних) → звірка токена через **`consteq`** (constant-time). Невідповідність → публічна сторінка «посилання недійсне» (НЕ статус-блокування).
3. Перевірки: `active==True`; `expiration_date` не вичерпано (інакше сторінка «термін дії вичерпано»); `password_hash` (якщо заданий); **`with_user(create_uid).has_access('read')`** на дашборд — автор не втратив право (інакше посилання деактивовано, AC-27).
4. Рендер **`snapshot_attachment_id`** (frozen-знімок) — БЕЗ живих запитів до бізнес-моделей. `/bi/share/.../data` віддає вже заморожені точки даних; `/bi/share/.../export` лише якщо `allow_export` ∧ `base.group_allow_export`.
5. Відкликання: `action_revoke` (`active=False`) або архівація дашборда → наступне відкриття того ж URL → «посилання недійсне» (AC-30). Створювати запис може лише `group_bi_admin`.

### (4) Підписка/алерт: `ir.cron` → render_snapshot → mail.template (ВИМ-44, AC-33/34/35/61)
**Підписка:** `ir.cron` (`_cron_run_subscriptions`) за розкладом (`daily`/`weekly`/`monthly`/`cron`) обходить активні `td.bi.subscription` з `next_run<=now` (протокол `_commit_progress` — стійкість до таймаутів). Для кожного **внутрішнього** отримувача (`recipient_user_ids`) викликає `render_snapshot(filters_payload, as_user=recipient)` під **`with_user(recipient)`** → вкладення = його права (RLS/record rules) ∧ фільтри підписки → лист на основі `mail_template_id` із вкладенням (`send_mail`/`send_mail_batch`). Зовнішні `emails` — рендер від імені автора з поміткою (ОВ-7). Збій рендера одного отримувача: лист не шлеться, помилка → `_logger` + журнал доставки; інші отримувачі не блокуються; стан не «зависає» (`last_run`/`next_run` оновлюються). «Надіслати зараз» (`action_send_now`) — той самий конвеєр негайно.

**Алерт:** `ir.cron` (`_cron_check_alerts`) за `check_interval` обчислює міру (той самий `run_query`-конвеєр, без кешу або bypass) → перевіряє `value operator threshold` (поріг = `threshold` або `threshold_parameter_id`) → троттлінг (`hourly`/`daily`: не шле, якщо `last_triggered` у вікні) → доставка по `channels` (`email`/`inbox`/`activity` через `activity_schedule`) → запис `td.bi.alert.log` (value/delivery) для КОЖНОГО спрацювання, оновлення `last_triggered` (двічі за день → лист один раз, обидва в журналі — AC-35).

### (5) Бленд: CTE-генератор з record rules через `td.bi.query.compiler` (ВИМ-38, AC-39, ОВ-6)
1. `run_query` на датасеті `mode='blend'` делегує `td.bi.query.compiler`.
2. Для КОЖНОЇ таблиці (`td.bi.dataset.join`, ≤5, AC-40) компілятор бере джерело (`source_model_id` або `source_dataset_id`) і викликає `Model.with_user(env.user)._search(table_domain)` → **Query-об'єкт із вбудованими доменами record rules поточного користувача** (запасний шлях — `search(domain).ids`; SPEC §Build-time confirmations).
3. Кожна таблиця **предагрегується до з'єднання** (GROUP BY за вимірами/ключем) як окремий CTE через `odoo.tools.SQL` (`SQL.identifier` для колонок, bind-параметри для значень). Без унікального ключа у вимірах — UI-попередження (рядки схлопнуться, AC-41).
4. CTE з'єднуються за `td.bi.dataset.join.key` (пари `left_field=right_field`), `join_type` лише `left`/`inner` (right/full/cross — етап 3, ОВ-6; AC-38).
5. Підсумкова агрегація поверх з'єднаних CTE. Оскільки WHERE кожного CTE містить домен `ir.rule` свого джерела під `with_user`, два користувачі з різними правами бачать різні суми за однією конфігурацією бленду (AC-39), без витоку даних.

## Dependencies

```python
'depends': ['base', 'web', 'mail'],
```

- **`base`** — обов'язковий фундамент: `res.users`/`res.groups`/`res.company`/`res.country`/`res.currency`, `ir.model`/`ir.model.fields` (дерево полів через `fields_get()`), `ir.rule`/`ir.model.access` (модель безпеки, яку модуль успадковує без дублювання), `ir.cron` (кеш/підписки/алерти/матеріалізація), `ir.config_parameter` (`statement_timeout`, ліміти), `ir.attachment` (frozen-знімки), `base.group_user` («для всіх співробітників»), `base.group_allow_export` (експорт), `report.paperformat`/`ir.actions.report` (PDF).
- **`web`** — фронтенд-каркас: OWL-рантайм і компоненти, реєстр `actions` (для `ir.actions.client` дашборда), assets-бандли (`web.assets_backend`/`assets_frontend`), вбудований **Chart.js** (база рендера CJS-віджетів — НЕ вендоримо), `Domain` (JS `Domain.and`), `DomainSelector`/`name_search`-віджети, web-RPC (`call_kw`/`web_search_read`).
- **`mail`** — `mail.thread` (mixin на `td.bi.dashboard`: chatter, згадки при шарингу), `mail.template` (тіло розсилки підписок/алертів), `send_mail`/`send_mail_batch`, `activity_schedule` (канал алерта `activity`), `mail.activity` для inbox/activity-каналів.
- **НЕ залежимо від `spreadsheet`/`spreadsheet_dashboard`** (рішення ОВ-5): модуль реалізує власний рушій запитів (`td.bi.query.compiler` поверх `formatted_read_group` + `odoo.tools.SQL`), власний рендер (OWL + Chart.js із `web`) і власні chart-плагіни (вендоровані в `static/lib`, НЕ через npm/spreadsheet-залежність). Це уникає прив'язки до o-spreadsheet API і дозволяє контрольований lazy-бандл важких плагінів.
- **Enterprise НЕ потрібен**: усі залежності — Community (`base`/`web`/`mail`). PDF — `wkhtmltopdf` (стандарт Community, не `web_studio`/Enterprise-PDF). Жодних Enterprise-only моделей/віджетів. Модуль `installable=True`, працює на Odoo 19 Community і Odoo.sh.
- **Зовнішні інтеграції** за потреби — новий зовнішній API Odoo 19 `/json/2` + Bearer; застарілі XML-RPC / JSON-RPC не використовуються (SPEC §External integrations).

## Odoo.sh considerations

- **Branch strategy** — стандартний потік Odoo.sh dev → staging → production. Розробку вести у `development`-гілці; перф-смоук (1 млн рядків етап 1 / 5 млн етап 2, §Data & demo) ганяти на **staging** (вона має production-обсяг даних із prod-нейтралізацією) — саме там валідувати TTI/перф-бюджети (AC-47/48). Production-merge лише після зеленого config-review/pr-review.
- **Build hooks** — **особливих немає**. Схема будується штатним `-u td_bi_dashboard`/`-i` при build. Єдиний нестандартний крок — `td.bi.materialization` (`_auto=False` + `init()` створює MATERIALIZED VIEW): перше наповнення MV — через `ir.cron` (`_cron_refresh`/`action_refresh`), а не через post-init hook, щоб build не ставав важким (CONCURRENTLY-refresh поза транзакцією встановлення). Тобто `post_init_hook` не потрібен; перший REFRESH — за розкладом крона.
- **Required config params** (Settings → System Parameters / Odoo.sh env, `ir.config_parameter`): `statement_timeout` (за замовч. 30 с — ставиться модулем на курсор per-query, але глобальний PG `statement_timeout` має бути ≥ цього; на Odoo.sh налаштовується через параметр БД/конфіг). Дефолтні ліміти (50 груп / 366 точок / 80 рядків / 5 МБ JSON / 6 RPC) — як `ir.config_parameter` керовані з `res.config.settings`. `web.base.url` має бути коректним (для `full_url` frozen-посилань).
- **Зовнішній конфіг (CSP `frame-ancestors`)** — для `/bi/embed` потрібен `Content-Security-Policy: frame-ancestors <whitelist>` із `allowed_frame_ancestors` запису share. На Odoo.sh заголовок віддає сам контролер (`make_response` з CSP-заголовком), тому окрема правка nginx/reverse-proxy НЕ потрібна; але треба переконатися, що Odoo.sh-проксі не перетирає CSP. Якщо потрібен глобальний дозвіл вбудовування, фіксувати в proxy-конфізі Odoo.sh. Для public-роутів (`/bi/share`, `/bi/embed`) — врахувати, що Odoo.sh має worker-таймаути (`limit_time_real`), тому frozen-рендер не робить живих запитів (миттєва віддача `ir.attachment`).

## Class design

> Скелети для першої половини моделей (12 із «## Models»). Поля, типи й атрибути — verbatim зі SPEC «## Models»; ключові атрибути (`required`/`default`/`ondelete`/`domain`) проставлено там, де SPEC їх задає. Синтаксис — лише Odoo 19 (`invisible`/`required`/`readonly`, `aggregator`, `models.Model`). `_inherit` додано лише для `td.bi.dashboard` (`mail.thread`, SPEC рядок 779). Усе, чого SPEC не містить, винесено в «Open technical decisions» і помічено `# OPEN` біля рядка.

```python
# ─────────────────────────────────────────────────────────────────────────────
# 1. td.bi.dataset  (SPEC §«Датасет», рядки 459-523)
# ─────────────────────────────────────────────────────────────────────────────
class BiDataset(models.Model):
    _name = 'td.bi.dataset'
    _description = 'BI Датасет'
    _order = 'name, id'                      # OPEN: SPEC _order не фіксує

    # ── Fields ──
    name = fields.Char(required=True, translate=True)                       # AC-01
    description = fields.Text()
    mode = fields.Selection(
        [('model', 'Модель Odoo'), ('blend', 'Обʼєднання таблиць'), ('sql', 'SQL-датасет')],
        default='model')
    model_id = fields.Many2one(
        'ir.model',
        domain="[('transient', '=', False), ('abstract', '=', False)]")     # required if mode=model → view/constrains
    model_name = fields.Char(related='model_id.model', store=True)
    domain = fields.Text(default='[]')       # ast.literal_eval, не eval (AC-18)
    field_ids = fields.One2many('td.bi.dataset.field', 'dataset_id')        # AC-02, AC-03
    join_ids = fields.One2many('td.bi.dataset.join', 'dataset_id')          # лише mode=blend (AC-38..41)
    measure_ids = fields.One2many('td.bi.measure', 'dataset_id')            # AC-08
    parameter_ids = fields.One2many('td.bi.parameter', 'dataset_id')
    sql_query = fields.Text()                # SELECT-only; редагує лише group_bi_admin (AC-50)
    sql_field_ids = fields.One2many('td.bi.dataset.field', 'dataset_id')    # OPEN: той самий inverse, що field_ids
    currency_strategy = fields.Selection(
        [('sum_currency', 'За поточним курсом'), ('historical', 'Історична'),
         ('group_by_currency', 'Групування за валютою')],
        default='sum_currency')              # AC-53, AC-54
    date_field_default = fields.Char()
    fiscalyear_offset = fields.Integer()
    cache_ttl = fields.Integer(default=600)  # 0 = кеш вимкнено (AC-23)
    row_limit = fields.Integer(default=100000)
    visibility = fields.Selection(
        [('private', 'Лише власник'), ('groups', 'Команди'), ('global', 'Усі')],
        default='private')
    group_ids = fields.Many2many('res.groups')                              # за visibility=groups
    company_ids = fields.Many2many('res.company')
    owner_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    active = fields.Boolean(default=True)    # OPEN: SPEC default не задає; конвенція active=True

    # ── Compute ──
    version = fields.Integer(compute='_compute_version', store=True)        # елемент ключа кешу; AC-23
    # @api.depends(...)  # OPEN: SPEC «ТР не уточнює depends-граф — потребує уточнення» (рядок 507)
    # def _compute_version(self): ...        # bump при зміні полів/конфігурації

    # ── Constraints ──
    # SPEC: SQL-constraints для td.bi.dataset не задано (рядки 509-513).
    # Видимість/мультикомпанія — через ir.rule, не constraints.

    # ── Actions ──
    def run_query(self, query_spec):
        """Єдина точка виконання: валідація→компіляція→виконання→пост-обробка→кеш.  # AC-06, AC-08, AC-49, AC-62"""
    def get_fields_tree(self, path=None):
        """Ліниве дерево полів за path (лише доступні fields_get(su=False) поля).  # AC-02, AC-04, AC-05"""
    def validate_integrity(self):
        """Блокує видалення поля, що використовується віджетами; перелік віджетів (ВИМ-10).  # AC (US-18)"""


# ─────────────────────────────────────────────────────────────────────────────
# 2. td.bi.dataset.field  (SPEC §«Поле датасету», рядки 525-593)
# ─────────────────────────────────────────────────────────────────────────────
class BiDatasetField(models.Model):
    _name = 'td.bi.dataset.field'
    _description = 'BI Поле датасету'
    _order = 'sequence, id'                   # OPEN: SPEC _order не фіксує; конвенція за sequence

    # ── Fields ──
    dataset_id = fields.Many2one('td.bi.dataset', required=True, ondelete='cascade')
    name = fields.Char(required=True)         # псевдонім; унікальний у межах датасету
    path = fields.Char()                      # напр. order_id.partner_id.country_id.name; порожній для formula/SQL (AC-03)
    field_type = fields.Selection(selection='_selection_field_type')        # OPEN: SPEC «потрібно уточнити» (рядок 548)
    role = fields.Selection(
        [('dimension', 'Вимір'), ('measure', 'Міра'), ('attribute', 'Атрибут')])
    aggregator = fields.Selection(
        [('sum', 'Сума'), ('avg', 'Середнє'), ('min', 'Мінімум'), ('max', 'Максимум'),
         ('count', 'Кількість'), ('count_distinct', 'Унікальних'),
         ('bool_and', 'Логічне І'), ('bool_or', 'Логічне АБО')])            # з fields_get()['aggregator']
    is_formula = fields.Boolean()
    formula = fields.Text()                   # DSL §2.4 (AC-09, AC-10, AC-13)
    currency_path = fields.Char()             # currency_field; для monetary (AC-53, AC-54)
    geo_role = fields.Selection(
        [('none', 'Немає'), ('country', 'Країна'), ('state', 'Регіон'), ('latlong', 'Координати')])  # AC-56
    format_spec = fields.Json()
    description = fields.Text()
    visible = fields.Boolean(default=True)
    sequence = fields.Integer()

    # ── Compute ──
    formula_compiled = fields.Text(compute='_compute_formula_compiled', readonly=True)  # store=False (OPEN, рядок 574)
    @api.depends('formula')
    def _compute_formula_compiled(self):
        """Компіляція DSL-формули у SQL-вираз; кеш у formula_compiled (readonly).
        Валідація DSL (AST-whitelist, агр./неагр. мікс, невідоме поле, dunder) — AC-09/10/13."""

    # ── Constraints ──
    _sql_constraints = [
        ('name_uniq_per_dataset', 'unique(dataset_id, name)',
         "Псевдонім поля має бути унікальним у межах датасету."),
    ]
    # Блокування видалення використовуваного поля — через td.bi.dataset.validate_integrity(), не SQL-constraint.
    # @api.constrains('formula') — валідація DSL при збереженні (AC-09/10/13); компіляція делегується td.bi.query.compiler.

    # ── Actions ── None (SPEC методів-дій не визначає; лише compute вище)
```

```python
# ─────────────────────────────────────────────────────────────────────────────
# 3. td.bi.dataset.join  (SPEC §«Таблиця бленда», рядки 596-633)
# ─────────────────────────────────────────────────────────────────────────────
class BiDatasetJoin(models.Model):
    _name = 'td.bi.dataset.join'
    _description = 'BI Таблиця бленда'
    _order = 'sequence, id'                   # порядок зʼєднання (поле sequence)

    # ── Fields ──
    dataset_id = fields.Many2one('td.bi.dataset', ondelete='cascade')       # бленд-батько
    sequence = fields.Integer()               # порядок зʼєднання таблиць
    source_dataset_id = fields.Many2one('td.bi.dataset')                    # один з: датасет АБО модель
    source_model_id = fields.Many2one('ir.model')                           # один з: датасет АБО модель
    table_domain = fields.Text()              # ast.literal_eval
    table_date_field = fields.Char()
    join_type = fields.Selection(
        [('left', 'Left outer'), ('inner', 'Inner'),
         ('right', 'Right'), ('full', 'Full'), ('cross', 'Cross')])         # для 1-ї таблиці порожній; AC-38
    key_ids = fields.One2many('td.bi.dataset.join.key', 'join_id')
    included_field_ids = fields.Many2many('td.bi.dataset.field')

    # ── Constraints ──
    # SPEC: SQL-constraints не задано (рядки 622-627).
    # OPEN: «один з source_dataset_id/source_model_id» та ліміт ≤5 таблиць (AC-40) не оформлені
    #       як SQL-constraint — потребує уточнення (кандидати на @api.constrains/CHECK).

    # ── Compute ── None
    # ── Actions ── None
    # SPEC: генерація SQL (схема CTE) — адаптер td.bi.query.compiler через odoo.tools.SQL, не метод моделі.


# ─────────────────────────────────────────────────────────────────────────────
# 4. td.bi.dataset.join.key  (SPEC §«Ключ зʼєднання», рядки 637-661)
# ─────────────────────────────────────────────────────────────────────────────
class BiDatasetJoinKey(models.Model):
    _name = 'td.bi.dataset.join.key'
    _description = 'BI Ключ зʼєднання'
    _order = 'id'                             # OPEN: SPEC _order не фіксує

    # ── Fields ──
    join_id = fields.Many2one('td.bi.dataset.join', required=True, ondelete='cascade')
    left_field = fields.Char()                # ліва частина рівності (шлях у накопиченому результаті)
    right_field = fields.Char()               # права частина рівності (шлях у приєднуваній таблиці)

    # ── Constraints ── None (SPEC рядки 652-655)
    # ── Compute ── None
    # ── Actions ── None (умови зʼєднання — лише рівність пар полів)
```

```python
# ─────────────────────────────────────────────────────────────────────────────
# 5. td.bi.measure  (SPEC §«Іменована міра», рядки 665-722)
# ─────────────────────────────────────────────────────────────────────────────
class BiMeasure(models.Model):
    _name = 'td.bi.measure'
    _description = 'BI Іменована міра'
    _order = 'id'                             # OPEN: SPEC _order не фіксує (немає поля sequence)

    # ── Fields ──
    dataset_id = fields.Many2one('td.bi.dataset', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    expression = fields.Text()                # DSL над агрегатами; АБО field_id+aggregator (AC-08, AC-09)
    field_id = fields.Many2one('td.bi.dataset.field')                       # для простої міри
    aggregator = fields.Selection(
        [('sum', 'Сума'), ('avg', 'Середнє'), ('min', 'Мінімум'), ('max', 'Максимум'),
         ('count', 'Кількість'), ('count_distinct', 'Унікальних'),
         ('bool_and', 'Логічне І'), ('bool_or', 'Логічне АБО')])
    extra_domain = fields.Text()              # фільтрована міра; кон'юнкція з доменом віджета (AC-12)
    show_as = fields.Selection(
        [('value', 'Значення'), ('percent_of_total', '% від підсумку'),
         ('percent_of_dimension', '% усередині виміру'), ('running_total', 'Накопичувальний'),
         ('rank', 'Ранг'), ('diff_prev', 'Різниця з попереднім'), ('diff_prev_pct', '% різниці')])  # AC-55
    time_intelligence = fields.Selection(
        [('none', 'Немає'), ('ytd', 'YTD'), ('qtd', 'QTD'), ('mtd', 'MTD'),
         ('yoy', 'YoY'), ('pop', 'PoP'), ('rolling', 'Ковзне вікно')])      # AC-42, AC-44
    rolling_n = fields.Integer()              # для time_intelligence=rolling
    comparison = fields.Selection(
        [('none', 'Немає'), ('prev_period', 'Попередній період'),
         ('prev_year', 'Попередній рік'), ('custom_shift', 'Власний зсув')])
    format_spec = fields.Json()
    description = fields.Text()

    # ── Constraints ──
    # SPEC: SQL-constraints None (рядки 713-716).
    # @api.constrains('expression') — валідація DSL (агр./неагр. мікс, невідоме поле) AC-09/10;
    # @api.constrains('time_intelligence') — заборона без виміру-дати (AC-44). Делегує td.bi.query.compiler.

    # ── Compute ── None
    # ── Actions ── None
    # SPEC: FILTER/GROUPING SETS/часовий інтелект/віконні функції — движок запитів (§2.1.4), не метод моделі.


# ─────────────────────────────────────────────────────────────────────────────
# 6. td.bi.parameter  (SPEC §«Параметр», рядки 726-776)
# ─────────────────────────────────────────────────────────────────────────────
class BiParameter(models.Model):
    _name = 'td.bi.parameter'
    _description = 'BI Параметр'
    _order = 'id'                             # OPEN: SPEC _order не фіксує

    # ── Fields ──
    name = fields.Char(required=True)         # технічне імʼя; латиниця
    label = fields.Char(translate=True)
    dataset_id = fields.Many2one('td.bi.dataset')                           # один з: dataset_id АБО dashboard_id
    dashboard_id = fields.Many2one('td.bi.dashboard')                       # один з: dataset_id АБО dashboard_id
    param_type = fields.Selection(
        [('text', 'Текст'), ('number', 'Число'), ('boolean', 'Логічний'),
         ('selection', 'Список'), ('date', 'Дата')])
    permitted = fields.Selection(
        [('any', 'Будь-яке'), ('list', 'Зі списку'), ('range', 'Діапазон')])
    selection_values = fields.Json()          # [{value, label}]
    min = fields.Float()                      # для number
    max = fields.Float()                      # для number
    step = fields.Float()                     # для number
    default_value = fields.Json()
    url_changeable = fields.Boolean()         # білий список URL (AC-51)

    # ── Constraints ──
    _sql_constraints = [
        ('one_owner', 'CHECK((dataset_id IS NOT NULL) <> (dashboard_id IS NOT NULL))',
         "Параметр має належати рівно одному: датасету АБО дашборду."),
    ]

    # ── Compute ── None
    # ── Actions ── None
    # SPEC: серверна валідація типу з URL і наслідування звіт→сторінка→група→віджет — движок (§2.1.5).
```

```python
# ─────────────────────────────────────────────────────────────────────────────
# 7. td.bi.dashboard  (SPEC §«Дашборд», рядки 778-821)  — ЄДИНА модель з _inherit
# ─────────────────────────────────────────────────────────────────────────────
class BiDashboard(models.Model):
    _name = 'td.bi.dashboard'
    _description = 'BI Дашборд'
    _inherit = ['mail.thread']                # SPEC: Inherits: mail.thread (рядок 779)
    _order = 'name, id'                       # OPEN: SPEC _order не фіксує

    # ── Fields ──
    name = fields.Char(required=True, translate=True)
    description = fields.Text()
    tag_ids = fields.Many2many('td.bi.dashboard.tag')
    group_folder_id = fields.Many2one('td.bi.dashboard.group')              # розділ каталогу
    page_ids = fields.One2many('td.bi.dashboard.page', 'dashboard_id')
    control_ids = fields.One2many('td.bi.control', 'dashboard_id')          # scope=dashboard
    theme_id = fields.Many2one('td.bi.theme')
    theme_overrides = fields.Json()
    interaction_matrix = fields.Json()        # cross-filter «джерело × приймач» (AC-15)
    state = fields.Selection(
        [('draft', 'Чернетка'), ('published', 'Опубліковано'), ('archived', 'Архів')],
        default='draft', tracking=True)       # OPEN: tracking — конвенція mail.thread, SPEC не фіксує
    published_version_id = fields.Many2one('td.bi.dashboard.version')       # AC-25, AC-28
    owner_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    access_ids = fields.One2many('td.bi.dashboard.access', 'dashboard_id')  # AC-59
    company_ids = fields.Many2many('res.company')
    favorite_user_ids = fields.Many2many('res.users')
    menu_id = fields.Many2one('ir.ui.menu', ondelete='set null')            # AC-60
    default_state = fields.Json()
    thumbnail = fields.Image()

    # ── Constraints ── None (SPEC рядок 811)
    # ── Compute ── None (SPEC рядок 809: явно не визначає computed-полів)

    # ── Actions ──
    def action_publish(self):
        """Створює знімок td.bi.dashboard.version і перемикає state→published.  # AC-25, AC-28 (ВИМ-41)"""
    def get_runtime_config(self):
        """Повертає повну runtime-конфігурацію дашборда одним RPC (§2.4)."""
    def action_open(self):
        """Відкриває дашборд клієнтською дією з повною runtime-конфігурацією (§2.4)."""
    def copy(self, default=None):
        """ORM override: дублювання зі сторінками/віджетами/контролами."""
    def render_snapshot(self, filters, as_user):
        """Серверний знімок даних під with_user(as_user); для frozen-посилань/підписок/PDF.  # AC-26, AC-32, AC-33, AC-61 (ВИМ-43)"""


# ─────────────────────────────────────────────────────────────────────────────
# 8. td.bi.dashboard.access  (SPEC §«Доступ до дашборда», рядки 824-857)
# ─────────────────────────────────────────────────────────────────────────────
class BiDashboardAccess(models.Model):
    _name = 'td.bi.dashboard.access'
    _description = 'BI Доступ до дашборда'
    _order = 'id'                             # OPEN: SPEC _order не фіксує

    # ── Fields ──
    dashboard_id = fields.Many2one('td.bi.dashboard', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users')    # заповнюється user_id АБО group_id (взаємовиключно)
    group_id = fields.Many2one('res.groups')  # base.group_user = «для всіх співробітників» (AC-59)
    role = fields.Selection(
        [('viewer', 'Перегляд'), ('editor', 'Редагування'), ('manager', 'Керування')])  # AC-25, AC-59
    extra_domain = fields.Json()              # {dataset_id: domain}; ЛИШЕ звужує (Domain.AND); AC-21
    active = fields.Boolean(default=True)

    # ── Constraints ──
    _sql_constraints = [
        ('exactly_one_subject', 'CHECK ((user_id IS NOT NULL) <> (group_id IS NOT NULL))',
         "Має бути заповнений рівно один із user_id/group_id (взаємовиключно)."),
    ]

    # ── Compute ── None
    # ── Actions ── None (SPEC рядок 857)


# ─────────────────────────────────────────────────────────────────────────────
# 9. td.bi.dashboard.page  (SPEC §«Сторінка», рядки 861-881)
# ─────────────────────────────────────────────────────────────────────────────
class BiDashboardPage(models.Model):
    _name = 'td.bi.dashboard.page'
    _description = 'BI Сторінка дашборда'
    _order = 'sequence, id'                   # порядок вкладок (поле sequence)

    # ── Fields ──
    dashboard_id = fields.Many2one('td.bi.dashboard', required=True, ondelete='cascade')
    name = fields.Char(translate=True)
    sequence = fields.Integer()
    is_hidden = fields.Boolean()
    is_drillthrough = fields.Boolean()        # сторінка деталізації (§2.2.4)
    drillthrough_field_ids = fields.Json()    # вхідні поля drill-through
    grid_rows_min = fields.Integer()
    control_ids = fields.One2many('td.bi.control', 'page_id')               # scope=page

    # ── Constraints ── None
    # ── Compute ── None
    # ── Actions ── None
```

```python
# ─────────────────────────────────────────────────────────────────────────────
# 10. td.bi.widget  (SPEC §«Віджет», рядки 885-918)
# ─────────────────────────────────────────────────────────────────────────────
class BiWidget(models.Model):
    _name = 'td.bi.widget'
    _description = 'BI Віджет'
    _order = 'sequence, id'                   # порядок завантаження/табуляції (поле sequence)

    # ── Fields ──
    page_id = fields.Many2one('td.bi.dashboard.page', required=True, ondelete='cascade')
    dataset_id = fields.Many2one('td.bi.dataset', required=True)
    widget_type = fields.Selection(selection='_selection_widget_type')      # OPEN: коди value не зафіксовані (рядок 912)
    title = fields.Char(translate=True)       # шаблонізація {{param}}
    subtitle = fields.Char(translate=True)
    config = fields.Json()                    # data/style/interactions; conditional_rules[] (AC-45, AC-46, §2.4)
    domain = fields.Text()                    # власний домен віджета (ast.literal_eval; AC-12)
    pos_x = fields.Integer()                  # сітка 24 колонки
    pos_y = fields.Integer()
    width = fields.Integer()
    height = fields.Integer()
    group_key = fields.Char()                 # scope контролів (§2.2.4)
    visible_condition = fields.Json()         # параметр = значення (переключувані види)
    sequence = fields.Integer()

    # ── Constraints ── None (SPEC рядок 916)
    # ── Compute ── None
    # ── Actions ── None (умовне форматування — декларативно в config.style.conditional_rules[])


# ─────────────────────────────────────────────────────────────────────────────
# 11. td.bi.control  (SPEC §«Контрол», рядки 922-960)
# ─────────────────────────────────────────────────────────────────────────────
class BiControl(models.Model):
    _name = 'td.bi.control'
    _description = 'BI Контрол'
    _order = 'sequence, id'                   # порядок у панелі контролів (поле sequence)

    # ── Fields ──
    dashboard_id = fields.Many2one('td.bi.dashboard')                       # scope=dashboard
    page_id = fields.Many2one('td.bi.dashboard.page')                       # scope=page
    group_key = fields.Char()                 # scope=group (виділення віджетів)
    control_type = fields.Selection(selection='_selection_control_type')    # OPEN: коди value не зафіксовані (рядок 954)
    label = fields.Char(translate=True)
    sequence = fields.Integer()
    mapping_ids = fields.One2many('td.bi.control.mapping', 'control_id')     # AC-57
    default_value = fields.Json()
    is_locked = fields.Boolean()              # глядач бачить, не змінює (ВИМ-25)
    is_hidden = fields.Boolean()
    cascade = fields.Boolean(default=True)    # каскад залежних контролів (AC-58)
    layout = fields.Json()

    # ── Constraints ── None (SPEC рядок 958)
    # ── Compute ── None
    # ── Actions ── None
    # OPEN: автосопоставлення mapping_ids при створенні контролю (AC-57) — SPEC не закріплює метод;
    #       кандидат на create()-override або onchange. Каскадний перерахунок (AC-58) — движок/клієнт.


# ─────────────────────────────────────────────────────────────────────────────
# 12. td.bi.control.mapping  (SPEC §«Сопоставлення полів контролу», рядки 964-980)
# ─────────────────────────────────────────────────────────────────────────────
class BiControlMapping(models.Model):
    _name = 'td.bi.control.mapping'
    _description = 'BI Сопоставлення поля контролу'
    _order = 'id'                             # OPEN: SPEC _order не фіксує

    # ── Fields ──
    control_id = fields.Many2one('td.bi.control', required=True, ondelete='cascade')
    dataset_id = fields.Many2one('td.bi.dataset')                           # датасет, для якого діє мапінг
    field_path = fields.Char()                # шлях поля у датасеті (AC-57; порожній → датасет пропускається)
    enabled = fields.Boolean()                # виключення датасету («не діє»); AC-57 (default=True у тексті AC)

    # ── Constraints ── None
    # ── Compute ── None
    # ── Actions ── None
```

### Тема (`td.bi.theme`)

```python
# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import api, fields, models

class TdBiTheme(models.Model):
    _name = "td.bi.theme"
    _description = "BI: Тема оформлення"
    # Since: 19.0.1.0.0

    # === Fields ===
    name = fields.Char(string="Назва", translate=True)
    # config: палітра, фони, шрифти, радіуси, висота ряду, дефолти per widget_type
    config = fields.Json(string="Конфігурація теми")
    is_default = fields.Boolean(string="За замовчуванням")
    company_id = fields.Many2one("res.company", string="Компанія")  # корпоративна тема
    logo = fields.Image(string="Логотип")  # для експорту / публічного вигляду

    # === Constraints ===
    # SPEC: SQL constraints — None. ACL: read для user/designer, CUD лише group_bi_admin.

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    # SPEC: Key methods — None.
```

### Закладка/стан (`td.bi.dashboard.state`)

```python
# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import api, fields, models

class TdBiDashboardState(models.Model):
    _name = "td.bi.dashboard.state"
    _description = "BI: Закладка / збережений стан дашборда"
    _order = "sequence, id"
    # Since: 19.0.1.0.0

    # === Fields ===
    dashboard_id = fields.Many2one(
        "td.bi.dashboard", string="Дашборд", required=True, ondelete="cascade",
    )
    user_id = fields.Many2one(
        "res.users", string="Користувач", default=lambda self: self.env.user,
    )  # порожній = авторська спільна закладка
    name = fields.Char(string="Назва")
    kind = fields.Selection(
        [
            ("bookmark", "Закладка"),
            ("autosave", "Автозбереження"),
            ("personal_default", "Стан за замовчуванням"),
        ],
        string="Вид",
    )
    # payload: контроли, cross-фільтри, drill-стек, сторінка, приховані віджети, overrides
    # AC-16: drill-стек (рівні + хлібні крихти) серіалізується сюди й відновлюється при
    #        відкритті дашборда за особистою закладкою (kind='bookmark', user_id=uid).
    payload = fields.Json(string="Дані стану")
    apply_scope = fields.Selection(
        [("data", "Фільтри"), ("display", "Видимість"), ("all", "Усе")],
        string="Область застосування",
    )
    sequence = fields.Integer(string="Послідовність")

    # === Constraints ===
    # SPEC: SQL constraints — None.
    # Record rule (з §2.6.3): усі дії — лише власнику запису (user_id = user.id);
    #   авторські спільні (user_id порожній) керує group_bi_admin. Реалізується ir.rule, не тут.

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    # SPEC: Key methods — None.
```

### Версія дашборда (`td.bi.dashboard.version`)

```python
# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import api, fields, models

class TdBiDashboardVersion(models.Model):
    _name = "td.bi.dashboard.version"
    _description = "BI: Версія дашборда (знімок конфігурації)"
    _order = "create_date desc, id desc"
    # Since: 19.0.1.0.0
    # Примітка SPEC: автор/дата = create_uid/create_date (авто-поля ORM), окремих полів немає.

    # === Fields ===
    dashboard_id = fields.Many2one(
        "td.bi.dashboard", string="Дашборд", required=True, ondelete="cascade",
    )
    name = fields.Char(string="Назва версії")
    comment = fields.Text(string="Опис публікації")
    config_snapshot = fields.Json(string="Знімок конфігурації")  # сторінки/віджети/контроли/тема
    is_published_snapshot = fields.Boolean(string="Поточна публікація")

    # === Constraints ===
    # SPEC: SQL constraints — None.

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    def action_restore_to_draft(self):
        """Відкат версії у чернетку (AC-28).
        Given опубліковано v2, виконано відкат на v1 -> глядач після оновлення бачить v1.
        Відновлює config_snapshot цієї версії у поточну конфігурацію дашборда й переводить
        dashboard.state у 'draft'. Історія версій (v1, v2 з create_uid/create_date) зберігається.
        """
        self.ensure_one()
        raise NotImplementedError  # AC-28

    def action_publish_this(self):
        """Повторна публікація знімка старої версії (AC-28).
        Робить цей знімок поточним опублікованим (is_published_snapshot=True,
        dashboard.published_version_id = self, dashboard.state = 'published').
        """
        self.ensure_one()
        raise NotImplementedError  # AC-28
```

### Тег каталогу (`td.bi.dashboard.tag`)

```python
# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import fields, models

class TdBiDashboardTag(models.Model):
    _name = "td.bi.dashboard.tag"
    _description = "BI: Тег каталогу дашбордів"
    # Since: 19.0.1.0.0

    # === Fields ===
    name = fields.Char(string="Назва")
    color = fields.Integer(string="Колір")  # індекс палітри Odoo (штатний патерн тегів)
    # Примітка SPEC: тип color як індекс кольору — потребує підтвердження (Open technical decisions).

    # === Constraints ===
    # SPEC: SQL constraints — None.

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    # SPEC: Key methods — None.
```

### Розділ каталогу (`td.bi.dashboard.group`)

```python
# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import fields, models

class TdBiDashboardGroup(models.Model):
    _name = "td.bi.dashboard.group"
    _description = "BI: Розділ каталогу дашбордів"
    _order = "sequence, id"  # аналог spreadsheet.dashboard.group
    # Since: 19.0.1.0.0

    # === Fields ===
    name = fields.Char(string="Назва розділу")
    sequence = fields.Integer(string="Послідовність")

    # === Constraints ===
    # SPEC: SQL constraints — None.

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    # SPEC: Key methods — None.
```

### Публічне посилання (`td.bi.dashboard.share`)

```python
# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
import uuid
from odoo import api, fields, models

class TdBiDashboardShare(models.Model):
    _name = "td.bi.dashboard.share"
    _description = "BI: Публічне (frozen) посилання на дашборд"
    # Since: 19.0.1.0.0
    # Примітки SPEC (ВИМ-42a): єдиний режим — frozen-знімок (ОВ-4, AC-29);
    #   створювати запис може лише group_bi_admin (ACL); звірка токена через consteq;
    #   при невідповідності — публічна сторінка-помилка, НЕ блокування статус-кодом (AC-26).

    # === Fields ===
    dashboard_id = fields.Many2one(
        "td.bi.dashboard", string="Дашборд", required=True, ondelete="cascade",
    )
    access_token = fields.Char(
        string="Токен доступу", copy=False, default=lambda self: uuid.uuid4().hex,
    )  # звірка через consteq
    snapshot_attachment_id = fields.Many2one(
        "ir.attachment", string="Знімок (frozen)",
    )  # frozen-знімок усіх віджетів — єдиний режим публічного доступу (ОВ-4)
    expiration_date = fields.Datetime(string="Термін дії")
    password_hash = fields.Char(string="Хеш пароля")
    allowed_frame_ancestors = fields.Char(
        string="Дозволені домени embed",
    )  # Content-Security-Policy: frame-ancestors
    allow_export = fields.Boolean(string="Дозволити експорт")  # разом із base.group_allow_export
    active = fields.Boolean(string="Активне", default=True)  # деактивація = миттєвий відзив

    # === Constraints ===
    # SPEC: SQL constraints — None.

    # === Compute ===
    full_url = fields.Char(string="Повне посилання", compute="_compute_full_url")

    @api.depends("access_token")  # + base_url (ir.config_parameter 'web.base.url')
    def _compute_full_url(self):
        """Формує /bi/share/<id>/<token> на базі web.base.url. readonly (без inverse)."""
        # base = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        raise NotImplementedError  # SPEC: _compute_full_url

    # === Actions ===
    def action_revoke(self):
        """Відкликати посилання (AC-30): active=False -> наступне відкриття URL веде на
        сторінку «посилання недійсне», знімок більше не віддається.
        """
        # self.write({"active": False})
        raise NotImplementedError  # AC-30

    # Контролерний контур (роут /bi/share/<id>/<token>, auth='public') — НЕ метод цієї моделі:
    #   AC-26: consteq(token) OK -> рендер знімка без живих запитів; fail -> «посилання недійсне»;
    #          expiration_date у минулому -> «термін дії вичерпано».
    #   AC-27: with_user(create_uid).has_access('read') == False -> доступ закрито (деактивація),
    #          живі запити до бізнес-моделей не виконуються.
    #   Посилання деактивуються авто при архівації дашборда і втраті автором права читання.
    #   (потребує уточнення розподілу: контролер vs хелпер моделі — Open technical decisions)
```

### Підписка (`td.bi.subscription`)

```python
# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import api, fields, models

class TdBiSubscription(models.Model):
    _name = "td.bi.subscription"
    _description = "BI: Підписка на розсилку дашборда"
    # Since: 19.0.1.0.0
    # Примітки SPEC (ВИМ-44): mail.template + ir.cron, протокол _commit_progress;
    #   record rule «лише свої»; розсилка send_mail / send_mail_batch.

    # === Fields ===
    dashboard_id = fields.Many2one(
        "td.bi.dashboard", string="Дашборд", required=True, ondelete="cascade",
    )
    page_ids = fields.Many2many("td.bi.dashboard.page", string="Сторінки")
    recipient_user_ids = fields.Many2many(
        "res.users", relation="td_bi_subscription_user_rel",
        column1="subscription_id", column2="user_id", string="Отримувачі (внутрішні)",
    )  # рендер від імені отримувача (AC-33, AC-61)
    recipient_partner_ids = fields.Many2many(
        "res.partner", relation="td_bi_subscription_partner_rel",
        column1="subscription_id", column2="partner_id", string="Отримувачі (контакти)",
    )
    emails = fields.Text(string="Зовнішні email")  # рендер від імені автора, помітка в UI (ОВ-7)
    schedule_type = fields.Selection(
        [("daily", "Щодня"), ("weekly", "Щотижня"),
         ("monthly", "Щомісяця"), ("cron", "Cron-вираз")],
        string="Тип розкладу",
    )
    weekday_ids = fields.Many2many(
        "td.bi.weekday", string="Дні тижня",
    )  # SPEC не задає comodel weekday_ids -> потребує уточнення (Open technical decisions)
    monthday = fields.Integer(string="День місяця")
    time = fields.Float(string="Година доби")
    cron_expr = fields.Char(string="Cron-вираз")  # schedule_type='cron', лише адмін
    format = fields.Selection(
        [("pdf", "PDF"), ("xlsx", "XLSX"), ("link", "Посилання")], string="Формат",
    )
    filters_payload = fields.Json(string="Фіксовані фільтри")  # значення контролів на розклад
    only_if_data = fields.Boolean(string="Слати лише якщо є дані")
    active = fields.Boolean(string="Активна", default=True)
    last_run = fields.Datetime(string="Останній запуск")
    next_run = fields.Datetime(string="Наступний запуск")
    mail_template_id = fields.Many2one("mail.template", string="Шаблон листа")

    # === Constraints ===
    # SPEC: SQL constraints — None.

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    def action_send_now(self):
        """«Надіслати зараз» (AC-61): для кожного внутрішнього отримувача викликає
        той самий конвеєр render_snapshot під with_user(recipient) — дані = його права
        (RLS/record rules) ∧ filters_payload; кожен отримує mail.template із власним зрізом.
        Зовнішньому email — від імені автора з поміткою (ОВ-7); внутрішньому — без помітки.
        AC-61: відсутність даних у отримувача -> порожній знімок без витоку; збій render_snapshot
        одного отримувача НЕ блокує інших (try/except per recipient, помилка -> _logger у журнал),
        кнопка завершується без падіння.
        """
        self.ensure_one()
        raise NotImplementedError  # AC-61

    @api.model
    def _cron_run_subscriptions(self):
        """ir.cron: плановий запуск за schedule_type (daily/weekly/monthly/cron).
        AC-34: якщо render падає -> лист НЕ надсилається, помилка в журнал підписки,
        наступний запуск за розкладом (стан не «зависає»). Стійкість — _commit_progress.
        Оновлює last_run / next_run.
        """
        raise NotImplementedError  # AC-33, AC-34
```

### Алерт (`td.bi.alert`)

```python
# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import api, fields, models

class TdBiAlert(models.Model):
    _name = "td.bi.alert"
    _description = "BI: Алерт за порогом міри"
    # Since: 19.0.1.0.0
    # Примітки SPEC (ВИМ-44): канал 'activity' -> activity_schedule; record rule «лише свої».

    # === Fields ===
    widget_id = fields.Many2one(
        "td.bi.widget", string="Віджет", ondelete="cascade",
        # domain обмежує KPI/gauge/card — точний домен залежить від кодів widget_type
        # (потребує уточнення — Open technical decisions)
    )
    measure_key = fields.Char(string="Ключ міри")  # яку міру конфіга віджета перевіряти
    operator = fields.Selection(
        [(">", "Більше"), (">=", "Більше або дорівнює"),
         ("<", "Менше"), ("<=", "Менше або дорівнює"),
         ("=", "Дорівнює"), ("!=", "Не дорівнює")],
        string="Оператор",
    )
    threshold = fields.Float(string="Поріг-константа")
    threshold_parameter_id = fields.Many2one(
        "td.bi.parameter", string="Поріг-параметр",
    )  # альтернатива константі (AC-46 — поріг з іншого джерела на рівні форматування)
    check_interval = fields.Selection(
        selection="_selection_check_interval", string="Інтервал перевірки",
    )  # SPEC: довідник значень частоти ВІДСУТНІЙ -> потребує уточнення (Open technical decisions)
    throttle = fields.Selection(
        [("hourly", "Не частіше разу на годину"), ("daily", "Не частіше разу на день")],
        string="Троттлінг",
    )
    recipient_user_ids = fields.Many2many("res.users", string="Отримувачі")
    channels = fields.Json(string="Канали доставки")  # email / inbox / activity
    last_triggered = fields.Datetime(string="Останнє спрацювання")
    trigger_log_ids = fields.One2many(
        "td.bi.alert.log", "alert_id", string="Журнал спрацювань",
    )

    @api.model
    def _selection_check_interval(self):
        # SPEC не наводить значень -> повертаємо порожньо, заповнюється на узгодженні (Open tech).
        return []

    # === Constraints ===
    # SPEC: SQL constraints — None.

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    @api.model
    def _cron_check_alerts(self):
        """ir.cron за check_interval (AC-35): обчислює «значення <operator> поріг»
        (поріг = threshold АБО threshold_parameter_id). Якщо умова виконана —
        застосовує throttle (hourly/daily): за троттлінгом 'daily' два спрацювання за день
        дають РІВНО одне сповіщення, але ОБИДВА фіксуються у td.bi.alert.log.
        Доставка по channels (email/inbox/activity -> activity_schedule),
        оновлює last_triggered.
        """
        raise NotImplementedError  # AC-35

    def action_view_trigger_log(self):
        """Smart-кнопка «Журнал спрацювань»: дія на td.bi.alert.log з фільтром alert_id=self."""
        self.ensure_one()
        raise NotImplementedError  # SPEC: action_view_trigger_log
```

### Журнал алертів (`td.bi.alert.log`)

```python
# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import fields, models

class TdBiAlertLog(models.Model):
    _name = "td.bi.alert.log"
    _description = "BI: Журнал спрацювань алерта"
    _order = "create_date desc, id desc"
    # Since: 19.0.1.0.0
    # ACL: read для user/designer (лише свої) / admin (усі); W/C/D немає — пише система.

    # === Fields ===
    alert_id = fields.Many2one(
        "td.bi.alert", string="Алерт", required=True, ondelete="cascade",
    )
    # create_date — авто-поле ORM (момент спрацювання, AC-35)
    value = fields.Float(string="Значення міри")
    delivery = fields.Text(string="Результат доставки")

    # === Constraints ===
    # SPEC: SQL constraints — None.

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    # SPEC: Key methods — None.
```

### Серверний кеш (`td.bi.cache`)

```python
# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
import hashlib
from odoo import api, fields, models

class TdBiCache(models.Model):
    _name = "td.bi.cache"
    _description = "BI: Серверний кеш результатів запитів"
    # Since: 19.0.1.0.0
    # Примітки SPEC (ВИМ-47, ВИМ-49): реалізувати з нуля (модель + unique-індекс + cron-очистка);
    #   uid-маркер = user_id (кеш персональний); інвалідація: TTL (cron), вручну («Оновити» —
    #   bypass), bump dataset.version. ACL: read лише group_bi_admin (пише система).

    # === Fields ===
    cache_key = fields.Char(string="Ключ кешу", index=True)  # SHA-256, unique
    dataset_id = fields.Many2one(
        "td.bi.dataset", string="Датасет", ondelete="cascade",
    )
    payload = fields.Json(string="Результат")  # JSON результату (за §2.4 — gzip-Binary)
    expires_at = fields.Datetime(string="Спливає", index=True)  # now + cache_ttl; для cron
    hit_count = fields.Integer(string="Звернень")

    # === Constraints ===
    _sql_constraints = [
        ("cache_key_uniq", "unique(cache_key)", "Ключ кешу має бути унікальним"),
    ]
    # SPEC (потребує уточнення): unique через _sql_constraints vs index=True + unique у init() —
    #   обрано _sql_constraints за дослівним зразком SPEC. (Open technical decisions)

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    @api.model
    def _cron_clear_expired(self):
        """ir.cron (кожні ~15 хв): видаляє записи з expires_at у минулому;
        протокол _commit_progress (стійкість до таймаутів)."""
        raise NotImplementedError  # SPEC: §2.3.4

    @api.model
    def _build_cache_key(self, dataset, query_spec):
        """Службовий: SHA-256 від (dataset_id+version, нормалізований домен, groupby,
        aggregates, having, order, limit, uid-маркер прав, lang, tz, company_ids).
        AC-23: ключ ВКЛЮЧАЄ маркер прав користувача (+ lang/tz/company_ids), тому А і Б
        НЕ отримують результат з одного кеш-ключа — кеш не змішує дані різних користувачів.
        """
        raise NotImplementedError  # AC-23
```

### Журнал аудиту (`td.bi.audit.log`)

```python
# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import fields, models

class TdBiAuditLog(models.Model):
    _name = "td.bi.audit.log"
    _description = "BI: Журнал аудиту подій"
    _order = "create_date desc, id desc"
    # Since: 19.0.1.0.0
    # ACL: лише читання для group_bi_admin; запис системою у точках подій (етап 2, ВИМ-40).

    # === Fields ===
    event_type = fields.Selection(
        [
            ("view", "Перегляд"),
            ("export", "Експорт"),
            ("share_create", "Створення посилання"),
            ("share_revoke", "Відкликання посилання"),
            ("access_change", "Зміна доступу"),
            ("sql_run", "Виконання SQL"),
        ],
        string="Тип події", required=True,
    )
    dashboard_id = fields.Many2one("td.bi.dashboard", string="Дашборд")
    dataset_id = fields.Many2one("td.bi.dataset", string="Датасет")
    user_id = fields.Many2one(
        "res.users", string="Користувач", required=True,
        default=lambda self: self.env.user,
    )
    payload = fields.Json(string="Деталі події")
    # create_date — авто-поле ORM (коли).
    # AC-22: «подивитися як користувач» пише запис event_type='view' (хто/коли/кого).
    # AC-50: створення SQL-датасету -> event_type='sql_run' з текстом запиту у payload.

    # === Constraints ===
    # SPEC: SQL constraints — None.

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    # SPEC: Key methods — None.
```

### Матеріалізація (`td.bi.materialization`)

```python
# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import api, fields, models
from odoo.exceptions import UserError

class TdBiMaterialization(models.Model):
    _name = "td.bi.materialization"
    _description = "BI: Матеріалізація (предагрегат) датасету"
    _auto = False  # модель без авто-таблиці ORM; схема будується в init() через odoo.tools.SQL
    # Since: 19.0.1.0.0
    # SPEC: патерн _auto=False + init() / REFRESH MATERIALIZED VIEW CONCURRENTLY (зразок
    #   sale.report). Будується БЕЗ користувацьких правил -> лише для RLS-безпечних конфігурацій.
    #   Потребує звірки з Odoo 19 (життєвий цикл _auto=False / _table_query / init() v19) —
    #   зафіксувати в DEVIATIONS перед стартом WP (Open technical decisions).
    # ACL: read/write/create/delete лише group_bi_admin.

    # === Fields ===
    dataset_id = fields.Many2one(
        "td.bi.dataset", string="Датасет", required=True, ondelete="cascade",
    )
    dimension_paths = fields.Json(string="Виміри предагрегата")  # фіксовані виміри
    measure_specs = fields.Json(string="Міри")  # фіксовані міри (+ aggregator на fallback)
    granularity = fields.Char(string="Гранулярність дати")
    table_name = fields.Char(string="Імʼя таблиці / MV")
    refresh_cron_id = fields.Many2one("ir.cron", string="Cron оновлення")
    last_refresh = fields.Datetime(string="Останнє оновлення")

    # === Constraints ===
    # SPEC: SQL constraints — None. Цілісність RLS гарантує is_rls_safe + UserError у create.

    # === Compute ===
    is_rls_safe = fields.Boolean(
        string="RLS-безпечна", compute="_compute_is_rls_safe", store=True,
    )

    @api.depends("dataset_id", "dimension_paths")  # + конфіг record rules датасету
    def _compute_is_rls_safe(self):
        """AC-63: True лише якщо RLS-варіативність відсутня АБО компенсована виміром-ключем
        правила (напр. team_id входить у dimension_paths). Інакше False -> create блокується.
        AC-62: при is_rls_safe=True домен record rules глядача застосовується через вимір-ключ.
        """
        raise NotImplementedError  # AC-62, AC-63

    # === Actions ===
    @api.model
    def init(self):
        """Створення фізичної таблиці / materialized view через odoo.tools.SQL
        (патерн _auto=False). Потребує звірки з Odoo 19 (Open technical decisions)."""
        raise NotImplementedError  # SPEC: init() — _auto=False

    @api.model_create_multi
    def create(self, vals_list):
        """AC-63: якщо is_rls_safe обчислюється у False — перервати створення дослівним
        UserError(«Неможливо створити матеріалізацію: датасет має RLS-варіативність,
        не компенсовану виміром-ключем правила. Предагрегат став би каналом витоку
        повз record rules.») і НЕ створювати ні запис, ні MV (стан БД незмінний).
        Додавання виміру-ключа правила (напр. team_id) -> is_rls_safe=True -> створення без помилки.
        """
        raise NotImplementedError  # AC-63

    def action_refresh(self):
        """REFRESH MATERIALIZED VIEW CONCURRENTLY <table_name>; оновлює last_refresh.
        CONCURRENTLY вимагає унікального індексу на MV (PostgreSQL)."""
        self.ensure_one()
        raise NotImplementedError  # SPEC: action_refresh

    @api.model
    def _cron_refresh(self):
        """ir.cron (refresh_cron_id): періодичний REFRESH MATERIALIZED VIEW CONCURRENTLY
        предагрегатів за розкладом; оновлює last_refresh (етап 2, ВИМ-48)."""
        raise NotImplementedError  # SPEC: §2.3.6
```

### Адаптер: компілятор запитів (`td.bi.query.compiler`)

```python
# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import api, models
from odoo.fields import Domain  # Odoo 19: первокласний Domain (Domain.AND для кон'юнкції рівнів)

class TdBiQueryCompiler(models.AbstractModel):
    _name = "td.bi.query.compiler"
    _description = "BI: Компілятор запитів (адаптер ORM -> SQL)"
    # Since: 19.0.1.0.0
    # Інкапсулює приватний API Odoo 19: Model._search(domain) як точка, що повертає Query
    # з вбудованими record rules (формально приватний API). Запасний шлях — search(domain).ids.
    # Жодних бізнес-запитів під sudo() (безпека за замовчуванням, §2.4.1).
    # ОДИН адаптер вміщує: компіляцію model/blend, роутер run_query для матеріалізації (AC-62),
    # DSL-компіляцію/валідацію (AC-09/10/13) і Domain.AND-склейку доменів (AC-64).
    # SPEC §2.1.3/§2.4 фіксує адаптер як модель td.bi.query.compiler (НЕ окремий engine/-пакет).

    # === Methods ===
    @api.model
    def compile_model_query(self, dataset, query_spec, domain):
        """Компіляція mode='model': кореневу модель -> formatted_read_group(domain, groupby,
        aggregates, having, order, limit, offset) ВІД ІМЕНІ користувача.
        formatted_read_group сам викликає check_access('read') і вбудовує домени ir.rule
        у WHERE/підзапити; поля з groups= відхиляються AccessError (AC-02, AC-19, AC-20).
        Ефективний домен склеюється виключно через Domain.AND (AC-64).
        Часовий інтелект/«% від підсумку»/ранги/мультивалютність — пост-обробка тут
        (AC-08, AC-11, AC-12, AC-17, AC-36, AC-42, AC-43, AC-53, AC-54, AC-55)."""
        raise NotImplementedError  # AC-08, AC-11, AC-12, AC-17, AC-19, AC-20, AC-36, AC-42, AC-43, AC-53, AC-54, AC-55, AC-64

    @api.model
    def compile_blend_query(self, dataset, query_spec, domain):
        """Компіляція mode='blend': по одному CTE на td.bi.dataset.join через odoo.tools.SQL.
        AC-39: WHERE кожного CTE містить домен record rules ВІДПОВІДНОГО джерела/користувача —
        через self._inject_record_rules(model, table_domain) як підзапит. Кожна таблиця
        предагрегується ДО зʼєднання (AC-41). Типи join — лише left/inner (AC-38, ОВ-6).
        Ліміт ≤ 5 таблиць (AC-40 перевіряється на рівні конфігурації бленда)."""
        raise NotImplementedError  # AC-38, AC-39, AC-41

    @api.model
    def route_query(self, dataset, query_spec, domain):
        """Роутер run_query для матеріалізації (AC-62): якщо запит «накривається»
        RLS-безпечним предагрегатом td.bi.materialization (виміри/міри/гранулярність ⊆),
        читає з table_name (RLS через вимір-ключ правила); інакше падає назад на
        compile_model_query/formatted_read_group по сирій моделі — числово ідентично,
        домен зібрано через Domain.AND. Без винятку/розбіжності."""
        raise NotImplementedError  # AC-62

    @api.model
    def compile_formula(self, dataset_field_or_measure):
        """DSL-компіляція/валідація (AC-09/10/13): ast.parse(mode='eval') + жорсткий whitelist
        вузлів AST; колонки лише через SQL.identifier, значення — bind-параметри; safe_eval
        ніде. Відхилення: змішування агр./неагр. операндів (ValidationError, AC-09),
        невідоме поле з підказкою (AC-10), dunder/__import__ -> відмова + запис у
        td.bi.audit.log (AC-13). Викликається з @api.constrains моделей field/measure."""
        raise NotImplementedError  # AC-09, AC-10, AC-13

    @api.model
    def build_effective_domain(self, levels):
        """Доменна безпека (AC-64): ефективний домен трьох рівнів виключно через
        Domain.AND([dataset, control, widget]); парс текстових доменів ast.literal_eval
        (як ir.filters._get_eval_domain()); білий список динамічних дат -> інакше
        ValidationError; OR-префікс лишається ізольованим у своєму рівні (атака
        нейтралізується). Без конкатенації списків."""
        raise NotImplementedError  # AC-64

    @api.model
    def _inject_record_rules(self, model, domain):
        """Повертає SQL-підзапит набору id, доступних поточному користувачу, із вбудованими
        record rules. Основний шлях — Model._search(domain) (Query-обʼєкт, приватний API).
        Запасний шлях — model.search(domain).ids (публічний, повертає лише дозволені id).
        Гарантує, що RLS діє в кожному CTE бленда (AC-39) і не обходиться (AC-21, AC-62).
        Без sudo()."""
        try:
            # Основний (приватний) шлях — Query з record rules у WHERE як підзапит.
            return model._search(domain)
        except Exception:  # pragma: no cover — звірити сигнатуру/виняток на збірці 19.0
            # Запасний шлях: публічний search -> лише дозволені id.
            return model.search(domain).ids
        # SPEC build-time confirmation: точна форма Model._search(domain) у 19.0 — зафіксувати
        # у DEVIATIONS (Open technical decisions).
```

### Налаштування (`res.config.settings`)

```python
# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    # Since: 19.0.1.0.0
    # Розділ Configuration SPEC. Значення зберігаються в ir.config_parameter
    # (config_parameter=...) -> читаються движком запитів і клієнтом (biDataService).

    # === Fields ===
    td_bi_statement_timeout = fields.Integer(
        string="statement_timeout BI-запиту (с)", default=30,
        config_parameter="td_bi_dashboard.statement_timeout",
    )  # ставиться на курсор перед виконанням, скидається після; таймаут -> UserError (AC-49)
    td_bi_max_concurrent_rpc = fields.Integer(
        string="Макс. паралельних data-RPC", default=6,
        config_parameter="td_bi_dashboard.max_concurrent_rpc",
    )  # черга biDataService
    td_bi_max_response_mb = fields.Integer(
        string="Ліміт відповіді (МБ JSON)", default=5,
        config_parameter="td_bi_dashboard.max_response_mb",
    )
    td_bi_control_debounce_ms = fields.Integer(
        string="Дебаунс контролів (мс)", default=400,
        config_parameter="td_bi_dashboard.control_debounce_ms",
    )
    td_bi_max_groups = fields.Integer(
        string="Ліміт груп", default=50,
        config_parameter="td_bi_dashboard.max_groups",
    )
    td_bi_max_time_points = fields.Integer(
        string="Ліміт точок часу", default=366,
        config_parameter="td_bi_dashboard.max_time_points",
    )
    td_bi_max_table_rows = fields.Integer(
        string="Ліміт рядків таблиці", default=80,
        config_parameter="td_bi_dashboard.max_table_rows",
    )
    td_bi_field_tree_max_depth = fields.Integer(
        string="Макс. глибина дерева полів", default=5,
        config_parameter="td_bi_dashboard.field_tree_max_depth",
    )  # AC-04: понад 5 рівнів блокується

    # === Constraints / Compute / Actions ===
    # SPEC: окремих constraints/compute/actions для налаштувань не визначено.
    # Примітка: SPEC дає тільки statement_timeout як параметр; решта лімітів подані як
    #   числові константи розділу Configuration — їх винесено в config_parameter тут,
    #   спосіб зберігання (config_parameter vs ir.config_parameter напряму) — Open technical
    #   decisions (SPEC §1.2: «за оголошенням (ir.config_parameter / поля моделей)»).
```

## AC traceability

Кожен AC покрито щонайменше одним рядком; «нещасливі» шляхи (валідація/права/межі) мапляться на метод-носій логіки + відповідний тест. Усі 65 AC (AC-01..AC-65) покрито. Імена моделей/методів/груп/контролерів/OWL-компонентів узяті дослівно зі SPEC (моделі `td.bi.*`, методи `run_query`/`render_snapshot`/`validate_integrity` тощо, групи `group_bi_*`, роути `/bi/...`, компоненти `biDataService`/`ControlBar`/`GeoWidget`/`ShareDialog`/`VersionHistory`/`MeasurePanel`/`BlendEditor`). Рядки з Type `engine` віднесено до адаптера `models/bi_query_compiler.py` (модель `td.bi.query.compiler`, SPEC §2.1.3/§2.4) — окремого `engine/`-пакета немає; компіляція model/blend, роутер run_query (AC-62), DSL-валідація (AC-09/10/13) і Domain.AND-склейка (AC-64) інкапсульовані в цьому адаптері (DSL/домен викликаються з `@api.constrains` моделей `td.bi.dataset.field`/`td.bi.measure`).

| AC | Implementation location | Type |
| :-- | :-- | :-- |
| AC-01 | `views/bi_dataset_views.xml` + `views/bi_menus.xml` — `menuitem`/`act_window` дії «Створити датасет» з `groups="td_bi_dashboard.group_bi_designer"` | view |
| AC-01 | `security/td_bi_dashboard_security.xml` — ACL `td.bi.dataset` create=✗ для `group_bi_user` (прямий виклик дії → `AccessError`) | security |
| AC-01 | `tests/test_ac01_dataset_create_access.py` — прямий create під `group_bi_user` піднімає `AccessError`, датасет не створено | test |
| AC-02 | `models/bi_dataset.py::get_fields_tree()` — лінива побудова дерева через `fields_get()` з `su=False` (поля з `groups=` відсутні) | method |
| AC-02 | `tests/test_ac02_fields_tree_acl.py` — поле, закрите `groups=`, відсутнє у `get_fields_tree()` і не додається до датасету | test |
| AC-03 | `models/bi_dataset.py::get_fields_tree()` + `models/bi_dataset_field.py` (поле `path`) — автофіксація багаторівневого шляху/JOIN при збереженні `td.bi.dataset.field` | method |
| AC-04 | `models/bi_dataset.py::get_fields_tree()` — обмеження глибини обходу шляху (5 рівнів; `ir.config_parameter`); 6-й рівень не розкривається | method |
| AC-04 | `tests/test_ac04_path_depth_limit.py` — спроба 6-го рівня → гілка не розкривається, повертається маркер ліміту | test |
| AC-05 | `models/bi_dataset.py::get_fields_tree()` — детекція повтору пари (модель, поле) → маркер рекурсії; додавання поля потребує `confirm`-прапора | method |
| AC-05 | `tests/test_ac05_recursion_confirm.py` — без підтвердження поле з рекурсивної гілки не додається | test |
| AC-06 | `models/bi_dataset.py::run_query()` — попередній перегляд = рівно один RPC `run_query`; `limit≤80` + пагінація (Configuration: 80 рядків таблиці) | method |
| AC-06 | `static/src/js/services/bi_data_service.js` (`biDataService`) — попередній перегляд викликає `run_query` один раз | owl |
| AC-07 | `models/bi_dataset.py::get_fields_tree()` — computed без `store=True` і без `search`-методу позначається неактивним (не вимір/не фільтр) | method |
| AC-07 | `tests/test_ac07_computed_field_inactive.py` — таке поле не можна обрати як вимір/фільтр | test |
| AC-08 | `models/bi_query_compiler.py::compile_model_query()` (`td.bi.query.compiler`) — компіляція ratio-міри в один агрегувальний `formatted_read_group` (`SUM`+`COUNT_DISTINCT`), ділення на сервері над агрегатами | engine |
| AC-08 | `models/bi_dataset.py::run_query()` — батч агрегатів одним викликом для міри-ratio | method |
| AC-09 | `models/bi_query_compiler.py::compile_formula()` + `models/bi_measure.py` (`@api.constrains` `expression`) — `ValidationError` «змішування агрегованого і неагрегованого операндів» при збереженні | method |
| AC-09 | `tests/test_ac09_measure_agg_mix.py` — `SUM([price_subtotal]) / [qty]` не зберігається | test |
| AC-10 | `models/bi_query_compiler.py::compile_formula()` — резолв полів формули; невідоме поле → `ValidationError` «невідоме поле» з підказкою найближчого імені | method |
| AC-10 | `tests/test_ac10_formula_unknown_field.py` — формула з `[pric]` не зберігається | test |
| AC-11 | `models/bi_query_compiler.py::compile_model_query()` — генерація `NULLIF(denominator,0)` для ratio (ділення на нуль → NULL) у `td.bi.query.compiler` | engine |
| AC-11 | `tests/test_ac11_ratio_div_zero.py` — група зі знаменником 0 дає NULL, інші групи коректні | test |
| AC-12 | `models/bi_query_compiler.py::compile_model_query()` — `extra_domain` фільтрованої міри в `formatted_read_group` через FILTER, склейка з доменом контролю через `Domain.AND` | engine |
| AC-12 | `tests/test_ac12_filtered_measure_and.py` — значення = (контрол березень) ∧ (`state=done`) | test |
| AC-13 | `models/bi_query_compiler.py::compile_formula()` — whitelist вузлів AST (`ast.parse(mode='eval')`); dunder/`__import__` → відмова | method |
| AC-13 | `models/bi_audit_log.py` + `models/bi_measure.py` — запис інциденту в `td.bi.audit.log`, міра не зберігається | method |
| AC-13 | `tests/test_ac13_formula_ast_whitelist.py` — `__import__`/подвійне підкреслення відхиляється і логується | test |
| AC-14 | `models/bi_dataset.py::run_query()` — домен спуску береться з `__extra_domain` відповіді й додається через `Domain.AND` (не конструюється клієнтом) | method |
| AC-14 | `static/src/js/services/bi_data_service.js` (`biDataService`) — drill використовує серверний `__extra_domain` точки даних | owl |
| AC-15 | `static/src/js/components/control_bar/` (`ControlBar`) + `static/src/js/components/dashboard_canvas/` — cross-filter «drill фільтрує інші віджети», чип у панелі фільтрів | owl |
| AC-16 | `models/bi_dashboard_state.py` (`td.bi.dashboard.state`, `kind=bookmark`, `payload`) — збереження/відновлення drill-стеку та хлібних крихт | method |
| AC-16 | `static/src/js/components/dashboard_canvas/` — відновлення drill-стеку з особистої закладки при переоткритті | owl |
| AC-17 | `models/bi_query_compiler.py::compile_model_query()` — обчислення меж місяця для `datetime` з урахуванням `tz` користувача (UTC-зсув) у `__extra_domain` | engine |
| AC-17 | `tests/test_ac17_datetime_month_tz.py` — діапазон «березень» коректний у Europe/Kyiv | test |
| AC-18 | `models/bi_dataset.py::run_query()` — порожня вибірка → коректний порожній стан (без винятку); деградація віджета | method |
| AC-18 | `static/src/js/components/widget_renderer/` — порожній стан + оновлення крихт + кнопка «вгору» при спуску в порожню групу | owl |
| AC-19 | `models/bi_dataset.py::run_query()` — `formatted_read_group` від імені користувача (без `sudo()`); record rules вбудовуються в WHERE/підзапити | method |
| AC-19 | `tests/test_ac19_rls_per_user.py` — продавець А і керівник Б бачать різні KPI з однією конфігурацією | test |
| AC-20 | `static/src/js/components/widget_renderer/` — per-віджет деградація: картка «нема доступу», решта віджетів працює | owl |
| AC-20 | `models/bi_dataset.py::run_query()` — відсутність ACL-`read` на модель → контрольована помилка віджета (`AccessError` ловиться на рівні віджета) | method |
| AC-20 | `tests/test_ac20_no_acl_widget_degrades.py` — фінансовий віджет показує «нема доступу», сторінка не падає | test |
| AC-21 | `models/bi_dashboard_access.py` (`extra_domain` per-датасет) + `models/bi_dataset.py::run_query()` — домен аудиторії додається через `Domain.AND` (лише звужує, не розширює понад record rules) | method |
| AC-21 | `tests/test_ac21_audience_domain_narrow.py` — дані = record rules ∧ `extra_domain`; `extra_domain` не розширює видимість | test |
| AC-22 | `models/bi_dashboard.py::render_snapshot()` / `models/bi_dataset.py::run_query()` — «подивитися як користувач» через `with_user(обраний)`; запис у `td.bi.audit.log` | method |
| AC-22 | `tests/test_ac22_view_as_user_audit.py` — data-RPC під `with_user`, факт перегляду в `td.bi.audit.log` | test |
| AC-23 | `models/bi_cache.py::_build_cache_key()` — SHA-256 ключ включає uid-маркер прав, `lang`, `tz`, `company_ids`, `dataset.version` | method |
| AC-23 | `tests/test_ac23_cache_key_per_user.py` — А і Б не отримують результат з одного кеш-ключа | test |
| AC-24 | `views/bi_dashboard_views.xml` / `static/src/js/components/dashboard_canvas/` — дія «Подивитися як користувач» з `groups="td_bi_dashboard.group_bi_admin"` (`invisible` для решти) | view |
| AC-24 | `models/bi_dashboard.py::render_snapshot()` — прямий виклик режиму «як користувач» без `group_bi_admin` → `AccessError`; дизайнеру доступний лише «як аудиторія» | method |
| AC-24 | `tests/test_ac24_view_as_user_access.py` — дизайнер без `group_bi_admin` → `AccessError` на «як користувач» | test |
| AC-25 | `security/td_bi_dashboard_security.xml` — record rule `td.bi.dashboard` (`perm_read`/`perm_write`): viewer бачить публікацію без редагування, editor — чернетку | security |
| AC-25 | `static/src/js/components/dashboard_canvas/` — viewer без кнопки редагування; editor бачить «Опублікувати» | owl |
| AC-26 | `controllers/main.py::/bi/share/<int:share_id>/<token>` (`auth='public'`) — `consteq`-звірка токена; коректний → рендер `snapshot_attachment_id`; некоректний/прострочений → публічна сторінка-помилка | controller |
| AC-26 | `tests/test_ac26_share_token.py` — коректний токен рендерить знімок без живих запитів; некоректний/прострочений → сторінка-помилка | test |
| AC-27 | `controllers/main.py::/bi/share` — перевірка `with_user(create_uid).has_access('read')`; при втраті права доступ закрито, живі запити не виконуються | controller |
| AC-27 | `tests/test_ac27_share_author_lost_read.py` — автор втратив `read` → посилання недоступне | test |
| AC-28 | `models/bi_dashboard_version.py::action_restore_to_draft()` + `action_publish_this()` — відкат на v1; глядач бачить v1; історія містить v1/v2 з авторами/датами (`create_uid`/`create_date`) | method |
| AC-28 | `tests/test_ac28_version_rollback.py` — після відкату глядач бачить v1, історія повна | test |
| AC-29 | `static/src/js/components/share_dialog/` (`ShareDialog`) — діалог публічного посилання пропонує лише frozen-режим (опції live немає, ОВ-4) | owl |
| AC-29 | `models/bi_dashboard_share.py` (`snapshot_attachment_id`, без live-полів) — модель підтримує лише frozen | method |
| AC-30 | `models/bi_dashboard_share.py::action_revoke()` (`active=False`) + `controllers/main.py::/bi/share` — деактивований/архівований запис → «посилання недійсне», знімок не віддається | method |
| AC-30 | `tests/test_ac30_share_instant_revoke.py` — після `action_revoke` той самий URL → сторінка-помилка | test |
| AC-31 | `views/bi_dashboard_views.xml` / `static/src/js/components/widget_container/` — пункти експорту з `groups="base.group_allow_export"` (`invisible` без права) | view |
| AC-31 | `controllers/main.py::/bi/export/xlsx` + `/bi/export/pdf` (`auth='user'`, `readonly=True`) — перевірка `base.group_allow_export`; прямий виклик без права → `AccessError`, файл не формується | controller |
| AC-31 | `tests/test_ac31_export_no_permission.py` — прямий виклик контролера експорту без права → `AccessError` | test |
| AC-32 | `controllers/main.py::/bi/export/pdf` + `report/bi_dashboard_templates.xml` (QWeb + wkhtmltopdf) — фільтри в колонтитулі, графіки растром (`chart.toBase64Image()`), без розрізання віджетів | controller |
| AC-33 | `models/bi_subscription.py::_cron_run_subscriptions()` → `models/bi_dashboard.py::render_snapshot(filters, as_user)` під `with_user(recipient)` — PDF за правами кожного отримувача ∧ фільтри підписки | method |
| AC-33 | `tests/test_ac33_subscription_per_recipient.py` — кожен внутрішній отримувач отримує знімок свого зрізу | test |
| AC-34 | `models/bi_subscription.py::_cron_run_subscriptions()` — try/except навколо рендера: збій → лист не надсилається, помилка в журнал, наступний запуск за розкладом (`_commit_progress`) | method |
| AC-34 | `tests/test_ac34_subscription_render_fail.py` — збій рендера не шле лист, логується, стан не «зависає» | test |
| AC-35 | `models/bi_alert.py::_cron_check_alerts()` — троттлінг `daily`; запис у `td.bi.alert.log`; одне сповіщення за день | method |
| AC-35 | `tests/test_ac35_alert_throttle.py` — двічі за день → одне сповіщення, обидва спрацювання в журналі | test |
| AC-36 | `controllers/main.py::/bi/export/xlsx` (`xlsxwriter`) + `models/bi_query_compiler.py` (`GROUPING SETS`) — структура pivot/підсумки збережені, числа як числові, валюта відформатована | controller |
| AC-37 | `controllers/main.py::/bi/export/xlsx` — порожня вибірка → файл лише з заголовками, без падіння | controller |
| AC-37 | `tests/test_ac37_export_empty.py` — нуль рядків → коректний файл без помилки | test |
| AC-38 | `models/bi_query_compiler.py::compile_blend_query()` (`td.bi.query.compiler`) — CTE-бленд: `left outer` зберігає рядок без пари (витрати NULL), `inner` — ні | engine |
| AC-38 | `views/bi_dataset_views.xml` (`BlendEditor`) — `join_type` обмежено `left`/`inner` (`right`/`full`/`cross` недоступні, етап 3) | view |
| AC-38 | `tests/test_ac38_blend_join_type.py` — товар без пари присутній у `left outer`, відсутній у `inner` | test |
| AC-39 | `models/bi_query_compiler.py::compile_blend_query()` / `_inject_record_rules()` — кожен CTE бленда отримує домен record rules користувача через `Model._search(domain)` як підзапит у WHERE | engine |
| AC-39 | `tests/test_ac39_blend_rls_per_cte.py` — суми бленда різні за правами двох користувачів, конфігурація одна | test |
| AC-40 | `models/bi_dataset.py` (`@api.constrains` на `join_ids`) / `static/src/js/components/blend_editor/` — ліміт ≤5 таблиць → `UserError` «Бленд підтримує не більше 5 таблиць-джерел» | method |
| AC-40 | `tests/test_ac40_blend_table_limit.py` — 6-та таблиця блокується `UserError`, конфіг не змінюється | test |
| AC-41 | `static/src/js/components/blend_editor/` (`BlendEditor`) — попередження «додайте унікальний ключ у виміри таблиці…» при відсутньому ключі предагрегації | owl |
| AC-42 | `models/bi_query_compiler.py::compile_model_query()` + `models/bi_measure.py` (`time_intelligence=yoy`) — зсув домену дат на 1 рік, другий «примарний» ряд, дельта (абс. і %) | engine |
| AC-43 | `models/bi_query_compiler.py::compile_model_query()` — групування за тижнем за `lang.week_start` користувача (ВИМ-50) | engine |
| AC-43 | `tests/test_ac43_week_start_by_lang.py` — межі тижнів відповідають `week_start` мови кожного користувача | test |
| AC-44 | `static/src/js/components/measure_panel/` (`MeasurePanel`) — вкладка «Дані» ховає/деактивує часовий інтелект без виміру-дати з підказкою «потрібен вимір-дата» | owl |
| AC-44 | `models/bi_measure.py` (`@api.constrains` `time_intelligence`) — заборона ввімкнути порівняння періодів без поля дати у датасеті | method |
| AC-45 | `static/src/js/components/widget_renderer/` — застосування `config.style.conditional_rules[]` у порядку списку (порядок = пріоритет) | owl |
| AC-46 | `static/src/js/components/widget_renderer/` — поріг з іншої міри; NULL-поріг → правило не застосовується (базовий стиль), решта рядків коректна, без падіння | owl |
| AC-47 | `tests/test_ac47_tti_budget.py` — перф-смоук: TTI ≤5с (теплий кеш)/≤20с (холодний), пам'ять ≤300МБ на дашборд з 10 віджетів, 5 млн рядків | test |
| AC-48 | `tests/test_ac48_widget_interaction_budget.py` — відгук віджета ≤1.5с, інтерактив ≤2с, 50 паралельних глядачів — деградація ≤2× | test |
| AC-49 | `models/bi_dataset.py::run_query()` — `statement_timeout` (30с) на курсор; таймаут → `UserError` (картка помилки з «повторити»), стан не змінюється | method |
| AC-49 | `static/src/js/components/widget_container/` — картка помилки з кнопкою «повторити»; решта віджетів працює; повтор не дублює ефект | owl |
| AC-49 | `tests/test_ac49_statement_timeout.py` — перевищення `statement_timeout` → картка помилки, без краху | test |
| AC-50 | `security/td_bi_dashboard_security.xml` (record rule) + `views/bi_dataset_views.xml` — режим `mode=sql` і поле `sql_query` редагує/створює лише `group_bi_admin` (інакше дія недоступна) | security |
| AC-50 | `models/bi_dataset.py` (`@api.constrains`/`create`/`write` для `mode=sql`) — не-адмін → `AccessError`; адміну попередження «record rules не діють», `statement_timeout`, журнал `sql_run` в `td.bi.audit.log` | method |
| AC-50 | `tests/test_ac50_sql_dataset_admin_only.py` — не-адмін → `AccessError`; адмін бачить попередження, текст запиту в аудиті | test |
| AC-51 | `controllers/main.py` (`?bi_params=`) + `models/bi_parameter.py` (`url_changeable` білий список, валідація типу) — параметр поза списком ігнорується, невідповідний тип → `ValidationError`; bind-параметри в SQL, валідація типу в домени | controller |
| AC-51 | `tests/test_ac51_url_params_whitelist.py` — параметр поза білим списком ігнорується; невідповідний тип відхиляється | test |
| AC-52 | `static/src/js/components/widget_container/` — помилка одного віджета → картка з «повторити», решта віджетів відрендерена (деградація замість відмови); повтор перезапитує лише цей віджет | owl |
| AC-52 | `tests/test_ac52_widget_error_isolation.py` — один віджет з помилкою не валить сторінку | test |
| AC-53 | `models/bi_query_compiler.py::compile_model_query()` (`currency_strategy=historical`) — `formatted_read_group` з групуванням за валютою + `_convert(amount, env.company.currency_id, env.company, date)` на дату документа (патерн `sale.report`) | engine |
| AC-53 | `tests/test_ac53_currency_historical.py` — суми за курсом дати документа; звір із `sum_currency` відрізняється для «старого» курсу, збігається для актуального | test |
| AC-54 | `models/bi_query_compiler.py::compile_model_query()` (`currency_strategy=group_by_currency`) — групування за валютою без `_convert` (кожна валюта окремим рядком/серією) | engine |
| AC-54 | `models/bi_dataset.py::run_query()` — `sum_currency`/`historical` без `currency_field` → `UserError` «Стратегія конвертації потребує визначеного поля валюти (`currency_field`) для monetary-міри.», стан не змінюється | method |
| AC-54 | `tests/test_ac54_currency_group_and_missing_field.py` — розбиття за валютою без конвертації; межовий шлях без `currency_field` → `UserError` | test |
| AC-55 | `static/src/js/components/measure_panel/` (`QuickMeasureWizard`) + `models/bi_measure.py` — генерує редаговану `td.bi.measure` `show_as=percent_of_total` (видима в `MeasurePanel`); пункт «YoY %» неактивний без поля дати | owl |
| AC-55 | `models/bi_query_compiler.py::compile_model_query()` — «% від підсумку» рахується через `GROUPING SETS` (детальні рядки + підсумок одним SQL, ділення на сервері; сума часток = 100%) | engine |
| AC-55 | `tests/test_ac55_quick_measure_percent_total.py` — створено редаговану міру, сума часток = 100%; швидка міра з виміром-датою неактивна без поля дати | test |
| AC-56 | `static/src/js/components/widget_renderer/` (`GeoWidget`) — хороплет розфарбовує регіони TopoJSON за мірою `sum` (інтенсивність ∝ значенню), легенда min→max | owl |
| AC-56 | `static/src/js/components/widget_renderer/` (`GeoWidget`) — нерозпізнаний/порожній код країни → нейтральний колір + категорія «Інше», рендер не падає, виняток не кидається | owl |
| AC-57 | `models/bi_control.py` (`create`/`write` контролю) — генерація `td.bi.control.mapping` per-датасет, автосопоставлення `field_path` за технім'ям/типом; `enabled=True` за замовч. | method |
| AC-57 | `static/src/js/components/control_bar/` (`ControlBar`) — ручне перевизначення `field_path` має пріоритет над авто (не перезатирається); `enabled=False` виключає датасет; порожній `field_path` пропускається без падіння | owl |
| AC-57 | `tests/test_ac57_control_mapping.py` — авто `date_order`/`invoice_date`; ручний `commitment_date` зберігається; `crm.lead` з порожнім `field_path` пропускається | test |
| AC-58 | `models/bi_control.py` (`cascade=True`, `control_type=hierarchical`) + `static/src/js/components/control_bar/` (`ControlBar`) — домен `[('categ_id','child_of',<id>)]`, каскадний перерахунок залежного контролю через `name_search` (поважає `ir.rule`) | owl |
| AC-58 | `tests/test_ac58_hierarchical_cascade.py` — `child_of` дає піддерево; порожнє піддерево → порожній список без падіння; зняття вибору → повний набір | test |
| AC-59 | `models/bi_dashboard.py` (toggle «Опублікувати для всіх») / `static/src/js/components/share_dialog/` — створює рівно один `td.bi.dashboard.access` (`group_id=base.group_user`, `role=viewer`), idempotent; вимкнення видаляє запис | method |
| AC-59 | `security/td_bi_dashboard_security.xml` — record rule «published-global» — член `base.group_user` бачить дашборд лише для читання | security |
| AC-59 | `models/bi_dashboard.py` (toggle) — без прав власника/editor спроба перемкнути → `AccessError`, запис не створюється/не видаляється | method |
| AC-59 | `tests/test_ac59_publish_all_employees.py` — idempotent access, viewer-видимість через `with_user`, вимкнення ховає, не-власник → `AccessError` | test |
| AC-60 | `models/bi_dashboard.py` (toggle «Показувати в меню») — автогенерація `ir.actions.client`+`ir.ui.menu`, `menu_id` (`ondelete='set null'`), `groups_id` = групи доступу; зняття видаляє `ir.ui.menu` | method |
| AC-60 | `static/src/js/components/bi_dashboard_action/` (`td_bi_dashboard.dashboard_action`) — клік по застарілому пункту → `UserError` «Дашборд недоступний або видалений», інтерфейс не падає | owl |
| AC-60 | `models/bi_dashboard.py` (toggle) — без прав на `ir.ui.menu` → `AccessError`, прапор лишається вимкненим, `menu_id` порожній | method |
| AC-60 | `tests/test_ac60_show_in_menu.py` — генерація меню/дії, видимість за `groups_id` через `with_user`, безпечне зняття/видалення, `AccessError` без прав | test |
| AC-61 | `models/bi_subscription.py::action_send_now()` → `models/bi_dashboard.py::render_snapshot()` під `with_user(recipient)` — знімок від імені кожного отримувача (дані = його права ∧ фільтри); без помітки «від імені автора» для внутрішніх | method |
| AC-61 | `models/bi_subscription.py::action_send_now()` — отримувач без доступу → порожній знімок без витоку; збій одного логується (`_logger`) і не блокує інших, кнопка завершується без падіння | method |
| AC-61 | `tests/test_ac61_send_now_per_recipient.py` — U1/U2 різні цифри, порожній знімок без витоку, збій одного не блокує іншого | test |
| AC-62 | `models/bi_query_compiler.py::route_query()` (роутер `run_query`) — накритий запит обслуговується з `td.bi.materialization.table_name`, RLS через вимір-ключ правила; ненакритий → fallback на `formatted_read_group` (числово ідентично) | engine |
| AC-62 | `tests/test_ac62_materialization_coverage.py` — накритий запит читає предагрегат за правами; ненакритий падає назад без розбіжності/винятку | test |
| AC-63 | `models/bi_materialization.py::_compute_is_rls_safe()` + `create` — RLS-небезпечна конфігурація → `is_rls_safe=False`, `UserError` (дослівний текст), запис/MV не створюється | method |
| AC-63 | `tests/test_ac63_materialization_rls_refusal.py` — без виміру-ключа правила → `UserError` і стан БД незмінний; додавання `team_id` → `is_rls_safe=True`, запис створюється | test |
| AC-64 | `models/bi_dataset.py::run_query()` + `models/bi_query_compiler.py::build_effective_domain()` — ефективний домен трьох рівнів виключно через `Domain.AND([dataset, control, widget])` (Python); парс текстових доменів `ast.literal_eval`; білий список динамічних дат | method |
| AC-64 | `static/src/js/services/bi_data_service.js` (`biDataService`) — клієнтська склейка через `Domain.and(...)`, без конкатенації списків; OR-префікс лишається ізольованим у своєму рівні | owl |
| AC-64 | `models/bi_query_compiler.py::build_effective_domain()` (валідація динамічних дат) — синтаксис поза білим списком → `ValidationError`, віджет не рендериться зі зміненими даними | method |
| AC-64 | `tests/test_ac64_domain_and_conjunction.py` — кон'юнкція трьох рівнів; OR-атака нейтралізується; недозволений синтаксис дати → `ValidationError` | test |
| AC-65 | `models/bi_dataset.py::validate_integrity()` — видалення поля-споживача блокується `UserError` з переліком віджетів; поле/`version` не змінюються | method |
| AC-65 | `models/bi_dataset.py` (computed `version` bump при дозволеній зміні) — `version` входить у ключ кешу → інвалідація застарілого кешу для всіх дашбордів-споживачів | method |
| AC-65 | `security/td_bi_dashboard_security.xml` — record rule `td.bi.dataset` за `visibility` (private/groups/global) — глядач без прав рівня видимості не бачить датасет | security |
| AC-65 | `tests/test_ac65_dataset_integrity_version.py` — блок видалення з переліком віджетів; bump `version` інвалідує кеш; перевикористання за `visibility` | test |

### Open technical decisions

- Конкретні імена файлів моделей/OWL-компонентів у таблиці виведено за стандартом Odoo 19 (`models/`, `controllers/`, `security/`, `views/`, `report/`, `static/src/js/...`, `tests/`). Імена `*.py`-моделей (наприклад `models/bi_dataset.py`) та назви OWL-компонентів — пропозиція; фінальні шляхи зафіксує крок scaffolding. SPEC дослівно фіксує лише: моделі `td.bi.*`, методи (`run_query`, `get_fields_tree`, `validate_integrity`, `action_publish`, `render_snapshot`, `action_restore_to_draft`, `action_publish_this`, `action_revoke`, `_compute_full_url`, `action_send_now`, `_cron_run_subscriptions`, `_cron_check_alerts`, `action_view_trigger_log`, `_cron_clear_expired`, `_build_cache_key`, `init`, `_compute_is_rls_safe`, `action_refresh`/`_cron_refresh`), групи `group_bi_user`/`group_bi_designer`/`group_bi_admin`, роути `/bi/share/<int:share_id>/<token>`, `/bi/embed/<id>`, `/bi/export/xlsx`, `/bi/export/pdf`, дію `td_bi_dashboard.dashboard_action`, компоненти `biDataService`/`ControlBar`/`GeoWidget`/`ShareDialog`/`VersionHistory`/`MeasurePanel`/`BlendEditor` та адаптер `td.bi.query.compiler`.
- Рядки з Type `engine` віднесено до **єдиного адаптера** `models/bi_query_compiler.py` (модель `td.bi.query.compiler`, SPEC §2.1.3/§2.4) — окремого `engine/`-пакета НЕМАЄ: компіляція model/blend, роутер `run_query` для матеріалізації (AC-62), DSL-компіляція/валідація (AC-09/10/13) і `Domain.AND`-склейка доменів (AC-64) інкапсульовані в цьому адаптері. SPEC не визначає окремих публічних методів моделей `td.bi.measure`/`td.bi.dataset.join` — логіка мір/бленда/часового інтелекту/мультивалютності реалізується адаптером; точний розподіл «метод моделі vs. метод адаптера» SPEC лишає відкритим (позначено в SPEC як «потребує уточнення розподілу методів»).
- Методи-носії DSL-валідації (AC-09/AC-10/AC-13) і доменної безпеки (AC-64) у SPEC не названі іменем — мапінг на `td.bi.query.compiler.compile_formula()`/`build_effective_domain()` (адаптер) + `@api.constrains` на `td.bi.measure`/`td.bi.dataset.field` є пропозицією, що випливає з §2.4.2/§2.4.3; підтвердити в scaffolding.
- Назву публічного методу GROUPING SETS (`formatted_read_grouping_sets`), нативний агрегат `sum_currency`, `Model._search(domain)` як точку record-rule-підзапиту і життєвий цикл `_auto=False`/`init()`/`REFRESH MATERIALIZED VIEW CONCURRENTLY` SPEC позначає як build-time confirmations Odoo 19 (не блокують, підтвердити на цільовій збірці 19.0; фіксувати в DEVIATIONS). Це впливає на реалізацію рядків AC-08, AC-36, AC-39, AC-53, AC-55, AC-62, AC-63.