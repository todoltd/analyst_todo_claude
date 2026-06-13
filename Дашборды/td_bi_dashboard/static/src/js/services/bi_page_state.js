/** @odoo-module **/
// Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
//
// biPageState (реєстр: services "bi_page_state") — реактивний стан сторінки:
// значення контролів + cross-filter (чипи drill). Компоненти підписуються через
// useState(state). Метод getControlsDomain() віддає список доменів-рівнів,
// який biDataService/WidgetContainer додають у querySpec. // AC-25/AC-26

import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";

export const biPageState = {
    dependencies: [],

    start() {
        // Реактивний контейнер стану сторінки — спільний для ControlBar/WidgetContainer.
        const state = reactive({
            activePageId: false, // активна сторінка дашборда
            controlValues: {}, // { control_id: value } — застосовані значення контролів // AC-25
            crossFilters: [], // [{ widgetId, field, domain, label }] — чипи cross-filter // AC-15
        });

        /**
         * Записати значення контролю. У режимі перегляду лише фільтрує дані. // AC-25
         * @param {number|string} controlId
         * @param {*} value
         */
        function setControlValue(controlId, value) {
            // Порожнє значення -> прибрати фільтр (показати все).
            if (value === undefined || value === null || value === "") {
                delete state.controlValues[controlId];
            } else {
                state.controlValues[controlId] = value;
            }
        }

        /** Поточне значення контролю (або undefined). */
        function getControlValue(controlId) {
            return state.controlValues[controlId];
        }

        /**
         * Додати/замінити чип cross-filter від drill-кліку у віджеті. // AC-15
         * @param {Object} chip {widgetId, field, domain, label}
         */
        function addCrossFilter(chip) {
            // Один активний чип на (widgetId, field) — заміна, не накопичення.
            state.crossFilters = state.crossFilters.filter(
                (c) => !(c.widgetId === chip.widgetId && c.field === chip.field)
            );
            state.crossFilters.push(chip);
        }

        /** Прибрати конкретний чип cross-filter. // AC-15 */
        function removeCrossFilter(chip) {
            state.crossFilters = state.crossFilters.filter((c) => c !== chip);
        }

        /** Скинути всі контролі та cross-filter до чистого стану. // AC-25 */
        function reset() {
            state.controlValues = {};
            state.crossFilters = [];
        }

        /**
         * Зібрати ефективні домени сторінки як список рівнів-доменів. // AC-25/AC-64
         * Рівні: (1) значення контролів, (2) чипи cross-filter. Сервер з'єднує їх
         * через Domain.AND разом із доменом датасету.
         * @param {number|string} [excludeWidgetId] — НЕ застосовувати cross-filter,
         *   що походить із цього віджета (джерело drill не фільтрує саме себе —
         *   інакше графік-джерело згорнувся б до однієї обраної точки). // AC-15
         * @returns {Array<Array>} список доменів-рівнів (кожен — стандартний Odoo-домен)
         */
        function getControlsDomain(excludeWidgetId) {
            const levels = [];
            // Рівень 1 — застосовані значення контролів.
            for (const [controlId, value] of Object.entries(state.controlValues)) {
                const dom = _controlToDomain(controlId, value);
                if (dom && dom.length) {
                    levels.push(dom);
                }
            }
            // Рівень 2 — чипи cross-filter (drill). // AC-15
            for (const chip of state.crossFilters) {
                if (excludeWidgetId !== undefined && chip.widgetId === excludeWidgetId) {
                    // Віджет-джерело не фільтрує сам себе (показує всі точки для вибору).
                    continue;
                }
                if (chip.domain && chip.domain.length) {
                    levels.push(chip.domain);
                }
            }
            return levels;
        }

        /**
         * Перетворити значення контролю на Odoo-домен. // AC-26
         * Підтримує базові форми Stage-1:
         *   { field, op, value }                      -> [[field, op, value]]
         *   { field, from, to }  (date range)         -> [[field,'>=',from],[field,'<=',to]]
         *   { field, value: [...] } (dropdown multi)  -> [[field,'in',[...]]]
         * Уже готовий домен (масив) пропускається як є.
         */
        function _controlToDomain(controlId, value) {
            if (Array.isArray(value)) {
                // Уже домен.
                return value;
            }
            if (!value || typeof value !== "object" || !value.field) {
                return [];
            }
            const f = value.field;
            if (value.from !== undefined || value.to !== undefined) {
                const dom = [];
                if (value.from) {
                    dom.push([f, ">=", value.from]);
                }
                if (value.to) {
                    dom.push([f, "<=", value.to]);
                }
                return dom;
            }
            if (Array.isArray(value.value)) {
                return value.value.length ? [[f, "in", value.value]] : [];
            }
            if (value.value !== undefined && value.value !== null && value.value !== "") {
                return [[f, value.op || "=", value.value]];
            }
            return [];
        }

        return {
            state,
            setControlValue,
            getControlValue,
            addCrossFilter,
            removeCrossFilter,
            reset,
            getControlsDomain,
        };
    },
};

registry.category("services").add("bi_page_state", biPageState);
