var erpnext_item_link_formatter = frappe.form.link_formatters['Item'];

frappe.form.link_formatters['Item'] = function (value, doc) {
    if (!value|| value.length == 16) {
        return doc && doc.item_name ? doc.item_name : value;
    }

    return erpnext_item_link_formatter(value, doc);
};