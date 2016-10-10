frappe.ui.form.on("Quotation", {
    onload: function (frm) {
        frm.set_indicator_formatter('item_code',
            function (doc) {
                return doc.test_result === "Passed" ? "green" :
                    doc.test_result !== undefined ? 'orange' : '';
            },
            function (doc) {
                return frappe.form.link_formatters['Item'](doc.item_code, doc);
            }
        )
    }
});
