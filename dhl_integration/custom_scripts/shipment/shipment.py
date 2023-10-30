import frappe
from dhl_integration.dhl_integration.doctype.dhl_settings.dhl_settings import DHLUtils

@frappe.whitelist()
def create_shipment(shipment='SHIPMENT-00004'):
	dhl = DHLUtils()
	dhl.create_shipment(shipment)
