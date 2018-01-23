package wojtek.loadtest

import io.gatling.core.Predef._
import io.gatling.http.Predef._
import io.gatling.core.scenario.Simulation
import scala.concurrent.duration._

abstract class WsSimulation extends Simulation {
  def baseUrl: String

  val httpConf = http
    .baseURL(baseUrl)
    .userAgentHeader("Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:16.0) Gecko/20100101 Firefox/16.0")

  val scn = scenario("Parallel requests")
    .exec(http("sole request")
      .get("/test")
      .check(status is 200))

  setUp(scn.inject(constantUsersPerSec(3) during(20 seconds)).protocols(httpConf))
}

class SingleThreadedSyncSimulation extends WsSimulation {
  override def baseUrl = "http://localhost:9000"
}

class MultiThreadedSyncSimulation extends WsSimulation {
  override def baseUrl = "http://localhost:9001"
}

class AsyncSimulation extends Simulation {
  val httpConf = http
    .baseURL("http://localhost:9000")
    .userAgentHeader("Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:16.0) Gecko/20100101 Firefox/16.0")

  val scn = scenario("Parallel requests")
    .exec(http("sole request")
      .get("/relay")
      .check(status is 200))

  setUp(scn.inject(constantUsersPerSec(8) during(10 seconds)).protocols(httpConf))
}