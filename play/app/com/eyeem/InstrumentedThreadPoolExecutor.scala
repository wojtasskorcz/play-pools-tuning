package com.eyeem

import java.sql.{Connection, DriverManager, Timestamp}
import java.util.concurrent._

import com.typesafe.scalalogging.LazyLogging

class InstrumentedThreadPoolExecutor(corePoolSize: Int, maximumPoolSize: Int, keepAliveTime: Long, unit: TimeUnit,
                                     workQueue: BlockingQueue[Runnable], threadFactory: ThreadFactory,
                                     handler: RejectedExecutionHandler)
  extends ThreadPoolExecutor(corePoolSize, maximumPoolSize, keepAliveTime, unit, workQueue, threadFactory, handler)
    with LazyLogging {

  private val startTime = new ThreadLocal[Long]
  private val connection = new ThreadLocal[Connection]
  private val requestTime = new java.util.concurrent.ConcurrentHashMap[Runnable, Long]()

  override def execute(command: Runnable) = {
//    logger.info("execute " + command.hashCode())
    requestTime.put(command, System.nanoTime())
    super.execute(command)
  }

  override def beforeExecute(t: Thread, r: Runnable) = {
//    logger.info("beforeExecute " + r.hashCode())
    startTime.set(System.nanoTime())
    super.beforeExecute(t, r)
  }

  override def afterExecute(r: Runnable, t: Throwable): Unit = {
    super.afterExecute(r, t)
//    logger.info("afterExecute " + r.hashCode())
    val nowNano = System.nanoTime()
    val nowMillis = System.currentTimeMillis()
    val durationMicro = (nowNano - startTime.get()) / 1000
    val poolTimeMicro = (nowNano - requestTime.remove(r)) / 1000
    val finishedAt = new Timestamp(nowMillis)

    if (connection.get == null) {
      val conn = DriverManager.getConnection("jdbc:h2:tcp://localhost/~/metrics", "sa", "")
      connection.set(conn)
    }
    connection.get.prepareStatement(s"insert into threads (finished_at, thread_micro, pool_micro) values ('$finishedAt', $durationMicro, $poolTimeMicro)").execute()

    //    logger.info(nowMillis + " thread execution took " + durationMicro + "us")
//    logger.info(nowMillis + " total pool time took " + poolTimeMicro + "us")
  }
}
