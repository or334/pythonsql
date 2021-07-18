'''
**SETUP**

Python 3.8+
python -m pip install --upgrade pip
pip install pandas openpyxl
'''

import pandas as pd
import sys, time

#Assuming the ID is not setup for AUTO-INCREMENT.
AUTO_INCREMENT_ID = False
DEBUG = False

def calculateEndTimestamp(tstamp, membership_name):
	membership_name = membership_name.lower()
	#Note the typo: 'montlhy'. Should we fail?
	if membership_name == 'monthly' or membership_name == 'montlhy':
		#add 1 month
		return tstamp + pd.to_timedelta(30,unit='d')
	elif membership_name == 'quaterly':
		#add 3 months
		return tstamp + pd.to_timedelta(90,unit='d')
	elif membership_name == 'yearly':
		#add 1 year
		return tstamp + pd.to_timedelta(365,unit='d')
	print(f"ERROR: Unknown membership_name {membership_name}")
	sys.exit(1)
		
def convertToValuesString(data_array):
	values_list = []
	for v in data_array:
		if type(v) == str:
			v = v.replace("'","''") #in case their name has this special character
			values_list.append(f'"{v}"')
		else:
			values_list.append(f'{v}')
	return '(' + ','.join(str(x) for x in values_list) + ')'

def pre_check_script(USERS_TABLE_DATA, MEMBERSHIP_TABLE_DATA, NEW_USERS_DATA):
	#print(USERS_TABLE_DATA)
	#print(MEMBERSHIP_TABLE_DATA)
	#print(NEW_USERS_DATA)
	#print(USERS_TABLE_DATA.columns)
	#print(MEMBERSHIP_TABLE_DATA.columns)
	#print(NEW_USERS_DATA.columns)
		
	#[ { key : value, ... }, ... ]
	users_dict = USERS_TABLE_DATA.to_dict('records')
	memberships_dict = MEMBERSHIP_TABLE_DATA.to_dict('records')
	new_users_dict = NEW_USERS_DATA.to_dict('records')

	#Verify we read the excel sheet correctly
	if 'id' not in USERS_TABLE_DATA.columns:
		print("ERROR: Could not find **id** column!")
		sys.exit(1)
	if 'email' not in USERS_TABLE_DATA.columns:
		print("ERROR: Could not find **email** column!")
		sys.exit(1)
		
	#checks that there is not the same email in the same file twice
	for new_user in new_users_dict:
		if 'email' not in new_user: continue
		email = new_user['email']
		if NEW_USERS_DATA.email[NEW_USERS_DATA.email == email].count() > 1:
			print(f"ERROR: Same new user's email found: {email}")
			sys.exit(1)
	
	for old_user in users_dict:
		if 'email' not in old_user: continue
		email = old_user['email']
		if USERS_TABLE_DATA.email[USERS_TABLE_DATA.email == email].count() > 1:
			print(f"ERROR: Same user exists more than once in the database: {email}")
			sys.exit(1)
		
	if DEBUG: print("Success: No same user's emails found.")
	
