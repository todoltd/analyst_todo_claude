/** @odoo-module **/
// Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
//
// ControlBar — панель глобальних контролів дашборда: date range, dropdown.
// props: { controls } — список контролів із runtime-конфігу.
// Зміни пишуться у bi_page_state з дебаунсом; WidgetContainer'и перечитують дані. // AC-25/AC-26

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const APPLY_DEBOUNCE_MS = 400; // AC-26

export class ControlBar extends Component {
    static template = "td_bi_dashboard.ControlBar";
    static props = {
        controls: { type: Array },
    };

    setup() {
        this.biPageState = useService("bi_page_state");
        // Підписка на реактивний стан сторінки -> чипи cross-filter оновлюються наживо. // AC-15
        this.biState = useState(this.biPageState.state);
        // Локальний стан полів вводу (до застосування у bi_page_state).
        this.local = useState({});
        this._timers = {};
    }

    /** Активні чипи cross-filter (drill) для відображення/зняття. // AC-15 */
    get crossFilters() {
        return this.biState.crossFilters || [];
    }

    /** Прибрати конкретний чип cross-filter (клік по «×»). // AC-15 */
    removeChip(chip) {
        this.biPageState.removeCrossFilter(chip);
    }

    /** Тип контролю (нормалізований): 'date_range' | 'dropdown' | 'text'. */
    controlType(control) {
        const t = control.control_type || control.type || "text";
        if (t === "date" || t === "date_range" || t === "daterange") {
            return "date_range";
        }
        if (t === "dropdown" || t === "select" || t === "selection") {
            return "dropdown";
        }
        return "text";
    }

    /** Опції dropdown-контролю (із конфігу). */
    options(control) {
        return control.options || (control.config && control.config.options) || [];
    }

    /** Поле моделі, на яке мапиться контроль. */
    _field(control) {
        return control.field || (control.config && control.config.field) || control.name;
    }

    /** Дебаунснутий запис значення у bi_page_state. // AC-26 */
    _applyDebounced(controlId, value) {
        if (this._timers[controlId]) {
            clearTimeout(this._timers[controlId]);
        }
        this._timers[controlId] = setTimeout(() => {
            this.biPageState.setControlValue(controlId, value);
        }, APPLY_DEBOUNCE_MS);
    }

    /** Зміна dropdown. // AC-25 */
    onDropdownChange(control, ev) {
        const raw = ev.target.value;
        this.local[control.id] = raw;
        // Коерція рядка <select> у тип поля: булеві true/false, числа.
        let v = raw;
        if (raw === "true") { v = true; } else if (raw === "false") { v = false; }
        const value = raw === "" ? "" : { field: this._field(control), value: v };
        this._applyDebounced(control.id, value);
    }

    /** Зміна тексту/пошуку. // AC-25 */
    onTextChange(control, ev) {
        const raw = ev.target.value;
        this.local[control.id] = raw;
        const value = raw === "" ? "" : { field: this._field(control), op: "ilike", value: raw };
        this._applyDebounced(control.id, value);
    }

    /** Зміна меж діапазону дат (which: 'from' | 'to'). // AC-25 */
    onDateChange(control, which, ev) {
        const cur = this.local[control.id] || {};
        cur[which] = ev.target.value;
        this.local[control.id] = { ...cur };
        const value = {
            field: this._field(control),
            from: cur.from || "",
            to: cur.to || "",
        };
        this._applyDebounced(control.id, value);
    }

    /** Скинути всі контролі сторінки. // AC-25 */
    onReset() {
        for (const k of Object.keys(this.local)) {
            delete this.local[k];
        }
        this.biPageState.reset();
    }
}
