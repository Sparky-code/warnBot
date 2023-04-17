import gspread
from datetime import *
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

 # define the scope
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']

# add credentials to the account
creds = ServiceAccountCredentials.from_json_keyfile_name('beaming-grid-381720-626e34e76cd4.json', scope)

# authorize the clientsheet 
client = gspread.authorize(creds)

# get the instance of the Spreadsheet
sheet = client.open('Warn Data - Current')

# get the first sheet of the Spreadsheet
sheet_instance = sheet.get_worksheet(0)

# get all the records of the data
records_data = sheet_instance.get_all_records()

# convert the json to dataframe
records_df = pd.DataFrame.from_dict(records_data)

# create a value for head() that references the last week of announcements
# now(-7d) > count of rows matching that band > recent = r
start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
end_date = datetime.now().strftime('%Y%m%d')
date_mod = df.astype({'Notice_Date':'int'})
recent_mask = (records_df.astype({'Notice_Date':'int'})['Notice_Date'] > start_date) & (records_df['Notice_Date'] <= end_date)
recent_view = records_df.loc[recent_mask]
print(recent_view)

# notice date may not be right, may need to use received or effective date

# view the top records
records_df.head()

# aggregate number of affected employees by county
recent_announce = records_df.groupby()
regional_count = records_df.groupby(['Notice_Date'])['County'].count().reset_index()
location_cause = records_df.groupby(['Company'])['Layoff_Closure'].count().reset_index()

# get the number of rows for the past week
recent_post = records_data.find('')

# check for existing sheet, if exists then break, else create
create_staging = sheet.add_worksheet(title='Recent Announcements', rows=(80), cols=8)
staging = sheet.get_worksheet(1)

# push the rows identified to a new sheet
staging.insert_rows(records_df.values.tolist())

# use sheet to fill mastadon toots