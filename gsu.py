import sys

header = """Summary for Release
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

CUSIP:  38259P508




""".split('\n')

class SeekToHeader:
  def next(self, line):
    return line != header[0]

class SeekPastHeader:
  def __init__(self):
    self.idx = 0

  def next(self, line):
    if line != header[self.idx]:
      raise Exception(line)
    self.idx += 1
    return self.idx < header.size

class Print5:
  def __init__(self):
    self.idx = 0

  def next(self, line):
    print(line)
    self.idx += 1
    return self.idx < 6

class ConsumeRest:
  def next(line):
    print("C: ", line)
    return True

seq = (SeekToHeader, SeekPastHeader, Print5, ConsumeRest)
idx = 0
curr = None

for line in sys.stdin:
  if not curr:
    curr = seq[idx]()
    idx += 1
  if not curr.next(line.rstrip()):
    curr = None
if idx != len(seq):
  raise Exception("short")
print("Done")
