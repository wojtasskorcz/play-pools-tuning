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
    fieldNames = ['end_time', 'utilization_percent', 'thread_median_ms', 'thread_p90_ms', 'thread_max_ms', 
      'pool_median_ms', 'pool_p90_ms', 'pool_max_ms', 'waiting_median_percent', 'waiting_p90_percent',
      'waiting_max_percent', 'response_median_ms', 'response_p90_ms', 'response_max_ms']
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

  while True:
    # query preparation
    now = datetime.now()
    endTimeDelta = timedelta(seconds = now.second % INTERVAL_SEC + INTERVAL_SEC, microseconds = now.microsecond)
    # endTime = datetime(now.year, now.month, now.day, now.hour, now.minute, now.second - now.second % INTERVAL_SEC, 0)
    endTime = now - endTimeDelta
    startTime = endTime - delta

    # It's possible that the while-loop will execute multiple times for one measurement period
    # (after the handler execution). Therefore we check if this is a new measurement period.
    if str(endTime) not in results:

      print(str(now) + ' measured interval: ' + str(startTime) + ' ' + str(endTime))

      # thread utilization
      curs.execute("SELECT finished_at, thread_micro, pool_micro FROM threads where finished_at >= '" + str(startTime) + "' ORDER BY finished_at asc")
      totalDurationMicro = 0
      threadDurations = []
      poolDurations = []
      for value in curs.fetchall():
        finishedAt = parseDatetime(value[0])
        threadMicro = value[1]
        poolMicro = value[2]
        # print(str(finishedAt) + ' ' + str(threadMicro) + ' ' + str(poolMicro))

        if (threadMicro > INTERVAL_SEC * 1000000):
          print "Thread execution time greater than metrics collection interval. Utilization metrics are inaccurate. Exiting."
          sys.exit(1)


        startedAt = finishedAt - timedelta(microseconds = threadMicro)
        if (startedAt < endTime):
          capDelta = min(finishedAt - startTime, endTime - startedAt)
          capMicro = capDelta.seconds * 1000000 +  capDelta.microseconds
          finalDurationMicro = min(threadMicro, capMicro) if startedAt < endTime else 0
          totalDurationMicro += finalDurationMicro
          # print(str(finishedAt) + ' ' + str(threadMicro) + ' ' + str(finalDurationMicro))

        # enqueuedAt = finishedAt - timedelta(microseconds = poolMicro)
        if (finishedAt < endTime):
          threadDurations.append(threadMicro)
          poolDurations.append(poolMicro)
          # print(str(finishedAt) + ' ' + str(poolMicro))

      utilizationPercent = totalDurationMicro / INTERVAL_SEC / 10000
      threadMedian = numpy.median(threadDurations) if len(threadDurations) > 0 else 0
      threadP90 = numpy.percentile(threadDurations, 90) if len(threadDurations) > 0 else 0
      threadMax = max(threadDurations) if len(threadDurations) > 0 else 0
      poolMedian = numpy.median(poolDurations) if len(poolDurations) > 0 else 0
      poolP90 = numpy.percentile(poolDurations, 90) if len(poolDurations) > 0 else 0
      poolMax = max(poolDurations) if len(poolDurations) > 0 else 0

      waitingRatios = map(
        lambda pair: (pair[1] - pair[0]) * 100 / pair[1],
        zip(threadDurations, poolDurations))
      waitingMedian = numpy.median(waitingRatios) if len(waitingRatios) > 0 else 0
      waitingP90 = numpy.percentile(waitingRatios, 90) if len(waitingRatios) > 0 else 0
      waitingMax = max(waitingRatios) if len(waitingRatios) > 0 else 0


      # response times
      curs.execute("SELECT finished_at, duration_micro FROM requests where finished_at >= '" + str(startTime) + "' ORDER BY finished_at asc")
      responseDurations = []
      for value in curs.fetchall():
        finishedAt = parseDatetime(value[0])
        durationMicro = value[1]
        if (finishedAt < endTime):
          responseDurations.append(durationMicro)
          # print(str(finishedAt) + ' ' + str(durationMicro))

      responseMedian = numpy.median(responseDurations) if len(responseDurations) > 0 else 0
      responseP90 = numpy.percentile(responseDurations, 90) if len(responseDurations) > 0 else 0
      responseMax = max(responseDurations) if len(responseDurations) > 0 else 0
      
      print(str(utilizationPercent) + '%')
      print("thread median: " + str(threadMedian / 1000) + "ms")
      print("thread p90: " + str(threadP90 / 1000) + "ms")
      print("thread max: " + str(threadMax / 1000) + "ms")
      print("pool median: " + str(poolMedian / 1000) + "ms")
      print("pool p90: " + str(poolP90 / 1000) + "ms")
      print("pool max: " + str(poolMax / 1000) + "ms")
      print("waiting median: " + str(waitingMedian) + "%")
      print("waiting p90: " + str(waitingP90) + "%")
      print("waiting max: " + str(waitingMax) + "%")
      print("response median: " + str(responseMedian / 1000) + "ms")
      print("response p90: " + str(responseP90 / 1000) + "ms")
      print("response max: " + str(responseMax / 1000) + "ms")


      if len(results) == HISTORY_LENGTH:
        results.popitem(last = False)

      results[str(endTime)] = {
        'end_time': str(endTime),
        'utilization_percent': utilizationPercent,
        'thread_median_ms': threadMedian / 1000,
        'thread_p90_ms': threadP90 / 1000,
        'thread_max_ms': threadMax / 1000,
        'pool_median_ms': poolMedian / 1000,
        'pool_p90_ms': poolP90 / 1000,
        'pool_max_ms': poolMax / 1000,
        'waiting_median_percent': waitingMedian,
        'waiting_p90_percent': waitingP90,
        'waiting_max_percent': waitingMax,
        'response_median_ms': responseMedian / 1000,
        'response_p90_ms': responseP90 / 1000,
        'response_max_ms': responseMax / 1000
      }

      # print results

      print
    
    time.sleep(INTERVAL_SEC)


finally:
  if curs is not None:
    curs.close()
  if conn is not None:
    conn.close()
