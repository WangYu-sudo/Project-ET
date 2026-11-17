"""
教师业务逻辑
考试 CRUD、试卷上传、学生导入、开启/结束、监控、解绑、通知、打包下载、导出、清理
"""
import os
import shutil
import zipfile
from datetime import datetime

from flask import (render_template, redirect, url_for, flash, session as flask_session,
                   current_app, send_file, jsonify, abort)

from ..extensions import db, bcrypt
from ..models import (User, Exam, Student, Binding, Submit,
                      Notification, ConfigItem)
from ..utils import (allowed_paper_file, read_student_file,
                     export_submits_to_excel, fmt_time)
from .admin_service import _hard_clean_exam


# ==================== 考试归属校验 ====================
def _assert_exam_owner(exam, flask_session):
    """当前用户是管理员，或是考试创建教师"""
    if flask_session.get('role') == 'admin':
        return
    if exam.created_by_id != flask_session.get('user_id'):
        abort(403)


# ==================== 考试列表 ====================
def exam_list(flask_request, flask_session):
    page = flask_request.args.get('page', 1, type=int)
    page_size = int(ConfigItem.get('page_size', '20'))
    keyword = flask_request.args.get('keyword', '').strip()

    query = Exam.query
    # 非管理员只能看自己创建的
    if flask_session.get('role') != 'admin':
        query = query.filter_by(created_by_id=flask_session['user_id'])
    if keyword:
        query = query.filter(Exam.name.like(f'%{keyword}%'))

    pagination = query.order_by(Exam.id.desc()).paginate(
        page=page, per_page=page_size, error_out=False)
    return render_template('teacher/exam_list.html',
                           pagination=pagination, keyword=keyword)


# ==================== 新建考试 ====================
def exam_create(flask_request, flask_session):
    if flask_request.method == 'POST':
        name = flask_request.form.get('name', '').strip()
        start_time_str = flask_request.form.get('start_time', '').strip()
        auto_start = flask_request.form.get('auto_start') == 'on'

        try:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M')
        except ValueError:
            flash('开始时间格式有误，请使用 YYYY-MM-DD HH:MM', 'danger')
            return render_template('teacher/exam_form.html', exam=None)

        if not name:
            flash('考试名称不能为空', 'danger')
        else:
            exam = Exam(
                name=name,
                start_time=start_time,
                auto_start=auto_start,
                created_by_id=flask_session['user_id'],
            )
            db.session.add(exam)
            db.session.commit()
            flash('考试创建成功', 'success')
            return redirect(url_for('teacher.exam_edit', exam_id=exam.id))

    return render_template('teacher/exam_form.html', exam=None)


# ==================== 编辑考试 ====================
def exam_edit(flask_request, flask_session, exam_id):
    exam = Exam.query.get_or_404(exam_id)
    _assert_exam_owner(exam, flask_session)

    if exam.started and not exam.finished:
        flash('考试已进行中，不能修改基本信息', 'warning')
        # 仍跳转到监控页
        return redirect(url_for('teacher.exam_monitor', exam_id=exam.id))

    if flask_request.method == 'POST':
        name = flask_request.form.get('name', '').strip()
        start_time_str = flask_request.form.get('start_time', '').strip()
        auto_start = flask_request.form.get('auto_start') == 'on'

        try:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M')
        except ValueError:
            flash('开始时间格式有误', 'danger')
        else:
            exam.name = name or exam.name
            exam.start_time = start_time
            exam.auto_start = auto_start
            db.session.commit()
            flash('保存成功', 'success')
            return redirect(url_for('teacher.exam_edit', exam_id=exam.id))

    return render_template('teacher/exam_form.html', exam=exam)


