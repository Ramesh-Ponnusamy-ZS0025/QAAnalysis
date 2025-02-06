import psycopg2
import pandas as pd 
from configparser import ConfigParser
#from config import Config 

def db_connect():
 config = ConfigParser()
 config.read("config.ini")
 hostname = config.get('DB Details', 'hostname')
 database = config.get('DB Details', 'database')
 username = config.get('DB Details', 'username')
 pwd = config.get('DB Details', 'pwd')
 port_id = config.get('DB Details', 'port_id')
 conn = psycopg2.connect(
    host=hostname,
    dbname=database,
    user=username,
    password=pwd,
    port=port_id)
 return conn

def get_data(project_name): 
  sql = """select id, scenario scenario_name, step_name, failure_reason, 
  error, start_time, end_time, execution_time  exec_time, project_name, status "Execution_status" ,NULL execution_type
   from "test_cases" where project_name=%s;"""
  conn = None
  cur = None
  try: 
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(sql, (project_name,))
    results = cur.fetchall()

    conn.commit()
    cur.close() 
        
  except (Exception, psycopg2.DatabaseError) as error: 
    print(error) 
  finally: 
    if conn is not None: 
        conn.close()
    if cur is not None:
        cur.close()
  column_names = ['id', 'scenario_name', 'step_name', 'failure_reason', 'error', 'start_time', 'end_time', 'exec_time', 'project_name', 'Execution_status', 'execution_type'] 
  df = pd.DataFrame(results, columns=column_names)
  return df


def insert_data(data): 
    sql = """INSERT INTO "AI_Test_result_prediction".report_data(
	  scenario_name, step_name, failure_reason, error, start_time, end_time, exec_time, project_name, execution_status, execution_type)
	  VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"""
    conn = None
    cur = None
    try: 
      conn = db_connect()
      cur = conn.cursor()
      cur = conn.cursor()

      for d in data:
        print(d)
        cur.execute(sql, d)

      conn.commit()
      cur.close() 
    except (Exception, psycopg2.DatabaseError) as error: 
     print(error) 
    finally: 
     if conn is not None: 
        conn.close()
     if cur is not None:
        cur.close()

schema_name = "AI_Test_result_prediction"
tablename = "report_matrix"
column_name_filename = "report_file_name"
column_name_projectname = "project_name"
column_name_file_hash = "file_hash"

def get_filenames_for_each_projectname(project_name:str):
  try:
    conn = db_connect()
    cursor = conn.cursor()
    getcolumnvalue_query = f"""SELECT "{column_name_file_hash}" FROM "{schema_name}".{tablename.lower()} WHERE project_name='{project_name}';"""
    print(getcolumnvalue_query)
    cursor.execute(getcolumnvalue_query)
    filenames_from_databasetable = cursor.fetchall()
    filenames_from_db_list = [filename[0] for filename in filenames_from_databasetable]
    
    cursor.close()
    if filenames_from_databasetable is None:
        raise Exception(f"Error : Filename column is empty in {tablename} Database table")
    return filenames_from_db_list
  except (Exception, psycopg2.DatabaseError) as error: 
    print(error) 
  finally: 
    if conn is not None: 
      conn.close()
    if cursor is not None:
      cursor.close()
    
def insert_data_into_table(project_name, filenames):
  try:
    conn = db_connect()
    cursor = conn.cursor()
    if not filenames:
        print(f"Filenames in the '{tablename}' table are up-to date. No new filenames are found in the sharepoint.")
    else:
        for key, value in filenames.items():
            getcolumnvalue_query = f"""INSERT INTO "{schema_name}".{tablename} 
            ({column_name_projectname},{column_name_filename}, {column_name_file_hash}) VALUES 
            ('{project_name}','{key}', '{value}');"""
            print(getcolumnvalue_query)
            cursor.execute(getcolumnvalue_query)
            
      
        conn.commit()  
        cursor.close()
        print("Table is updated successfully.")
  except (Exception, psycopg2.DatabaseError) as error: 
    print(error) 
  finally: 
    if conn is not None: 
      conn.close()
    if cursor is not None:
      cursor.close()