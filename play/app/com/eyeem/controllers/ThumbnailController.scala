package com.eyeem.controllers

import akka.actor.ActorSystem
import com.typesafe.scalalogging.LazyLogging
import play.api.libs.ws.WSClient
import play.api.mvc.{BaseController, ControllerComponents}

import scala.concurrent.{ExecutionContext, Future}

class ThumbnailController(val controllerComponents: ControllerComponents, ws: WSClient, actorSystem: ActorSystem)
                         (implicit ec: ExecutionContext) extends BaseController with LazyLogging {

  def test() = Action.async {
    val dbEc = actorSystem.dispatchers.lookup("db-pool")
    
    Future {
      Thread.sleep(500)
    }(dbEc) map { _ =>
      Ok("done")
    }
  }

  def relay() = Action.async {
    val t0 = System.currentTimeMillis()
    val response = ws.url("http://localhost:9001/test").get()

    response.map { r =>
      Thread.sleep(100)
      val t1 = System.currentTimeMillis()
//      logger.info(s"response time ${t1 - t0}ms")
      Ok("relayed: " + r.body)
    }
  }
}