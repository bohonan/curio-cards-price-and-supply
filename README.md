# OpenSea API Data Pull For Curio Cards

```bash
.
├── utils                       <-- Source code utility classes
│   ├── google_utils.py         <-- Utility to help with google functions
│   └── opensea_utils.py        <-- Utility to help with opensea functions
│   └── web3_utils.py           <-- Utility to help with web3 functions
├── .gitignore                  <-- Dev SAM Template
├── app.py                      <-- main code
├── README.md                   <-- Instructions file
├── requirements.txt            <-- package requirements
└── runtime.txt                 <-- runtime for app
```

## About

This app was created to pull data from Opensea and insert it into a Google Sheet.  This data can then be used in Google Data Studio for analytics.

## Getting Started

### Requirements

- [Python 3 installed](https://www.python.org/downloads/)
- [pip installed](https://pip.pypa.io/en/stable/cli/pip_install/)
- [Google Service Account with Google Drive and Google Sheets API enabled](https://console.cloud.google.com/)
- Googe Drive folder to store Google Sheets
- Google Sheet in folder with tabs for Configuration, Curio Sales, Curio Supply and Owners, Curio Collection Stats

### Installation

1. Clone the repo

   ```bash
   git clone https://github.com/bohonan/opensea_data_pull.git
   ```

2. Install package requirements

   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables

    For any environment running this app the following environment variables must be configured
    - GOOGLE_SHEET_ID - The ID of main sheet in Google Sheets being used
    - GOOGLE_DRIVE_FOLDER_ID - The ID of the folder in Google Drive
    - GOOGLE_SERVICE_ACCOUNT_B64 - The google service account json in base64 format
    - GOOGLE_SHEET_CONFIG_TAB - The name of the configuration tab in the Google Sheet
    - GOOGLE_SHEET_SALES_TAB - The name of the sales tab in the Google Sheet
    - GOOGLE_SHEET_SUPPLY_AND_OWNERS_TAB - The name of the supply and owners tab in the Google Sheet
    - GOOGLE_SHEET_COLLECTION_STATS_TAB - The name of the collection stats tab in the Google Sheet
    - GOOGLE_SHEET_SALES_GID - The ID of the sales tab in the Google Sheet
    - GOOGLE_SHEET_SUPPLY_AND_OWNERS_GID - The ID of the supply and owners tab in the Google Sheet
    - GOOGLE_SHEET_COLLECTION_STATS_GID - The ID of the collection stats tab in the Google Sheet
    - OPENSEA_GRAPHQL - <https://api.opensea.io/graphql/>

## Usage

### Run Command

```bash
    python app.py all
```

```bash
    python app.py sales
```

```bash
    python app.py supply_and_owners
```

```bash
    python app.py collection_stats
```

## Contact

Tom Bohonan - bohonan@gmail.com
