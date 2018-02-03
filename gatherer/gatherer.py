#!/usr/bin/env python2

import jaydebeapi, numpy
import time, signal, os, csv, sys
from collections import OrderedDict
from datetime import datetime, timedelta


INTERVAL_SEC = 5
HISTORY_LENGTH = 100
CSV_DIR = 'csvs'


def handler(signum, frame):
  fileName = datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S-%f') + '.csv'
  filePath = os.path.join(CSV_DIR, fileName)
  with open(filePath, 'w+') as file:
    fieldNames = ['end_time', 'utilization_percent', 'thread_median_ms', 'thread_p90_ms', 'thread_max_ms', 
      'pool_median_ms', 'pool_p90_ms', 'pool_max_ms', 'waiting_median_percent', 'waiting_p90_percent',
      'waiting_max_percent', 'num_responses', 'response_median_ms', 'response_p90_ms', 'response_max_ms']
    writer = csv.DictWriter(file, fieldNames)
    writer.writeheader()
    for result in results.values():
      writer.writerow(result)
  print 'Results exported to', filePath

def parseDatetime(datetimeStr):
  normalizedStr = datetimeStr if '.' in datetimeStr else datetimeStr + '.0'
  return datetime.strptime(normalizedStr, '%Y-%m-%d %H:%M:%S.%f')

def measureThreads(cursor, intervalStartTime, intervalEndTime):
  cursor.execute("SELECT finished_at, thread_micro, pool_micro FROM threads where finished_at >= '" +
    str(intervalStartTime) + "' ORDER BY finished_at asc")

  totalDurationMicro = 0
  threadDurations = []
  poolDurations = []
  for value in cursor.fetchall():
    finishedAt = parseDatetime(value[0])
    threadMicro = value[1]
    poolMicro = value[2]

    if (threadMicro > INTERVAL_SEC * 1000000):
      print 'Thread execution time greater than metrics collection interval. Utilization metrics are inaccurate. Exiting.'
      sys.exit(1)

    startedAt = finishedAt - timedelta(microseconds = threadMicro)
    if (startedAt < intervalEndTime):
      capDelta = min(finishedAt - intervalStartTime, intervalEndTime - startedAt)
      capMicro = capDelta.seconds * 1000000 +  capDelta.microseconds
      finalDurationMicro = min(threadMicro, capMicro) if startedAt < intervalEndTime else 0
      totalDurationMicro += finalDurationMicro

    if (finishedAt < intervalEndTime):
      threadDurations.append(threadMicro)
      poolDurations.append(poolMicro)

  utilizationPercent = float(totalDurationMicro) / INTERVAL_SEC / 10000
  threadMedian = numpy.median(threadDurations) if len(threadDurations) > 0 else 0
  threadP90 = numpy.percentile(threadDurations, 90) if len(threadDurations) > 0 else 0
  threadMax = max(threadDurations) if len(threadDurations) > 0 else 0
  poolMedian = numpy.median(poolDurations) if len(poolDurations) > 0 else 0
  poolP90 = numpy.percentile(poolDurations, 90) if len(poolDurations) > 0 else 0
  poolMax = max(poolDurations) if len(poolDurations) > 0 else 0

  waitingRatios = [(float(p) - t) / p * 100 for (t, p) in zip(threadDurations, poolDurations)]
  waitingMedian = numpy.median(waitingRatios) if len(waitingRatios) > 0 else 0
  waitingP90 = numpy.percentile(waitingRatios, 90) if len(waitingRatios) > 0 else 0
  waitingMax = max(waitingRatios) if len(waitingRatios) > 0 else 0

  return {
    'utilization_percent': utilizationPercent,
    'thread_median_ms': threadMedian / 1000,
    'thread_p90_ms': threadP90 / 1000,
    'thread_max_ms': threadMax / 1000,
    'pool_median_ms': poolMedian / 1000,
    'pool_p90_ms': poolP90 / 1000,
    'pool_max_ms': poolMax / 1000,
    'waiting_median_percent': waitingMedian,
    'waiting_p90_percent': waitingP90,
    'waiting_max_percent': waitingMax
  }

def measureResponses(cursor, intervalStartTime, intervalEndTime):
  cursor.execute("SELECT finished_at, duration_micro FROM requests where finished_at >= '" +
    str(intervalStartTime) + "' ORDER BY finished_at asc")
  
  responseDurations = []
  for value in cursor.fetchall():
    finishedAt = parseDatetime(value[0])
    durationMicro = value[1]
    if (finishedAt < intervalEndTime):
      responseDurations.append(durationMicro)

  numResponses = len(responseDurations)
  responseMedian = numpy.median(responseDurations) if numResponses > 0 else 0
  responseP90 = numpy.percentile(responseDurations, 90) if numResponses > 0 else 0
  responseMax = max(responseDurations) if numResponses > 0 else 0

  return {
    'num_responses': numResponses,
    'response_median_ms': responseMedian / 1000,
    'response_p90_ms': responseP90 / 1000,
    'response_max_ms': responseMax / 1000
  }

def measure(cursor, intervalStartTime, intervalEndTime):
  threadsResult = measureThreads(cursor, intervalStartTime, intervalEndTime)
  responsesResult = measureResponses(cursor, intervalStartTime, intervalEndTime)
  result = {'end_time': str(intervalEndTime)}
  result.update(threadsResult)
  result.update(responsesResult)
  return result

def printResult(result):
  print 'utilization:', str(result['utilization_percent']) + '%'
  print 'thread median:', str(result['thread_median_ms']) + 'ms'
  print 'thread p90:', str(result['thread_p90_ms']) + 'ms'
  print 'thread max:', str(result['thread_max_ms']) + 'ms'
  print 'pool median:', str(result['pool_median_ms']) + 'ms'
  print 'pool p90:', str(result['pool_p90_ms']) + 'ms'
  print 'pool max:', str(result['pool_max_ms']) + 'ms'
  print 'waiting median:', str(result['waiting_median_percent']) + '%'
  print 'waiting p90:', str(result['waiting_p90_percent']) + '%'
  print 'waiting max:', str(result['waiting_max_percent']) + '%'
  print 'num responses:', result['num_responses']
  print 'response median:', str(result['response_median_ms']) + 'ms'
  print 'response p90:', str(result['response_p90_ms']) + 'ms'
  print 'response max:', str(result['response_max_ms']) + 'ms'
  print


signal.signal(signal.SIGTSTP, handler)
connection = jaydebeapi.connect('org.h2.Driver', 'jdbc:h2:tcp://localhost/~/metrics', ['sa', ''], 'h2-1.4.196.jar')
results = OrderedDict()
delta = timedelta(seconds = INTERVAL_SEC)

try:
  cursor = connection.cursor()

  while True:
    # query preparation
    now = datetime.now()
    intervalEndTimeDelta = timedelta(seconds = now.second % INTERVAL_SEC + INTERVAL_SEC, microseconds = now.microsecond)
    intervalEndTime = now - intervalEndTimeDelta
    intervalStartTime = intervalEndTime - delta

    # It's possible that the while-loop will execute multiple times for one measurement period
    # (after the handler execution). Therefore we check if this is a new measurement period.
    if str(intervalEndTime) not in results:
      print now, 'measured interval:', intervalStartTime, '-', intervalEndTime

      result = measure(cursor, intervalStartTime, intervalEndTime)

      if len(results) == HISTORY_LENGTH:
        results.popitem(last = False)

      results[str(intervalEndTime)] = result

      printResult(result)
    
    time.sleep(INTERVAL_SEC)

finally:
  if cursor is not None:
    cursor.close()
  if connection is not None:
    connection.close()
