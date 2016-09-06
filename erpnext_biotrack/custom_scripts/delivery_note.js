frappe.ui.form.on("Delivery Note", {
    onload: function (frm) {
        frm.set_indicator_formatter('item_code',
            function (doc) {
                return (doc.docstatus == 1 || doc.qty <= doc.actual_qty) ? "green" : "orange"
            },
            function (doc) {
                return frappe.form.link_formatters['Item'](doc.item_code, doc);
            }
        )
    }
});