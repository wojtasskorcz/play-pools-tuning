package wojtek.loadtest

import java.sql.{Connection, SQLException, Timestamp}
import java.util.concurrent._

import com.typesafe.scalalogging.LazyLogging
import wojtek.loadtest.services.DbService

class InstrumentedThreadPoolExecutor(corePoolSize: Int, maximumPoolSize: Int, keepAliveTime: Long, unit: TimeUnit,
                                     workQueue: BlockingQueue[Runnable], threadFactory: ThreadFactory,
                                     handler: RejectedExecutionHandler)
  extends ThreadPoolExecutor(corePoolSize, maximumPoolSize, keepAliveTime, unit, workQueue, threadFactory, handler)
    with LazyLogging {

  private val startTime = new ThreadLocal[Long]
  private val requestTime = new java.util.concurrent.ConcurrentHashMap[Runnable, Long]()
  private val connection = new ThreadLocal[Connection]

  override def execute(command: Runnable) = {
    requestTime.put(command, System.nanoTime())
    super.execute(command)
  }

  override def beforeExecute(t: Thread, r: Runnable) = {
    startTime.set(System.nanoTime())
    super.beforeExecute(t, r)
  }

  override def afterExecute(r: Runnable, t: Throwable): Unit = {
    super.afterExecute(r, t)
    val nowNano = System.nanoTime()
    val nowMillis = System.currentTimeMillis()
    val threadTimeMicro = (nowNano - startTime.get()) / 1000
    val poolTimeMicro = (nowNano - requestTime.remove(r)) / 1000
    val finishedAt = new Timestamp(nowMillis)

    try {
      if (connection.get == null) {
        val conn = DbService.openConnection()
        connection.set(conn)
      }
      connection.get.prepareStatement(s"insert into threads (finished_at, thread_micro, pool_micro) " +
        s"values ('$finishedAt', $threadTimeMicro, $poolTimeMicro)").execute()
    } catch {
      case e: SQLException => logger.error("Exception when saving measurement data. This data will be omitted.", e)
    }

//    logger.info(nowMillis + " thread execution took " + threadTimeMicro + "us")
//    logger.info(nowMillis + " total pool time took " + poolTimeMicro + "us")
  }
}
