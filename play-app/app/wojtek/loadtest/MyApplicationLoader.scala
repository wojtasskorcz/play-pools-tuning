package wojtek.loadtest

import wojtek.loadtest.controllers.ThumbnailController
import wojtek.loadtest.filters.MetricsFilter
import org.h2.tools.Server
import play.api.ApplicationLoader.Context
import play.api.{ApplicationLoader, BuiltInComponentsFromContext, LoggerConfigurator}
import play.filters.HttpFiltersComponents
import router.Routes
import wojtek.loadtest.services.DbService

class MyApplicationLoader extends ApplicationLoader {

  def load(context: Context) = {
    LoggerConfigurator(context.environment.classLoader).foreach {
      _.configure(context.environment, context.initialConfiguration, Map.empty)
    }

    Server.createTcpServer("-tcpAllowOthers").start()
    Class.forName("org.h2.Driver")
    val conn = DbService.openConnection()
    conn.prepareStatement("drop all objects").execute()
    conn.prepareStatement("create table threads (id int not null auto_increment, " +
      "finished_at timestamp, thread_micro int, pool_micro int, primary key (id))").execute()
    conn.prepareStatement("create table requests (id int not null auto_increment, " +
      "finished_at timestamp, duration_micro int, primary key (id))").execute()
    conn.close()

    new MyComponents(context).application
  }

}

class MyComponents(context: Context) extends BuiltInComponentsFromContext(context) with HttpFiltersComponents {
  lazy val instrumentedEc = actorSystem.dispatchers.lookup("instrumented-pool")
  lazy val thumbnailController = new ThumbnailController(controllerComponents, instrumentedEc)
  lazy val metricsFilter = new MetricsFilter()

  override lazy val router = new Routes(httpErrorHandler, thumbnailController)
  override lazy val httpFilters = super.httpFilters :+ metricsFilter
}