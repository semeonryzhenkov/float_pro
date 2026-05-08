import os
import json
import math
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash
from models import db, User, Project
from functools import wraps

# Создание блюпринта
routes_bp = Blueprint('routes', __name__)

# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему.', 'warning')
            return redirect(url_for('routes.login'))
        user = User.query.get(session['user_id'])
        if not user:
            session.clear()
            flash('Пользователь не найден. Войдите снова.', 'error')
            return redirect(url_for('routes.login'))
        return f(user, *args, **kwargs)
    return decorated_function

@routes_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('routes.dashboard'))
    return redirect(url_for('routes.login'))

@routes_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        # Простая логика для примера (в реальном проекте нужна проверка пароля и хеширование)
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()
        
        session['user_id'] = user.id
        flash('Вы успешно вошли!', 'success')
        return redirect(url_for('routes.dashboard'))
    return render_template('login.html')

@routes_bp.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('routes.login'))

@routes_bp.route('/dashboard')
@login_required
def dashboard(user):
    projects = Project.query.filter_by(user_id=user.id).order_by(Project.updated_at.desc()).all()
    return render_template('dashboard.html', projects=projects, user=user)

@routes_bp.route('/editor/<int:project_id>')
@login_required
def editor(user, project_id):
    project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
    return render_template('editor.html', project=project, user=user)

@routes_bp.route('/api/projects', methods=['POST'])
@login_required
def create_project(user):
    data = request.json
    name = data.get('name', 'Новый проект')
    new_project = Project(name=name, user_id=user.id, data={})
    db.session.add(new_project)
    db.session.commit()
    return jsonify({'id': new_project.id, 'name': new_project.name}), 201

@routes_bp.route('/api/project/<int:project_id>', methods=['GET'])
@login_required
def get_project(user, project_id):
    project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
    return jsonify({
        'id': project.id,
        'name': project.name,
        'data': project.data or {},
        'updated_at': project.updated_at.isoformat()
    })

@routes_bp.route('/api/project/<int:project_id>', methods=['PUT'])
@login_required
def update_project_name(user, project_id):
    project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
    data = request.json
    if 'name' in data:
        project.name = data['name']
        db.session.commit()
    return jsonify({'message': 'Имя обновлено'})

@routes_bp.route('/api/project/<int:project_id>/save', methods=['POST'])
@login_required
def save_project_data(user, project_id):
    """Эндпоинт для сохранения данных плана"""
    project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
    data = request.json
    
    if 'canvas_data' in data:
        project.data = data['canvas_data']
        project.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'message': 'Проект успешно сохранен', 'time': project.updated_at.isoformat()})
    
    return jsonify({'error': 'Нет данных для сохранения'}), 400

@routes_bp.route('/api/project/<int:project_id>', methods=['DELETE'])
@login_required
def delete_project(user, project_id):
    project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
    db.session.delete(project)
    db.session.commit()
    return jsonify({'message': 'Проект удален'})

@routes_bp.route('/api/project/<int:project_id>/stats')
@login_required
def get_project_stats(user, project_id):
    project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
    data = project.data or {}
    
    walls = data.get('walls', [])
    windows = data.get('windows', [])
    doors = data.get('doors', [])
    rooms = data.get('rooms', [])
    labels = data.get('labels', [])
    
    total_wall_length = 0
    for wall in walls:
        x1, y1 = wall.get('x1', 0), wall.get('y1', 0)
        x2, y2 = wall.get('x2', 0), wall.get('y2', 0)
        length = math.sqrt((x2 - x1)**2 + **(y2 - y1)2)
        total_wall_length += length

    stats = {
        'walls_count': len(walls),
        'windows_count': len(windows),
        'doors_count': len(doors),
        'rooms_count': len(rooms),
        'labels_count': len(labels),
        'total_wall_length': round(total_wall_length, 2),
        'estimated_area': round(total_wall_length * 0.5, 2) # Примерная оценка
    }
    return jsonify(stats)


