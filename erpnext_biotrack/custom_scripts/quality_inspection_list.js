frappe.listview_settings['Quality Inspection'] = {
    onload: function (DocListView) {
        DocListView.page.add_action_item(__("Synchronization"), function () {
            frappe.call({
                method: "erpnext_biotrack.tasks.client_sync",
                args: {"doctype": "Quality Inspection"}
            })
        })
    }
}