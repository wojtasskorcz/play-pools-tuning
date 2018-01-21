# play-vs-spring

Run a single-threaded Play server simply with `run`.

Concurrently, run a multi-threaded Play server using:
```
run -Dconfig.resource=application-multithreaded.conf 9001
```

Test their behavior using Gatling scenarios. For example, the single-threaded server should asynchronously relay received requests to the multi-threaded server in scenario:
```
gatling:testOnly *AsyncSimulation
```
