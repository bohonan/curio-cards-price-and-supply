import os
import copy
import time
import json
import datetime
import requests
from fake_useragent import UserAgent
from utils import google_utils
from utils import web3_utils

ua = UserAgent()

field_name_map = {}

def calcSoldFor(quantity, decimal):
    return float(quantity) / pow(10, decimal)

def getSoldForInTokenCurrentUSDPrice(sold_for_token_quantity, usd_spot_price):
    return '${:,.2f}'.format(sold_for_token_quantity * float(usd_spot_price))

def getLastSoldDate(last_sold_date):
    if not last_sold_date:
        last_sold_date = '01/01/1970 00:00:00'
    return datetime.datetime.strptime(last_sold_date, '%m/%d/%Y %H:%M:%S')

def initFieldNamesMap(field_names_array):
    if len(field_name_map) > 0:
        field_name_map.clear()
    for field_name in field_names_array:
        field_name_map[field_name] = field_name
    return field_name_map

def updateFieldNamesMap(item):
    for key in item:
        field_name_map[key] = key
    return field_name_map

def getAllSales(token_id, wrapped_contract_address, offset, counter):
    last_sale_info = {}
    url = "https://api.opensea.io/api/v1/events?asset_contract_address={0}&token_id={1}&event_type=successful&only_opensea=false&offset={2}&limit=100".format(wrapped_contract_address, token_id, offset)
    headers_dict = {
        "User-Agent": str(ua.random)
    }
    response = requests.get(url, headers=headers_dict)
    if response.ok:
        last_sale_info = response.json()
    else:
        print(response.status_code)
        if counter < 50:
            counter += 1
            time.sleep(10)
            last_sale_info = getAllSales(token_id, wrapped_contract_address, offset, counter)
        else:
            print('Error getting last sale info {0}'.format(response.content))
            raise Exception
    
    return last_sale_info

def buildAssetItem(sale, date_entered):
    item = {}
    item['Token Id'] = sale.get('asset').get('token_id')
    item['Token Name'] = sale.get('asset').get('name')
    item['Date Entered'] = date_entered
    item['Sold Date'] = datetime.datetime.strptime(sale.get('transaction').get('timestamp'), '%Y-%m-%dT%H:%M:%S').strftime('%m/%d/%Y %H:%M:%S')
    item['Sold For Token Quantity'] = calcSoldFor(
        quantity=sale.get('total_price'), 
        decimal=sale.get('payment_token').get('decimals')
    )
    item['Sold For Token'] = sale.get('payment_token').get('symbol')
    item['Sold For Token Current USD Price'] = '${:,.2f}'.format(float(sale.get('payment_token').get('usd_price')))
    item['Sold For USD Price'] = getSoldForInTokenCurrentUSDPrice(
        sold_for_token_quantity=item.get('Sold For Token Quantity'),
        usd_spot_price=sale.get('payment_token').get('usd_price')
    )
    if sale.get('seller').get('user') and sale.get('seller').get('user').get('username'):
        item['Seller\'s Name'] = sale.get('seller').get('user').get('username')
    else:
        item['Seller\'s Name'] = ""
    item['Seller\'s Address'] = sale.get('seller').get('address')
    if sale.get('winner_account').get('user') and sale.get('winner_account').get('user').get('username'):
        item['Buyer\'s Name'] = sale.get('winner_account').get('user').get('username')
    else:
        item['Buyer\'s Name'] = ""
    item['Buyer\'s Address'] = sale.get('winner_account').get('address')

    return item

def processAllSales(allSales, last_sold_date, offset, processing, config_index, config_row, date_entered):
    all_sold = []
    last_sold = None
    for index, sale in enumerate(allSales.get('asset_events')):
        if sale.get('asset') and sale.get('asset').get("token_id") and sale.get('asset_bundle') is None:
            item = buildAssetItem(sale, date_entered)
            updateFieldNamesMap(item)
            if getLastSoldDate(last_sold_date) < getLastSoldDate(item.get('Sold Date')):
                print('Processing token_id {0}...'.format(item.get('Token Id')))
                all_sold.append(item)
                if index == 0 and offset == 0:
                    last_sold = item
                    google_utils.updateLastSoldDate(item.get('Sold Date'), config_index, config_row)
            else:
                processing = False
                if last_sold is None:
                    last_sold = item
                break
    return {
        "all_sold": all_sold,
        "last_sold": last_sold,
        "processing": processing
    }