# ==================== 上传试卷 ====================
def exam_upload_paper(flask_request, flask_session, exam_id):
    exam = Exam.query.get_or_404(exam_id)
    _assert_exam_owner(exam, flask_session)

    if exam.finished or exam.cleaned:
        flash('考试已结束或已清理，不能上传试卷', 'danger')
        return redirect(flask_request.referrer or url_for('teacher.exam_edit', exam_id=exam.id))

    if exam.started:
        flash('考试已开始，不能再上传试卷', 'warning')
        return redirect(flask_request.referrer or url_for('teacher.exam_edit', exam_id=exam.id))

    file = flask_request.files.get('paper')
    if not file or not file.filename:
        flash('未选择文件', 'danger')
    elif not allowed_paper_file(file.filename):
        flash('不支持的试卷格式', 'danger')
    else:
        upload_dir = os.path.join(current_app.config['PAPER_FOLDER'], f'exam_{exam.id}')
        os.makedirs(upload_dir, exist_ok=True)

        # 删除旧试卷
        if exam.paper:
            old = os.path.join(current_app.root_path, '..', exam.paper)
            if os.path.exists(old):
                try:
                    os.remove(old)
                except OSError:
                    pass

        # 保存新试卷，用原始文件名（去除路径）
        original_name = os.path.basename(file.filename)
        abs_path = os.path.join(upload_dir, original_name)
        file.save(abs_path)
        rel_path = os.path.relpath(abs_path,
                                   os.path.join(current_app.root_path, '..')).replace('\\', '/')
        exam.paper = rel_path
        db.session.commit()
        flash('试卷上传成功', 'success')

    return redirect(flask_request.referrer or url_for('teacher.exam_edit', exam_id=exam.id))


# ==================== 导入学生名单 ====================
def exam_import_students(flask_request, flask_session, exam_id):
    exam = Exam.query.get_or_404(exam_id)
    _assert_exam_owner(exam, flask_session)

    file = flask_request.files.get('student_file')
    if not file or not file.filename:
        flash('未选择文件', 'danger')
        return redirect(flask_request.referrer or url_for('teacher.exam_edit', exam_id=exam.id))

    try:
        rows = read_student_file(file)
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(flask_request.referrer or url_for('teacher.exam_edit', exam_id=exam.id))

    added = 0
    skipped = 0
    for r in rows:
        exists = Student.query.filter_by(exam_id=exam.id, number=r['number']).first()
        if exists:
            skipped += 1
            # 更新姓名/班级
            exists.name = r['name']
            exists.clazz = r.get('clazz', exists.clazz)
        else:
            s = Student(exam_id=exam.id, number=r['number'],
                        name=r['name'], clazz=r.get('clazz', ''))
            db.session.add(s)
            added += 1

    db.session.commit()
    flash(f'导入完成：新增 {added} 人，更新/跳过 {skipped} 人', 'success')
    return redirect(flask_request.referrer or url_for('teacher.exam_edit', exam_id=exam.id))


# ==================== 手动添加学生 ====================
def exam_student_add(flask_request, flask_session, exam_id):
    exam = Exam.query.get_or_404(exam_id)
    _assert_exam_owner(exam, flask_session)

    number = flask_request.form.get('number', '').strip()
    name = flask_request.form.get('name', '').strip()
    clazz = flask_request.form.get('clazz', '').strip()

    if not number or not name:
        flash('学号和姓名不能为空', 'danger')
    elif Student.query.filter_by(exam_id=exam.id, number=number).first():
        flash('该学号已存在', 'warning')
    else:
        db.session.add(Student(exam_id=exam.id, number=number, name=name, clazz=clazz))
        db.session.commit()
        flash('添加成功', 'success')

    return redirect(flask_request.referrer or url_for('teacher.exam_monitor', exam_id=exam.id))


# ==================== 删除学生 ====================
def exam_student_delete(flask_request, flask_session, exam_id, sid):
    exam = Exam.query.get_or_404(exam_id=exam_id)
    _assert_exam_owner(exam, flask_session)
    student = Student.query.filter_by(id=sid, exam_id=exam.id).first_or_404()
    if exam.started:
        flash('考试已开始，不能删除学生', 'warning')
    else:
        db.session.delete(student)
        db.session.commit()
        flash('已删除', 'success')
    return redirect(flask_request.referrer or url_for('teacher.exam_edit', exam_id=exam.id))


