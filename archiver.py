import praw
import os
import requests
import json
import zipfile
import socket
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from pathlib import Path

# Global variable to store the authorization code
AUTH_CODE = None

class OAuthHandler(BaseHTTPRequestHandler):
    """Handler for OAuth callback"""
    def do_GET(self):
        global AUTH_CODE
        try:
            query_components = parse_qs(urlparse(self.path).query)
            
            # Extract the authorization code
            AUTH_CODE = query_components["code"][0]
            
            # Send success response to browser
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            response_html = """
            <html>
            <body>
                <h1>Authentication Successful!</h1>
                <p>You can close this window and return to the application.</p>
                <script>window.close()</script>
            </body>
            </html>
            """
            self.wfile.write(response_html.encode('utf-8'))
        except Exception as e:
            print(f"Error in callback handler: {str(e)}")
            self.send_response(500)
            self.end_headers()
            
    def log_message(self, format, *args):
        # Suppress log messages
        return

def find_available_port():
    """Find an available port for the callback server"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def setup_reddit(port):
    """Setup Reddit API connection using OAuth"""
    return praw.Reddit(
        client_id="your_client_id_here",
        client_secret="your_client_secret_here",
        redirect_uri=f"http://localhost:{port}",
        user_agent="SavedPostsExtractor/1.0"
    )

def authenticate_reddit(reddit, port):
    """Handle OAuth authentication"""
    global AUTH_CODE
    
    # Start local server to handle callback
    server = HTTPServer(('localhost', port), OAuthHandler)
    
    # Generate authentication URL
    state = str(hash(datetime.now().strftime("%Y%m%d%H%M%S")))
    auth_url = reddit.auth.url(['history', 'identity'], state, 'permanent')
    
    print("\nOpening browser for Reddit authentication...")
    webbrowser.open(auth_url)
    
    print("Waiting for authentication response...")
    while AUTH_CODE is None:
        server.handle_request()
    
    # Clean up
    server.server_close()
    
    try:
        # Use the authorization code to get the refresh token
        refresh_token = reddit.auth.authorize(AUTH_CODE)
        print("Authentication successful!")
        return True
    except Exception as e:
        print(f"Authentication failed: {str(e)}")
        return False

def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    return "".join(char for char in filename if char.isalnum() or char in (' ', '-', '_')).rstrip()

def download_media(url, directory):
    """Download media from URL"""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if not filename:
                filename = 'media_' + str(hash(url)) + '.jpg'
            
            filepath = os.path.join(directory, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            return filename
    except Exception as e:
        print(f"Failed to download {url}: {str(e)}")
    return None

def extract_saved_posts():
    """Main function to extract saved posts"""
    # Find available port and setup Reddit instance
    port = find_available_port()
    reddit = setup_reddit(port)
    
    # Authenticate user
    if not authenticate_reddit(reddit, port):
        print("Failed to authenticate. Exiting...")
        return
    
    # Create base directory with timestamp
    base_dir = f"reddit_saved_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(base_dir, exist_ok=True)
    
    try:
        # Get saved posts
        print("\nFetching saved posts...")
        saved_posts = list(reddit.user.me().saved(limit=None))
        print(f"Found {len(saved_posts)} saved posts")
        
        for i, post in enumerate(saved_posts, 1):
            try:
                # Create directory for post
                post_title = sanitize_filename(post.title if hasattr(post, 'title') else f'post_{i}')
                post_dir = os.path.join(base_dir, f"{i:04d}_{post_title[:50]}")
                os.makedirs(post_dir, exist_ok=True)
                
                # Extract post data
                post_data = {
                    'title': post.title if hasattr(post, 'title') else 'No Title',
                    'author': str(post.author),
                    'created_utc': datetime.fromtimestamp(post.created_utc).isoformat(),
                    'url': post.url if hasattr(post, 'url') else '',
                    'permalink': f"https://reddit.com{post.permalink}",
                    'subreddit': str(post.subreddit),
                    'type': 'submission' if isinstance(post, praw.models.Submission) else 'comment'
                }
                
                # Handle text content
                if isinstance(post, praw.models.Submission):
                    post_data['selftext'] = post.selftext
                else:
                    post_data['body'] = post.body
                
                # Save post metadata
                with open(os.path.join(post_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
                    json.dump(post_data, f, indent=4, ensure_ascii=False)
                
                # Download media if it's an image post
                if hasattr(post, 'url'):
                    url = post.url.lower()
                    if any(url.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                        downloaded_file = download_media(post.url, post_dir)
                        if downloaded_file:
                            post_data['downloaded_media'] = downloaded_file
                
                print(f"Processed post {i}/{len(saved_posts)}: {post_title}")
                
            except Exception as e:
                print(f"Error processing post {i}: {str(e)}")
                continue
        
        # Create zip archive
        print("\nCreating zip archive...")
        zip_filename = f"{base_dir}.zip"
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(base_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, base_dir)
                    zipf.write(file_path, arcname)
        
        print(f"\nExtraction complete!")
        print(f"Posts have been saved to: {base_dir}")
        print(f"Zip archive created: {zip_filename}")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    extract_saved_posts()