def getDataFromOpenSeaByLastSaleDate(index, row):
    last_sold = None
    offset = 0
    processing = True
    date_entered = datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S')
    token_id = google_utils.getRowColumnValue(row, 'Token Id')
    wrapped_contract_address = google_utils.getRowColumnValue(row, 'Wrapped Contracted Address')
    last_sold_date = google_utils.getRowColumnValue(row, 'Last Sold Date')
    initFieldNamesMap(google_utils.getFieldNamesFromSheet(os.getenv('GOOGLE_SHEET_SALES_TAB')))

    all_sales = getAllSales(token_id, wrapped_contract_address, offset, 0)
    while processing:
        print('----------------- Get Sales Offset {0}  | Token ID {1} -----------------'.format(offset, token_id))

        processed_results = processAllSales(all_sales, last_sold_date, offset, processing, index, row, date_entered)
        processing = processed_results.get('processing')
        
        google_utils.saveData(processed_results.get('all_sold'), field_name_map, os.getenv('GOOGLE_SHEET_SALES_TAB'))

        if last_sold is None:
            last_sold = processed_results.get('last_sold')

        offset += 100          
        if offset < 10000:
            all_sales = getAllSales(token_id, wrapped_contract_address, offset, 0)
        else:
            break

        if len(all_sales) == 0:
            processing = False
    
    return {
        "data": last_sold,
        "field_name_map": copy.deepcopy(field_name_map)
    }

def getAllTokenOwners(token_id, wrapped_contract_address, cursor, counter):
    owners_info = {}
    payload = {
        "id": "ItemOwnersListQuery",
        "query": "query ItemOwnersListQuery(\n  $archetype: ArchetypeInputType!\n  $count: Int = 20\n  $cursor: String\n) {\n  ...ItemOwnersList_data_1rbxFq\n}\n\nfragment AccountItem_data on AccountType {\n  ...accounts_url\n  imageUrl\n  displayName\n  config\n  address\n  metadata {\n    discordUsername\n    id\n  }\n}\n\nfragment ItemOwnersList_data_1rbxFq on Query {\n  archetype(archetype: $archetype) {\n    asset {\n      assetOwners(after: $cursor, first: $count) {\n        edges {\n          node {\n            relayId\n            quantity\n            owner {\n              ...AccountItem_data\n              id\n            }\n            id\n            __typename\n          }\n          cursor\n        }\n        pageInfo {\n          endCursor\n          hasNextPage\n        }\n      }\n      id\n    }\n  }\n}\n\nfragment accounts_url on AccountType {\n  address\n  user {\n    publicUsername\n    id\n  }\n}\n",
        "variables": {
            "archetype": {
                "assetContractAddress": wrapped_contract_address,
                "chain": "ETHEREUM",
                "tokenId": token_id
            },
            "count": 100,
            "cursor": cursor
        }
    }
    headers_dict = {
        "Content-Type": "application/json",
        "Content-Length": len(payload),
        "origin": "https://opensea.io",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36",
        "x-api-key": "2f6f419a083c46de9d83ce3dbe7db601"
    }
    response = requests.post(os.getenv('OPENSEA_GRAPHQL'), json=payload, headers=headers_dict)
    if response.ok:
        owners_info = response.json()
    else:
        if counter < 50:
            counter += 1
            time.sleep(10)
            owners_info = getAllTokenOwners(token_id, wrapped_contract_address, cursor, counter)
        else:
            print('Error getting last sale info {0}'.format(response.content))
            raise Exception
    
    return owners_info

def getTokenOwners(token_id, wrapped_contract_address):
    total_owners = 0
    offset = 0
    next_page = ''
    processing = True

    all_owners = getAllTokenOwners(token_id, wrapped_contract_address, None, 0)
    while processing:
        print('----------------- Get Owners Offset {0}  | Token ID {1} -----------------'.format(offset, token_id))
        if next_page != all_owners.get('data').get('archetype').get('asset').get('assetOwners').get('pageInfo').get('endCursor'):
            next_page = all_owners.get('data').get('archetype').get('asset').get('assetOwners').get('pageInfo').get('endCursor')

        total_owners += len(all_owners.get('data').get('archetype').get('asset').get('assetOwners').get('edges'))

        offset += 100          
        if offset < 10000:
            all_owners = getAllTokenOwners(token_id, wrapped_contract_address, next_page, 0)
        else:
            break

        if not all_owners.get('data').get('archetype').get('asset').get('assetOwners').get('pageInfo').get('endCursor'):
            processing = False
    
    return total_owners

def buildOwnerSupplyItem(token_id, total_supply, total_owners, date_entered):
    item = {
        "Token Id": token_id,
        "Date Entered": date_entered,
        "Supply On OpenSea": total_supply,
        "Number Of Owners": total_owners
    }
    return item

