from frappe import _

def get_data():
	return {
		'non_standard_fieldnames': {
			'Stock Entry': 'plant',
		},
		'transactions': [
			# {
			# 	'label': _('Traceability'),
			# 	'items': ['Item']
			# },
			{
				'label': _('Traceability'),
				'items': ['Stock Entry']
			}
		]
	}