def printSQLCommand(USERS_TABLE_DATA, MEMBERSHIP_TABLE_DATA, NEW_USERS_DATA, CLUB_ID, USERS_TABLE_NAME, MEMBERSHIPS_TABLE_NAME):
	
	#[ { key : value, ... }, ... ]
	users_dict = USERS_TABLE_DATA.to_dict('records')
	memberships_dict = MEMBERSHIP_TABLE_DATA.to_dict('records')
	new_users_dict = NEW_USERS_DATA.to_dict('records')
	
	email_to_id = {}
	#Generate for users table
	#Get all the matching column names
	USER_CNAMES = []
	if not AUTO_INCREMENT_ID:
		USER_CNAMES.append("id")
	for col_a in USERS_TABLE_DATA.columns:
		for col_b in NEW_USERS_DATA.columns:
			if col_a.lower() == col_b.lower() and col_b.lower() not in USER_CNAMES:
				USER_CNAMES.append(col_a.lower())
	if "joined_at" not in USER_CNAMES:
		USER_CNAMES.append("joined_at")
	if "club_id" not in USER_CNAMES:
		USER_CNAMES.append("club_id")
	#If user already exists in the user table, only add their membership!
	TIMESTAMP = pd.to_datetime(int(time.time()),unit='s')
	CUR_ID = USERS_TABLE_DATA['id'].max() + 1
	ALL_NEW_USERS = []
	for new_user in new_users_dict:
		email_to_id[new_user['email']] = CUR_ID
		new_user_values = []
		for c in USER_CNAMES:
			if c in new_user:
				new_user_values.append(new_user[c])
			elif c == "joined_at":
				#Joined today
				new_user_values.append(TIMESTAMP)
			elif c == "club_id":
				new_user_values.append(CLUB_ID)
			elif c == "id":
				new_user_values.append(CUR_ID)
		CUR_ID += 1
		new_user_string = convertToValuesString(new_user_values)
		ALL_NEW_USERS.append(new_user_string)
	ALL_NEW_USERS = ','.join(x for x in ALL_NEW_USERS)
	USER_COLUMNS = ','.join(x for x in USER_CNAMES)
	insert_users = f"INSERT INTO {USERS_TABLE_NAME} ({USER_COLUMNS}) VALUES {ALL_NEW_USERS}"
	print(insert_users)
		
	#Generate for memberships table
	
	#Get all the matching column names
	MEMBERSHIP_CNAMES = []
	if not AUTO_INCREMENT_ID:
		MEMBERSHIP_CNAMES.append("id")
	if "user_id" not in MEMBERSHIP_CNAMES:
		MEMBERSHIP_CNAMES.append("user_id")
	for col_a in MEMBERSHIP_TABLE_DATA.columns:
		for col_b in NEW_USERS_DATA.columns:
			if col_a.lower() == col_b.lower() and col_b.lower() not in MEMBERSHIP_CNAMES:
				MEMBERSHIP_CNAMES.append(col_a.lower())
	if "start_date" not in MEMBERSHIP_CNAMES:
		MEMBERSHIP_CNAMES.append("start_date")
	if "end_date" not in MEMBERSHIP_CNAMES:
		MEMBERSHIP_CNAMES.append("end_date")
		
	CUR_ID = MEMBERSHIP_TABLE_DATA['id'].max() + 1
	ALL_NEW_MEMBERSHIPS = []
	for new_user in new_users_dict:
		if 'membership_name' not in new_user: continue
		new_mem_values = []
		for c in MEMBERSHIP_CNAMES:
			if c in new_user:
				new_mem_values.append(new_user[c])
			elif c == "start_date":
				#Start date is today
				new_mem_values.append(TIMESTAMP)
			elif c == "end_date":
				END_TIMESTAMP = calculateEndTimestamp(TIMESTAMP, new_user['membership_name'])
				new_mem_values.append(END_TIMESTAMP)
			elif c == "user_id":
				#new_user's email must be in the email_to_id map
				new_mem_values.append(email_to_id[new_user['email']])
			elif c == "id":
				new_mem_values.append(CUR_ID)
		CUR_ID += 1
		new_mem_string = convertToValuesString(new_mem_values)
		ALL_NEW_MEMBERSHIPS.append(new_mem_string)
	ALL_NEW_MEMBERSHIPS = ','.join(x for x in ALL_NEW_MEMBERSHIPS)
	MEMBERSHIP_COLUMNS = ','.join(x for x in MEMBERSHIP_CNAMES)
	insert_memberships = f"INSERT INTO {MEMBERSHIPS_TABLE_NAME} ({MEMBERSHIP_COLUMNS}) VALUES {ALL_NEW_MEMBERSHIPS}"
	print(insert_memberships)

def execute(USERS_TABLE_DATA, MEMBERSHIP_TABLE_DATA, NEW_USERS_DATA, CLUB_ID, USERS_TABLE_NAME="users", MEMBERSHIPS_TABLE_NAME="memberships"):
	pre_check_script(USERS_TABLE_DATA, MEMBERSHIP_TABLE_DATA, NEW_USERS_DATA)
	printSQLCommand(USERS_TABLE_DATA, MEMBERSHIP_TABLE_DATA, NEW_USERS_DATA, CLUB_ID, USERS_TABLE_NAME, MEMBERSHIPS_TABLE_NAME)

if __name__ == '__main__':
	#Test1 - Provided Example
	CLUB_ID = 2400 #Gimalia Club in Buenos Aires (which received the ID number 2400)
	NEW_USERS_FILE = "jimalaya.xlsx"
	DATABASE_FILE = "ar_db.xlsx"
	USERS_TABLE_NAME = "users"
	MEMBERSHIPS_TABLE_NAME = "memberships"
	#id	first_name	last_name	phone	email	joined_at	club_id
	USERS_TABLE_DATA = pd.read_excel(DATABASE_FILE, sheet_name=USERS_TABLE_NAME)
	#id	user_id	start_date	end_date	membership_name
	MEMBERSHIP_TABLE_DATA = pd.read_excel(DATABASE_FILE, sheet_name=MEMBERSHIPS_TABLE_NAME)
	#Assume it's a single sheet
	#first_name	last_name	email	phone	membershp_start_date	membership_end_date	membership_name
	NEW_USERS_DATA = pd.read_excel(NEW_USERS_FILE)
	execute(USERS_TABLE_DATA, MEMBERSHIP_TABLE_DATA, NEW_USERS_DATA, CLUB_ID)
	
	#from collections import OrderedDict
	#Test2 - same new users
	#NEW_USERS_DATA = pd.DataFrame( OrderedDict([ ("email", ["dbanarse@msn.com", "dbanarse@msn.com"]) ] ) )
	#execute(USERS_TABLE_DATA, MEMBERSHIP_TABLE_DATA, NEW_USERS_DATA, CLUB_ID)
	
	#Test3 - same user exists in the database more than once
	#USERS_TABLE_DATA = pd.DataFrame( OrderedDict([ ("id", [10, 11]), ("email", ["dbanarse@msn.com", "dbanarse@msn.com"]) ] ) )
	#execute(USERS_TABLE_DATA, MEMBERSHIP_TABLE_DATA, NEW_USERS_DATA, CLUB_ID)
	
	
	

















