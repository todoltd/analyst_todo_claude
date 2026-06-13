/** @odoo-module **/
// Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
//
// ChartWidget — рендерер графіків 'bar'/'column'/'line'/'area'/'pie' через Chart.js.
// Props {widget, data}. Завантажує бандл web.chartjs_lib (loadBundle), будує
// конфіг із data.rows (keys -> мітки, values -> датасети), у onMounted створює
// new window.Chart(canvas, cfg), у onWillUpdateProps перебудовує, у onWillUnmount destroy.
// AC-14 — кожна точка має extra_domains (drill-down) — проброшено у meta точки (TODO-drill).
// Порожній/помилковий стан НЕ валить компонент.

import { Component, onWillStart, onMounted, onWillUnmount, onWillUpdateProps, useRef, useState } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";

// Базова палітра (узгоджена з темою; тема перевизначає через config.style.palette).
const DEFAULT_PALETTE = [
    "#714B67", "#017E84", "#F0AD4E", "#5CB85C", "#5BC0DE",
    "#D9534F", "#9B59B6", "#3498DB", "#E67E22", "#2ECC71",
];

export class ChartWidget extends Component {
    static template = "td_bi_dashboard.ChartWidget";
    static props = {
        widget: { type: Object },
        data: { type: Object, optional: true },
    };

    setup() {
        this.canvasRef = useRef("canvas");
        this.localization = useService("localization");
        // Стан сторінки для drill/cross-filter: клік по точці -> чип фільтра. // AC-14/AC-15
        this.biPageState = useService("bi_page_state");
        this._chart = null;
        // Заповнюється у _buildChartConfig; читається обробником кліку по точці.
        this._dimKey = null;
        this._extraDomains = [];
        this._labels = [];
        this.state = useState({
            // Помилка рендеру Chart.js НЕ валить сторінку — показуємо повідомлення (AC-52).
            renderError: false,
        });

        onWillStart(async () => {
            // Бандл Chart.js (web.assets — web.chartjs_lib). window.Chart стане доступним.
            await this._loadChartLib();
        });

        onMounted(() => this._renderChart());
        // onWillUpdateProps спрацьовує ДО оновлення this.props — рендеримо за nextProps,
        // інакше графік перемалювався б на застарілих даних.
        onWillUpdateProps((nextProps) => this._renderChart(nextProps));
        onWillUnmount(() => this._destroyChart());
    }

    /**
     * Активні props для рендеру: під час onWillUpdateProps — nextProps, інакше this.props.
     */
    get activeProps() {
        return this._pendingProps || this.props;
    }

    async _loadChartLib() {
        try {
            await loadBundle("web.chartjs_lib");
        } catch {
            // Бандл не завантажився — позначаємо помилку, але не кидаємо (AC-52).
            this.state.renderError = true;
        }
    }

    get lang() {
        const code = this.localization && this.localization.code;
        return code ? code.replace("_", "-") : undefined;
    }

    /**
     * Тип Chart.js, виведений з widget_type.
     * column -> горизонтальний bar (indexAxis 'y'); area -> line з fill.
     */
    get chartType() {
        const wt = (this.activeProps.widget && this.activeProps.widget.widget_type) || "bar";
        switch (wt) {
            case "line":
            case "area":
            case "timeseries":
                return "line";
            case "pie":
                return "pie";
            case "column":
            case "bar":
            default:
                return "bar";
        }
    }

    get isHorizontal() {
        return (this.activeProps.widget && this.activeProps.widget.widget_type) === "column";
    }

    get isArea() {
        return (this.activeProps.widget && this.activeProps.widget.widget_type) === "area";
    }

    get config() {
        const cfg = (this.activeProps.widget && this.activeProps.widget.config) || {};
        return { style: cfg.style || {}, data: cfg.data || {} };
    }

    get palette() {
        const p = this.config.style.palette;
        return Array.isArray(p) && p.length ? p : DEFAULT_PALETTE;
    }

    /**
     * Нормалізовані рядки {keys, values, extra_domains}; підтримка плаского рядка.
     */
    _rows() {
        const data = this.activeProps.data || {};
        const raw = Array.isArray(data.rows) ? data.rows : [];
        return raw.map((row) => {
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
            const keys = {};
            const values = {};
            for (const [k, v] of Object.entries(row)) {
                if (k === "extra_domains" || k.startsWith("__")) {
                    continue;
                }
                values[k] = v;
            }
            return { keys, values, extra_domains: row.__extra_domain || null };
        });
    }

    /**
     * Поле-вимір (мітки осі X): style.x_axis -> перший groupby результату -> перший ключ keys.
     * Повертаємо ПОВНИЙ токен (із гранулярністю, напр. 'create_date:year'), бо саме під
     * ним лежить значення у плаского рядка formatted_read_group. Гранулярність відсікається
     * лише там, де потрібне базове поле (cross-filter у _onPointClick).
     */
    _dimensionKey(rows) {
        const style = this.config.style || {};
        if (style.x_axis) {
            return String(style.x_axis);
        }
        const groupby = this.activeProps.data && this.activeProps.data.groupby;
        if (Array.isArray(groupby) && groupby.length) {
            return String(groupby[0]);
        }
        const sample = rows.find((r) => Object.keys(r.keys).length);
        return sample ? Object.keys(sample.keys)[0] : null;
    }

