# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo.
import ast

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.fields import Domain  # Odoo 19: первокласний Domain (Domain.AND для звуження видимості)


class TdBiDashboardAccess(models.Model):
    _name = 'td.bi.dashboard.access'
    _description = 'BI: Доступ до дашборда'
    _order = 'id'
    # Since: 19.0.1.0.0

    # === Fields ===
    dashboard_id = fields.Many2one(
        'td.bi.dashboard', string="Дашборд", required=True, ondelete='cascade',
    )
    user_id = fields.Many2one('res.users', string="Користувач")  # user_id XOR group_id
    group_id = fields.Many2one('res.groups', string="Група")  # base.group_user = «для всіх» (AC-59)
    role = fields.Selection(
        [('viewer', 'Перегляд'), ('editor', 'Редагування'), ('manager', 'Керування')],
        string="Роль",
    )  # AC-25, AC-59
    extra_domain = fields.Json(string="Домен аудиторії")  # {dataset_id: domain}; лише звужує (AC-21)
    active = fields.Boolean(string="Активне", default=True)

    # === Constraints ===
    # Odoo 19: models.Constraint замість _sql_constraints (deprecated)
    _exactly_one_subject = models.Constraint(
        'CHECK ((user_id IS NOT NULL) <> (group_id IS NOT NULL))',
        "Має бути заповнений рівно один із user_id/group_id (взаємовиключно).",
    )
    # AC-21 — extra_domain лише звужує видимість (Domain.AND з record rules).
    # AC-59 — рядок viewer для base.group_user; idempotent при повторному ввімкненні.

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    @api.model
    def get_audience_domain(self, dataset):
        """AC-21 — повертає домен аудиторії для датасету, що ЛИШЕ звужує видимість.

        Збирає extra_domain[dataset_id] з рядків доступу поточного користувача
        (особистих user_id і його груп group_id) до дашборда і повертає його як
        Domain. Цей домен далі склеюється з record rules ВИКЛЮЧНО по І (Domain.AND
        у движку run_query), тож аудиторія НЕ може розширити видимість понад те, що
        дозволяють record rules — лише додатково обмежити (AC-21).

        Декілька рядків аудиторії (наприклад, через різні групи) також з'єднуються
        через Domain.AND: домен користувача = ∧ усіх його аудиторій для цього
        датасету. Динамічні плейсхолдери user / company_id / company_ids
        підставляються як у контексті ir.rule (поточні значення сесії).

        Читання рядків доступу — від імені користувача через ORM (без sudo()):
        record rules самі обмежать видимі access-рядки. Якщо аудиторій немає,
        повертаємо порожній домен Domain.TRUE (нічого не звужує).

        :param dataset: recordset td.bi.dataset (1 запис) або його id
        :return: odoo.fields.Domain — звужувальний домен для цього датасету
        """
        dataset_id = dataset.id if hasattr(dataset, 'id') else int(dataset)
        user = self.env.user
        # DEVIATION(Odoo19): підтвердити імʼя поля груп користувача на збірці 19.0
        # (groups_id vs group_ids). Беремо доступним атрибутом із запасним шляхом.
        user_group_ids = self._user_group_ids(user)
        # Рядки доступу, релевантні поточному користувачу: персональні + за групами.
        # Domain.AND([...]) на двох рівнях замість ручної конкатенації списків (§2.4.3).
        subject_domain = Domain.OR([
            [('user_id', '=', user.id)],
            [('group_id', 'in', user_group_ids)],
        ])
        access_lines = self.search(Domain.AND([
            [('active', '=', True)],
            subject_domain,
        ]))

        domains = []
        for line in access_lines:
            raw_map = line.extra_domain or {}
            # extra_domain — мапа {dataset_id: domain}; ключі JSON завжди рядки.
            spec = raw_map.get(str(dataset_id))
            if spec is None:
                spec = raw_map.get(dataset_id)
            if not spec:
                continue
            parsed = self._parse_audience_spec(spec)
            if parsed is not None:
                domains.append(parsed)

        if not domains:
            # Жодної аудиторії -> нічого не звужуємо (нейтральний елемент кон'юнкції).
            return Domain.TRUE
        # Кон'юнкція по І: лише звужує (AC-21). Ніколи не Domain.OR на цьому рівні.
        return Domain.AND(domains)

    def _parse_audience_spec(self, spec):
        """AC-21 — парсить один extra_domain-спек у Domain із підстановкою змінних ir.rule.

        Домен зберігається як список умов (Json) або текстом; текст парситься через
        ast.literal_eval (НЕ eval/safe_eval, §2.4.3). Динамічні змінні user /
        company_id / company_ids замінюються поточними значеннями сесії — так само,
        як контекст обчислення ir.rule. Невалідний спек відхиляється ValidationError,
        щоб помилкова аудиторія не перетворилася на «тихе» розширення видимості.
        """
        if isinstance(spec, str):
            try:
                spec = ast.literal_eval(spec)
            except (ValueError, SyntaxError):
                raise ValidationError(_(
                    "Домен аудиторії має некоректний синтаксис: %s", spec,
                ))
        if not isinstance(spec, (list, tuple)):
            raise ValidationError(_(
                "Домен аудиторії має бути списком умов, отримано: %r", spec,
            ))
        eval_context = self._audience_eval_context()
        resolved = self._resolve_dynamic_values(list(spec), eval_context)
        # Domain(...) валідує структуру умов; повертаємо первокласний Domain.
        return Domain(resolved)

    @api.model
    def _user_group_ids(self, user):
        """Повертає id груп користувача, стійко до імені поля (groups_id/group_ids).

        # DEVIATION(Odoo19): звірити канонічне імʼя поля груп res.users на збірці 19.0.
        """
        groups = getattr(user, 'groups_id', None)
        if groups is None:  # запасний шлях для збірок з іншим імʼям поля
            groups = getattr(user, 'group_ids', user.browse())
        return groups.ids

    @api.model
    def _audience_eval_context(self):
        """Контекст динамічних змінних аудиторії (як у обчисленні ir.rule)."""
        user = self.env.user
        return {
            'user': user,
            'company_id': self.env.company.id,
            'company_ids': list(self.env.companies.ids),
            'uid': user.id,
        }

    def _resolve_dynamic_values(self, spec, eval_context):
        """Рекурсивно підставляє маркери змінних (user/company_id/company_ids) у значення домену.

        Підтримує два записи маркера в JSON-домені:
        - рядок-маркер: 'user.id', 'company_id', 'company_ids';
        - кортеж/список з трьох елементів — звичайна умова (field, op, value), де value
          може бути маркером.
        Це повторює семантику динамічних плейсхолдерів record rules без eval коду.
        """
        if isinstance(spec, (list, tuple)):
            # Логічні оператори ('&','|','!') лишаємо як є; решта — рекурсія.
            if len(spec) == 3 and isinstance(spec[0], str) and not isinstance(spec[1], (list, tuple)):
                field, operator, value = spec
                return (field, operator, self._resolve_marker(value, eval_context))
            return [self._resolve_dynamic_values(item, eval_context) for item in spec]
        return self._resolve_marker(spec, eval_context)

    def _resolve_marker(self, value, eval_context):
        """Підставляє значення маркера змінної; не-маркери повертає без змін."""
        markers = {
            'user.id': eval_context['uid'],
            'uid': eval_context['uid'],
            'company_id': eval_context['company_id'],
            'company_id.id': eval_context['company_id'],
            'company_ids': eval_context['company_ids'],
        }
        if isinstance(value, str) and value in markers:
            return markers[value]
        return value
