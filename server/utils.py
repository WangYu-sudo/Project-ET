"""
工具函数集合
"""
import os
import uuid
import csv
from datetime import datetime

from flask import request, current_app
from openpyxl import Workbook, load_workbook


# ==================== IP 获取 ====================
def get_client_ip():
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        # 可能有多个，取第一个
        return forwarded.split(',')[0].strip()
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip.strip()
    return request.remote_addr or '127.0.0.1'


# ==================== 文件处理 ====================
def allowed_paper_file(filename):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in {'pdf', 'doc', 'docx', 'zip', 'rar'}


def allowed_submit_file(filename):
    return bool(filename) and '.' in filename


def save_upload(file_storage, save_dir, filename=None):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir, exist_ok=True)

    if filename is None:
        original = file_storage.filename or 'upload.bin'
        ext = original.rsplit('.', 1)[-1] if '.' in original else ''
        filename = f"{uuid.uuid4().hex[:12]}.{ext}" if ext else uuid.uuid4().hex[:12]

    abs_path = os.path.join(save_dir, filename)
    file_storage.save(abs_path)

    base = current_app.config['BASE_DIR'] if 'BASE_DIR' in current_app.config \
        else os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return os.path.relpath(abs_path, base).replace('\\', '/')


# ==================== Excel / CSV 读取 ====================
def read_student_file(file_storage):

    filename = (file_storage.filename or '').lower()
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else ''

    rows = []
    if ext == 'xlsx':
        wb = load_workbook(file_storage.stream, read_only=True, data_only=True)
        ws = wb.active
        for idx, row in enumerate(ws.iter_rows(values_only=True)):
            if idx == 0:
                continue  
            if row is None or all(c is None or str(c).strip() == '' for c in row):
                continue
            number = str(row[0] or '').strip()
            name = str(row[1] or '').strip()
            clazz = str(row[2] or '').strip() if len(row) > 2 else ''
            if number and name:
                rows.append({'number': number, 'name': name, 'clazz': clazz})
        wb.close()

    elif ext == 'csv':
        raw = file_storage.read()
        for enc in ('utf-8', 'gbk', 'utf-8-sig'):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                text = None
        if text is None:
            raise ValueError('CSV 文件编码无法识别，请使用 UTF-8')

        reader = csv.reader(text.splitlines())
        header_skipped = False
        for row in reader:
            if not header_skipped:
                header_skipped = True
                continue
            if not row or all(not str(c).strip() for c in row):
                continue
            number = str(row[0] or '').strip()
            name = str(row[1] or '').strip()
            clazz = str(row[2] or '').strip() if len(row) > 2 else ''
            if number and name:
                rows.append({'number': number, 'name': name, 'clazz': clazz})

    else:
        raise ValueError(f'不支持的文件格式: .{ext}，请使用 .xlsx / .csv')

    return rows


# ==================== Excel 导出 ====================
def export_submits_to_excel(students_with_submit_info, save_path):
    """
    将学生提交信息导出到 Excel
    students_with_submit_info: list of dict，每个包含 number, name, clazz, submit_time
    """
    wb = Workbook()
    ws = wb.active
    ws.title = '提交信息'
    ws.append(['班级', '学号', '姓名', '最后提交时间'])
    for s in students_with_submit_info:
        ws.append([
            s.get('clazz', ''),
            s.get('number', ''),
            s.get('name', ''),
            s.get('submit_time', '未提交'),
        ])
    wb.save(save_path)
    return save_path


# ==================== 时间格式化 ====================
def fmt_time(dt):
    if not dt:
        return ''
    if isinstance(dt, datetime):
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    return str(dt)


# ==================== 考试状态判断 ====================
def exam_is_available(exam):
    """学生能否登录这场考试"""
    return exam.started and not exam.finished and not exam.cleaned
