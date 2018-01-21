package com.eyeem

import com.eyeem.controllers.ThumbnailController
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
    new MyComponents(context).application
  }

}

class MyComponents(context: Context) extends BuiltInComponentsFromContext(context)
  with HttpFiltersComponents with AhcWSComponents {
  lazy val thumbnailController = new ThumbnailController(controllerComponents, wsClient)
  lazy val router = new Routes(httpErrorHandler, thumbnailController)
}