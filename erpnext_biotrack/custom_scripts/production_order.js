frappe.ui.form.on("Production Order", {
    onload: function (frm) {
        frm.set_indicator_formatter('item_code',
            function (doc) {
                return (frm.doc.qty==doc.completed_qty) ? "green" : "orange";
            },
            function (doc) {
                return frappe.form.link_formatters['Item'](doc.item_code, doc);
            }
        )
    }
});