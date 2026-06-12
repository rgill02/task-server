################################################################################
###                                 Imports                                  ###
################################################################################
#Standard imports
import sqlite3
import argparse

################################################################################
###                                Constants                                 ###
################################################################################
DB_NAME = "tasks.db"
DB_TIMEOUT = 5

################################################################################
###                                Services                                  ###
################################################################################
def get_db_conn(dbname=DB_NAME):
	"""
	Gets a connection to the database. Should close the connection when you are 
	done with it

	Parameters
	----------
	dbname : str
		Path to sqlite3 database file to connect to

	Returns
	-------
	conn : sqlite3.conn
		Connection to database
	"""
	#Connect to database with timeout to handle multi threads/procs
	conn = sqlite3.connect(dbname, timeout=DB_TIMEOUT)

	#Configure concurrent settings
	conn.execute("PRAGMA journal_mode=WAL;")
	conn.execute("PRAGMA synchronous=NORMAL;")

	#Return connection
	return conn

################################################################################
def init_db(dbname=DB_NAME):
	"""
	This sets up all the tables in the database if they aren't already. 
	Only needs to be called once.

	Parameters
	----------
	dbname : str
		Path to sqlite3 database file to initialize
	"""
	with get_db_conn(dbname) as conn:
		cursor = conn.cursor()

		#Create tasks table
		cursor.execute("""
			CREATE TABLE IF NOT EXISTS tasks (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				name TEXT NOT NULL,
				created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%S', 'NOW')),
				status INTEGER NOT NULL CHECK(status in (0, 1, 2, 3)), --0: waiting, 1: running, 2: error, 3: done
				input_file TEXT,
				output_file TEXT,
				config TEXT,
				task_type INTEGER NOT NULL,	--0: creates a new file with new data, 1: modifies the existing file by adding or modifying auxiliary or metadata
				output TEXT
				) STRICT;
		""")
		cursor.execute("""
			CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
		""")

		#Commit to db
		conn.commit()

