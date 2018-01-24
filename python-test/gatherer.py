#!/usr/bin/env python2
print 'a'
import jaydebeapi

conn = jaydebeapi.connect("org.h2.Driver", "jdbc:h2:tcp://localhost/~/metrics", ["sa", ""], "h2-1.4.196.jar",)

try:
  curs = conn.cursor()
  print('successfully connected')
  # Fetch the last 10 timestamps
  curs.execute("SELECT duration FROM threads ORDER BY id DESC LIMIT 10")
  for value in curs.fetchall():
    # the values are returned as wrapped java.lang.Long instances
    # invoke the toString() method to print them
    print(value[0].toString())

finally:
  if curs is not None:
    curs.close()
  if conn is not None:
    conn.close()
