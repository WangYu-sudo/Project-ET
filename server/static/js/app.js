/* ===== 上机考试管理系统 - 前端脚本 ===== */

$(function () {

    // ============================================================
    // 通用确认弹窗：为所有带 data-confirm 属性的 form / a 提供确认
    // 用法：
    //   <form method="post" data-confirm="确定要删除吗？">...</form>
    // 依赖 Bootstrap 5 Modal
    // ============================================================
    var $modal = $('#__confirm_modal__');
    if (!$modal.length) {
        $('body').append(
            '<div class="modal fade" id="__confirm_modal__" tabindex="-1">' +
            '  <div class="modal-dialog modal-dialog-centered">' +
            '    <div class="modal-content">' +
            '      <div class="modal-header bg-warning text-white">' +
            '        <h5 class="modal-title"><i class="bi bi-exclamation-triangle"></i> 确认操作</h5>' +
            '        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>' +
            '      </div>' +
            '      <div class="modal-body" id="__confirm_body__">确定要执行此操作吗？</div>' +
            '      <div class="modal-footer">' +
            '        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>' +
            '        <button type="button" class="btn btn-danger" id="__confirm_ok__">确认</button>' +
            '      </div>' +
            '    </div>' +
            '  </div>' +
            '</div>'
        );
        $modal = $('#__confirm_modal__');
    }
    var confirmModal = new bootstrap.Modal($modal[0]);
    var $body = $('#__confirm_body__');
    var $ok = $('#__confirm_ok__');
    var pendingForm = null;

    // 拦截 form submit
    $(document).on('submit', 'form[data-confirm]', function (e) {
        var $form = $(this);
        var msg = $form.attr('data-confirm') || '确定要执行此操作吗？';
        pendingForm = $form;
        $body.text(msg);
        confirmModal.show();
        e.preventDefault();
        e.stopImmediatePropagation();
        return false;
    });

    // 点击确认按钮后，取消拦截并重新提交
    $ok.off('click').on('click', function () {
        confirmModal.hide();
        if (pendingForm) {
            var form = pendingForm[0];
            pendingForm = null;
            form.submit();
        }
    });

    // 清理
    $modal.on('hidden.bs.modal', function () {
        pendingForm = null;
    });


    // ============================================================
    // 学生端通知轮询（仅在页面包含 #notify-area 时启用）
    // 由 student/exam.html 内联脚本负责，这里仅提供一个通用封装，
    // 方便其他模板复用时调用： $.startNotifyPoll(url, options)
    // ============================================================
    $.startNotifyPoll = function (url, options) {
        options = options || {};
        var intervalMs = options.interval || 5000;
        var lastId = options.lastId || 0;
        var $area = options.$area || $('#notify-area');
        var $content = options.$content || $('#notify-content');

        function tick() {
            $.ajax({
                url: url,
                type: 'GET',
                data: { last_id: lastId },
                dataType: 'json',
                success: function (data) {
                    if (data && data.has_new) {
                        $content.text(data.content);
                        $area.removeClass('d-none');
                        lastId = data.id;
                    }
                }
            });
        }
        tick();
        setInterval(tick, intervalMs);
    };

});
