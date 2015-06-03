import datetime
import decimal
import sys
import os.path

def text(s): return s
def number(s): return decimal.Decimal(s.replace(',', ''))
def currency(s):
  if s[0] != '$': raise Exception("Should start with $: [" + s + "]")
  return number(s[1:])
def date(s):
  return datetime.datetime.strptime(s, '%d-%b-%Y')
def price_date(s):
  return currency(s.partition('/')[0].rstrip())
def paren_number(s):
  if s[0] != '(' or s[-1] != ')':
    raise Exception("Expected parentheses: [" + s + "]")
  return number(s[1:-1])
def paren_currency(s):
  if s[0] != '(' or s[-1] != ')':
    raise Exception("Expected parentheses: [" + s + "]")
  return currency(s[1:-1])
def tax(s):
  # 1.4500 % $377.95
  p = s.partition(' % ')
  return (float(p[0]), currency(p[2]))


fields = (
'Release Detail Report',
'Total Release Cost Calculation',
'Summary for Release',
('Quantity Released: ', number, 'shares'),  # 30.0000
('Total Release Cost Detailed Below: ', currency, 'taxes'), # $6,629.30
('Quantity Withheld to Pay for Release: ', number, 'shares_withheld'), # 13.0000
('**Excess Amount: ', currency, 'excess'), # $339.87
('Net Quantity: ', number, 'shares_net'), # 17.000000
'Transaction Detail',
('Security Name: ', text, 'name'), # GOOGLE INC CL C
('Trading Symbol: ', text, 'ticker'), # GOOG
('Plan Name / Plan Number: ', text, 'plan'), # 2012 Stock Option Plan / C2012
('Award Date: ', date, 'award_date'), # 02-Jul-2014
'Award Type: Restricted Stock Units',
('Award ID: ', text, 'award_id'), # C148136
'Award Price: $0.0000',
('Release Date: ', date, 'date'), # 25-Feb-2015
('*FMV @ Vest / FMV Date: ', price_date, 'price'), # $536.0900 / 25-Feb-2015
'Additional Information — Please retain this confirmation for your tax'
' records',
'Total Aggregate Award Price: $0.00',
('Total Tax Amount: ', currency, 'taxes'), #  $6,629.30
('Total Release Cost: ', paren_currency, 'taxes'),  #  ($6,629.30)
('Primary Payment Method: WTC ', currency, 'withheld_total'), # $6,969.17
('**Excess Amount: ', currency, 'excess'), # $339.87
'*Fair Market Value (FMV) is calculated according to the Company\'s Plan.',
'**This Excess Amount will be paid to you via your Company payroll in'
' accordance with your Company\'s instructions',
('Quantity Released: ', number, 'shares'), #  30.0000
('Quantity Withheld: ', paren_number, 'shares_withheld'), #  (13.0000)
('Net Quantity: ', number, 'shares_net'), # 17.0000
('Total Gain (FMV x Quantity Released): ', currency, 'gross'), # $16,082.70
'Aggregate Award Price: $0.00',
('Taxable Compensation: ', currency, 'gross'), # $16,082.70
('Withheld Quantity: ', number, 'shares_withheld'), # 13.0000
'x Withheld Quantity Value Per',
('Share: ', currency, 'price'), # $536.09
('Withheld Quantity Value: ', currency, 'withheld_total'), # $6,969.17
'Tax Information',
'Tax % Tax Paid',
('Federal Tax ', tax, 'tax_fed_p'), # $4,020.68
('Medicare Tax ', tax, 'tax_med_p'), # 1.4500 % $377.95
('State Tax 9.6200 % ', currency, 'tax_nys'), # $1,547.16
('Local1 Tax 4.2500 % ', currency, 'tax_nyc')) # $683.51

