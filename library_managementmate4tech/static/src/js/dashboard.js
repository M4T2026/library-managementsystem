import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class LibraryDashboard extends Component {
    static template = "library_management.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({ data: null, loading: true });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        this.state.data = await this.orm.call("library.loan", "get_dashboard_data", []);
        this.state.loading = false;
    }

    // ---- formatting -------------------------------------------------
    money(value) {
        const { symbol, position } = this.state.data.currency;
        const num = (value || 0).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        return position === "before" ? `${symbol}${num}` : `${num} ${symbol}`;
    }

    pct(value, max) {
        return max ? Math.max(Math.round((value / max) * 100), value ? 4 : 0) : 0;
    }

    get maxMonth() {
        return Math.max(1, ...this.state.data.months.map((m) => Math.max(m.loans, m.returns)));
    }

    get maxTop() {
        return Math.max(1, ...this.state.data.top_books.map((b) => b.count));
    }

    get maxCategory() {
        return Math.max(1, ...this.state.data.categories.map((c) => c.count));
    }

    get kpis() {
        const k = this.state.data.kpis;
        const d = this.state.data;
        return [
            { key: "books", label: "Books", value: k.books, icon: "fa-book", tone: "primary",
              onClick: () => this.openList("Books", "library.book", [], ["kanban", "list", "form"]) },
            { key: "available", label: "Available Copies", value: `${k.available} / ${k.copies}`, icon: "fa-check-circle", tone: "success",
              onClick: () => this.openList("Available Copies", "library.book.copy", [["state", "=", "available"]]) },
            { key: "members", label: "Members", value: k.members, icon: "fa-users", tone: "info",
              onClick: () => this.openList("Members", "library.member") },
            { key: "active", label: "Active Loans", value: k.active_loans, icon: "fa-exchange", tone: "primary",
              onClick: () => this.openList("Active Loans", "library.loan", [["state", "in", ["borrowed", "overdue"]]]) },
            { key: "due", label: "Due Today", value: k.due_today, icon: "fa-calendar-check-o", tone: "warning",
              onClick: () => this.openList("Due Today", "library.loan", [["state", "=", "borrowed"], ["due_date", "=", d.today]]) },
            { key: "overdue", label: "Overdue", value: k.overdue, icon: "fa-exclamation-triangle", tone: "danger",
              onClick: () => this.openList("Overdue Loans", "library.loan", [["state", "=", "overdue"]]) },
            { key: "fines", label: "Unpaid Fines", value: this.money(k.unpaid_fines), icon: "fa-money", tone: "danger",
              onClick: () => this.openList("Unpaid Fines", "library.loan", [["fine_amount", ">", 0], ["fine_paid", "=", false]]) },
        ];
    }

    // ---- navigation -------------------------------------------------
    openList(name, resModel, domain = [], viewTypes = ["list", "form"]) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name,
            res_model: resModel,
            views: viewTypes.map((v) => [false, v]),
            domain,
            target: "current",
        });
    }

    openLoan(id) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "library.loan",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    newLoan() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "New Loan",
            res_model: "library.loan",
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("library_management.dashboard", LibraryDashboard);
