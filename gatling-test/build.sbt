name := "gatling-test"

version := "1.0"

scalaVersion := "2.12.4"

libraryDependencies += "io.gatling.highcharts" % "gatling-charts-highcharts" % "2.3.0" % "test,it"
libraryDependencies += "io.gatling"            % "gatling-test-framework"    % "2.3.0" % "test,it"

enablePlugins(GatlingPlugin)
