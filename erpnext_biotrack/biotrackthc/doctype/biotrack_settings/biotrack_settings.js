// Copyright (c) 2016, Webonyx and contributors
// For license information, please see license.txt

frappe.ui.form.on('BioTrack Settings', {
    refresh: function (frm) {
        frm.events.toggle_location(frm);

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
    },

    synchronization: function (frm) {
        frm.events.toggle_location(frm);
    },

    toggle_location: function (frm) {
        var needLocation = (frm.doc.synchronization == 'All' || frm.doc.synchronization == 'Up');

        frm.toggle_reqd("location", needLocation);
        frm.toggle_display("location", needLocation);
        frm.toggle_display("detect_location", needLocation && frm.doc.license_number && frm.doc.username && frm.doc.password);
    }
});

cur_frm.cscript.detect_location = function () {
    var dialog = new frappe.ui.Dialog({
        title: __('Detect Location'),
        fields: [
            {
                fieldname: 'location_list',
                label: __('Found Locations'),
                fieldtype: 'Select',
                hidden: 1,
                options: []
            }
        ]
    });

    frappe.call({
        method: "erpnext_biotrack.biotrackthc.doctype.biotrack_settings.biotrack_settings.detect_locations",
        callback: function (r) {
            var location_list = dialog.get_field('location_list');
            location_list.df.options = r.message.locations;
            location_list.df.reqd = 1;
            location_list.df.hidden = 0;
            dialog.refresh();
            if (r.message.locations.length === 1) {
                location_list.set_value(r.message.locations[0]);
            }

            dialog.loading_indicator.addClass('hidden');
        }
    });

    dialog.set_primary_action(__('Select'), function () {
        cur_frm.set_value('location', dialog.get_value('location_list'));
        dialog.hide();
    });

    dialog.msg_area = $('<div class="msgprint">')
        .appendTo(dialog.body);

    dialog.loading_indicator = $('<div class="loading-indicator text-center" \
    		style="margin: 15px;">\
    		<img src="/assets/frappe/images/ui/ajax-loader.gif"></div>')
        .appendTo(dialog.body);

    dialog.show();
}