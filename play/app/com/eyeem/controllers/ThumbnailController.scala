package com.eyeem.controllers

import akka.actor.ActorSystem
import com.typesafe.scalalogging.LazyLogging
import play.api.mvc.{BaseController, ControllerComponents}

import scala.concurrent.{ExecutionContext, Future}

class ThumbnailController(val controllerComponents: ControllerComponents, actorSystem: ActorSystem)
                         (implicit ec: ExecutionContext) extends BaseController with LazyLogging {

  private val instrumentedEc = actorSystem.dispatchers.lookup("instrumented-pool")

  def testWs() = Action.async {
    Future {
      Thread.sleep(500) // simulate a blocking call to a web service
    }(instrumentedEc) map { _ =>
      Ok("done")
    }
  }

  def testCpu(cycles: Int) = Action.async {
    Future {
      spin(cycles)
    }(instrumentedEc) map { _ =>
      Ok("done")
    }
  }

  def spin(cycles: Int): Unit = {
    val base = 42
    0 to cycles foreach { i =>
      Math.atan(Math.sqrt(Math.pow(base, 10)))
    }
  }
}