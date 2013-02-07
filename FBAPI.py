#!/usr/bin/env python

import urllib2 as ur
import xml.etree.ElementTree as xmlparser
from datetime import date
from config import *

class FBAPI:
  def __init__(self, url, token):
    self.url = url
    self.token = token
  def request(self, method, elements):
    # TODO: Retire this function and make everything generate a proper element tree (ala x_request)
    xml = '<!--?xml version="1.0" encoding="utf-8"?--><request method="' + method + '">'
    for key in elements:
      xml = xml + '<' + key + '>' + elements[key] + '</' + key + '>'
    xml = xml + '</request>'
    pw = ur.HTTPPasswordMgrWithDefaultRealm()
    pw.add_password(None, url, token, 'X')
    auth = ur.HTTPBasicAuthHandler(pw)
    opener = ur.build_opener(auth)
    ur.install_opener(opener)
    page = ur.urlopen(url, xml)
    self.raw_xml = page.read()
    self.tree = xmlparser.fromstring(self.raw_xml)
    self.xmlns = self.tree.tag.split('}')[0][1:]
  def x_request(self, method, text):
    xml = '<!--?xml version="1.0" encoding="utf-8"?--><request method="' + method + '">'
    xml = xml + text
    xml = xml + '</request>'
    pw = ur.HTTPPasswordMgrWithDefaultRealm()
    pw.add_password(None, url, token, 'X')
    auth = ur.HTTPBasicAuthHandler(pw)
    opener = ur.build_opener(auth)
    ur.install_opener(opener)
    page = ur.urlopen(url, xml)
    self.raw_xml = page.read()
    print self.raw_xml
  def get_items(self):
    return self.tree[0]
    
class FBListNode:
  def __init__(self, item, xmlns):
    self.item = item
    self.xmlns = xmlns
  def elem(self, name):
    return self.item.find('{' + self.xmlns + '}' + name)
    
class FBClient:
  def __init__(self, element, xmlns):
    item = FBListNode(element, xmlns)
    self.id = int(item.elem('client_id').text)
    self.name = item.elem('organization').text
    self.street1 = item.elem('p_street1').text
    self.street2 = item.elem('p_street2').text
    self.city = item.elem('p_city').text
    self.state = item.elem('p_state').text
    self.zip = item.elem('p_code').text
    
class FBPayment:
  def __init__(self, element, xmlns):
    item = FBListNode(element, xmlns)
    self.id = int(item.elem('payment_id').text)
    self.client_id = int(item.elem('client_id').text)
    self.invoice_id = int(item.elem('invoice_id').text)
    dateparts = item.elem('date').text.split()[0].split('-')
    self.date = date(int(dateparts[0]), int(dateparts[1]), int(dateparts[2]))
    self.amount = float(item.elem('amount').text)
    self.type = item.elem('type').text

class FBInvoice:
  def __init__(self, client_id, date, lines, id=None, number=None, amount=None):
    self.id = id
    self.number = number
    self.client_id = client_id
    self.amount = amount
    self.date = date
    self.lines = lines
  def to_xml(self):
    invoice = xmlparser.Element('invoice')
    client_id = xmlparser.SubElement(invoice, 'client_id')
    client_id.text = self.client_id
    datefield = xmlparser.SubElement(invoice, 'date')
    datefield.text = self.date
    lines = xmlparser.SubElement(invoice, 'lines')
    for item in self.lines:
      line = xmlparser.SubElement(lines, 'line')
      name = xmlparser.SubElement(line, 'name')
      name.text = item.name
      unit_cost = xmlparser.SubElement(line, 'unit_cost')
      unit_cost.text = str(item.unit_cost)
      quantity = xmlparser.SubElement(line, 'quantity')
      quantity.text = str(item.quantity)
      amount = xmlparser.SubElement(line, 'amount')
      amount.text = str(item.amount)
      typefield = xmlparser.SubElement(line, 'type')
      typefield.text = item.category
      description = xmlparser.SubElement(line, 'description')
      description.text = item.description
    return xmlparser.tostring(invoice)

