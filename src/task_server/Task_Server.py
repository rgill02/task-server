################################################################################
###                                 Imports                                  ###
################################################################################
#Standard imports
import multiprocessing
import time

#Our imports
from . import db_service as db
from .task_monitor import monitor_tasks
from .task_api_server import run_app

################################################################################
###                                  Main                                    ###
################################################################################
def run_task_server(tasks, max_proc=4, log_dir="logs", 
					dbname=db.DB_NAME, title="Task Server", host="0.0.0.0", 
					port=8001):
	"""
	Runs our task monitor service in one process and our api server in another 
	process

	Parameters
	----------
	tasks : dict
		Dictionary of tasks we can run. Key = name, val = function to run
	max_proc : int
		Maximum number of processes to spawn to work on tasks
	log_dir : str
		Path to directory to store log files, will create if doesn't exist
	dbname : str
		Path to task database to use
	title : str
		Title of app
	host : str
		IP address to host app on
	port : int
		Port to host app on
	"""
	#Make sure database is setup
	db.init_db(dbname)

	#Start our monitor process
	monitor_args = (
		tasks,
		max_proc,
		log_dir,
		dbname
	)
	monitor_proc = multiprocessing.Process(target=monitor_tasks, 
										   args=monitor_args)
	monitor_proc.start()

	#Start our api server
	api_args = (
		list(tasks.keys()),
		title,
		dbname,
		host,
		port
	)
	api_proc = multiprocessing.Process(target=run_app, args=api_args, 
									   daemon=True)
	api_proc.start()

	#Now we have both processes running so monitor them
	try:
		while True:
			time.sleep(10)
	except KeyboardInterrupt as e:
		pass

	#Kill processes
	monitor_proc.terminate()
	monitor_proc.join()
	api_proc.terminate()
	api_proc.join()

################################################################################
###                               End of File                                ###
################################################################################