def getOwnerAndTotalSupply(row):
    date_entered = datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S')
    token_id = google_utils.getRowColumnValue(row, 'Token Id')
    contract_address = google_utils.getRowColumnValue(row, 'Contract Address')
    wrapped_contract_address = google_utils.getRowColumnValue(row, 'Wrapped Contracted Address')
    initFieldNamesMap(google_utils.getFieldNamesFromSheet(os.getenv('GOOGLE_SHEET_SUPPLY_AND_OWNERS_TAB')))
    total_supply = web3_utils.getTotalSupplyAtWrappedContract(contract_address, wrapped_contract_address)
    total_owners = getTokenOwners(token_id, wrapped_contract_address)
    return {
        "data": buildOwnerSupplyItem(token_id, total_supply, total_owners, date_entered),
        "field_name_map": copy.deepcopy(field_name_map)
    }

def getCurioCardsCollection(collection, counter):
    collection_info = {}
    payload = {
    "id": "collectionQuery",
    "query": "query collectionQuery( $collection: CollectionSlug! $collections: [CollectionSlug!] $collectionQuery: String $includeHiddenCollections: Boolean $numericTraits: [TraitRangeType!] $query: String $sortAscending: Boolean $sortBy: SearchSortBy $stringTraits: [TraitInputType!] $toggles: [SearchToggle!] $showContextMenu: Boolean ) { collection(collection: $collection) { isEditable bannerImageUrl name description imageUrl relayId representativeAsset { assetContract { address openseaVersion id } id } ...collection_url ...CollectionHeader_data id } assets: query { ...AssetSearch_data_1bS60n } } fragment AssetCardContent_asset on AssetType { relayId name ...AssetMedia_asset assetContract { address chain openseaVersion id } tokenId collection { slug id } isDelisted } fragment AssetCardContent_assetBundle on AssetBundleType { assetQuantities(first: 18) { edges { node { asset { relayId ...AssetMedia_asset id } id } } } } fragment AssetCardFooter_assetBundle on AssetBundleType { name assetCount assetQuantities(first: 18) { edges { node { asset { collection { name relayId isVerified id } id } id } } } assetEventData { lastSale { unitPriceQuantity { ...AssetQuantity_data id } } } orderData { bestBid { orderType paymentAssetQuantity { ...AssetQuantity_data id } } bestAsk { closedAt orderType dutchAuctionFinalPrice openedAt priceFnEndedAt quantity decimals paymentAssetQuantity { quantity ...AssetQuantity_data id } } } } fragment AssetCardFooter_asset_2V84VL on AssetType { name tokenId collection { name isVerified id } hasUnlockableContent isDelisted isFrozen assetContract { address chain openseaVersion id } assetEventData { firstTransfer { timestamp } lastSale { unitPriceQuantity { ...AssetQuantity_data id } } } decimals orderData { bestBid { orderType paymentAssetQuantity { ...AssetQuantity_data id } } bestAsk { closedAt orderType dutchAuctionFinalPrice openedAt priceFnEndedAt quantity decimals paymentAssetQuantity { quantity ...AssetQuantity_data id } } } } fragment AssetCardHeader_data_27d9G3 on AssetType { relayId favoritesCount isDelisted isFavorite ...AssetContextMenu_data_3z4lq0 @include(if: $showContextMenu) } fragment AssetContextMenu_data_3z4lq0 on AssetType { ...asset_edit_url ...itemEvents_data isDelisted isEditable { value reason } isListable ownership(identity: {}) { isPrivate quantity } creator { address id } collection { isAuthorizedEditor id } } fragment AssetMedia_asset on AssetType { animationUrl backgroundColor collection { displayData { cardDisplayStyle } id } isDelisted displayImageUrl } fragment AssetQuantity_data on AssetQuantityType { asset { ...Price_data id } quantity } fragment AssetSearchFilter_data_1GloFv on Query { ...CollectionFilter_data_tXjHb collection(collection: $collection) { numericTraits { key value { max min } ...NumericTraitFilter_data } stringTraits { key ...StringTraitFilter_data } id } ...PaymentFilter_data_2YoIWt } fragment AssetSearchList_data_gVyhu on SearchResultType { asset { assetContract { address chain id } collection { isVerified id } relayId tokenId ...AssetSelectionItem_data ...asset_url id } assetBundle { relayId id } ...Asset_data_gVyhu } fragment AssetSearch_data_1bS60n on Query { ...CollectionHeadMetadata_data_2YoIWt ...AssetSearchFilter_data_1GloFv ...SearchPills_data_2Kg4Sq search( collections: $collections first: 32 numericTraits: $numericTraits querystring: $query resultType: ASSETS sortAscending: $sortAscending sortBy: $sortBy stringTraits: $stringTraits toggles: $toggles ) { edges { node { ...AssetSearchList_data_gVyhu __typename } cursor } totalCount pageInfo { endCursor hasNextPage } } } fragment AssetSelectionItem_data on AssetType { backgroundColor collection { displayData { cardDisplayStyle } imageUrl id } imageUrl name relayId } fragment Asset_data_gVyhu on SearchResultType { asset { isDelisted ...AssetCardHeader_data_27d9G3 ...AssetCardContent_asset ...AssetCardFooter_asset_2V84VL ...AssetMedia_asset ...asset_url ...itemEvents_data id } assetBundle { ...bundle_url ...AssetCardContent_assetBundle ...AssetCardFooter_assetBundle id } } fragment CollectionFilter_data_tXjHb on Query { selectedCollections: collections( first: 25 collections: $collections includeHidden: true ) { edges { node { assetCount imageUrl name slug id } } } collections( first: 100 includeHidden: $includeHiddenCollections query: $collectionQuery sortBy: SEVEN_DAY_VOLUME ) { edges { node { assetCount imageUrl name slug id __typename } cursor } pageInfo { endCursor hasNextPage } } } fragment CollectionHeadMetadata_data_2YoIWt on Query { collection(collection: $collection) { bannerImageUrl description imageUrl name id } } fragment CollectionHeader_data on CollectionType { name description imageUrl bannerImageUrl ...CollectionStatsBar_data ...SocialBar_data ...verification_data } fragment CollectionModalContent_data on CollectionType { description imageUrl name slug } fragment CollectionStatsBar_data on CollectionType { stats { floorPrice numOwners totalSupply totalVolume id } slug } fragment NumericTraitFilter_data on NumericTraitTypePair { key value { max min } } fragment PaymentFilter_data_2YoIWt on Query { paymentAssets(first: 10) { edges { node { symbol relayId id __typename } cursor } pageInfo { endCursor hasNextPage } } PaymentFilter_collection: collection(collection: $collection) { paymentAssets { symbol relayId id } id } } fragment Price_data on AssetType { decimals imageUrl symbol usdSpotPrice assetContract { blockExplorerLink chain id } } fragment SearchPills_data_2Kg4Sq on Query { selectedCollections: collections( first: 25 collections: $collections includeHidden: true ) { edges { node { imageUrl name slug ...CollectionModalContent_data id } } } } fragment SocialBar_data on CollectionType { discordUrl externalUrl instagramUsername mediumUsername slug telegramUrl twitterUsername ...collection_url } fragment StringTraitFilter_data on StringTraitType { counts { count value } key } fragment asset_edit_url on AssetType { assetContract { address chain id } tokenId collection { slug id } } fragment asset_url on AssetType { assetContract { address chain id } tokenId } fragment bundle_url on AssetBundleType { slug } fragment collection_url on CollectionType { slug } fragment itemEvents_data on AssetType { assetContract { address chain id } tokenId } fragment verification_data on CollectionType { isMintable isSafelisted isVerified }",
    "variables": {
        "collection": collection,
        "collections": [
            collection
        ],
        "collectionQuery": None,
        "includeHiddenCollections": None,
        "numericTraits": None,
        "query": None,
        "sortAscending": None,
        "sortBy": None,
        "stringTraits": None,
        "toggles": None,
        "showContextMenu": True
    }
}
    headers_dict = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36"}
    response = requests.post(os.getenv('OPENSEA_GRAPHQL'), json=payload, headers=headers_dict)
    if response.ok:
        collection_info = response.json()
    else:
        if counter < 50:
            counter += 1
            time.sleep(10)
            collection_info = getCurioCardsCollection(collection, counter)
        else:
            print('Error getting last sale info {0}'.format(response.content))
            raise Exception
    
    return collection_info

def buildCollectionStatsItem(collection_stats, date_entered):
    item = {
        "Date Entered": date_entered,
        "Floor Price": collection_stats.get('floorPrice'),
        "Number Of Owners": collection_stats.get('numOwners'),
        "Total Supply": collection_stats.get('totalSupply'),
        "Total Volume": collection_stats.get('totalVolume')
    }
    return item
def getCollectionStats():
    date_entered = datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S')
    initFieldNamesMap(google_utils.getFieldNamesFromSheet(os.getenv('GOOGLE_SHEET_COLLECTION_STATS_TAB')))
    collection_stats = getCurioCardsCollection("curiocardswrapper", 0).get('data').get('collection').get('stats')
    google_utils.saveData(
        [buildCollectionStatsItem(collection_stats, date_entered)], 
        field_name_map, 
        os.getenv('GOOGLE_SHEET_COLLECTION_STATS_TAB')
    )
    
