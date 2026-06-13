/** @odoo-module **/
// Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
//
// Реєстр рендерерів: widget_type -> OWL-компонент {widget, data}.
// WidgetContainer імпортує лише цей модуль і обирає рендерер через getRenderer(widget_type).
// Коди узгоджені з td.bi.widget.widget_type (model) і Stage-1 контрактом:
//   контракт: 'kpi','table','bar','line','pie'
//   модель/демо: 'kpi_card','table','bar','column','line','area','pie','timeseries'

import { KpiWidget } from "./kpi_widget";
import { TableWidget } from "./table_widget";
import { ChartWidget } from "./chart_widget";

/**
 * Мапа widget_type -> компонент. Обидва набори кодів вказують на ті самі рендерери.
 * ChartWidget сам читає widget.widget_type і обирає тип Chart.js (bar/line/pie/area/column).
 */
export const WIDGET_RENDERERS = {
    // KPI
    kpi: KpiWidget,
    kpi_card: KpiWidget,
    // Таблиця
    table: TableWidget,
    // Графіки (Chart.js)
    bar: ChartWidget,
    column: ChartWidget,
    line: ChartWidget,
    area: ChartWidget,
    pie: ChartWidget,
    timeseries: ChartWidget,
};

// Компоненти для static components = {...} у WidgetContainer (один імпорт).
export const RENDERER_COMPONENTS = {
    KpiWidget,
    TableWidget,
    ChartWidget,
};

/**
 * Повертає компонент-рендерер за кодом widget_type.
 * Невідомий/порожній тип -> null (WidgetContainer показує «тип не підтримується», не падає).
 *
 * @param {string} widgetType
 * @returns {typeof import("@odoo/owl").Component | null}
 */
export function getRenderer(widgetType) {
    if (!widgetType) {
        return null;
    }
    return WIDGET_RENDERERS[widgetType] || null;
}

export { KpiWidget, TableWidget, ChartWidget };
