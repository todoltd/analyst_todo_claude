# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BiParameter(models.Model):
    _name = 'td.bi.parameter'
    _description = 'BI Параметр'
    _order = 'id'

    # === Fields ===
    name = fields.Char(string="Технічне імʼя", required=True)
    label = fields.Char(string="Підпис", translate=True)
    dataset_id = fields.Many2one('td.bi.dataset', string="Датасет")
    dashboard_id = fields.Many2one('td.bi.dashboard', string="Дашборд")
    param_type = fields.Selection(
        [
            ('text', 'Текст'),
            ('number', 'Число'),
            ('boolean', 'Логічний'),
            ('selection', 'Список'),
            ('date', 'Дата'),
        ],
        string="Тип параметра",
    )
    permitted = fields.Selection(
        [
            ('any', 'Будь-яке'),
            ('list', 'Зі списку'),
            ('range', 'Діапазон'),
        ],
        string="Допустимі значення",
    )
    selection_values = fields.Json(string="Значення списку")
    min = fields.Float(string="Мінімум")
    max = fields.Float(string="Максимум")
    step = fields.Float(string="Крок")
    default_value = fields.Json(string="Значення за замовчуванням")
    url_changeable = fields.Boolean(string="Змінюваний з URL")

    # === SQL constraints ===
    # Odoo 19: models.Constraint замість _sql_constraints (deprecated)
    _one_owner = models.Constraint(
        'CHECK((dataset_id IS NOT NULL) <> (dashboard_id IS NOT NULL))',
        "Параметр має належати рівно одному: датасету АБО дашборду.",
    )

    # === Constraints ===
    @api.constrains('url_changeable', 'param_type', 'permitted', 'default_value',
                    'selection_values', 'min', 'max')
    def _check_url_value(self):
        """AC-51 — конфігурація URL-змінюваного параметра має бути валідно оголошена.

        Для url_changeable=True вимагаємо коректного оголошення (тип + допустимі
        значення), бо саме це оголошення — білий список, проти якого валідуються
        значення з URL у coerce_url_value(). Якщо оголошення неповне, значення з
        URL ніколи не пройдуть, тож блокуємо некоректну конфігурацію одразу.
        """
        for param in self:
            if not param.url_changeable:
                continue
            if not param.param_type:
                raise ValidationError(_(
                    "URL-змінюваний параметр «%s» мусить мати визначений тип.",
                    param.name or param.id,
                ))
            # Дефолт (якщо заданий) має сам проходити типову валідацію оголошення.
            if param.default_value is not None:
                try:
                    param._coerce_typed_value(param.default_value)
                except (UserError, ValidationError) as err:
                    raise ValidationError(_(
                        "Значення за замовчуванням параметра «%(name)s» некоректне: "
                        "%(err)s",
                        name=param.name or param.id,
                        err=err.args[0] if err.args else err,
                    ))
            if param.permitted == 'list' and not param.selection_values:
                raise ValidationError(_(
                    "Параметр «%s» з режимом «Зі списку» мусить мати список значень.",
                    param.name or param.id,
                ))
            if param.permitted == 'range' and param.param_type != 'number':
                raise ValidationError(_(
                    "Режим «Діапазон» доступний лише для числового параметра «%s».",
                    param.name or param.id,
                ))

    # === Compute === None

    # === Actions ===
    @api.model
    def coerce_url_value(self, declared_name, raw_value):
        """AC-51 — серверна валідація значення параметра, переданого з URL.

        Приймає лише оголошені параметри і лише ті, де url_changeable=True (білий
        список). Значення невідповідного типу або поза дозволеним набором/діапазоном
        відхиляється серверною валідацією. Повертає типізоване значення, готове до
        підстановки.

        Підстановка дозволених параметрів далі (контракт DSL/§2.4):
        - у SQL — ВИКЛЮЧНО bind-параметрами (`%s` / SQL placeholders), ніколи не
          конкатенацією тексту запиту; це закриває SQL-ін'єкцію через ?bi_params=.
        - у домени — лише ПІСЛЯ цієї типової валідації; значення вкладається як
          літерал у Domain-умову, а не як виконуваний вираз (без eval/safe_eval).

        :param declared_name: технічне імʼя параметра з ?bi_params=
        :param raw_value: сире значення з URL (рядок)
        :return: типізоване значення
        :raises ValidationError: параметр поза білим списком / значення невідповідне
        """
        param = self.search([('name', '=', declared_name)], limit=1)
        # Параметр поза білим списком (не оголошений) — ігнорується (AC-51).
        if not param:
            raise ValidationError(_(
                "Параметр «%s» не оголошено — значення з URL ігнорується.",
                declared_name,
            ))
        # Не дозволений до зміни з URL — ігнорується (білий список url_changeable).
        if not param.url_changeable:
            raise ValidationError(_(
                "Параметр «%s» не дозволено змінювати з URL.", declared_name,
            ))
        return param._coerce_typed_value(raw_value)

    def _coerce_typed_value(self, raw_value):
        """AC-51 — приводить сире значення до оголошеного типу і перевіряє домен значень.

        Типова валідація (text/number/boolean/selection/date) — обовʼязкова перед
        будь-якою підстановкою. Невідповідний тип/набір/діапазон -> ValidationError.
        """
        self.ensure_one()
        ptype = self.param_type
        if ptype == 'number':
            value = self._coerce_number(raw_value)
            self._check_range(value)
            return value
        if ptype == 'boolean':
            return self._coerce_boolean(raw_value)
        if ptype == 'date':
            return self._coerce_date(raw_value)
        if ptype == 'selection':
            value = raw_value if isinstance(raw_value, str) else str(raw_value)
            self._check_in_selection(value)
            return value
        # text (та будь-який нетипізований) — рядок; набір значень перевіряємо за potр.
        value = raw_value if isinstance(raw_value, str) else str(raw_value)
        if self.permitted == 'list':
            self._check_in_selection(value)
        return value

    def _coerce_number(self, raw_value):
        """Перетворює значення на float; невідповідний тип -> ValidationError (AC-51)."""
        self.ensure_one()
        if isinstance(raw_value, bool):
            raise ValidationError(_(
                "Параметр «%s» очікує число, отримано логічне значення.", self.name,
            ))
        try:
            return float(raw_value)
        except (TypeError, ValueError):
            raise ValidationError(_(
                "Значення «%(val)s» параметра «%(name)s» не є числом.",
                val=raw_value, name=self.name,
            ))

    def _coerce_boolean(self, raw_value):
        """Перетворює значення на bool за фіксованим словником; інакше ValidationError."""
        self.ensure_one()
        if isinstance(raw_value, bool):
            return raw_value
        text = str(raw_value).strip().lower()
        if text in ('1', 'true', 'yes', 'on'):
            return True
        if text in ('0', 'false', 'no', 'off'):
            return False
        raise ValidationError(_(
            "Значення «%(val)s» параметра «%(name)s» не є логічним.",
            val=raw_value, name=self.name,
        ))

    def _coerce_date(self, raw_value):
        """Перетворює значення на date (ISO) через field-парсер Odoo; інакше ValidationError."""
        self.ensure_one()
        if isinstance(raw_value, datetime.date):
            return raw_value
        try:
            # fields.Date.to_date поважає формат ISO та валідує коректність дати.
            value = fields.Date.to_date(raw_value)
        except (TypeError, ValueError):
            value = None
        if value is None:
            raise ValidationError(_(
                "Значення «%(val)s» параметра «%(name)s» не є коректною датою (ISO).",
                val=raw_value, name=self.name,
            ))
        return value

    def _check_range(self, value):
        """Числовий діапазон permitted='range': value у [min, max]; інакше ValidationError."""
        self.ensure_one()
        if self.permitted != 'range':
            return
        if self.min is not None and value < self.min:
            raise ValidationError(_(
                "Значення %(val)s параметра «%(name)s» менше за мінімум %(min)s.",
                val=value, name=self.name, min=self.min,
            ))
        if self.max is not None and value > self.max:
            raise ValidationError(_(
                "Значення %(val)s параметра «%(name)s» більше за максимум %(max)s.",
                val=value, name=self.name, max=self.max,
            ))

    def _check_in_selection(self, value):
        """permitted='list': value має бути серед оголошених selection_values; інакше ValidationError."""
        self.ensure_one()
        allowed = self._allowed_selection_values()
        if value not in allowed:
            raise ValidationError(_(
                "Значення «%(val)s» параметра «%(name)s» поза дозволеним списком.",
                val=value, name=self.name,
            ))

    def _allowed_selection_values(self):
        """Повертає множину дозволених значень зі selection_values ([{value,label}] або [value])."""
        self.ensure_one()
        raw = self.selection_values or []
        allowed = set()
        for item in raw:
            if isinstance(item, dict):
                allowed.add(item.get('value'))
            else:
                allowed.add(item)
        return allowed

    # SPEC: серверна валідація типу з URL і наслідування звіт→сторінка→група→віджет — движок (§2.1.5).
