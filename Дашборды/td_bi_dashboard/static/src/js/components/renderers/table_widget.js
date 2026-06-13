/** @odoo-module **/
// Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
//
// TableWidget — рендерер віджета типу 'table'.
// Props {widget, data}. Будує <table> з рядків data.rows (keys+values),
// додає підсумковий рядок з data.totals; порожній стан без падіння.
// AC-36 — показуємо лише ті колонки, що повернув run_query (поля, доступні користувачу);
// AC-18 — порожня група/відсутність даних дає порожній стан, не помилку.

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class TableWidget extends Component {
    static template = "td_bi_dashboard.TableWidget";
    static props = {
        widget: { type: Object },
        data: { type: Object, optional: true },
    };

    setup() {
        this.localization = useService("localization");
        // Drill/cross-filter по кліку в рядку таблиці (паралель до ChartWidget). // AC-14/AC-15
        this.biPageState = useService("bi_page_state");
    }

    get lang() {
        const code = this.localization && this.localization.code;
        return code ? code.replace("_", "-") : undefined;
    }

    /**
     * Нормалізовані рядки: масив { keys, values, extra_domains }.
     * Деградація: підтримуємо й «плаский» рядок компілятора (без keys/values).
     */
    get rows() {
        const data = this.props.data || {};
        const raw = Array.isArray(data.rows) ? data.rows : [];
        return raw.map((row) => this._normalizeRow(row));
    }

    _normalizeRow(row) {
        if (!row || typeof row !== "object") {
            return { keys: {}, values: {}, extra_domains: null };
        }
        if (row.values || row.keys) {
            return {
                keys: row.keys && typeof row.keys === "object" ? row.keys : {},
                values: row.values && typeof row.values === "object" ? row.values : {},
                extra_domains: row.extra_domains || row.__extra_domain || null,
            };
        }
        // Плаский рядок: розділяємо службові ключі від даних, зберігаємо домен спуску.
        const keys = {};
        const values = {};
        for (const [k, v] of Object.entries(row)) {
            if (k === "extra_domains" || k.startsWith("__")) {
                continue;
            }
            values[k] = v;
        }
        return { keys, values, extra_domains: row.__extra_domain || null };
    }

    /**
     * Колонки таблиці. Беремо з meta.columns (якщо сервер передав підписи),
     * інакше виводимо з ключів keys+values першого рядка (AC-36 — лише наявні поля).
     */
    get columns() {
        const data = this.props.data || {};
        // Пріоритет: налаштовані колонки віджета (config.style.columns) з людськими підписами.
        const cfg = (this.props.widget && this.props.widget.config) || {};
        const styleCols = (cfg.style && cfg.style.columns) || (cfg.data && cfg.data.columns);
        if (Array.isArray(styleCols) && styleCols.length) {
            return styleCols.map((c) => {
                const name = String(c.field || c.name);
                // Міра, ЯКЩО: явний kind='value'; службовий ('__count'); колонка часового
                // інтелекту ('...__prior/__delta/__delta_pct'); агрегат-СУФІКС через ':'
                // (path:count/sum/...); або агрегат-токен як окремий сегмент.
                // ВАЖЛИВО: НЕ матчити ':' взагалі — інакше вимір-дата 'create_date:year'
                // (гранулярність, не агрегат) хибно став би мірою. Так само межі сегментів
                // не дають 'country_id'/'account_id'/'discount' матчити 'count'. // AC-36/AC-42
                const isValue =
                    c.kind === "value" ||
                    /^__/.test(name) ||
                    /__(prior|delta|delta_pct)$/i.test(name) ||
                    /:(count|sum|avg|min|max|count_distinct|bool_and|bool_or)/i.test(name) ||
                    /(^|_)(count|sum|avg|min|max)(_|$)/i.test(name);
                return { name, label: c.label || c.string || this._humanize(name), kind: isValue ? "value" : "key" };
            });
        }
        const meta = data.meta && typeof data.meta === "object" ? data.meta : {};
        if (Array.isArray(meta.columns) && meta.columns.length) {
            return meta.columns.map((c) =>
                typeof c === "string" ? { name: c, label: c, kind: "value" } : {
                    name: c.name || c.field,
                    label: c.label || c.string || c.name || c.field,
                    kind: c.kind || "value",
                }
            );
        }
        const rows = this.rows;
        if (!rows.length) {
            return [];
        }
        const first = rows[0];
        const cols = [];
        for (const k of Object.keys(first.keys)) {
            cols.push({ name: k, label: this._humanize(k), kind: "key" });
        }
        for (const k of Object.keys(first.values)) {
            cols.push({ name: k, label: this._humanize(k), kind: "value" });
        }
        return cols;
    }

    /**
     * Значення комірки за рядком і колонкою (keys мають пріоритет над values).
     */
    cell(row, column) {
        const val = column.kind === "key"
            ? (column.name in row.keys ? row.keys[column.name] : row.values[column.name])
            : (column.name in row.values ? row.values[column.name] : row.keys[column.name]);
        // Колонки відсотка часового інтелекту (…__delta_pct) — як відсоток зі знаком. // AC-42
        if (/(_pct|__delta_pct)$/i.test(column.name)) {
            return this._formatPct(val);
        }
        return this._formatCell(val);
    }

    /** Форматує частку (0.3 -> «+30 %») зі знаком; null -> «—». Без винятків (AC-18). */
    _formatPct(val) {
        if (val === null || val === undefined || val === "") {
            return "—";
        }
        try {
            return new Intl.NumberFormat(this.lang || undefined, {
                style: "percent", maximumFractionDigits: 1, signDisplay: "exceptZero",
            }).format(val);
        } catch {
            return String(val);
        }
    }

    /**
     * Підсумковий рядок з data.totals (тільки value-колонки).
     */
    get totals() {
        const data = this.props.data || {};
        const totals = data.totals && typeof data.totals === "object" ? data.totals : null;
        return totals;
    }

    get hasTotals() {
        const totals = this.totals;
        if (!totals) {
            return false;
        }
        return this.columns.some((c) => c.kind === "value" && c.name in totals);
    }

    totalCell(column) {
        const totals = this.totals || {};
        if (column.kind !== "value" || !(column.name in totals)) {
            return "";
        }
        return this._formatCell(totals[column.name]);
    }

    /**
     * Форматування комірки: число -> локалізований роздільник; m2o [id, name] -> name;
     * null/undefined -> «—». Жодне виключення не валить таблицю (AC-18).
     */
    _formatCell(val) {
        try {
            if (val === null || val === undefined || val === "") {
                return "—";
            }
            if (Array.isArray(val)) {
                // m2o-стиль [id, display_name] або вкладений масив.
                return val.length > 1 ? String(val[1]) : String(val[0]);
            }
            if (typeof val === "boolean") {
                return val ? "✓" : "";
            }
            if (typeof val === "number") {
                return new Intl.NumberFormat(this.lang || undefined, {
                    maximumFractionDigits: Number.isInteger(val) ? 0 : 2,
                }).format(val);
            }
            return String(val);
        } catch {
            return String(val);
        }
    }

    _humanize(key) {
        const base = String(key).split(":")[0]; // відсікти :month/:week гранулярність
        return base.replace(/_/g, " ").replace(/(^|\s)\S/g, (m) => m.toUpperCase());
    }

    /**
     * Порожній стан: немає жодного рядка.
     */
    get isEmpty() {
        return this.rows.length === 0;
    }

    get title() {
        const w = this.props.widget || {};
        return w.title || w.name || "";
    }

    /** Поле-вимір для cross-filter: перший groupby результату або перша key-колонка. */
    _dimField() {
        const data = this.props.data || {};
        const groupby = data.groupby;
        if (Array.isArray(groupby) && groupby.length) {
            return String(groupby[0]).split(":")[0];
        }
        const keyCol = this.columns.find((c) => c.kind === "key");
        return keyCol ? String(keyCol.name).split(":")[0] : false;
    }

    /**
     * Клік по рядку таблиці -> drill/cross-filter (паралель до ChartWidget._onPointClick).
     * Бере __extra_domain рядка (серверний домен спуску) і додає/прибирає чип. Тогл по
     * повторному кліку; заміна — за (widgetId, field). // AC-14/AC-15
     */
    onRowClick(rowIndex) {
        const row = this.rows[rowIndex];
        const domain = row && row.extra_domains;
        if (!Array.isArray(domain) || !domain.length) {
            return;
        }
        const widget = this.props.widget || {};
        const field = this._dimField() || (Array.isArray(domain[0]) ? domain[0][0] : false);
        // Підпис чипа — значення першої key-колонки рядка.
        const keyCol = this.columns.find((c) => c.kind === "key");
        const label = keyCol ? this.cell(row, keyCol) : "";
        const chips = this.biPageState.state.crossFilters || [];
        const existing = chips.find(
            (c) => c.widgetId === widget.id && c.field === field && this._sameDomain(c.domain, domain)
        );
        if (existing) {
            this.biPageState.removeCrossFilter(existing);
        } else {
            this.biPageState.addCrossFilter({ widgetId: widget.id, field, domain, label });
        }
    }

    /** Чи активний (вибраний drill) цей рядок — для підсвічування. */
    isRowActive(rowIndex) {
        const row = this.rows[rowIndex];
        const domain = row && row.extra_domains;
        if (!Array.isArray(domain) || !domain.length) {
            return false;
        }
        const widget = this.props.widget || {};
        return (this.biPageState.state.crossFilters || []).some(
            (c) => c.widgetId === widget.id && this._sameDomain(c.domain, domain)
        );
    }

    _sameDomain(a, b) {
        try {
            return JSON.stringify(a) === JSON.stringify(b);
        } catch {
            return false;
        }
    }
}
