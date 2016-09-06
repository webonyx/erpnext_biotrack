frappe.listview_settings['Plant'] = {
    add_fields: ['disabled', 'birthdate'],
    filters: [["disabled", "=", "No"]],
    get_indicator: function (doc) {
        if (doc.disabled) {
            return [__("Disabled"), "grey", "disabled,=,Yes"];
        } else {
            return [this.calculate_time_in_room(doc.birthdate), "green", "disabled,=,No"];
        }
    },

    onload: function (DocListView) {
        DocListView.listview.stats.push("state");
        DocListView.listview.stats.push("warehouse");

        DocListView.page.add_action_item(__("Synchronization"), function () {
            frappe.call({
                method: "erpnext_biotrack.tasks.sync_plant"
            })
        })
    },
    calculate_time_in_room: function (birthdate) {
        var diff = dateutil.get_diff(dateutil.get_today(), birthdate.split(' ')[0]);
        if (diff == 0) {
            return comment_when(birthdate);
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
