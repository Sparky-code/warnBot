# import create_msg
# import sheets_ctrl
import tempfile
import shutil
import pandas as pd


# create temp folder locally
fp = tempfile.mkdtemp()

# URL for California WARN data 
# TO DO - Create a dynamic way to check and pull most recent year
url = "https://edd.ca.gov/siteassets/files/jobs_and_training/warn/warn_report.xlsx"

# convert to dataframe > csv
df = pd.DataFrame(pd.read_excel(url))
temp_file = fp + '/warn_report.csv'
cf = df.to_csv(temp_file, sep=',')

# pull a reference to sheets_ctrl (google-sheets)

# create a diff between cf and google-sheets

# save the diff as message-staging

# format the diff to make messages useful

# call create_message (for each announcement? each weeks? - based on number)
# confirm posting(s)

#remove temp dir
shutil.rmtree(fp)