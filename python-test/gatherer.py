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
    curs.execute("SELECT finished_at, thread_micro, pool_micro FROM threads where finished_at >= '" + str(startTime) + "' ORDER BY finished_at asc")
    totalDurationMicro = 0
    poolDurations = []
    waitingRatios = []
    for value in curs.fetchall():
      # handling the rare case when the timestamp doesn't have the microsecond part
      finishedAtRaw = value[0] if '.' in value[0] else value[0] + '.0'
      finishedAt = datetime.strptime(finishedAtRaw, '%Y-%m-%d %H:%M:%S.%f')
      durationMicro = value[1]
      poolMicro = value[2]

      startedAt = finishedAt - timedelta(microseconds = durationMicro)
      if (startedAt < endTime):
        capDelta = min(finishedAt - startTime, endTime - startedAt)
        capMicro = capDelta.seconds * 1000000 +  capDelta.microseconds
        finalDurationMicro = min(durationMicro, capMicro) if startedAt < endTime else 0
        totalDurationMicro += finalDurationMicro
        # print(str(finishedAt) + ' ' + str(durationMicro) + ' ' + str(finalDurationMicro))

      # enqueuedAt = finishedAt - timedelta(microseconds = poolMicro)
      if (finishedAt < endTime):
        poolDurations.append(poolMicro)
        waitingRatios.append((poolMicro - durationMicro) * 100 / poolMicro)
        # print(str(finishedAt) + ' ' + str(poolMicro))

    utilizationPercent = totalDurationMicro / INTERVAL_SEC / 10000
    poolMedian = numpy.median(poolDurations) if len(poolDurations) > 0 else 0
    poolP90 = numpy.percentile(poolDurations, 90) if len(poolDurations) > 0 else 0
    waitingMedian = numpy.median(waitingRatios) if len(waitingRatios) > 0 else 0
    waitingP90 = numpy.percentile(waitingRatios, 90) if len(waitingRatios) > 0 else 0
    print(str(utilizationPercent) + '%')
    print("pool median: " + str(poolMedian) + "us")
    print("pool p90: " + str(poolP90) + "us")
    print("waiting median: " + str(waitingMedian) + "%")
    print("waiting p90: " + str(waitingP90) + "%")



    # response times
    print("response times")
    curs.execute("SELECT finished_at, duration_micro FROM requests where finished_at >= '" + str(startTime) + "' ORDER BY finished_at asc")
    durations = []
    for value in curs.fetchall():
      finishedAt = datetime.strptime(value[0], '%Y-%m-%d %H:%M:%S.%f')
      durationMicro = value[1]
      if (finishedAt < endTime):
        durations.append(durationMicro)
        # print(str(finishedAt) + ' ' + str(durationMicro))

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
