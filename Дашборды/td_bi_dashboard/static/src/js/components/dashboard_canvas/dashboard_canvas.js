/** @odoo-module **/
// Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
//
// DashboardCanvas — сітка віджетів сторінки: CSS Grid 24 колонки.
// props: { page } — { id, name, widgets:[{id,widget_type,title,dataset_id,config,
//                       pos_x,pos_y,width,height}] }.
// Кожен widget -> <WidgetContainer widget="w"/> з grid-column/grid-row за
// pos_x/width/pos_y/height. // AC-31

import { Component } from "@odoo/owl";
import { WidgetContainer } from "../widget_container/widget_container";

export class DashboardCanvas extends Component {
    static template = "td_bi_dashboard.DashboardCanvas";
    static components = { WidgetContainer };
    static props = {
        page: { type: Object },
    };

    get widgets() {
        return (this.props.page && this.props.page.widgets) || [];
    }

    /**
     * Inline grid-стиль для одного віджета. // AC-31
     * grid-column: pos_x+1 / span width;  grid-row: pos_y+1 / span height.
     * (CSS Grid 1-based; pos_x/pos_y 0-based з конфігу.)
     */
    widgetStyle(w) {
        const colStart = (w.pos_x || 0) + 1;
        const colSpan = Math.max(1, w.width || 1);
        const rowStart = (w.pos_y || 0) + 1;
        const rowSpan = Math.max(1, w.height || 1);
        return (
            `grid-column: ${colStart} / span ${colSpan};` +
            `grid-row: ${rowStart} / span ${rowSpan};`
        );
    }
}
