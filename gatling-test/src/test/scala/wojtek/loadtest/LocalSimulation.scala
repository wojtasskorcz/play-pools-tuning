package wojtek.loadtest

import io.gatling.core.Predef._
import io.gatling.http.Predef._
import io.gatling.core.scenario.Simulation
import scala.concurrent.duration._

abstract class LocalSimulation extends Simulation {
  val httpConf = http
    .baseURL("http://localhost:9000")
    .userAgentHeader("Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:16.0) Gecko/20100101 Firefox/16.0")
}

class CpuSimulation extends LocalSimulation {
  val scn = scenario("Parallel requests")
    .exec(http("sole request")
      .get("/testCpu")
      .queryParam("cycles", 1500000)
      .check(status is 200))

  setUp(scn.inject(
    constantUsersPerSec(5) during(30 seconds),
    constantUsersPerSec(60) during(30 seconds),
    constantUsersPerSec(40) during(30 seconds), // ~ max throughput
    constantUsersPerSec(5) during(30 seconds),
    constantUsersPerSec(200) during(5 seconds),
    constantUsersPerSec(5) during(30 seconds)
  ).protocols(httpConf))
}

class WsSimulation extends LocalSimulation {
  val scn = scenario("Parallel requests")
    .exec(http("sole request")
      .get("/testWs")
      .check(status is 200))

  setUp(scn.inject(
    constantUsersPerSec(10) during(30 seconds),
    constantUsersPerSec(20) during(30 seconds),
    constantUsersPerSec(30) during(60 seconds),
    constantUsersPerSec(10) during(30 seconds)
  ).protocols(httpConf))
}