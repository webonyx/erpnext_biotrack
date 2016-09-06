frappe.ui.form.on("Material Request", {
    onload: function (frm) {
        // formatter for material request item
        frm.set_indicator_formatter('item_code',
            function (doc) {
                return (doc.qty <= doc.ordered_qty) ? "green" : "orange";
            },
            function (doc) {
                return frappe.form.link_formatters['Item'](doc.item_code, doc);
            }
        )
    }
});