package wojtek.loadtest

import java.util.concurrent._

import akka.dispatch._
import com.typesafe.config.Config

import scala.concurrent.duration.Duration

class InstrumentedThreadPoolExecutorConfigurator(config: Config, prerequisites: DispatcherPrerequisites) extends ExecutorServiceConfigurator(config, prerequisites) {

  val instrumentedThreadPoolConfig: InstrumentedThreadPoolConfig = createInstrumentedThreadPoolConfigBuilder(config, prerequisites).config

  protected def createInstrumentedThreadPoolConfigBuilder(outerConfig: Config, prerequisites: DispatcherPrerequisites): InstrumentedThreadPoolConfigBuilder = {
    val config = outerConfig.getConfig("thread-pool-executor")
    val builder =
      InstrumentedThreadPoolConfigBuilder(InstrumentedThreadPoolConfig())
        .setKeepAliveTime(Duration(config.getDuration("keep-alive-time", TimeUnit.MILLISECONDS), TimeUnit.MILLISECONDS))
        .setAllowCoreThreadTimeout(config getBoolean "allow-core-timeout")
        .configure(
          Some(config getInt "task-queue-size") flatMap {
            case size if size > 0 ⇒
              Some(config getString "task-queue-type") map {
                case "array"       ⇒ ThreadPoolConfig.arrayBlockingQueue(size, false)
                case "" | "linked" ⇒ ThreadPoolConfig.linkedBlockingQueue(size)
                case x             ⇒ throw new IllegalArgumentException("[%s] is not a valid task-queue-type [array|linked]!" format x)
              } map { qf ⇒ (q: InstrumentedThreadPoolConfigBuilder) ⇒ q.setQueueFactory(qf) }
            case _ ⇒ None
          })

    if (config.getString("fixed-pool-size") == "off")
      builder
        .setCorePoolSizeFromFactor(config getInt "core-pool-size-min", config getDouble "core-pool-size-factor", config getInt "core-pool-size-max")
        .setMaxPoolSizeFromFactor(config getInt "max-pool-size-min", config getDouble "max-pool-size-factor", config getInt "max-pool-size-max")
    else
      builder.setFixedPoolSize(config.getInt("fixed-pool-size"))
  }

  def createExecutorServiceFactory(id: String, threadFactory: ThreadFactory): ExecutorServiceFactory =
    instrumentedThreadPoolConfig.createExecutorServiceFactory(id, threadFactory)
}



