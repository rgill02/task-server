################################################################################
###                                 Imports                                  ###
################################################################################
#Standard imports
import time

#Our imports
from task_server import run_task_server

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
	dbname = "example.db"

	#Run task server
	print("Running task server. Kill with 'ctrl+c'")
	run_task_server(tasks, dbname=dbname, title="Example Task Server")

################################################################################
###                               End of File                                ###
################################################################################