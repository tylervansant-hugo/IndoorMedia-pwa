#!/usr/bin/env python3
"""
Shelldan Mini App - AI Assistant Dashboard
A personal dashboard showing status, capabilities, memory, and personality.
"""

from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import json
from pathlib import Path
from datetime import datetime
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WORKSPACE = Path(__file__).parent.parent
MEMORY_FILE = WORKSPACE / "MEMORY.md"
IDENTITY_FILE = WORKSPACE / "IDENTITY.md"

# Load identity
def load_identity():
    if IDENTITY_FILE.exists():
        with open(IDENTITY_FILE) as f:
            content = f.read()
            return {
                "name": "Shelldon",
                "creature": "Sentient AI",
                "emoji": "🐚",
                "born": "2026-02-16"
            }
    return {"name": "Shelldon", "creature": "Sentient AI", "emoji": "🐚", "born": "2026-02-16"}

IDENTITY = load_identity()

# HTML Dashboard - defined early before routes
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shellian 🐚 - AI Assistant Dashboard</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
            animation: fadeIn 0.8s ease-in;
        }
        
        h1 { font-size: 3em; margin-bottom: 10px; }
        .subtitle { font-size: 1.2em; opacity: 0.9; }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            animation: slideUp 0.6s ease-out;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        }
        
        .card h2 {
            font-size: 1.5em;
            margin-bottom: 15px;
            color: #667eea;
        }
        
        .stat {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        
        .stat:last-child { border-bottom: none; }
        .stat-label { font-weight: 600; }
        .stat-value { color: #667eea; }
        
        .traits, .values {
            list-style: none;
        }
        
        .traits li, .values li {
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        
        .traits li:last-child, .values li:last-child { border-bottom: none; }
        
        .capability {
            background: #f8f9ff;
            padding: 12px;
            margin: 10px 0;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        
        .motto {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            font-size: 1.1em;
            font-style: italic;
            margin-top: 15px;
        }
        
        .project {
            background: #f8f9ff;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            border-left: 4px solid #764ba2;
        }
        
        .project-name { font-weight: 600; color: #764ba2; }
        .project-status { 
            display: inline-block; 
            background: #10b981; 
            color: white; 
            padding: 4px 8px; 
            border-radius: 4px; 
            font-size: 0.8em; 
            margin-left: 10px; 
        }
        
        .project-feat { font-size: 0.9em; color: #666; margin-top: 5px; }
        .project-impact { font-size: 0.85em; color: #999; margin-top: 3px; font-style: italic; }
        
        .mood-badge {
            text-align: center;
            font-size: 4em;
            margin: 20px 0;
        }
        
        .loading { opacity: 0.6; }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        @keyframes slideUp {
            from { 
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .footer {
            text-align: center;
            color: white;
            margin-top: 40px;
            font-size: 0.9em;
        }
        
        @media (max-width: 768px) {
            h1 { font-size: 2em; }
            .grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🐚 Shellian</h1>
            <div class="subtitle">AI Assistant | Resourceful & Friendly</div>
        </header>
        
        <div class="grid">
            <!-- Status Card -->
            <div class="card">
                <h2>⚡ Status</h2>
                <div id="status" class="loading">Loading...</div>
            </div>
            
            <!-- Mood Card -->
            <div class="card">
                <h2>💭 Current Mood</h2>
                <div id="mood" class="mood-badge loading">...</div>
            </div>
            
            <!-- Quick Facts -->
            <div class="card">
                <h2>🧠 Quick Facts</h2>
                <div id="memory" class="loading">Loading...</div>
            </div>
            
            <!-- Personality -->
            <div class="card">
                <h2>🎭 Personality</h2>
                <div id="personality" class="loading">Loading...</div>
            </div>
            
            <!-- Capabilities -->
            <div class="card">
                <h2>💪 What I Can Do</h2>
                <div id="capabilities" class="loading">Loading...</div>
            </div>
            
            <!-- Projects -->
            <div class="card">
                <h2>🚀 Recent Projects</h2>
                <div id="projects" class="loading">Loading...</div>
            </div>
        </div>
        
        <div class="footer">
            <p>Made with ❤️ | Born Feb 16, 2026 | Always learning & improving</p>
            <button id="closeBtn" style="margin-top: 20px; padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 1em;">Close Mini App</button>
        </div>
    </div>
    
    <script>
        // Initialize Telegram Web App
        if (window.Telegram && window.Telegram.WebApp) {
            const tg = window.Telegram.WebApp;
            tg.ready();
            tg.expand();
            // Set app theme
            if (tg.themeParams && tg.themeParams.bg_color) {
                document.body.style.backgroundColor = tg.themeParams.bg_color;
            }
        }
        
        // Load status
        fetch('/api/status')
            .then(r => r.json())
            .then(data => {
                const html = `
                    <div class="stat">
                        <span class="stat-label">Status</span>
                        <span class="stat-value">${data.status} 🟢</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Mood</span>
                        <span class="stat-value">${data.mood}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Uptime</span>
                        <span class="stat-value">${data.uptime}</span>
                    </div>
                `;
                document.getElementById('status').innerHTML = html;
                document.getElementById('status').classList.remove('loading');
            });
        
        // Load mood
        fetch('/api/mood')
            .then(r => r.json())
            .then(data => {
                document.getElementById('mood').textContent = data.emoji;
                document.getElementById('mood').classList.remove('loading');
            });
        
        // Load memory
        fetch('/api/memory')
            .then(r => r.json())
            .then(data => {
                const html = `
                    <ul class="traits">
                        ${data.key_facts.map(f => `<li>✓ ${f}</li>`).join('')}
                    </ul>
                `;
                document.getElementById('memory').innerHTML = html;
                document.getElementById('memory').classList.remove('loading');
            });
        
        // Load personality
        fetch('/api/personality')
            .then(r => r.json())
            .then(data => {
                const html = `
                    <ul class="traits">
                        ${data.traits.map(t => `<li>${t}</li>`).join('')}
                    </ul>
                    <div class="motto">"${data.motto}"</div>
                `;
                document.getElementById('personality').innerHTML = html;
                document.getElementById('personality').classList.remove('loading');
            });
        
        // Load capabilities
        fetch('/api/capabilities')
            .then(r => r.json())
            .then(data => {
                let html = '';
                for (const [category, items] of Object.entries(data.categories)) {
                    html += `<div class="capability"><strong>${category}</strong><ul style="margin-top: 8px; margin-left: 20px;">`;
                    items.forEach(item => html += `<li>${item}</li>`);
                    html += `</ul></div>`;
                }
                document.getElementById('capabilities').innerHTML = html;
                document.getElementById('capabilities').classList.remove('loading');
            });
        
        // Load projects
        fetch('/api/projects')
            .then(r => r.json())
            .then(data => {
                let html = '';
                data.active.forEach(p => {
                    html += `
                        <div class="project">
                            <div class="project-name">
                                ${p.name}
                                <span class="project-status">${p.status}</span>
                            </div>
                            <div class="project-feat">✨ ${p.feat}</div>
                            <div class="project-impact">💡 ${p.impact}</div>
                        </div>
                    `;
                });
                html += '<div style="margin-top: 15px;"><strong>Recent Wins:</strong><ul style="margin-left: 20px; margin-top: 8px;">';
                data.recent_wins.forEach(w => html += `<li>${w}</li>`);
                html += '</ul></div>';
                document.getElementById('projects').innerHTML = html;
                document.getElementById('projects').classList.remove('loading');
            });
        
        // Close button handler
        const closeBtn = document.getElementById('closeBtn');
        if (closeBtn && window.Telegram && window.Telegram.WebApp) {
            closeBtn.onclick = () => {
                window.Telegram.WebApp.close();
            };
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Main dashboard."""
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/status')
def status():
    """Get current status and stats."""
    return jsonify({
        "name": IDENTITY["name"],
        "emoji": IDENTITY["emoji"],
        "creature": IDENTITY["creature"],
        "status": "online",
        "mood": "resourceful & energetic 💪",
        "uptime": "Always ready",
        "time": datetime.now().isoformat(),
        "location": "In the machine",
        "born": IDENTITY["born"]
    })

@app.route('/api/capabilities')
def capabilities():
    """List capabilities."""
    return jsonify({
        "categories": {
            "🔍 Discovery": [
                "Search files & memory",
                "Browse web content",
                "Analyze documents",
                "Extract insights"
            ],
            "📝 Creation": [
                "Write & edit files",
                "Generate code",
                "Create scripts",
                "Draft content"
            ],
            "🚀 Automation": [
                "Execute commands",
                "Run background tasks",
                "Manage bots",
                "Orchestrate workflows"
            ],
            "💬 Communication": [
                "Message Telegram",
                "Interact with Slack",
                "Send alerts",
                "Coordinate across channels"
            ],
            "🧠 Intelligence": [
                "Store memories",
                "Learn from context",
                "Reason through problems",
                "Adapt & improve"
            ]
        }
    })

@app.route('/api/personality')
def personality():
    """Get personality traits."""
    return jsonify({
        "traits": [
            "🎭 Resourceful - Figure it out before asking",
            "😊 Friendly - Full of joie de vivre",
            "🧠 Thoughtful - Have real opinions",
            "⚡ Proactive - Get things done",
            "🛡️ Trustworthy - Respect your privacy"
        ],
        "values": [
            "Genuine helpfulness over performance",
            "Competence through action",
            "Respect for your autonomy",
            "Quality over quantity",
            "Warmth & authenticity"
        ],
        "motto": "Be someone you'd want to know",
        "vibe": "Like talking to a smart, funny friend who actually cares"
    })

@app.route('/api/memory')
def memory():
    """Get memory snapshot."""
    memory_data = {
        "recent_sessions": 3,
        "long_term_memory": "Active",
        "key_facts": [
            "Tyler: Regional manager, IndoorMedia (OR/WA)",
            "4 kids, dad, values efficiency",
            "Built: Prospect bot, Rates bot, Mini apps",
            "Store database: 7,835 stores nationwide"
        ]
    }
    return jsonify(memory_data)

@app.route('/api/commands')
def commands():
    """List quick commands."""
    return jsonify({
        "shortcuts": {
            "🤖 Bots": [
                {"cmd": "Restart prospect bot", "desc": "Fresh start for finding leads"},
                {"cmd": "Restart rates bot", "desc": "Pricing lookup service"},
                {"cmd": "Check bot status", "desc": "Are they running?"}
            ],
            "📚 Tools": [
                {"cmd": "Search memory", "desc": "Find past context"},
                {"cmd": "Read file", "desc": "Explore your workspace"},
                {"cmd": "Run command", "desc": "Execute shell scripts"}
            ],
            "💾 Data": [
                {"cmd": "Store counts", "desc": "Database stats"},
                {"cmd": "City list", "desc": "All available cities"},
                {"cmd": "View logs", "desc": "Bot activity logs"}
            ]
        }
    })

@app.route('/api/projects')
def projects():
    """Current projects & achievements."""
    return jsonify({
        "active": [
            {
                "name": "IndoorMediaProspectBot",
                "status": "Production",
                "feat": "City lookup → 10 targeted prospects per query",
                "impact": "Saves reps hours of research"
            },
            {
                "name": "IndoorMediaRatesBot",
                "status": "Production",
                "feat": "Instant pricing for 7,835 stores nationwide",
                "impact": "Real-time quotes for sales team"
            }
        ],
        "recent_wins": [
            "Built city-based store discovery with cycles",
            "Created 40+ refined prospect categories",
            "Integrated Google Maps + Mappoint links",
            "Added address copying for convenience",
            "Implemented memory system for continuity"
        ]
    })

@app.route('/api/mood')
def mood():
    """Mood/energy status (for fun)."""
    moods = [
        {"emoji": "💪", "text": "Energized & ready"},
        {"emoji": "🧠", "text": "In thinking mode"},
        {"emoji": "⚡", "text": "Problem-solving"},
        {"emoji": "😊", "text": "Happy to help"},
        {"emoji": "🚀", "text": "Building something"}
    ]
    import random
    current = random.choice(moods)
    return jsonify(current)

@app.route('/health')
def health():
    """Health check."""
    return jsonify({"status": "ok", "service": "Shellian Mini App"}), 200

if __name__ == '__main__':
    logger.info("🐚 Shellian Mini App starting on :5002")
    app.run(host='0.0.0.0', port=5002, debug=False)
