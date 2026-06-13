# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class TdBiDashboard(models.Model):
    _name = 'td.bi.dashboard'
    _description = 'BI: Дашборд'
    _inherit = ['mail.thread']
    _order = 'name, id'
    # Since: 19.0.1.0.0

    # === Fields ===
    name = fields.Char(string="Назва", required=True, translate=True)
    description = fields.Text(string="Опис")
    tag_ids = fields.Many2many('td.bi.dashboard.tag', string="Теги")
    group_folder_id = fields.Many2one('td.bi.dashboard.group', string="Розділ каталогу")
    page_ids = fields.One2many('td.bi.dashboard.page', 'dashboard_id', string="Сторінки")
    control_ids = fields.One2many('td.bi.control', 'dashboard_id', string="Глобальні контроли")
    theme_id = fields.Many2one('td.bi.theme', string="Тема оформлення")
    theme_overrides = fields.Json(string="Правки теми")
    interaction_matrix = fields.Json(string="Матриця взаємодій")  # cross-filter (AC-15)
    state = fields.Selection(
        [('draft', 'Чернетка'), ('published', 'Опубліковано'), ('archived', 'Архів')],
        string="Стан", default='draft', tracking=True,
    )
    published_version_id = fields.Many2one(
        'td.bi.dashboard.version', string="Опублікована версія",
    )  # AC-25, AC-28
    owner_id = fields.Many2one(
        'res.users', string="Власник", default=lambda self: self.env.user,
    )
    access_ids = fields.One2many(
        'td.bi.dashboard.access', 'dashboard_id', string="Доступи",
    )  # AC-59
    company_ids = fields.Many2many('res.company', string="Компанії")
    favorite_user_ids = fields.Many2many('res.users', string="В обраному")
    menu_id = fields.Many2one('ir.ui.menu', string="Пункт меню", ondelete='set null')  # AC-60
    default_state = fields.Json(string="Стан за замовчуванням")
    thumbnail = fields.Image(string="Мініатюра")

    # === Constraints ===
    # SPEC: SQL constraints — None.

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Create ===
    @api.model_create_multi
    def create(self, vals_list):
        """Створення дашборда(ів).  # TODO: AC-59, AC-60 — публікація/меню при налаштуванні."""
        # TODO: AC-59 — idempotent-доступ «для всіх співробітників».
        # TODO: AC-60 — генерація ir.ui.menu/ir.actions.client за прапором «показувати в меню».
        return super().create(vals_list)

    # === Actions ===
    def action_publish(self):
        """Створює знімок td.bi.dashboard.version і перемикає state -> published.
        Given редактор за state=='draft' -> створюється td.bi.dashboard.version
        (config_snapshot, is_published_snapshot=True), state='published',
        viewer бачить опубліковану версію без редагування (ВИМ-41)."""
        self.ensure_one()
        # TODO: AC-25 — viewer бачить публікацію без кнопки редагування, editor — чернетку.
        # TODO: AC-28 — історія версій із відкатом; знімок поточної конфігурації.
        return True

    def get_runtime_config(self):
        """Повертає повну runtime-конфігурацію дашборда одним RPC (§2.4).

        Контракт фронтенду Stage-1 (get_runtime_config):
          {id, name, pages:[{id,name,widgets:[{id,widget_type,title,dataset_id,
           config,pos_x,pos_y,width,height}]}], controls:[...], theme:{}}

        Виконується ВІД ІМЕНІ користувача (без sudo): self вже відфільтрований
        record rules доступу до дашборда; читаємо лише дозволені рядки сторінок,
        віджетів і контролів — приховані за правами рядки просто не потрапляють у
        вихід. Якщо на сторінці немає віджетів — widgets порожній; якщо немає
        сторінок — pages порожній (AC-31/AC-32 контекст; AC-20/AC-52 деградація
        per-віджет робиться на фронтенді — сервер віддає лише видимі рядки).
        """
        self.ensure_one()
        # AC-20 — деградація per-віджет (картка «нема доступу»), сторінка не падає:
        #         сервер повертає лише дозволені рядки, рендер кожного віджета
        #         фронтенд огортає у try/catch.
        # AC-52 — помилка одного віджета не зупиняє сторінку (per-віджет рендер).

        # Сторінки в порядку sequence; приховані не віддаємо у runtime (is_hidden).
        pages = []
        for page in self.page_ids.sorted(lambda p: (p.sequence, p.id)):
            if page.is_hidden:
                continue
            widgets = []
            for widget in page.widget_ids.sorted(lambda w: (w.sequence, w.id)) \
                    if 'widget_ids' in page._fields else self._page_widgets(page):
                widgets.append({
                    'id': widget.id,
                    'widget_type': widget.widget_type or False,
                    'title': widget.title or '',
                    'dataset_id': widget.dataset_id.id if widget.dataset_id else False,
                    'config': self._coerce_json(widget.config, {}),
                    'domain': widget.domain or '',
                    'pos_x': widget.pos_x or 0,
                    'pos_y': widget.pos_y or 0,
                    'width': widget.width or 0,
                    'height': widget.height or 0,
                })
            pages.append({
                'id': page.id,
                'name': page.name or '',
                'is_drillthrough': bool(page.is_drillthrough),
                'widgets': widgets,
            })

        # Контроли: глобальні (на дашборді) + сторінкові; приховані не віддаємо.
        controls = []
        for control in self.control_ids.sorted(lambda c: (c.sequence, c.id)):
            if control.is_hidden:
                continue
            controls.append(self._control_runtime_dict(control))
        for page in self.page_ids:
            for control in page.control_ids.sorted(lambda c: (c.sequence, c.id)):
                if control.is_hidden:
                    continue
                controls.append(self._control_runtime_dict(control, page_id=page.id))

        return {
            'id': self.id,
            'name': self.name or '',
            'pages': pages,
            'controls': controls,
            'theme': self._theme_runtime_dict(),
        }

    def _page_widgets(self, page):
        """Віджети сторінки ВІД ІМЕНІ користувача (запасний шлях, якщо немає
        зворотного O2M widget_ids на сторінці). Record rules td.bi.widget
        застосовуються автоматично — недоступні рядки відсіються."""
        return self.env['td.bi.widget'].search(
            [('page_id', '=', page.id)], order='sequence, id')

    @staticmethod
    def _coerce_json(val, default):
        """Json-поле, записане з XML, може повернутись рядком (подвійне кодування).
        Нормалізуємо у dict/list; некоректне -> default. Гарантує фронтенду структуру, а не рядок."""
        import json
        if val in (None, False, ''):
            return default
        if isinstance(val, str):
            try:
                return json.loads(val)
            except (ValueError, TypeError):
                return default
        return val

    def _control_runtime_dict(self, control, page_id=False):
        """Серіалізація контролу у runtime-словник для фронтенду (bi_page_state).
        Несе field (поле фільтрації: layout.field АБО перший mapping) і options для UI."""
        layout = self._coerce_json(control.layout, {})
        mapping = control.mapping_ids[:1]
        field = layout.get('field') or (mapping.field_path if mapping else False)
        return {
            'id': control.id,
            'control_type': control.control_type or False,
            'label': control.label or '',
            'default_value': self._coerce_json(control.default_value, False),
            'is_locked': bool(control.is_locked),
            'cascade': bool(control.cascade),
            'group_key': control.group_key or False,
            'page_id': page_id or (control.page_id.id if control.page_id else False),
            'layout': layout,
            'config': layout,
            'field': field,
            'options': layout.get('options') or [],
        }

    def _theme_runtime_dict(self):
        """Тема дашборда у вигляді dict (палітра/шрифти) з накладанням theme_overrides.
        Якщо тема не задана — беремо системну за замовчуванням (is_default=True)."""
        theme = self.theme_id
        if not theme:
            theme = self.env['td.bi.theme'].search([('is_default', '=', True)], limit=1)
        config = self._coerce_json(theme.config, {}) if theme else {}
        if not isinstance(config, dict):
            config = {}
        overrides = self._coerce_json(self.theme_overrides, {})
        if isinstance(overrides, dict):
            config.update(overrides)
        return config

    def action_open(self):
        """Відкриває дашборд клієнтською дією (ir.actions.client, тег 'bi_dashboard').

        Передає dashboard_id у params — BiDashboardAction._resolveDashboardId()
        читає action.params.dashboard_id і монтує дашборд у режимі перегляду
        (без каталогу). Викликається кнопкою «Відкрити дашборд» форми та з kanban.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'bi_dashboard',
            'name': self.name or _("Дашборд"),
            'params': {'dashboard_id': self.id},
        }

    def copy(self, default=None):
        """ORM override: дублювання зі сторінками/віджетами/контролами."""
        # TODO: AC-28 — глибоке копіювання конфігурації дашборда.
        return super().copy(default=default)

    def render_snapshot(self, filters, as_user):
        """Серверний знімок даних під with_user(as_user); frozen-посилання/підписки/PDF.
        Given frozen-посилання/підписка -> вкладення = права отримувача ∧ фільтри (ВИМ-43)."""
        self.ensure_one()
        # TODO: AC-26 — рендер знімка без живих запитів до бізнес-моделей.
        # TODO: AC-32 — PDF: активні фільтри в колонтитулі, графіки растром, без розрізання.
        # TODO: AC-47 — TTI/перф-бюджет дашборда.
        # TODO: AC-48 — одиночний віджет/інтерактив у межах бюджету.
        # TODO: AC-59 — публікація «для всіх співробітників».
        # TODO: AC-60 — пункт меню/видимість за групами.
        return False
