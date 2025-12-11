# Usage of this directory
Place files in this directory, that follow this pattern

# Filename
"<insta_username>_creds.json"

# Content of the file
{
    "username": "insta_username",
    "password": "insta_password",
    "proxy_url": "proxy_url for instagrapi",
    "delay_range_bottom": 1, # bottom boundary, how many seconds instagrapi should wait between API calls
    "delay_range_top": 4 # top boundary, how many seconds instagrapi should wait between API calls
}
