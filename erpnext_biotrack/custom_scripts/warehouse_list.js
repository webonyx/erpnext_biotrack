frappe.listview_settings['Warehouse'] = {
    add_fields: ["disabled"],
    get_indicator: function(doc) {
		if (doc.disabled) {
			return [__("Disabled"), "grey", "disabled,=,Yes"];
		}
	},
	onload: function (DocListView) {
		DocListView.page.add_action_item(__("Synchronization"), function () {
            frappe.call({
                method: "erpnext_biotrack.tasks.client_sync",
                args: {"doctype": "Warehouse"}
            })
        })
	}
};