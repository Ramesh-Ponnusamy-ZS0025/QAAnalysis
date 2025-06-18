from bs4 import BeautifulSoup
from prettytable import PrettyTable 
import json
import db_utils
import os
import datetime
from configparser import ConfigParser
from pathlib import Path
import training
import pandas as pd
import xlrd
import msal
import requests
import utils
from datetime import datetime

def unix_to_date_and_time_convertor(unix_time):
  # print(unix_time)
  return datetime.fromtimestamp(int(unix_time)).strftime('%Y-%m-%d %H:%M:%S')

def read_allure_json(filename, filetype, project_name, execution_type):
  # count = 0
  # for folder in Path(folder_path).rglob('*'):
  #  if folder.is_dir():
  #   if "test-cases" in str(folder):
  #    dir_list = os.listdir(str(folder))
  #    for json_file in dir_list:
  #     file_path=str(folder) + "\\" + json_file
  #     print(file_path)
  #     count = count +1
      testcase_list=[] 
      file_path=".//"+filename+"."+filetype 
      with open(file_path, 'r', encoding='utf-8') as file:
       json_data = json.load(file)

      # print(f"Folder: {folder}")
      myTable = PrettyTable(["Scenario", "StepName", "Status", "Failure reason", "error", "StartTime", "EndTime", "ExecutionTime"])

      test_name=json_data["name"].split("@")[0]
      error_desc=None
      error_trace=None
      step_name=None
      if "skipped" not in json_data["status"]:
       for x in json_data["testStage"]["steps"]:
        step_name=x["name"]
        if "unknown" not in x["status"]:
         start_time=unix_to_date_and_time_convertor(int(x["time"]['start'])//1000)
         end_time = unix_to_date_and_time_convertor(int(x["time"]['stop'])//1000)
         exec_time= x["time"]['duration']
        if "failed" in x["status"]:
         error_desc=x["statusMessage"].replace('"', '')
         error_trace=x["statusTrace"]
         myTable.add_row([test_name, step_name, "Failed", error_desc , "error", start_time, end_time, exec_time])
         testcase_list.append([test_name, step_name, error_desc , "error_trace", start_time, end_time, exec_time, project_name, x["status"], execution_type])
        elif "passed" in x["status"]:
         myTable.add_row([test_name, step_name, "Passed", "Null" , "error", start_time, end_time, exec_time])
         testcase_list.append([test_name, step_name, "Null" , "Null", start_time, end_time, exec_time, project_name, x["status"], execution_type])
        elif "skipped" in x["status"]:
         myTable.add_row([test_name, step_name, "Skipped", "Null" , "error", start_time, end_time, exec_time])
         testcase_list.append([test_name, step_name, "Null" , "Null", start_time, end_time, exec_time, project_name, x["status"], execution_type])
      print(len(testcase_list))
      db_utils.insert_data(testcase_list)

def format_date(input_string):
   input_string_ = input_string.replace("\\", "")
   date_format = "%d/%m/%y %H:%M:%S"
   try:
        date_value = datetime.strptime(input_string_, date_format)
        # Print extracted date in 'YYYY-MM-DD' format
        return date_value.strftime("%Y-%m-%d")
   except ValueError:
        print("Invalid date format.")

def read_json_report(filename,filetype,project_name, execution_type):
   data_list=[]
   json_data=None
   file_path=".//"+filename+"."+filetype 
   with open(file_path, 'r') as file:
     json_data = json.load(file)
#    print(json_data["Agadia_WorkFlow_PaHub_SmokeTest_Job_Chrome_Jenkins_202411211335"]["Test Case level Execution Details"][0])
   myTable = PrettyTable(["Scenario", "Step Name", "Status", "Failure Reason", "Error", "Start Time", "End Time", "Execution Time"])
   cases= json_data[filename]["Test Case level Execution Details"]
   start_time = format_date(json_data[filename]["Execution Summary"]["Start Time"])
   end_time = format_date(json_data[filename]["Execution Summary"]["End Time"])
   
   count = 0
   for x in cases:
     print(x["Exec.Status"])
     if "Failed" in x["Exec.Status"]:
       count=count+1
       myTable.add_row([x["Test Name"], x["Title"],x["Exec.Status"], x["Failure Reason"] , "null", start_time, end_time, x["Duration"]])
       data_list.append([x["Test Name"], x["Title"], x["Failure Reason"] , "null", start_time, end_time, x["Duration"],project_name,x["Exec.Status"],execution_type])
       print(x["Failure Reason"])
     if "Passed" in x["Exec.Status"]:
       count=count+1
       myTable.add_row([x["Test Name"], x["Title"],x["Exec.Status"], "null" , "null", start_time, end_time, x["Duration"]])
       data_list.append([x["Test Name"], x["Title"], "null" , "null", start_time, end_time, x["Duration"],project_name,x["Exec.Status"],execution_type])
     if "Skipped" in x["Exec.Status"]:
       count=count+1
       myTable.add_row([x["Test Name"], x["Title"],x["Exec.Status"], "null" , "null", start_time, end_time, x["Duration"]])
       data_list.append([x["Test Name"], x["Title"], x["Skip Reason"] , "null", start_time, end_time, x["Duration"],project_name,x["Exec.Status"],execution_type])    
   print(count)
   
   db_utils.insert_data(data_list)


def read_extent_report(filename, filetype, project_name, execution_type):
       data_list=[]
      #  file_path=".//"+filename
      #  print(file_path)
      #  with open(file_path, 'r') as f:
      #    soup = BeautifulSoup(f, 'html.parser')
       folder_path='ExecutionResults/'+project_name
       soup = get_file_content_as_soup(folder_path, filename)
       myTable = PrettyTable(["Scenario", "StepName", "Status", "Failure reason", "error", "StartTime", "EndTime", "ExecutionTime"])

       scenario_list = soup.find('ul',id='test-collection')

       
       for x in scenario_list.find_all('li'):
         test_name = x.find('span', class_='test-name').get_text()
         print(test_name)
         step_name_arr = x.find_all('td', class_='step-details')
         start_time=x.find('span', title='Test started time').get_text()
         print(start_time)
         end_time=x.find('span', title='Test ended time').get_text()
         exec_time=x.find('span', title='Time taken to finish').get_text()
         error=None
         step_name=None
         error_list=None
         reason_list=None
     
         for y in range(len(step_name_arr)):
          print(y)
          status=None
          step_name=step_name_arr[y].get_text()
          error=None
          error_arr=[]
          if "FAIL" in step_name_arr[y].get_text():
            status="Failed"
            error = step_name_arr[y+1].get_text()
            error_arr = error.split("at ")
            data_list.append([test_name, step_name, error_arr[0] , "error", start_time, end_time, exec_time, project_name, status, execution_type])
            myTable.add_row([test_name, step_name, status, "error_arr", "error", start_time, end_time, exec_time])
          elif "Step No:" in step_name_arr[y].get_text():
            status="Passed"
            data_list.append([test_name, step_name, "Null" , "Null", start_time, end_time, exec_time, project_name, status, execution_type])
            myTable.add_row([test_name, step_name, status, "error_arr" , "error", start_time, end_time, exec_time])
    
          status=None
          step_name=None
          error=None
       db_utils.insert_data(data_list)


def read_cucumber_report(file_path):
    # Read HTML file
    with open(file_path, 'r') as f:
        # Parse HTML using BeautifulSoup
        soup = BeautifulSoup(f, 'html.parser')
        
    myTable = PrettyTable(["Scenario", "StepName", "Failure reason", "error", "StartTime", "EndTime", "ExecutionTime"])
    scenario_list= soup.select("li[status= 'fail']")
    # print(scenario_list[0])
    for x in scenario_list:
      print(len(scenario_list))
      test_name = x.find('p', class_='name').get_text()
      step_details_tag = x.find('div', class_='step fail-bg')
      step_name = step_details_tag.find('span').get_text()
      error = step_details_tag.find('textarea').get_text()
      error_arr = error.split("at ")
      failure_reason=error_arr[0]
      time_tag=x.find('p', class_='text-sm')
      start_time=x.find_all('span')[0].get_text()
      exec_time=x.find_all('span')[1].get_text()
      print(exec_time)
      myTable.add_row([test_name, step_name, error_arr[0] , "error", start_time, "null", exec_time])
      print(myTable)
    df = myTable
    # df = pd.read_html(str(h2))
    return df

def read_excel_data():
    current_dir = Path(os.getcwd())
    exceldata_path = os.path.join(current_dir,"excel_reports","test_execution_for_prepare_intake_and_client_intake__sprint_8_.xls")

    try:
        data_dict = {}
        project_name = "Lexitas"
        file_extension = os.path.splitext(exceldata_path)[1].lower()
        
        # Read data based on the file extension
        if file_extension == '.xlsx' or file_extension == '.xls':
            df = pd.read_excel(exceldata_path)
        elif file_extension == '.csv':
            df = pd.read_csv(exceldata_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
        

        # Variable to keep track of the current ID
        current_id = None
        count=1
        # Iterate through each row in the DataFrame
        for index, row in df.iterrows():
            # Check if ID is not NaN (indicates a new record)
            if not pd.isna(row['ID']):
                current_id = row['ID']
                data_dict[current_id] = {
                    'Title': row['Title'],
                    'Status': row['Status'],
                    'Steps': row.iloc[29] if not pd.isna(row.iloc[29]) else ""
                }
            else:
                if current_id:
                    current_id_sub = current_id+"_"+ str(count)
                    data_dict[current_id_sub] = {
                    'Title': data_dict[current_id]['Title'],
                    'Status': data_dict[current_id]['Status'],
                    'Steps': row.iloc[29] if not pd.isna(row.iloc[29]) else ""
                    }
                count +=1

        testdata_list = []
        # Print the dictionary
        for id, details in data_dict.items():
            testdata_list.append([details['Title'],details['Steps'],None,None,None,None,None,project_name,details['Status'],"Functional"])
            db_utils.insert_data(testdata_list)
            testdata_list.clear()
            print("Data is inserted.")
    except Exception as ex:
        print(ex)

#Sharepoint access
config = ConfigParser()
config.read("config.ini")
client_id = config.get('Sharepoint Details', 'client_id')
client_secret = config.get('Sharepoint Details', 'client_secret')
tenant_id = config.get('Sharepoint Details', 'tenant_id')
authority = f'https://login.microsoftonline.com/{tenant_id}'
scope = ['https://graph.microsoft.com/.default']
tenant_name = "zuciinc"
site_name = "testautomation"

url_graph = "https://graph.microsoft.com/"
url_graph_v1 = url_graph + "v1.0/"
url_graph_v1_sites = url_graph_v1 + "sites/"
url_graph_v1_drives = url_graph_v1 + "drives/"

def get_access_token():
  try:
      # Create a confidential client application
      app = msal.ConfidentialClientApplication(
          client_id,
          authority=authority,
          client_credential=client_secret
      )
      # Acquire a token
      result = app.acquire_token_for_client(scopes=scope)
      if 'access_token' in result:
          access_token = result['access_token']
          return access_token
      else:
          print("Error acquiring token:", result.get("error_description"))
  except Exception as ex:
      raise Exception(f"Error in get_access_token method : {ex}")


def get_headers():
  headers = {
  "Authorization": f"Bearer {get_access_token()}",
  "Content-Type": "application/json",
  }
  return headers

def _get_site_id():
  
  site_url = f"{url_graph_v1_sites}{tenant_name}.sharepoint.com:/sites/{site_name}"
  site_response = requests.get(site_url, headers=get_headers())
  if site_response.status_code == 200:
      return site_response.json()["id"]
  else:
      raise Exception("Failed to get site ID: " + site_response.json())


def _get_drive_id(site_id):
  
  drive_url = f"{url_graph_v1_sites}{site_id}/drives"
  drive_response = requests.get(drive_url, headers=get_headers())
  if drive_response.status_code == 200:
      return drive_response.json()["value"][0]["id"]
  else:
      raise Exception("Failed to get drive ID: " + drive_response.json())

def get_file_content_as_soup(folder_name, file_name):
  try:
      site_id = _get_site_id()
      drive_id = _get_drive_id(site_id)
      file_url = f"{url_graph_v1}sites/{site_id}/drives/{drive_id}/root:/{folder_name}/{file_name}:/content"
      response = requests.get(file_url, headers=get_headers())
      if response.status_code == 200:
        content = response.text
        return BeautifulSoup(content, "html.parser")
      else:
        raise Exception(f"Failed to fetch file content: {response.text}")
  except Exception as ex:
      raise Exception(f"Error in get_file_content_as_text: {ex}")

def get_filenames_from_folder(site_id, drive_id, folder_name):
  try:
      # Get the contents of a specific folder
      folder_contents_url = f'https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{folder_name}:/children'
      contents_response = requests.get(folder_contents_url, headers=get_headers())
      filenames_list=[]
      if contents_response.status_code == 200:
          folder_contents = contents_response.json()
          for item in folder_contents.get('value', []):
              print(item['name'])  # Prints the file or folder name
              filenames_list.append(item['name'])
          
          if filenames_list is None:
              print("Error : filenames_list is empty. Could not fetch file names from the sharepoint folder")
              return
          else:
              return filenames_list
      else:
          print(f"Error: {contents_response.status_code}, {contents_response.text}")
  except Exception as ex:
      raise Exception(f"Error in get_filenames_from_folder method : {ex}")
  

def filter_duplicate_filenames(project_name):
  
  filenames_from_db_list = db_utils.get_filenames_for_each_projectname(project_name)
  site_id = _get_site_id()
  drive_id = _get_drive_id(site_id)
  #folder_path = "ExecutionResults/Lexitas"
  folder_path = "ExecutionResults/"+project_name
  filenames_from_sharepoint = get_filenames_from_folder(site_id,drive_id,folder_path)


  for filename in filenames_from_sharepoint[:]:
    if filename in filenames_from_db_list:
      filenames_from_sharepoint.remove(filename)
  print(len(filenames_from_sharepoint))
  return filenames_from_sharepoint

def update_database_with_unique_filenames(project_name):
  filenames_to_update = filter_duplicate_filenames(project_name)
  db_utils.insert_data_into_table(project_name,filenames_to_update)

# update_database_with_unique_filenames()
#read_excel_data()


def read_reports_config():
  config = ConfigParser()
  config.read("config.ini")
  report = config.get('Executions', 'report')
  report_type = config.get('Executions', 'report_type')
  execution_type = config.get('Executions', 'execution_type')
  project_name = config.get('Executions', 'project')
  
  if project_name=='Lexitas' and report_type=='json':
    read_allure_json(report, report_type, project_name, execution_type)
  elif project_name=='Intellihealth' and report_type=='html':
    for filename in utils.filter_duplicate_filenames(project_name):
     print(filename)
     read_extent_report(filename, report_type, project_name, execution_type)
    utils.update_database_with_unique_filenames(project_name)
  elif project_name=='Agadia' and report_type=='json':
     read_json_report(report,report_type,project_name,execution_type)
     utils.update_database_with_unique_filenames(project_name)

# filter_duplicate_filenames('Intellihealth')
# update_database_with_unique_filenames('Intellihealth')

read_reports_config()