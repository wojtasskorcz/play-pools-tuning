#!/usr/bin/env python2

import jaydebeapi
import numpy
import time
from datetime import datetime, timedelta

INTERVAL_SEC = 5

delta = timedelta(seconds = INTERVAL_SEC)

conn = jaydebeapi.connect("org.h2.Driver", "jdbc:h2:tcp://localhost/~/metrics", ["sa", ""], "h2-1.4.196.jar")

try:
  curs = conn.cursor()
  print('successfully connected')

  while True:
    # query preparation
    now = datetime.now()
    endTime = datetime(now.year, now.month, now.day, now.hour, now.minute, now.second - now.second % 5, 0)
    startTime = endTime - delta
    print(str(startTime) + ' ' + str(endTime))


    # thread utilization
    print("thread utilization")
    curs.execute("SELECT finished_at, duration_micro FROM threads where finished_at >= '" + str(startTime) + "' ORDER BY finished_at asc")
    totalDurationMicro = 0
    for value in curs.fetchall():
      finishedAt = datetime.strptime(value[0], '%Y-%m-%d %H:%M:%S.%f')
      durationMicro = value[1]
      startedAt = finishedAt - timedelta(microseconds = durationMicro)
      if (startedAt > endTime):
        # print("skipping: " + str(finishedAt) + ' ' + str(durationMicro))
        continue

      capDelta = min(finishedAt - startTime, endTime - startedAt)
      capMicro = capDelta.seconds * 1000000 +  capDelta.microseconds
      finalDurationMicro = min(durationMicro, capMicro) if startedAt < endTime else 0
      totalDurationMicro += finalDurationMicro
      print(str(finishedAt) + ' ' + str(durationMicro) + ' ' + str(finalDurationMicro))

    utilizationPercent = totalDurationMicro / INTERVAL_SEC /10000
    print(str(utilizationPercent) + '%')


    # response times
    print("response times")
    curs.execute("SELECT finished_at, duration_micro FROM requests where finished_at >= '" + str(startTime) + "' ORDER BY finished_at asc")
    durations = []
    for value in curs.fetchall():
      finishedAt = datetime.strptime(value[0], '%Y-%m-%d %H:%M:%S.%f')
      durationMicro = value[1]
      if (finishedAt > endTime):
        # print("skipping: " + str(finishedAt) + ' ' + str(durationMicro))
        continue

      durations.append(durationMicro)
      print(str(finishedAt) + ' ' + str(durationMicro))

    median = numpy.median(durations) if len(durations) > 0 else 0
    p90 = numpy.percentile(durations, 90) if len(durations) > 0 else 0
    print("median: " + str(median) + "us")
    print("p90: " + str(p90) + "us")


    print()
    time.sleep(5)


finally:
  if curs is not None:
    curs.close()
  if conn is not None:
    conn.close()
