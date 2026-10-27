"""
学生功能蓝图
考试主页、下载试卷、上传答案、查看已提交、接收通知（AJAX 接口）
"""
from flask import Blueprint, request, session as flask_session

from ..decorators import student_required
from ..services import student_service

student_bp = Blueprint('student', __name__)


# ==================== 考试主页 ====================
@student_bp.route('/exam/')
@student_required
def exam_page():
    return student_service.exam_page(flask_session)


# ==================== 下载试卷 ====================
@student_bp.route('/exam/paper/')
@student_required
def exam_paper():
    return student_service.exam_paper(flask_session)


# ==================== 上传答案 ====================
@student_bp.route('/exam/submit/', methods=['POST'])
@student_required
def exam_submit():
    return student_service.exam_submit(request, flask_session)


# ==================== 查看已提交（JSON / 页面都可） ====================
@student_bp.route('/exam/submitted/')
@student_required
def exam_submitted():
    return student_service.exam_submitted(request, flask_session)


# ==================== 下载自己提交的文件 ====================
@student_bp.route('/exam/submitted/<int:sid>/download/')
@student_required
def exam_submitted_download(sid):
    return student_service.exam_submitted_download(sid, flask_session)


# ==================== 最新通知（AJAX 轮询接口） ====================
@student_bp.route('/notifications/latest/')
@student_required
def latest_notification():
    return student_service.latest_notification(request, flask_session)
