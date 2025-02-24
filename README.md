# redditsavedpostextractor
Extract Posts from your Saved Posts and saves them as files. It automatically zips those files.

## Features

- Authenticates with Reddit using OAuth
- Fetches all saved posts from your Reddit account
- Saves post metadata and content to individual files
- Downloads media (images) associated with posts
- Creates a zip archive of all saved posts

## Requirements

- Python 3.x
- `praw` library
- `requests` library

## Installation

1. Clone the repository:
    git clone https://github.com/yourusername/redditsavedpostextractor.git
   
    cd redditsavedpostextractor

2. Install the required libraries:
    pip install praw requests

## Usage

1. Run the script:
    python archiver.py

2. The script will open a browser window for Reddit authentication. Log in and authorize the application.

3. The script will fetch your saved posts, download any associated media, and save them to a directory with a timestamp.

4. A zip archive of the saved posts will be created in the same directory.

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](https://github.com/jayjay3108/redditsavedpostextractor/blob/main/LICENSE) file for details.
