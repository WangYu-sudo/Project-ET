"""
教师功能蓝图
考试 CRUD、试卷上传、学生导入、开启/结束、监控、解绑、通知、打包下载、导出、清理
"""
from flask import Blueprint, request, session as flask_session

from ..decorators import teacher_required
from ..services import teacher_service

teacher_bp = Blueprint('teacher', __name__)


# ==================== 考试列表 ====================
@teacher_bp.route('/exam/list/')
@teacher_required
def exam_list():
    return teacher_service.exam_list(request, flask_session)


# ==================== 新建考试 ====================
@teacher_bp.route('/exam/create/', methods=['GET', 'POST'])
@teacher_required
def exam_create():
    return teacher_service.exam_create(request, flask_session)


# ==================== 编辑考试 ====================
@teacher_bp.route('/exam/<int:exam_id>/edit/', methods=['GET', 'POST'])
@teacher_required
def exam_edit(exam_id):
    return teacher_service.exam_edit(request, flask_session, exam_id)


# ==================== 上传试卷 ====================
@teacher_bp.route('/exam/<int:exam_id>/upload/', methods=['POST'])
@teacher_required
def exam_upload_paper(exam_id):
    return teacher_service.exam_upload_paper(request, flask_session, exam_id)


# ==================== 导入学生名单 ====================
@teacher_bp.route('/exam/<int:exam_id>/import/', methods=['POST'])
@teacher_required
def exam_import_students(exam_id):
    return teacher_service.exam_import_students(request, flask_session, exam_id)


# ==================== 手动添加学生 ====================
@teacher_bp.route('/exam/<int:exam_id>/student/add/', methods=['POST'])
@teacher_required
def exam_student_add(exam_id):
    return teacher_service.exam_student_add(request, flask_session, exam_id)


# ==================== 删除学生 ====================
@teacher_bp.route('/exam/<int:exam_id>/student/<int:sid>/delete/', methods=['POST'])
@teacher_required
def exam_student_delete(exam_id, sid):
    return teacher_service.exam_student_delete(request, flask_session, exam_id, sid)


# ==================== 开启考试 ====================
@teacher_bp.route('/exam/<int:exam_id>/start/', methods=['POST'])
@teacher_required
def exam_start(exam_id):
    return teacher_service.exam_start(request, flask_session, exam_id)


# ==================== 结束考试 ====================
@teacher_bp.route('/exam/<int:exam_id>/finish/', methods=['POST'])
@teacher_required
def exam_finish(exam_id):
    return teacher_service.exam_finish(request, flask_session, exam_id)


# ==================== 监控页 ====================
@teacher_bp.route('/exam/<int:exam_id>/monitor/')
@teacher_required
def exam_monitor(exam_id):
    return teacher_service.exam_monitor(request, flask_session, exam_id)


# ==================== 解除 IP 锁定 ====================
@teacher_bp.route('/exam/<int:exam_id>/unlock/', methods=['POST'])
@teacher_required
def exam_unlock(exam_id):
    return teacher_service.exam_unlock(request, flask_session, exam_id)


# ==================== 通知管理 ====================
@teacher_bp.route('/exam/<int:exam_id>/notify/', methods=['POST'])
@teacher_required
def exam_notify(exam_id):
    return teacher_service.exam_notify(request, flask_session, exam_id)


@teacher_bp.route('/exam/<int:exam_id>/notify/<int:nid>/delete/', methods=['POST'])
@teacher_required
def exam_notify_delete(exam_id, nid):
    return teacher_service.exam_notify_delete(request, flask_session, exam_id, nid)


# ==================== 打包下载答卷 ====================
@teacher_bp.route('/exam/<int:exam_id>/download/')
@teacher_required
def exam_download(exam_id):
    return teacher_service.exam_download(request, flask_session, exam_id)


# ==================== 导出提交信息 ====================
@teacher_bp.route('/exam/<int:exam_id>/export/')
@teacher_required
def exam_export(exam_id):
    return teacher_service.exam_export(request, flask_session, exam_id)


# ==================== 清理考试（教师视角） ====================
@teacher_bp.route('/exam/<int:exam_id>/clean/', methods=['POST'])
@teacher_required
def exam_clean(exam_id):
    return teacher_service.exam_clean(request, flask_session, exam_id)
