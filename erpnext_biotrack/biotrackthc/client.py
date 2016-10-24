import os, json, frappe

from frappe.modules.import_file import read_doc_from_file
from frappe.utils import get_request_session, encode
from frappe.utils.data import flt, cint

class BioTrackClientError(frappe.ValidationError):
    http_status_code = 500

    def __init__(self, *args, **kwargs):
        if len(args) and isinstance(args[0], basestring):
            frappe.local.message_log.append(args[0])

        super(frappe.ValidationError, self).__init__(*args, **kwargs)


class BioTrackEmptyDataError(BioTrackClientError): pass


class BioTrackClient:
    __API__ = "4.0"
    __API_URL__ = "https://wslcb.mjtraceability.com/serverjson.asp"

    def __init__(self, license_number, username, password, is_training=0):
        self.license_number = license_number
        self.username = username
        self.password = password
        self.is_training = is_training

    def post(self, action, data, raise_on_empty=True):
        if not isinstance(data, dict):
            raise BioTrackClientError("data must be instance of dict")

        data["action"] = action
        action_data = data.copy()

        data.update({
            "license_number": self.license_number,
            "username": self.username,
            "password": self.password,
            "training": self.is_training,
            "API": self.__API__,
        })

        if action != 'login':
            data["nosession"] = 1

        print_log(data, " - Request Data")

        request = get_request_session()
        response = request.post(self.__API_URL__, data=json.dumps(data), headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        result = response.json()

        if not result.get('success'):
            raise BioTrackClientError(encode(result.get('error')))

        if raise_on_empty and len(result) == 1:
            raise BioTrackEmptyDataError(
                'BioTrackTHC request was response empty data: {}'.format(json.dumps(action_data))
            )

        print_log(result, " - Response")

        return result

    def login(self):
        return self.post('login', {})


def get_client(license_number, username, password, is_training=0):
    """
    :return BioTrackClient:
    """
    return BioTrackClient(license_number, username, password, is_training)


def get_data(action, params=None, key=None):
    result = post(action, data=params)
    if key and key in result:
        return result[key]

    return result


def post(action, data):
    settings = frappe.get_doc("BioTrack Settings")
    if not settings.enable_biotrack:
        raise BioTrackClientError('BioTrackTHC integration is not enabled')

    client = get_client(settings.license_number, settings.username, settings.get_password(), settings.is_training)

    def try_from_cache():
        filename = action + '.json'
        training_dir = '/training' if settings.is_training else ''
        cache_dir = frappe.get_app_path("erpnext_biotrack",
                                        "fixtures/offline_sync{training_dir}".format(training_dir=training_dir))

        if not os.path.exists(cache_dir):
            os.mkdir(cache_dir)

        f = frappe.get_app_path("erpnext_biotrack", cache_dir, filename)

        if os.path.exists(f):
            result = read_doc_from_file(f)
        else:
            result = client.post(action, data)
            with open(f, "w") as outfile:
                outfile.write(frappe.as_json(result))

        return result

    offline_sync = frappe.conf.get('erpnext_biotrack.offline_sync') or 0
    if action.startswith("sync_") and offline_sync:
        return try_from_cache()

    return client.post(action, data)


def create_lot(stock_entry):
    qty = 0
    data = []
    for entry in stock_entry.get("items"):
        data.append({
            "barcodeid": entry.item_code,
            "remove_quantity": entry.qty,
            "remove_quantity_uom": "g",
        })
        qty += entry.qty

    response = {}
    try:
        response = post("inventory_create_lot", {"data": data})
    except BioTrackClientError as ex:
        frappe.local.message_log.pop()
        frappe.throw(ex.message, title="BioTrack Request Failed")

    try:
        from ..item_utils import make_lot_item
        strain = frappe.get_value("Item", stock_entry.get("items")[0].item_code, "strain")
        item = make_lot_item({
            "item_code": response.get("barcode_id"),
            "barcode": response.get("barcode_id"),
            "item_group": stock_entry.lot_group,
            "default_warehouse": stock_entry.from_warehouse,
            "strain": strain,
        }, qty)

        stock_entry.lot_item = item.item_code
        stock_entry.save()
    except Exception:
        post("inventory_convert_undo", {"barcodeid": [response.get("barcode_id")]})
        raise

def create_product(stock_entry):
    conversion_type = frappe.get_value("Item Group", stock_entry.product_group, "external_id")

    if not conversion_type:
        frappe.throw("Inventory Type not found")

    qty = 0
    data = []
    request_data = {}

    for entry in stock_entry.get("items"):
        data.append({
            "barcodeid": entry.item_code,
            "remove_quantity": flt(entry.qty),
            "remove_quantity_uom": "g",
        })
        qty += entry.qty

    request_data["data"] = data
    request_data["derivative_type"] = cint(conversion_type)
    request_data["derivative_quantity"] = flt(stock_entry.product_qty)
    request_data["derivative_quantity_uom"] = "g"
    request_data["waste"] = flt(stock_entry.product_waste)
    request_data["waste_uom"] = "g"

    product_usable = flt(stock_entry.product_usable)
    if product_usable:
        request_data["derivative_usable"] = product_usable

    if stock_entry.product_name:
        request_data["derivative_product"] = stock_entry.product_name

    response = {}
    try:
        response = post("inventory_convert", request_data)
    except BioTrackClientError as ex:
        frappe.local.message_log.pop()
        frappe.throw(ex.message, title="BioTrack Request Failed")

    derivatives = response.get("derivatives", [])
    try:
        from ..item_utils import make_item
        for derivative in derivatives:
            item_type = derivative.get("barcode_type")
            barcode = derivative.get("barcode_id")

            # Waste
            if item_type == 27:
                make_item(properties={
                    "item_name": "Waste",
                    "item_code": barcode,
                    "barcode": barcode,
                    "item_group": "Waste",
                    "default_warehouse": stock_entry.from_warehouse,
                }, qty=stock_entry.product_waste)
                stock_entry.waste_item = barcode

            if item_type == conversion_type:
                make_item(properties={
                    "item_name": stock_entry.product_name or stock_entry.product_group,
                    "item_code": barcode,
                    "barcode": barcode,
                    "item_group": stock_entry.product_group,
                    "default_warehouse": stock_entry.from_warehouse,
                }, qty=stock_entry.product_qty)

                stock_entry.product_item = barcode

        stock_entry.save()

    except Exception:
        barcodeid = []
        for derivative in derivatives:
            barcodeid.append(derivative.get("barcode_id"))
        post("inventory_convert_undo", {"barcodeid": barcodeid})
        raise


def print_log(data, description=None):
    if (frappe.conf.get("logging") or 0) > 0:
        frappe.log("<<<< BioTrackTHC{description}".format(description=description))
        frappe.log(json.dumps(data))
        frappe.log(">>>>")
