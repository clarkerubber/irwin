import csv

def writeCSV(entries):
  with open('data/classified-moves.csv', 'w') as fh:
    writer = csv.writer(fh, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['engine', 'titled', 'moveNumber', 'rank', 'loss', 'advantage', 'ambiguous', 'timeConsistent', 'bot', 'blur'])
    for entry in entries:
      writer.writerow([
        int(entry['engine']),
        int(entry['titled']),
        entry['moveNumber'],
        entry['rank'] + 1,
        int(100 * entry['loss']),
        int(100 * entry['advantage']),
        int(entry['ambiguous']),
        int(entry['timeConsistent']),
        int(entry['bot']),
        entry['blurs']])