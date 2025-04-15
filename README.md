# Plex to Letterboxd

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)

A Python script that syncs your Plex movie watch history and ratings with Letterboxd by generating a CSV file compatible with Letterboxd's import format.

> **Note**: This script was developed with the assistance of Cursor AI. While it has been tested and works as described, it was created as a quick solution to a specific need - YMMV.

## Features

- Exports recently watched movies from Plex to Letterboxd-compatible CSV format
- Includes watch dates and ratings
- Supports both direct Plex server connection and Plex account authentication
- Maintains a master list to track changes and avoid duplicates
- Includes both IMDb and TMDb IDs when available
- Detailed logging with rotation

## Prerequisites

- Python 3.6 or higher
- A Plex server with a movie library (likely plex pass but i'm not sure)
- A Letterboxd account (free or pro)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/plex-to-letterboxd.git
   cd plex-to-letterboxd
   ```

2. Install required packages:
   ```bash
   pip3 install -r requirements.txt
   ```

3. Configure your Plex connection by copying the example config file:
   ```bash
   cp config.ini.example config.ini
   ```
   
4. Edit the config.ini file with your Plex details:
   ```ini
   [Plex]
   # Authentication method: 'direct' or 'account'
   auth_method = direct

   # For direct authentication
   baseurl = http://your-plex-server:32400
   token = your-plex-token

   # For account authentication
   #username = your-username
   #password = your-password
   #servername = your-server-name
   ```

## Usage

1. Run the script:
   ```bash
   python3 plex_to_letterboxd.py
   ```

2. The script will:
   - Connect to your Plex server
   - Fetch your watched movies history
   - Generate a CSV file named `letterboxd_import_watched-YYYY-MM-DD.csv`
   - Maintain a master list in `letterboxd_master.csv`
   - Create detailed logs in `output.log`

3. Import the generated CSV file into Letterboxd:
   - Go to your Letterboxd Settings
   - Select "Import & Export"
   - Upload the generated CSV file

## File Structure

- `plex_to_letterboxd.py`: Main script containing the sync logic
- `config.ini`: Configuration file for Plex connection details
- `letterboxd_master.csv`: Master list of all exported movies
- `output.log`: Detailed log file
- `old_logs/`: Directory containing archived log files

## Configuration

### Finding Your Plex Token
To use direct authentication, you'll need to find your Plex authentication token. Follow these steps:

1. Sign in to your Plex account in Plex Web App
2. Browse to any library item
3. View the page source (CTRL+U)
4. Search for "X-Plex-Token"
5. Copy the token value

For more detailed instructions, see the [official Plex guide](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/).

**Note**: This token is "temporary." If you're developing a tool that needs permanent authentication, please refer to Plex's third-party development forum.

### Direct Authentication
1. Set in config.ini:
   ```ini
   auth_method = direct
   baseurl = http://your-plex-server:32400
   token = your-plex-token
   ```

### Account Authentication
1. Set in config.ini:
   ```ini
   auth_method = account
   username = your-plex-username
   password = your-plex-password
   servername = your-plex-server-name
   ```

## Dependencies

- `plexapi`: For connecting to Plex
- Other standard Python libraries:
  - `csv`
  - `configparser`
  - `datetime`
  - `logging`
  - `os`
  - `shutil`
  - `glob`

## Logging System

The script includes a comprehensive logging system that helps track operations and troubleshoot issues:

### Log Files
- **output.log**: The main log file containing detailed information about the current run
- **output.log.1, output.log.2, etc.**: Rotated log files from previous runs (created automatically)
- **old_logs/**: Directory containing archived log files

### Log Levels
- **DEBUG**: Detailed information, including all processed movies (only in log files)
- **INFO**: General operational messages (console and log files)
- **ERROR**: Issues that might prevent proper operation (console and log files)

The log system automatically:
- Rotates logs when they reach 1MB in size
- Maintains up to 5 backup log files before rotation
- Archives older log files to the `old_logs/` directory at the end of each successful run
- Adds timestamps to avoid overwriting archived logs with the same name

For normal usage, you can monitor progress in the console, while the detailed logs in `output.log` provide complete information if you need to troubleshoot issues.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

