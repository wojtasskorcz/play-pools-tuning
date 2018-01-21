package com.eyeem.controllers

import com.typesafe.scalalogging.LazyLogging
import play.api.libs.ws.WSClient
import play.api.mvc.{BaseController, ControllerComponents}

import scala.concurrent.ExecutionContext

class ThumbnailController(val controllerComponents: ControllerComponents, ws: WSClient)
                         (implicit ec: ExecutionContext) extends BaseController with LazyLogging {

  def test() = Action {
    Thread.sleep(500)
    Ok("done")
  }

  def relay() = Action.async {
    val response = ws.url("http://localhost:9001/test").get()

    response.map(r => Ok("relayed: " + r.body))
  }
}