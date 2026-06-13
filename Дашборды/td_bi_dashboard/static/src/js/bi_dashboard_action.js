/** @odoo-module **/
// Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
//
// BiDashboardAction — коренева клієнтська дія (ir.actions.client, тег "bi_dashboard").
// onWillStart -> bi_data.getRuntimeConfig(id) у this.state.config; рендерить
// ControlBar + DashboardCanvas поточної сторінки. Якщо id немає -> каталог
// (searchRead td.bi.dashboard опублікованих) з кнопкою «Відкрити». // AC-25/AC-31

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ControlBar } from "./components/control_bar/control_bar";
import { DashboardCanvas } from "./components/dashboard_canvas/dashboard_canvas";

export class BiDashboardAction extends Component {
    static template = "td_bi_dashboard.BiDashboardAction";
    static components = { ControlBar, DashboardCanvas };
    static props = {
        "*": true, // action props (action, actionId, className, ...) — приймаємо як є
    };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.biData = useService("bi_data");
        this.biPageState = useService("bi_page_state");

        this.state = useState({
            dashboardId: this._resolveDashboardId(),
            isLoading: true,
            error: null,
            config: null, // runtime-конфіг дашборда
            activePageId: false,
            catalog: null, // список опублікованих дашбордів (режим каталогу)
        });

        onWillStart(async () => {
            if (this.state.dashboardId) {
                await this._loadRuntimeConfig();
            } else {
                await this._loadCatalog();
            }
        });
    }

    /** id дашборда з context.active_id АБО params.dashboard_id. */
    _resolveDashboardId() {
        const action = this.props.action || {};
        const fromParams = action.params && action.params.dashboard_id;
        const fromContext = action.context && action.context.active_id;
        return fromParams || fromContext || false;
    }

    /** Завантажити runtime-конфіг одним RPC. // AC-46 */
    async _loadRuntimeConfig() {
        this.state.isLoading = true;
        this.state.error = null;
        try {
            const config = await this.biData.getRuntimeConfig(this.state.dashboardId);
            this.state.config = config;
            const pages = (config && config.pages) || [];
            this.state.activePageId = pages.length ? pages[0].id : false;
            this.biPageState.state.activePageId = this.state.activePageId;
            this.state.isLoading = false;
        } catch (e) {
            this.state.isLoading = false;
            this.state.error =
                (e && e.data && e.data.message) || (e && e.message) || "Не вдалося завантажити дашборд.";
        }
    }

    /** Каталог опублікованих дашбордів (немає id). */
    async _loadCatalog() {
        this.state.isLoading = true;
        try {
            const records = await this.orm.searchRead(
                "td.bi.dashboard",
                [["state", "=", "published"]],
                ["id", "name", "description"],
                { order: "name" }
            );
            this.state.catalog = records;
            this.state.isLoading = false;
        } catch (e) {
            this.state.isLoading = false;
            this.state.error =
                (e && e.data && e.data.message) || (e && e.message) || "Не вдалося завантажити каталог.";
        }
    }

    /** Сторінки дашборда. */
    get pages() {
        return (this.state.config && this.state.config.pages) || [];
    }

    /** Поточна активна сторінка. */
    get activePage() {
        return this.pages.find((p) => p.id === this.state.activePageId) || this.pages[0] || null;
    }

    /** Глобальні контроли дашборда. */
    get controls() {
        return (this.state.config && this.state.config.controls) || [];
    }

    /** Перемкнути активну сторінку. */
    onSelectPage(pageId) {
        this.state.activePageId = pageId;
        this.biPageState.state.activePageId = pageId;
    }

    /** Відкрити дашборд з каталогу — перемикання виду В МЕЖАХ компонента
     *  (без re-doAction того ж client-action, який Odoo дедуплює). */
    async onOpenDashboard(dashboardId) {
        this.state.dashboardId = dashboardId;
        await this._loadRuntimeConfig();
    }

    /** Повернутися до каталогу опублікованих дашбордів. */
    async backToCatalog() {
        this.state.dashboardId = false;
        this.state.config = null;
        this.state.activePageId = false;
        await this._loadCatalog();
    }
}

// Реєстрація клієнтської дії під тегом "bi_dashboard".
registry.category("actions").add("bi_dashboard", BiDashboardAction);
