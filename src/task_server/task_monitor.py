################################################################################
###                                 Imports                                  ###
################################################################################
#Standard imports
import multiprocessing
import logging
import json
import argparse
import os
import time

#Our imports
from . import db_service as db

################################################################################
###                             Helper Functions                             ###
################################################################################
def task_launcher(task_func, logfile, task_id, name, input_file="", 
				  output_file="", config="{}"):
	"""
	Launches a given task function after setting up a logger for it

	Parameters
	----------
	task_func : func
		Function to call as task
	logfile : str
		Path to log file for this task to write to
	task_id : int
		ID of task
	name : str
		Name of task
	input_file : str
		Path to input file associated with task
	output_file : str
		Path to output file associated with task
	config : str
		JSON serialized dictionary representing kwargs for task func
	"""
	#Create logger
	logger = logging.getLogger(name)
	logger.setLevel(logging.DEBUG)
	logger.propagate = False

	#Create log file handler
	file_handler = logging.FileHandler(logfile, mode="a", delay=True)

	#Create log formatter
	log_format = "%(asctime)s [%(levelname)s] %(name)s (PID: %(process)d) (TaskID: %(task_id)d): %(message)s"
	formatter = logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S')

	#Attach formatter to handler and handler to logger
	file_handler.setFormatter(formatter)
	logger.addHandler(file_handler)

	#Create a logging adapter to include task id in log message
	task_logger = logging.LoggerAdapter(logger, {"task_id": task_id})

	task_func(task_logger, input_file, output_file, **json.loads(config))

################################################################################
###                                  Main                                    ###
################################################################################
def monitor_tasks(tasks, max_proc=4, log_dir="logs", 
				  dbname=db.DB_NAME):
	"""
	This function constantly monitors the tasks in the database. If there are 
	tasks waiting and it has an open processor it runs a new task. If a task 
	finishes it updates the database entry. All tasks are run in a separate 
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
	"""
	#Create log dir if doesn't exist
	if not os.path.exists(log_dir):
		os.makedirs(log_dir)

	#Keep track of processes
	procs = []

	#Initialize db if needed
	db.init_db(dbname=dbname)

	#Any tasks that are marked as running got killed in the middle of running 
	#last time so lets change those to waiting so that we can rerun them
	running_tasks = db.get_all_running_tasks(dbname=dbname)
	for ii in range(len(running_tasks)):
		db.update_to_waiting(running_tasks[ii][0], dbname=dbname)

	#Monitor tasks
	while True:
		#Check if we are maxed out on processes
		proc_we_can_add = max_proc - len(procs)
		if proc_we_can_add > 0:
			#We have room for more processes so check if any tasks are 
			#waiting
			waiting_tasks = db.get_all_waiting_tasks(dbname=dbname)
			#Add as many waiting tasks as we can
			for ii in range(min(len(waiting_tasks), proc_we_can_add)):
				#Start new task
				task_id = waiting_tasks[ii][0]
				name = waiting_tasks[ii][1]
				infile = waiting_tasks[ii][4]
				outfile = waiting_tasks[ii][5]
				config = waiting_tasks[ii][6]
				logfile = os.path.join(log_dir, "task_%d.log" % task_id)
				launcher_args = (
					tasks[name],
					logfile,
					task_id,
					name,
					infile,
					outfile,
					config
				)
				new_proc = multiprocessing.Process(target=task_launcher, 
												   args=launcher_args, 
												   daemon=True)
				db.update_to_running(task_id, dbname=dbname)
				new_proc.start()
				procs.append((task_id, new_proc))

		#Now we are either maxed out on processes or there are no more tasks 
		#waiting. So now check on the running processes
		idxs_to_remove = []
		for ii in range(len(procs)):
			task_id = procs[ii][0]
			proc = procs[ii][1]
			if proc.exitcode is None:
				#Process is still running
				pass
			elif proc.exitcode == 0:
				#Process completed successfully
				db.update_to_finished(task_id, dbname=dbname)
				#Process ended so join and mark for removal
				proc.join()
				idxs_to_remove.append(ii)
			else:
				#Process completed unsuccessfully
				output_msg = "Exitcode = %d" % proc.exitcode
				db.update_to_finished(task_id, False, output_msg, 
									  dbname=dbname)
				#Process ended so join and mark for removal
				proc.join()
				idxs_to_remove.append(ii)

		#Remove all finished procs
		procs = [x for idx, x in enumerate(procs) if idx not in idxs_to_remove]

		#Sleep a little before repeating
		time.sleep(1)

################################################################################
###                               End of File                                ###
################################################################################