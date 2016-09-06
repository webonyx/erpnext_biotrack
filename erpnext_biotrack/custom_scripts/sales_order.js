frappe.ui.form.on("Sales Order", {
    onload: function (frm) {
        frm.set_indicator_formatter('item_code',
            function (doc) {
                return (doc.qty <= doc.delivered_qty) ? "green" : "orange";
            },
            function (doc) {
                return frappe.form.link_formatters['Item'](doc.item_code, doc);
            }
        )
    }
});