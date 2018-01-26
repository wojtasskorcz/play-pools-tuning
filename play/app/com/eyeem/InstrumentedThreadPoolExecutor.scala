package com.eyeem

import java.sql.{DriverManager, Timestamp}
import java.util.concurrent._

import com.typesafe.scalalogging.LazyLogging

class InstrumentedThreadPoolExecutor(corePoolSize: Int, maximumPoolSize: Int, keepAliveTime: Long, unit: TimeUnit,
                                     workQueue: BlockingQueue[Runnable], threadFactory: ThreadFactory,
                                     handler: RejectedExecutionHandler)
  extends ThreadPoolExecutor(corePoolSize, maximumPoolSize, keepAliveTime, unit, workQueue, threadFactory, handler)
    with LazyLogging {

  private val startTime = new ThreadLocal[Long]

  override def beforeExecute(t: Thread, r: Runnable) = {
    logger.info(System.currentTimeMillis() + " beforeExecute")
    startTime.set(System.nanoTime())
    super.beforeExecute(t, r)
  }

  override def afterExecute(r: Runnable, t: Throwable): Unit = {
    super.afterExecute(r, t)
    val durationMicro = (System.nanoTime() - startTime.get()) / 1000
    val finishedAt = new Timestamp(System.currentTimeMillis())
    val conn = DriverManager.getConnection("jdbc:h2:tcp://localhost/~/metrics", "sa", "")
    conn.prepareStatement(s"insert into threads (finished_at, duration_micro) values ('$finishedAt', $durationMicro)").execute()
    logger.info(System.currentTimeMillis() + " afterExecute took " + durationMicro + "us")
  }

//  override def execute(command: Runnable) = {
//    logger.info("execute")
//    super.execute(command)
//  }
}
