# play-vs-spring

> [...] if you plan to write blocking IO code, or code that could potentially do a lot of CPU intensive work, you need to know exactly which thread pool is bearing that workload, and you need to tune it accordingly

-- [Play Framework documentation](https://www.playframework.com/documentation/2.6.x/ThreadPools)

This project contains an implementation of a few metrics that are helpful in properly configuring thread pools. Configuration of thread pools is a very important topic in Play Framework but [also in other reactive frameworks such as Akka](https://doc.akka.io/docs/akka/2.5.4/scala/dispatchers.html#blocking-needs-careful-management). They are very often used to provide a layer over blocking calls (e.g. JDBC) or CPU-intensive code in order to keep the rest of the application responsive.

### Prerequisites

Running the Play application and Gatling tests requires [sbt](http://www.scala-sbt.org) and Java 8 JDK. Sbt will download all other necessary dependencies (including Scala itself).

The metrics collection script requires Python 2.7 along with the [JayDeBeApi](https://pypi.python.org/pypi/JayDeBeApi/) and [numpy](https://pypi.python.org/pypi/numpy) libraries.

### Configuring the test setup

To configure the tested thread pool settings change the `fixed-pool-size` property in `<path_to_play>/conf/application.conf`.

You may want to tune the following variables in the metrics gathering script in `<path_to_script>`:
  * `INTERVAL_SEC` - in what intervals should the metrics be gathered
  * `HISTORY_LENGTH` - how many intervals are kept by the script in history in order to later export them to CSV
  * `CSV_DIR` - where to store the generated CSVs

Gatling scenarios can be adjusted in `<path_to_gatling>/wojtek/loadtest/LocalSimulation.scala`.

### Running the test

1. Start the Play application from `<path_to_play>` by running `sbt run`.
2. Start the metrics gathering script from `<path_to_script>` simply using `./gatherer.py`.
3. Start the Gatling simulation from `<path_to_gatling>` by running `sbt 'gatling:testOnly *CpuSimulation'` or `sbt 'gatling:testOnly *WsSimulation'`

You can observe the gathered metrics in the standard output from the gatherer script. In order to export the metrics to CSV press <kbd>CTRL</kbd> + <kbd>Z</kbd>. The script and the other applications can be shut down using <kbd>CTRL</kbd> + <kbd>C</kbd>.

### Test results


