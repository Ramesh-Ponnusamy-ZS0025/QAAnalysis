import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix,accuracy_score,classification_report
from sklearn.preprocessing import LabelEncoder,MinMaxScaler
from sklearn.preprocessing import OrdinalEncoder
import xgboost as xgb
import numpy as np
from tqdm import tqdm
import db_utils
from configparser import ConfigParser
# from config import Config

# result2 = pd.read_csv(r"C:\Users\dhanalakshmi.t\OneDrive - zucisystems.com\Reports\Proposal\Agadia_PredictiveResults\PredictiveReports\Testcase_level.csv")
config = ConfigParser()
config.read("config.ini")
project_name = config.get('Executions', 'project')
result2 = db_utils.get_data(project_name)
data = result2.drop(['failure_reason', 'error', 'project_name'], axis=1)
unique_dates = data["start_time"].unique()
unique_dates = sorted(unique_dates)

data1 = []
for i in tqdm(range(5, len(unique_dates)),desc="training...."):
    testdate = unique_dates[i]
    
    # data from “2024-02-19” to “2024-03-10” is taken into consideration as traning data
    training_data_1 = data[data["start_time"] < testdate]
    # "2024-03-10" data is taken as test data
    test_data_1 = data[data["start_time"] == testdate]

    training_data = training_data_1.drop(columns="start_time").copy()
    test_data = test_data_1.drop(columns="start_time").copy()

    Y_train = training_data['Execution_status']
    X_train = training_data.drop(columns='Execution_status')
    Y_test = test_data['Execution_status']
    X_test = test_data.drop(columns='Execution_status')

    encoder = OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)
    X_train = encoder.fit_transform(X_train)
    X_test = encoder.transform(X_test)
    label_mapping = {'Failed' : 0  ,  'Passed' : 1 ,'Passedwithwarnings' : 2 , 'Skipped': 3}
    Y_train = [label_mapping[label] for label in Y_train]
    Y_test = [label_mapping[label] for label in Y_test]

    # Training the model
    model = xgb.XGBClassifier()
    model.fit(X_train, Y_train)
    Y_pred = model.predict(X_test)
    probablities = model.predict_proba(X_test)
    max_prob = np.max(probablities,axis =1)
    conf_matrix = confusion_matrix(Y_test, Y_pred)

    # Other metrics
    accuracy = accuracy_score(Y_test, Y_pred)

    class_names = ['Failed', 'Passed', 'Passedwithwarnings', 'Skipped']

    # Create DataFrame
    
    for i, row in enumerate(conf_matrix):
        for j, count in enumerate(row):
            data1.append({'Actual': class_names[i], 'Predicted': class_names[j], 'Count': count, 'Date': testdate,'accuracy': accuracy})
    if testdate == unique_dates[-1]:  # Adjust the condition to use the second last date
        test_data_1['Predicted_Status'] = [class_names[pred] for pred in Y_pred]
        test_data_1['Max_Probability'] = max_prob
        
df_confusion_matrix = pd.DataFrame(data1)
df = pd.DataFrame(test_data_1)
# Display DataFrame
df_confusion_matrix.to_csv("confusion_matrix.csv",index=False)
test_data_1.to_csv("latest_test_data_with_predictions.csv", index=False)
filtered_data = df[(test_data_1['Predicted_Status']=="Passed") & (test_data_1['Execution_status']=="Passed") ]
print(filtered_data)
def filter_latest_predicted_data(predicted, actual):
   print("test" +predicted)
   
   df = pd.DataFrame(test_data_1)
   filtered_data = df[(test_data_1['Predicted_Status']==predicted) & (test_data_1['Execution_status']==actual) ]
   filtered_data.to_csv("filtered_test_data_with_predictions.csv", index=False)