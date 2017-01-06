var available_products = [];

var ste_listeners = {
    onload: function (frm) {
        // readonly for product_group: do not show Create New or Advance Search
        frm.set_df_property("product_group", "only_select", true);
    },
    refresh: function (frm) {
        ste_listeners.toggle_related_fields(frm);
        ste.set_items_query(frm);
    },
    validate: function (frm) {
        var doc = frm.doc;

        if (!doc.conversion) {
            return
        }


    },
    toggle_related_fields: function (frm) {
        var conversion_support = frm.doc.purpose === 'Material Issue'

        frm.toggle_display("conversion_sec", conversion_support);
        frm.toggle_display("lot_group", frm.doc.conversion == 'Create Lot');

        frm.toggle_display(
            ["product_group", "product_name", "product_qty", "product_usable", "product_waste"],
            frm.doc.conversion == 'Create Product'
        );

        frm.toggle_reqd('product_group', frm.doc.conversion === 'Create Product');
        frm.toggle_reqd('product_qty', frm.doc.conversion === 'Create Product');
        frm.toggle_reqd('lot_group', frm.doc.conversion === 'Create Lot');
    },
    purpose: function (frm) {
        ste_listeners.toggle_related_fields(frm);
    },
    conversion: function (frm) {
        ste_listeners.toggle_related_fields(frm);
        ste.set_items_query(frm);

        if (frm.doc.conversion === 'Create Product') {
            if (!available_products.length) {
                frappe.call({
                    method: 'erpnext_biotrack.controllers.queries.available_products',
                    callback: function (r) {
                        available_products = r.message || [];
                        ste.set_product_query(frm);

                        if (!available_products.length) {
                            frappe.msgprint({
                                    title: __('No Product Available'),
                                    message: __('There is not products can be made from your current inventory'),
                                    indicator: 'red'
                                }
                            );

                            frm.set_value('conversion', '')
                        }
                    }
                });
            }
        }
    },
    product_group: function (frm) {
        frappe.call({
            method: 'erpnext_biotrack.controllers.queries.lookup_product_sources',
            args: {product: frm.doc.product_group},
            callback: function (r) {
                ste.item_filters.item_group = ['item_group', 'in', r.message || []];
                ste.set_items_query(frm);
            }
        });
    },

    lot_group: function (frm) {
        ste.set_items_query(frm);
    },
    from_warehouse: function (frm) {
        ste.set_items_query(frm);
    }
};

frappe.ui.form.on("Stock Entry", ste_listeners);
frappe.ui.form.on("Stock Entry Detail", {
    items_add: function (frm, cdt, cdn) {
        var doc = frm.doc
        if (!doc.conversion) {
            return;
        }

        var doclist = doc['items'];
        var row = frappe.get_doc(cdt, cdn);
        if (doclist.length === 2 && doclist[0] !== row) {
            var strain = doclist[0]['strain'];
            ste.item_filters.strain = {strain: strain};
            // add strain into query filter to make sure next item is same strain
            ste.set_items_query(cur_frm);
        }

    },
    items_remove: function (frm) {
        var doc = frm.doc

        if (!doc.conversion) {
            return;
        }

        // Reset item query base on first row
        if (doc['items'].length === 0) {
            ste.item_filters.strain = null;
            ste.set_items_query(cur_frm)
        }
    }
});

var ste = {
    item_filters: {
        item_group: null
    },

    reset_items: function (frm) {
        if (frm.is_new()) {
            frm.doc['items'] = [];
        }

        refresh_field("items");
    },
    set_product_query: function (frm) {
        frm.fields_dict.product_group.get_query = function () {
            return {
                filters: [['item_group_name', 'in', available_products]]
            }
        }
    },

    set_items_query: function (frm) {
        var filters = [{is_stock_item: 1}];
        var conditions = {
            conversion: {
                'Create Lot': {
                    'Flower Lot': {
                        item_group: 'Flower'
                    },
                    'Other Plant Material Lot': {
                        item_group: 'Other Plant Material'
                    }
                },
            }
        };

        if (ste.item_filters.strain && Object.keys(ste.item_filters.strain).length > 0) {
            filters.push(ste.item_filters.strain);
        }

        if (frm.doc.conversion) {
            var cond = conditions.conversion[frm.doc.conversion];
            if (cond) {
                cond = cond[frm.doc.lot_group];
                if (cond) {
                    filters.push(cond)
                }
            } else if (ste.item_filters.item_group) {
                filters.push(ste.item_filters.item_group);
            }
        }

        if (frm.doc.from_warehouse) {
            filters.push({default_warehouse: frm.doc.from_warehouse});
        }

        frm.fields_dict.items.grid.get_field('item_code').get_query = function () {
            return erpnext.queries.item(filters);
        };
    }
};