final case class InstrumentedThreadPoolConfigBuilder(config: InstrumentedThreadPoolConfig) {
  import ThreadPoolConfig._

  def withNewThreadPoolWithCustomBlockingQueue(newQueueFactory: QueueFactory): InstrumentedThreadPoolConfigBuilder =
    this.copy(config = config.copy(queueFactory = newQueueFactory))

  def withNewThreadPoolWithCustomBlockingQueue(queue: BlockingQueue[Runnable]): InstrumentedThreadPoolConfigBuilder =
    withNewThreadPoolWithCustomBlockingQueue(reusableQueue(queue))

  def withNewThreadPoolWithLinkedBlockingQueueWithUnboundedCapacity: InstrumentedThreadPoolConfigBuilder =
    this.copy(config = config.copy(queueFactory = linkedBlockingQueue()))

  def withNewThreadPoolWithLinkedBlockingQueueWithCapacity(capacity: Int): InstrumentedThreadPoolConfigBuilder =
    this.copy(config = config.copy(queueFactory = linkedBlockingQueue(capacity)))

  def withNewThreadPoolWithSynchronousQueueWithFairness(fair: Boolean): InstrumentedThreadPoolConfigBuilder =
    this.copy(config = config.copy(queueFactory = synchronousQueue(fair)))

  def withNewThreadPoolWithArrayBlockingQueueWithCapacityAndFairness(capacity: Int, fair: Boolean): InstrumentedThreadPoolConfigBuilder =
    this.copy(config = config.copy(queueFactory = arrayBlockingQueue(capacity, fair)))

  def setFixedPoolSize(size: Int): InstrumentedThreadPoolConfigBuilder =
    this.copy(config = config.copy(corePoolSize = size, maxPoolSize = size))

  def setCorePoolSize(size: Int): InstrumentedThreadPoolConfigBuilder =
    this.copy(config = config.copy(corePoolSize = size, maxPoolSize = math.max(size, config.maxPoolSize)))

  def setMaxPoolSize(size: Int): InstrumentedThreadPoolConfigBuilder =
    this.copy(config = config.copy(maxPoolSize = math.max(size, config.corePoolSize)))

  def setCorePoolSizeFromFactor(min: Int, multiplier: Double, max: Int): InstrumentedThreadPoolConfigBuilder =
    setCorePoolSize(scaledPoolSize(min, multiplier, max))

  def setMaxPoolSizeFromFactor(min: Int, multiplier: Double, max: Int): InstrumentedThreadPoolConfigBuilder =
    setMaxPoolSize(scaledPoolSize(min, multiplier, max))

  def setKeepAliveTimeInMillis(time: Long): InstrumentedThreadPoolConfigBuilder =
    setKeepAliveTime(Duration(time, TimeUnit.MILLISECONDS))

  def setKeepAliveTime(time: Duration): InstrumentedThreadPoolConfigBuilder =
    this.copy(config = config.copy(threadTimeout = time))

  def setAllowCoreThreadTimeout(allow: Boolean): InstrumentedThreadPoolConfigBuilder =
    this.copy(config = config.copy(allowCorePoolTimeout = allow))

  def setQueueFactory(newQueueFactory: QueueFactory): InstrumentedThreadPoolConfigBuilder =
    this.copy(config = config.copy(queueFactory = newQueueFactory))

  def configure(fs: Option[Function[InstrumentedThreadPoolConfigBuilder, InstrumentedThreadPoolConfigBuilder]]*): InstrumentedThreadPoolConfigBuilder =
    fs.foldLeft(this)((c, f) ⇒ f.map(_(c)).getOrElse(c))
}



final case class InstrumentedThreadPoolConfig(
                                   allowCorePoolTimeout: Boolean                       = ThreadPoolConfig.defaultAllowCoreThreadTimeout,
                                   corePoolSize:         Int                           = ThreadPoolConfig.defaultCorePoolSize,
                                   maxPoolSize:          Int                           = ThreadPoolConfig.defaultMaxPoolSize,
                                   threadTimeout:        Duration                      = ThreadPoolConfig.defaultTimeout,
                                   queueFactory:         ThreadPoolConfig.QueueFactory = ThreadPoolConfig.linkedBlockingQueue(),
                                   rejectionPolicy:      RejectedExecutionHandler      = ThreadPoolConfig.defaultRejectionPolicy)
  extends ExecutorServiceFactoryProvider {

  class InstrumentedThreadPoolExecutorServiceFactory(val threadFactory: ThreadFactory) extends ExecutorServiceFactory {
    def createExecutorService: ExecutorService = {
      val service: InstrumentedThreadPoolExecutor = new InstrumentedThreadPoolExecutor(
        corePoolSize,
        maxPoolSize,
        threadTimeout.length,
        threadTimeout.unit,
        queueFactory(),
        threadFactory,
        rejectionPolicy) {
        def atFullThrottle(): Boolean = this.getActiveCount >= this.getPoolSize
      }
      service.allowCoreThreadTimeOut(allowCorePoolTimeout)
      service
    }
  }

  final def createExecutorServiceFactory(id: String, threadFactory: ThreadFactory): ExecutorServiceFactory = {
    val tf = threadFactory match {
      case m: MonitorableThreadFactory ⇒
        // add the dispatcher id to the thread names
        m.withName(m.name + "-" + id)
      case other ⇒ other
    }
    new InstrumentedThreadPoolExecutorServiceFactory(tf)
  }

}
