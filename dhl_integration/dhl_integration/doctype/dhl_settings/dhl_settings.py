# Copyright (c) 2023, Othermo GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password
from datetime import datetime
from dhl_integration.utils.countries import get_country_code
import requests
import base64
import json
from frappe.utils import get_files_path

class DHLSettings(Document):
	pass

class DHLUtils():
	def __init__(self):
		self.enabled = frappe.db.get_single_value('DHL Settings', 'enabled')
		if not self.enabled:
			frappe.throw("Please enable DHL Integration in DHL Settings")
			
		doc = frappe.get_doc('DHL Settings', 'DHL Settings')
		self.api_key = doc.api_key
		self.api_secret = get_decrypted_password('DHL Settings', 'DHL Settings', 'api_secret')
		self.username = doc.username
		self.password = get_decrypted_password('DHL Settings', 'DHL Settings', 'password')
		
		if doc.is_sandbox:
			self.base_url = "https://api-sandbox.dhl.com/parcel/de/shipping/v2/"
		else:
			self.base_url = "https://api-eu.dhl.com/parcel/de/shipping/v2/"
			
	def create_shipment(self, shipment):
		shipments = {}
		
		shipment_doc = frappe.get_doc("Shipment", shipment)
		today = datetime.strptime(frappe.utils.now(), "%Y-%m-%d %H:%M:%S.%f").date()
		if shipment_doc.pickup_date < today:
			frappe.throw("The pickup date must be after today's date")
		
		consignee, dhl_product = self.get_consignee(shipment_doc)
		dhl_product_code = None
		if dhl_product == "DHLPaket":
			dhl_product_code = "V01PAK"
		else:
			dhl_product_code = "V53WPAK"
			
		billing_number = frappe.db.get_value("DHL Billing Number", {"service": dhl_product}, "billing_number")
		
		if not billing_number or billing_number == "":
			frappe.throw(f"Please enter a billing number for the {dhl_product} service in DHL Settings")
		
		shipments.update({
			"product": dhl_product_code,
			"billingNumber": billing_number,
			"shipDate": datetime.strftime(shipment_doc.pickup_date, "%Y-%m-%d"),
			"shipper": self.get_shipper(shipment_doc),
			"consignee": consignee,
			"details": self.get_details(shipment_doc, 1)
		})
		
		try:
			url = f"{self.base_url}/orders"
			token = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
			header = {
				'content-type': "application/json",
				"Authorization": f"Basic {token}",
				"dhl-api-key": self.api_key
			}
			data = {
				"profile": "",
				"shipments": [shipments]
			}
			
			data = json.dumps(data)
			response = requests.post(url, data=data, headers=header)
			if response.status_code == 200:
				content = response.json()
				if content.get("items"):
					item = content.get("items")[0]
					frappe.db.set_value(shipment_doc.doctype, shipment_doc.name, "service_provider", "DHL", update_modified=False)
					frappe.db.set_value(shipment_doc.doctype, shipment_doc.name, "carrier", "DHL", update_modified=False)
					frappe.db.set_value(shipment_doc.doctype, shipment_doc.name, "carrier_service", dhl_product, update_modified=False)
					frappe.db.set_value(shipment_doc.doctype, shipment_doc.name, "shipment_id", item.get("shipmentNo"), update_modified=False)
					self.save_file(shipment_doc, item.get("label").get("b64"))
					return "OK"
			else:
				self.post_error(response.json())
		except Exception as e:
			frappe.throw(str(e))
		
	def get_shipper(self, shipment_doc):
		ret_address = frappe._dict()
		address = frappe.get_doc('Address', shipment_doc.pickup_address_name)
		pickup_name, pickup_email = frappe.db.get_value('User', shipment_doc.pickup_contact_person, ["full_name", "email"])
		ret_address.update({
			"name1": shipment_doc.pickup_company,
			"addressStreet": address.address_line1,
			"postalCode": address.pincode,
			"city": address.city,
			"country": get_country_code(address.country),
			"contactName": pickup_name,
			"email": pickup_email
		})
		
		if address.address_line2:
			ret_address.update({
				"addressHouse": address.address_line2
			})
		return ret_address
		
	def get_consignee(self, shipment_doc):
		# DHL product: DHLPaket if is Germany, otherwise DHLPaketInternational
		product = "DHLPaket"
		 
		ret_address = frappe._dict()
		address = frappe.get_doc('Address', shipment_doc.delivery_address_name)
		contact = frappe.get_doc('Contact', shipment_doc.delivery_contact_name)
		contact_name = f"{contact.first_name} {contact.last_name or ''}"
		
		ret_address.update({
			"name1": shipment_doc.delivery_customer,
			"addressStreet": address.address_line1,
			"postalCode": address.pincode or "",
			"city": address.city,
			"state": address.state or "",
			"country": get_country_code(address.country),
			"contactName": contact_name,
			"phone": contact.phone or contact.mobile_no or "",
			"email": contact.email_id or ""
		})
		
		if address.address_line2:
			ret_address.update({
				"additionalAddressInformation1": address.address_line2
			})
		
		# Determine the product based on the country of the consignee
		if address.country != "Germany":
			product = "DHLPaketInternational"
		
		return ret_address, product
		
	def get_details(self, shipment_doc, idx):
		details = frappe._dict()
		details.update({
			"dim": {
				"uom": "cm",
				"height": shipment_doc.shipment_parcel[0].height,
				"length": shipment_doc.shipment_parcel[0].length,
				"width": shipment_doc.shipment_parcel[0].width
			}, 
			"weight": {
				"uom": "kg",
				"value": shipment_doc.shipment_parcel[0].weight
			}
		})
		return details
		
	def post_error(self, content):
		res = ""
		log = frappe.new_doc("Error Log")
		log.update({
			"method": "DHL Error",
			"error": str(content)
		})
		log.save()
		link_to_log = frappe.utils.get_link_to_form("Error Log", log.name, "Link to full error log")
		if content.get("items"):
			res = frappe.render_template("""
						<table class="table table-bordered">
						<tr>
							<th>Property</th>
							<th> Description </th>
						</tr>
						{% for item in items %}
							{% for message in item.validationMessages %}
								<tr>
									<th>{{ message.property }} </th>
									<td>{{ message.validationMessage }} </td>
								</tr>
							{% endfor %}
						{% endfor %}
						</table>
						<br>
						{{link_to_log}}
					""", {"items": content.get("items"), "link_to_log": link_to_log})
		else:
			res = f"Error while fetching order. Please view full error log {link_to_log}"
		frappe.msgprint(res)
		
	def save_file(self, shipment_doc, label_content):
		file_path = get_files_path(f"{shipment_doc.name}_label.pdf", is_private=True)
		with open(file_path, 'wb') as f:
			f.write(base64.b64decode(label_content))
			
		file_doc = frappe.new_doc('File')
		file_doc.update({
			'file_name': f"{shipment_doc.name}_label.pdf",
			'file_url': file_path.replace(frappe.get_site_path(), ''),
			'is_private': 1,
			'folder': 'Home/Attachments',
			'attached_to_doctype': shipment_doc.doctype,
			'attached_to_name': shipment_doc.name,
			'attached_to_field': None
		})
		file_doc.insert(ignore_permissions=True)
