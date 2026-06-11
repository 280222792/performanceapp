import os
import json
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session

app = Flask(__name__)
app.secret_key = 'performance-commitment-app-secret-key-2024'

# ── User accounts (from 花名册26Q1) ─────────────────
USERS = {
    '03019722': {'name': '陈驰',   'password': '123'},
    '03106524': {'name': '谢万意', 'password': '123'},
    '03289722': {'name': '卢本见', 'password': '123'},
}

# ── Directory config ────────────────────────────────
UPLOAD_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

MAIN_FOLDERS = [
    '总部一级',
    '总部二级',
    '大区总',
    '快递国家总',
    '货运国家总',
    '中国区货运站长',
]

QUARTERS = ['Q1', 'Q2', 'Q3', 'Q4']

# Metadata filename (hidden)
META_FILE = '_meta.json'


def is_visible_file(filename):
    """Exclude hidden/system files (._ , .DS_Store, _meta.json, etc.)."""
    return not filename.startswith('.') and not filename.startswith('_')

# ── Metadata helpers ───────────────────────────────

def load_metadata(quarter_path):
    """Load metadata dict from _meta.json, return {} if missing."""
    meta_path = os.path.join(quarter_path, META_FILE)
    if os.path.exists(meta_path):
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_metadata(quarter_path, meta):
    """Save metadata dict to _meta.json."""
    meta_path = os.path.join(quarter_path, META_FILE)
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


# ── Helpers ─────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated


def get_human_size(size_bytes):
    if size_bytes == 0:
        return '0 B'
    units = ['B', 'KB', 'MB', 'GB']
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f'{size:.2f} {units[i]}'


def ensure_directories():
    for folder in MAIN_FOLDERS:
        for q in QUARTERS:
            os.makedirs(os.path.join(UPLOAD_ROOT, folder, q), exist_ok=True)


def build_file_entry(filename, quarter_path, meta):
    """Build a file-info dict for template rendering."""
    fp = os.path.join(quarter_path, filename)
    fsize = os.path.getsize(fp)
    mtime = datetime.fromtimestamp(os.path.getmtime(fp))
    entry = {
        'name': filename,
        'size': get_human_size(fsize),
        'size_bytes': fsize,
        'modified': mtime.strftime('%Y-%m-%d %H:%M:%S'),
        'uploader': '',
    }
    # Attach uploader from metadata if present
    file_meta = meta.get(filename, {})
    if file_meta.get('uploader_name'):
        entry['uploader'] = file_meta['uploader_name']
    return entry


