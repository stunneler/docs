#!/usr/bin/env python3
"""
AcadeMerit Document Uploader v3.0
Streamlined version focusing on session persistence and reliable uploads
"""

import os
import sys
import time
import json
import getpass
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class AcadeMeritUploaderV3:
    """Streamlined AcadeMerit uploader with persistent session"""
    
    def __init__(self, renamed_files_dir="../downloaded_files/renamed"):
        self.renamed_files_dir = Path(renamed_files_dir)
        self.driver = None
        self.credentials = {}
        self.upload_stats = {
            'total_files': 0,
            'uploaded': 0,
            'failed': 0,
            'start_time': time.time()
        }
        
        # Subject mapping for AcadeMerit
        self.subject_mapping = {
            'nursing': 'Health Care',
            'medical': 'Health Care', 
            'healthcare': 'Health Care',
            'health': 'Health Care',
            'nclex': 'Health Care',
            'ati': 'Health Care',
            'hesi': 'Health Care',
            'psychology': 'Psychology',
            'mathematics': 'Mathematics',
            'math': 'Mathematics',
            'physics': 'Science',
            'chemistry': 'Science',
            'biology': 'Science',
            'science': 'Science',
            'computer': 'Programming',
            'programming': 'Programming',
            'engineering': 'Programming',
            'business': 'Business',
            'accounting': 'Business',
            'economics': 'Business',
            'finance': 'Business',
            'english': 'Writing',
            'literature': 'Humanities',
            'history': 'Humanities',
            'philosophy': 'Humanities'
        }
    
    def setup_browser(self):
        """Setup Firefox with session persistence"""
        try:
            options = FirefoxOptions()
            
            # Keep JavaScript enabled for session management
            options.set_preference('javascript.enabled', True)
            
            # File upload permissions
            options.set_preference('dom.file.createInChild', True)
            
            # Network timeouts
            options.set_preference('network.http.connection-timeout', 60)
            options.set_preference('network.http.response.timeout', 300)
            
            # Disable images for faster loading
            options.set_preference('permissions.default.image', 2)
            
            # Run headless unless debug mode
            if not getattr(self, 'debug_mode', False):
                options.add_argument('--headless')
            
            self.driver = webdriver.Firefox(options=options)
            self.driver.implicitly_wait(10)
            self.driver.set_page_load_timeout(30)
            
            print("✅ Firefox browser initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize browser: {e}")
            return False
    
    def load_credentials(self):
        """Load credentials from file or prompt user"""
        creds_file = Path("academerit_credentials.json")
        
        if creds_file.exists():
            try:
                with open(creds_file, 'r') as f:
                    self.credentials = json.load(f)
                print(f"✅ Loaded credentials for: {self.credentials['email']}")
                return True
            except Exception as e:
                print(f"⚠️  Could not load credentials: {e}")
        
        # Prompt for credentials
        print("🔐 Enter AcadeMerit credentials:")
        email = input("📧 Email: ").strip()
        password = getpass.getpass("🔑 Password: ")
        
        if not email or not password:
            print("❌ Email and password required")
            return False
        
        self.credentials = {'email': email, 'password': password}
        
        # Save for future use
        try:
            with open(creds_file, 'w') as f:
                json.dump(self.credentials, f)
            print("💾 Credentials saved")
        except Exception:
            pass
        
        return True
    
    def login(self):
        """Login to AcadeMerit with session validation"""
        try:
            print("🔐 Logging into AcadeMerit...")
            self.driver.get("https://academerit.com/login")
            
            # Wait for login form
            WebDriverWait(self.driver, 15).until(
                EC.all_of(
                    EC.presence_of_element_located((By.NAME, "email")),
                    EC.presence_of_element_located((By.NAME, "password")),
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
                )
            )
            
            # Fill credentials
            email_field = self.driver.find_element(By.NAME, "email")
            password_field = self.driver.find_element(By.NAME, "password")
            
            email_field.clear()
            email_field.send_keys(self.credentials['email'])
            password_field.clear()
            password_field.send_keys(self.credentials['password'])
            
            # Submit login
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_button.click()
            
            # Wait for login completion
            WebDriverWait(self.driver, 15).until(
                EC.any_of(
                    EC.url_changes("https://academerit.com/login"),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".alert-danger"))
                )
            )
            
            # Validate login success
            if self.validate_session():
                print("✅ Login successful!")
                return True
            else:
                # Check for error messages
                try:
                    error_elem = self.driver.find_element(By.CSS_SELECTOR, ".alert-danger")
                    print(f"❌ Login failed: {error_elem.text}")
                except NoSuchElementException:
                    print("❌ Login failed: Unknown error")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def validate_session(self):
        """Multi-check session validation"""
        try:
            # Check 1: Not on login page
            if "/login" in self.driver.current_url:
                return False
            
            # Check 2: Look for authenticated user elements
            auth_indicators = [
                ".navbar-nav",
                "a[href*='logout']",
                ".user-menu",
                "[data-user]"
            ]
            
            for indicator in auth_indicators:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, indicator)
                    if elements and any(el.is_displayed() for el in elements):
                        return True
                except:
                    continue
            
            return False
            
        except Exception:
            return False
    
    def detect_subject(self, title):
        """Detect subject from filename"""
        title_lower = title.lower()
        
        for keyword, subject in self.subject_mapping.items():
            if keyword in title_lower:
                return subject
        
        return "Programming"  # Default fallback
    
    def calculate_price(self, title):
        """Calculate intelligent pricing"""
        title_lower = title.lower()
        
        # Free indicators
        free_keywords = ['basic', 'intro', 'simple', 'overview', 'sample']
        if any(kw in title_lower for kw in free_keywords):
            return 0
        
        # Premium indicators
        premium_keywords = ['comprehensive', 'complete', 'verified', 'actual', 'latest']
        exam_keywords = ['exam', 'test', 'quiz', 'nclex', 'ati', 'hesi']
        
        base_price = 7.99
        
        if any(kw in title_lower for kw in premium_keywords):
            base_price += 3.00
        
        if any(kw in title_lower for kw in exam_keywords):
            base_price += 2.00
        
        # Healthcare premium
        if any(kw in title_lower for kw in ['nursing', 'medical', 'healthcare', 'nclex']):
            base_price *= 1.2
        
        return round(base_price, 2)
    
    def upload_file(self, file_path):
        """Upload single file with error handling"""
        try:
            print(f"\n📤 Uploading: {file_path.name}")
            
            # Navigate to upload page
            self.driver.get("https://academerit.com/study-notes/create")
            
            # Check if redirected to login (session expired)
            if "/login" in self.driver.current_url:
                print("❌ Session expired - login required")
                return False
            
            # Wait for upload form
            WebDriverWait(self.driver, 20).until(
                EC.all_of(
                    EC.presence_of_element_located((By.NAME, "title")),
                    EC.presence_of_element_located((By.NAME, "description")),
                    EC.presence_of_element_located((By.NAME, "subject_id")),
                    EC.presence_of_element_located((By.NAME, "file"))
                )
            )
            
            # Extract title and detect metadata
            title = file_path.stem[:255]  # Respect max length
            subject = self.detect_subject(title)
            price = self.calculate_price(title)
            
            # Fill form fields
            self.driver.find_element(By.NAME, "title").send_keys(title)
            
            description = f"Study material: {title}\n\nEducational content for academic purposes."
            self.driver.find_element(By.NAME, "description").send_keys(description[:2000])
            
            # Select subject
            subject_dropdown = Select(self.driver.find_element(By.NAME, "subject_id"))
            try:
                subject_dropdown.select_by_visible_text(subject)
                print(f"📋 Subject: {subject}")
            except:
                # Fallback to first available option
                options = [opt.text for opt in subject_dropdown.options if opt.text.strip()]
                if len(options) > 1:
                    subject_dropdown.select_by_visible_text(options[1])
                    print(f"📋 Subject (fallback): {options[1]}")
            
            # Handle pricing
            is_free_checkbox = self.driver.find_element(By.NAME, "is_free")
            
            if price == 0:
                if not is_free_checkbox.is_selected():
                    is_free_checkbox.click()
                print("💰 Price: FREE")
            else:
                if is_free_checkbox.is_selected():
                    is_free_checkbox.click()
                
                try:
                    price_field = self.driver.find_element(By.NAME, "price")
                    price_field.clear()
                    price_field.send_keys(str(price))
                    print(f"💰 Price: ${price}")
                except NoSuchElementException:
                    # Price field might not be visible, set as free
                    if not is_free_checkbox.is_selected():
                        is_free_checkbox.click()
                    print("💰 Price: FREE (fallback)")
            
            # Upload file
            file_input = self.driver.find_element(By.NAME, "file")
            file_input.send_keys(str(file_path.absolute()))
            print("📁 File attached")
            
            # Submit form
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_button.click()
            print("🚀 Form submitted")
            
            # Wait for upload completion
            return self.wait_for_upload_completion()
            
        except Exception as e:
            print(f"❌ Upload error: {e}")
            return False
    
    def wait_for_upload_completion(self, timeout=300):
        """Wait for upload to complete with multiple detection methods"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                current_url = self.driver.current_url
                
                # Method 1: Successful redirect to study note page
                if "/study-notes/" in current_url and "/create" not in current_url:
                    print("✅ Upload successful - redirected to study note page")
                    return True
                
                # Method 2: Success alert message
                success_alerts = self.driver.find_elements(By.CSS_SELECTOR, ".alert-success")
                if any(alert.is_displayed() for alert in success_alerts):
                    print("✅ Upload successful - success message detected")
                    return True
                
                # Method 3: Error detection
                error_alerts = self.driver.find_elements(By.CSS_SELECTOR, ".alert-danger, .invalid-feedback")
                visible_errors = [el for el in error_alerts if el.is_displayed() and el.text.strip()]
                if visible_errors:
                    error_msg = visible_errors[0].text
                    print(f"❌ Upload failed: {error_msg}")
                    return False
                
                # Method 4: Still on create page after long time = likely failed
                if time.time() - start_time > 60 and "/create" in current_url:
                    print("❌ Upload timeout - still on create page")
                    return False
                
                time.sleep(2)
                
            except Exception:
                continue
        
        print("❌ Upload timeout - no completion detected")
        return False
    
    def get_pdf_files(self):
        """Get list of PDF files to upload"""
        if not self.renamed_files_dir.exists():
            print(f"❌ Directory not found: {self.renamed_files_dir}")
            return []
        
        pdf_files = list(self.renamed_files_dir.glob("*.pdf"))
        print(f"📁 Found {len(pdf_files)} PDF files")
        return pdf_files
    
    def upload_batch(self, batch_size=5, max_files=None):
        """Upload files in batches"""
        pdf_files = self.get_pdf_files()
        
        if not pdf_files:
            print("❌ No PDF files found")
            return
        
        # Limit files if specified
        if max_files:
            pdf_files = pdf_files[:max_files]
        
        self.upload_stats['total_files'] = min(len(pdf_files), batch_size)
        uploaded_files = []
        failed_files = []
        
        print(f"🚀 Starting upload of {self.upload_stats['total_files']} files")
        print("=" * 60)
        
        for i, file_path in enumerate(pdf_files[:batch_size]):
            print(f"\n📤 Processing file {i+1}/{self.upload_stats['total_files']}")
            
            # Verify session before each upload
            if not self.validate_session():
                print("❌ Session lost - stopping uploads")
                break
            
            # Upload file
            success = self.upload_file(file_path)
            
            if success:
                uploaded_files.append(file_path)
                self.upload_stats['uploaded'] += 1
                print(f"✅ Success: {file_path.name}")
            else:
                failed_files.append(file_path)
                self.upload_stats['failed'] += 1
                print(f"❌ Failed: {file_path.name}")
            
            # Brief pause between uploads
            if i < len(pdf_files[:batch_size]) - 1:
                time.sleep(2)
        
        # Summary
        elapsed = time.time() - self.upload_stats['start_time']
        print(f"\n✅ Upload batch complete!")
        print(f"📊 Results: {self.upload_stats['uploaded']} uploaded, {self.upload_stats['failed']} failed")
        print(f"⏱️  Time: {elapsed:.1f}s")
        
        # Move uploaded files
        if uploaded_files:
            self.move_uploaded_files(uploaded_files)
        
        # Save log
        self.save_log(uploaded_files, failed_files)
    
    def move_uploaded_files(self, uploaded_files):
        """Move uploaded files to uploaded subdirectory"""
        uploaded_dir = self.renamed_files_dir / "uploaded"
        uploaded_dir.mkdir(exist_ok=True)
        
        moved_count = 0
        for file_path in uploaded_files:
            try:
                if file_path.exists():
                    new_path = uploaded_dir / file_path.name
                    file_path.rename(new_path)
                    moved_count += 1
            except Exception as e:
                print(f"⚠️  Could not move {file_path.name}: {e}")
        
        if moved_count > 0:
            print(f"📁 Moved {moved_count} files to uploaded/ directory")
    
    def save_log(self, uploaded_files, failed_files):
        """Save upload results to log"""
        log_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'stats': self.upload_stats,
            'uploaded_files': [str(f) for f in uploaded_files],
            'failed_files': [str(f) for f in failed_files]
        }
        
        with open("upload_log.json", 'w') as f:
            json.dump(log_data, f, indent=2)
        
        print("📝 Upload log saved")
    
    def cleanup(self):
        """Clean up browser resources"""
        if self.driver:
            try:
                self.driver.quit()
                print("🧹 Browser closed")
            except:
                pass

def main():
    """Main function with CLI options"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AcadeMerit Uploader v3.0")
    parser.add_argument("--batch-size", type=int, default=5, help="Files per batch")
    parser.add_argument("--max-files", type=int, help="Limit total files to upload")
    parser.add_argument("--debug", action="store_true", help="Show browser window")
    parser.add_argument("--dir", default="../downloaded_files/renamed", help="Files directory")
    
    args = parser.parse_args()
    
    print("🚀 AcadeMerit Document Uploader v3.0")
    print("Streamlined uploader with persistent session")
    print("=" * 50)
    
    uploader = AcadeMeritUploaderV3(args.dir)
    uploader.debug_mode = args.debug
    
    try:
        # Setup
        if not uploader.setup_browser():
            return
        
        if not uploader.load_credentials():
            return
        
        # Login
        if not uploader.login():
            return
        
        # Upload files
        uploader.upload_batch(args.batch_size, args.max_files)
        
    except KeyboardInterrupt:
        print("\n⏹️  Upload cancelled")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        uploader.cleanup()

if __name__ == "__main__":
    main()
