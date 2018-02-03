# play-pools-tuning

> [...] if you plan to write blocking IO code, or code that could potentially do a lot of CPU intensive work, you need to know exactly which thread pool is bearing that workload, and you need to tune it accordingly

-- [Play Framework documentation](https://www.playframework.com/documentation/2.6.x/ThreadPools)

This project contains an implementation of a few metrics that are helpful in properly configuring thread pools. Configuration of thread pools is a very important topic in Play Framework but [also in other reactive frameworks such as Akka](https://doc.akka.io/docs/akka/2.5.4/scala/dispatchers.html#blocking-needs-careful-management). They are very often used to provide a layer over blocking calls (e.g. JDBC) or CPU-intensive code in order to keep the rest of the application responsive.

### Prerequisites

Running the Play application and Gatling tests requires [sbt](http://www.scala-sbt.org) and Java 8 JDK. Sbt will download all other necessary dependencies (including Scala itself).

The metrics collection script requires Python 2.7 along with the [JayDeBeApi](https://pypi.python.org/pypi/JayDeBeApi/) and [numpy](https://pypi.python.org/pypi/numpy) libraries.

### Configuring the test setup

To configure the tested thread pool settings change the `fixed-pool-size` property in `play-app/conf/application.conf`.

You may want to tune the following variables in the metrics gathering script in `gatherer/gatherer.py`:
  * `INTERVAL_SEC` - in what intervals should the metrics be gathered
  * `HISTORY_LENGTH` - how many intervals are kept by the script in history in order to later export them to CSV
  * `CSV_DIR` - where to store the generated CSVs

Gatling scenarios can be adjusted in `gatling-test/src/test/scala/wojtek/loadtest/LocalSimulation.scala`.

### Running a test

1. Start the Play application from `play-app/` by running `sbt run`.
2. Start the metrics gathering script from `gatherer/` by running `./gatherer.py`.
3. Start the Gatling simulation from `gatling-test/` by running `sbt 'gatling:testOnly *CpuSimulation'` or `sbt 'gatling:testOnly *WsSimulation'`

You can observe the gathered metrics in the standard output from the gatherer script. In order to export the metrics to CSV press <kbd>CTRL</kbd> + <kbd>Z</kbd>. The script and the other applications can be shut down using <kbd>CTRL</kbd> + <kbd>C</kbd>.

### Test results

#### First test: CPU-heavy requests

In this test we simulate multiple users requesting a CPU-heavy computation on the server. The exact scenario is defined in [CpuSimulation](https://github.com/wojtasskorcz/play-pools-tuning/blob/master/gatling-test/src/test/scala/wojtek/loadtest/LocalSimulation.scala#L14) but it may need some adjustments on different machines to reproduce the results. The test was performed on a machine with a 6-core AMD Ryzen 5 1600 CPU running 12 threads. Test results may be slightly skewed/inaccurate, as the whole infrastructure (Gatling, H2 database and the script collecting the metrics) was running on the same machine as the application under test. Nevertheless, the influence of those applications should be relatively insignificant.

![](https://github.com/wojtasskorcz/play-pools-tuning/blob/master/results/cpu-response.png)

The first chart shows response times from the service when running the test scenario twice: once on a thread pool with 100 threads (16:58:50 - 17:01:25) and once with 12 threads (17:01:40 - 17:04:15). Metrics were collected every five seconds. The small blips at 16:58:40 and 17:01:35 are single requests sent in order to cause application reload (to change the thread pool settings).

As we can see, and what was to be expected, running on 12 threads is faster than on 100. This is a well-known practice, to configure CPU-bound thread pools to be the size of physical CPUs or slightly larger. Measuring response times helps a bit when configuring thread pools but by its nature it requires us to compare different settings and empirically decide which is better. Let's look at a metric that allows us to predict how to scale the thread pools without such comparisons.

![](https://github.com/wojtasskorcz/play-pools-tuning/blob/master/results/cpu-thread.png)

This chart shows how long the execution of a pool thread took per each request. As we can see, for the 100-thread application, with the increase of the number of requests, their execution time increases around 20-fold. This is a clear sign that the pool threads lack underlying resources (system threads or CPU cores) to proceed and the pool should be shrank. In general, the pool itself should be throttling the number of simultaneously executing threads (forcing tasks to wait for a thread if necessary) in order to ensure that the threads execute in a timely and predictable manner. This desired behavior can be observed in the 12-thread application, where the execution time only doubles under heavy load as the thread forces tasks to wait for threads.

![](https://github.com/wojtasskorcz/play-pools-tuning/blob/master/results/cpu-waiting.png)

As we can see here, under heavy load the more optimized pool forces its tasks to wait relatively longer. The difference between 90% and 98% may not seem very significant, but if we invert the meaning of the chart - how long did thread execution take in relation the the whole time a task was scheduled in a pool - the difference between 10% and 2% is five-fold.

We've shown how the previous metrics can help predict when to scale down a CPU-heavy thread pool. If we want to check if scaling up is needed we can work with a reverse logic. Before, we checked if thread execution time was high (relatively to the baseline) and waiting ratio was low -- it meant that the pool was too big. On the other hand, if execution time stays relatively constant but waiting ratio keeps growin, it may be worth to try a bit bigger pool. In our case We could see if 18- or 24-thread pool would speed things up.

#### Second test: blocking requests

The need for scaling up a thread pool rarely arises in case of CPU-heavy requests (unless we upgrade the underlying hardware). On the other hand, it may well be the case for thread pools designed for handling blocking operations if a downstream web service or database get upgraded and suddenly can handle more load. Let's consider this scenario in the test defined in [WsSimulation](https://github.com/wojtasskorcz/play-pools-tuning/blob/master/gatling-test/src/test/scala/wojtek/loadtest/LocalSimulation.scala#L14).

![](https://github.com/wojtasskorcz/play-pools-tuning/blob/master/results/blocking-response.png)

This time we first test a thread pool of 12 threads ([times]) as an example of bad configuration. Then, we show a thread pool of 100 threads ([times]). Here, when handling a request, we simulate a request to a downstream service that takes 500ms.

As we can see, for blocking operations the difference in response times between the test configurations is much more pronounced. The 100-thread application always responds within 500ms, whereas the 12-thread application takes up to 15s under heavy load. Fortunately, properly configuring a thread pool for blocking operations is relatively easy, because we usually can set the number of threads to the number of connections supported by the downstream database or web service. 


![](https://github.com/wojtasskorcz/play-pools-tuning/blob/master/results/blocking-utilization.png)

Such thread pools also make it quite easy to predict when we'll have to scale. In the chart above we can see that, at first, thread utilization sits at 500% (which can mean, for example, 5 threads being utilized 100% of the time, or 10 threads being utilized 50% of the time). Later it goes up to 1000% and knowing we have a thread pool of 12 threads and expecting a growing traffic, we can predict that soon we'll need to scale the pool up. Such prediction also gives us time to scale up the downstream infrastructure (e.g. start more DB replicas) in order to support the bigger pool.

![](https://github.com/wojtasskorcz/play-pools-tuning/blob/master/results/blocking-waiting.png)

On the other hand, the charts we used previously only start to indicate the need for scaling up post factum. There's no way to tell that the pool is reaching its capacity from the waiting ratio because it only starts to show after the pool is already overloaded. The thread execution time metrics is ever less useful as the thread execution is not limited by the CPU and therefore always takes 500ms and doesn't show any signs of overload.

Of course, in real life even with the pool waiting metrics we'll first have some indications of overload (e.g. occasional waiting ratios over 0% during 10s every minute) but in general the utilization metrics allows for much greater accuracy in our predictions.

### Known issues
- delay in metrics collection in order to correctly compute utilization
- sometimes utilization over its theoretical limits (eg. 1210% on a 12-thread pool)
- no thread pool used in the play app because it's difficult (most likely impossible) to inject it into an custom `ThreadPoolExecutor`
