import json
import pandas as pd
from datetime import datetime
from prettytable import PrettyTable
import os
def format_date(input_string):
   input_string_ = input_string.replace("\\", "")
   date_format = "%d/%m/%y %H:%M:%S"
   try:
        date_value = datetime.strptime(input_string_, date_format)
        # Print extracted date in 'YYYY-MM-DD' format
        return date_value.strftime("%Y-%m-%d")
   except ValueError:
        print("Invalid date format.")

def read_json_report(file_path,filename ,file_type ,project_name):
    data_list =[]
    json_data =None
    with open(file_path, 'r') as file:
        json_data = json.load(file)
    #    print(json_data["Agadia_WorkFlow_PaHub_SmokeTest_Job_Chrome_Jenkins_202411211335"]["Test Case level Execution Details"][0])
    myTable = PrettyTable \
        (["Scenario", "Step Name", "Status", "Failure Reason", "Error", "Start Time", "End Time", "Execution Time"])
    cases= json_data[filename]["Test Case level Execution Details"]
    start_time = format_date(json_data[filename]["Execution Summary"]["Start Time"])
    end_time = format_date(json_data[filename]["Execution Summary"]["End Time"])

    count = 0
    for x in cases:
        # print(x["Exec.Status"])
        if "Failed" in x["Exec.Status"]:
            count =count +1
            myTable.add_row \
                ([x["Test Name"], x["Title"] ,x["Exec.Status"], x["Failure Reason"] , "null", start_time, end_time, x["Duration"]])
            data_list.append \
                ([x["Test Name"], x["Title"], x["Failure Reason"] , "Error", start_time, end_time, x["Duration"]
                 ,project_name ,x["Exec.Status"] ])
            # print(x["Failure Reason"])
        if "Passed" in x["Exec.Status"]:
            count =count +1
            myTable.add_row \
                ([x["Test Name"], x["Title"] ,x["Exec.Status"], "null" , "null", start_time, end_time, x["Duration"]])
            data_list.append \
                ([x["Test Name"], x["Title"], "null" , "null", start_time, end_time, x["Duration"] ,project_name
                 ,x["Exec.Status"] ])
        if "Skipped" in x["Exec.Status"]:
            count =count +1
            myTable.add_row \
                ([x["Test Name"], x["Title"] ,x["Exec.Status"], "null" , "null", start_time, end_time, x["Duration"]])
            data_list.append([x["Test Name"], x["Title"], x["Skip Reason"] , "null", start_time, end_time, x["Duration"]
                              ,project_name ,x["Exec.Status"] ])
    df = pd.DataFrame(myTable.rows, columns=myTable.field_names)
    df['TCID'] = df['Scenario'].str.extract(r'^(C\d+)')
    return df
    # print(count)