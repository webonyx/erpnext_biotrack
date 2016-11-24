$.extend(frappe.listview_settings['Employee'], {
    onload: function (DocListView) {
        if (frappe.boot.biotrackthc_sync_down) {
            DocListView.page.add_action_item(__("BioTrackTHC Sync"), function () {
                frappe.call({
                    method: "erpnext_biotrack.biotrackthc.doctype.biotrack_settings.biotrack_settings.sync_now",
                    args: {"doctype": "Employee"}
                })
            })
        }
    }
});
