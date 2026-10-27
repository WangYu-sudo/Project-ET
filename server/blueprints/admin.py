# -*- coding: utf-8 -*-
"""
管理员功能蓝图
- 教师账号增删改查
- 考试清理
- 系统配置
"""
from flask import Blueprint, request, session as flask_session

from ..decorators import admin_required
from ..services import admin_service

admin_bp = Blueprint('admin', __name__)


# ==================== 教师管理 ====================
@admin_bp.route('/teachers/')
@admin_required
def teacher_list():
    return admin_service.teacher_list(request)


@admin_bp.route('/teachers/create/', methods=['GET', 'POST'])
@admin_required
def teacher_create():
    return admin_service.teacher_create(request)


@admin_bp.route('/teachers/<int:uid>/edit/', methods=['GET', 'POST'])
@admin_required
def teacher_edit(uid):
    return admin_service.teacher_edit(request, uid)


@admin_bp.route('/teachers/<int:uid>/delete/', methods=['POST'])
@admin_required
def teacher_delete(uid):
    return admin_service.teacher_delete(uid)


# ==================== 考试清理（管理员视角） ====================
@admin_bp.route('/exams/')
@admin_required
def exam_list():
    return admin_service.exam_list(request)


@admin_bp.route('/exams/<int:exam_id>/clean/', methods=['POST'])
@admin_required
def exam_clean(exam_id):
    return admin_service.exam_clean(request, exam_id)


# ==================== 系统配置 ====================
@admin_bp.route('/config/', methods=['GET', 'POST'])
@admin_required
def system_config():
    return admin_service.system_config(request)
