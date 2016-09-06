frappe.ui.form.on("Purchase Invoice", {
    onload: function (frm) {
        frm.set_indicator_formatter('item_code',
            function (doc) {
                return (doc.qty<=doc.received_qty) ? "green" : "orange";
            },
            function (doc) {
                return frappe.form.link_formatters['Item'](doc.item_code, doc);
            }
        )
    }
});