class FBInvoiceFromXML(FBInvoice):
  def __init__(self, element, xmlns):
    item = FBListNode(element, xmlns)
    self.id = int(item.elem('invoice_id').text)
    self.number = int(item.elem('number').text)
    self.client_id = int(item.elem('client_id').text)
    self.amount = float(item.elem('amount').text)
    dateparts = item.elem('date').text.split()[0].split('-')
    self.date = date(int(dateparts[0]), int(dateparts[1]), int(dateparts[2]))
    self.lines = []
    nodes = item.elem('lines')
    for node in nodes:
      node = FBListNode(node, xmlns)
      line = FBLineItem(node.elem('name').text, node.elem('unit_cost').text, node.elem('quantity').text)
      if line.amount > 0:
        self.lines.append(line)
    
class FBLineItem:
  def __init__(self, name, unit_cost, quantity, description=None, category='Time'):
    self.name = name
    self.unit_cost = float(unit_cost)
    self.quantity = float(quantity)
    self.amount = self.unit_cost * self.quantity
    self.description = description
    self.category = category
    
def get_clients():
  fb = FBAPI(url, token)
  clients = {}
  filters = {}
  filters['folder'] = 'active'
  filters['per_page'] = '100'
  fb.request('client.list', filters)
  items = fb.get_items()
  for item in items:
    client = FBClient(item, fb.xmlns)
    clients[client.id] = client

  filters = {}
  filters['folder'] = 'archived'
  filters['per_page'] = '100'
  fb.request('client.list', filters)
  items = fb.get_items()
  for item in items:
    client = FBClient(item, fb.xmlns)
    clients[client.id] = client
  return clients

def get_invoices(date_from):
  fb = FBAPI(url, token)
  invoices = {}
  filters = {}
  filters['folder'] = 'active'
  filters['date_from'] = date_from
  filters['per_page'] = '100'
  fb.request('invoice.list', filters)
  items = fb.get_items()
  for item in items:
    invoice = FBInvoiceFromXML(item, fb.xmlns)
    invoices[invoice.id] = invoice

  filters = {}
  filters['folder'] = 'archived'
  filters['date_from'] = date_from
  filters['per_page'] = '100'
  fb.request('invoice.list', filters)
  items = fb.get_items()
  for item in items:
    invoice = FBInvoice(item, fb.xmlns)
    invoices[invoice.id] = invoice
  return invoices
  
def get_payments(date_from):
  fb = FBAPI(url, token)
  payments = {}
  filters = {}
  filters['date_from'] = date_from
  filters['per_page'] = '100'
  fb.request('payment.list', filters)
  items = fb.get_items()
  for item in items:
    payment = FBPayment(item, fb.xmlns)
    payments[payment.id] = payment
  return payments
  
def print_all(invoices, payments, clients):
  for k in invoices:
    print "(%d) Inv %d    %s    %s    $%0.2f" % (k, invoices[k].number, invoices[k].date.isoformat(), clients[invoices[k].client_id].name, invoices[k].amount)
    for line in invoices[k].lines:
      print "  %30s  %0.2f @ $%0.2f  $%0.2f" % (line.name, line.quantity, line.unit_cost, line.amount)
    print "\n"
  for k in payments:
    print "%s paid $%0.2f on %s for inv %d with %s" % (clients[payments[k].client_id].name, payments[k].amount, payments[k].date.isoformat(), invoices[payments[k].invoice_id].number, payments[k].type)
  for k in clients:
    print "%s\n%s\n%s\n%s, %s %s\n" % (clients[k].name, clients[k].street1, clients[k].street2, clients[k].city, clients[k].state, clients[k].zip)

def main():
  print "Use the included utilities to perform FreshBooks API functions."

if __name__ == '__main__':
  main()
  

