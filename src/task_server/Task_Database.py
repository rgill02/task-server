################################################################################
###                                 Imports                                  ###
################################################################################
#Standard imports
import sqlite3
import argparse

################################################################################
###                           Task Database Class                            ###
################################################################################
class Task_Database:
	"""
	This represents a multi-thread, multi-process interface to the database 
	that keeps track of tasks. It uses sqlite3.
	"""
	############################################################################
	def __init__(self, dbname="tasks.db"):
		"""
		Parameters
		----------
		dbname : str
			Path to sqlite3 database to connect to
		"""
		#Save user args
		self.dbname = dbname

	############################################################################
	def setup_db(self):
		"""
		This sets up all the tables in the database if they aren't already. 
		Only needs to be called once.
		"""
		#Create connection
		conn = sqlite3.connect(self.dbname)
		cursor = conn.cursor()

		#Enforce WAL mode
		cursor.execute("PRAGMA journal_mode=WAL;")

		#Create tasks table
		cursor.execute("""
			CREATE TABLE IF NOT EXISTS tasks (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				name TEXT NOT NULL,
				created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%S', 'NOW')),
				status INTEGER NOT NULL CHECK(status in (0, 1, 2, 3)), --0: waiting, 1: running, 2: error, 3: done
				input_file TEXT NOT NULL,
				output_file TEXT NOT NULL,
				config TEXT NOT NULL,
				task_type INTEGER NOT NULL,	--0: creates a new file with new data, 1: modifies the existing file by adding or modifying auxiliary or metadata
				output TEXT
				) STRICT;
		""")
		cursor.execute("""
			CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
		""")

		#Commit to db
		conn.commit()
		conn.close()

	############################################################################
	def create_new_task(self, name, input_file, output_file, config):
		"""
		Creates a new entry in the tasks table

		Parameters
		----------
		name : str
			Name of the task
		input_file : str
			Full path to input file
		output_file: str
			Full path to output file
		config : str
			JSON serialized dict representing config for the task

		Returns
		-------
		id : int
			Id of new entry in table
		"""
		#Create connection
		conn = sqlite3.connect(self.dbname)
		cursor = conn.cursor()

		#Enforce WAL mode
		cursor.execute("PRAGMA journal_mode=WAL;")

		#Create and execute query
		query = "INSERT INTO tasks (name, created_at, status, input_file, " \
			  + "output_file, config, task_type) VALUES (?, DATETIME('now'), " \
			  + "0, ?, ?, ?, ?)"
		cursor.execute(query, (name, input_file, output_file, config, 
					   input_file == output_file))
		new_task_id = cursor.lastrowid

		#Commit database
		conn.commit()
		conn.close()

		#Return id
		return new_task_id

	############################################################################
	def get_all_tasks(self):
		"""
		Gets all the tasks in the tasks table and groups them by status

		Returns
		-------
		tasks : dict
			Dictionary with 3 keys: running_tasks, errored_tasks, and 
			finished_tasks. Each value is a list of entries
		"""
		#Create connection
		conn = sqlite3.connect(self.dbname)
		cursor = conn.cursor()

		#Enforce WAL mode
		cursor.execute("PRAGMA journal_mode=WAL;")

		print("1")

		#Get all waiting tasks
		tasks = {}
		query = "SELECT * FROM tasks WHERE status = 0"
		cursor.execute(query)
		tasks["waiting_tasks"] = cursor.fetchall()

		print("2")

		#Get all running tasks
		query = "SELECT * FROM tasks WHERE status = 1"
		cursor.execute(query)
		tasks["running_tasks"] = cursor.fetchall()

		print("3")

		#Get all tasks that errored
		query = "SELECT * FROM tasks WHERE status = 2"
		cursor.execute(query)
		tasks["errored_tasks"] = cursor.fetchall()

		print("4")

		#Get all tasks that finished succesfully
		query = "SELECT * FROM tasks WHERE status = 3"
		cursor.execute(query)
		tasks["finished_tasks"] = cursor.fetchall()

		print("5")

		#Close database
		conn.close()

		print("6")

		#Return tasks
		return tasks

	############################################################################
	def get_all_waiting_tasks(self):
		"""
		Gets all the tasks in the tasks table that are waiting

		Returns
		-------
		tasks : list
			List of entries of waiting tasks
		"""
		#Create connection
		conn = sqlite3.connect(self.dbname)
		cursor = conn.cursor()

		#Enforce WAL mode
		cursor.execute("PRAGMA journal_mode=WAL;")

		#Get all waiting tasks
		query = "SELECT * FROM tasks WHERE status = 0"
		cursor.execute(query)
		tasks = cursor.fetchall()

		#Close database
		conn.close()

		#Return tasks
		return tasks

	############################################################################
	def get_all_running_tasks(self):
		"""
		Gets all the tasks in the tasks table that are running

		Returns
		-------
		tasks : list
			List of entries of running tasks
		"""
		#Create connection
		conn = sqlite3.connect(self.dbname)
		cursor = conn.cursor()

		#Enforce WAL mode
		cursor.execute("PRAGMA journal_mode=WAL;")

		#Get all waiting tasks
		query = "SELECT * FROM tasks WHERE status = 1"
		cursor.execute(query)
		tasks = cursor.fetchall()

		#Close database
		conn.close()

		#Return tasks
		return tasks

	############################################################################
	def update_finished_process(self, task_id, success=True, output=""):
		"""
		Updates a running processed to finished

		Parameters
		----------
		task_id : int
			Id of the process to update
		success : bool
			True if the process exited successfully, False if not
		output : str
			String representing the output of the process. Could be an 
			exitcode, message, whatever
		"""
		#Create connection
		conn = sqlite3.connect(self.dbname)
		cursor = conn.cursor()

		#Enforce WAL mode
		cursor.execute("PRAGMA journal_mode=WAL;")

		#Update entry
		query = "UPDATE tasks SET status = ?, output = ? WHERE id = ?"
		cursor.execute(query, (3 if success else 2, output, task_id))

		#Commit database
		conn.commit()
		conn.close()

	############################################################################
	def update_running_process(self, task_id):
		"""
		Updates a waiting processed to running

		Parameters
		----------
		task_id : int
			Id of the process to update
		"""
		#Create connection
		conn = sqlite3.connect(self.dbname)
		cursor = conn.cursor()

		#Enforce WAL mode
		cursor.execute("PRAGMA journal_mode=WAL;")

		#Update entry
		query = "UPDATE tasks SET status = 1 WHERE id = ?"
		cursor.execute(query, (task_id,))

		#Commit database
		conn.commit()
		conn.close()

	############################################################################
	def update_waiting_process(self, task_id):
		"""
		Updates a running processed to waiting. Useful if the server crashes 
		while a task is running. Next time we boot it will be in the running 
		state in the database so by moving it to waiting we will rerun it

		Parameters
		----------
		task_id : int
			Id of the process to update
		"""
		#Create connection
		conn = sqlite3.connect(self.dbname)
		cursor = conn.cursor()

		#Enforce WAL mode
		cursor.execute("PRAGMA journal_mode=WAL;")

		#Update entry
		query = "UPDATE tasks SET status = 0 WHERE id = ?"
		cursor.execute(query, (task_id,))

		#Commit database
		conn.commit()
		conn.close()

################################################################################
###                                  Main                                    ###
################################################################################
if __name__ == "__main__":
	#Get user inputs
	desc = "Initialize database"
	parser = argparse.ArgumentParser(desc)
	help_str = "Path to sqlite3 database to initialize. Default = 'tasks.db'"
	parser.add_argument("--dbname", help=help_str, default="tasks.db")
	args = parser.parse_args()

	#Initialize database
	task_db = Task_Database(args.dbname)
	task_db.setup_db()

################################################################################
###                               End of File                                ###
################################################################################