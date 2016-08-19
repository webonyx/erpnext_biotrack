var hidden_fields = {
    creation: {
        fieldtype: "Int", // set to int so it will align right
        fieldname: "creation",
        label: "Creation",
        options: {}
    }
};

frappe.listview_settings['Plant'] = {
    add_fields: ['creation'],
    add_columns: {
        creation: {
            colspan: 3,
			content: hidden_fields.creation.fieldname,
			type: hidden_fields.creation.fieldtype,
			df: hidden_fields.creation,
			fieldtype: hidden_fields.creation.fieldtype,
			fieldname: hidden_fields.creation.fieldname,
			title: "Time In Room"
        }
    },
    formatters: {
        creation: function (value, df, data) {
            var diff = dateutil.get_diff(dateutil.get_today(), value.split(' ')[0]);
            // if (diff == 0) {
            //     return comment_when(value);
            // }
            //
            // if (diff == 1) {
            //     return __('Yesterday')
            // }
            //
            // if (diff == 2) {
            //     return __('2 days ago')
            // }

            return diff + ' days';
        }
    },

    onload: function (DocListView) {
       DocListView.listview.stats.push("warehouse")

    }
};
