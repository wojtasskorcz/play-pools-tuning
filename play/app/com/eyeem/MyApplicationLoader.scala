package com.eyeem

import java.sql.DriverManager

import com.eyeem.controllers.ThumbnailController
import com.eyeem.filters.MetricsFilter
import org.h2.tools.Server
import play.api.ApplicationLoader.Context
import play.api.libs.ws.ahc.AhcWSComponents
import play.api.{ApplicationLoader, BuiltInComponentsFromContext, LoggerConfigurator}
import play.filters.HttpFiltersComponents
import router.Routes

class MyApplicationLoader extends ApplicationLoader {

  def load(context: Context) = {
    LoggerConfigurator(context.environment.classLoader).foreach {
      _.configure(context.environment, context.initialConfiguration, Map.empty)
    }

    val server = Server.createTcpServer("-tcpAllowOthers").start()
    Class.forName("org.h2.Driver")
    val conn = DriverManager.getConnection("jdbc:h2:tcp://localhost/~/metrics", "sa", "")
    conn.prepareStatement("drop all objects").execute()
    conn.prepareStatement("create table threads (id int not null auto_increment, finished_at timestamp, thread_micro int, pool_micro int, primary key (id));").execute()
    conn.prepareStatement("create table requests (id int not null auto_increment, finished_at timestamp, duration_micro int, primary key (id));").execute()

    new MyComponents(context).application
  }

}

class MyComponents(context: Context) extends BuiltInComponentsFromContext(context)
  with HttpFiltersComponents with AhcWSComponents {
  lazy val thumbnailController = new ThumbnailController(controllerComponents, wsClient, actorSystem)
  lazy val metricsFilter = new MetricsFilter()

  override lazy val router = new Routes(httpErrorHandler, thumbnailController)
  override lazy val httpFilters = super.httpFilters :+ metricsFilter
}