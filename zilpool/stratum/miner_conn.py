class Connections:
   __instance = None

   @staticmethod 
   def getInstance():
      """ Static access method. """
      if Connections.__instance == None:
         Connections()
      return Connections.__instance

   def __init__(self):
      """ Virtually private constructor. """
      if Connections.__instance != None:
         raise Exception("This class is a singleton!")
      else:
         Connections.__instance = self
      self._connections = []

   def add(self, conn):
      self._connections.append(conn)

   def remove(self, conn):
      self._connections.remove(conn)