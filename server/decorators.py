from functools import wraps
from flask import session, redirect, url_for, flash, request


def login_required(view):
    """必须登录（教师或管理员）"""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            flash('请先登录', 'warning')
            next_url = request.path
            return redirect(url_for('auth.login', next=next_url))
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    """必须是管理员"""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            flash('请先登录', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash('需要管理员权限', 'danger')
            return redirect(url_for('teacher.exam_list'))
        return view(*args, **kwargs)
    return wrapper


def teacher_required(view):
    """必须是教师或管理员"""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            flash('请先登录', 'warning')
            return redirect(url_for('auth.login'))
        role = session.get('role')
        if role not in ('teacher', 'admin'):
            flash('需要教师权限', 'danger')
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)
    return wrapper


def student_required(view):
    """必须是已登录的学生"""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get('student_id') or not session.get('exam_id'):
            flash('请先登录', 'warning')
            return redirect(url_for('student.login'))
        return view(*args, **kwargs)
    return wrapper
