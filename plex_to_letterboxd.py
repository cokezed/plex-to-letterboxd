#!/usr/bin/env python3
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount
import csv
from datetime import datetime
import configparser
import os
import logging
from logging.handlers import RotatingFileHandler
import glob
import shutil

class PlexToLetterboxd:
    def __init__(self):
        # Get the directory where the script is located
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.setup_logging()
        logging.info("=== Starting Plex to Letterboxd Export ===")
        logging.info(f"Script started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Read config
        self.config = self.load_config()
        
        # Connect to Plex
        try:
            auth_method = self.config.get('Plex', 'auth_method', fallback='direct')
            
            if auth_method == 'direct':
                self.baseurl = self.config.get('Plex', 'baseurl', fallback='http://localhost:32400')
                self.token = self.config.get('Plex', 'token')
                if not self.token:
                    raise ValueError("Plex token not found in config file. Please add your token to the config file.")
                self.plex = PlexServer(self.baseurl, self.token)
                logging.info(f"Successfully connected to Plex server at {self.baseurl} using direct authentication")
            
            elif auth_method == 'account':
                username = self.config.get('Plex', 'username')
                password = self.config.get('Plex', 'password')
                servername = self.config.get('Plex', 'servername')
                
                if not all([username, password, servername]):
                    raise ValueError("Username, password, and servername are required for account authentication")
                
                logging.info(f"Attempting to connect to Plex server '{servername}' using account credentials")
                account = MyPlexAccount(username, password)
                self.plex = account.resource(servername).connect()
                logging.info("Successfully connected using Plex account authentication")
            
            else:
                raise ValueError(f"Invalid auth_method in config: {auth_method}")
                
        except Exception as e:
            logging.error(f"Failed to connect to Plex server: {str(e)}")
            raise

    def setup_logging(self):
        # Create formatters
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # Setup file handler with rotation
        log_file = os.path.join(self.script_dir, 'output.log')
        file_handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)  # Capture all logs in file
        
        # Setup console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)  # Only INFO and above for console
        
        # Create a filter for the console handler
        class ExcludeMovieLogsFilter(logging.Filter):
            def filter(self, record):
                # Exclude logs about processing individual movies
                return not any(x in record.msg for x in [
                    "Processed movie:",
                    "Error processing movie"
                ])
        
        console_handler.addFilter(ExcludeMovieLogsFilter())
        
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)  # Capture all logs
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

    def load_config(self):
        config = configparser.ConfigParser()
        config_path = os.path.join(self.script_dir, 'config.ini')
        
        try:
            # Create config if it doesn't exist
            if not os.path.exists(config_path):
                config['Plex'] = {
                    'auth_method': 'direct',
                    'baseurl': 'http://replace_me:32400', #windows threw a fit about localhost, put in real ip 
                    'token': '',  # Token should be added to config file manually
                    'username': '',
                    'password': '',
                    'servername': 'replace_me'
                }
                with open(config_path, 'w') as f:
                    config.write(f)
                logging.error(f"Config file not found. Created new config.ini at {config_path} - please edit with your Plex credentials")
                exit(1)
                
            config.read(config_path)
            logging.info("Successfully loaded config file")
            return config
        except Exception as e:
            logging.error(f"Error loading config: {str(e)}")
            raise

    def get_watch_history(self):
        try:
            # Get movie library
            movie_lib = self.plex.library.section('Movies')
            logging.info("Successfully connected to Movies library")
            
            # Get watched movies
            watched_movies = []
            processed_count = 0
            total_movies = len(movie_lib.search(unwatched=False))
            
            print(f"Starting to process {total_movies} movies...")
            logging.info(f"Starting to process {total_movies} movies...")
            
            # Calculate thresholds for 20%, 40%, 60%, 80%, 100%
            progress_thresholds = [int(total_movies * x/100) for x in range(20, 101, 20)]
            
            for movie in movie_lib.search(unwatched=False):
                try:
                    # Get basic movie info
                    movie_data = {
                        'Title': movie.title,
                        'Year': movie.year,
                        'imdbID': '',
                        'tmdbID': '',
                        'WatchedDate': '',
                        'Rating': '',
                    }
                    
                    # Extract IMDb and TMDb IDs from guid
                    if movie.guid:
                        if 'imdb://' in movie.guid:
                            movie_data['imdbID'] = movie.guid.split('//')[1].split('?')[0]
                        elif 'tmdb://' in movie.guid:
                            movie_data['tmdbID'] = movie.guid.split('//')[1].split('?')[0]
                        
                        # Try to get IDs from movie extras
                        for guid in movie.guids:
                            if 'imdb://' in guid.id and not movie_data['imdbID']:
                                movie_data['imdbID'] = guid.id.split('//')[1]
                            elif 'tmdb://' in guid.id and not movie_data['tmdbID']:
                                movie_data['tmdbID'] = guid.id.split('//')[1]
                    
                    # Get watch date from history
                    history = movie.history()
                    if history:
                        latest_watch = max(history, key=lambda x: x.viewedAt)
                        movie_data['WatchedDate'] = latest_watch.viewedAt.strftime('%Y-%m-%d')
                    
                    # Get user rating if available
                    if movie.userRating:
                        movie_data['Rating'] = str(movie.userRating / 2)
                    
                    watched_movies.append(movie_data)
                    
                    # Log detailed movie info to debug (file only)
                    logging.debug(f"Processed movie: {movie.title} ({movie.year}) - IMDb: {movie_data['imdbID']}, TMDb: {movie_data['tmdbID']}")
                    
                    # Update and log progress at thresholds
                    processed_count += 1
                    if processed_count in progress_thresholds:
                        progress_percentage = (processed_count / total_movies) * 100
                        msg = f"Progress: {processed_count}/{total_movies} movies processed ({progress_percentage:.0f}%)"
                        print(msg)
                        logging.info(msg)
                    
                except Exception as e:
                    error_msg = f"Error processing movie {movie.title}: {str(e)}"
                    print(f"ERROR: {error_msg}")
                    logging.error(error_msg)
                    continue
            
            final_msg = f"Completed processing {processed_count} movies"
            print(final_msg)
            logging.info(final_msg)
            return watched_movies
            
        except Exception as e:
            error_msg = f"Error getting watch history: {str(e)}"
            print(f"ERROR: {error_msg}")
            logging.error(error_msg)
            raise

    def load_master_file(self, master_file='letterboxd_master.csv'):
        """Load the master file if it exists, return empty list if it doesn't"""
        try:
            if os.path.exists(master_file):
                with open(master_file, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    return list(reader)
            return []
        except Exception as e:
            logging.error(f"Error loading master file: {str(e)}")
            raise

    def get_differential_changes(self, new_movies, master_movies):
        """Compare new movies against master list to find changes"""
        master_dict = {(m['Title'], m['Year'], m['WatchedDate']): m for m in master_movies if m['WatchedDate']}
        
        # Find new or updated entries
        changes = []
        for movie in new_movies:
            if not movie['WatchedDate']:
                continue
                
            key = (movie['Title'], movie['Year'], movie['WatchedDate'])
            master_entry = master_dict.get(key)
            
            # Add to changes if:
            # 1. Movie not in master
            # 2. Movie in master but rating changed
            if not master_entry or master_entry['Rating'] != movie['Rating']:
                changes.append(movie)
                
        return changes

    def sanitize_string(self, text):
        """
        Sanitize strings for CSV output according to Letterboxd requirements:
        - Strings containing commas must be quoted
        - Quotes within quoted text must be escaped with backslash
        - No spaces after commas
        """
        if text is None:
            return ''
        
        # Convert to string and strip whitespace
        text = str(text).strip()
        
        # If text contains quotes, escape them with backslash
        if '"' in text:
            text = text.replace('"', '\\"')
            
        return text

    def write_csv_file(self, filename, movies, fields):
        """Write movies to CSV file following Letterboxd's strict formatting requirements"""
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                # Write header without spaces after commas
                header = ','.join(fields) + '\n'
                f.write(header)
                
                # Write each movie entry
                for movie in movies:
                    row_values = []
                    for field in fields:
                        value = self.sanitize_string(movie.get(field, ''))
                        # Quote values containing commas or escaped quotes
                        if ',' in value or '\\"' in value:
                            value = f'"{value}"'
                        row_values.append(value)
                    
                    # Join with commas, no spaces
                    row = ','.join(row_values) + '\n'
                    f.write(row)
            
            return True
        except Exception as e:
            logging.error(f"Error writing CSV file {filename}: {str(e)}")
            raise

    def export_to_csv(self, movies, output_file='letterboxd_import.csv'):
        try:
            # Split movies into watched and unwatched
            watched_movies = [m for m in movies if m['WatchedDate']]
            unwatched_movies = [m for m in movies if not m['WatchedDate']]
            
            # Sort watched movies by date descending
            watched_movies.sort(key=lambda x: x['WatchedDate'], reverse=True)
            
            # Define fields based on Letterboxd format
            fields = ['Title','Year','imdbID','tmdbID','WatchedDate','Rating']
            
            # Load master file
            master_file = os.path.join(self.script_dir, 'letterboxd_master.csv')
            master_movies = self.load_master_file(master_file)
            
            # Get differential changes
            changes = self.get_differential_changes(watched_movies, master_movies)
            
            # Update master file with all watched movies
            if watched_movies:
                self.write_csv_file(master_file, watched_movies, fields)
                logging.info(f"Updated master file with {len(watched_movies)} movies")
            
            # Export differential changes with datestamp
            if changes:
                date_stamp = datetime.now().strftime('%Y-%m-%d')
                changes_file = os.path.join(
                    self.script_dir,
                    output_file.replace('.csv', f'_watched-{date_stamp}.csv')
                )
                self.write_csv_file(changes_file, changes, fields)
                logging.info(f"Exported {len(changes)} new/updated movies to {changes_file}")
            else:
                logging.info("No new changes to export")
            
            # Export unwatched movies
            if unwatched_movies:
                unwatched_file = os.path.join(
                    self.script_dir,
                    output_file.replace('.csv', '_unwatched.csv')
                )
                self.write_csv_file(unwatched_file, unwatched_movies, fields)
                logging.info(f"Exported {len(unwatched_movies)} unwatched movies to {unwatched_file}")
            
            logging.info(f"Total movies processed: {len(movies)}")
            
        except Exception as e:
            logging.error(f"Error exporting to CSV: {str(e)}")
            raise

    def archive_logs(self):
        """Move all output.log.* files to the old_logs directory"""
        try:
            # Create old_logs directory if it doesn't exist
            old_logs_dir = os.path.join(self.script_dir, 'old_logs')
            os.makedirs(old_logs_dir, exist_ok=True)
            
            # Get all output.log files
            log_pattern = os.path.join(self.script_dir, 'output.log*')
            log_files = glob.glob(log_pattern)
            
            # Move each log file
            for log_file in log_files:
                if os.path.basename(log_file) == 'output.log':
                    continue  # Skip current log file
                    
                dest_file = os.path.join(old_logs_dir, os.path.basename(log_file))
                try:
                    # If destination exists, append timestamp to filename
                    if os.path.exists(dest_file):
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        base, ext = os.path.splitext(dest_file)
                        dest_file = f"{base}_{timestamp}{ext}"
                    
                    shutil.move(log_file, dest_file)
                    logging.debug(f"Moved {log_file} to {dest_file}")
                except Exception as e:
                    logging.error(f"Failed to move {log_file}: {str(e)}")
            
            logging.info("Log files archived")
            
        except Exception as e:
            logging.error(f"Error archiving logs: {str(e)}")

    def write_to_csv(self, movies, output_file):
        """Write movies to CSV file."""
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            # Write header
            writer.writerow(['Title', 'Year', 'Rating10'])
            
            for movie in movies:
                # Escape double quotes in title with backslash
                escaped_title = movie['title'].replace('"', '\\"')
                writer.writerow([escaped_title, movie['year'], movie['rating']])

def main():
    try:
        exporter = PlexToLetterboxd()
        movies = exporter.get_watch_history()
        exporter.export_to_csv(movies)
        exporter.archive_logs()  # Archive logs at end of successful run
        logging.info(f"Script completed successfully at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info("=== Export Complete ===\n")
    except Exception as e:
        logging.error(f"Script failed: {str(e)}")
        logging.info("=== Export Failed ===\n")

if __name__ == "__main__":
    main() 