# ==================== 开启考试 ====================
def exam_start(flask_request, flask_session, exam_id):
    exam = Exam.query.get_or_404(exam_id)
    _assert_exam_owner(exam, flask_session)

    if exam.started:
        flash('考试已开启', 'warning')
    elif exam.finished:
        flash('考试已结束，不能重新开启', 'danger')
    elif not exam.paper:
        flash('请先上传试卷', 'danger')
    elif Student.query.filter_by(exam_id=exam.id).count() == 0:
        flash('请先导入学生名单', 'danger')
    else:
        exam.started = True
        db.session.commit()
        flash('考试已开启', 'success')

    return redirect(url_for('teacher.exam_monitor', exam_id=exam.id))


# ==================== 结束考试 ====================
def exam_finish(flask_request, flask_session, exam_id):
    exam = Exam.query.get_or_404(exam_id)
    _assert_exam_owner(exam, flask_session)

    if exam.finished:
        flash('考试已结束', 'warning')
    elif not exam.started:
        flash('考试尚未开启', 'warning')
    else:
        exam.finished = True
        db.session.commit()
        flash('考试已结束，学生不能再提交', 'success')

    return redirect(url_for('teacher.exam_monitor', exam_id=exam.id))


# ==================== 监控页 ====================
def exam_monitor(flask_request, flask_session, exam_id):
    exam = Exam.query.get_or_404(exam_id)
    _assert_exam_owner(exam, flask_session)

    total = Student.query.filter_by(exam_id=exam.id).count()
    login_count = Binding.query.join(Student).filter(Student.exam_id == exam.id).count()
    submit_count = db.session.query(Submit.student_id).distinct().join(
        Student).filter(Student.exam_id == exam.id).count()

    # 最近通知
    notifications = Notification.query.filter_by(exam_id=exam.id)\
        .order_by(Notification.created_at.desc()).limit(20).all()

    # 最近提交
    recent_submits = (Submit.query.join(Student).filter(Student.exam_id == exam.id)
                      .order_by(Submit.submit_time.desc()).limit(30).all())

    # 名单搜索
    keyword = flask_request.args.get('keyword', '').strip()
    query = Student.query.filter_by(exam_id=exam.id)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter((Student.number.like(like)) | (Student.name.like(like)))
    students = query.order_by(Student.number).all()

    # 把每个学生的绑定/提交信息准备好
    student_info = []
    for s in students:
        b = Binding.query.filter_by(student_id=s.id).first()
        last_submit = (Submit.query.filter_by(student_id=s.id)
                       .order_by(Submit.submit_time.desc()).first())
        student_info.append({
            'student': s,
            'ip': b.ip if b else '',
            'login_time': fmt_time(b.login_time) if b else '',
            'submitted': last_submit is not None,
            'last_submit_time': fmt_time(last_submit.submit_time) if last_submit else '',
        })

    return render_template('teacher/exam_monitor.html',
                           exam=exam,
                           total=total, login_count=login_count, submit_count=submit_count,
                           notifications=notifications,
                           recent_submits=recent_submits,
                           student_info=student_info,
                           keyword=keyword)


# ==================== 解除 IP 锁定 ====================
def exam_unlock(flask_request, flask_session, exam_id):
    exam = Exam.query.get_or_404(exam_id)
    _assert_exam_owner(exam, flask_session)

    sid = flask_request.form.get('student_id', type=int)
    number = flask_request.form.get('number', '').strip()
    ip = flask_request.form.get('ip', '').strip()

    binding = None
    if sid:
        binding = Binding.query.filter_by(student_id=sid).first()
    elif number:
        student = Student.query.filter_by(exam_id=exam.id, number=number).first()
        if student:
            binding = Binding.query.filter_by(student_id=student.id).first()
    elif ip:
        binding = Binding.query.filter_by(ip=ip).first()

    if not binding:
        flash('未找到对应的绑定记录', 'warning')
    else:
        db.session.delete(binding)
        db.session.commit()
        flash('已解除锁定', 'success')

    return redirect(flask_request.referrer or url_for('teacher.exam_monitor', exam_id=exam.id))