<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ArchiPlan Studio - {{ project.name }}</title>
    <style>
        :root {
            --bg-color: #f0f2f5;
            --panel-bg: #ffffff;
            --text-color: #333;
            --accent-color: #4a90e2;
            --border-color: #ddd;
            --grid-color: #e0e0e0;
            --tool-hover: #f5f7fa;
        }

        body.dark-mode {
            --bg-color: #1a1a1a;
            --panel-bg: #2d2d2d;
            --text-color: #e0e0e0;
            --accent-color: #64b5f6;
            --border-color: #444;
            --grid-color: #333;
            --tool-hover: #3d3d3d;
        }

        body {
            margin: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            overflow: hidden;
            transition: background 0.3s, color 0.3s;
            display: flex;
            flex-direction: column;
            height: 100vh;
        }

        /* Header */
        header {
            background: var(--panel-bg);
            border-bottom: 1px solid var(--border-color);
            padding: 10px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            z-index: 100;
        }

        .logo {
            font-size: 1.2rem;
            font-weight: bold;
            background: linear-gradient(45deg, #4a90e2, #9013fe);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .controls {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        button {
            background: var(--panel-bg);
            border: 1px solid var(--border-color);
            color: var(--text-color);
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        button:hover {
            background: var(--tool-hover);
            border-color: var(--accent-color);
        }

        button.primary {
            background: var(--accent-color);
            color: white;
            border: none;
        }

        button.primary:hover {
            opacity: 0.9;
        }

        /* Main Layout */
        .workspace {
            display: flex;
            flex: 1;
            position: relative;
            overflow: hidden;
        }

        /* Toolbar */
        .toolbar {
            width: 60px;
            background: var(--panel-bg);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            align-items: center;
            padding-top: 10px;
            gap: 10px;
            z-index: 90;
        }

        .tool-btn {
            width: 40px;
            height: 40px;
            border-radius: 8px;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 1.2rem;
            cursor: pointer;
            border: 1px solid transparent;
            transition: all 0.2s;
        }

        .tool-btn.active {
            background: var(--accent-color);
            color: white;
            box-shadow: 0 2px 8px rgba(74, 144, 226, 0.4);
        }

        .tool-btn:hover:not(.active) {
            background: var(--tool-hover);
        }

        /* Canvas Area */
        .canvas-container {
            flex: 1;
            position: relative;
            background-color: var(--bg-color);
            overflow: hidden;
            cursor: crosshair;
        }

        canvas {
            display: block;
        }

        /* Mini Map */
        .mini-map-container {
            position: absolute;
            bottom: 20px;
            right: 20px;
            width: 200px;
            height: 150px;
            background: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            overflow: hidden;
            z-index: 80;
            pointer-events: none; /* Чтобы клики проходили сквозь, если нужно, или сделать интерактивной */
        }
        
        .mini-map-label {
            position: absolute;
            top: 5px;
            left: 5px;
            font-size: 10px;
            color: var(--text-color);
            background: rgba(0,0,0,0.5);
            color: white;
            padding: 2px 4px;
            border-radius: 4px;
        }

        /* Context Menu for Selection */
        .context-menu {
            position: absolute;
            background: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            padding: 5px;
            display: none;
            flex-direction: column;
            gap: 5px;
            z-index: 200;
            min-width: 120px;
        }

        .context-menu button {
            width: 100%;
            justify-content: flex-start;
            font-size: 0.85rem;
            padding: 6px 10px;
        }

        /* Properties Panel (Right) */
        .properties-panel {
            width: 250px;
            background: var(--panel-bg);
            border-left: 1px solid var(--border-color);
            padding: 15px;
            overflow-y: auto;
            z-index: 90;
        }

        .prop-group {
            margin-bottom: 20px;
        }

        .prop-group h3 {
            font-size: 0.9rem;
            margin-bottom: 10px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 5px;
        }

        .prop-item {
            margin-bottom: 10px;
            display: flex;
            flex-direction: column;
            gap: 5px;
        }

        .prop-item label {
            font-size: 0.8rem;
            color: var(--text-color);
            opacity: 0.8;
        }

        input[type="text"], input[type="number"], input[type="range"] {
            width: 100%;
            padding: 6px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            background: var(--bg-color);
            color: var(--text-color);
            box-sizing: border-box;
        }

        /* Notifications */
        .notification {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #333;
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            opacity: 0;
            transition: opacity 0.3s;
            pointer-events: none;
            z-index: 1000;
        }
        .notification.show { opacity: 1; }
        .notification.success { background: #4caf50; }
        .notification.error { background: #f44336; }

        /* Shortcuts Hint */
        .shortcuts-hint {
            position: absolute;
            bottom: 10px;
            left: 70px;
            font-size: 0.75rem;
            color: var(--text-color);
            opacity: 0.6;
            pointer-events: none;
        }
    </style>
</head>
<body>

<header>
    <div class="logo">
        <span>🏠</span> ArchiPlan Studio
    </div>
    <div class="controls">
        <button onclick="toggleTheme()" title="Тема">🌓</button>
        <button onclick="undo()" title="Отменить (Ctrl+Z)">↩️</button>
        <button onclick="redo()" title="Повторить (Ctrl+Y)">↪️</button>
        <div style="width: 1px; height: 20px; background: var(--border-color); margin: 0 5px;"></div>
        <button class="primary" onclick="saveProject()" title="Сохранить (Ctrl+S)">💾 Сохранить</button>
        <button onclick="window.location.href='/dashboard'" title="Назад">🏠 Выход</button>
    </div>
</header>

<div class="workspace">
    <!-- Toolbar -->
    <div class="toolbar">
        <div class="tool-btn active" id="tool-select" onclick="setTool('select')" title="Выделение (V)">✋</div>
        <div class="tool-btn" id="tool-wall" onclick="setTool('wall')" title="Стена (W)">🧱</div>
        <div class="tool-btn" id="tool-window" onclick="setTool('window')" title="Окно (O)">🪟</div>
        <div class="tool-btn" id="tool-door" onclick="setTool('door')" title="Дверь (D)">🚪</div>
        <div class="tool-btn" id="tool-room" onclick="setTool('room')" title="Комната (R)">⭕</div>
        <div class="tool-btn" id="tool-label" onclick="setTool('label')" title="Текст (T)">📝</div>
    </div>

    <!-- Canvas -->
    <div class="canvas-container" id="canvasContainer">
        <canvas id="mainCanvas"></canvas>
        <div class="shortcuts-hint">V: Выделение | W: Стена | O: Окно | D: Дверь | R: Комната | Del: Удалить</div>
        
        <!-- Context Menu -->
        <div id="contextMenu" class="context-menu">
            <button onclick="duplicateSelection()">📋 Дублировать</button>
            <button onclick="deleteSelection()" style="color: red;">🗑️ Удалить</button>
            <button onclick="closeContextMenu()">❌ Закрыть</button>
        </div>

        <!-- Mini Map -->
        <div class="mini-map-container">
            <div class="mini-map-label">Мини-карта</div>
            <canvas id="miniMapCanvas" width="200" height="150"></canvas>
        </div>
    </div>

    <!-- Properties Panel -->
    <div class="properties-panel">
        <div class="prop-group" id="prop-general">
            <h3>Свойства проекта</h3>
            <div class="prop-item">
                <label>Название</label>
                <input type="text" id="projName" value="{{ project.name }}" onchange="updateProjectName(this.value)">
            </div>
        </div>

        <div class="prop-group" id="prop-selection" style="display: none;">
            <h3>Выбранный объект</h3>
            <div class="prop-item">
                <label>Тип</label>
                <input type="text" id="objType" disabled>
            </div>
            <div class="prop-item" id="prop-name-group">
                <label>Название / Текст</label>
                <input type="text" id="objName" oninput="updateObjectProperty('name', this.value)">
            </div>
            <div class="prop-item" id="prop-thickness-group">
                <label>Толщина стены: <span id="thickVal">10</span> см</label>
                <input type="range" id="objThickness" min="5" max="50" value="10" oninput="updateObjectProperty('thickness', this.value); document.getElementById('thickVal').innerText=this.value">
            </div>
            <div class="prop-item">
                <label>Цвет</label>
                <input type="color" id="objColor" style="width:100%; height:30px; border:none;" oninput="updateObjectProperty('color', this.value)">
            </div>
        </div>
        
        <div class="prop-group">
            <h3>Статистика</h3>
            <div id="statsInfo" style="font-size: 0.85rem; line-height: 1.6;">
                Загрузка...
            </div>
        </div>
    </div>
</div>

<div id="notification" class="notification">Сохранено!</div>

<script>
    // --- Глобальные переменные ---
    const canvas = document.getElementById('mainCanvas');
    const ctx = canvas.getContext('2d');
    const miniMapCanvas = document.getElementById('miniMapCanvas');
    const miniMapCtx = miniMapCanvas.getContext('2d');
    const container = document.getElementById('canvasContainer');

    let currentTool = 'select';
    let isDark = false;
    let scale = 20; // Пикселей на единицу (см)
    let offsetX = 100;
    let offsetY = 100;
    
    // Данные проекта
    let projectData = {
        walls: [],
        windows: [],
        doors: [],
        rooms: [],
        labels: []
    };

    // Состояние взаимодействия
    let isDragging = false;
    let dragStart = { x: 0, y: 0 };
    let currentElement = null; // Элемент, который рисуется сейчас
    let selectedElement = null; // Выбранный элемент
    let selectionBox = null; // Для выделения рамкой

    // Undo/Redo
    let history = [];
    let historyStep = -1;
    const MAX_HISTORY = 50;

    // Инициализация
    function init() {
        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);
        
        // Загрузка данных
        loadProjectData();

        // Обработчики событий мыши
        canvas.addEventListener('mousedown', handleMouseDown);
        canvas.addEventListener('mousemove', handleMouseMove);
        canvas.addEventListener('mouseup', handleMouseUp);
        canvas.addEventListener('dblclick', handleDoubleClick);
        canvas.addEventListener('contextmenu', e => e.preventDefault());

        // Горячие клавиши
        document.addEventListener('keydown', handleKeyDown);

        // Запуск цикла отрисовки
        requestAnimationFrame(drawLoop);
        
        // Обновление статистики
        updateStats();
    }

    function resizeCanvas() {
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
        draw();
    }

    async function loadProjectData() {
        try {
            const response = await fetch(`/api/project/{{ project.id }}`);
            if (response.ok) {
                const data = await response.json();
                if (data.data && Object.keys(data.data).length > 0) {
                    projectData = data.data;
                }
                saveState(); // Сохраняем начальное состояние в историю
            }
        } catch (e) {
            console.error("Ошибка загрузки:", e);
            showNotification("Ошибка загрузки данных", "error");
        }
        draw();
    }

    // --- Инструменты ---

    function setTool(tool) {
        currentTool = tool;
        selectedElement = null;
        closeContextMenu();
        document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
        document.getElementById(`tool-${tool}`).classList.add('active');
        document.getElementById('prop-selection').style.display = 'none';
        draw();
    }

    // --- Логика Мыши ---

    function getMousePos(e) {
        const rect = canvas.getBoundingClientRect();
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    }

    function screenToWorld(x, y) {
        return {
            x: (x - offsetX) / scale,
            y: (y - offsetY) / scale
        };
    }

    function worldToScreen(x, y) {
        return {
            x: x * scale + offsetX,
            y: y * scale + offsetY
        };
    }

    function handleMouseDown(e) {
        const pos = getMousePos(e);
        const worldPos = screenToWorld(pos.x, pos.y);

        if (currentTool === 'select') {
            // Проверка попадания в объект (с конца списка, чтобы брать верхние)
            let clicked = null;
            
            // Проверка комнат (кружков)
            for (let i = projectData.rooms.length - 1; i >= 0; i--) {
                const r = projectData.rooms[i];
                const center = getRoomCenter(r.points);
                const dist = Math.sqrt((worldPos.x - center.x)**2 + (worldPos.y - center.y)**2);
                if (dist <= (r.radius || 20)) {
                    clicked = { type: 'room', index: i, data: r };
                    break;
                }
            }

            // Проверка стен, окон, дверей, меток
            if (!clicked) {
                const allElements = [
                    ...projectData.walls.map((w, i) => ({ type: 'wall', index: i, data: w })),
                    ...projectData.windows.map((w, i) => ({ type: 'window', index: i, data: w })),
                    ...projectData.doors.map((d, i) => ({ type: 'door', index: i, data: d })),
                    ...projectData.labels.map((l, i) => ({ type: 'label', index: i, data: l }))
                ];

                for (let el of allElements) {
                    if (isPointInElement(worldPos, el)) {
                        clicked = el;
                        break;
                    }
                }
            }

            if (clicked) {
                selectedElement = clicked;
                showProperties(clicked);
                isDragging = true;
                dragStart = { x: worldPos.x, y: worldPos.y };
                // Запоминаем начальные координаты элемента для перемещения
                if (clicked.type === 'wall') {
                    dragStart.original = { x1: clicked.data.x1, y1: clicked.data.y1, x2: clicked.data.x2, y2: clicked.data.y2 };
                } else if (clicked.type === 'room') {
                     // Для комнаты запоминаем смещение центра
                     const center = getRoomCenter(clicked.data.points);
                     dragStart.originalCenter = center;
                } else {
                    dragStart.original = { x: clicked.data.x, y: clicked.data.y };
                }
            } else {
                selectedElement = null;
                closeContextMenu();
                document.getElementById('prop-selection').style.display = 'none';
                // Начало выделения рамкой
                selectionBox = { start: worldPos, end: worldPos };
            }
        } 
        else if (currentTool === 'wall') {
            currentElement = { x1: worldPos.x, y1: worldPos.y, x2: worldPos.x, y2: worldPos.y, thickness: 10 };
            isDragging = true;
        }
        else if (currentTool === 'room') {
            // Создаем комнату с начальной точкой
            currentElement = { points: [{x: worldPos.x, y: worldPos.y}], name: "Комната", radius: 20 };
            isDragging = true;
        }
        else if (['window', 'door', 'label'].includes(currentTool)) {
            // Размещение точкой
            const newObj = { x: worldPos.x, y: worldPos.y };
            if (currentTool === 'label') newObj.text = "Текст";
            if (currentTool === 'window') newObj.width = 100; // см
            if (currentTool === 'door') newObj.width = 90;
            
            addToList(currentTool + 's', newObj);
            saveState();
            draw();
        }
    }

    function handleMouseMove(e) {
        const pos = getMousePos(e);
        const worldPos = screenToWorld(pos.x, pos.y);

        if (isDragging) {
            if (currentTool === 'select' && selectedElement) {
                // Перемещение объекта
                const dx = worldPos.x - dragStart.x;
                const dy = worldPos.y - dragStart.y;

                if (selectedElement.type === 'wall') {
                    const orig = dragStart.original;
                    selectedElement.data.x1 = orig.x1 + dx;
                    selectedElement.data.y1 = orig.y1 + dy;
                    selectedElement.data.x2 = orig.x2 + dx;
                    selectedElement.data.y2 = orig.y2 + dy;
                } else if (selectedElement.type === 'room') {
                    const origCenter = dragStart.originalCenter;
                    const newCenter = { x: origCenter.x + dx, y: origCenter.y + dy };
                    // Сдвигаем все точки комнаты относительно нового центра
                    // Упрощенно: просто сдвигаем точки на dx, dy
                    selectedElement.data.points.forEach(p => {
                        // Нам нужно знать исходные точки относительно центра, но у нас только абсолютные.
                        // Проще: запомнить дельту от предыдущего кадра. 
                        // Но здесь мы используем dragStart от нажатия. 
                        // Проблема: если мы двигаем второй раз, оригинал уже старый.
                        // Решение: хранить смещение от момента нажатия.
                        // Исправление логики выше: dragStart.original хранит координаты на момент начала драга.
                        // Значит формула верна: New = Original + Delta.
                        
                        // Но для комнаты точки массивом. 
                        // Нужно было сохранить копию точек в dragStart.
                        // Исправим "на лету": нам нужно знать, насколько сдвинулись с прошлого кадра.
                        // Для простоты: применяем дельту к ТЕКУЩИМ координатам, но накапливаем ошибку.
                        // Правильнее: хранить дельту от предыдущего кадра.
                        
                        // В данном случае, просто пересчитаем точки как смещение центра
                        p.x = p.x - origCenter.x + newCenter.x;
                        p.y = p.y - origCenter.y + newCenter.y;
                    });
                } else {
                    const orig = dragStart.original;
                    selectedElement.data.x = orig.x + dx;
                    selectedElement.data.y = orig.y + dy;
                }
                draw();
            } 
            else if (currentTool === 'wall' && currentElement) {
                currentElement.x2 = worldPos.x;
                currentElement.y2 = worldPos.y;
                draw();
            }
            else if (currentTool === 'room' && currentElement) {
                // Добавляем точку при движении (режим полигона) или просто двигаем последнюю?
                // Сделаем режим "кликай по углам". А здесь просто показываем линию к курсору.
                // Для простоты: комната рисуется как линия пока не замкнута? 
                // Пусть будет просто точка, которая растет в радиус при отпускании.
                // Или режим "перетаскивания размера".
                // Реализуем: первая точка фиксирована, вторая следует за мышью (прямоугольная комната пока что для простоты, или радиус).
                // Пусть будет круг: центр в первой точке, радиус = расстоянию до мыши.
                const startX = currentElement.points[0].x;
                const startY = currentElement.points[0].y;
                const radius = Math.sqrt((worldPos.x - startX)**2 + **(worldPos.y - startY)2);
                currentElement.radius = radius;
                draw();
            }
            else if (selectionBox) {
                selectionBox.end = worldPos;
                draw();
            }
        }
    }

    function handleMouseUp(e) {
        const pos = getMousePos(e);
        const worldPos = screenToWorld(pos.x, pos.y);
        isDragging = false;

        if (currentTool === 'select') {
            if (selectionBox) {
                // Выделение рамкой
                selectByBox(selectionBox.start, selectionBox.end);
                selectionBox = null;
                draw();
            } else if (selectedElement) {
                // Конец перемещения - сохраняем состояние
                saveState();
                // Показываем контекстное меню рядом
                const screenPos = worldToScreen(
                    selectedElement.type === 'wall' ? (selectedElement.data.x1+selectedElement.data.x2)/2 : selectedElement.data.x,
                    selectedElement.type === 'wall' ? (selectedElement.data.y1+selectedElement.data.y2)/2 : selectedElement.data.y
                );
                showContextMenu(screenPos.x, screenPos.y);
            }
        } 
        else if (currentTool === 'wall' && currentElement) {
            // Не создаем стену нулевой длины
            if (currentElement.x1 !== currentElement.x2 || currentElement.y1 !== currentElement.y2) {
                projectData.walls.push(currentElement);
                saveState();
            }
            currentElement = null;
            draw();
        }
        else if (currentTool === 'room' && currentElement) {
            if (currentElement.radius > 5) {
                projectData.rooms.push(currentElement);
                saveState();
            }
            currentElement = null;
            draw();
        }
    }

    function handleDoubleClick(e) {
        if (selectedElement && selectedElement.type === 'room') {
            const newName = prompt("Введите название комнаты:", selectedElement.data.name);
            if (newName !== null) {
                selectedElement.data.name = newName;
                updateObjectProperty('name', newName);
                saveState();
                draw();
            }
        }
    }

    // --- Отрисовка ---

    function drawLoop() {
        draw();
        drawMiniMap();
        requestAnimationFrame(drawLoop);
    }

    function draw() {
        // Очистка
        ctx.fillStyle = isDark ? '#1a1a1a' : '#f0f2f5';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        drawGrid();

        ctx.save();
        ctx.translate(offsetX, offsetY);
        ctx.scale(scale, scale);

        // 1. Рисуем объединенные стены (штриховка)
        drawWallsMerged();

        // 2. Окна и двери (поверх стен)
        projectData.windows.forEach(w => drawWindow(w));
        projectData.doors.forEach(d => drawDoor(d));

        // 3. Комнаты
        projectData.rooms.forEach(r => drawRoom(r));

        // 4. Метки
        projectData.labels.forEach(l => drawLabel(l));

        // 5. Текущий рисуемый элемент
        if (currentElement) {
            ctx.strokeStyle = '#ff0000';
            ctx.lineWidth = 0.5;
            if (currentTool === 'wall') {
                ctx.beginPath();
                ctx.moveTo(currentElement.x1, currentElement.y1);
                ctx.lineTo(currentElement.x2, currentElement.y2);
                ctx.stroke();
            } else if (currentTool === 'room') {
                ctx.beginPath();
                ctx.arc(currentElement.points[0].x, currentElement.points[0].y, currentElement.radius || 0, 0, Math.PI*2);
                ctx.stroke();
            }
        }

        // 6. Выделение
        if (selectedElement) {
            drawSelectionHighlight(selectedElement);
        }

        // 7. Рамка выделения
        if (selectionBox) {
            ctx.strokeStyle = '#4a90e2';
            ctx.lineWidth = 0.5 / scale;
            ctx.setLineDash([5, 5]);
            ctx.strokeRect(
                Math.min(selectionBox.start.x, selectionBox.end.x),
                Math.min(selectionBox.start.y, selectionBox.end.y),
                Math.abs(selectionBox.end.x - selectionBox.start.x),
                Math.abs(selectionBox.end.y - selectionBox.start.y)
            );
            ctx.setLineDash([]);
        }

        ctx.restore();
    }

    function drawGrid() {
        ctx.strokeStyle = isDark ? '#333' : '#e0e0e0';
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        
        const startX = -offsetX / scale;
        const startY = -offsetY / scale;
        const endX = (canvas.width - offsetX) / scale;
        const endY = (canvas.height - offsetY) / scale;

        // Вертикальные
        for (let x = Math.floor(startX); x <= endX; x+=10) {
            ctx.moveTo(x, startY);
            ctx.lineTo(x, endY);
        }
        // Горизонтальные
        for (let y = Math.floor(startY); y <= endY; y+=10) {
            ctx.moveTo(startX, y);
            ctx.lineTo(endX, y);
        }
        ctx.stroke();
    }

    function drawWallsMerged() {
        // Простая реализация: рисуем все стены, но стиль делаем "монолитным" через глобальный паттерн или просто толстые линии
        // Для настоящей булевой операции нужен clipper library, здесь эмулируем визуальный стиль
        
        ctx.lineCap = 'square';
        ctx.lineJoin = 'round';
        
        // Сначала заполняем штриховкой (диагональной)
        ctx.save();
        ctx.strokeStyle = isDark ? '#555' : '#aaa';
        ctx.lineWidth = 0.5;
        ctx.setLineDash([5, 5]); // Пунктир
        
        projectData.walls.forEach(w => {
            ctx.beginPath();
            ctx.moveTo(w.x1, w.y1);
            ctx.lineTo(w.x2, w.y2);
            ctx.stroke();
        });
        ctx.restore();

        // Затем рисуем контур толщиной
        ctx.strokeStyle = isDark ? '#888' : '#666';
        ctx.lineWidth = 1; // Базовая толщина, далее умножается на scale в transform, но тут мы в мире координат
        // Внимание: lineWidth тоже масштабируется. Если стена 10см, а масштаб 20px/10см, то lineWidth должен быть 10 (в единицах мира)?
        // Нет, lineWidth в canvas задается в пикселях экрана, если не внутри transform. Но мы внутри transform.
        // Значит, чтобы получить 10см на экране (200px), нужно lineWidth = 10 (единиц мира).
        
        projectData.walls.forEach(w => {
            ctx.beginPath();
            ctx.moveTo(w.x1, w.y1);
            ctx.lineTo(w.x2, w.y2);
            ctx.lineWidth = (w.thickness || 10) / 10; // Нормализуем
            ctx.stroke();
        });
    }

    function drawWindow(w) {
        ctx.save();
        ctx.translate(w.x, w.y);
        // Поворот? Пока нет, считаем горизонтальными или привязанными к стене (упрощено)
        ctx.fillStyle = '#87CEEB';
        ctx.fillRect(-2, -2, 4, 4); // Условно
        ctx.strokeStyle = '#333';
        ctx.strokeRect(-2, -2, 4, 4);
        ctx.restore();
    }

    function drawDoor(d) {
        ctx.save();
        ctx.translate(d.x, d.y);
        ctx.beginPath();
        ctx.arc(0, 0, 4, 0, Math.PI/2); // Дуга открытия
        ctx.strokeStyle = '#8B4513';
        ctx.stroke();
        ctx.fillStyle = '#DEB887';
        ctx.fillRect(0, 0, 4, 0.5); // Полотно
        ctx.restore();
    }

    function drawRoom(r) {
        const center = getRoomCenter(r.points);
        
        // Круг
        ctx.beginPath();
        ctx.arc(center.x, center.y, r.radius || 20, 0, Math.PI * 2);
        ctx.fillStyle = isDark ? 'rgba(100, 181, 246, 0.2)' : 'rgba(74, 144, 226, 0.1)';
        ctx.fill();
        ctx.strokeStyle = isDark ? '#64b5f6' : '#4a90e2';
        ctx.lineWidth = 0.5;
        ctx.stroke();

        // Текст (название)
        ctx.fillStyle = isDark ? '#fff' : '#333';
        ctx.font = '1px Arial'; // Масштабируемый шрифт
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(r.name || "Комната", center.x, center.y);
    }

    function drawLabel(l) {
        ctx.fillStyle = isDark ? '#fff' : '#000';
        ctx.font = '1px Arial';
        ctx.textAlign = 'left';
        ctx.fillText(l.text || "", l.x, l.y);
    }

    function drawSelectionHighlight(el) {
        ctx.strokeStyle = '#ff0000';
        ctx.lineWidth = 0.5;
        ctx.setLineDash([5, 5]);
        
        if (el.type === 'room') {
            const center = getRoomCenter(el.data.points);
            ctx.beginPath();
            ctx.arc(center.x, center.y, (el.data.radius||20) + 1, 0, Math.PI*2);
            ctx.stroke();
        } else if (el.type === 'wall') {
            ctx.beginPath();
            ctx.moveTo(el.data.x1, el.data.y1);
            ctx.lineTo(el.data.x2, el.data.y2);
            ctx.stroke();
            // Точки на концах
            ctx.fillStyle = 'red';
            ctx.fillRect(el.data.x1-0.5, el.data.y1-0.5, 1, 1);
            ctx.fillRect(el.data.x2-0.5, el.data.y2-0.5, 1, 1);
        } else {
            ctx.beginPath();
            ctx.arc(el.data.x, el.data.y, 2, 0, Math.PI*2);
            ctx.stroke();
        }
        ctx.setLineDash([]);
    }

    function drawMiniMap() {
        miniMapCtx.fillStyle = isDark ? '#2d2d2d' : '#fff';
        miniMapCtx.fillRect(0, 0, miniMapCanvas.width, miniMapCanvas.height);
        
        // Вычисляем границы всех объектов для масштабирования
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        const all = [...projectData.walls, ...projectData.rooms.map(r => ({x:r.points[0].x, y:r.points[0].y}))];
        
        if (all.length === 0) return;

        all.forEach(p => {
            if (p.x1 !== undefined) { minX=Math.min(minX,p.x1,p.x2); maxX=Math.max(maxX,p.x1,p.x2); }
            if (p.y1 !== undefined) { minY=Math.min(minY,p.y1,p.y2); maxY=Math.max(maxY,p.y1,p.y2); }
            if (p.x !== undefined) { minX=Math.min(minX,p.x); maxX=Math.max(maxX,p.x); }
            if (p.y !== undefined) { minY=Math.min(minY,p.y); maxY=Math.max(maxY,p.y); }
        });

        const padding = 10;
        const mapW = maxX - minX + padding*2;
        const mapH = maxY - minY + padding*2;
        const scaleMapX = miniMapCanvas.width / mapW;
        const scaleMapY = miniMapCanvas.height / mapH;
        const mScale = Math.min(scaleMapX, scaleMapY);

        miniMapCtx.save();
        miniMapCtx.translate(padding, padding);
        miniMapCtx.scale(mScale, mScale);
        miniMapCtx.translate(-minX, -minY);

        miniMapCtx.strokeStyle = '#4a90e2';
        miniMapCtx.lineWidth = 2 / mScale;
        
        projectData.walls.forEach(w => {
            miniMapCtx.beginPath();
            miniMapCtx.moveTo(w.x1, w.y1);
            miniMapCtx.lineTo(w.x2, w.y2);
            miniMapCtx.stroke();
        });
        
        projectData.rooms.forEach(r => {
            const c = getRoomCenter(r.points);
            miniMapCtx.beginPath();
            miniMapCtx.arc(c.x, c.y, r.radius||10, 0, Math.PI*2);
            miniMapCtx.stroke();
        });

        miniMapCtx.restore();
    }

    // --- Утилиты ---

    function getRoomCenter(points) {
        if (!points || points.length === 0) return {x:0, y:0};
        const sumX = points.reduce((s, p) => s + p.x, 0);
        const sumY = points.reduce((s, p) => s + p.y, 0);
        return { x: sumX / points.length, y: sumY / points.length };
    }

    function isPointInElement(p, el) {
        const threshold = 1.0; // Допуск в единицах мира
        if (el.type === 'wall') {
            // Расстояние от точки до отрезка
            const A = p.x - el.data.x1;
            const B = p.y - el.data.y1;
            const C = el.data.x2 - el.data.x1;
            const D = el.data.y2 - el.data.y1;
            const dot = A * C + B * D;
            const len_sq = C * C + D * D;
            let param = -1;
            if (len_sq != 0) param = dot / len_sq;
            let xx, yy;
            if (param < 0) { xx = el.data.x1; yy = el.data.y1; }
            else if (param > 1) { xx = el.data.x2; yy = el.data.y2; }
            else { xx = el.data.x1 + param * C; yy = el.data.y1 + param * D; }
            const dx = p.x - xx;
            const dy = p.y - yy;
            return (dx * dx + dy * dy) < (threshold * threshold);
        } else {
            const dx = p.x - el.data.x;
            const dy = p.y - el.data.y;
            return (dx*dx + dy*dy) < (threshold*threshold);
        }
    }

    function selectByBox(start, end) {
        const x1 = Math.min(start.x, end.x);
        const y1 = Math.min(start.y, end.y);
        const x2 = Math.max(start.x, end.x);
        const y2 = Math.max(start.y, end.y);

        // Ищем первый попавшийся (для простоты одиночного выбора)
        // Можно реализовать множественный выбор
        for (let r of projectData.rooms) {
            const c = getRoomCenter(r.points);
            if (c.x >= x1 && c.x <= x2 && c.y >= y1 && c.y <= y2) {
                selectedElement = { type: 'room', data: r };
                showProperties(selectedElement);
                return;
            }
        }
        // ... аналогично для других
    }

    // --- Свойства и Контекстное меню ---

    function showProperties(el) {
        const panel = document.getElementById('prop-selection');
        panel.style.display = 'block';
        document.getElementById('objType').value = el.type === 'wall' ? 'Стена' : 
                                                  el.type === 'room' ? 'Комната' : 
                                                  el.type === 'window' ? 'Окно' : 
                                                  el.type === 'door' ? 'Дверь' : 'Метка';
        
        const nameGroup = document.getElementById('prop-name-group');
        const thickGroup = document.getElementById('prop-thickness-group');
        
        if (el.type === 'room' || el.type === 'label') {
            nameGroup.style.display = 'flex';
            document.getElementById('objName').value = el.type === 'room' ? (el.data.name || '') : (el.data.text || '');
        } else {
            nameGroup.style.display = 'none';
        }

        if (el.type === 'wall') {
            thickGroup.style.display = 'flex';
            document.getElementById('objThickness').value = el.data.thickness || 10;
            document.getElementById('thickVal').innerText = el.data.thickness || 10;
        } else {
            thickGroup.style.display = 'none';
        }
    }

    function updateObjectProperty(key, value) {
        if (!selectedElement) return;
        if (selectedElement.type === 'label' && key === 'name') {
            selectedElement.data.text = value;
        } else if (selectedElement.type === 'room' && key === 'name') {
            selectedElement.data.name = value;
        } else if (key === 'thickness') {
            selectedElement.data.thickness = parseInt(value);
        }
        saveState();
        draw();
    }

    function showContextMenu(x, y) {
        const menu = document.getElementById('contextMenu');
        menu.style.display = 'flex';
        menu.style.left = x + 'px';
        menu.style.top = y + 'px';
    }

    function closeContextMenu() {
        document.getElementById('contextMenu').style.display = 'none';
    }

    function duplicateSelection() {
        if (!selectedElement) return;
        const el = selectedElement.data;
        const type = selectedElement.type + 's';
        
        let newEl = JSON.parse(JSON.stringify(el)); // Глубокая копия
        
        // Смещение на 0.5 ширины (условно 50 единиц)
        const offset = 50; 
        if (newEl.x1 !== undefined) { // Wall
            newEl.x1 += offset; newEl.x2 += offset;
        } else {
            newEl.x += offset;
        }
        
        addToList(type, newEl);
        saveState();
        draw();
        closeContextMenu();
    }

    function deleteSelection() {
        if (!selectedElement) return;
        const type = selectedElement.type + 's';
        projectData[type].splice(selectedElement.index, 1);
        selectedElement = null;
        document.getElementById('prop-selection').style.display = 'none';
        saveState();
        draw();
        closeContextMenu();
    }

    function addToList(listName, item) {
        projectData[listName].push(item);
        // Обновляем индекс для выбранного элемента если нужно, но сейчас просто добавляем
    }

    // --- Сохранение и История ---

    function saveState() {
        // Удаляем будущую историю если были отмены
        if (historyStep < history.length - 1) {
            history = history.slice(0, historyStep + 1);
        }
        history.push(JSON.stringify(projectData));
        if (history.length > MAX_HISTORY) history.shift();
        else historyStep++;
    }

    function undo() {
        if (historyStep > 0) {
            historyStep--;
            projectData = JSON.parse(history[historyStep]);
            draw();
            showNotification("Отменено");
        }
    }

    function redo() {
        if (historyStep < history.length - 1) {
            historyStep++;
            projectData = JSON.parse(history[historyStep]);
            draw();
            showNotification("Повторено");
        }
    }

    async function saveProject() {
        const btn = document.querySelector('button.primary');
        const originalText = btn.innerHTML;
        btn.innerHTML = '⏳ Сохранение...';
        
        try {
            const response = await fetch(`/api/project/{{ project.id }}/save`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ canvas_data: projectData })
            });
            
            if (response.ok) {
                showNotification("Проект сохранен!", "success");
                updateStats(); // Обновить статистику после сохранения
            } else {
                throw new Error('Ошибка сервера');
            }
        } catch (e) {
            showNotification("Ошибка сохранения", "error");
            console.error(e);
        } finally {
            btn.innerHTML = originalText;
        }
    }

    async function updateProjectName(name) {
        await fetch(`/api/project/{{ project.id }}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name })
        });
    }

    async function updateStats() {
        try {
            const res = await fetch(`/api/project/{{ project.id }}/stats`);
            const stats = await res.json();
            document.getElementById('statsInfo').innerHTML = `
                Стен: ${stats.walls_count}<br>
                Окон: ${stats.windows_count}<br>
                Дверей: ${stats.doors_count}<br>
                Комнат: ${stats.rooms_count}<br>
                Длина стен: ${stats.total_wall_length} м
            `;
        } catch(e) { console.log(e); }
    }

    function showNotification(msg, type='success') {
        const n = document.getElementById('notification');
        n.innerText = msg;
        n.className = 'notification show ' + type;
        setTimeout(() => n.classList.remove('show'), 2000);
    }

    function toggleTheme() {
        isDark = !isDark;
        document.body.classList.toggle('dark-mode');
        draw();
    }

    function handleKeyDown(e) {
        if (e.target.tagName === 'INPUT') return; // Не срабатывать при вводе текста
        
        switch(e.key.toLowerCase()) {
            case 'v': setTool('select'); break;
            case 'w': setTool('wall'); break;
            case 'o': setTool('window'); break;
            case 'd': setTool('door'); break;
            case 'r': setTool('room'); break;
            case 't': setTool('label'); break;
            case 'delete': 
            case 'backspace': deleteSelection(); break;
        }
        
        if ((e.ctrlKey || e.metaKey) && e.key === 'z') { e.preventDefault(); undo(); }
        if ((e.ctrlKey || e.metaKey) && e.key === 'y') { e.preventDefault(); redo(); }
        if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); saveProject(); }
    }

    // Старт
    init();
</script>
</body>
</html>



это более новый код для этой ветки 
