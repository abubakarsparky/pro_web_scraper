from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import json
import sqlite3
import threading
import time
from datetime import datetime
import uuid
import re
from urllib.parse import urljoin, urlparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)


# Database setup
def init_db():
    conn = sqlite3.connect('scraping_dashboard.db')
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            config TEXT,
            error_message TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id TEXT PRIMARY KEY,
            task_id TEXT,
            url TEXT,
            title TEXT,
            content TEXT,
            links TEXT,
            images TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT,
            level TEXT,
            message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        )
    ''')

    conn.commit()
    conn.close()


class WebScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def scrape_url(self, url, config=None):
        """Scrape a single URL and return structured data"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract basic information
            title = soup.find('title')
            title = title.get_text().strip() if title else 'No title'

            # Extract text content
            for script in soup(["script", "style"]):
                script.decompose()
            content = soup.get_text()
            content = re.sub(r'\s+', ' ', content).strip()[:5000]  # Limit content length

            # Extract links
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('http'):
                    links.append(href)
                elif href.startswith('/'):
                    links.append(urljoin(url, href))

            # Extract images
            images = []
            for img in soup.find_all('img', src=True):
                src = img['src']
                if src.startswith('http'):
                    images.append(src)
                elif src.startswith('/'):
                    images.append(urljoin(url, src))

            return {
                'success': True,
                'title': title,
                'content': content,
                'links': links[:50],  # Limit links
                'images': images[:20],  # Limit images
                'status_code': response.status_code
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


def log_message(task_id, level, message):
    """Log a message to the database"""
    conn = sqlite3.connect('scraping_dashboard.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO logs (task_id, level, message) VALUES (?, ?, ?)',
        (task_id, level, message)
    )
    conn.commit()
    conn.close()


def scrape_task_worker(task_id, url, config):
    """Worker function to handle scraping tasks"""
    scraper = WebScraper()

    try:
        # Update task status
        conn = sqlite3.connect('scraping_dashboard.db')
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE tasks SET status = ? WHERE id = ?',
            ('running', task_id)
        )
        conn.commit()
        conn.close()

        log_message(task_id, 'INFO', f'Starting scrape of {url}')

        # Perform scraping
        result = scraper.scrape_url(url, config)

        if result['success']:
            # Save results
            result_id = str(uuid.uuid4())
            conn = sqlite3.connect('scraping_dashboard.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO results (id, task_id, url, title, content, links, images)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                result_id, task_id, url, result['title'], result['content'],
                json.dumps(result['links']), json.dumps(result['images'])
            ))

            # Update task status
            cursor.execute(
                'UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?',
                ('completed', datetime.now(), task_id)
            )

            conn.commit()
            conn.close()

            log_message(task_id, 'INFO', f'Successfully scraped {url}')

        else:
            # Update task with error
            conn = sqlite3.connect('scraping_dashboard.db')
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE tasks SET status = ?, error_message = ?, completed_at = ? WHERE id = ?',
                ('failed', result['error'], datetime.now(), task_id)
            )
            conn.commit()
            conn.close()

            log_message(task_id, 'ERROR', f'Failed to scrape {url}: {result["error"]}')

    except Exception as e:
        # Handle unexpected errors
        conn = sqlite3.connect('scraping_dashboard.db')
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE tasks SET status = ?, error_message = ?, completed_at = ? WHERE id = ?',
            ('failed', str(e), datetime.now(), task_id)
        )
        conn.commit()
        conn.close()

        log_message(task_id, 'ERROR', f'Unexpected error: {str(e)}')


@app.route('/')
def index():
    return render_template('dashboard.html')


@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Get all scraping tasks"""
    conn = sqlite3.connect('scraping_dashboard.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, url, name, status, created_at, completed_at, error_message
        FROM tasks
        ORDER BY created_at DESC
    ''')

    tasks = []
    for row in cursor.fetchall():
        tasks.append({
            'id': row[0],
            'url': row[1],
            'name': row[2],
            'status': row[3],
            'created_at': row[4],
            'completed_at': row[5],
            'error_message': row[6]
        })

    conn.close()
    return jsonify(tasks)


