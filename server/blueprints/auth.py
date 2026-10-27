# -*- coding: utf-8 -*-
"""
认证相关路由：选择角色登录、管理员登录、教师登录、学生登录、退出
"""
from flask import Blueprint, request, session as flask_session

from ..decorators import login_required, teacher_required, admin_required, student_required
from ..services import auth_service

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    """首页：选择角色登录"""
    return auth_service.index()


# ==================== 管理员登录 ====================
@auth_bp.route('/admin/login/', methods=['GET', 'POST'])
def admin_login():
    return auth_service.admin_login(request)


# ==================== 教师登录 ====================
@auth_bp.route('/teacher/login/', methods=['GET', 'POST'])
def teacher_login():
    return auth_service.teacher_login(request)


# ==================== 学生登录 ====================
@auth_bp.route('/student/login/', methods=['GET', 'POST'])
def student_login():
    return auth_service.student_login(request)


# ==================== 退出 ====================
@auth_bp.route('/logout/')
def logout():
    return auth_service.logout()
