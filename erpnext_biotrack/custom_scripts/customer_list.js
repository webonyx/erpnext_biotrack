$.extend(frappe.listview_settings['Customer'], {
    onload: function (DocListView) {
        DocListView.listview.stats.push("customer_group");
        DocListView.page.add_action_item(__("Synchronization"), function () {
            frappe.call({
                method: "erpnext_biotrack.tasks.client_sync",
                args: {"doctype": "Customer"}
            })
        })
    }
});

