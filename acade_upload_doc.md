 AcadeMerit Bot Workflow Documentation                                      ┃ │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
│                                                                                                                     │
│                                                                                                                     │
│                              Complete Redesign Guide for Automated Study Notes Upload                               │
│                                                                                                                     │
│ ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────── │
│                                                                                                                     │
│                                                 1. SYSTEM OVERVIEW                                                  │
│                                                                                                                     │
│                                                  Platform Details                                                   │
│                                                                                                                     │
│  • Base URL: https://academerit.com                                                                                 │
│  • Framework: Laravel (PHP)                                                                                         │
│  • Authentication: Session-based with CSRF protection                                                               │
│  • Upload Method: Multipart form with optional AJAX enhancement                                                     │
│                                                                                                                     │
│                                                  Bot Requirements                                                   │
│                                                                                                                     │
│  • Selenium WebDriver (Firefox/Chrome)                                                                              │
│  • Session persistence                                                                                              │
│  • File handling capabilities                                                                                       │
│  • Error detection and recovery                                                                                     │
│                                                                                                                     │
│ ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────── │
│                                                                                                                     │
│                                             2. AUTHENTICATION WORKFLOW                                              │
│                                                                                                                     │
│                                               2.1 Login Page Analysis                                               │
│                                                                                                                     │
│                                                                                                                     │
│  URL: https://academerit.com/login                                                                                  │
│  Method: POST                                                                                                       │
│  Content-Type: application/x-www-form-urlencoded                                                                    │
│                                                                                                                     │
│                                                                                                                     │
│                                                  Critical Elements                                                  │
│                                                                                                                     │
│                                                                                                                     │
│  <!-- Login Form -->                                                                                                │
│  <form method="POST" action="/login">                                                                               │
│      <input type="hidden" name="_token" value="CSRF_TOKEN">                                                         │
│      <input type="email" name="email" required>                                                                     │
│      <input type="password" name="password" required>                                                               │
│      <input type="checkbox" name="remember"> <!-- Optional -->                                                      │
│      <button type="submit">Login</button>                                                                           │
│  </form>                                                                                                            │
│                                                                                                                     │
│                                                                                                                     │
│                                                  Selectors for Bot                                                  │
│                                                                                                                     │
│                                                                                                                     │
│  SELECTORS = {                                                                                                      │
│      'email_field': 'input[name="email"]',                                                                          │
│      'password_field': 'input[name="password"]',                                                                    │
│      'remember_checkbox': 'input[name="remember"]',                                                                 │
│      'submit_button': 'button[type="submit"]',                                                                      │
│      'csrf_token': 'input[name="_token"]',                                                                          │
│      'error_message': '.alert-danger, .invalid-feedback'                                                            │
│  }                                                                                                                  │
│                                                                                                                     │
│                                                                                                                     │
│                                            2.2 Login Success Indicators                                             │
│                                                                                                                     │
│                                                                                                                     │
│  SUCCESS_INDICATORS = {                                                                                             │
│      'url_change': lambda url: '/login' not in url,                                                                 │
│      'logout_link': 'a[href*="logout"]',                                                                            │
│      'user_menu': '.user-menu, .dropdown-toggle',                                                                   │
│      'dashboard_elements': '.dashboard, [data-user]',                                                               │
│      'page_title': lambda title: 'login' not in title.lower()                                                       │
│  }                                                                                                                  │
│                                                                                                                     │
│                                                                                                                     │
│                                               2.3 Session Validation                                                │
│                                                                                                                     │
│                                                                                                                     │
│  def validate_session(driver):                                                                                      │
│      """Multi-layer session validation"""                                                                           │
│      checks = [                                                                                                     │
│          # Primary: URL not login page                                                                              │
│          lambda: '/login' not in driver.current_url,                                                                │
│                                                                                                                     │
│          # Secondary: Logout link exists                                                                            │
│          lambda: len(driver.find_elements(By.CSS_SELECTOR, 'a[href*="logout"]')) > 0,                               │
│                                                                                                                     │
│          # Tertiary: User-specific elements                                                                         │
│          lambda: len(driver.find_elements(By.CSS_SELECTOR, '.user-menu, [data-user]')) > 0,                         │
│                                                                                                                     │
│          # Quaternary: Page title check                                                                             │
│          lambda: 'login' not in driver.title.lower()                                                                │
│      ]                                                                                                              │
│                                                                                                                     │
│      return sum(check() for check in checks) >= 2  # At least 2 checks must pass                                    │
│                                                                                                                     │
│                                                                                                                     │
│ ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────── │
│                                                                                                                     │
│                                                 3. UPLOAD WORKFLOW                                                  │
│                                                                                                                     │
│                                              3.1 Upload Page Structure                                              │
│                                                                                                                     │
│                                                                                                                     │
│  URL: https://academerit.com/study-notes/create                                                                     │
│  Method: POST                                                                                                       │
│  Action: /study-notes                                                                                               │
│  Encoding: multipart/form-data                                                                                      │
│                                                                                                                     │
│                                                                                                                     │
│                                                Complete Form Schema                                                 │
│                                                                                                                     │
│                                                                                                                     │
│  <form method="POST" action="/study-notes" enctype="multipart/form-data" id="upload-form">                          │
│      <!-- Security -->                                                                                              │
│      <input type="hidden" name="_token" value="CSRF_TOKEN">                                                         │
│                                                                                                                     │
│      <!-- Required Fields -->                                                                                       │
│      <input type="text" name="title" maxlength="255" required>                                                      │
│      <textarea name="description" maxlength="2000" required></textarea>                                             │
│      <select name="subject_id" required>                                                                            │
│          <option value="">Select a subject</option>                                                                 │
│          <!-- Dynamic options -->                                                                                   │
│      </select>                                                                                                      │
│      <input type="file" name="file" accept=".pdf" required>                                                         │
│                                                                                                                     │
│      <!-- Pricing -->                                                                                               │
│      <input type="checkbox" name="is_free" value="1">                                                               │
│      <input type="number" name="price" min="1" max="1000" step="0.01">                                              │
│                                                                                                                     │
│      <!-- Optional Fields -->                                                                                       │
│      <select name="document_type">                                                                                  │
│          <option value="">Select document type</option>                                                             │
│          <option value="notes">Study Notes</option>                                                                 │
│          <option value="assignment">Assignment</option>                                                             │
│          <option value="exam">Exam/Test</option>                                                                    │
│          <option value="project">Project</option>                                                                   │
│          <option value="thesis">Thesis/Dissertation</option>                                                        │
│          <option value="other">Other</option>                                                                       │
│      </select>                                                                                                      │
│                                                                                                                     │
│      <input type="text" name="course_codes" placeholder="MATH101, CS201">                                           │
│      <input type="text" name="tags[]" multiple>                                                                     │
│                                                                                                                     │
│      <button type="submit">Upload Study Notes</button>                                                              │
│  </form>                                                                                                            │
│                                                                                                                     │
│                                                                                                                     │
│                                               3.2 Critical Selectors                                                │
│                                                                                                                     │
│                                                                                                                     │
│  UPLOAD_SELECTORS = {                                                                                               │
│      # Form identification                                                                                          │
│      'form': '#upload-form',                                                                                        │
│      'csrf_token': 'input[name="_token"]',                                                                          │
│                                                                                                                     │
│      # Required fields                                                                                              │
│      'title': 'input[name="title"]',                                                                                │
│      'description': 'textarea[name="description"]',                                                                 │
│      'subject_dropdown': 'select[name="subject_id"]',                                                               │
│      'file_input': 'input[name="file"]',                                                                            │
│                                                                                                                     │
│      # Pricing controls                                                                                             │
│      'is_free_checkbox': 'input[name="is_free"]',                                                                   │
│      'price_input': 'input[name="price"]',                                                                          │
│      'price_section': '#price-section',                                                                             │
│                                                                                                                     │
│      # Optional fields                                                                                              │
│      'document_type': 'select[name="document_type"]',                                                               │
│      'course_codes': 'input[name="course_codes"]',                                                                  │
│      'tags_input': '#tags-input',                                                                                   │
│                                                                                                                     │
│      # Submission                                                                                                   │
│      'submit_button': 'button[type="submit"]',                                                                      │
│                                                                                                                     │
│      # Progress tracking (if JS enabled)                                                                            │
│      'progress_container': '#progress-container',                                                                   │
│      'progress_bar': '#progress-bar',                                                                               │
│      'file_preview': '#file-preview',                                                                               │
│                                                                                                                     │
│      # Status indicators                                                                                            │
│      'success_alert': '.alert-success',                                                                             │
│      'error_alert': '.alert-danger',                                                                                │
│      'validation_errors': '.invalid-feedback, .is-invalid'                                                          │
│  }                                                                                                                  │
│                                                                                                                     │
│                                                                                                                     │
│                                            3.3 Subject Options (Current)                                            │
│                                                                                                                     │
│                                                                                                                     │
│  AVAILABLE_SUBJECTS = {                                                                                             │
│      'Programming': 1,                                                                                              │
│      'Mathematics': 2,                                                                                              │
│      'Science': 3,                                                                                                  │
│      'Business': 4,                                                                                                 │
│      'Humanities': 5,                                                                                               │
│      'Writing': 6,                                                                                                  │
│      'Linear Algebra': 7,                                                                                           │
│      'Chemical Engineering': 8,                                                                                     │
│      'Rocket Science': 9,                                                                                           │
│      'Psychology': 10,                                                                                              │
│      'Health Care': 11  # Updated from Nursing                                                                      │
│  }                                                                                                                  │
│                                                                                                                     │
│                                                                                                                     │
│ ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────── │
│                                                                                                                     │
│                                                4. RESPONSE HANDLING                                                 │
│                                                                                                                     │
│                                            4.1 Success Response Patterns                                            │
│                                                                                                                     │
│                                                                                                                     │
│  SUCCESS_PATTERNS = {                                                                                               │
│      # URL-based detection                                                                                          │
│      'redirect_success': {                                                                                          │
│          'pattern': r'/study-notes/[^/]+$',                                                                         │
│          'description': 'Redirected to study note page'                                                             │
│      },                                                                                                             │
│                                                                                                                     │
│      # Content-based detection                                                                                      │
│      'success_message': {                                                                                           │
│          'selectors': ['.alert-success'],                                                                           │
│          'text_patterns': [                                                                                         │
│              'uploaded.*successfully',                                                                              │
│              'published.*successfully',                                                                             │
│              'study note.*created'                                                                                  │
│          ]                                                                                                          │
│      },                                                                                                             │
│                                                                                                                     │
│      # Progress completion (if JS enabled)                                                                          │
│      'progress_complete': {                                                                                         │
│          'selector': '#progress-bar',                                                                               │
│          'text_values': ['100%', 'Complete!', 'Success']                                                            │
│      }                                                                                                              │
│  }                                                                                                                  │
│                                                                                                                     │
│                                                                                                                     │
│                                             4.2 Error Response Patterns                                             │
│                                                                                                                     │
│                                                                                                                     │
│  ERROR_PATTERNS = {                                                                                                 │
│      # Validation errors                                                                                            │
│      'validation_errors': {                                                                                         │
│          'selectors': ['.invalid-feedback', '.alert-danger'],                                                       │
│          'field_specific': {                                                                                        │
│              'title': 'input[name="title"] + .invalid-feedback',                                                    │
│              'description': 'textarea[name="description"] + .invalid-feedback',                                     │
│              'file': 'input[name="file"] + .invalid-feedback',                                                      │
│              'subject': 'select[name="subject_id"] + .invalid-feedback',                                            │
│              'price': 'input[name="price"] + .invalid-feedback'                                                     │
│          }                                                                                                          │
│      },                                                                                                             │
│                                                                                                                     │
│      # File-specific errors                                                                                         │
│      'file_errors': {                                                                                               │
│          'size_exceeded': ['file size', 'exceeds.*limit', 'too large'],                                             │
│          'invalid_format': ['pdf.*only', 'invalid.*format', 'file type'],                                           │
│          'upload_failed': ['upload.*failed', 'file.*error']                                                         │
│      },                                                                                                             │
│                                                                                                                     │
│      # Server errors                                                                                                │
│      'server_errors': {                                                                                             │
│          'selectors': ['.alert-danger', '.error-message'],                                                          │
│          'status_codes': [500, 422, 413, 403]                                                                       │
│      },                                                                                                             │
│                                                                                                                     │
│      # Session errors                                                                                               │
│      'session_errors': {                                                                                            │
│          'redirect_to_login': lambda url: '/login' in url,                                                          │
│          'csrf_mismatch': ['csrf', 'token.*mismatch', 'session.*expired']                                           │
│      }                                                                                                              │
│  }                                                                                                                  │
│                                                                                                                     │
│                                                                                                                     │
│                                                4.3 Processing States                                                │
│                                                                                                                     │
│                                                                                                                     │
│  PROCESSING_STATES = {                                                                                              │
│      'uploading': {                                                                                                 │
│          'indicators': ['uploading', 'progress-bar.*visible'],                                                      │
│          'progress_selector': '#progress-bar',                                                                      │
│          'timeout': 300  # 5 minutes                                                                                │
│      },                                                                                                             │
│                                                                                                                     │
│      'processing': {                                                                                                │
│          'indicators': ['processing', 'generating.*preview'],                                                       │
│          'text_patterns': ['processing.*file', 'creating.*thumbnail'],                                              │
│          'timeout': 180  # 3 minutes                                                                                │
│      },                                                                                                             │
│                                                                                                                     │
│      'completing': {                                                                                                │
│          'indicators': ['complete', 'redirecting'],                                                                 │
│          'final_states': ['100%', 'Complete!', 'Success'],                                                          │
│          'timeout': 30  # 30 seconds                                                                                │
│      }                                                                                                              │
│  }                                                                                                                  │
│                                                                                                                     │
