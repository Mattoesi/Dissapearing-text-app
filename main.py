from flask import Flask, render_template, flash, redirect, url_for, request, send_file, Response
from story_prompts import prompts
import os
from dotenv import load_dotenv
import random
from datetime import datetime, timedelta
import time
import threading
import json

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

current_text = ""
last_input_time = datetime.now()
session_active = False
current_prompt = "Generate a prompt to start writing..."

def disappearing_text_thread():
    global current_text, last_input_time, session_active
    while session_active:
        time.sleep(1)  # Check every second
        if (datetime.now() - last_input_time).total_seconds() > 5:
            words = current_text.split()
            if words:
                words.pop()
                current_text = ' '.join(words)
        if not current_text:
            session_active = False

@app.route('/', methods=['GET', 'POST'])
def index():
    global current_text, last_input_time, session_active, current_prompt
    
    if request.method == 'POST':    
        if 'generate' in request.form:
            current_prompt = random.choice(prompts) + "..."
        elif 'user_input' in request.form:
            new_text = request.form['user_input']
            if new_text != current_text:
                if not session_active:
                    session_active = True
                    threading.Thread(target=disappearing_text_thread, daemon=True).start()
                current_text = new_text
                last_input_time = datetime.now()
    
    return render_template('index.html', 
                           prompt=current_prompt, 
                           current_text=current_text, 
                           words_left=len(current_text.split()),
                           session_active=session_active)

@app.route('/save', methods=['POST'])
def save():
    global current_text, session_active
    
    filename = f"story_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(os.path.join('stories', filename), 'w') as f:
        f.write(current_text)
    
    session_active = False
    return redirect(url_for('view_story', filename=filename))

@app.route('/view/<filename>')
def view_story(filename):
    return send_file(os.path.join('stories', filename), as_attachment=True)

@app.route('/stream')
def stream():
    def event_stream():
        global current_text, session_active
        while True:
            data = json.dumps({
                'text': current_text,
                'words_left': len(current_text.split()),
                'session_active': session_active
            })
            yield f"data: {data}\n\n"
            time.sleep(1)
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/update', methods=['POST'])
def update():
    global current_text, last_input_time, session_active
    
    new_text = request.form['user_input']
    if new_text != current_text:
        if not session_active:
            session_active = True
            threading.Thread(target=disappearing_text_thread, daemon=True).start()
        current_text = new_text
        last_input_time = datetime.now()
    
    return '', 204

if __name__ == '__main__':
    os.makedirs('stories', exist_ok=True)
    app.run(debug=True)