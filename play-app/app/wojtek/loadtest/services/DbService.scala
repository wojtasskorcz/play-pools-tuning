package wojtek.loadtest.services

import java.sql.{Connection, DriverManager}

object DbService {

  def openConnection(): Connection = {
    DriverManager.getConnection("jdbc:h2:tcp://localhost/~/metrics", "sa", "")
  }

}
