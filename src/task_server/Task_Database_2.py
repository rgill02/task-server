################################################################################
###                                 Imports                                  ###
################################################################################
#Standard imports
import json
import os
import threading
from datetime import datetime
import copy

################################################################################
###                           Task Database Class                            ###
################################################################################
class Task_Database:
	"""
	I tried originally making a database interface to an sqlite3 database. I 
	tried making it handle multi-threading/multi-process access but it seems to 
	hang occasionally. Therefore, this is my temporary fix. I will store the 
	database in memory as a dictionary that I occassionally write to a file to 
	backup. This is not elegant, but it should get the job done for now without 
	hanging.
	"""
	############################################################################
	def __init__(self, dbname="task_db.json"):
		"""
		Parameters
		----------
		dbname : str
			Path to json file representing our database
		"""
		#Save args
		self.dbname = dbname

		#Load file if it exists
		if os.path.exists(dbname):
			with open(dbname, 'r') as fh:
				self.db = json.load(fh)
		else:
			self.db = {
				"waiting_tasks": [],
				"running_tasks": [],
				"errored_taasks": [],
				"finished_tasks": []
			}

		#Determine next id
		highest_id = 0
		for key, val in self.db.items():
			for entry in val:
				if entry[0] > highest_id:
					highest_id = entry[0]
		self.next_id = highest_id + 1

		#Create mutex so multiple threads can safely access the database
		self.lock = threading.Lock()

	############################################################################
	def _write_db_to_file(self):
		with open(self.dbname, 'w') as fh:
			json.dump(self.db, fh)

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
		with self.lock:
			now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			new_entry = [
				self.next_id, 
				name, 
				now_str, 
				0,	#waiting
				input_file, 
				output_file, 
				config, 
				int(input_file == output_file), 
				""
			]
			self.next_id += 1
			self.db["waiting_tasks"].append(new_entry)
			self._write_db_to_file()
		return new_entry[0]

	############################################################################
	def get_all_tasks(self):
		"""
		Gets all the tasks in the tasks table and groups them by status

		Returns
		-------
		tasks : dict
			Dictionary with 4 keys: waiting_tasks, running_tasks, errored_tasks, 
			and finished_tasks. Each value is a list of entries
		"""
		with self.lock:
			return copy.deepcopy(self.db)

	############################################################################
	def get_all_waiting_tasks(self):
		"""
		Gets all the waiting tasks in the tasks table

		Returns
		-------
		tasks : dict
			List of entries for waiting tasks
		"""
		with self.lock:
			return copy.deepcopy(self.db["waiting_tasks"])

	############################################################################
	def get_all_running_tasks(self):
		"""
		Gets all the running tasks in the tasks table

		Returns
		-------
		tasks : dict
			List of entries for running tasks
		"""
		with self.lock:
			return copy.deepcopy(self.db["running_tasks"])

	############################################################################
	def get_all_errored_tasks(self):
		"""
		Gets all the errored tasks in the tasks table

		Returns
		-------
		tasks : dict
			List of entries for errored tasks
		"""
		with self.lock:
			return copy.deepcopy(self.db["errored_tasks"])

	############################################################################
	def get_all_finished_tasks(self):
		"""
		Gets all the finished tasks in the tasks table

		Returns
		-------
		tasks : dict
			List of entries for finished tasks
		"""
		with self.lock:
			return copy.deepcopy(self.db["finished_tasks"])

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
		with self.lock:
			idx = -1
			for ii in range(len(self.db["running_tasks"])):
				if self.db["running_tasks"][ii][0] == task_id:
					#This is the process to update
					idx = ii
					break
			self.db["running_tasks"][idx][3] = 0
			self.db["waiting_tasks"].append(self.db["running_tasks"][idx])
			del self.db["running_tasks"][idx]
			self._write_db_to_file()

	############################################################################
	def update_running_process(self, task_id):
		"""
		Updates a waiting processed to running

		Parameters
		----------
		task_id : int
			Id of the process to update
		"""
		with self.lock:
			idx = -1
			for ii in range(len(self.db["waiting_tasks"])):
				if self.db["waiting_tasks"][ii][0] == task_id:
					#This is the process to update
					idx = ii
					break
			self.db["waiting_tasks"][idx][3] = 1
			self.db["running_tasks"].append(self.db["waiting_tasks"][idx])
			del self.db["waiting_tasks"][idx]
			self._write_db_to_file()

	############################################################################
	def update_finished_process(self, task_id, success=True, output=""):
		"""
		Updates a running processed to finished

		Parameters
		----------
		task_id : int
			Id of the process to update
		"""
		with self.lock:
			idx = -1
			for ii in range(len(self.db["running_tasks"])):
				if self.db["running_tasks"][ii][0] == task_id:
					#This is the process to update
					idx = ii
					break
			self.db["running_tasks"][idx][3] = 3 if success else 2
			self.db["running_tasks"][idx][8] = output
			if success:
				self.db["finished_tasks"].append(self.db["running_tasks"][idx])
			else:
				self.db["errored_tasks"].append(self.db["running_tasks"][idx])
			del self.db["running_tasks"][idx]
			self._write_db_to_file()

	############################################################################