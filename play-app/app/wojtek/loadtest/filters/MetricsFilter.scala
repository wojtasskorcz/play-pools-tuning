package wojtek.loadtest.filters

import java.sql.{SQLException, Timestamp}

import akka.stream.Materializer
import com.typesafe.scalalogging.LazyLogging
import play.api.mvc._
import wojtek.loadtest.services.DbService

import scala.concurrent.{ExecutionContext, Future}

class MetricsFilter(implicit val mat: Materializer, implicit val ec: ExecutionContext) extends Filter with LazyLogging {

  private val connection = DbService.openConnection()

  def apply(nextFilter: (RequestHeader) => Future[Result])(rh: RequestHeader): Future[Result] = {
    val requestStartTime = System.nanoTime()
    nextFilter(rh).map(
      result => {
        val durationMicro = (System.nanoTime() - requestStartTime) / 1000
        val finishedAt = new Timestamp(System.currentTimeMillis())

        try {
          connection.prepareStatement(s"insert into requests (finished_at, duration_micro) " +
            s"values ('$finishedAt', $durationMicro)").execute()
        } catch {
          case e: SQLException => logger.error("Exception when saving measurement data. This data will be omitted.", e)
        }

//        logger.info(System.currentTimeMillis() + " request took " + durationMicro + "us")
        result
      }
    )
  }

}
