import datetime
import decimal
import sys

header1 = """  Transaction Detail
Security Name:
Trading Symbol:
Plan Name / Plan Number:
Award Date:
Award Type:
Award ID:
Award Price:
Release Date:
*FMV @ Vest / FMV Date:
Quantity Released:
Quantity Withheld:
Net Quantity:
Total Gain (FMV x Quantity Released):
Aggregate Award Price:
Taxable Compensation:
  Total Release Cost Calculation
Total Aggregate Award Price:
Total Tax Amount:
Total Release Cost:
Primary Payment Method: WTC
**Excess Amount:
*Fair Market Value (FMV) is calculated according to the Company's Plan.
**This Excess Amount will be paid to you via your Company payroll in accordance with your Company's instructions
  Additional Information — Please retain this confirmation for your tax records
""".split('\n')

header2 = """Summary for Release
Quantity Released:
Total Release Cost Detailed Below:
Quantity Withheld to Pay for Release:
**Excess Amount:
Net Quantity:

Federal Tax
Medicare Tax
State Tax
Local1 Tax

Tax %
39.6000 %
2.3500 %
9.6200 %
4.2500 %

© 2014 Morgan Stanley Smith Barney LLC. Member SIPC.
""".split('\n')

class SeekToHeader:
  def __init__(self, hdr):
    self._hdr = hdr
  def next(self, line):
    return line != self._hdr[0]

class SeekPastHeader:
  def __init__(self, hdr):
    self._hdr = hdr
    self._idx = 1

  def next(self, line):
    if line != self._hdr[self._idx]:
      raise Exception(str(self._idx) + ": [" + line + "] expected [" +
                      self._hdr[self._idx] + "]")
    self._idx += 1
    return self._idx < len(self._hdr)

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

fields1 = (('name', text), ('ticker', text), ('plan', text),
           ('award_date', text), (None, 'Restricted Stock Units'),
           ('award_id', text), (None, '$0.0000'), ('date', date),
           ('price', price_date), ('shares', number),
           ('shares_withheld', paren_number),
           ('shares_net', number), ('gross', currency))
fields2 = (('cusip', text), (None, ''), (None, ''), (None, ''), (None, ''),
           ('shares', number), ('taxes', currency),
           ('shares_withheld', number), ('excess', currency),
           ('shares_net', number), (None, ''),
           ('price', currency),
           ('withheld_total', currency), (None, ''),
           ('shares_withheld', number), (None, ''), (None, 'Tax Paid'),
           ('tax_fed', currency), ('tax_med', currency),
           ('tax_nys', currency), ('tax_nyc', currency))

class Capture:
  def __init__(self, rec, fields):
    self._idx = 0
    self._rec = rec
    self._fields = fields

  def next(self, line):
    f = self._fields[self._idx]
    if not f[0]:
      if line != f[1]:
        raise Exception(str(self._idx) + ": [" + line + "] expected [" +
                        f[1] + "]")
    else:
      new = f[1](line)
      if f[0] in self._rec:
        old = self._rec[f[0]]
        if old != new:
          raise Exception("old value [%s] does not match new [%s]" % (old, new))
      else:
        self._rec[f[0]] = new

    self._idx += 1
    return self._idx < len(self._fields)

class ConsumeRest:
  def next(self, line): return True

rec = {}
seq = (SeekToHeader(header1), SeekPastHeader(header1), Capture(rec, fields1),
       SeekToHeader(header2), SeekPastHeader(header2), Capture(rec, fields2),
       ConsumeRest())
idx = 0
curr = None

for line in sys.stdin:
  if not curr:
    curr = seq[idx]
    idx += 1
  if not curr.next(line.rstrip()):
    curr = None
if idx != len(seq):
  raise Exception("short")

# consistency checks
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
  if rec['cusip'] != 'CUSIP:  38259P706' or rec['name'] != 'GOOGLE INC CL C':
    raise Exception('bad class C')
elif (rec['ticker'] != 'GOOGL' or rec['cusip'] != 'CUSIP:  38259P508' or
  rec['name'] != 'GOOGLE INC-CL A'):
    raise Exception('bad class A')
if rec['shares'] * rec['price'] != rec['gross']:
  raise Exception('shares*price != gross')

# print('!Type:Invst')
print('D%s' % rec['date'].strftime('%x'))
print('NBuy')
print('YGoogle, Inc')
print('I%s', rec['price'])
print('Q%s', rec['shares'])
print('T%s', rec['gross'])
print('^')
print('D%s' % rec['date'].strftime('%x'))
print('NSell')
print('YGoogle, Inc')
print('I%s', rec['price'])
print('Q%s', rec['shares_withheld'])
print('T%s', rec['withheld_total'])
print('^')
print('D%s' % rec['date'].strftime('%x'))
print('NCash')
print('PGSU')
print('T%s' % (rec['gross'] - rec['taxes']))
print('SWages & Salary:Alex Gross Pay')
print('$%s' % rec['gross'])
print('STaxes:Alex Federal Income Tax')
print('$-%s' % rec['tax_fed'])
print('STaxes:Alex Medicare Tax')
print('$-%s' % rec['tax_med'])
print('STaxes:Alex NYS Income Tax')
print('$-%s' % rec['tax_nys'])
print('STaxes:Alex NYC Income Tax')
print('$-%s' % rec['tax_nyc'])
print('^')
