$.extend(cur_frm.cscript, {
    custom_setup: function () {
        this.frm.get_field('items').grid.editable_fields = [
            {fieldname: 'item_code', columns: 4},
            {fieldname: 'item_name', columns: 3},
            {fieldname: 'qty', columns: 1},
            {fieldname: 'rate', columns: 1},
            {fieldname: 'amount', columns: 1}
        ];
    }
});