    /**
     * Ключі-міри (числові серії): style.y_axis (рядок/масив) -> усі value-ключі, крім виміру.
     */
    _measureKeys(rows, dimKey) {
        const style = this.config.style || {};
        if (style.y_axis) {
            return Array.isArray(style.y_axis) ? style.y_axis.slice() : [style.y_axis];
        }
        const sample = rows.find((r) => Object.keys(r.values).length) || { values: {} };
        return Object.keys(sample.values).filter((k) => k !== dimKey);
    }

    /** Людиночитна мітка значення виміру: m2o [id,name], boolean -> Так/Ні, інше -> рядок. */
    _formatLabel(v, i) {
        if (Array.isArray(v)) {
            return v.length > 1 ? String(v[1]) : String(v[0]);
        }
        if (v === true) {
            return "Так";
        }
        if (v === false) {
            return "Ні";
        }
        return v === null || v === undefined ? "—" : String(v);
    }

    /**
     * Будує Chart.js config із data.rows.
     * Мітки — значення поля-виміру (x_axis/groupby); датасети — поля-міри (y_axis).
     */
    _buildChartConfig() {
        const rows = this._rows();
        const dimKey = this._dimensionKey(rows);

        // Мітки осі X — значення поля-виміру (з values для плаского рядка, або з keys).
        const labels = rows.map((r, i) => {
            let v;
            if (dimKey && r.values[dimKey] !== undefined) {
                v = r.values[dimKey];
            } else if (dimKey && r.keys[dimKey] !== undefined) {
                v = r.keys[dimKey];
            } else {
                const keyNames = Object.keys(r.keys);
                v = keyNames.length ? r.keys[keyNames[0]] : undefined;
            }
            return v === undefined && !dimKey ? `#${i + 1}` : this._formatLabel(v, i);
        });

        // Ключі-міри (без поля-виміру) + людські назви серій із серверних measures.
        const measureNames = this._measureKeys(rows, dimKey);
        const niceNames = (this.activeProps.data && this.activeProps.data.measures) || [];
        // Домени точок для drill (AC-14) — за серіями однакові, тримаємо по індексу точки.
        const extraDomains = rows.map((r) => r.extra_domains || null);
        // Зберігаємо для обробника кліку (cross-filter). // AC-15
        this._dimKey = dimKey;
        this._extraDomains = extraDomains;
        this._labels = labels;

        const type = this.chartType;
        const datasets = measureNames.map((name, mi) => {
            const color = this.palette[mi % this.palette.length];
            const points = rows.map((r) => {
                const val = r.values[name];
                return typeof val === "number" ? val : (val === null || val === undefined ? null : Number(val) || null);
            });
            const ds = {
                label: niceNames[mi] || this._humanize(name),
                data: points,
                // pie фарбує кожну точку окремо; bar/line — одним кольором серії.
                backgroundColor: type === "pie"
                    ? points.map((_, pi) => this.palette[pi % this.palette.length])
                    : this._withAlpha(color, type === "line" && !this.isArea ? 1 : 0.7),
                borderColor: color,
                borderWidth: type === "line" ? 2 : 1,
            };
            if (type === "line") {
                ds.fill = this.isArea;
                ds.tension = 0.25;
                ds.pointRadius = 2;
            }
            // Домени точок для drill (cross-filter) — однакові за серіями, по індексу точки.
            ds._extraDomains = extraDomains;
            return ds;
        });

        // Примарна серія порівняння (AC-42): якщо рядки несуть <name>__prior (часовий
        // інтелект), додаємо напівпрозору «минулу» серію поряд із поточною. Для pie — ні.
        const ghostDatasets = [];
        if (type !== "pie") {
            measureNames.forEach((name, mi) => {
                const priorKey = name + "__prior";
                const hasPrior = rows.some(
                    (r) => r.values[priorKey] !== undefined && r.values[priorKey] !== null
                );
                if (!hasPrior) {
                    return;
                }
                const color = this.palette[mi % this.palette.length];
                const points = rows.map((r) => {
                    const val = r.values[priorKey];
                    return typeof val === "number" ? val : (val === null || val === undefined ? null : Number(val) || null);
                });
                const gds = {
                    label: (niceNames[mi] || this._humanize(name)) + " (минулий період)",
                    data: points,
                    backgroundColor: this._withAlpha(color, 0.2),
                    borderColor: this._withAlpha(color, 0.55),
                    borderWidth: 1,
                };
                if (type === "line") {
                    gds.fill = false;
                    gds.tension = 0.25;
                    gds.pointRadius = 2;
                    gds.borderDash = [5, 4];
                }
                gds._extraDomains = extraDomains;
                ghostDatasets.push(gds);
            });
        }
        const allDatasets = datasets.concat(ghostDatasets);

        const options = {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: this.isHorizontal ? "y" : "x",
            // Drill/cross-filter: клік по точці -> чип фільтра у bi_page_state. // AC-14/AC-15
            onClick: (evt, elements) => this._onPointClick(elements),
            onHover: (evt, elements) => {
                const target = evt && evt.native && evt.native.target;
                if (target) {
                    target.style.cursor = elements && elements.length ? "pointer" : "default";
                }
            },
            plugins: {
                legend: {
                    display: type === "pie" || allDatasets.length > 1,
                    position: "bottom",
                },
                tooltip: { enabled: true },
            },
        };
        if (type !== "pie") {
            options.scales = {
                [this.isHorizontal ? "x" : "y"]: { beginAtZero: true },
            };
        }

        return { type, data: { labels, datasets: allDatasets }, options };
    }

