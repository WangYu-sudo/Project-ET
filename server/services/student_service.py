# -*- coding: utf-8 -*-
"""
学生业务逻辑
考试主页、下载试卷、上传答案、查看已提交、接收通知（AJAX 接口）
"""
import os

from flask import (render_template, redirect, url_for, flash, session as flask_session,
                   current_app, send_file, jsonify, abort)

from ..extensions import db
from ..models import Exam, Student, Binding, Submit, Notification
from ..utils import fmt_time, exam_is_available


# ==================== 考试主页 ====================
def exam_page(flask_session):
    
    return render_template('student/exam.html')


# ==================== 下载试卷 ====================
def exam_paper(flask_session):

    return send_file()


# ==================== 上传答案 ====================
def exam_submit(flask_request, flask_session):
    
    return redirect(url_for('student.exam_page'))


# ==================== 查看已提交（JSON / 页面都可） ====================
def exam_submitted(flask_request, flask_session):

    return render_template('student/submitted.html')


# ==================== 下载自己提交的文件 ====================
def exam_submitted_download(sid, flask_session):
   
    return send_file()


# ==================== 最新通知（AJAX 轮询接口） ====================
def latest_notification(flask_request, flask_session):
    
    return
