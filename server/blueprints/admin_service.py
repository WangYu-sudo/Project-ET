# -*- coding: utf-8 -*-
"""
管理员业务逻辑
- 教师账号增删改查
- 考试清理
- 系统配置
"""
import os
import shutil

from flask import (render_template, redirect, url_for, flash, session as flask_session,
                   current_app, abort)

from ..extensions import db
from ..models import (User, Exam, Student, Binding, Submit,
                      Notification, ConfigItem)


# ==================== 教师管理 ====================
def teacher_list(flask_request):

    return render_template('admin/teacher_list.html', pagination=pagination, keyword=keyword)


def teacher_create(flask_request):
    
    return render_template('admin/teacher_form.html', teacher=None)


def teacher_edit(flask_request, uid):

    return render_template('admin/teacher_form.html', teacher=teacher)


def teacher_delete(uid):
    
    return redirect(url_for('admin.teacher_list'))


# ==================== 考试清理（管理员视角） ====================
def exam_list(flask_request):
    
    return render_template('admin/exam_list.html', pagination=pagination)


def exam_clean(flask_request, exam_id):

    return redirect(flask_request.referrer or url_for('admin.exam_list'))


# ==================== 系统配置 ====================
def system_config(flask_request):
    
    return render_template('admin/config.html')
