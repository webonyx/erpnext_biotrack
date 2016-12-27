from frappe import _

def get_data():
	return {
		'non_standard_fieldnames': {
			'Stock Entry': 'plant',
			'Plant Entry': 'plant_code',
			'Item': 'plant',
		},
		'transactions': [

			{
				'label': _('Traceability'),
				'items': ['Stock Entry', 'Plant Entry', 'Item']
			}
		]
	}