# ── Login / Logout ─────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form.get('user_id', '').strip()
        password = request.form.get('password', '').strip()

        user = USERS.get(user_id)
        if user and user['password'] == password:
            session['user_id'] = user_id
            session['user_name'] = user['name']
            flash(f'欢迎回来，{user["name"]}！', 'success')
            next_url = request.args.get('next', url_for('index'))
            return redirect(next_url)
        else:
            flash('工号或密码错误，请重试', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('已安全退出', 'success')
    return redirect(url_for('login'))


# ── Protected Routes ───────────────────────────────

@app.route('/')
@login_required
def index():
    ensure_directories()
    folder_stats = []
    for folder in MAIN_FOLDERS:
        folder_path = os.path.join(UPLOAD_ROOT, folder)
        total_files = 0
        total_size = 0
        quarter_info = []
        for q in QUARTERS:
            q_path = os.path.join(folder_path, q)
            files = os.listdir(q_path) if os.path.exists(q_path) else []
            real_files = [f for f in files if is_visible_file(f) and os.path.isfile(os.path.join(q_path, f))]
            q_size = sum(os.path.getsize(os.path.join(q_path, f)) for f in real_files)
            quarter_info.append({
                'name': q,
                'count': len(real_files),
                'size': get_human_size(q_size),
                'size_bytes': q_size,
            })
            total_files += len(real_files)
            total_size += q_size

        folder_stats.append({
            'name': folder,
            'total_files': total_files,
            'total_size': get_human_size(total_size),
            'quarters': quarter_info,
        })

    return render_template('index.html', folder_stats=folder_stats)


@app.route('/folder/<folder_name>')
@login_required
def folder_view(folder_name):
    if folder_name not in MAIN_FOLDERS:
        flash('文件夹不存在', 'error')
        return redirect(url_for('index'))

    ensure_directories()
    folder_path = os.path.join(UPLOAD_ROOT, folder_name)
    quarters_data = []

    for q in QUARTERS:
        q_path = os.path.join(folder_path, q)
        files = os.listdir(q_path) if os.path.exists(q_path) else []
        meta = load_metadata(q_path)
        file_list = []
        total_size = 0
        for f in files:
            if not is_visible_file(f):
                continue
            fp = os.path.join(q_path, f)
            if os.path.isfile(fp):
                entry = build_file_entry(f, q_path, meta)
                file_list.append(entry)
                total_size += entry['size_bytes']

        quarters_data.append({
            'name': q,
            'files': file_list,
            'file_count': len(file_list),
            'total_size': get_human_size(total_size),
        })

    return render_template(
        'folder.html', folder_name=folder_name,
        quarters_data=quarters_data, quarters=QUARTERS)


@app.route('/folder/<folder_name>/<quarter>', methods=['GET', 'POST'])
@login_required
def quarter_view(folder_name, quarter):
    if folder_name not in MAIN_FOLDERS or quarter not in QUARTERS:
        flash('路径不存在', 'error')
        return redirect(url_for('index'))

    quarter_path = os.path.join(UPLOAD_ROOT, folder_name, quarter)
    os.makedirs(quarter_path, exist_ok=True)

    if request.method == 'POST':
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            flash('请选择要上传的文件', 'warning')
            return redirect(url_for('quarter_view',
                                    folder_name=folder_name, quarter=quarter))

        # Load current metadata
        meta = load_metadata(quarter_path)
        uploader_name = session['user_name']
        uploader_id = session['user_id']

        # 以人员姓名为准：删除该用户在此文件夹下的所有旧文件
        removed = 0
        old_filenames = list(meta.keys())
        for old_fn in old_filenames:
            old_info = meta[old_fn]
            if old_info.get('uploader_name') == uploader_name:
                old_path = os.path.join(quarter_path, old_fn)
                if os.path.isfile(old_path):
                    os.remove(old_path)
                    removed += 1
                del meta[old_fn]

        # Save new files and record metadata
        uploaded_count = 0
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for file in files:
            if file.filename == '':
                continue
            filename = os.path.basename(file.filename)
            save_path = os.path.join(quarter_path, filename)
            file.save(save_path)
            meta[filename] = {
                'uploader_name': uploader_name,
                'uploader_id': uploader_id,
                'uploaded_at': now_str,
            }
            uploaded_count += 1

        save_metadata(quarter_path, meta)

        msg = f'成功上传 {uploaded_count} 个文件'
        if removed > 0:
            msg += f'（已替换 {removed} 个旧版本）'
        flash(msg, 'success')
        return redirect(url_for('quarter_view',
                                folder_name=folder_name, quarter=quarter))

    # GET: list files
    files = os.listdir(quarter_path) if os.path.exists(quarter_path) else []
    meta = load_metadata(quarter_path)
    file_list = []
    for f in sorted(files):
        if f == META_FILE:
            continue
        fp = os.path.join(quarter_path, f)
        if os.path.isfile(fp):
            file_list.append(build_file_entry(f, quarter_path, meta))

    breadcrumbs = [
        {'name': '首页', 'url': url_for('index')},
        {'name': folder_name, 'url': url_for('folder_view', folder_name=folder_name)},
        {'name': quarter, 'url': None},
    ]

    return render_template(
        'files.html', folder_name=folder_name, quarter=quarter,
        files=file_list, breadcrumbs=breadcrumbs,
        total_size=get_human_size(sum(f['size_bytes'] for f in file_list)))


@app.route('/download/<folder_name>/<quarter>/<filename>')
@login_required
def download_file(folder_name, quarter, filename):
    if folder_name not in MAIN_FOLDERS or quarter not in QUARTERS:
        flash('路径不存在', 'error')
        return redirect(url_for('index'))

    file_path = os.path.join(UPLOAD_ROOT, folder_name, quarter, filename)
    if not os.path.isfile(file_path):
        flash('文件不存在', 'error')
        return redirect(url_for('quarter_view',
                                folder_name=folder_name, quarter=quarter))

    return send_file(file_path, as_attachment=True, download_name=filename)


@app.route('/delete/<folder_name>/<quarter>/<filename>', methods=['POST'])
@login_required
def delete_file(folder_name, quarter, filename):
    if folder_name not in MAIN_FOLDERS or quarter not in QUARTERS:
        flash('路径不存在', 'error')
        return redirect(url_for('index'))

    quarter_path = os.path.join(UPLOAD_ROOT, folder_name, quarter)
    file_path = os.path.join(quarter_path, filename)

    if os.path.isfile(file_path):
        os.remove(file_path)
        # Also remove from metadata
        meta = load_metadata(quarter_path)
        if filename in meta:
            del meta[filename]
            save_metadata(quarter_path, meta)
        flash(f'已删除: {filename}', 'success')
    else:
        flash('文件不存在', 'error')

    return redirect(url_for('quarter_view',
                            folder_name=folder_name, quarter=quarter))


# Ensure upload directories exist on startup (works for both dev & prod)
ensure_directories()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
