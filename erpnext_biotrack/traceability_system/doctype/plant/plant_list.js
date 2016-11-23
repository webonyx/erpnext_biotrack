frappe.listview_settings['Plant'] = {
    add_fields: ['disabled', 'posting_date', 'destroy_scheduled'],
    filters: [["disabled", "=", "No"]],
    get_indicator: function (doc) {
        if (doc.disabled) {
            return [__("Destroyed"), "grey", "disabled,=,Yes"];
        } else if (doc.destroy_scheduled) {
            return [__("Destroy Scheduled"), "orange", "destroy_scheduled,=,Yes"];
        } else {
            return [this.calculate_time_in_room(doc.posting_date), "green", "disabled,=,No"];
        }
    },

    onload: function (DocListView) {
        DocListView.listview.stats.push("state");
        DocListView.listview.stats.push("plant_room");

        if (frappe.boot.biotrackthc_sync_down) {
            DocListView.page.add_action_item(__("BioTrackTHC Sync"), function () {
                frappe.call({
                    method: "erpnext_biotrack.tasks.client_sync",
                    args: {"doctype": "Plant"}
                })
            })
        }
    },
    calculate_time_in_room: function (posting_date) {
        var diff = frappe.datetime.get_diff(frappe.datetime.get_today(), posting_date);
        if (diff == 0) {
            return comment_when(posting_date);
        }

        if (diff == 1) {
            return __('Yesterday')
        }

        if (diff == 2) {
            return __('2 days ago')
        }

        return diff + ' days';
    }
};