# ==================== 通知管理 ====================
def exam_notify(flask_request, flask_session, exam_id):
    exam = Exam.query.get_or_404(exam_id)
    _assert_exam_owner(exam, flask_session)

    content = flask_request.form.get('content', '').strip()
    if content:
        n = Notification(exam_id=exam.id, content=content)
        db.session.add(n)
        db.session.commit()
        flash('通知已发布', 'success')
    return redirect(flask_request.referrer or url_for('teacher.exam_monitor', exam_id=exam.id))


def exam_notify_delete(flask_request, flask_session, exam_id, nid):
    exam = Exam.query.get_or_404(exam_id)
    _assert_exam_owner(exam, flask_session)
    n = Notification.query.filter_by(id=nid, exam_id=exam.id).first_or_404()
    db.session.delete(n)
    db.session.commit()
    return redirect(flask_request.referrer or url_for('teacher.exam_monitor', exam_id=exam.id))


# ==================== 打包下载答卷 ====================
def exam_download(flask_request, flask_session, exam_id):
    exam = Exam.query.get_or_404(exam_id)
    _assert_exam_owner(exam, flask_session)

    submit_root = os.path.join(current_app.config['SUBMIT_FOLDER'], f'exam_{exam.id}')
    if not os.path.exists(submit_root):
        flash('暂无答卷文件', 'warning')
        return redirect(url_for('teacher.exam_monitor', exam_id=exam.id))

    tmp_dir = current_app.config['TMP_FOLDER']
    os.makedirs(tmp_dir, exist_ok=True)
    zip_path = os.path.join(tmp_dir, f'exam_{exam.id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip')

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for student in Student.query.filter_by(exam_id=exam.id):
            stu_dir = os.path.join(submit_root, f'{student.number}_{student.name}')
            if not os.path.exists(stu_dir):
                continue
            for root, dirs, files in os.walk(stu_dir):
                for f in files:
                    full = os.path.join(root, f)
                    arcname = os.path.relpath(full, submit_root)
                    zf.write(full, arcname)

    return send_file(zip_path, as_attachment=True,
                     download_name=os.path.basename(zip_path),
                     mimetype='application/zip')


# ==================== 导出提交信息 ====================
def exam_export(flask_request, flask_session, exam_id):
    exam = Exam.query.get_or_404(exam_id)
    _assert_exam_owner(exam, flask_session)

    students = Student.query.filter_by(exam_id=exam.id).order_by(Student.number).all()

    data = []
    for s in students:
        last = Submit.query.filter_by(student_id=s.id)\
            .order_by(Submit.submit_time.desc()).first()
        data.append({
            'clazz': s.clazz,
            'number': s.number,
            'name': s.name,
            'submit_time': fmt_time(last.submit_time) if last else '未提交',
        })

    tmp_dir = current_app.config['TMP_FOLDER']
    os.makedirs(tmp_dir, exist_ok=True)
    excel_path = os.path.join(tmp_dir, f'exam_{exam.id}_提交信息.xlsx')
    export_submits_to_excel(data, excel_path)

    return send_file(excel_path, as_attachment=True,
                     download_name=os.path.basename(excel_path),
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# ==================== 清理考试（教师视角） ====================
def exam_clean(flask_request, flask_session, exam_id):
    exam = Exam.query.get_or_404(exam_id)
    _assert_exam_owner(exam, flask_session)

    if not exam.finished:
        flash('考试尚未结束，不能清理', 'warning')
        return redirect(flask_request.referrer or url_for('teacher.exam_monitor', exam_id=exam.id))

    allow = ConfigItem.get('allow_teacher_clean', 'yes').lower()
    if allow != 'yes' and flask_session.get('role') != 'admin':
        flash('管理员未授权教师清理，请联系管理员', 'danger')
        return redirect(flask_request.referrer or url_for('teacher.exam_monitor', exam_id=exam.id))

    if exam.cleaned:
        flash('已清理过', 'warning')
        return redirect(url_for('teacher.exam_list'))

    _hard_clean_exam(exam)
    exam.cleaned = True
    db.session.commit()
    flash('清理成功', 'success')
    return redirect(url_for('teacher.exam_list'))
