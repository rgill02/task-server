################################################################################
###                                 Imports                                  ###
################################################################################
#Standard imports
import multiprocessing
import threading
import time
import os
import logging
import json

#Third party imports
from fastapi import FastAPI, HTTPException, Response, Body
from fastapi import status as apistatus
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

#Our imports
from Task_Database_2 import Task_Database

################################################################################
###                            Helper Functions                              ###
################################################################################
def task_runner(task_func, logfile, task_id, name, input_file, output_file, config):
	"""
	Runs a given task function after setting up a logger for it
	"""
	logger = logging.getLogger(name)
	logger.setLevel(logging.DEBUG)
	logger.propagate = False

	file_handler = logging.FileHandler(logfile, mode="a", delay=True)

	log_format = "%(asctime)s [%(levelname)s] %(name)s (PID: %(process)d) (TaskID: %(task_id)d): %(message)s"
	formatter = logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S')
	file_handler.setFormatter(formatter)
	logger.addHandler(file_handler)

	task_logger = logging.LoggerAdapter(logger, {"task_id": task_id})
	
	task_logger.info("Starting task '%s'" % name)

	task_func(task_logger, input_file, output_file, **json.loads(config))

################################################################################
###                            Task Server Class                             ###
################################################################################
class Task_Server:
	"""
	This is the server that manages the tasks. It kicks off new tasks and adds 
	entries to the task db. It monitors running tasks. And updates the entry in 
	the db when the task is finished. Runs tasks in multiple process to get 
	around the GIL
	"""
	############################################################################
	def __init__(self, tasks={}, host="0.0.0.0", port="8001", 
				 dbname="task_db.json", log_dir="logs", max_procs=4, 
				 title="Task Server"):
		"""
		Parameters
		----------
		tasks : dict
			Dictionary of tasks we can run. Key = name, val = function to run
		host : str
			IP address to host api server on
		port : int
			Port to hose api server on
		dbname : str
			Path to sqlite3 database holding tasks table
		log_dir : str
			Path to directory to store log files, will create if doesn't exist
		max_proc : int
			Maximum number of processes to spawn to work on tasks
		title : str
			Title of api
		"""
		#Save user args
		self.tasks = tasks
		self.host = host
		self.port = int(port)
		self.dbname = dbname
		self.log_dir = log_dir
		self.max_procs = int(max_procs)

		#Create log dir if doesn't exist
		if not os.path.exists(log_dir):
			os.makedirs(log_dir)

		#Create db interface
		self.task_db = Task_Database(dbname)

		#Keep track of processes and threads
		self.procs = []
		self.monitor_procs_should_run = threading.Event()
		self.monitor_procs_should_run.clear()
		self.monitor_procs_thread = None

		#Create fast api app
		self.app = FastAPI(title=title)

		#Setup routes
		self._setup_routes()

	############################################################################
	def __del__(self):
		#Cleanup
		if self.monitor_procs_thread:
			self.monitor_procs_should_run.clear()
			self.monitor_procs_thread.join()
			self.monitor_procs_thread = None

	############################################################################
	def move_all_leftover_running_tasks_to_waiting(self):
		running_tasks = self.task_db.get_all_running_tasks()
		for ii in range(len(running_tasks)):
			self.task_db.update_waiting_process(running_tasks[ii][0])

	############################################################################
	def monitor_procs(self):
		while self.monitor_procs_should_run.is_set():
			#Check if we are maxed out on processes
			proc_we_can_add = self.max_procs - len(self.procs)
			if proc_we_can_add > 0:
				#We have room for more so query database and see if any are 
				#waiting
				waiting_tasks = self.task_db.get_all_waiting_tasks()
				for ii in range(min(len(waiting_tasks), proc_we_can_add)):
					#Start new task
					task_id = waiting_tasks[ii][0]
					func_name = waiting_tasks[ii][1]
					infile = waiting_tasks[ii][4]
					outfile = waiting_tasks[ii][5]
					config = waiting_tasks[ii][6]
					logfile = os.path.join(self.log_dir, "task_%d.log" % task_id)
					new_proc = multiprocessing.Process(target=task_runner, args=(self.tasks[func_name], logfile, task_id, func_name, infile, outfile, config))
					self.task_db.update_running_process(task_id)
					new_proc.start()
					self.procs.append((task_id, new_proc))

			#Now we are either maxed out on processes or there are no more 
			#tasks waiting. So now check on the running processes
			idxs_to_remove = []
			for ii in range(len(self.procs)):
				task_id = self.procs[ii][0]
				proc = self.procs[ii][1]
				if proc.exitcode is None:
					#Process is still running
					pass
				elif proc.exitcode == 0:
					#Process completed successfully
					self.task_db.update_finished_process(task_id)
				else:
					#Process completed unsuccessfully
					self.task_db.update_finished_process(task_id, False, "Exitcode = %d" % proc.exitcode)
					#Process ended so we need to update the database and mark 
					#this one for removal
					proc.join()
					idxs_to_remove.append(ii)

			#Remove all the finished procs
			self.procs = [x for idx, x in enumerate(self.procs) if idx not in idxs_to_remove]

			#Sleep a little before repeating
			time.sleep(1)

	############################################################################
	def run(self):
		"""
		Runs the task server by starting the monitor thread
		"""
		self.move_all_leftover_running_tasks_to_waiting()

		#Start task monitor thread
		self.monitor_procs_should_run.set()
		self.monitor_procs_thread = threading.Thread(target=self.monitor_procs, 
													 daemon=True)
		self.monitor_procs_thread.start()

		#Start api server
		print("Running server on http://%s:%d" % (self.host, self.port))
		uvicorn.run(self.app, host=self.host, port=self.port)

		#Stop monitor thread
		self.monitor_procs_should_run.clear()
		self.monitor_procs_thread.join()

	############################################################################
	def _setup_routes(self):
		"""
		Defines the API endpoints
		"""
		########################################################################
		#Get all tasks
		@self.app.get("/")
		def get_all_tasks():
			return self.task_db.get_all_tasks()

		########################################################################
		#Create task
		@self.app.post("/add_task")
		def start_job(name: str = Body(), input_file: str = Body(), 
					  output_file: str = Body(), config: dict = Body()):
			#Check if job exists
			if name in self.tasks:
				task_func = self.tasks[name]
			else:
				raise HTTPException(
					status_code=apistatus.HTTP_400_BAD_REQUEST,
					detail="Task '%s' does not exist" % name
				)

			#Add entry to database
			self.task_db.create_new_task(name, input_file, output_file, json.dumps(config))

			#Tell user we successfully added the task
			return Response(status_code=apistatus.HTTP_200_OK)

################################################################################
###                                 Example                                  ###
################################################################################
#Create example tasks
def print_alphabet(input_file, output_file, config, logger):
	"""
	Prints a letter of the alphabet every second
	"""
	for ii in range(26):
		logger.info("Alphabet: %s" % chr(65 + ii))
		time.sleep(1)

def print_1to100(input_file, output_file, config, logger):
	for ii in range(100):
		logger.info("Number: %d" % (ii + 1))
		time.sleep(1)

if __name__ == "__main__":
	#Create task server
	task_server = Task_Server(tasks={
		"print_alphabet": print_alphabet,
		"print_1to100": print_1to100
	})

	#Run task server
	task_server.run()

################################################################################
###                               End of File                                ###
################################################################################