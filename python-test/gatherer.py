#!/usr/bin/env python2

import jaydebeapi, numpy
import time, signal, os, csv
from collections import OrderedDict
from datetime import datetime, timedelta

INTERVAL_SEC = 5
HISTORY_LENGTH = 999999
CSV_DIR = 'csvs'


def parseDatetime(datetimeStr):
  normalizedStr = datetimeStr if '.' in datetimeStr else datetimeStr + '.0'
  return datetime.strptime(normalizedStr, '%Y-%m-%d %H:%M:%S.%f')

def handler(signum, frame):
  fileName = datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S-%f') + '.csv'
  filePath = os.path.join(CSV_DIR, fileName)
  with open(filePath, 'w+') as file:
    fieldNames = ['end_time', 'utilization_percent', 'thread_median', 'thread_p90', 'response_median', 'response_p90']
    writer = csv.DictWriter(file, fieldNames)
    writer.writeheader()
    for result in results.values():
      writer.writerow(result)
  print 'Results exported to', filePath


delta = timedelta(seconds = INTERVAL_SEC)

signal.signal(signal.SIGTSTP, handler)

results = OrderedDict()

conn = jaydebeapi.connect("org.h2.Driver", "jdbc:h2:tcp://localhost/~/metrics", ["sa", ""], "h2-1.4.196.jar")

try:
  curs = conn.cursor()
  print('successfully connected')

  while True:
    # query preparation
    now = datetime.now()
    endTimeDelta = timedelta(seconds = now.second % INTERVAL_SEC + INTERVAL_SEC, microseconds = now.microsecond)
    # endTime = datetime(now.year, now.month, now.day, now.hour, now.minute, now.second - now.second % INTERVAL_SEC, 0)
    endTime = now - endTimeDelta
    startTime = endTime - delta
    print(str(now) + ' measured interval: ' + str(startTime) + ' ' + str(endTime))


    # thread utilization
    print("thread utilization")
    curs.execute("SELECT finished_at, thread_micro, pool_micro FROM threads where finished_at >= '" + str(startTime) + "' ORDER BY finished_at asc")
    totalDurationMicro = 0
    threadDurations = []
    poolDurations = []
    waitingRatios = []
    for value in curs.fetchall():
      finishedAt = parseDatetime(value[0])
      durationMicro = value[1]
      poolMicro = value[2]
      # print(str(finishedAt) + ' ' + str(durationMicro) + ' ' + str(poolMicro))

      startedAt = finishedAt - timedelta(microseconds = durationMicro)
      if (startedAt < endTime):
        capDelta = min(finishedAt - startTime, endTime - startedAt)
        capMicro = capDelta.seconds * 1000000 +  capDelta.microseconds
        finalDurationMicro = min(durationMicro, capMicro) if startedAt < endTime else 0
        totalDurationMicro += finalDurationMicro
        # print(str(finishedAt) + ' ' + str(durationMicro) + ' ' + str(finalDurationMicro))

      # enqueuedAt = finishedAt - timedelta(microseconds = poolMicro)
      if (finishedAt < endTime):
        threadDurations.append(durationMicro)
        poolDurations.append(poolMicro)
        waitingRatios.append((poolMicro - durationMicro) * 100 / poolMicro)
        # print(str(finishedAt) + ' ' + str(poolMicro))

    utilizationPercent = totalDurationMicro / INTERVAL_SEC / 10000
    threadMedian = numpy.median(threadDurations) if len(threadDurations) > 0 else 0
    threadP90 = numpy.percentile(threadDurations, 90) if len(threadDurations) > 0 else 0
    poolMedian = numpy.median(poolDurations) if len(poolDurations) > 0 else 0
    poolP90 = numpy.percentile(poolDurations, 90) if len(poolDurations) > 0 else 0
    waitingMedian = numpy.median(waitingRatios) if len(waitingRatios) > 0 else 0
    waitingP90 = numpy.percentile(waitingRatios, 90) if len(waitingRatios) > 0 else 0
    print(str(utilizationPercent) + '%')
    print("thread median: " + str(threadMedian) + "us")
    print("thread p90: " + str(threadP90) + "us")
    print("pool median: " + str(poolMedian) + "us")
    print("pool p90: " + str(poolP90) + "us")
    print("waiting median: " + str(waitingMedian) + "%")
    print("waiting p90: " + str(waitingP90) + "%")



    # response times
    print("response times")
    curs.execute("SELECT finished_at, duration_micro FROM requests where finished_at >= '" + str(startTime) + "' ORDER BY finished_at asc")
    durations = []
    for value in curs.fetchall():
      finishedAt = parseDatetime(value[0])
      durationMicro = value[1]
      if (finishedAt < endTime):
        durations.append(durationMicro)
        # print(str(finishedAt) + ' ' + str(durationMicro))

    median = numpy.median(durations) if len(durations) > 0 else 0
    p90 = numpy.percentile(durations, 90) if len(durations) > 0 else 0
    print("median: " + str(median) + "us")
    print("p90: " + str(p90) + "us")

    if str(endTime) not in results:
      if len(results) == HISTORY_LENGTH:
        results.popitem(last = False)
      results[str(endTime)] = {
        'end_time': str(endTime),
        'utilization_percent': utilizationPercent,
        'thread_median': threadMedian,
        'thread_p90': threadP90,
        'response_median': median,
        'response_p90': p90
      }

    print
    time.sleep(5)


finally:
  if curs is not None:
    curs.close()
  if conn is not None:
    conn.close()
