#!/usr/bin/env python3
"""
Fixed Nursing Certification PDF Downloader
Key fixes for Google search result parsing and bot detection
"""

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
import random
import os
import urllib.parse
from urllib.parse import urljoin, urlparse
import logging
import sys
from datetime import datetime
import json
import re

# Setup file logging
def setup_file_logging(log_dir):
    """Setup detailed file logging"""
    os.makedirs(log_dir, exist_ok=True)
    
    # Create timestamped log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"nursing_downloader_{timestamp}.log")
    
    # Setup file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Setup formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Setup logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    
    # Suppress console logging
    logging.getLogger().setLevel(logging.CRITICAL)
    
    return logger, log_file

class NursingPDFDownloader:
    def __init__(self, download_dir="nursing_certification_pdfs", delay_range=(2, 5), max_file_size_mb=10):
        """
        Initialize Nursing PDF downloader with improved search parsing
        """
        self.download_dir = download_dir
        self.delay_range = delay_range
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.session = requests.Session()
        
        # Create download directory
        os.makedirs(download_dir, exist_ok=True)
        
        # Setup file logging
        log_dir = os.path.join(download_dir, "logs")
        self.logger, self.log_file = setup_file_logging(log_dir)
        
        self.setup_session()
        self.setup_selenium()
        
        # Statistics tracking
        self.stats = {
            'total_attempted': 0,
            'successful_downloads': 0,
            'skipped_too_large': 0,
            'failed_downloads': 0,
            'total_size_mb': 0
        }
        
        # Progress tracking
        self.current_query = ""
        self.current_file = ""
        self.query_count = 0
        self.total_queries = 0
        
        # Log initialization
        self.logger.info(f"=== Nursing PDF Downloader Initialized ===")
        self.logger.info(f"Download directory: {download_dir}")
        self.logger.info(f"Max file size: {max_file_size_mb} MB")
        self.logger.info(f"Log file: {self.log_file}")
    
    def setup_session(self):
        """Setup requests session with better headers to avoid bot detection"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        })
    
    def setup_selenium(self):
        """Setup Selenium with enhanced stealth options"""
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_argument('--disable-web-security')
        self.chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    def random_delay(self):
        """Add random delay to avoid detection"""
        delay = random.uniform(*self.delay_range)
        time.sleep(delay)
    
    def check_file_size(self, url):
        """Check file size before downloading"""
        try:
            response = self.session.head(url, timeout=10)
            content_length = response.headers.get('content-length')
            if content_length:
                size_bytes = int(content_length)
                size_mb = size_bytes / (1024 * 1024)
                self.logger.info(f"File size: {size_mb:.2f} MB")
                return size_bytes <= self.max_file_size_bytes, size_mb
            else:
                return True, 0
        except Exception as e:
            self.logger.warning(f"Could not check file size for {url}: {e}")
            return True, 0
    
    def extract_google_pdf_links_fixed(self, soup):
        """FIXED: Better extraction of PDF links from Google search results"""
        pdf_links = []
        potential_pages = []
        
        self.logger.info("Starting Google PDF link extraction...")
        
        # Method 1: Look for direct PDF links in various link formats
        all_links = soup.find_all('a', href=True)
        self.logger.info(f"Found {len(all_links)} total links to process")
        
        for link in all_links:
            href = link.get('href', '')
            
            # Handle different Google URL formats
            actual_url = self.extract_actual_url(href)
            if not actual_url:
                continue
                
            # Check for direct PDF links
            if self.is_pdf_link(actual_url):
                pdf_links.append(actual_url)
                self.logger.info(f"Found direct PDF: {actual_url}")
            
            # Collect potential pages that might contain PDFs
            elif self.is_potential_pdf_page(actual_url):
                potential_pages.append(actual_url)
        
        # Method 2: Look for PDF indicators in search result text
        self.logger.info(f"Checking search results for PDF indicators...")
        
        # Updated selectors for current Google layout
        result_selectors = [
            'div.g',           # Classic Google result container
            'div.tF2Cxc',      # Alternative result container
            'div.MjjYud',      # Newer result container
            'div[data-sokoban-container]',  # Another variant
            'div[data-ved]'    # Results with data-ved attribute
        ]
        
        results_found = 0
        for selector in result_selectors:
            results = soup.select(selector)
            if results:
                results_found += len(results)
                self.logger.info(f"Found {len(results)} results with selector: {selector}")
                
                for result in results:
                    # Look for PDF mentions in result text
                    text_content = result.get_text().lower()
                    
                    # Check for PDF indicators
                    pdf_indicators = [
                        'pdf', 'filetype:pdf', '.pdf', 'download pdf',
                        'view pdf', 'full text pdf', 'document pdf'
                    ]
                    
                    if any(indicator in text_content for indicator in pdf_indicators):
                        # Find the main link for this result
                        main_links = result.find_all('a', href=True)
                        
                        for main_link in main_links:
                            href = main_link.get('href', '')
                            actual_url = self.extract_actual_url(href)
                            
                            if actual_url:
                                if self.is_pdf_link(actual_url):
                                    pdf_links.append(actual_url)
                                    self.logger.info(f"Found PDF from result text: {actual_url}")
                                elif self.is_potential_pdf_page(actual_url):
                                    potential_pages.append(actual_url)
        
        self.logger.info(f"Total search results processed: {results_found}")
        
        # Method 3: Check potential pages for PDFs (limit to avoid too many requests)
        unique_potential = list(set(potential_pages))
        self.logger.info(f"Found {len(unique_potential)} potential PDF pages to check")
        
        for i, page_url in enumerate(unique_potential[:8]):  # Limit to 8 pages
            try:
                self.update_progress(f"Checking page {i+1}/8 for PDFs...")
                page_pdfs = self.extract_pdfs_from_page(page_url)
                pdf_links.extend(page_pdfs)
                if page_pdfs:
                    self.logger.info(f"Found {len(page_pdfs)} PDFs on page: {page_url}")
                
                # Delay between page checks
                time.sleep(random.uniform(1, 2))
                
            except Exception as e:
                self.logger.warning(f"Failed to check page {page_url}: {e}")
                continue
        
        # Remove duplicates and return
        unique_pdf_links = list(set(pdf_links))
        self.logger.info(f"Final PDF links found: {len(unique_pdf_links)}")
        
        return unique_pdf_links
    
    def extract_actual_url(self, href):
        """Extract actual URL from Google's various link formats"""
        if not href:
            return None
            
        # Handle Google's /url?q= format
        if href.startswith('/url?q='):
            try:
                # Parse the query parameters
                query_part = href[7:]  # Remove '/url?q='
                actual_url = query_part.split('&')[0]  # Get part before first &
                actual_url = urllib.parse.unquote(actual_url)
                return actual_url
            except:
                return None
        
        # Handle /search?q= (skip these - they're internal Google links)
        elif href.startswith('/search?'):
            return None
        
        # Handle relative URLs (skip these too)
        elif href.startswith('/'):
            return None
        
        # Handle direct HTTP links
        elif href.startswith('http'):
            return href
        
        return None
    
    def is_pdf_link(self, url):
        """Check if URL is likely a direct PDF link"""
        if not url:
            return False
            
        url_lower = url.lower()
        
        # Direct PDF file extensions
        if url_lower.endswith('.pdf'):
            return True
        
        # PDF in URL path or parameters
        if '.pdf' in url_lower:
            return True
        
        # Common PDF download patterns
        pdf_patterns = [
            '/pdf/', '/pdfs/', '/documents/', '/download/',
            'format=pdf', 'type=pdf', 'filetype=pdf'
        ]
        
        return any(pattern in url_lower for pattern in pdf_patterns)
    
    def is_potential_pdf_page(self, url):
        """Check if URL might contain PDFs"""
        if not url:
            return False
            
        url_lower = url.lower()
        
        # Skip obviously non-PDF sites
        skip_domains = [
            'google.com', 'youtube.com', 'facebook.com', 'twitter.com',
            'instagram.com', 'linkedin.com', 'amazon.com', 'ebay.com'
        ]
        
        if any(domain in url_lower for domain in skip_domains):
            return False
        
        # Look for promising indicators
        good_indicators = [
            'repository', 'library', 'docs', 'publications', 'resources',
            'nursing', 'medical', 'health', 'education', '.edu', '.ac.',
            'university', 'college', 'research', 'journal', 'ncbi',
            'pubmed', 'who.int', 'cdc.gov', 'nih.gov'
        ]
        
        return any(indicator in url_lower for indicator in good_indicators)
    
    def search_google_direct_pdfs_fixed(self, query, max_results=15):
        """FIXED: Search Google directly for PDF files with better parsing"""
        self.update_progress("Searching Google for direct PDFs...")
        self.logger.info(f"Starting FIXED Google direct PDF search for: {query}")
        
        # Multiple search variations for better results
        search_variations = [
            f"{query} filetype:pdf",
            f"{query} nursing filetype:pdf",
            f"{query} medical filetype:pdf",
            f"{query} textbook filetype:pdf",
            f"{query} guide filetype:pdf",
            f"{query} handbook filetype:pdf site:edu"
        ]
        
        all_links = []
        
        for i, search_query in enumerate(search_variations, 1):
            try:
                self.update_progress(f"Google PDF search {i}/{len(search_variations)}")
                
                # Search multiple pages for this variation
                variation_links = self.search_google_pages_fixed(search_query, pages=2)
                all_links.extend(variation_links)
                self.logger.info(f"Google variation {i} found {len(variation_links)} PDF links")
                
                if len(all_links) >= max_results:
                    break
                
                # Respectful delay between search variations
                time.sleep(random.uniform(3, 5))
                
            except Exception as e:
                self.logger.error(f"Google PDF search variation {i} failed: {e}")
                continue
        
        unique_links = list(set(all_links))[:max_results]
        self.logger.info(f"Google direct PDF search found {len(unique_links)} unique links")
        
        # Log some example links for debugging
        for i, link in enumerate(unique_links[:5]):
            self.logger.info(f"Example link {i+1}: {link}")
        
        return unique_links
    
    def search_google_pages_fixed(self, search_query, pages=2):
        """FIXED: Search multiple pages of Google results with better parsing"""
        all_links = []
        
        for page in range(pages):
            try:
                # Google pagination: start parameter (0, 10, 20, etc.)
                start = page * 10
                search_url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}&start={start}"
                self.logger.info(f"Google search page {page + 1}: {search_url}")
                
                # Add random delay before request
                time.sleep(random.uniform(1, 3))
                
                response = self.session.get(search_url, timeout=15)
                
                if response.status_code == 200:
                    # Save raw HTML for debugging
                    if page == 0:  # Only save first page
                        debug_file = os.path.join(self.download_dir, f"google_debug_{search_query[:20]}.html")
                        try:
                            with open(debug_file, 'w', encoding='utf-8') as f:
                                f.write(response.text)
                            self.logger.info(f"Saved debug HTML to: {debug_file}")
                        except:
                            pass
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    page_links = self.extract_google_pdf_links_fixed(soup)
                    all_links.extend(page_links)
                    self.logger.info(f"Google page {page + 1} found {len(page_links)} PDF links")
                    
                    # If no results on this page, stop searching further pages
                    if not page_links and page > 0:
                        self.logger.info(f"No results on page {page + 1}, stopping pagination")
                        break
                        
                else:
                    self.logger.warning(f"Google search page {page + 1} failed with status: {response.status_code}")
                    
                    # Try with Selenium if regular request fails
                    if page == 0:  # Only try Selenium for first page
                        self.logger.info("Trying Selenium for first page...")
                        selenium_links = self.selenium_search_fixed(search_url)
                        all_links.extend(selenium_links)
                    
                    break
                
                # Delay between pages
                if page < pages - 1:
                    time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                self.logger.error(f"Google search page {page + 1} failed: {e}")
                
                # Try Selenium as fallback for first page
                if page == 0:
                    try:
                        self.logger.info("Trying Selenium as fallback...")
                        selenium_links = self.selenium_search_fixed(f"https://www.google.com/search?q={urllib.parse.quote(search_query)}")
                        all_links.extend(selenium_links)
                    except:
                        pass
                
                break
        
        return all_links
    
    def selenium_search_fixed(self, search_url):
        """FIXED: Use Selenium with better PDF extraction"""
        self.logger.info("Using Selenium for search")
        
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            
            # Execute script to hide webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            driver.get(search_url)
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Additional wait for dynamic content
            time.sleep(3)
            
            # Get page source and parse
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            pdf_links = self.extract_google_pdf_links_fixed(soup)
            
            self.logger.info(f"Selenium found {len(pdf_links)} PDF links")
            
            driver.quit()
            return pdf_links
            
        except Exception as e:
            self.logger.error(f"Selenium search error: {e}")
            return []
    
    def extract_pdfs_from_page(self, page_url):
        """Extract PDF links from a specific page"""
        pdf_links = []
        
        try:
            response = self.session.get(page_url, timeout=10)
            if response.status_code != 200:
                return pdf_links
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for direct PDF links
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Convert relative URLs to absolute
                if href.startswith('/'):
                    href = urljoin(page_url, href)
                elif not href.startswith('http'):
                    continue
                
                # Check if it's a PDF
                if self.is_pdf_link(href):
                    pdf_links.append(href)
            
            # Look for download buttons or PDF indicators
            for element in soup.find_all(['a', 'button'], href=True):
                text = element.get_text().lower()
                href = element.get('href', '')
                
                if any(word in text for word in ['download', 'pdf', 'view pdf', 'full text']):
                    if href.startswith('/'):
                        href = urljoin(page_url, href)
                    
                    if href.startswith('http') and self.is_pdf_link(href):
                        pdf_links.append(href)
            
            # Look for meta tags
            for meta in soup.find_all('meta'):
                content = meta.get('content', '')
                if self.is_pdf_link(content):
                    if content.startswith('http'):
                        pdf_links.append(content)
                    elif content.startswith('/'):
                        pdf_links.append(urljoin(page_url, content))
                        
        except Exception as e:
            self.logger.error(f"Error extracting PDFs from {page_url}: {e}")
        
        return list(set(pdf_links))
    
    def download_pdf(self, url, filename=None):
        """Download a single PDF file with size checking"""
        self.stats['total_attempted'] += 1
        self.logger.info(f"Attempting to download: {url}")
        
        try:
            # Check file size first
            size_ok, size_mb = self.check_file_size(url)
            if not size_ok:
                self.logger.warning(f"File too large ({size_mb:.2f} MB > {self.max_file_size_bytes/(1024*1024)} MB): {url}")
                self.stats['skipped_too_large'] += 1
                return False
            
            # Generate filename if not provided
            if not filename:
                parsed_url = urlparse(url)
                filename = os.path.basename(parsed_url.path)
                if not filename.endswith('.pdf'):
                    filename += '.pdf'
            
            filepath = os.path.join(self.download_dir, filename)
            self.logger.info(f"Saving as: {filename}")
            
            # Check if file already exists
            if os.path.exists(filepath):
                self.logger.info(f"File already exists: {filename}")
                self.stats['successful_downloads'] += 1  # Count as success
                return True
            
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and not url.lower().endswith('.pdf'):
                self.logger.warning(f"Not a PDF file (content-type: {content_type}): {url}")
                self.stats['failed_downloads'] += 1
                return False
            
            # Download with size checking
            downloaded_size = 0
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    downloaded_size += len(chunk)
                    
                    # Check if file is getting too large
                    if downloaded_size > self.max_file_size_bytes:
                        self.logger.warning(f"File exceeded size limit during download: {url}")
                        f.close()
                        os.remove(filepath)  # Remove partial file
                        self.stats['skipped_too_large'] += 1
                        return False
                    
                    f.write(chunk)
            
            file_size_mb = downloaded_size / (1024 * 1024)
            self.stats['total_size_mb'] += file_size_mb
            self.stats['successful_downloads'] += 1
            
            self.logger.info(f"Successfully downloaded: {filename} ({file_size_mb:.2f} MB)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to download {url}: {e}")
            self.stats['failed_downloads'] += 1
            return False
    
    def download_pdfs_from_search(self, query, max_downloads=10):
        """Search and download PDFs for a specific query using fixed methods"""
        self.current_query = query
        
        # Use the fixed Google search method
        all_links = self.search_google_direct_pdfs_fixed(query, max_downloads)
        
        # Remove duplicates and limit results
        unique_links = list(set(all_links))[:max_downloads]
        self.logger.info(f"Total unique links for '{query}': {len(unique_links)}")
        
        if not unique_links:
            self.update_progress("No PDFs found")
            self.logger.warning(f"No PDF links found for query: {query}")
            return 0
        
        # Download each PDF
        successful_downloads = 0
        for i, link in enumerate(unique_links, 1):
            # Update current file being processed
            self.current_file = os.path.basename(urlparse(link).path)
            self.update_progress(f"Downloading {i}/{len(unique_links)}")
            
            # Generate descriptive filename
            filename = self.generate_filename(query, link, i)
            
            if self.download_pdf(link, filename):
                successful_downloads += 1
                self.update_progress(f"Downloaded {i}/{len(unique_links)}")
            else:
                self.update_progress(f"Failed {i}/{len(unique_links)}")
            
            # Add delay between downloads
            if i < len(unique_links):
                time.sleep(random.uniform(1, 3))
        
        self.current_file = ""
        self.logger.info(f"Query '{query}' completed: {successful_downloads}/{len(unique_links)} downloads successful")
        return successful_downloads
    
    def generate_filename(self, query, url, index):
        """Generate descriptive filename for PDF"""
        # Clean query for filename
        clean_query = "".join(c for c in query if c.isalnum() or c in (' ', '-', '_')).rstrip()
        clean_query = clean_query.replace(' ', '_')
        
        # Get original filename if possible
        parsed_url = urlparse(url)
        original_name = os.path.basename(parsed_url.path)
        
        if original_name and original_name.endswith('.pdf'):
            # Use original name with query prefix
            filename = f"{clean_query}_{index:03d}_{original_name}"
        else:
            # Generate generic filename
            filename = f"{clean_query}_{index:03d}.pdf"
        
        # Ensure filename isn't too long
        if len(filename) > 100:
            filename = filename[:90] + f"_{index:03d}.pdf"
            
        return filename
    
    def update_progress(self, status=""):
        """Update progress display in place"""
        # Clear the line and move cursor to beginning
        sys.stdout.write('\r' + ' ' * 120 + '\r')
        
        # Create progress line
        progress_line = f"Query {self.query_count}/{self.total_queries}: '{self.current_query}' | "
        progress_line += f"Downloads: {self.stats['successful_downloads']} | "
        progress_line += f"Failed: {self.stats['failed_downloads']} | "
        progress_line += f"Size: {self.stats['total_size_mb']:.1f}MB"
        
        if status:
            progress_line += f" | {status}"
        
        if self.current_file:
            progress_line += f" | Current: {self.current_file[:30]}..."
        
        # Truncate if too long
        if len(progress_line) > 120:
            progress_line = progress_line[:117] + "..."
        
        sys.stdout.write(progress_line)
        sys.stdout.flush()
    
    def print_stats(self):
        """Print final download statistics"""
        print(f"\n\n=== FINAL DOWNLOAD STATISTICS ===")
        print(f"Total files attempted: {self.stats['total_attempted']}")
        print(f"Successful downloads: {self.stats['successful_downloads']}")
        print(f"Skipped (too large): {self.stats['skipped_too_large']}")
        print(f"Failed downloads: {self.stats['failed_downloads']}")
        print(f"Total size downloaded: {self.stats['total_size_mb']:.2f} MB")
        if self.stats['successful_downloads'] > 0:
            avg_size = self.stats['total_size_mb'] / self.stats['successful_downloads']
            print(f"Average file size: {avg_size:.2f} MB")

def main():
    """Test the fixed downloader with a single query"""
    print("=== TESTING FIXED PDF DOWNLOADER ===")
    
    # Initialize downloader
    downloader = NursingPDFDownloader(
        download_dir="test_nursing_pdfs", 
        delay_range=(1, 3),
        max_file_size_mb=10.0
    )
    
    # Test with pediatric nursing
    test_query = "pediatric nursing"
    print(f"Testing search for: {test_query}")
    print(f"Log file: {downloader.log_file}")
    
    try:
        downloaded_count = downloader.download_pdfs_from_search(test_query, max_downloads=5)
        print(f"\nTest completed: {downloaded_count} files downloaded")
        
        # Print statistics
        downloader.print_stats()
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        downloader.logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    main()
