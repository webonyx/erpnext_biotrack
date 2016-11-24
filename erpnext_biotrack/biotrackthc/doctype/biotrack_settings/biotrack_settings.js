// Copyright (c) 2016, Webonyx and contributors
// For license information, please see license.txt

frappe.ui.form.on('BioTrack Settings', {
    refresh: function (frm) {
        if (frm.doc.username) {
            if (frm.doc.synchronization == 'All' || frm.doc.synchronization == 'Down') {
                cur_frm.add_custom_button('<span class="octicon octicon-sync" aria-hidden="true"></span> ' + __('Sync Now'),
                    function () {
                        frappe.call({
                            method: "erpnext_biotrack.biotrackthc.doctype.biotrack_settings.biotrack_settings.sync_now"
                        })
                    }
                )
            }

            if (frm.doc.is_training) {
                cur_frm.set_intro('Training mode is enabled')
            }
        }

        cur_frm.add_custom_button('<span class="octicon octicon-info" aria-hidden="true"></span> ' + __("Show Log"), function () {
            frappe.route_options = {"integration_request_service": "BioTrack"};
			frappe.set_route("List", "Integration Request");
        });

        $('<a class="btn btn-link btn-xs"' +
            ' href="https://github.com/webonyx/erpnext_biotrack#erpnext-biotrack"' +
            ' target="_blank" style="margin-left: 10px;"><span class="octicon octicon-question" aria-hidden="true"></span> ' + __("Help") + '</a>')
            .appendTo(cur_frm.page.inner_toolbar);
    }

});