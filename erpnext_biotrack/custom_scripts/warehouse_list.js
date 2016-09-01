frappe.listview_settings['Warehouse'] = {
    add_fields: ["disabled"],
    get_indicator: function(doc) {
		if (doc.disabled) {
			return [__("Disabled"), "grey", "disabled,=,Yes"];
		}
	}
};