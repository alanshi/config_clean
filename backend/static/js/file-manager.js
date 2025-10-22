document.addEventListener('DOMContentLoaded', () => {
    const batchesList = document.getElementById('batchesList');
    const noBatches = document.getElementById('noBatches');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const refreshBatchesBtn = document.getElementById('refreshBatches');
    const fileContentModal = document.getElementById('fileContentModal');
    const modalTitle = document.getElementById('modalTitle');
    const fileContent = document.getElementById('fileContent');
    const closeModal = document.getElementById('closeModal');
    const closeModalBtn = document.getElementById('closeModalBtn');

    // 加载批次列表
    loadBatches();

    // 刷新按钮事件
    refreshBatchesBtn.addEventListener('click', loadBatches);

    // 关闭模态框事件
    closeModal.addEventListener('click', hideFileContentModal);
    closeModalBtn.addEventListener('click', hideFileContentModal);

    // 点击模态框外部关闭
    fileContentModal.addEventListener('click', (e) => {
        if (e.target === fileContentModal) {
            hideFileContentModal();
        }
    });

    // 加载批次数据
    async function loadBatches() {
        showLoading();
        try {
            const response = await fetch('/api/batches/');
            if (!response.ok) {
                throw new Error('获取批次数据失败');
            }

            const batches = await response.json();
            displayBatches(batches);

        } catch (error) {
            console.error('加载批次错误:', error);
            showError('加载批次失败，请重试');
        } finally {
            hideLoading();
        }
    }

    // 显示批次列表
function displayBatches(batches) {
    batchesList.innerHTML = '';

    // 校验 batches 是否为数组
    if (!Array.isArray(batches)) {
        showError('获取的数据格式错误');
        return;
    }

    if (batches.length === 0) {
        noBatches.classList.remove('hidden');
        batchesList.classList.add('hidden');
        return;
    }

    noBatches.classList.add('hidden');
    batchesList.classList.remove('hidden');

    // 按时间戳降序排序
    batches.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    batches.forEach(batch => {
        // 关键修复：强制为缺失的文件列表字段设置默认空数组
        batch.original_files = batch.original_files || [];
        batch.cleaned_files_1 = batch.cleaned_files_1 || [];
        batch.cleaned_files_2 = batch.cleaned_files_2 || [];
        // 确保id存在（避免后续操作报错）
        batch.id = batch.id || Date.now(); // 临时id，避免undefined

        const batchElement = createBatchElement(batch);
        batchesList.appendChild(batchElement);
    });
}
    // 创建批次元素
    function createBatchElement(batch) {
        const batchDiv = document.createElement('div');
        batchDiv.className = 'border rounded-lg overflow-hidden';

        const formattedDate = new Date(batch.timestamp).toLocaleString();

        const originalFiles = batch.original_files || [];
        const cleanedFiles1 = batch.cleaned_files_1 || [];
        const cleanedFiles2 = batch.cleaned_files_2 || [];

        batchDiv.innerHTML = `
        <div class="bg-gray-50 px-4 py-3 border-b flex justify-between items-center">
            <div>
                <h3 class="font-medium text-gray-900">批次 #${batch.id || '未知'}</h3>
                <p class="text-sm text-gray-500">创建时间: ${formattedDate}</p>
                ${batch.description ? `<p class="text-sm text-gray-600 mt-1">描述: ${batch.description}</p>` : ''}
            </div>
            <button class="viewBatchDetails px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
                    data-batch-id="${batch.id}">
                查看详情
            </button>
        </div>
        <div class="batchDetails hidden p-4">
            <div class="mb-4">
                <h4 class="font-medium text-gray-800 mb-2">原始文件 (${originalFiles.length})</h4>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-2 originalFiles">
                    ${originalFiles.map(file => createFileElement(file, 'original')).join('')}
                </div>
            </div>

            <div class="mb-4">
                <h4 class="font-medium text-gray-800 mb-2">初次清洗文件 (${cleanedFiles1.length})</h4>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-2 cleanedFiles1">
                    ${cleanedFiles1.map(file => createFileElement(file, 'cleaned1')).join('')}
                </div>
            </div>

            <div>
                <div class="flex justify-between items-center mb-2">
                    <h4 class="font-medium text-gray-800">二次清洗文件 (${cleanedFiles2.length})</h4>
                    ${cleanedFiles1.length > 0 && cleanedFiles2.length === 0 ? `
                        <button class="performClean2 px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700"
                                data-batch-id="${batch.id}">
                            执行二次清洗
                        </button>
                    ` : ''}
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-2 cleanedFiles2">
                    ${cleanedFiles2.map(file => createFileElement(file, 'cleaned2')).join('')}
                </div>
            </div>
        </div>
    `;

        // 添加查看详情事件
        batchDiv.querySelector('.viewBatchDetails').addEventListener('click', function() {
            const detailsDiv = batchDiv.querySelector('.batchDetails');
            detailsDiv.classList.toggle('hidden');
            this.textContent = detailsDiv.classList.contains('hidden') ? '查看详情' : '收起详情';
        });

        // 添加查看文件内容事件
        batchDiv.querySelectorAll('.viewFileContent').forEach(btn => {
            btn.addEventListener('click', function() {
                const fileId = this.dataset.fileId;
                const fileType = this.dataset.fileType;
                const fileName = this.dataset.fileName;
                viewFileContent(fileId, fileType, fileName);
            });
        });

        // 添加二次清洗事件
        const clean2Btn = batchDiv.querySelector('.performClean2');
        if (clean2Btn) {
            clean2Btn.addEventListener('click', async function() {
                const batchId = this.dataset.batchId;
                await performSecondCleaning(batchId, batchDiv);
            });
        }

        return batchDiv;
    }

    // 创建文件元素
    function createFileElement(file, fileType) {
        return `
            <div class="flex justify-between items-center p-2 border rounded bg-gray-50">
                <span class="text-sm truncate max-w-[70%]">${file.filename}</span>
                <button class="viewFileContent text-blue-600 hover:text-blue-800 text-sm"
                        data-file-id="${file.id}"
                        data-file-type="${fileType}"
                        data-file-name="${file.filename}">
                    <i class="fa fa-eye mr-1"></i> 查看
                </button>
            </div>
        `;
    }

async function viewFileContent(fileId, fileType, fileName) {
    try {
        const response = await fetch(`/api/files/${fileType}/${fileId}/content`);
        if (!response.ok) {
            throw new Error('获取文件内容失败');
        }

        const modalTitle = document.getElementById('modalTitle');
        const fileContent = document.getElementById('fileContent');
        modalTitle.textContent = `文件内容: ${fileName}`;

        // 针对二次清洗的JSON文件进行特殊处理
        if (fileType === 'cleaned2' && fileName.endsWith('.json')) {
            try {
                // 解析JSON并格式化展示
                const jsonData = await response.json();

                // 添加JSON高亮样式
                fileContent.innerHTML = `
                    <style>
                        .json-key { color: #0066cc; font-weight: bold; }
                        .json-string { color: #008000; }
                        .json-number { color: #ff0000; }
                        .json-boolean { color: #aa00aa; }
                        .json-null { color: #888888; }
                        .json-indent { margin-left: 20px; }
                    </style>
                    ${formatJson(jsonData)}
                `;
            } catch (e) {
                // 解析失败时显示原始文本
                const content = await response.text();
                fileContent.textContent = content;
            }
        } else {
            // 其他文件显示原始文本
            const content = await response.text();
            fileContent.textContent = content;
        }

        showFileContentModal();

    } catch (error) {
        console.error('获取文件内容错误:', error);
        alert('获取文件内容失败，请重试');
    }
}

    // 新增：JSON格式化显示函数
function formatJson(data, indent = 0) {
    const spaces = '  '.repeat(indent);
    let result = '';

    if (typeof data === 'object' && data !== null) {
        const isArray = Array.isArray(data);
        result += isArray ? '[' : '{';
        result += '<br>';

        const entries = isArray ? data.entries() : Object.entries(data);
        const total = entries.length;
        let index = 0;

        for (const [key, value] of entries) {
            const isLast = index === total - 1;
            const keyPart = isArray ? '' : `<span class="json-key">"${key}": </span>`;

            result += `${spaces}  ${keyPart}${formatJson(value, indent + 1)}`;
            result += isLast ? '' : ',';
            result += '<br>';
            index++;
        }

        result += `${spaces}${isArray ? ']' : '}'}`;
    } else if (typeof data === 'string') {
        result += `<span class="json-string">"${escapeHtml(data)}"</span>`;
    } else if (typeof data === 'number') {
        result += `<span class="json-number">${data}</span>`;
    } else if (typeof data === 'boolean') {
        result += `<span class="json-boolean">${data}</span>`;
    } else {
        result += `<span class="json-null">null</span>`;
    }

    return result;
}

// 新增：HTML转义函数（防止XSS）
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


    // 执行二次清洗
    async function performSecondCleaning(batchId, batchElement) {
        if (!confirm('确定要执行二次清洗吗？')) {
            return;
        }

        try {
            const response = await fetch(`/api/batches/${batchId}/clean2`, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error('二次清洗失败');
            }

            // 重新加载批次数据
            loadBatches();

        } catch (error) {
            console.error('二次清洗错误:', error);
            alert('二次清洗失败，请重试');
        }
    }

    // 显示文件内容模态框
    function showFileContentModal() {
        fileContentModal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }

    // 隐藏文件内容模态框
    function hideFileContentModal() {
        fileContentModal.classList.add('hidden');
        document.body.style.overflow = '';
    }

    // 显示加载状态
    function showLoading() {
        loadingIndicator.classList.remove('hidden');
        batchesList.classList.add('hidden');
        noBatches.classList.add('hidden');
    }

    // 隐藏加载状态
    function hideLoading() {
        loadingIndicator.classList.add('hidden');
    }

    // 显示错误消息
    function showError(message) {
        batchesList.classList.add('hidden');
        noBatches.classList.remove('hidden');
        noBatches.innerHTML = `
            <i class="fa fa-exclamation-circle text-5xl mb-4 text-red-500"></i>
            <p>${message}</p>
        `;
    }
});