document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('uploadForm');
    const fileUpload = document.getElementById('fileUpload');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressBar = document.getElementById('progressBar');
    const progressPercent = document.getElementById('progressPercent');
    const uploadSuccess = document.getElementById('uploadSuccess');
    const uploadError = document.getElementById('uploadError');
    const errorMessage = document.getElementById('errorMessage');
    const dropArea = fileUpload.closest('.border-dashed');
    const fileListDisplay = document.createElement('div'); // 新增：显示已选文件列表
    fileListDisplay.className = 'mt-2 p-3 bg-gray-50 rounded-md hidden';
    dropArea.after(fileListDisplay); // 添加到页面

    // 1. 显示已选择的文件列表（关键反馈）
    function updateFileList() {
        const files = fileUpload.files;
        if (files.length === 0) {
            fileListDisplay.classList.add('hidden');
            return;
        }

        fileListDisplay.classList.remove('hidden');
        let html = '<p class="text-sm font-medium text-gray-700 mb-2">已选择文件：</p><ul class="text-sm text-gray-600">';
        for (let i = 0; i < files.length; i++) {
            html += `<li class="flex items-center"><i class="fa fa-file-text-o mr-2 text-gray-400"></i>${files[i].name}</li>`;
        }
        html += `</ul><p class="text-xs text-gray-500 mt-2">共 ${files.length} 个文件</p>`;
        fileListDisplay.innerHTML = html;
    }

    // 2. 监听文件选择变化（核心修复：确保选择文件后有反馈）
    fileUpload.addEventListener('change', updateFileList);

    // 3. 修复拖放功能
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });

    function highlight() {
        dropArea.classList.add('border-blue-500');
        dropArea.classList.add('bg-blue-50');
    }

    function unhighlight() {
        dropArea.classList.remove('border-blue-500');
        dropArea.classList.remove('bg-blue-50');
    }

    // 拖放后更新文件列表（核心修复）
    dropArea.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            fileUpload.files = files;
            updateFileList(); // 拖放后强制更新文件列表
        }
    }, false);

    // 4. 表单提交处理（增加验证反馈）
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const files = fileUpload.files;
        if (files.length === 0) {
            showError('请选择至少一个文件');
            return;
        }

        const formData = new FormData();
        const description = document.getElementById('fileDescription').value;

        if (description) {
            formData.append('description', description);
        }

        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }

        try {
            showProgress();
            resetStatusMessages();

            // 使用XMLHttpRequest替代fetch，更好地支持进度条（修复进度反馈）
            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/api/files/upload/');

            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    updateProgress(percent);
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    updateProgress(100);
                    setTimeout(() => {
                        hideProgress();
                        showSuccess();
                        fileUpload.value = ''; // 重置文件选择
                        updateFileList(); // 清空文件列表
                    }, 500);
                } else {
                    throw new Error('上传失败: ' + xhr.statusText);
                }
            });

            xhr.addEventListener('error', () => {
                throw new Error('网络错误，上传失败');
            });

            xhr.send(formData);

        } catch (error) {
            hideProgress();
            showError(error.message);
            console.error('上传错误:', error);
        }
    });

    // UI辅助函数
    function showProgress() {
        uploadProgress.classList.remove('hidden');
        updateProgress(0);
    }

    function hideProgress() {
        uploadProgress.classList.add('hidden');
    }

    function updateProgress(percent) {
        progressBar.style.width = `${percent}%`;
        progressPercent.textContent = `${percent}%`;
    }

    function showSuccess() {
        uploadSuccess.classList.remove('hidden');
    }

    function showError(message) {
        errorMessage.textContent = message;
        uploadError.classList.remove('hidden');
        // 3秒后自动隐藏错误消息
        setTimeout(() => uploadError.classList.add('hidden'), 3000);
    }

    function resetStatusMessages() {
        uploadSuccess.classList.add('hidden');
        uploadError.classList.add('hidden');
    }
});