# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
import hashlib
import json

from odoo import api, fields, models, _
from odoo.fields import Domain  # Odoo 19: первокласний Domain


class TdBiCache(models.Model):
    _name = 'td.bi.cache'
    _description = 'BI: Серверний кеш'
    # Записує система (run_query); лише читання для group_bi_admin (ACL).

    # === Fields ===
    cache_key = fields.Char(string="Ключ кешу", index=True)  # SHA-256 запиту; unique
    dataset_id = fields.Many2one(
        'td.bi.dataset', string="Датасет", ondelete='cascade',
    )
    payload = fields.Json(string="Результат запиту")  # JSON результату (Binary gzip)
    expires_at = fields.Datetime(string="Спливає", index=True)  # now + cache_ttl
    hit_count = fields.Integer(string="Лічильник звернень")

    # === Constraints ===
    # Odoo 19: models.Constraint замість _sql_constraints (deprecated)
    _cache_key_uniq = models.Constraint('unique(cache_key)', "Ключ кешу має бути унікальним")

    # === Compute ===
    # SPEC: Computed fields — None.

    # === Actions ===
    @api.model
    def _cron_clear_expired(self):
        """AC-23 — інвалідація за TTL: видаляє записи з expires_at у минулому.

        Cron очистки кешу (кожні ~15 хв, §2.3.4 / ВИМ-47). Видалення партіями з
        протоколом _commit_progress (стійкість до таймаутів на великих наборах):
        кожна партія комітиться окремо, тож переривання cron не відкочує вже
        очищене. Виконується від імені користувача cron (group_bi_admin за ACL).
        """
        now = fields.Datetime.now()
        # Domain.AND([...]) — навіть для одного рівня уникаємо ручної конкатенації.
        domain = Domain.AND([[('expires_at', '<', now)]])
        expired = self.search(domain)
        total = len(expired)
        batch_size = 1000
        for index in range(0, total, batch_size):
            batch = expired[index:index + batch_size]
            batch.unlink()
            # _commit_progress: фіксуємо партію, щоб таймаут cron не втратив прогрес.
            if hasattr(self.env, '_commit_progress'):
                # DEVIATION(Odoo19): підтвердити сигнатуру _commit_progress на збірці 19.0;
                # запасний шлях — явний cr.commit() між партіями.
                self.env._commit_progress(processed=min(index + batch_size, total),
                                          total=total)
            else:  # pragma: no cover — запасний шлях для збірок без хелпера
                self.env.cr.commit()
        return True

    @api.model
    def _build_cache_key(self, dataset, query_spec, uid_perm_marker=None,
                         lang=None, tz=None, company_ids=None):
        """AC-23 — обчислює SHA-256 від нормалізованого JSON-опису запиту.

        Ключ кешу включає (§2.4): dataset_id+version, нормалізований домен, groupby,
        aggregates, having, order, limit, uid-маркер прав користувача, lang, tz,
        company_ids. Завдяки uid-маркеру (за замовчуванням user_id) РІЗНІ користувачі
        НЕ ділять кеш-ключ — результати з record rules одного не віддаються іншому.

        :param dataset: recordset td.bi.dataset (1 запис) — джерело dataset_id+version
        :param query_spec: dict опису запиту (domain/groupby/aggregates/having/order/limit)
        :param uid_perm_marker: маркер прав користувача (default — self.env.uid)
        :param lang: код мови (default — контекст)
        :param tz: часовий пояс (default — контекст)
        :param company_ids: список id компаній (default — allowed companies контексту)
        :return: hex-рядок SHA-256
        """
        env = self.env
        # uid-маркер прав: за замовчуванням персональний кеш (user_id). Саме він
        # гарантує, що два користувачі не отримають результат з одного ключа (AC-23).
        if uid_perm_marker is None:
            uid_perm_marker = env.uid
        if lang is None:
            lang = env.context.get('lang') or (env.user.lang or False)
        if tz is None:
            tz = env.context.get('tz') or (env.user.tz or False)
        if company_ids is None:
            company_ids = list(env.companies.ids)

        query_spec = query_spec or {}
        # Нормалізований образ запиту: стабільний порядок ключів, сортовані company_ids.
        components = {
            'dataset_id': dataset.id if dataset else False,
            'version': dataset.version if dataset else 0,
            'domain': self._normalize_component(query_spec.get('domain')),
            # AC-23: УСІ рівні домену мають входити в ключ, інакше відфільтровані
            # запити колізують зі стале-кешованим нефільтрованим результатом.
            'control_domain': self._normalize_component(query_spec.get('control_domain')),
            'widget_domain': self._normalize_component(query_spec.get('widget_domain')),
            'audience_domain': self._normalize_component(query_spec.get('audience_domain')),
            'cross_filter_domain': self._normalize_component(query_spec.get('cross_filter_domain')),
            'drill_domain': self._normalize_component(query_spec.get('drill_domain')),
            'measures': self._normalize_component(query_spec.get('measures')),
            'comparison': self._normalize_component(query_spec.get('comparison')),
            # AC-23: конфіг часового інтелекту мір (time_intelligence/comparison/rolling_n/
            # show_as) змінює ВИХІД при тих самих groupby/домені -> мусить бути в ключі,
            # інакше база і YoY-варіант тієї ж міри колізують у кеші.
            'ti_signature': self._ti_signature(dataset, query_spec),
            'groupby': self._normalize_component(query_spec.get('groupby')),
            'aggregates': self._normalize_component(query_spec.get('aggregates')),
            'having': self._normalize_component(query_spec.get('having')),
            'order': self._normalize_component(query_spec.get('order')),
            'limit': query_spec.get('limit'),
            'offset': query_spec.get('offset'),
            # Маркер прав/контексту користувача — основа ізоляції кешу між користувачами.
            'uid_perm_marker': uid_perm_marker,
            'lang': lang,
            'tz': tz,
            'company_ids': sorted(company_ids or []),
        }
        # sort_keys=True + default=str -> детермінований серіалізований образ незалежно
        # від порядку ключів у вхідному query_spec.
        normalized = json.dumps(
            components, sort_keys=True, ensure_ascii=False, default=str,
        )
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    @api.model
    def _ti_signature(self, dataset, query_spec):
        """Стабільний підпис часового інтелекту мір, задіяних у запиті (AC-23).
        Лише для явно вибраних мір (query_spec['measures']); сортований список
        [name, time_intelligence, comparison, rolling_n, show_as]. None, якщо нічого."""
        requested = query_spec.get('measures') or []
        if not dataset or not requested:
            return None
        sig = []
        for m in dataset.measure_ids:
            if m.name in requested or m.id in requested:
                sig.append([
                    m.name, m.time_intelligence or 'none', m.comparison or 'none',
                    m.rolling_n or 0, m.show_as or 'value',
                ])
        return sorted(sig) if sig else None

    @api.model
    def _normalize_component(self, value):
        """Нормалізує компонент query_spec у JSON-серіалізовну, стабільну форму.

        Domain-об'єкти Odoo 19 зводяться до списку умов; tuple -> list (бо JSON не
        розрізняє кортежі). Гарантує, що логічно однаковий запит дає однаковий ключ.
        """
        if value is None:
            return None
        if isinstance(value, Domain):
            # Domain -> нормалізований список умов (детермінований образ).
            return list(value)
        if isinstance(value, tuple):
            return [self._normalize_component(item) for item in value]
        if isinstance(value, list):
            return [self._normalize_component(item) for item in value]
        return value

    @api.model
    def get_cached(self, key):
        """AC-23 — повертає payload за кеш-ключем, якщо запис не спливла.

        Інкрементує hit_count для статистики. Прострочені записи трактуються як
        промах (None) і прибираються cron-ом _cron_clear_expired. Кеш — системна
        інфраструктура (за ACL bi-користувачі мають 0,0,0,0 на td.bi.cache): читаємо
        і пишемо через sudo(). Ізоляція між користувачами тримається НЕ на record
        rules таблиці кешу, а на самому ключі — він містить uid-маркер прав (+lang/tz/
        company), тож звернення за key одного користувача не може натрапити на запис
        іншого (AC-23).
        """
        if not key:
            return None
        cache = self.sudo()
        record = cache.search([('cache_key', '=', key)], limit=1)
        if not record:
            return None
        now = fields.Datetime.now()
        if record.expires_at and record.expires_at < now:
            # Промах за TTL: фактичне видалення — за cron-ом (стійкість до таймаутів).
            return None
        record.hit_count = record.hit_count + 1
        return record.payload

    @api.model
    def store(self, key, payload, ttl):
        """AC-23 — зберігає payload під унікальним ключем з expires_at = now + ttl.

        ttl=0 (кеш вимкнено політикою датасету) — нічого не зберігаємо. Ключ
        унікальний (_sql_constraints): при повторному store того ж ключа оновлюємо
        наявний запис замість порушення обмеження. Запис системний (sudo): таблиця
        кешу закрита для bi-користувачів за ACL, а ізоляція тримається на ключі.
        """
        if not key or not ttl:
            return self.browse()
        cache = self.sudo()
        expires_at = fields.Datetime.add(fields.Datetime.now(), seconds=ttl)
        existing = cache.search([('cache_key', '=', key)], limit=1)
        if existing:
            existing.write({'payload': payload, 'expires_at': expires_at})
            return existing
        return cache.create({
            'cache_key': key,
            'payload': payload,
            'expires_at': expires_at,
            'hit_count': 0,
        })

    # === Аліаси пламбінгу run_query (sibling-трек Stage-1) ===
    # run_query (td.bi.dataset) звертається до кешу через приватні _get/_set під
    # guard hasattr. Імена історично розійшлися з публічним API (get_cached/store):
    # hasattr не знаходив _get/_set і МОВЧКИ вимикав серверний кеш (AC-23) — кеш не
    # читався і не писався, кожен run_query перекомпільовувався. Тонкі аліаси
    # делегують у публічний API (зберігаючи його незмінним) і вмикають кеш-шлях.
    @api.model
    def _get(self, key):
        """Аліас читання кешу: делегує у get_cached(key) (AC-23)."""
        return self.get_cached(key)

    @api.model
    def _set(self, key, dataset, payload):
        """Аліас запису кешу. run_query викликає _set(key, dataset, result); TTL беремо
        з політики датасету (dataset.cache_ttl) і делегуємо у store(key, payload, ttl)."""
        ttl = dataset.cache_ttl if dataset else 0
        return self.store(key, payload, ttl)
