$.extend(frappe.listview_settings['Customer'], {
    onload: function (DocListView) {
        DocListView.listview.stats.push("customer_group");
        if (frappe.boot.biotrackthc_sync_down) {
            DocListView.page.add_action_item(__("BioTrackTHC Sync"), function () {
                frappe.call({
                    method: "erpnext_biotrack.biotrackthc.doctype.biotrack_settings.biotrack_settings.sync_now",
                    args: {"doctype": "Customer"}
                })
            })
        }
    }
});

