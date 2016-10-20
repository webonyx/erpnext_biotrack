var erpnext_item_link_formatter = frappe.form.link_formatters['Item'];

frappe.form.link_formatters['Item'] = function (value, doc) {
    var text;

    if (doc && doc.item_code !== value) {
        doc = null
    }

    if (!value || value.length == 16) {
        text = doc && doc.item_name ? doc.item_name : value;
    } else {
        text = erpnext_item_link_formatter(value, doc);
    }

    if (doc && doc.test_result) {
        text += ' - ' + doc.test_result
    }

    return text;
};

$(document).on("autocompletesearch", '[data-fieldname="item_code"]', function (event, ui) {
    var $target = $(event.target), _renderItem = $target.data('ui-autocomplete')._renderItem;
    if ($target.data('autocomplete-hacked'))
        return;

    $target.data('autocomplete-hacked', true);
    $target.data('ui-autocomplete')._renderItem = function (ul, d) {
        // Create New & Advance Search
        if (!d.description) {
            return _renderItem(ul, d);
        }

        // do not want to hack server queries, last part is item_name
        var parts = d.description.split(',').filter(function (part) {
            return $.trim(part) != ''
        });

        var html = "<strong>" + __(parts.pop()) + "</strong>";
        html += '<br><span class="small">' + __(d.value) + '</span>';

        return $('<li></li>')
            .data('item.autocomplete', d)
            .html('<a><p>' + html + '</p></a>')
            .appendTo(ul);
    };
});
