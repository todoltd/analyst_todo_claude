# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
from odoo import api, fields, models, _


class TdBiDashboardVersion(models.Model):
    _name = 'td.bi.dashboard.version'
    _description = 'BI: Версія дашборда (знімок конфігурації)'
    _order = 'create_date desc, id desc'
    # Since: 19.0.1.0.0
    # Примітка SPEC: автор/дата = create_uid/create_date (авто-поля ORM), окремих полів немає.

    # === Fields ===
    dashboard_id = fields.Many2one(
        'td.bi.dashboard', string="Дашборд", required=True, ondelete='cascade',
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
        """Відкат версії у чернетку.
        Given опубліковано v2, виконано відкат на v1 -> глядач після оновлення бачить v1;
        відновлює config_snapshot у поточну конфігурацію, dashboard.state='draft',
        історія версій (v1, v2) зберігається."""
        self.ensure_one()
        # TODO: AC-28 — відкат на попередню версію; історія з авторами/датами.
        return True

    def action_publish_this(self):
        """Повторна публікація знімка старої версії.
        Робить цей знімок поточним опублікованим (is_published_snapshot=True,
        dashboard.published_version_id=self, dashboard.state='published')."""
        self.ensure_one()
        # TODO: AC-28 — повторна публікація обраного знімка версії.
        return True