################################################################################
def create_new_task(name, input_file="", output_file="", config="{}", 
					dbname=DB_NAME):
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
	dbname : str
		Path to database file

	Returns
	-------
	id : int
		Id of new entry in table
	"""
	#Create connection
	with get_db_conn(dbname) as conn:
		conn.execute("BEGIN IMMEDIATE")
		cursor = conn.cursor()

		#Create and execute query
		query = "INSERT INTO tasks (name, created_at, status, input_file, " \
			  + "output_file, config, task_type) VALUES (?, DATETIME('now'), " \
			  + "0, ?, ?, ?, ?)"
		cursor.execute(query, (name, input_file, output_file, config, 
					   input_file == output_file))
		new_task_id = cursor.lastrowid

		#Commit database
		conn.commit()

	#Return id
	return new_task_id

############################################################################
def get_all_tasks(dbname=DB_NAME):
	"""
	Gets all the tasks in the tasks table and groups them by status

	Parameters
	----------
	dbname : str
		Path to database file

	Returns
	-------
	tasks : dict
		Dictionary with 4 keys: waiting_tasks, running_tasks, errored_tasks, and 
		finished_tasks. Each value is a list of entries
	"""
	tasks = {}
	with get_db_conn(dbname) as conn:
		cursor = conn.cursor()

		#Get all waiting tasks
		query = "SELECT * FROM tasks WHERE status = 0"
		cursor.execute(query)
		tasks["waiting_tasks"] = cursor.fetchall()

		#Get all running tasks
		query = "SELECT * FROM tasks WHERE status = 1"
		cursor.execute(query)
		tasks["running_tasks"] = cursor.fetchall()

		#Get all tasks that errored
		query = "SELECT * FROM tasks WHERE status = 2"
		cursor.execute(query)
		tasks["errored_tasks"] = cursor.fetchall()

		#Get all tasks that finished succesfully
		query = "SELECT * FROM tasks WHERE status = 3"
		cursor.execute(query)
		tasks["finished_tasks"] = cursor.fetchall()

	#Return tasks
	return tasks

############################################################################
def get_all_waiting_tasks(dbname=DB_NAME):
	"""
	Gets all the tasks in the tasks table that are waiting

	Parameters
	----------
	dbname : str
		Path to database file

	Returns
	-------
	tasks : list
		List of entries of waiting tasks
	"""
	#Create connection
	with get_db_conn() as conn:
		cursor = conn.cursor()

		#Get all waiting tasks
		query = "SELECT * FROM tasks WHERE status = 0"
		cursor.execute(query)
		tasks = cursor.fetchall()

	#Return tasks
	return tasks

############################################################################
def get_all_running_tasks(dbname=DB_NAME):
	"""
	Gets all the tasks in the tasks table that are running

	Parameters
	----------
	dbname : str
		Path to database file

	Returns
	-------
	tasks : list
		List of entries of running tasks
	"""
	#Create connection
	with get_db_conn() as conn:
		cursor = conn.cursor()

		#Get all running tasks
		query = "SELECT * FROM tasks WHERE status = 1"
		cursor.execute(query)
		tasks = cursor.fetchall()

	#Return tasks
	return tasks

############################################################################
def get_all_errored_tasks(dbname=DB_NAME):
	"""
	Gets all the tasks in the tasks table that are errored

	Parameters
	----------
	dbname : str
		Path to database file

	Returns
	-------
	tasks : list
		List of entries of errored tasks
	"""
	#Create connection
	with get_db_conn() as conn:
		cursor = conn.cursor()

		#Get all errored tasks
		query = "SELECT * FROM tasks WHERE status = 2"
		cursor.execute(query)
		tasks = cursor.fetchall()

	#Return tasks
	return tasks

############################################################################
def get_all_finished_tasks(dbname=DB_NAME):
	"""
	Gets all the tasks in the tasks table that are finished

	Parameters
	----------
	dbname : str
		Path to database file

	Returns
	-------
	tasks : list
		List of entries of finished tasks
	"""
	#Create connection
	with get_db_conn() as conn:
		cursor = conn.cursor()

		#Get all finished tasks
		query = "SELECT * FROM tasks WHERE status = 3"
		cursor.execute(query)
		tasks = cursor.fetchall()

	#Return tasks
	return tasks

################################################################################
def update_to_finished(task_id, success=True, output="", dbname=DB_NAME):
	"""
	Updates a processe to finished or errored

	Parameters
	----------
	task_id : int
		Id of the process to update
	success : bool
		True if the process exited successfully, False if not
	output : str
		String representing the output of the process. Could be an 
		exitcode, message, whatever
	dbname : str
		Path to database file
	"""
	with get_db_conn() as conn:
		conn.execute("BEGIN IMMEDIATE")
		cursor = conn.cursor()

		#Update entry
		query = "UPDATE tasks SET status = ?, output = ? WHERE id = ?"
		cursor.execute(query, (3 if success else 2, output, task_id))

		#Commit database
		conn.commit()

################################################################################
def update_to_running(task_id, dbname=DB_NAME):
	"""
	Updates a process to running

	Parameters
	----------
	task_id : int
		Id of the process to update
	dbname : str
		Path to database file
	"""
	with get_db_conn() as conn:
		conn.execute("BEGIN IMMEDIATE")
		cursor = conn.cursor()

		#Update entry
		query = "UPDATE tasks SET status = ? WHERE id = ?"
		cursor.execute(query, (1, task_id))

		#Commit database
		conn.commit()

################################################################################
def update_to_waiting(task_id, dbname=DB_NAME):
	"""
	Updates a process to waiting. Useful if the program dies with some 
	processes in the middle of running. If we boot again to find some in the 
	running state we can set them to waiting to rerun them

	Parameters
	----------
	task_id : int
		Id of the process to update
	dbname : str
		Path to database file
	"""
	with get_db_conn() as conn:
		conn.execute("BEGIN IMMEDIATE")
		cursor = conn.cursor()

		#Update entry
		query = "UPDATE tasks SET status = ? WHERE id = ?"
		cursor.execute(query, (0, task_id))

		#Commit database
		conn.commit()

################################################################################
###                                  Main                                    ###
################################################################################
if __name__ == "__main__":
	#Get user inputs
	desc = "Initialize database and show all tasks"
	parser = argparse.ArgumentParser(desc)
	help_str = "Path to sqlite3 database to initialize. Default = 'tasks.db'"
	parser.add_argument("--dbname", help=help_str, default="tasks.db")
	args = parser.parse_args()

	#Initialize database
	init_db(args.dbname)
	print("Initialized database: %s\n" % args.dbname)

	#Get and print all tasks
	tasks = get_all_tasks(args.dbname)
	print("Waiting Tasks:")
	if "waiting_tasks" in tasks:
		for entry in tasks["waiting_tasks"]:
			task_type = "New File"
			if entry[7]:
				task_type = "In Place"
			print("\tID: %d" % entry[0])
			print("\t\tName: %s" % entry[1])
			print("\t\tCreated: %s" % entry[2])
			print("\t\tInput File: %s" % entry[4])
			print("\t\tOutput File: %s" % entry[5])
			print("\t\tConfig: %s" % entry[6])
			print("\t\tTask Type: %s" % task_type)
	print("Running Tasks:")
	if "running_tasks" in tasks:
		for entry in tasks["running_tasks"]:
			task_type = "New File"
			if entry[7]:
				task_type = "In Place"
			print("\tID: %d" % entry[0])
			print("\t\tName: %s" % entry[1])
			print("\t\tCreated: %s" % entry[2])
			print("\t\tInput File: %s" % entry[4])
			print("\t\tOutput File: %s" % entry[5])
			print("\t\tConfig: %s" % entry[6])
			print("\t\tTask Type: %s" % task_type)
	print("Errored Tasks:")
	if "errored_tasks" in tasks:
		for entry in tasks["errored_tasks"]:
			task_type = "New File"
			if entry[7]:
				task_type = "In Place"
			print("\tID: %d" % entry[0])
			print("\t\tName: %s" % entry[1])
			print("\t\tCreated: %s" % entry[2])
			print("\t\tInput File: %s" % entry[4])
			print("\t\tOutput File: %s" % entry[5])
			print("\t\tConfig: %s" % entry[6])
			print("\t\tTask Type: %s" % task_type)
			print("\t\tOutput: %s" % entry[8])
	print("Finished Tasks:")
	if "finished_tasks" in tasks:
		for entry in tasks["finished_tasks"]:
			task_type = "New File"
			if entry[7]:
				task_type = "In Place"
			print("\tID: %d" % entry[0])
			print("\t\tName: %s" % entry[1])
			print("\t\tCreated: %s" % entry[2])
			print("\t\tInput File: %s" % entry[4])
			print("\t\tOutput File: %s" % entry[5])
			print("\t\tConfig: %s" % entry[6])
			print("\t\tTask Type: %s" % task_type)
			print("\t\tOutput: %s" % entry[8])


################################################################################
###                               End of File                                ###
################################################################################