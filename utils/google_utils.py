import os
import time
import json
import base64
from googleapiclient.discovery import build
from google.oauth2 import service_account

config_sheet_columns_to_index_map = {}

def getGoogleCreds():
    return service_account.Credentials.from_service_account_info(json.loads(base64.b64decode(os.getenv('GOOGLE_SERVICE_ACCOUNT_B64')).decode('utf-8')))

def getGoogleService(service_name, version, creds):
    return build(service_name, version, credentials=creds)

def initGoogleServices():
    print('Initializing google services...')
    global drive_service, sheets_service
    creds = getGoogleCreds()
    drive_service = getGoogleService('drive', 'v3', creds)
    sheets_service = getGoogleService('sheets', 'v4', creds)
    print('Google services intialized')

def createColumnToIndexMapping(row):
    for index, column in enumerate(row):
        config_sheet_columns_to_index_map[column] = index
    return config_sheet_columns_to_index_map

def getRowColumnValue(row, column_name):
    return row[config_sheet_columns_to_index_map.get(column_name)]

def setRowEmptyValues(row):
    while len(row) < len(config_sheet_columns_to_index_map.keys()):
        row.append("")
    return row

def updateConfigSheet(index, row, counter):
    results = {}

    values = [
        row
    ]
    body = {
        'values': values
    }

    try:
        results = sheets_service.spreadsheets().values().update(
            spreadsheetId=os.getenv('GOOGLE_SHEET_ID'), range="{0}!A{1}".format(os.getenv('GOOGLE_SHEET_CONFIG_TAB'), index),
            valueInputOption='RAW', body=body).execute()
    except:
        if counter < 50:
            counter += 1
            time.sleep(1)
            results = updateConfigSheet(index, row, counter)
        else:
            print('Error updating config')
            raise

    return results

def appendDataToSheet(data, tab, counter):
    results = {}
    try: 
        body = {
            'values': data
        }
        results = sheets_service.spreadsheets().values().append(
            spreadsheetId=os.getenv('GOOGLE_SHEET_ID'), 
            range="{0}!A1".format(tab),
            valueInputOption='RAW', 
            insertDataOption='INSERT_ROWS', 
            body=body
        ).execute()
    except:
        if counter < 50:
            counter += 1
            time.sleep(10)
            results = appendDataToSheet(data, tab, counter)
        else:
            print('Error appending data')
            raise
    return results

def getConfigurationSheet():
    print('Loading main sheet...')
    result = sheets_service.spreadsheets().values().get(
    spreadsheetId=os.getenv('GOOGLE_SHEET_ID'), range=os.getenv('GOOGLE_SHEET_CONFIG_TAB')).execute()
    createColumnToIndexMapping(result.get('values', [])[0])
    print('Configuration sheet loaded')
    return result.get('values', [])

def getFieldNamesFromSheet(tab):
    print('Loading field names sheet...')
    field_names = []
    result = sheets_service.spreadsheets().values().get(
    spreadsheetId=os.getenv('GOOGLE_SHEET_ID'), range=tab).execute()
    if len(result.get('values', [])) > 0:
        field_names = result.get('values', [])[0]
    print('Configuration field names loaded')
    return field_names

def addDataToSheet(data, tab):
    print('Adding data to sheet...')
    records = []

    for info in data.get('data'):
        record = []
        for field_name in list(data.get('field_names').keys()):
            record.append(info.get(field_name))
        records.append(record)

    appendDataToSheet(records, tab, 0)
    print('Data added to sheet')

def sortSheet(gid, dimension_index, counter):
    results = {},

    request = {
        "requests": [
            {
                "sortRange": {
                    "range": {
                        "sheetId": gid,
                        "startRowIndex": 1,
                        "startColumnIndex": 0
                    },
                    "sortSpecs": [
                        {
                            'dimensionIndex': dimension_index,
                            "sortOrder": "DESCENDING"
                        }
                    ]
                }
            }
        ]
    }

    try:
        results = sheets_service.spreadsheets().batchUpdate(body=request, spreadsheetId=os.getenv('GOOGLE_SHEET_ID')).execute()
    except:
        if counter < 50:
            counter += 1
            time.sleep(1)
            results = sortSheet(gid, dimension_index, counter)
        else:
            print('Error sorting sheet by sold date')
            raise
    
    return results

def updateLastSoldDate(last_sold_date, index, row):
    if last_sold_date:
        row[config_sheet_columns_to_index_map.get('Last Sold Date')] = last_sold_date
        updateConfigSheet(index, row, 0)

def saveData(data, field_name_map, tab):
    data = {
        'data': data,
        'field_names': field_name_map
    }
    addDataToSheet(data, tab)