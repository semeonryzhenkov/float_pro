import os
import json
import io
from flask import render_template, request, redirect, url_for, jsonify, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image, ImageDraw
from main import app
from models import db, User, Project


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json() or request.form
        email = data.get('email')
        password = data.get('password')
        if User.query.filter_by(email=email).first():
            if request.is_json:
                return jsonify({'error': 'Email exists'}), 400
            return redirect(url_for('register'))
        user = User(email=email, password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        if request.is_json:
            return jsonify({'success': True})
        return redirect(url_for('dashboard'))
    return render_template('login.html', register=True)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() or request.form
        email = data.get('email')
        password = data.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            if request.is_json:
                return jsonify({'success': True})
            return redirect(url_for('dashboard'))
        if request.is_json:
            return jsonify({'error': 'Invalid credentials'}), 401
        return redirect(url_for('login'))
    return render_template('login.html', register=False)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if user is None:
        # Пользователь не найден (возможно, был удален), очищаем сессию
        session.pop('user_id', None)
        return redirect(url_for('login'))
    
    projects = Project.query.filter_by(user_id=user.id).order_by(Project.updated_at.desc()).all()
    return render_template('dashboard.html', projects=projects)


@app.route('/project/new', methods=['POST'])
def create_project():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json() or request.form
    name = data.get('name', 'New Project')
    project = Project(name=name, user_id=session['user_id'], data='{}')
    db.session.add(project)
    db.session.commit()
    if request.is_json:
        return jsonify({'id': project.id, 'name': project.name})
    return redirect(url_for('editor', project_id=project.id))


@app.route('/project/<int:project_id>')
def editor(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    project = Project.query.filter_by(id=project_id, user_id=session['user_id']).first_or_404()
    return render_template('editor.html', project=project)


@app.route('/api/project/<int:project_id>', methods=['GET'])
def get_project(project_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    project = Project.query.filter_by(id=project_id, user_id=session['user_id']).first_or_404()
    return jsonify({'id': project.id, 'name': project.name, 'data': json.loads(project.data or '{}')})


@app.route('/api/project/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    project = Project.query.filter_by(id=project_id, user_id=session['user_id']).first_or_404()
    data = request.get_json()
    if 'name' in data:
        project.name = data['name']
    if 'data' in data:
        project.data = json.dumps(data['data'])
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/project/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    project = Project.query.filter_by(id=project_id, user_id=session['user_id']).first_or_404()
    db.session.delete(project)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/project/<int:project_id>/copy', methods=['POST'])
def copy_project(project_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    project = Project.query.filter_by(id=project_id, user_id=session['user_id']).first_or_404()
    new_project = Project(
        name=project.name + ' (Copy)',
        data=project.data,
        user_id=session['user_id']
    )
    db.session.add(new_project)
    db.session.commit()
    return jsonify({'id': new_project.id, 'name': new_project.name})


@app.route('/api/project/<int:project_id>/export/png')
def export_png(project_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    project = Project.query.filter_by(id=project_id, user_id=session['user_id']).first_or_404()
    data = json.loads(project.data or '{}')
    img = Image.new('RGB', (2000, 2000), 'white')
    draw = ImageDraw.Draw(img)
    
    walls = data.get('walls', [])
    for wall in walls:
        x1, y1 = wall.get('x1', 0), wall.get('y1', 0)
        x2, y2 = wall.get('x2', 0), wall.get('y2', 0)
        th = wall.get('thickness', 20)
        
        import math
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx * dx + dy * dy)
        if length == 0:
            continue
        
        nx = -dy / length
        ny = dx / length
        hw = th / 2
        
        points = [
            (x1 + nx * hw, y1 + ny * hw),
            (x2 + nx * hw, y2 + ny * hw),
            (x2 - nx * hw, y2 - ny * hw),
            (x1 - nx * hw, y1 - ny * hw)
        ]
        draw.polygon(points, fill='white', outline='black')
        
        spacing = 8
        t = -hw + 2
        while t < hw:
            offsetX = nx * t
            offsetY = ny * t
            draw.line([
                (x1 + offsetX, y1 + offsetY),
                (x2 + offsetX, y2 + offsetY)
            ], fill='black', width=1)
            t += spacing
        
        draw.ellipse([x1-3, y1-3, x1+3, y1+3], fill='black', outline='black')
        draw.ellipse([x2-3, y2-3, x2+3, y2+3], fill='black', outline='black')
    
    windows = data.get('windows', [])
    for win in windows:
        x, y = win.get('x', 0), win.get('y', 0)
        wall = None
        min_dist = 30
        for w in walls:
            wx1, wy1 = w.get('x1', 0), w.get('y1', 0)
            wx2, wy2 = w.get('x2', 0), w.get('y2', 0)
            A = x - wx1
            B = y - wy1
            C = wx2 - wx1
            D = wy2 - wy1
            dot = A * C + B * D
            lenSq = C * C + D * D
            if lenSq != 0:
                param = dot / lenSq
                param = max(0, min(1, param))
                projx = wx1 + param * C
                projy = wy1 + param * D
                dist = math.sqrt((x-projx)**2 + (y-projy)**2)
                if dist < min_dist:
                    min_dist = dist
                    angle = math.atan2(wy2 - wy1, wx2 - wx1)
        
        cos_a = math.cos(angle) if wall else 1
        sin_a = math.sin(angle) if wall else 0
        
        def rot(px, py):
            return (x + (px - x) * cos_a - (py - y) * sin_a,
                    y + (px - x) * sin_a + (py - y) * cos_a)
        
        pts = [rot(x-12, y-5), rot(x+12, y-5), rot(x+12, y+5), rot(x-12, y+5)]
        draw.polygon(pts, fill='white', outline='black')
        draw.line([rot(x-8, y-5), rot(x-8, y+5)], fill='black', width=2)
        draw.line([rot(x, y-5), rot(x, y+5)], fill='black', width=2)
        draw.line([rot(x+8, y-5), rot(x+8, y+5)], fill='black', width=2)
    
    doors = data.get('doors', [])
    for door in doors:
        x, y = door.get('x', 0), door.get('y', 0)
        door_len = door.get('length', 20)
        
        wall = None
        min_dist = 30
        angle = 0
        for w in walls:
            wx1, wy1 = w.get('x1', 0), w.get('y1', 0)
            wx2, wy2 = w.get('x2', 0), w.get('y2', 0)
            A = x - wx1
            B = y - wy1
            C = wx2 - wx1
            D = wy2 - wy1
            dot = A * C + B * D
            lenSq = C * C + D * D
            if lenSq != 0:
                param = dot / lenSq
                param = max(0, min(1, param))
                projx = wx1 + param * C
                projy = wy1 + param * D
                dist = math.sqrt((x-projx)**2 + (y-projy)**2)
                if dist < min_dist:
                    min_dist = dist
                    angle = math.atan2(wy2 - wy1, wx2 - wx1)
        
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        def rot_door(px, py):
            return (x + (px - x) * cos_a - (py - y) * sin_a,
                    y + (px - x) * sin_a + (py - y) * cos_a)
        
        draw.arc([x-door_len, y-door_len, x+door_len, y+door_len], 0, 90, fill='black', width=2)
        draw.line([rot_door(x, y), rot_door(x+door_len, y)], fill='black', width=2)
        draw.line([rot_door(x-door_len, y), rot_door(x+door_len, y)], fill='gray', width=1)
    
    labels = data.get('labels', [])
    for lbl in labels:
        lx, ly = lbl.get('x', 0), lbl.get('y', 0)
        txt = lbl.get('text', '')
        try:
            from PIL import ImageFont
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        except:
            font = ImageFont.load_default()
        draw.text((lx, ly), txt, fill='black', font=font)
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png', as_attachment=True, download_name=f'{project.name}.png')


@app.route('/api/project/<int:project_id>/export/json')
def export_json(project_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    project = Project.query.filter_by(id=project_id, user_id=session['user_id']).first_or_404()
    return send_file(
        io.BytesIO(project.data.encode()),
        mimetype='application/json',
        as_attachment=True,
        download_name=f'{project.name}.json'
    )
