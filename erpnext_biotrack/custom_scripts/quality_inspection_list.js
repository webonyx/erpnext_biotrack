frappe.listview_settings['Quality Inspection'] = {
    onload: function (DocListView) {
        DocListView.page.add_action_item(__("BioTrackTHC Sync"), function () {
            frappe.call({
                method: "erpnext_biotrack.biotrackthc.doctype.biotrack_settings.biotrack_settings.sync_now",
                args: {"doctype": "Quality Inspection"}
            })
        })
    }
}