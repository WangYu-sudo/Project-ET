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
    exam_id = flask_session.get('exam_id')
    student_id = flask_session.get('student_id')

    exam = Exam.query.get(exam_id)
    student = Student.query.get(student_id)

    if not exam or not student:
        flask_session.clear()
        flash('登录信息失效，请重新登录', 'warning')
        return redirect(url_for('auth.student_login'))

    if not exam_is_available(exam):
        # 考试结束或被清理
        return render_template('student/finished.html', exam=exam)

    # 已提交的文件
    submits = Submit.query.filter_by(student_id=student.id)\
        .order_by(Submit.submit_time.desc()).all()

    # 最近一条通知（页面加载展示，轮询接口在下方）
    latest = Notification.query.filter_by(exam_id=exam.id)\
        .order_by(Notification.created_at.desc()).first()

    return render_template('student/exam.html',
                           exam=exam, student=student,
                           submits=submits, latest_notification=latest)


# ==================== 下载试卷 ====================
def exam_paper(flask_session):
    exam_id = flask_session.get('exam_id')
    exam = Exam.query.get_or_404(exam_id)

    if not exam.paper or not exam.paper_exists:
        flash('试卷尚未上传', 'warning')
        return redirect(url_for('student.exam_page'))

    abs_path = os.path.join(current_app.root_path, '..', exam.paper)
    if not os.path.exists(abs_path):
        flash('试卷文件丢失', 'danger')
        return redirect(url_for('student.exam_page'))

    return send_file(abs_path, as_attachment=True,
                     download_name=os.path.basename(abs_path))


# ==================== 上传答案 ====================
def exam_submit(flask_request, flask_session):
    exam_id = flask_session.get('exam_id')
    student_id = flask_session.get('student_id')

    exam = Exam.query.get(exam_id)
    student = Student.query.get(student_id)
    if not exam or not student:
        flash('会话失效', 'danger')
        return redirect(url_for('auth.student_login'))

    if not exam_is_available(exam):
        flash('考试已结束，不能再提交', 'warning')
        return redirect(url_for('student.exam_page'))

    files = flask_request.files.getlist('files')
    if not files or all(not f.filename for f in files):
        flash('未选择文件', 'danger')
        return redirect(url_for('student.exam_page'))

    save_dir = os.path.join(current_app.config['SUBMIT_FOLDER'],
                            f'exam_{exam.id}',
                            f'{student.number}_{student.name}')
    os.makedirs(save_dir, exist_ok=True)

    saved_count = 0
    for f in files:
        if not f.filename:
            continue
        # 防止路径穿越
        filename = os.path.basename(f.filename)
        abs_path = os.path.join(save_dir, filename)
        f.save(abs_path)

        # 同名文件覆盖逻辑：若之前已存在同名提交记录，则更新；否则新增
        existing = Submit.query.filter_by(student_id=student.id,
                                          filename=filename).first()
        if existing:
            rel = os.path.relpath(abs_path,
                                  os.path.join(current_app.root_path, '..')).replace('\\', '/')
            existing.file_path = rel
            existing.submit_time = db.func.now()
        else:
            rel = os.path.relpath(abs_path,
                                  os.path.join(current_app.root_path, '..')).replace('\\', '/')
            db.session.add(Submit(student_id=student.id,
                                  file_path=rel, filename=filename))
        saved_count += 1

    db.session.commit()
    flash(f'成功提交 {saved_count} 个文件', 'success')
    return redirect(url_for('student.exam_page'))


# ==================== 查看已提交（JSON / 页面都可） ====================
def exam_submitted(flask_request, flask_session):
    student_id = flask_session.get('student_id')
    submits = Submit.query.filter_by(student_id=student_id)\
        .order_by(Submit.submit_time.desc()).all()

    # 若是 AJAX 请求，返回 JSON
    if flask_request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify([{
            'id': s.id,
            'filename': s.filename,
            'submit_time': fmt_time(s.submit_time),
            'exists': os.path.exists(
                os.path.join(current_app.root_path, '..', s.file_path)
            ),
        } for s in submits])

    return render_template('student/submitted.html', submits=submits)


# ==================== 下载自己提交的文件 ====================
def exam_submitted_download(sid, flask_session):
    student_id = flask_session.get('student_id')
    submit = Submit.query.filter_by(id=sid, student_id=student_id).first_or_404()

    abs_path = os.path.join(current_app.root_path, '..', submit.file_path)
    if not os.path.exists(abs_path):
        flash('文件丢失', 'danger')
        return redirect(url_for('student.exam_submitted'))

    return send_file(abs_path, as_attachment=True,
                     download_name=os.path.basename(abs_path))


# ==================== 最新通知（AJAX 轮询接口） ====================
def latest_notification(flask_request, flask_session):
    exam_id = flask_session.get('exam_id')
    last_id = flask_request.args.get('last_id', type=int, default=0)

    latest = (Notification.query.filter_by(exam_id=exam_id)
              .order_by(Notification.created_at.desc()).first())
    if not latest:
        return jsonify({'has_new': False, 'content': ''})

    has_new = latest.id != last_id
    return jsonify({
        'has_new': has_new,
        'id': latest.id,
        'content': latest.content,
        'time': fmt_time(latest.created_at),
    })
