# app.py
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import os
import pandas as pd
from bs4 import BeautifulSoup
import json
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from prettytable import PrettyTable
import json
import os
import pandas as pd
import sqlite3
import psycopg2
import configparser

from db_utils import db_query_form
from extract_reports import read_json_report
from training import training_model
app = Flask(__name__)

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'html', 'xlsx', 'json', 'xml'}

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Store the last uploaded file path
last_uploaded_file = None
project_name=None

import math

def sanitize_data(data):
    if isinstance(data, dict):
        return {key: sanitize_data(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    elif isinstance(data, float) and (math.isnan(data) or math.isinf(data)):
        return None  # or replace with a default value like 0
    return data


def get_db_connection():
    # Read database credentials from config.ini
    config = configparser.ConfigParser()
    config.read('config.ini')
    db_type = config['DB Details']['db_type']

    if db_type == 'sqlite':
        return sqlite3.connect(config['DB Details']['sqlite_db_path'])
    else:
        return psycopg2.connect(
            host=config['DB Details']['hostname'],
            database=config['DB Details']['database'],
            user=config['DB Details']['username'],
            password=config['DB Details']['pwd'],
            port=config['DB Details']['port_id']
        )


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_file(file_path, file_type):
    """Process different file types and return first two records"""
    try:
        if file_type == 'html':
            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'html.parser')
                # Extract table data
                tables = soup.find_all('table')
                if tables:
                    rows = tables[0].find_all('tr')
                    data = []
                    for row in rows[1:3]:  # Get first two data rows
                        cols = row.find_all('td')
                        data.append([col.text.strip() for col in cols])
                    return data

        elif file_type == 'xlsx':
            df = pd.read_excel(file_path)
            return df.head(2).values.tolist()

        elif file_type == 'json':
            with open(file_path, 'r') as f:
                data = json.load(f)
                return data[:2] if isinstance(data, list) else list(data.items())[:2]

        elif file_type == 'xml':
            tree = ET.parse(file_path)
            root = tree.getroot()
            data = []
            for child in list(root)[:2]:
                data.append([elem.text for elem in child])
            return data

        return []
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return []


def analyze_issues(file_path, file_type):
    """Analyze file for issues and return top 2 issues"""
    try:
        issues = []

        if file_type == 'html':
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'error' in content.lower():
                    issues.append("Error detected in HTML content")
                if 'warning' in content.lower():
                    issues.append("Warning messages found in content")
                if 'failed' in content.lower():
                    issues.append("Test failure detected")

        # Add similar analysis for other file types

        return issues[:2]  # Return top 2 issues
    except Exception as e:
        return [f"Error analyzing file: {str(e)}"]


@app.route('/')
def index():
    return render_template('index.html')

def separate_failure_and_error(row):
    row['Error'] = row['Failure Reason']
    failure_lines = row['Failure Reason'].strip().split('\n')
    if len(failure_lines) > 1:
        row['Failure Reason'] = failure_lines[0]
        # row['Error'] = "\n".join(failure_lines[1:])
    else:
        row['Error'] = "ERROR"  # No additional lines, set "ERROR"
    return row

# Function to create table if it doesn't exist
def create_table():
    # Connect to SQLite database
    conn = get_db_connection()
    cursor = conn.cursor()
    # cursor.execute("""drop table if exists TestCases """)
    # conn.commit()
    # Create table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS TestCases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name text,
        project_type text,
        tcid TEXT,
        scenario TEXT,
        step_name TEXT,
        failure_reason TEXT,
        error TEXT,
        start_time TEXT,
        end_time TEXT,
        execution_time TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Commit and close
    conn.commit()
    cursor.close()
    conn.close()
def insert_test_case(project_name,project_type,tcid,scenario, step_name, failure_reason, error, start_time, end_time, execution_time,status):
    # Connect to the SQLite database
    conn = get_db_connection()
    cursor = conn.cursor()
    insert_query = """
    INSERT INTO test_cases (project_name,project_type,tcid,scenario, step_name, failure_reason, error, start_time, end_time, execution_time,status)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    insert_query = db_query_form(insert_query)
    # Insert the test case into the database
    cursor.execute(insert_query, (project_name,project_type,tcid,scenario, step_name, failure_reason, error, start_time, end_time, execution_time,status))

    # Commit the transaction and close the connection
    conn.commit()
    cursor.close()
    conn.close()

    # print("Test case inserted successfully.")


def read_extent_report(file_path,project_name,report_type):
    data_list = []
    #  file_path=".//"+filename
    #  print(file_path)
    #  with open(file_path, 'r') as f:
    #    soup = BeautifulSoup(f, 'html.parser')
    folder_path = 'ExecutionResults/' + project_name
    # soup = get_file_content_as_soup(folder_path, filename)
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    myTable = PrettyTable(
        ["Scenario", "Step Name", "Status", "Failure Reason", "Error", "Start Time", "End Time", "Execution Time"])

    scenario_list = soup.find('ul', id='test-collection')

    for x in scenario_list.find_all('li'):
        test_name = x.find('span', class_='test-name').get_text()
        step_name_arr = x.find_all('td', class_='step-details')
        start_time = x.find('span', title='Test started time').get_text()
        end_time = x.find('span', title='Test ended time').get_text()
        exec_time = x.find('span', title='Time taken to finish').get_text()
        error = None
        step_name = None
        error_list = None
        reason_list = None

        for y in range(len(step_name_arr)):
            status = None
            step_name = step_name_arr[y].get_text()
            error = None
            error_arr = []
            if "FAIL" in step_name_arr[y].get_text():
                status = "Failed"
                error = step_name_arr[y + 1].get_text()
                error_arr = error.split("at ")
                data_list.append(
                    [test_name, step_name, error_arr[0], "error", start_time, end_time, exec_time, project_name, status])
                myTable.add_row([test_name, step_name, status, error_arr[0], "error", start_time, end_time, exec_time])
            elif "Step No:" in step_name_arr[y].get_text():
                status = "Passed"
                data_list.append(
                    [test_name, step_name, "Null", "Null", start_time, end_time, exec_time, project_name, status])
                myTable.add_row([test_name, step_name, status, "", "", start_time, end_time, exec_time])

            status = None
            step_name = None
            error = None
    df = pd.DataFrame(myTable.rows, columns=myTable.field_names)
    df['TCID'] = df['Scenario'].str.extract(r'^(C\d+)')
    return df


def read_cucumber_report(file_path,project_name,report_type):
    # Read HTML file
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    all_data = []

    # Select failed test cases
    failed_tests = soup.select("li.collection-item.test.displayed.fail")

    for test in failed_tests:
        test_name = test.find('span', class_='test-name').get_text(strip=True)
        start_time = test.find('span', class_='test-started-time').get_text(strip=True)
        end_time = test.find('span', class_='test-ended-time').get_text(strip=True)
        exec_time = test.find('span', class_='test-time-taken').get_text(strip=True)

        # Dictionary to map each step to its failure reason
        failed_reason = {}

        # Extract failed steps
        failed_steps = test.select('tr td.status.fail')

        current_step = ""

        for step in failed_steps:
            failure_reason = ""

            step_row = step.find_parent('tr')
            step_details_td = step_row.find('td', class_='step-details')

            if step_details_td:
                # Extract step name without <pre> content
                for pre in step_details_td.find_all('pre'):
                    failure_reason += '\n' + pre.get_text(strip=True)
                    pre.extract()  # Remove <pre> so it doesn't appear in step name

                step_name = step_details_td.get_text(strip=True)
            else:
                step_name = "Unknown"

            # If "Snapshot below" is in step_name, treat it as part of failure reason
            if 'Snapshot below:' in step_name:
                failure_reason += '\n' + step_name
                step_name = ''

            # Assign the correct step name
            if step_name:
                current_step = step_name

            # Update failure reason mapping
            if current_step:
                if current_step in failed_reason:
                    failed_reason[current_step] += " " + failure_reason.strip()
                else:
                    failed_reason[current_step] = failure_reason.strip()

        # Append extracted data
        for step_name, failure_text in failed_reason.items():
            all_data.append([
                test_name,  # Scenario
                step_name,  # Step Name
                failure_text.strip() if failure_text else "Unknown",  # Failure Reason
                "Error",  # Error Type
                start_time,  # Start Time
                end_time,  # End Time
                exec_time  # Execution Time
            ])

    # Convert to DataFrame
    df = pd.DataFrame(all_data, columns=["Scenario", "Step Name", "Failure Reason", "Error", "Start Time", "End Time",
                                         "Execution Time"])
    df = df.apply(separate_failure_and_error, axis=1)
    df['TCID'] = df['Scenario'].str.extract(r'^(C\d+)')
    # create_table()
    return df
def get_color_code(querystr):
    conn = get_db_connection()
    df = pd.read_sql(querystr,conn=conn)
    print(df)
    conn.close()

@app.route('/upload', methods=['POST'])
def upload_file():
    global last_uploaded_file
    try:

        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        project_name = request.form.get('project_name')
        report_type = request.form.get('report_type')

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            last_uploaded_file = file_path

            file_type = filename.rsplit('.', 1)[1].lower()
            # processed_data = process_file(file_path, file_type)
            if report_type=='Extent Report' and  file_type=='html':
                df = read_extent_report(file_path,project_name,report_type)
            elif report_type=='Allure Report' and  file_type=='json':
                file_full_name = os.path.basename(file_path)
                file_name, filetype = file_full_name.split('.')
                df= read_json_report(file_path,file_name ,file_type ,project_name)
            # df = read_cucumber_report(file_path,project_name,report_type)
            # print(df.columns)
            df['Scenario']=df['Scenario'].replace("'","")
            df['Step Name'] = df['Step Name'].replace("'", "")
            df['Failure Reason'] = df['Failure Reason'].replace("'", "")
            conditions = [
                f""" ('{row['Scenario'].replace("'","") }', '{row['Step Name'].replace("'","")}', '{row['Failure Reason'].replace("'","")}')"""
                for _, row in df.iterrows()
            ]
            # conditions_tuple_list = [tuple(condition.split(", ")) for condition in conditions]

            query = f"""
            SELECT scenario, step_name, failure_reason ,count(*)
            FROM test_cases
            WHERE (scenario, step_name, failure_reason) IN ({', '.join(conditions)})
            group by scenario, step_name, failure_reason ;
            """


            # Fetch existing test cases from PostgreSQL
            existing_test_cases = {}

            # Convert conditions into a list of tuples

            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(query)
                for row in cursor.fetchall():
                    scenario, step, failure_reason, count = row
                    existing_test_cases[(scenario, step, failure_reason)] = count  # Store as dict with count
                conn.close()
            except Exception as e:
                print("Database Error:", e)
                raise e

            # Process and group the data
            grouped = df.groupby('Failure Reason').apply(
                lambda x: sorted(  # Sort descending by count
                    [
                        {
                            "TestCase": scenario,
                            "StepName": f"{step} (Count: {existing_test_cases.get((scenario, step, failure_reason), 0)})",
                            "FailureReason": failure_reason,
                            "Color": "red" if (scenario, step, failure_reason) in existing_test_cases else "black",
                            "Count": existing_test_cases.get((scenario, step, failure_reason), 0)
                            # Store count separately for sorting
                        }
                        for scenario, step, failure_reason in zip(x['Scenario'], x['Step Name'], x['Failure Reason'])
                    ],
                    key=lambda item: item["Count"],  # Sort based on count
                    reverse=True  # Descending order
                )
            ).reset_index()


            processed_data=df.to_dict(orient='records')

            # Insert DataFrame rows into SQLite database
            for _, row in df.iterrows():
                insert_test_case(project_name, report_type,
                                 row["TCID"],
                                 row["Scenario"],
                                 row["Step Name"],
                                 row["Failure Reason"],
                                 row["Error"],
                                 row["Start Time"],
                                 row["End Time"],
                                 row["Execution Time"],
                                 row["Status"]
                                 )

            print(f"Inserted {len(df)} test cases into the database.")


            # Convert to JSON format for frontend
            processed_group_data = [
                {'FailureReason': row['Failure Reason'], 'Details': row[0]}
                for _, row in grouped.iterrows()
            ]
            processed_data = sanitize_data(processed_data)
            processed_group_data = sanitize_data(processed_group_data)
            return jsonify({
                'message': 'File uploaded successfully',
                'processed_data': processed_data
                ,"processed_group_data" :processed_group_data
            })
    except Exception as e:
        print(e)
        return jsonify({"error":"Failed to process the file!, Please try with another report"})


    return jsonify({'error': 'Invalid file type'}), 400


@app.route('/analyze', methods=['POST'])
def analyze():
    global last_uploaded_file
    global project_name

    if not last_uploaded_file:
        return jsonify({'error': 'No file has been uploaded'}), 400

    try:
        file_type = last_uploaded_file.rsplit('.', 1)[1].lower()
        issues = analyze_issues(last_uploaded_file, file_type)

        # Get project details from request
        data = request.json
        project_name = data.get('projectName', '')
        report_type = data.get('reportType', '')

        # You can use project_name and report_type in your analysis if needed

        return jsonify({
            'issues': issues,
            'project': project_name,
            'report_type': report_type
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects', methods=['GET'])
def get_projects():
    try:
        # Implement your logic to fetch projects from your database/storage
        projects = ['Intellihealth','Agadia' ]  # Replace with actual project names
        return jsonify({'projects': projects})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chart-data' ,methods=['POST'])
def get_chart_data():
    project_name = request.form.get('project_name')
    # report_type = request.form.get('report_type')

    print(project_name)
    training_model(project_name)
    file_path = 'confusion_matrix.csv'
    df = pd.read_csv(file_path)
    df['Date'] = pd.to_datetime(df['Date'])

    # Aggregate Data
    actual_counts = df.groupby(['Date', 'Actual'])['Count'].sum().unstack(fill_value=0)
    # print(actual_counts)
    predicted_counts = df[df['Actual'] == df['Predicted']].groupby(['Date', 'Predicted'])['Count'].sum().unstack(
        fill_value=0)
    actual_counts.index = actual_counts.index.astype(str)
    predicted_counts.index = predicted_counts.index.astype(str)
    latest_date = df['Date'].max()
    latest_df = df[df['Date'] == latest_date]
    confusion_matrix = latest_df.pivot_table(index='Actual', columns='Predicted', values='Count',
                                             fill_value=0).reset_index()

    # Convert to JSON format
    data = {
        "dates": actual_counts.index.tolist(),  # Already converted to str
        "actual": {str(k): v for k, v in actual_counts.to_dict(orient="index").items()},
        "predicted": {str(k): v for k, v in predicted_counts.to_dict(orient="index").items()},
        "confusion_matrix": {
            "columns": confusion_matrix.columns.tolist(),
            "data": confusion_matrix.to_dict(orient="records"),
            "latest_date": latest_date.strftime('%Y-%m-%d')
        }
    }
    # Convert to JSON format

    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True,port=8081,host='0.0.0.0')