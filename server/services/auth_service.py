# -*- coding: utf-8 -*-
"""
认证业务逻辑：选择角色登录、管理员登录、教师登录、学生登录、退出
"""
from flask import render_template, redirect, url_for, flash, session as flask_session

from ..extensions import db, bcrypt
from ..models import User, Exam, Student, Binding
from ..utils import get_client_ip, exam_is_available


def index():

    return render_template('login.html', role='select')


# ==================== 管理员登录 ====================
def admin_login(flask_request):
    
    return render_template('login.html', role='admin')


# ==================== 教师登录 ====================
def teacher_login(flask_request):

    return render_template('login.html', role='teacher')


def _login_success(user, flask_request):
   
    return redirect(url_for('teacher.exam_list'))


# ==================== 学生登录 ====================
def student_login(flask_request):

    return render_template('login.html', role='student')


# ==================== 退出 ====================
def logout():
    
    return redirect(url_for('auth.index'))
