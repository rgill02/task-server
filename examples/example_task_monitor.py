################################################################################
###                                 Imports                                  ###
################################################################################
#Standard imports
import time
import threading

#Our imports
from task_server import db_service as db
from task_server import monitor_tasks

################################################################################
###                              Example Tasks                               ###
################################################################################
def print_alphabet(logger, input_file, output_file, sleep_time=1):
	"""
	Prints a letter of the alphabet every second
	"""
	for ii in range(26):
		logger.info("Alphabet: %s" % chr(65 + ii))
		time.sleep(sleep_time)

################################################################################
def print_1to100(logger, input_file, output_file, sleep_time=1):
	for ii in range(100):
		logger.info("Number: %d" % (ii + 1))
		time.sleep(sleep_time)

################################################################################
###                                  Main                                    ###
################################################################################
if __name__ == "__main__":
	#Create tasks
	tasks = {
		"print_alphabet": print_alphabet,
		"print_1to100": print_1to100
	}

	#Launch some test tasks
	dbname = "example.db"
	db.init_db(dbname)
	db.create_new_task("print_alphabet", dbname=dbname)
	db.create_new_task("print_1to100", dbname=dbname, config='{"sleep_time": 5}')

	#Run monitor function
	print("Monitoring tasks...")
	print("Kill with 'ctrl+c'")
	should_run = threading.Event()
	should_run.set()
	try:
		monitor_tasks(tasks, should_run, dbname=dbname)
	except KeyboardInterrupt as e:
		should_run.clear()

################################################################################
###                               End of File                                ###
################################################################################