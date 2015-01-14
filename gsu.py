import datetime
import decimal
import sys
import getopt
import os.path

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

header2a = """Summary for Release
Quantity Released:
Total Release Cost Detailed Below:
Quantity Withheld to Pay for Release:
**Excess Amount:
Net Quantity:
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
      raise Exception("H" + str(self._idx) + ": [" + line + "] expected [" +
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
fields2a = (('shares', number), ('taxes', currency),
            ('shares_withheld', number), ('excess', currency),
            ('shares_net', number), (None, ''),
            ('price', currency),
            ('withheld_total', currency), (None, ''),
            ('shares_withheld', number), (None, ''), (None, 'Tax Paid'),
            ('tax_fed', currency), ('tax_med', currency),
            ('tax_nys', currency), ('tax_nyc', currency))
fields2b = (('price', currency),
            ('withheld_total', currency), (None, ''),
            ('shares_withheld', number), (None, ''), (None, 'Tax Paid'),
            ('tax_fed', currency), ('tax_med', currency),
            ('tax_nys', currency), ('tax_nyc', currency), (None, ''),
            ('shares', number), ('taxes', currency),
            ('shares_withheld', number), ('excess', currency),
            ('shares_net', number))

class Capture:
  def __init__(self, rec, fields):
    self._idx = 0
    self._rec = rec
    self._fields = fields

  def next(self, line):
    f = self._fields[self._idx]
    if not f[0]:
      if line != f[1]:
        raise Exception("C" + str(self._idx) + ": [" + line + "] expected [" +
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

alt = None
post_split = True
opts, args = getopt.getopt(sys.argv[1:],"abo")
for opt, arg in opts:
  if opt == '-a': alt = 'a'
  if opt == '-b': alt = 'b'
  if opt == '-o': post_split = False

rec = {}

if not alt:
  seq = (SeekToHeader(header1), SeekPastHeader(header1),
         Capture(rec, fields1),
         SeekToHeader(header2), SeekPastHeader(header2),
         Capture(rec, fields2),
         ConsumeRest())
else:
  seq = (SeekToHeader(header1), SeekPastHeader(header1),
         Capture(rec, fields1),
         SeekToHeader(header2a), SeekPastHeader(header2a),
         Capture(rec, fields2a if alt == 'a' else fields2b),
         ConsumeRest())

idx = 0
curr = None

i = 0
for line in sys.stdin:
  if not curr:
    curr = seq[idx]
    idx += 1
  try:
    if not curr.next(line.rstrip()):
      curr = None
  except:
    print("Line ", i)
    raise
  i += 1
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
if post_split:
  if rec['ticker'] == 'GOOG':
    if rec['name'] != 'GOOGLE INC CL C':
      raise Exception('bad class C')
  elif (rec['ticker'] != 'GOOGL' or rec['name'] != 'GOOGLE INC-CL A'):
    raise Exception('bad class A')
else:
  if rec['ticker'] == 'GOOG':
    if rec['name'] != 'GOOGLE INC-CL A':
      raise Exception('bad presplit class A')
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
