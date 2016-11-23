$.extend(frappe.listview_settings['Employee'], {
    onload: function (DocListView) {
        if (frappe.boot.biotrackthc_sync_down) {
            DocListView.page.add_action_item(__("BioTrackTHC Sync"), function () {
                frappe.call({
                    method: "erpnext_biotrack.tasks.client_sync",
                    args: {"doctype": "Employee"}
                })
            })
        }
    }
});
