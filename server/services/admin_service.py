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
    """教师账号列表"""
    page = flask_request.args.get('page', 1, type=int)
    page_size = int(ConfigItem.get('page_size', '20'))
    keyword = flask_request.args.get('keyword', '').strip()

    query = User.query.filter(User.is_admin.is_(False))
    if keyword:
        like = f"%{keyword}%"
        query = query.filter((User.username.like(like)) | (User.fullname.like(like)))

    pagination = query.order_by(User.id.desc()).paginate(page=page, per_page=page_size, error_out=False)
    return render_template('admin/teacher_list.html', pagination=pagination, keyword=keyword)


def teacher_create(flask_request):
    if flask_request.method == 'POST':
        username = flask_request.form.get('username', '').strip()
        password = flask_request.form.get('password', '')
        fullname = flask_request.form.get('fullname', '').strip()
        make_admin = flask_request.form.get('make_admin') == 'on'

        if not username or not password:
            flash('账号和密码不能为空', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('账号已存在', 'danger')
        else:
            user = User(username=username, fullname=fullname,
                        role='admin' if make_admin else 'teacher',
                        is_admin=make_admin)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('创建成功', 'success')
            return redirect(url_for('admin.teacher_list'))

    return render_template('admin/teacher_form.html', teacher=None)


def teacher_edit(flask_request, uid):
    teacher = User.query.filter_by(id=uid).first_or_404()
    if teacher.is_admin and teacher.id == flask_session.get('user_id'):
        # 自己不能取消自己管理员身份（略简单处理）
        pass

    if flask_request.method == 'POST':
        fullname = flask_request.form.get('fullname', '').strip()
        password = flask_request.form.get('password', '')
        make_admin = flask_request.form.get('make_admin') == 'on'

        teacher.fullname = fullname
        teacher.is_admin = make_admin
        teacher.role = 'admin' if make_admin else 'teacher'
        if password:
            teacher.set_password(password)
        db.session.commit()
        flash('保存成功', 'success')
        return redirect(url_for('admin.teacher_list'))

    return render_template('admin/teacher_form.html', teacher=teacher)


def teacher_delete(uid):
    teacher = User.query.get_or_404(uid)
    if teacher.is_admin and User.query.filter_by(is_admin=True).count() <= 1:
        flash('至少保留一个管理员', 'danger')
        return redirect(url_for('admin.teacher_list'))
    # 级联删除其创建的考试及其学生/提交等数据
    Exam.query.filter_by(created_by_id=teacher.id).delete()
    db.session.delete(teacher)
    db.session.commit()
    flash('已删除', 'success')
    return redirect(url_for('admin.teacher_list'))


# ==================== 考试清理（管理员视角） ====================
def exam_list(flask_request):
    """所有考试列表，管理员可清理"""
    page = flask_request.args.get('page', 1, type=int)
    page_size = int(ConfigItem.get('page_size', '20'))
    pagination = Exam.query.order_by(Exam.id.desc()).paginate(page=page, per_page=page_size, error_out=False)
    return render_template('admin/exam_list.html', pagination=pagination)


def exam_clean(flask_request, exam_id):
    """清理一场考试：删除学生、绑定、提交、通知、文件；考试标记 cleaned=True"""
    exam = Exam.query.get_or_404(exam_id)

    if exam.cleaned:
        flash('该考试已清理过', 'warning')
        return redirect(flask_request.referrer or url_for('admin.exam_list'))

    try:
        _hard_clean_exam(exam)
        exam.cleaned = True
        db.session.commit()
        flash('清理成功', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'清理失败: {e}', 'danger')

    return redirect(flask_request.referrer or url_for('admin.exam_list'))


def _hard_clean_exam(exam):
    """硬清理考试相关数据与文件"""
    exam_id = exam.id

    # 关联数据
    Binding.query.filter(Binding.student_id.in_(
        db.session.query(Student.id).filter_by(exam_id=exam_id)
    )).delete(synchronize_session=False)

    Submit.query.filter(Submit.student_id.in_(
        db.session.query(Student.id).filter_by(exam_id=exam_id)
    )).delete(synchronize_session=False)

    Notification.query.filter_by(exam_id=exam_id).delete()
    Student.query.filter_by(exam_id=exam_id).delete()

    # 删除文件
    submit_dir = os.path.join(current_app.config['SUBMIT_FOLDER'], f'exam_{exam_id}')
    if os.path.exists(submit_dir):
        shutil.rmtree(submit_dir, ignore_errors=True)

    if exam.paper:
        paper_path = os.path.join(current_app.root_path, '..', exam.paper)
        if os.path.exists(paper_path):
            try:
                os.remove(paper_path)
            except OSError:
                pass

    exam.paper = None


# ==================== 系统配置 ====================
def system_config(flask_request):
    editable_keys = [
        ('scheduler_interval_sec', '定时任务检查周期(秒)'),
        ('page_size', '分页大小'),
        ('manual_start_tolerance_min', '手动开启时间偏差(分钟)'),
        ('max_upload_mb', '上传文件大小上限(MB)'),
        ('allow_teacher_clean', '是否允许教师清理(yes/no)'),
    ]

    if flask_request.method == 'POST':
        for key, _ in editable_keys:
            value = flask_request.form.get(key, '').strip()
            ConfigItem.set(key, value)
        flash('配置已更新', 'success')
        return redirect(url_for('admin.system_config'))

    configs = {key: ConfigItem.get(key, '') for key, _ in editable_keys}
    return render_template('admin/config.html',
                           editable_keys=editable_keys, configs=configs)
