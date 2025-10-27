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

    // 模态框元素
    const keywordSetModal = document.getElementById('keywordSetModal');
    const keywordSetSelect = document.getElementById('keywordSetSelect');
    noKeywordSetTip = document.getElementById('noKeywordSetTip');
    const closeModal = document.getElementById('closeModal');
    const cancelKeywordSelect = document.getElementById('cancelKeywordSelect');
    const confirmKeywordSelect = document.getElementById('confirmKeywordSelect');
    // 存储选中的关键词组ID
    let selectedKeywordSetId = null;

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
        // 加载关键词组并显示模态框
        loadKeywordSets();
        keywordSetModal.classList.remove('hidden');

        // const formData = new FormData();
        // const description = document.getElementById('fileDescription').value;

        // if (description) {
        //     formData.append('description', description);
        // }

        // for (let i = 0; i < files.length; i++) {
        //     formData.append('files', files[i]);
        // }

        // try {
        //     showProgress();
        //     resetStatusMessages();

        //     // 使用XMLHttpRequest替代fetch，更好地支持进度条（修复进度反馈）
        //     const xhr = new XMLHttpRequest();
        //     xhr.open('POST', '/api/files/upload/');

        //     xhr.upload.addEventListener('progress', (e) => {
        //         if (e.lengthComputable) {
        //             const percent = Math.round((e.loaded / e.total) * 100);
        //             updateProgress(percent);
        //         }
        //     });

        //     xhr.addEventListener('load', () => {
        //         if (xhr.status >= 200 && xhr.status < 300) {
        //             updateProgress(100);
        //             setTimeout(() => {
        //                 hideProgress();
        //                 showSuccess();
        //                 fileUpload.value = ''; // 重置文件选择
        //                 updateFileList(); // 清空文件列表
        //             }, 500);
        //         } else {
        //             throw new Error('上传失败: ' + xhr.statusText);
        //         }
        //     });

        //     xhr.addEventListener('error', () => {
        //         throw new Error('网络错误，上传失败');
        //     });

        //     xhr.send(formData);

        // } catch (error) {
        //     hideProgress();
        //     showError(error.message);
        //     console.error('上传错误:', error);
        // }
    });
    // 2. 加载所有关键词组（从后端接口获取）
    async function loadKeywordSets() {
        try {
            const response = await fetch('/api/keywords/sets/'); // 后端获取关键词组列表的接口
            if (!response.ok) {
                throw new Error('获取关键词组失败');
            }

            const keywordSets = await response.json();
            keywordSetSelect.innerHTML = ''; // 清空加载提示

            // 无关键词组时显示提示
            if (keywordSets.length === 0) {
                keywordSetSelect.innerHTML = '<option value="" disabled selected>无可用关键词组</option>';
                noKeywordSetTip.classList.remove('hidden');
                confirmKeywordSelect.disabled = true;
                return;
            }

            // 填充关键词组下拉列表
            noKeywordSetTip.classList.add('hidden');
            keywordSets.forEach(set => {
                const option = document.createElement('option');
                option.value = set.id;
                option.textContent = `${set.name}（${set.keywords.length}个关键词）`;
                keywordSetSelect.appendChild(option);
            });

            // 启用确认按钮
            confirmKeywordSelect.disabled = false;
        } catch (error) {
            keywordSetSelect.innerHTML = '<option value="" disabled selected>加载失败</option>';
            showError(`关键词组加载失败: ${error.message}`);
            confirmKeywordSelect.disabled = true;
        }
    }


    // 3. 模态框事件：关闭/取消
    function closeKeywordModal() {
        keywordSetModal.classList.add('hidden');
        document.body.style.overflow = ''; // 恢复页面滚动
        selectedKeywordSetId = null; // 重置选中状态
    }

    [closeModal, cancelKeywordSelect].forEach(btn => {
        btn.addEventListener('click', closeKeywordModal);
    });

    // 点击模态框外部关闭
    keywordSetModal.addEventListener('click', (e) => {
        if (e.target === keywordSetModal) {
            closeKeywordModal();
        }
    });

    // 4. 确认选择关键词组：执行上传
    confirmKeywordSelect.addEventListener('click', async () => {

        var selectedKeywordSetId = keywordSetSelect.value;
        console.log(selectedKeywordSetId);
        if (!selectedKeywordSetId) {
            showError('请选择一个关键词组');
            return;
        }

        // 关闭模态框，显示进度条
        closeKeywordModal();
        uploadProgress.classList.remove('hidden');
        uploadSuccess.classList.add('hidden');
        uploadError.classList.add('hidden');

        // 构造FormData（包含文件、描述、关键词组ID）
        const formData = new FormData(uploadForm);
        // add keyword_set_id to formData
        formData.append('keyword_set_id', selectedKeywordSetId); // 关键：传递关键词组ID
        console.log(selectedKeywordSetId);
        try {
            // 发送上传请求（带进度监听）
            const response = await fetch('/api/files/upload/', { // 后端上传接口
                method: 'POST',
                body: formData,
                headers: {
                    // 注意：FormData不需要设置Content-Type，浏览器会自动处理
                },

                signal: new AbortController().signal,
            });

            // 处理响应
            if (!response.ok) {
                const errorData = await response.json().catch(() => null);
                throw new Error(errorData?.detail || '文件上传失败');
            }

            // 上传成功
            progressBar.style.width = '100%';
            progressPercent.textContent = '100%';
            uploadSuccess.classList.remove('hidden');
            // 重置表单
            uploadForm.reset();
            setTimeout(() => {
                uploadProgress.classList.add('hidden');
            }, 1000);

        } catch (error) {
            // 上传失败
            uploadProgress.classList.add('hidden');
            showError(error.message);
        }
    });

      // 5. 辅助：显示错误提示
    function showError(msg) {
        errorMessage.textContent = msg;
        uploadError.classList.remove('hidden');
        // 3秒后自动隐藏错误提示
        setTimeout(() => {
            uploadError.classList.add('hidden');
        }, 3000);
    }


    // 6. 可选：监听文件选择，自动启用上传按钮
    fileUpload.addEventListener('change', () => {
        if (fileUpload.files.length > 0) {
            uploadButton.disabled = false;
        } else {
            uploadButton.disabled = true;
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