#!/usr/bin/env python2

import jaydebeapi
import time
from datetime import datetime, timedelta

INTERVAL_SEC = 5

delta = timedelta(seconds = INTERVAL_SEC)

conn = jaydebeapi.connect("org.h2.Driver", "jdbc:h2:tcp://localhost/~/metrics", ["sa", ""], "h2-1.4.196.jar")

try:
  curs = conn.cursor()
  print('successfully connected')

  while True:
    now = datetime.now()
    endTime = datetime(now.year, now.month, now.day, now.hour, now.minute, now.second - now.second % 5, 0)
    startTime = endTime - delta
    print(str(startTime) + ' ' + str(endTime))

    curs.execute("SELECT finished_at, duration_micro FROM threads where finished_at >= '" + str(startTime) + "' ORDER BY finished_at asc LIMIT 10")
    for value in curs.fetchall():
      finishedAt = datetime.strptime(value[0], '%Y-%m-%d %H:%M:%S.%f')
      durationMicro = value[1]
      startedAt = finishedAt - timedelta(microseconds = durationMicro)
      capDelta = min(finishedAt - startTime, endTime - startedAt)
      capMicro = capDelta.seconds * 1000000 +  capDelta.microseconds
      finalDurationMicro = min(durationMicro, capMicro) if startedAt < endTime else 0
      print(str(finishedAt) + ' ' + str(durationMicro) + ' ' + str(finalDurationMicro))

    print()
    time.sleep(5)


finally:
  if curs is not None:
    curs.close()
  if conn is not None:
    conn.close()
