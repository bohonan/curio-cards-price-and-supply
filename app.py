import os
import argparse
from utils import google_utils, opensea_utils

def initArgParser():
    global parser
    parser = argparse.ArgumentParser()
    parser.add_argument('app', type=str, help='App to run')

def processSales(index, row):
    print('Processing sales...')
    last_sale = opensea_utils.getDataFromOpenSeaByLastSaleDate(index, row)
    google_utils.sortSheet(os.getenv('GOOGLE_SHEET_SALES_GID'), 3, 0)
    print('Sales processed...')
    return last_sale

def processSupplyAndOwners(row):
    print('Processing supply and owners...')
    supply_and_owner = opensea_utils.getOwnerAndTotalSupply(row)
    print('Supply and owners processed...')
    return supply_and_owner

def processTokens(config_sheet_data, args):
    print('Processing tokens...')
    all_last_sales = []
    last_sales_field_map = {}
    all_supply_and_owners = []
    supply_and_owner_field_map = {}
    for index, row in enumerate(config_sheet_data, start=1):
        if not index == 1:
            row = google_utils.setRowEmptyValues(row)
            if args.app == 'sales' or args.app == 'all':
                last_sale = processSales(index, row)
                all_last_sales.append(last_sale.get('data'))
                last_sales_field_map = last_sale.get('field_name_map')
            if args.app == 'supply_and_owners' or args.app == 'all':
                supply_and_owner = processSupplyAndOwners(row)
                all_supply_and_owners.append(supply_and_owner.get('data'))
                supply_and_owner_field_map = supply_and_owner.get('field_name_map')
                

    if args.app == 'sales' or args.app == 'all':
        google_utils.saveData(
            all_last_sales, 
            last_sales_field_map, 
            os.getenv('GOOGLE_SHEET_LAST_SALES_TAB')
        )
        google_utils.sortSheet(os.getenv('GOOGLE_SHEET_LAST_SALES_GID'), 2, 0)

    if args.app == 'supply_and_owners' or args.app == 'all':
        google_utils.saveData(
            all_supply_and_owners, 
            supply_and_owner_field_map, 
            os.getenv('GOOGLE_SHEET_SUPPLY_AND_OWNERS_TAB')
        )
        google_utils.sortSheet(os.getenv('GOOGLE_SHEET_SUPPLY_AND_OWNERS_GID'), 1, 0)

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
