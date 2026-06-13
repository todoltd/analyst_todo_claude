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

    def render_snapshot(self, filters=None, as_user=None):
        """Серверний знімок ДАНИХ дашборда ВІД ІМЕНІ отримувача (RLS ∧ фільтри, ВИМ-43).

        Повертає структуру {id, name, pages:[{id,name,widgets:[{id,title,data}]}]}, де data —
        результат run_query кожного віджета, виконаний with_user(as_user) (права отримувача,
        без sudo на бізнес-даних). Помилка одного віджета локалізується у його data.error
        (AC-20/AC-61 — збій не валить увесь знімок). filters (Json) додаються як control_domain.

        Рендер у PDF/XLSX поверх цього знімка — наступний крок (підписки format=pdf/xlsx);
        формат 'link'/дані-знімок повністю готові тут (AC-26 — без повторних живих запитів
        у споживача: дані вже у знімку)."""
        self.ensure_one()
        user = as_user or self.env.user
        dash = self.with_user(user)
        config = dash.get_runtime_config()
        flat_filter = self._coerce_json(filters, []) if filters else []
        if isinstance(flat_filter, dict):
            flat_filter = flat_filter.get('domain') or []
        pages_out = []
        for page in config.get('pages', []):
            widgets_out = []
            for widget in page.get('widgets', []):
                data = None
                if widget.get('dataset_id'):
                    try:
                        spec = self._snapshot_widget_spec(widget, flat_filter)
                        data = self.env['td.bi.dataset'].with_user(user).browse(
                            widget['dataset_id']).run_query(spec)
                    except Exception as exc:  # noqa: BLE001 — локалізуємо збій віджета
                        data = {'error': str(exc)}
                widgets_out.append({
                    'id': widget.get('id'), 'title': widget.get('title') or '', 'data': data,
                })
            pages_out.append({
                'id': page.get('id'), 'name': page.get('name') or '', 'widgets': widgets_out,
            })
        return {'id': self.id, 'name': config.get('name') or '', 'pages': pages_out}

    def _snapshot_widget_spec(self, widget, flat_filter):
        """querySpec віджета для знімка: config.data (groupby/measures/aggregates) +
        фіксовані фільтри підписки як control_domain (плоский список умов = неявне І)."""
        cfg = self._coerce_json(widget.get('config'), {})
        data = cfg.get('data') if isinstance(cfg, dict) else None
        data = data or (cfg if isinstance(cfg, dict) else {})
        spec = {
            'groupby': data.get('groupby') or [],
            'measures': data.get('measures') or [],
            'aggregates': data.get('aggregates') or [],
        }
        if data.get('limit') is not None:
            spec['limit'] = data['limit']
        if flat_filter:
            spec['control_domain'] = list(flat_filter)
        return spec

    def snapshot_has_data(self, snapshot):
        """Чи містить знімок хоч один віджет із непорожніми рядками (для only_if_data)."""
        for page in (snapshot or {}).get('pages', []):
            for widget in page.get('widgets', []):
                data = widget.get('data') or {}
                if isinstance(data, dict) and data.get('rows'):
                    return True
        return False

    # === Експорт (AC-31/32/36/37) ===
    @staticmethod
    def _snapshot_widget_columns(widget):
        """Колонки віджета знімка: ключі першого рядка без службових (__*) АБО header-only
        зі стилю/спеки (AC-37 — порожня вибірка дає файл лише із заголовками)."""
        data = widget.get('data') or {}
        rows = data.get('rows') or []
        if rows and isinstance(rows[0], dict):
            return [k for k in rows[0].keys() if not str(k).startswith('__')
                    and k not in ('extra_domains',)]
        return list(data.get('groupby') or []) + list(data.get('measures') or [])

    @staticmethod
    def _cell_scalar(value):
        """Скаляр для комірки: m2o [id,label]->label; tuple дати->мітка; інше як є."""
        if isinstance(value, (list, tuple)):
            return value[1] if len(value) > 1 else (value[0] if value else '')
        return value

    def export_xlsx(self, filters=None, as_user=None, snapshot=None):
        """Рендерить знімок дашборда у XLSX (xlsxwriter): один аркуш на віджет, рядки таблицею.
        Дані — ВІД ІМЕНІ as_user (RLS) АБО з готового snapshot (frozen-посилання). Порожня
        вибірка -> аркуш лише із заголовками (AC-37). AC-36 — числа лишаються числами."""
        self.ensure_one()
        import io
        import xlsxwriter
        snapshot = snapshot or self.render_snapshot(filters, as_user or self.env.user)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        bold = workbook.add_format({'bold': True})
        used_names = set()
        sheet_idx = 0
        for page in snapshot.get('pages', []):
            for widget in page.get('widgets', []):
                sheet_idx += 1
                raw = (widget.get('title') or 'Widget %d' % sheet_idx)
                # XLSX-обмеження імені аркуша: <=31 символ, без []:*?/\\, унікальне.
                name = ''.join(c for c in raw if c not in '[]:*?/\\')[:28] or 'Sheet'
                base, n = name, 1
                while name in used_names:
                    name = ('%s_%d' % (base[:26], n))[:31]
                    n += 1
                used_names.add(name)
                sheet = workbook.add_worksheet(name)
                cols = self._snapshot_widget_columns(widget)
                for c, col in enumerate(cols):
                    sheet.write(0, c, str(col), bold)
                rows = (widget.get('data') or {}).get('rows') or []
                for r, row in enumerate(rows, start=1):
                    for c, col in enumerate(cols):
                        val = self._cell_scalar(row.get(col))
                        if isinstance(val, (int, float)):
                            sheet.write_number(r, c, val)
                        elif val in (None, False):
                            sheet.write_blank(r, c, None)
                        else:
                            sheet.write_string(r, c, str(val))
        workbook.close()
        return output.getvalue()

    def _snapshot_html_doc(self, snapshot):
        """Самодостатній HTML-документ знімка (для PDF). Активні фільтри в підзаголовку (AC-32)."""
        parts = ['<!DOCTYPE html><html><head><meta charset="utf-8">',
                 '<style>body{font-family:sans-serif;font-size:11px}'
                 'table{border-collapse:collapse;margin:6px 0;width:100%}'
                 'th,td{border:1px solid #ccc;padding:3px 6px;text-align:left}'
                 'h1{font-size:16px}h2{font-size:13px}</style></head><body>']
        parts.append('<h1>%s</h1>' % (snapshot.get('name') or ''))
        for page in snapshot.get('pages', []):
            parts.append('<h2>%s</h2>' % (page.get('name') or ''))
            for widget in page.get('widgets', []):
                parts.append('<h3>%s</h3>' % (widget.get('title') or ''))
                cols = self._snapshot_widget_columns(widget)
                rows = (widget.get('data') or {}).get('rows') or []
                parts.append('<table><tr>%s</tr>' % ''.join('<th>%s</th>' % c for c in cols))
                for row in rows:
                    parts.append('<tr>%s</tr>' % ''.join(
                        '<td>%s</td>' % (self._cell_scalar(row.get(c)) if row.get(c) not in (None, False) else '')
                        for c in cols))
                parts.append('</table>')
        parts.append('</body></html>')
        return ''.join(parts)

    def export_pdf(self, filters=None, as_user=None, snapshot=None):
        """Рендерить знімок дашборда у PDF через wkhtmltopdf (HTML stdin -> PDF stdout).
        Дані — ВІД ІМЕНІ as_user (RLS) АБО з готового snapshot. AC-32 — таблиці віджетів."""
        self.ensure_one()
        import subprocess
        snapshot = snapshot or self.render_snapshot(filters, as_user or self.env.user)
        html = self._snapshot_html_doc(snapshot)
        try:
            proc = subprocess.run(
                ['wkhtmltopdf', '-q', '--encoding', 'utf-8', '-', '-'],
                input=html.encode('utf-8'), capture_output=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as exc:
            raise UserError(_("Не вдалося згенерувати PDF: %s", exc))
        if proc.returncode != 0 or not proc.stdout.startswith(b'%PDF'):
            raise UserError(_("wkhtmltopdf повернув помилку: %s",
                              (proc.stderr or b'').decode('utf-8', 'ignore')[:300]))
        return proc.stdout
