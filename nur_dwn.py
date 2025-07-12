#!/usr/bin/env python3
"""
Nursing Certification PDF Downloader
Downloads nursing certification course PDFs with file size limits
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
        Initialize Nursing PDF downloader
        
        Args:
            download_dir: Directory to save PDFs
            delay_range: Random delay between requests (min, max) seconds
            max_file_size_mb: Maximum file size in MB
        """
        self.download_dir = download_dir
        self.delay_range = delay_range
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024  # Convert MB to bytes
        self.session = requests.Session()
        
        # Create download directory
        os.makedirs(download_dir, exist_ok=True)
        
        # Setup file logging
        log_dir = os.path.join(download_dir, "logs")
        self.logger, self.log_file = setup_file_logging(log_dir)
        
        self.setup_session()
        self.setup_selenium()
        
        # Bot detection keywords
        self.bot_indicators = [
            "captcha", "robot", "verify", "human", "recaptcha",
            "cloudflare", "access denied", "blocked", "403", "bot detection"
        ]
        
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
        """Setup requests session with realistic headers"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def setup_selenium(self):
        """Setup Selenium with stealth options"""
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    
    def random_delay(self):
        """Add random delay to avoid detection"""
        delay = random.uniform(*self.delay_range)
        time.sleep(delay)
    
    def is_bot_challenge(self, content):
        """Check if page contains bot detection challenge"""
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in self.bot_indicators)
    
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
                # If no content-length header, we'll check during download
                return True, 0
        except Exception as e:
            self.logger.warning(f"Could not check file size for {url}: {e}")
            return True, 0
    
    def search_duckduckgo(self, query, max_results=20):
        """Search DuckDuckGo for PDFs"""
        self.update_progress("Searching DuckDuckGo...")
        self.logger.info(f"Starting DuckDuckGo search for: {query}")
        
        # Try multiple search variations
        search_variations = [
            f"{query} filetype:pdf",
            f"{query} nursing filetype:pdf",
            f"{query} medical filetype:pdf",
            f"{query} textbook filetype:pdf site:edu"
        ]
        
        all_links = []
        
        for i, search_query in enumerate(search_variations, 1):
            try:
                self.update_progress(f"DuckDuckGo variation {i}/{len(search_variations)}")
                search_url = f"https://duckduckgo.com/?q={urllib.parse.quote(search_query)}"
                self.logger.info(f"DuckDuckGo search URL: {search_url}")
                
                response = self.session.get(search_url, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    pdf_links = self.extract_pdf_links(soup, "https://duckduckgo.com")
                    all_links.extend(pdf_links)
                    self.logger.info(f"DuckDuckGo variation {i} found {len(pdf_links)} links")
                    
                    if len(all_links) >= max_results:
                        break
                else:
                    self.logger.warning(f"DuckDuckGo search failed with status: {response.status_code}")
                        
                # Small delay between variations
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"DuckDuckGo search variation {i} failed: {e}")
                continue
        
        unique_links = list(set(all_links))[:max_results]
        self.logger.info(f"DuckDuckGo total unique links found: {len(unique_links)}")
        return unique_links
    
    def search_google_scholar(self, query, max_results=20):
        """Search Google Scholar for PDFs"""
        self.update_progress("Searching Google Scholar...")
        self.logger.info(f"Starting Google Scholar search for: {query}")
        
        scholar_query = f"{query} filetype:pdf"
        search_url = f"https://scholar.google.com/scholar?q={urllib.parse.quote(scholar_query)}"
        self.logger.info(f"Google Scholar URL: {search_url}")
        
        try:
            response = self.session.get(search_url, timeout=15)
            if self.is_bot_challenge(response.text):
                self.logger.warning("Bot challenge detected on Google Scholar")
                self.update_progress("Scholar blocked - trying Selenium...")
                return self.selenium_search(search_url, max_results)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            pdf_links = self.extract_pdf_links(soup, "https://scholar.google.com")
            self.logger.info(f"Google Scholar found {len(pdf_links)} links")
            return pdf_links[:max_results]
            
        except Exception as e:
            self.logger.error(f"Google Scholar search failed: {e}")
            return []
    
    def search_google_direct_pdfs(self, query, max_results=15):
        """Search Google directly for PDF files - most effective method"""
        self.update_progress("Searching Google for direct PDFs...")
        self.logger.info(f"Starting Google direct PDF search for: {query}")
        
        # Multiple search variations for better results
        search_variations = [
            f"{query} filetype:pdf",
            f"{query} nursing filetype:pdf",
            f"{query} medical filetype:pdf",
            f"{query} textbook filetype:pdf",
            f"{query} guide filetype:pdf",
            f"{query} manual filetype:pdf site:edu"
        ]
        
        all_links = []
        
        for i, search_query in enumerate(search_variations, 1):
            try:
                self.update_progress(f"Google PDF search {i}/{len(search_variations)}")
                
                # Search multiple pages for this variation
                variation_links = self.search_google_pages(search_query, pages=2)
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
        return unique_links
    
    def search_google_pages(self, search_query, pages=2):
        """Search multiple pages of Google results"""
        all_links = []
        
        for page in range(pages):
            try:
                # Google pagination: start parameter (0, 10, 20, etc.)
                start = page * 10
                search_url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}&start={start}"
                self.logger.info(f"Google search page {page + 1}: {search_url}")
                
                response = self.session.get(search_url, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    page_links = self.extract_google_pdf_links(soup)
                    all_links.extend(page_links)
                    self.logger.info(f"Google page {page + 1} found {len(page_links)} PDF links")
                    
                    # If no results on this page, stop searching further pages
                    if not page_links and page > 0:
                        self.logger.info(f"No results on page {page + 1}, stopping pagination")
                        break
                        
                else:
                    self.logger.warning(f"Google search page {page + 1} failed with status: {response.status_code}")
                    break
                
                # Delay between pages
                if page < pages - 1:
                    time.sleep(random.uniform(2, 3))
                
            except Exception as e:
                self.logger.error(f"Google search page {page + 1} failed: {e}")
                break
        
        return all_links
    
    def extract_google_pdf_links(self, soup):
        """Extract PDF links from Google search results and follow promising links"""
        pdf_links = []
        potential_pages = []
        
        # Look for direct PDF links in Google search results
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Handle Google's URL redirection format
            if href.startswith('/url?q='):
                try:
                    actual_url = href.split('/url?q=')[1].split('&')[0]
                    actual_url = urllib.parse.unquote(actual_url)
                    
                    # Direct PDF links
                    if actual_url.lower().endswith('.pdf'):
                        pdf_links.append(actual_url)
                        self.logger.info(f"Found direct PDF link: {actual_url}")
                    
                    # Potential pages that might contain PDFs
                    elif any(indicator in actual_url.lower() for indicator in [
                        'repository', 'library', 'docs', 'publications', 'resources',
                        'nursing', 'medical', 'health', 'education', '.edu', '.ac.',
                        'poltekkes', 'university', 'college'
                    ]):
                        potential_pages.append(actual_url)
                        
                except Exception as e:
                    continue
            
            # Direct HTTP links
            elif href.startswith('http'):
                if href.lower().endswith('.pdf'):
                    pdf_links.append(href)
                    self.logger.info(f"Found direct PDF link: {href}")
        
        # Look for PDF indicators in search result snippets
        for result_div in soup.find_all('div', class_=['g', 'tF2Cxc']):  # Google result containers
            # Check if result mentions PDF
            text_content = result_div.get_text().lower()
            if 'pdf' in text_content and any(word in text_content for word in [
                'pages', 'download', 'file', 'document', 'nursing', 'pediatric'
            ]):
                # Find the main link for this result
                main_link = result_div.find('a', href=True)
                if main_link:
                    href = main_link['href']
                    if href.startswith('/url?q='):
                        try:
                            actual_url = href.split('/url?q=')[1].split('&')[0]
                            actual_url = urllib.parse.unquote(actual_url)
                            if actual_url not in potential_pages and not actual_url.endswith('.pdf'):
                                potential_pages.append(actual_url)
                        except:
                            continue
        
        # Follow promising pages to look for PDFs (limit to avoid too many requests)
        self.logger.info(f"Found {len(potential_pages)} potential PDF pages to check")
        for i, page_url in enumerate(potential_pages[:5]):  # Limit to 5 pages per search
            try:
                self.update_progress(f"Checking page {i+1}/5 for PDFs...")
                page_pdfs = self.extract_pdfs_from_page(page_url)
                pdf_links.extend(page_pdfs)
                if page_pdfs:
                    self.logger.info(f"Found {len(page_pdfs)} PDFs on page: {page_url}")
                
                # Small delay between page checks
                time.sleep(1)
                
            except Exception as e:
                self.logger.warning(f"Failed to check page {page_url}: {e}")
                continue
        
        return list(set(pdf_links))  # Remove duplicates
    
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
                if href.lower().endswith('.pdf') or '.pdf' in href.lower():
                    pdf_links.append(href)
            
            # Look for download buttons or PDF indicators
            for element in soup.find_all(['a', 'button'], href=True):
                text = element.get_text().lower()
                href = element.get('href', '')
                
                if any(word in text for word in ['download', 'pdf', 'view pdf', 'full text']):
                    if href.startswith('/'):
                        href = urljoin(page_url, href)
                    
                    if href.startswith('http') and ('.pdf' in href.lower() or 'pdf' in text):
                        pdf_links.append(href)
            
            # Look for meta tags or specific patterns
            for meta in soup.find_all('meta'):
                content = meta.get('content', '')
                if '.pdf' in content.lower():
                    if content.startswith('http'):
                        pdf_links.append(content)
                    elif content.startswith('/'):
                        pdf_links.append(urljoin(page_url, content))
                        
        except Exception as e:
            self.logger.error(f"Error extracting PDFs from {page_url}: {e}")
        
        return list(set(pdf_links))
    
    def search_educational_sites(self, query, max_results=10):
        """Search known educational and medical sites directly"""
        self.update_progress("Searching educational sites...")
        self.logger.info(f"Starting educational sites search for: {query}")
        
        # Known sites that often have nursing/medical PDFs
        educational_sites = [
            "ncbi.nlm.nih.gov/pmc",
            "who.int",
            "cdc.gov",
            "nih.gov",
            "pubmed.ncbi.nlm.nih.gov"
        ]
        
        all_links = []
        
        for i, site in enumerate(educational_sites, 1):
            try:
                self.update_progress(f"Educational sites {i}/{len(educational_sites)}")
                # Search within the site
                search_query = f"site:{site} {query} filetype:pdf"
                search_url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}"
                self.logger.info(f"Educational site search URL: {search_url}")
                
                response = self.session.get(search_url, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    site_links = self.extract_google_pdf_links(soup)
                    
                    # Filter to only include links from the target site
                    filtered_links = [link for link in site_links if any(domain in link for domain in [site])]
                    all_links.extend(filtered_links)
                    
                    self.logger.info(f"Educational site {site} found {len(filtered_links)} links")
                else:
                    self.logger.warning(f"Educational site search failed with status: {response.status_code}")
                
                time.sleep(2)  # Be respectful to Google
                
                if len(all_links) >= max_results:
                    break
                    
            except Exception as e:
                self.logger.error(f"Educational site search failed for {site}: {e}")
                continue
        
        unique_links = list(set(all_links))[:max_results]
        self.logger.info(f"Educational sites total unique links found: {len(unique_links)}")
        return unique_links
    
    def selenium_search(self, search_url, max_results=20):
        """Use Selenium when bot detection is encountered"""
        self.logger.info("Using Selenium for bot-protected search")
        
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            driver.get(search_url)
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            if self.is_bot_challenge(driver.page_source):
                self.logger.warning("CAPTCHA detected - manual intervention may be needed")
                return []
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            pdf_links = self.extract_pdf_links(soup, search_url)
            
            driver.quit()
            return pdf_links[:max_results]
            
        except Exception as e:
            self.logger.error(f"Selenium search error: {e}")
            return []
    
    def extract_pdf_links(self, soup, base_url=""):
        """Extract PDF links from search results"""
        pdf_links = []
        
        # Look for direct PDF links
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Skip relative URLs that are just search results
            if href.startswith('/') and 'q=' in href:
                continue
                
            # Convert relative URLs to absolute
            if href.startswith('/') and base_url:
                href = urljoin(base_url, href)
            elif not href.startswith('http'):
                continue
                
            if href.lower().endswith('.pdf'):
                pdf_links.append(href)
            elif 'pdf' in href.lower() and '.pdf' in href.lower():
                pdf_links.append(href)
        
        # Look for links with PDF indicators in text
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Skip relative search URLs
            if href.startswith('/') and 'q=' in href:
                continue
                
            # Convert relative URLs to absolute
            if href.startswith('/') and base_url:
                href = urljoin(base_url, href)
            elif not href.startswith('http'):
                continue
                
            link_text = link.get_text().lower()
            if 'pdf' in link_text and any(word in link_text for word in ['download', 'view', 'file']):
                pdf_links.append(href)
        
        return list(set(pdf_links))  # Remove duplicates
    
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
                return True
            
            response = self.session.get(url, stream=True)
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
        """Search and download PDFs for a specific query"""
        self.current_query = query
        
        # Try multiple search strategies in order of effectiveness
        all_links = []
        
        # 1. Google direct PDF search (most effective - gets actual PDF links)
        google_links = self.search_google_direct_pdfs(query, max_downloads // 2)
        all_links.extend(google_links)
        self.logger.info(f"Google direct search found {len(google_links)} links")
        
        # 2. Educational sites (reliable sources)
        if len(all_links) < max_downloads:
            remaining = max_downloads - len(all_links)
            educational_links = self.search_educational_sites(query, remaining // 2)
            all_links.extend(educational_links)
            self.logger.info(f"Educational sites found {len(educational_links)} links")
        
        # 3. DuckDuckGo (backup method)
        if len(all_links) < max_downloads:
            remaining = max_downloads - len(all_links)
            duckduckgo_links = self.search_duckduckgo(query, remaining // 2)
            all_links.extend(duckduckgo_links)
            self.logger.info(f"DuckDuckGo found {len(duckduckgo_links)} links")
        
        # 4. Google Scholar (academic sources)
        if len(all_links) < max_downloads:
            remaining = max_downloads - len(all_links)
            scholar_links = self.search_google_scholar(query, remaining)
            all_links.extend(scholar_links)
            self.logger.info(f"Google Scholar found {len(scholar_links)} links")
        
        # Remove duplicates and limit results
        unique_links = list(set(all_links))[:max_downloads]
        self.logger.info(f"Total unique links for '{query}': {len(unique_links)}")
        
        if not unique_links:
            self.update_progress("No PDFs found")
            self.logger.warning(f"No PDF links found for query: {query}")
            time.sleep(2)
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
                time.sleep(random.uniform(0.5, 1.5))
        
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
    # Get download directory from user
    download_dir = input("Enter download directory (default: nursing_certification_pdfs): ").strip()
    if not download_dir:
        download_dir = "nursing_certification_pdfs"
    
    # Get max file size from user
    max_size_input = input("Enter max file size in MB (default: 10): ").strip()
    try:
        max_size_mb = float(max_size_input) if max_size_input else 10.0
    except ValueError:
        max_size_mb = 10.0
    
    # Initialize downloader
    downloader = NursingPDFDownloader(
        download_dir=download_dir, 
        delay_range=(1, 3),
        max_file_size_mb=max_size_mb
    )
    
    # Comprehensive nursing and medical terms
    nursing_medical_terms = [
        # Basic nursing education and practice
        "nursing fundamentals", "nursing principles", "nursing theory",
        "nursing practice", "clinical nursing", "bedside nursing",
        "patient care", "nursing assessment", "nursing diagnosis",
        "nursing interventions", "nursing outcomes", "care planning",
        
        # Medical sciences and pathology
        "pathology", "pathophysiology", "disease process", "medical diagnosis",
        "clinical pathology", "anatomical pathology", "cellular pathology",
        "tissue pathology", "organ pathology", "systemic pathology",
        "infectious diseases", "chronic diseases", "acute conditions",
        "autoimmune disorders", "genetic disorders", "metabolic disorders",
        
        # Anatomy and physiology
        "human anatomy", "physiology", "body systems", "cardiovascular system",
        "respiratory system", "nervous system", "endocrine system",
        "digestive system", "urinary system", "musculoskeletal system",
        "integumentary system", "reproductive system", "immune system",
        
        # Clinical specialties
        "medical surgical nursing", "critical care nursing", "intensive care",
        "emergency nursing", "trauma nursing", "perioperative nursing",
        "operating room procedures", "surgical nursing", "anesthesia care",
        "recovery room nursing", "post operative care",
        
        # Specialty areas
        "pediatric nursing", "child health", "neonatal care", "infant care",
        "maternal nursing", "obstetric nursing", "gynecologic nursing",
        "geriatric nursing", "elderly care", "gerontology nursing",
        "psychiatric nursing", "mental health nursing", "behavioral health",
        
        # Disease-specific nursing
        "oncology nursing", "cancer care", "chemotherapy administration",
        "radiation therapy", "palliative care", "hospice care",
        "cardiac nursing", "heart disease", "cardiovascular care",
        "diabetes nursing", "endocrine disorders", "hormone therapy",
        "renal nursing", "kidney disease", "dialysis care",
        "respiratory nursing", "pulmonary care", "ventilator management",
        
        # Infection control and safety
        "infection control", "hospital acquired infections", "sterile technique",
        "isolation precautions", "hand hygiene", "personal protective equipment",
        "wound care", "pressure ulcers", "wound healing", "dressing changes",
        "medication safety", "drug administration", "pharmacology nursing",
        
        # Advanced practice and leadership
        "nurse practitioner", "clinical nurse specialist", "nurse educator",
        "nursing leadership", "nursing management", "quality improvement",
        "evidence based practice", "nursing research", "clinical research",
        "healthcare quality", "patient safety", "risk management",
        
        # Education and certification
        "nursing education", "clinical instruction", "nursing curriculum",
        "competency assessment", "skill validation", "continuing education",
        "professional development", "certification preparation", "exam review",
        "study guides", "practice questions", "clinical guidelines",
        
        # Healthcare systems and ethics
        "healthcare delivery", "nursing ethics", "patient rights",
        "informed consent", "cultural competency", "diversity in healthcare",
        "health disparities", "community health", "public health nursing",
        "health promotion", "disease prevention", "wellness programs",
        
        # Technology and documentation
        "electronic health records", "nursing documentation", "care coordination",
        "telehealth nursing", "remote monitoring", "health informatics",
        "clinical decision support", "nursing protocols", "standard procedures",
        
        # Pharmacology and therapeutics
        "nursing pharmacology", "drug interactions", "medication effects",
        "therapeutic interventions", "pain management", "symptom management",
        "comfort care", "rehabilitation nursing", "physical therapy",
        "occupational therapy", "speech therapy", "nutrition therapy"
    ]
    
    print(f"Starting comprehensive nursing and medical PDF download...")
    print(f"Download directory: {download_dir}")
    print(f"Max file size: {max_size_mb} MB")
    print(f"Available search terms: {len(nursing_medical_terms)}")
    print(f"Target downloads: 200 files")
    print(f"Detailed logs: {downloader.log_file}")
    print(f"Progress display will update below...\n")
    
    # Progressive download
    total_downloaded = 0
    max_total_downloads = 200  # Increased limit for comprehensive medical materials
    queries_tried = set()
    
    # Set up progress tracking
    downloader.total_queries = min(len(nursing_medical_terms), 50)  # Reasonable limit
    
    try:
        downloader.logger.info(f"=== Starting download session ===")
        downloader.logger.info(f"Target: {max_total_downloads} files")
        downloader.logger.info(f"Available terms: {len(nursing_medical_terms)}")
        
        while total_downloaded < max_total_downloads and len(queries_tried) < len(nursing_medical_terms):
            # Select next term
            available_terms = [term for term in nursing_medical_terms if term not in queries_tried]
            if not available_terms:
                break
                
            query = random.choice(available_terms)
            queries_tried.add(query)
            downloader.query_count = len(queries_tried)
            
            downloader.logger.info(f"=== Query {len(queries_tried)}: '{query}' ===")
            
            # Download batch (5-10 per query for nursing materials)
            remaining = max_total_downloads - total_downloaded
            batch_size = min(random.randint(5, 10), remaining)
            
            downloader.logger.info(f"Batch size: {batch_size}, Total so far: {total_downloaded}/{max_total_downloads}")
            downloaded_count = downloader.download_pdfs_from_search(query, max_downloads=batch_size)
            total_downloaded += downloaded_count
            
            downloader.logger.info(f"Query '{query}' completed: {downloaded_count} files downloaded")
            
            # Break if we've hit our target
            if total_downloaded >= max_total_downloads:
                downloader.logger.info(f"Target reached: {total_downloaded} files")
                break
                
            # Delay between queries
            time.sleep(random.uniform(3, 7))
            
            # Every 10 queries, take a longer break
            if len(queries_tried) % 10 == 0:
                downloader.update_progress("Taking longer break...")
                downloader.logger.info(f"Taking longer break after {len(queries_tried)} queries")
                time.sleep(random.uniform(15, 30))
    
    except KeyboardInterrupt:
        print("\n\nDownload interrupted by user.")
        downloader.logger.info("Download session interrupted by user")
    
    # Final results
    print(f"\n=== FINAL RESULTS ===")
    downloader.print_stats()
    print(f"Total queries tried: {len(queries_tried)}")
    if len(queries_tried) > 0:
        print(f"Average PDFs per query: {total_downloaded/len(queries_tried):.2f}")
    
    # Log final results
    downloader.logger.info(f"=== SESSION COMPLETED ===")
    downloader.logger.info(f"Total files downloaded: {total_downloaded}")
    downloader.logger.info(f"Total queries tried: {len(queries_tried)}")
    downloader.logger.info(f"Success rate: {downloader.stats['successful_downloads']}/{downloader.stats['total_attempted']} ({100*downloader.stats['successful_downloads']/max(1,downloader.stats['total_attempted']):.1f}%)")
    downloader.logger.info(f"Total size: {downloader.stats['total_size_mb']:.2f} MB")
    if len(queries_tried) > 0:
        downloader.logger.info(f"Average PDFs per query: {total_downloaded/len(queries_tried):.2f}")
    
    # Save query log
    log_file = os.path.join(downloader.download_dir, "nursing_queries_log.txt")
    with open(log_file, "w") as f:
        f.write("Nursing certification queries used in this session:\n")
        f.write(f"Download directory: {download_dir}\n")
        f.write(f"Max file size: {max_size_mb} MB\n")
        f.write(f"Total files downloaded: {total_downloaded}\n")
        f.write(f"Detailed logs: {downloader.log_file}\n\n")
        f.write("Queries:\n")
        for query in sorted(queries_tried):
            f.write(f"- {query}\n")
    
    downloader.logger.info(f"Query log saved to: {log_file}")
    print(f"\nQuery log saved to: {log_file}")
    print(f"Detailed logs available at: {downloader.log_file}")

if __name__ == "__main__":
    main() 
