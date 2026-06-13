/** @odoo-module **/
// Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
//
// KpiWidget — рендерер віджета типу 'kpi'/'kpi_card'.
// Props {widget, data}. Велике число (data.totals або перший rows.values),
// підпис (widget.title/subtitle), форматування за config.style.format.
// Порожній/помилковий стан НЕ валить компонент (try/catch у геттері + дефолти).

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Локальне форматування числа через Intl (без крос-версійних залежностей @web).
 * Гарантує, що бандл завантажиться у будь-якій 19.x і ніякий формат не валить картку.
 */
function _fmtNumber(num, { digits = 0, lang } = {}) {
    try {
        return new Intl.NumberFormat(lang || undefined, {
            minimumFractionDigits: digits,
            maximumFractionDigits: digits,
        }).format(num);
    } catch {
        return String(num);
    }
}

export class KpiWidget extends Component {
    static template = "td_bi_dashboard.KpiWidget";
    static props = {
        widget: { type: Object },
        data: { type: Object, optional: true },
    };

    setup() {
        // Локалізація форматування (роздільники тисяч/десяткові) за мовою користувача.
        this.localization = useService("localization");
    }

    get lang() {
        const code = this.localization && this.localization.code;
        // Odoo code виду 'uk_UA' -> BCP47 'uk-UA'.
        return code ? code.replace("_", "-") : undefined;
    }

    /**
     * Конфіг віджета (config.style / config.data) із безпечними дефолтами.
     */
    get config() {
        const cfg = (this.props.widget && this.props.widget.config) || {};
        return {
            style: cfg.style || {},
            data: cfg.data || {},
        };
    }

    /**
     * Назва міри, яку показуємо у KPI.
     * Беремо з config.data.measure; інакше — перша доступна міра з даних.
     */
    get measureKey() {
        const cfgMeasure = this.config.data.measure || this.config.data.value_field;
        if (cfgMeasure) {
            return cfgMeasure;
        }
        // Спроба вивести з totals або першого рядка.
        const totals = this._totals();
        const totalKeys = Object.keys(totals);
        if (totalKeys.length) {
            return totalKeys[0];
        }
        const firstValues = this._firstRowValues();
        const valKeys = Object.keys(firstValues);
        return valKeys.length ? valKeys[0] : null;
    }

    /**
     * totals із нормалізованого контракту run_query ({rows, totals, meta}).
     */
    _totals() {
        const data = this.props.data || {};
        const totals = data.totals;
        return totals && typeof totals === "object" ? totals : {};
    }

    /**
     * values першого рядка. Нормалізований контракт: rows[0].values.
     * Деградація: підтримуємо й «плаский» рядок (без .values) — тоді сам рядок.
     */
    _firstRowValues() {
        const data = this.props.data || {};
        const rows = Array.isArray(data.rows) ? data.rows : [];
        if (!rows.length) {
            return {};
        }
        const first = rows[0] || {};
        if (first.values && typeof first.values === "object") {
            return first.values;
        }
        // Плаский рядок компілятора: відкидаємо службові ключі.
        const flat = {};
        for (const [k, v] of Object.entries(first)) {
            if (k === "keys" || k === "extra_domains" || k.startsWith("__")) {
                continue;
            }
            flat[k] = v;
        }
        return flat;
    }

    /**
     * AC-19 — KPI рахується від імені користувача; ми лише показуємо те, що повернув run_query
     * (RLS/права застосовані на сервері). Сире числове значення міри (або null).
     */
    get rawValue() {
        try {
            const key = this.measureKey;
            if (!key) {
                return null;
            }
            const totals = this._totals();
            if (key in totals && totals[key] !== undefined) {
                return totals[key];
            }
            const values = this._firstRowValues();
            if (key in values && values[key] !== undefined) {
                return values[key];
            }
            return null;
        } catch {
            // Деградація: жодне виключення не валить картку.
            return null;
        }
    }

    /**
     * AC-08 — форматоване значення (валюта/відсоток/ціле/дробове) за config.style.format.
     * Невідоме/порожнє значення -> «—», без винятку.
     */
    get displayValue() {
        const value = this.rawValue;
        if (value === null || value === undefined || value === "" || Number.isNaN(value)) {
            return "—";
        }
        const num = Number(value);
        if (Number.isNaN(num)) {
            // Нечислове значення показуємо як рядок (деградація, не крах).
            return String(value);
        }
        const style = this.config.style || {};
        const format = style.format || style.value_format;
        const digits = style.digits !== undefined ? style.digits : 0;
        const lang = this.lang;
        const symbol = style.currency_symbol || style.symbol || "";
        const suffix = style.suffix || "";
        const prefix = style.prefix || "";
        try {
            switch (format) {
                case "monetary":
                case "currency": {
                    const body = _fmtNumber(num, { digits: style.digits !== undefined ? style.digits : 2, lang });
                    // Символ валюти (якщо переданий у config) як префікс; інакше просто число.
                    return symbol ? `${symbol} ${body}` : `${prefix}${body}${suffix}`;
                }
                case "percentage":
                case "percent": {
                    // Значення може бути часткою (0..1) або вже у відсотках — config керує множником.
                    const factor = style.percent_as_fraction ? 100 : 1;
                    return `${_fmtNumber(num * factor, { digits: digits || 1, lang })}%`;
                }
                case "float":
                case "decimal":
                    return `${prefix}${_fmtNumber(num, { digits: digits || 2, lang })}${suffix}`;
                case "integer":
                default:
                    // Дефолт KPI — ціле з роздільником тисяч; дробове -> 2 знаки.
                    return Number.isInteger(num)
                        ? `${prefix}${_fmtNumber(num, { digits: 0, lang })}${suffix}`
                        : `${prefix}${_fmtNumber(num, { digits: digits || 2, lang })}${suffix}`;
            }
        } catch {
            // Формат не спрацював — повертаємо просте число, картка живе (AC-08).
            return String(num);
        }
    }

    /**
     * Підпис: widget.title; субпідпис — widget.subtitle або config.data.label.
     */
    get label() {
        const w = this.props.widget || {};
        return w.title || w.name || "";
    }

    get sublabel() {
        const w = this.props.widget || {};
        return w.subtitle || (this.config.data && this.config.data.label) || "";
    }

    /**
     * Чи є взагалі дані для показу (для порожнього стану).
     */
    get hasValue() {
        return this.rawValue !== null && this.rawValue !== undefined;
    }
}
