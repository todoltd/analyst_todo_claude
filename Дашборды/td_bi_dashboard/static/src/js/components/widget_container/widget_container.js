/** @odoo-module **/
// Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
//
// WidgetContainer — обгортка одного віджета: тулбар з title, лоадер, картка
// помилки з «Повторити», делегування рендеру конкретному рендереру за widget_type.
// props: { widget }.
// onWillStart/onWillUpdateProps -> bi_data.runQuery(widget.dataset_id, specFromWidget(widget)).
// try/catch -> деградація per-віджет (одна картка падає, сторінка живе). // AC-52/AC-20

import { Component, useState, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { KpiWidget } from "../renderers/kpi_widget";
import { TableWidget } from "../renderers/table_widget";
import { ChartWidget } from "../renderers/chart_widget";

// Відповідність widget_type -> компонент-рендерер.
// (ChartWidget сам обробляє bar/column/line/area/pie/timeseries.)
const RENDERERS = {
    kpi: KpiWidget,
    kpi_card: KpiWidget,
    table: TableWidget,
    bar: ChartWidget,
    column: ChartWidget,
    line: ChartWidget,
    area: ChartWidget,
    timeseries: ChartWidget,
    pie: ChartWidget,
};

export class WidgetContainer extends Component {
    static template = "td_bi_dashboard.WidgetContainer";
    static components = { KpiWidget, TableWidget, ChartWidget };
    static props = {
        widget: { type: Object },
    };

    setup() {
        this.biData = useService("bi_data");
        this.biPageState = useService("bi_page_state");
        // Підписка на реактивний стан сторінки: ЧИТАЄМО через цей проксі у deps ефекту,
        // щоб зміна значень контролів/cross-filter ре-рендерила саме цей компонент. // AC-25/AC-15
        this.biState = useState(this.biPageState.state);

        this.state = useState({
            loading: true,
            error: null,
            data: null,
        });
        this._reqSeq = 0; // лічильник запитів: лише найсвіжіший _load керує станом loading

        // Єдиний ефект: завантаження на монтуванні + при зміні віджета АБО доменів контролів.
        // deps повертають серіалізований «відбиток» — _load спрацьовує лише коли він змінився. // AC-46
        useEffect(
            () => {
                this._load(this.props.widget);
            },
            () => [
                this.props.widget.id,
                this.props.widget.dataset_id,
                JSON.stringify(this.props.widget.config),
                this.props.widget.domain,
                // Читаємо ПІДПИСАНИЙ проксі (this.biState) -> OWL ре-рендерить при зміні фільтра.
                JSON.stringify(this.biState.controlValues || {}),
                JSON.stringify(this.biState.crossFilters || []),
            ]
        );
    }

    /** Назва компонента-рендерера за widget_type (для t-component). */
    rendererFor(widgetType) {
        return RENDERERS[widgetType] || null;
    }

    /** Чи відомий тип віджета. */
    get hasRenderer() {
        return !!this.rendererFor(this.props.widget.widget_type);
    }

    /**
     * Зібрати querySpec із конфігурації віджета + домени контролів сторінки.
     * Контракт: {groupby,aggregates,measures,limit,preview}. // AC-46
     */
    _specFromWidget(widget) {
        // Специфікація запиту лежить у config.data (get_runtime_config повертає {data:{...},style:{...}}).
        // Читання з кореня cfg давало порожній спец для ВСІХ віджетів -> однаковий ключ дебаунсу
        // -> взаємне скасування (KPI/таблиця вічно «Завантаження»). Читаємо саме cfg.data.
        const cfg = widget.config || {};
        const data = cfg.data || cfg; // fallback на корінь для зворотної сумісності
        const spec = {
            groupby: data.groupby || [],
            aggregates: data.aggregates || [],
            measures: data.measures || [],
        };
        if (data.limit !== undefined) {
            spec.limit = data.limit;
        }
        if (data.preview !== undefined) {
            spec.preview = data.preview;
        }
        // Домени-рівні зі стану сторінки (контролі + cross-filter) // AC-25:
        // зливаємо у ОДИН домен під ключем control_domain (саме його читає сервер,
        // compile_model_query -> spec.get('control_domain')). Плоский список умов = неявне І.
        // excludeWidgetId=widget.id: drill-чип цього ж віджета НЕ застосовуємо до нього
        // самого (джерело cross-filter показує всі точки для вибору). // AC-15
        const levels = this.biPageState.getControlsDomain(widget.id) || [];
        const flat = [].concat(...levels);
        if (flat.length) {
            spec.control_domain = flat;
        }
        return spec;
    }

    /**
     * Завантажити дані віджета рівно одним RPC run_query. // AC-46
     * try/catch -> деградація per-віджет: помилка лишається локальною. // AC-52/AC-20
     */
    async _load(widget) {
        const seq = ++this._reqSeq; // токен цього запиту
        this.state.loading = true;
        this.state.error = null;
        if (!widget.dataset_id) {
            this.state.loading = false;
            this.state.error = "Віджет не прив'язано до датасету.";
            return;
        }
        try {
            const data = await this.biData.runQuery(
                widget.dataset_id,
                this._specFromWidget(widget)
            );
            if (seq !== this._reqSeq) return; // застарілий результат — новіший _load керує станом
            this.state.data = data;
            this.state.loading = false;
        } catch (e) {
            // Застарілий/витіснений запит: новіший _load уже керує loading — нічого не робимо.
            if (seq !== this._reqSeq) return;
            // Дебаунс/скасування: новіший _load (зі свіжими props) візьме стан на себе.
            if (e && (e.message === "debounced" || e.message === "cancelled")) {
                return;
            }
            // Інша помилка -> картка помилки з кнопкою «Повторити». // AC-52/AC-49
            this.state.loading = false;
            this.state.error =
                (e && (e.data && e.data.message)) ||
                (e && e.message) ||
                "Помилка завантаження даних.";
        }
    }

    /** Повторити запит після помилки (кнопка «Повторити»). // AC-49/AC-52 */
    async onRetry() {
        await this._load(this.props.widget);
    }
}
