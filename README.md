# Web Scraping Dashboard Setup Guide

## Overview
This is a complete web scraping dashboard system with a Python Flask backend and modern HTML/CSS/JavaScript frontend. It provides real-time monitoring, task management, and result visualization for web scraping operations.

## Features

### Backend Features
- **RESTful API** built with Flask
- **SQLite Database** for persistent storage
- **Multi-threaded scraping** with background task processing
- **Real-time logging** and error tracking
- **Task management** (create, monitor, delete)
- **Data extraction**: titles, content, links, images
- **CORS support** for frontend integration

### Frontend Features
- **Modern UI** with glassmorphism design and animations
- **Real-time dashboard** with auto-refresh every 5 seconds
- **Interactive charts** showing activity trends
- **Task management interface** with status tracking
- **Modal popups** for detailed task information and results
- **Responsive design** that works on desktop and mobile
- **Statistics overview** with key metrics

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

### Step 1: Install Python Dependencies
Create a `requirements.txt` file with the following content:

```
Flask==2.3.3
Flask-CORS==4.0.0
requests==2.31.0
beautifulsoup4==4.12.2
```

Install the dependencies:
```bash
pip install -r requirements.txt
```

### Step 2: Set Up the Backend
1. Save the Python backend code as `app.py`
2. Create a `templates` directory in the same folder
3. Save the HTML frontend code as `templates/dashboard.html`

### Step 3: Run the Application
```bash
python app.py
```

The application will start on `http://localhost:5000`

## File Structure
```
web-scraping-dashboard/
├── app.py                 # Flask backend
├── requirements.txt       # Python dependencies
├── templates/
│   └── dashboard.html    # Frontend dashboard
└── scraping_dashboard.db # SQLite database (created automatically)
```

## API Endpoints

### Tasks
- `GET /api/tasks` - Get all tasks
- `POST /api/tasks` - Create a new scraping task
- `GET /api/tasks/{id}` - Get specific task details
- `DELETE /api/tasks/{id}` - Delete a task

### Results
- `GET /api/tasks/{id}/results` - Get scraping results for a task

### Logs
- `GET /api/tasks/{id}/logs` - Get logs for a task

### Statistics
- `GET /api/stats` - Get dashboard statistics

## Usage

### Creating a Scraping Task
1. Enter a URL in the "URL to Scrape" field
2. Optionally provide a custom task name
3. Click "Start Scraping"
4. Monitor the task status in real-time

### Viewing Results
1. Wait for the task to complete (status changes to "completed")
2. Click "View Results" to see extracted data:
   - Page title
   - Text content preview
   - Found links
   - Found images

### Monitoring Tasks
- Tasks update automatically every 5 seconds
- View detailed logs by clicking "View Details"
- Delete tasks that are no longer needed
- Monitor statistics in the dashboard cards

## Database Schema

### Tasks Table
- `id` - Unique task identifier
- `url` - Target URL to scrape
- `name` - Human-readable task name
- `status` - Current status (pending, running, completed, failed)
- `created_at` - Task creation timestamp
- `completed_at` - Task completion timestamp
- `config` - JSON configuration (for future extensions)
- `error_message` - Error details if task fails

### Results Table
- `id` - Unique result identifier
- `task_id` - Foreign key to tasks table
- `url` - Scraped URL
- `title` - Page title
- `content` - Extracted text content
- `links` - JSON array of found links
- `images` - JSON array of found images
- `scraped_at` - Scraping timestamp

### Logs Table
- `id` - Auto-increment log ID
- `task_id` - Foreign key to tasks table
- `level` - Log level (INFO, ERROR)
- `message` - Log message
- `timestamp` - Log entry timestamp

## Customization

### Adding New Extraction Features
Modify the `WebScraper.scrape_url()` method to extract additional data:
```python
# Extract meta descriptions
meta_desc = soup.find('meta', attrs={'name': 'description'})
description = meta_desc['content'] if meta_desc else ''

# Extract headings
headings = [h.get_text().strip() for h in soup.find_all(['h1', 'h2', 'h3'])]
```

### Styling Customization
The frontend uses CSS custom properties for easy theming:
```css
:root {
    --primary-color: #667eea;
    --secondary-color: #764ba2;
    --success-color: #28a745;
    --error-color: #dc3545;
}
```

### Adding Authentication
For production use, consider adding authentication:
```python
from flask_login import LoginManager, login_required

# Add @login_required decorator to protected routes
@app.route('/api/tasks', methods=['POST'])
@login_required
def create_task():
    # ... existing code
```

## Security Considerations

### For Production Use
1. **Disable debug mode**: Set `app.run(debug=False)`
2. **Use environment variables**: Store sensitive configuration
3. **Add rate limiting**: Prevent abuse of the scraping API
4. **Implement authentication**: Protect access to the dashboard
5. **Use HTTPS**: Encrypt data transmission
6. **Validate inputs**: Sanitize URLs and user inputs
7. **Set up logging**: Monitor for suspicious activity

### Example Environment Configuration
```python
import os
from flask import Flask

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key')
app.config['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'sqlite:///dashboard.db')
```

## Troubleshooting

### Common Issues

1. **"Connection refused" errors**
   - Ensure the Flask app is running on port 5000
   - Check firewall settings

2. **Database errors**
   - Delete `scraping_dashboard.db` to reset the database
   - Check file permissions

3. **CORS issues**
   - Flask-CORS is configured to allow all origins
   - For production, restrict to specific domains

4. **Scraping failures**
   - Some websites block automated requests
   - Check the error logs for specific issues
   - Consider adding delays or rotating user agents

### Extending the System

#### Adding Proxy Support
```python
proxies = {
    'http': 'http://proxy.example.com:8080',
    'https': 'https://proxy.example.com:8080'
}
response = self.session.get(url, proxies=proxies, timeout=10)
```

#### Adding Scheduled Tasks
```python
import schedule
import time

def run_scheduled_tasks():
    # Add logic for recurring scraping tasks
    pass

schedule.every().hour.do(run_scheduled_tasks)
```

## Performance Tips

1. **Limit concurrent tasks**: Prevent overwhelming target servers
2. **Add delays**: Implement respectful scraping intervals
3. **Use connection pooling**: Reuse HTTP connections
4. **Implement caching**: Cache results for frequently accessed pages
5. **Add pagination**: Handle large result sets efficiently

This dashboard provides a solid foundation for web scraping operations and can be extended based on specific requirements.