rec = {}
i = 0
for line in sys.stdin:
  line = line.rstrip()
  if i < len(fields):
    f = fields[i]
    if isinstance(f, str):
      if line != f:
        raise Exception("line %i expected [%s], found [%s]" % (i, f, line))
    else:
      prefix = f[0]
      if not line.startswith(prefix):
        raise Exception("line %i should start with [%s]: [%s]" %
                        (i, prefix, line))
      new = f[1](line[len(prefix):])
      if f[2] in rec:
        old = rec[f[2]]
        if old != new:
          raise Exception("line %i old value [%s] does not match new [%s]: [%s]"
                          % (i, old, new, line))
      else:
        rec[f[2]] = new
  i += 1

rec['tax_fed'] = rec['tax_fed_p'][1]
rec['tax_med'] = rec['tax_med_p'][1]

# consistency checks
if not (rec['tax_fed_p'][0] in (25, 39.6)):
  raise Exception('unexpected fed tax: %f' % rec['tax_fed_p'][0])
if not (rec['tax_med_p'][0] in (1.45, 1.76, 2.35)):
  raise Exception('unexpected med tax: %f' % rec['tax_med_p'][0])
if (rec['tax_fed'] + rec['tax_med'] + rec['tax_nys'] + rec['tax_nyc'] !=
    rec['taxes']):
  raise Exception('taxes do not add up')
if rec['shares'] != rec['shares_withheld'] + rec['shares_net']:
  raise Exception('shares do not add up')
if rec['taxes'] + rec['excess'] != rec['withheld_total']:
  raise Exception('witholdings do not add up')
if rec['price'] * rec['shares_withheld'] != rec['withheld_total']:
  raise Exception('bad witholding total')
if rec['ticker'] == 'GOOG':
  if rec['name'] != 'GOOGLE INC CL C':
    raise Exception('bad class C')
elif (rec['ticker'] != 'GOOGL' or rec['name'] != 'GOOGLE INC-CL A'):
  raise Exception('bad class A')
if rec['shares'] * rec['price'] != rec['gross']:
  raise Exception('shares*price != gross')

date = rec['date'].strftime('%m/%d/%Y')

gsu = 'gsu.qif'
cash = 'cash.qif'

gsu_new = not os.path.exists(gsu)
cash_new = not os.path.exists(cash)

with open(gsu, 'a') as i:
  with open(cash, 'a') as c:
    if gsu_new:
      i.write('!Account\n')
      i.write('NGoogle GSU\n')
      i.write('TInvst\n')
      i.write('^\n')
      i.write('!Type:Invst\n')

    if cash_new:
      c.write('!Account\n')
      c.write('NGoogle GSU-Cash\n')
      c.write('TCash\n')
      c.write('^\n')
      c.write('!Type:Cash\n')

    i.write('D%s\n' % date)
    i.write('NBuyX\n')
    i.write('L[Google GSU-Cash]\n')
    i.write('YGoogle, Inc.\n')
    i.write('I%s\n' % rec['price'])
    i.write('Q%s\n' % rec['shares'])
    i.write('T%s\n' % rec['gross'])
    i.write('^\n')
    i.write('D%s\n' % date)
    i.write('NSellX\n')
    i.write('L[Google GSU-Cash]\n')
    i.write('YGoogle, Inc.\n')
    i.write('I%s\n' % rec['price'])
    i.write('Q%s\n' % rec['shares_withheld'])
    i.write('T%s\n' % rec['withheld_total'])
    i.write('^\n')

    c.write('D%s\n' % date)
    c.write('NCash\n')
    c.write('PGSU\n')
    c.write('LWages & Salary:Alex Gross Pay\n')
    c.write('T%s\n' % (rec['gross'] - rec['taxes']))
    c.write('SWages & Salary:Alex Gross Pay\n')
    c.write('$%s\n' % rec['gross'])
    c.write('STaxes:Alex Federal Income Tax\n')
    c.write('$-%s\n' % rec['tax_fed'])
    c.write('STaxes:Alex Medicare Tax\n')
    c.write('$-%s\n' % rec['tax_med'])
    c.write('STaxes:Alex NYS Income Tax\n')
    c.write('$-%s\n' % rec['tax_nys'])
    c.write('STaxes:Alex NYC Income Tax\n')
    c.write('$-%s\n' % rec['tax_nyc'])
    c.write('^\n')