@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Create a new scraping task"""
    data = request.json

    if not data or not data.get('url'):
        return jsonify({'error': 'URL is required'}), 400

    task_id = str(uuid.uuid4())
    url = data['url']
    name = data.get('name', f'Scrape {urlparse(url).netloc}')
    config = data.get('config', {})

    # Save task to database
    conn = sqlite3.connect('scraping_dashboard.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tasks (id, url, name, config)
        VALUES (?, ?, ?, ?)
    ''', (task_id, url, name, json.dumps(config)))
    conn.commit()
    conn.close()

    # Start scraping in background thread
    thread = threading.Thread(target=scrape_task_worker, args=(task_id, url, config))
    thread.daemon = True
    thread.start()

    return jsonify({'task_id': task_id, 'status': 'created'})


@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """Get a specific task"""
    conn = sqlite3.connect('scraping_dashboard.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, url, name, status, created_at, completed_at, config, error_message
        FROM tasks
        WHERE id = ?
    ''', (task_id,))

    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Task not found'}), 404

    task = {
        'id': row[0],
        'url': row[1],
        'name': row[2],
        'status': row[3],
        'created_at': row[4],
        'completed_at': row[5],
        'config': json.loads(row[6]) if row[6] else {},
        'error_message': row[7]
    }

    conn.close()
    return jsonify(task)


@app.route('/api/tasks/<task_id>/results', methods=['GET'])
def get_task_results(task_id):
    """Get results for a specific task"""
    conn = sqlite3.connect('scraping_dashboard.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, url, title, content, links, images, scraped_at
        FROM results
        WHERE task_id = ?
        ORDER BY scraped_at DESC
    ''', (task_id,))

    results = []
    for row in cursor.fetchall():
        results.append({
            'id': row[0],
            'url': row[1],
            'title': row[2],
            'content': row[3],
            'links': json.loads(row[4]) if row[4] else [],
            'images': json.loads(row[5]) if row[5] else [],
            'scraped_at': row[6]
        })

    conn.close()
    return jsonify(results)


@app.route('/api/tasks/<task_id>/logs', methods=['GET'])
def get_task_logs(task_id):
    """Get logs for a specific task"""
    conn = sqlite3.connect('scraping_dashboard.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT level, message, timestamp
        FROM logs
        WHERE task_id = ?
        ORDER BY timestamp DESC
    ''', (task_id,))

    logs = []
    for row in cursor.fetchall():
        logs.append({
            'level': row[0],
            'message': row[1],
            'timestamp': row[2]
        })

    conn.close()
    return jsonify(logs)


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get dashboard statistics"""
    conn = sqlite3.connect('scraping_dashboard.db')
    cursor = conn.cursor()

    # Get task counts by status
    cursor.execute('SELECT status, COUNT(*) FROM tasks GROUP BY status')
    status_counts = dict(cursor.fetchall())

    # Get total tasks
    cursor.execute('SELECT COUNT(*) FROM tasks')
    total_tasks = cursor.fetchone()[0]

    # Get total results
    cursor.execute('SELECT COUNT(*) FROM results')
    total_results = cursor.fetchone()[0]

    # Get recent activity
    cursor.execute('''
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM tasks
        WHERE created_at >= datetime('now', '-7 days')
        GROUP BY DATE(created_at)
        ORDER BY date DESC
    ''')
    recent_activity = [{'date': row[0], 'count': row[1]} for row in cursor.fetchall()]

    conn.close()

    return jsonify({
        'total_tasks': total_tasks,
        'total_results': total_results,
        'status_counts': status_counts,
        'recent_activity': recent_activity
    })


@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task and its results"""
    conn = sqlite3.connect('scraping_dashboard.db')
    cursor = conn.cursor()

    # Delete results first (foreign key constraint)
    cursor.execute('DELETE FROM results WHERE task_id = ?', (task_id,))
    cursor.execute('DELETE FROM logs WHERE task_id = ?', (task_id,))
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))

    conn.commit()
    conn.close()

    return jsonify({'status': 'deleted'})


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)