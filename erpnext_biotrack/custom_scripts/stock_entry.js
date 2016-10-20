frappe.ui.form.on("Stock Entry", {
    refresh: function (frm) {
        // set doc.company and hide
        erpnext.hide_company();

        ste.toggle_related_fields(frm);
        ste.set_warehouse_query(frm);
        ste.set_items_query(frm);
    },
    convert: function (frm) {
        ste.toggle_related_fields(frm);
    },
    convert_type: function (frm) {
        frm.toggle_reqd("lot_group", (frm.doc.convert_type === 'New Lot'));
        ste.reset_items(frm);
    },
    lot_group: function (frm) {
        ste.set_items_query(frm);
        ste.reset_items(frm);
    },
    from_warehouse: function (frm) {
        ste.set_items_query(frm);
    }
});

var ccscript = $.extend({}, cur_frm.cscript);
cur_frm.cscript = $.extend(cur_frm.cscript, {
    items_add: function (doc, cdt, cdn) {
        ccscript.items_add.apply(ccscript, arguments);

        if (!doc.convert) {
            return;
        }

        var doclist = doc['items'];
        var row = frappe.get_doc(cdt, cdn);
        if (doclist.length === 2 && doclist[0] !== row) {
            var strain = doclist[0]['strain'];

            // add strain into query filter to make sure next item is same strain
            ste.set_items_query(cur_frm, {strain: strain});
        }
    },
    items_remove: function (doc) {
        if (!doc.convert) {
            return;
        }

        // Reset item query base on first row
        if (doc['items'].length === 0) {
            ste.set_items_query(cur_frm);
        }
    },

});

var ste = {
    toggle_related_fields: function (frm) {
        frm.toggle_reqd("convert_type", frm.doc.convert);
        frm.toggle_reqd("lot_group", (frm.doc.convert_type === 'New Lot'));
    },
    reset_items: function (frm) {
        if (frm.is_new()) {
            frm.doc['items'] = [];
            refresh_field("items");
        }
    },
    set_warehouse_query: function (frm) {
        var filters = frm.fields_dict.from_warehouse.get_query().filters, i, is_filtered = false;
        for (i = 0; i < filters.length; i++) {
            is_filtered = is_filtered || (filters[i][1] == "warehouse_type");
        }

        if (!is_filtered) {
            filters.push([
                "Warehouse",
                "warehouse_type",
                "=",
                "Inventory Room"
            ]);

            frm.fields_dict.from_warehouse.get_query = function () {
                return {
                    filters: filters
                }
            };

            frm.fields_dict.to_warehouse.get_query = function () {
                return {
                    filters: filters
                }
            };

            frm.fields_dict.items.grid.get_field('s_warehouse').get_query = function () {
                return {
                    filters: filters
                }
            };

            frm.fields_dict.items.grid.get_field('f_warehouse').get_query = function () {
                return {
                    filters: filters
                }
            }
        }
    },
    set_items_query: function (frm, cond) {
        var filters = [{is_stock_item: 1}];

        if (cond) {
            filters.push(cond)
        }

        if (frm.doc.lot_group === 'Flower Lot') {
            filters.push({item_group: 'Flower'})
        } else if (frm.doc.lot_group === 'Other Plant Material Lot') {
            filters.push({item_group: 'Other Plant Material'});
        } /*else if (frm.doc.lot_group === 'Marijuana Mix') { // BioTrack api does not support this
         filters.push(['item_group', 'in', ['Flower', 'Other Plant Material']])
         }*/ else {
            // default
        }

        if (frm.doc.from_warehouse) {
            filters.push({default_warehouse: frm.doc.from_warehouse});
        }

        frm.fields_dict.items.grid.get_field('item_code').get_query = function () {
            return erpnext.queries.item(filters);
        };
    }
};
