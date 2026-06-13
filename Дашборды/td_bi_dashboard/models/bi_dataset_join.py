# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BiDatasetJoin(models.Model):
    _name = 'td.bi.dataset.join'
    _description = 'BI Таблиця бленда'
    _order = 'sequence, id'

    # === Fields ===
    dataset_id = fields.Many2one(
        'td.bi.dataset', string="Бленд-датасет", ondelete='cascade',
    )
    sequence = fields.Integer(string="Послідовність")
    source_dataset_id = fields.Many2one(
        'td.bi.dataset', string="Джерело-датасет",
    )
    source_model_id = fields.Many2one('ir.model', string="Джерело-модель")
    table_domain = fields.Text(string="Локальний домен")
    table_date_field = fields.Char(string="Поле дати таблиці")
    join_type = fields.Selection(
        [
            ('left', 'Left outer'),
            ('inner', 'Inner'),
            ('right', 'Right'),
            ('full', 'Full'),
            ('cross', 'Cross'),
        ],
        string="Тип зʼєднання",
    )
    key_ids = fields.One2many(
        'td.bi.dataset.join.key', 'join_id', string="Ключі зʼєднання",
    )
    included_field_ids = fields.Many2many(
        'td.bi.dataset.field', string="Включені поля",
    )

    # === SQL constraints ===
    # SPEC: SQL-constraints для td.bi.dataset.join не задано.
    # Обмеження «один з: source_dataset_id АБО source_model_id» та ліміт ≤ 5 таблиць —
    # реалізуються через @api.constrains нижче.

    # === Constraints ===
    @api.constrains('source_dataset_id', 'source_model_id', 'dataset_id', 'join_type')
    def _check_blend(self):
        """Валідація конфігурації таблиці бленда.
        AC-38 — left outer і inner дають різний набір рядків; right/full/cross недоступні
        AC-40 — перевищення ліміту 5 таблиць-джерел блокується
        AC-41 — попередження (не блокуюче) про відсутній унікальний вимір-ключ предагрегації
        """
        import logging
        _logger = logging.getLogger(__name__)
        for join in self:
            # AC-38: лише left/inner; right/full/cross — етап 3 (ОВ-6).
            if join.join_type and join.join_type not in ('left', 'inner'):
                raise ValidationError(_(
                    "Тип зʼєднання «%s» недоступний — лише left/inner.", join.join_type))
            # Рівно одне джерело: модель АБО вкладений датасет.
            if bool(join.source_model_id) == bool(join.source_dataset_id):
                raise ValidationError(_(
                    "Таблиця бленда «%s» має мати рівно ОДНЕ джерело: модель АБО датасет.",
                    join.dataset_id.name or ''))
            # AC-40: ≤ 5 таблиць-джерел бленда.
            if join.dataset_id and len(join.dataset_id.join_ids) > 5:
                raise ValidationError(_("Бленд підтримує не більше 5 таблиць-джерел."))
            # AC-41: попередження, якщо джерело не має виміру-ключа предагрегації (рядки можуть
            # розмножитись на зʼєднанні). Не блокуємо (за формулюванням SPEC — попередження).
            if join.included_field_ids and not any(
                    f.role == 'dimension' for f in join.included_field_ids):
                _logger.warning(
                    "BI blend: джерело без виміру-ключа предагрегації у датасеті «%s» "
                    "(рядки можуть розмножитись на зʼєднанні, AC-41).",
                    join.dataset_id.name or '')
        return True
