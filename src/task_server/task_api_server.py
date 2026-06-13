################################################################################
###                                 Imports                                  ###
################################################################################
#Standard imports
import json
import argparse

#Third party imports
from fastapi import FastAPI, HTTPException, Response, Body
from fastapi import status as apistatus
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

#Our imports
from . import db_service as db

################################################################################
###                                   API                                    ###
################################################################################
def setup_app(task_names=[], title="Task Server", dbname=db.DB_NAME):
	"""
	Creates a fastapi app

	Parameters
	----------
	task_names : list
		List of strings representing possible task names
	title : str
		Title of app
	dbname : str
		Path of database to connect to

	Returns
	-------
	app : FastAPI.app
		Fast api app
	"""
	app = FastAPI(title=title)

	db.init_db(dbname)

	@app.get("/")
	def get_all_tasks():
		return db.get_all_tasks(dbname)

	@app.get("/task_names")
	def get_task_names():
		return task_names

	@app.post("/add_task")
	def add_task(name: str = Body(), input_file: str = Body(), 
				 output_file: str = Body(), config: dict = Body()):
		#Check if job exists
		if name not in task_names:
			raise HTTPException(status_code=apistatus.HTTP_400_BAD_REQUEST, 
								detail="Task '%s' does not exist" % name)

		#Add entry to database
		db.create_new_task(name, input_file, output_file, json.dumps(config), 
						   dbname=dbname)

		return Response(status_code=apistatus.HTTP_200_OK)

	return app

################################################################################
def run_app(task_names=[], title="Task Server", dbname=db.DB_NAME, 
			host="0.0.0.0", port=8001):
	"""
	Creates and runs a fastapi app via uvicorn

	Parameters
	----------
	task_names : list
		List of strings representing possible task names
	title : str
		Title of app
	dbname : str
		Path of database to connect to
	host : str
		IP address to host app on
	port : int
		Port to host app on
	"""
	app = setup_app(task_names, title, dbname)
	print("Running api server on http://%s:%d" % (host, port))
	uvicorn.run(app, host=host, port=port)

################################################################################
###                               End of File                                ###
################################################################################