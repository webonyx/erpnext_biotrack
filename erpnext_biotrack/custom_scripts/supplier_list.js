frappe.listview_settings['Supplier'] = {
	// add_fields: ["supplier_name", "supplier_type", 'status'],
	// filters: [],
	// group_by: 'supplier_type',
	// get_indicator: function(doc) {
	// 	if(doc.status==="Open") {
	// 		return [doc.status, "red", "status,=," + doc.status];
	// 	}
	// },
    onload: function (DocListView) {
        // DocListView.page.add_action_item(__("Custom Action"), function() {
		// }, "octicon octicon-sync");

        DocListView.listview.stats.push("supplier_type")

    },
    refresh: function (DocListView) {
        // DocListView.page.add_sidebar_item(__("QA Labs"), function() {
         //    DocListView.set_filter('supplier_type', 'Lab & Scientific')
		// }, false, true);
    },

    /*before_run: function (DocListView) {

    },

    post_render_item: function (DocListView, row, data) {

    },

    post_render: function (DocListView) {

    }*/
};
