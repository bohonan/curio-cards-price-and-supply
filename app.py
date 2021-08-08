import os
import argparse
from utils import google_utils, opensea_utils

def initArgParser():
    global parser
    parser = argparse.ArgumentParser()
    parser.add_argument('app', type=str, help='App to run')

def processSales(index, row):
    print('Processing sales...')
    opensea_utils.getDataFromOpenSeaByLastSaleDate(index, row)
    google_utils.sortSheet(os.getenv('GOOGLE_SHEET_SALES_GID'), 3, 0)
    print('Sales processed...')

def processSupplyAndOwners(row):
    print('Processing supply and owners...')
    opensea_utils.getOwnerAndTotalSupply(row)
    google_utils.sortSheet(os.getenv('GOOGLE_SHEET_SUPPLY_AND_OWNERS_GID'), 1, 0)
    print('Supply and owners processed...')

def processTokens(config_sheet_data, args):
    print('Processing tokens...')
    for index, row in enumerate(config_sheet_data, start=1):
        if not index == 1:
            row = google_utils.setRowEmptyValues(row)
            if args.app == 'sales' or args.app == 'all':
                processSales(index, row)
            if args.app == 'supply_and_owners' or args.app == 'all':
                processSupplyAndOwners(row)
    print('Tokens processed')

def processCollectionStats():
    print('Processing collection stats...')
    opensea_utils.getCollectionStats()
    google_utils.sortSheet(os.getenv('GOOGLE_SHEET_COLLECTION_STATS_GID'), 0, 0)
    print('Collection processed...')

def main():
    print('Processing started...')
    initArgParser()
    args = parser.parse_args()
    google_utils.initGoogleServices()
    config_sheet_data = google_utils.getConfigurationSheet()
    if args.app == 'collection_stats' or args.app == 'all':
        processCollectionStats()
    if args.app != 'collection_stats' or args.app == 'all':
        processTokens(config_sheet_data, args)
    print('Processing ended...')

if __name__ == "__main__":
    main()
