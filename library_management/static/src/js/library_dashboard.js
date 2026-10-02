/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, useState } from "@odoo/owl";

export class LibraryDashboard extends Component {
    static template = "library_management.DashboardTemplate";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            data: null,
        });
        onMounted(() => this._loadData());
    }

    async _loadData() {
        try {
            const data = await this.orm.call(
                "library.dashboard",
                "get_dashboard_data",
                []
            );
            this.state.data = data;
            this.state.loading = false;
            // Render charts after DOM is ready
            setTimeout(() => this._renderCharts(), 100);
        } catch (e) {
            console.error("Dashboard load error", e);
            this.state.loading = false;
        }
    }

    _renderCharts() {
        if (!this.state.data) return;
        this._renderTrendChart();
        this._renderCategoryChart();
    }

    _renderTrendChart() {
        const canvas = document.getElementById("lib_trend_chart");
        if (!canvas) return;
        const d = this.state.data;
        const labels = d.monthly_trend.map((m) => m.month);
        const counts = d.monthly_trend.map((m) => m.count);
        this._drawLineChart(canvas, labels, counts, "Monthly Borrowings", "#7c7bad");
    }

    _renderCategoryChart() {
        const canvas = document.getElementById("lib_category_chart");
        if (!canvas) return;
        const d = this.state.data;
        if (!d.category_data.length) return;
        const labels = d.category_data.map((c) => c.name);
        const counts = d.category_data.map((c) => c.count);
        this._drawDoughnutChart(canvas, labels, counts);
    }

    _drawLineChart(canvas, labels, data, label, color) {
        const ctx = canvas.getContext("2d");
        const width = canvas.width;
        const height = canvas.height;
        const padding = { top: 20, right: 20, bottom: 40, left: 50 };
        const chartW = width - padding.left - padding.right;
        const chartH = height - padding.top - padding.bottom;
        const maxVal = Math.max(...data, 1);
        const stepX = chartW / (labels.length - 1 || 1);

        ctx.clearRect(0, 0, width, height);

        // Grid lines
        ctx.strokeStyle = "rgba(124,123,173,0.15)";
        ctx.lineWidth = 1;
        for (let i = 0; i <= 4; i++) {
            const y = padding.top + (chartH * i) / 4;
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(padding.left + chartW, y);
            ctx.stroke();
            ctx.fillStyle = "#888";
            ctx.font = "11px Inter,sans-serif";
            ctx.textAlign = "right";
            ctx.fillText(Math.round(maxVal * (1 - i / 4)), padding.left - 8, y + 4);
        }

        // Area fill
        const gradient = ctx.createLinearGradient(0, padding.top, 0, padding.top + chartH);
        gradient.addColorStop(0, "rgba(124,123,173,0.35)");
        gradient.addColorStop(1, "rgba(124,123,173,0.02)");
        ctx.beginPath();
        data.forEach((val, i) => {
            const x = padding.left + i * stepX;
            const y = padding.top + chartH - (val / maxVal) * chartH;
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        });
        ctx.lineTo(padding.left + (data.length - 1) * stepX, padding.top + chartH);
        ctx.lineTo(padding.left, padding.top + chartH);
        ctx.closePath();
        ctx.fillStyle = gradient;
        ctx.fill();

        // Line
        ctx.beginPath();
        ctx.strokeStyle = color;
        ctx.lineWidth = 3;
        ctx.lineJoin = "round";
        data.forEach((val, i) => {
            const x = padding.left + i * stepX;
            const y = padding.top + chartH - (val / maxVal) * chartH;
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        });
        ctx.stroke();

        // Dots
        data.forEach((val, i) => {
            const x = padding.left + i * stepX;
            const y = padding.top + chartH - (val / maxVal) * chartH;
            ctx.beginPath();
            ctx.arc(x, y, 4, 0, Math.PI * 2);
            ctx.fillStyle = "#fff";
            ctx.fill();
            ctx.strokeStyle = color;
            ctx.lineWidth = 2;
            ctx.stroke();
        });

        // X labels
        ctx.fillStyle = "#888";
        ctx.font = "10px Inter,sans-serif";
        ctx.textAlign = "center";
        labels.forEach((lbl, i) => {
            const x = padding.left + i * stepX;
            ctx.fillText(lbl, x, height - 10);
        });
    }

    _drawDoughnutChart(canvas, labels, data) {
        const ctx = canvas.getContext("2d");
        const colors = [
            "#7c7bad", "#5b9bd5", "#ed7d31", "#70ad47", "#ffc000",
            "#ff4f4f", "#26c6da", "#ab47bc", "#42a5f5", "#66bb6a",
        ];
        const total = data.reduce((a, b) => a + b, 0);
        const cx = canvas.width / 2;
        const cy = canvas.height / 2;
        const r = Math.min(cx, cy) - 10;
        const inner = r * 0.55;
        let angle = -Math.PI / 2;

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        data.forEach((val, i) => {
            const slice = (val / total) * 2 * Math.PI;
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.arc(cx, cy, r, angle, angle + slice);
            ctx.closePath();
            ctx.fillStyle = colors[i % colors.length];
            ctx.fill();
            ctx.strokeStyle = "#fff";
            ctx.lineWidth = 2;
            ctx.stroke();
            angle += slice;
        });

        // Inner circle (donut hole)
        ctx.beginPath();
        ctx.arc(cx, cy, inner, 0, Math.PI * 2);
        ctx.fillStyle = "#fff";
        ctx.fill();

        // Center text
        ctx.fillStyle = "#333";
        ctx.font = "bold 18px Inter,sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(total, cx, cy - 8);
        ctx.font = "11px Inter,sans-serif";
        ctx.fillStyle = "#888";
        ctx.fillText("Total Books", cx, cy + 10);
    }

    // Navigation helpers
    goTo(model, domain, name) {
        this.action.doAction({
            name,
            type: "ir.actions.act_window",
            res_model: model,
            view_mode: "list,form",
            domain: domain || [],
            target: "current",
        });
    }

    goToBooks() { this.goTo("library.book", [], "Books"); }
    goToAvailableBooks() { this.goTo("library.book", [["state", "=", "available"]], "Available Books"); }
    goToBorrowedBooks() { this.goTo("library.book", [["state", "=", "borrowed"]], "Borrowed Books"); }
    goToMembers() { this.goTo("library.member", [], "Members"); }
    goToActiveMembers() { this.goTo("library.member", [["state", "=", "active"]], "Active Members"); }
    goToBorrowings() { this.goTo("library.borrowing", [], "Borrowings"); }
    goToOverdue() { this.goTo("library.borrowing", [["state", "=", "overdue"]], "Overdue Borrowings"); }
    goToFines() { this.goTo("library.fine", [["state", "=", "unpaid"]], "Unpaid Fines"); }
    goToReservations() { this.goTo("library.reservation", [["state", "=", "reserved"]], "Reservations"); }
}

registry.category("actions").add("library_management.Dashboard", LibraryDashboard);
