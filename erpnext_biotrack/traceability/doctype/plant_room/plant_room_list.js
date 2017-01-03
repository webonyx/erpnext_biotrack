// Copyright (c) 2016, Webonyx and contributors
// For license information, please see license.txt

frappe.listview_settings['Plant Room'] = {
    onload: function (ListView) {
        if (frappe.boot.biotrackthc_sync_down) {
            ListView.page.add_action_item(__("BioTrackTHC Sync"), function () {
                frappe.call({
                    method: "erpnext_biotrack.biotrackthc.doctype.biotrack_settings.biotrack_settings.sync_now",
                    args: {"doctype": "Plant Room"}
                })
            })
        }
    }
};