    /**
     * Обробник кліку по точці графіка -> drill/cross-filter. // AC-14/AC-15
     * Бере __extra_domain клікнутої групи (серверний домен спуску у tz користувача)
     * і додає/прибирає чип у bi_page_state. Повторний клік по тій самій точці = тогл.
     */
    _onPointClick(elements) {
        if (!Array.isArray(elements) || !elements.length) {
            return;
        }
        const idx = elements[0].index;
        const domain = this._extraDomains[idx];
        if (!Array.isArray(domain) || !domain.length) {
            return;
        }
        const widget = this.activeProps.widget || {};
        // Поле фільтрації — БАЗОВЕ поле виміру (без гранулярності) або перше поле домену спуску.
        const field = (this._dimKey ? String(this._dimKey).split(":")[0] : false)
            || (Array.isArray(domain[0]) ? domain[0][0] : false);
        const label = this._labels[idx] !== undefined ? this._labels[idx] : "";
        const chips = this.biPageState.state.crossFilters || [];
        const existing = chips.find(
            (c) =>
                c.widgetId === widget.id &&
                c.field === field &&
                this._sameDomain(c.domain, domain)
        );
        if (existing) {
            // Тогл: повторний клік по обраній точці прибирає фільтр.
            this.biPageState.removeCrossFilter(existing);
        } else {
            this.biPageState.addCrossFilter({ widgetId: widget.id, field, domain, label });
        }
    }

    /** Порівняння двох доменів за значенням (для тоглу cross-filter). */
    _sameDomain(a, b) {
        try {
            return JSON.stringify(a) === JSON.stringify(b);
        } catch {
            return false;
        }
    }

    _renderChart(nextProps) {
        // Під час onWillUpdateProps читаємо дані з nextProps (this.props ще не оновлено).
        this._pendingProps = nextProps || null;
        try {
            if (this.state.renderError) {
                return;
            }
            const Chart = window.Chart;
            const canvas = this.canvasRef.el;
            if (!Chart || !canvas) {
                // Бібліотека/DOM ще не готові — тихо виходимо (повторний рендер у onMounted/update).
                return;
            }
            this._destroyChart();
            if (!this._hasData()) {
                // Порожній стан показує шаблон (t-elif isEmpty); графік не створюємо.
                return;
            }
            const cfg = this._buildChartConfig();
            this._chart = new Chart(canvas, cfg);
            // Drill/cross-filter реалізовано через cfg.options.onClick -> _onPointClick. // AC-14/AC-15
        } catch {
            // Будь-яке виключення Chart.js -> картка-помилка, сторінка живе (AC-52).
            this.state.renderError = true;
        } finally {
            this._pendingProps = null;
        }
    }

    _destroyChart() {
        if (this._chart) {
            try {
                this._chart.destroy();
            } catch {
                // ігноруємо — destroy має бути ідемпотентним.
            }
            this._chart = null;
        }
    }

    _hasData() {
        const rows = this._rows();
        if (!rows.length) {
            return false;
        }
        // Є хоч одна числова міра з ненульовим значенням.
        return rows.some((r) => Object.values(r.values).some((v) => v !== null && v !== undefined && v !== ""));
    }

    get isEmpty() {
        return !this._hasData();
    }

    get title() {
        const w = this.activeProps.widget || {};
        return w.title || w.name || "";
    }

    _humanize(key) {
        const base = String(key).split(":")[0];
        return base.replace(/_/g, " ").replace(/(^|\s)\S/g, (m) => m.toUpperCase());
    }

    /**
     * Додає прозорість до hex-кольору (#RRGGBB -> rgba). Невалідний колір -> повертаємо як є.
     */
    _withAlpha(hex, alpha) {
        if (typeof hex !== "string" || !/^#?[0-9a-fA-F]{6}$/.test(hex)) {
            return hex;
        }
        const h = hex.replace("#", "");
        const r = parseInt(h.slice(0, 2), 16);
        const g = parseInt(h.slice(2, 4), 16);
        const b = parseInt(h.slice(4, 6), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
}
