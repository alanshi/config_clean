document.addEventListener('DOMContentLoaded', () => {
    // 页面元素
    const batchesList = document.getElementById('batchesList');
    const noBatches = document.getElementById('noBatches');
    const errorMessage = document.getElementById('errorMessage');
    const fileContentModal = document.getElementById('fileContentModal');
    const modalTitle = document.getElementById('modalTitle');
    const fileContent = document.getElementById('fileContent');
    const closeModal = document.getElementById('closeModal');

    // 页面加载时加载批次数据
    loadBatches();

    // 加载所有批次
    async function loadBatches() {
        try {
            const response = await fetch('/api/batches/');
            if (!response.ok) {
                throw new Error(`HTTP错误: ${response.status}`);
            }
            const batches = await response.json();
            displayBatches(batches);
        } catch (error) {
            console.error('加载批次错误:', error);
            showError(`加载批次失败: ${error.message}`);
        }
    }

    // 显示批次列表
    function displayBatches(batches) {
        batchesList.innerHTML = '';
        hideError();

        // 校验批次数据格式
        if (!Array.isArray(batches)) {
            showError('获取的批次数据格式错误');
            return;
        }

        if (batches.length === 0) {
            noBatches.classList.remove('hidden');
            batchesList.classList.add('hidden');
            return;
        }

        noBatches.classList.add('hidden');
        batchesList.classList.remove('hidden');

        // 按时间戳降序排序（最新的在前）
        // batches.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).reverse();
        batches.sort((a, b) => b.id - a.id);

        batches.forEach(batch => {
            // 确保必要字段存在（防止undefined错误）
            batch.original_files = batch.original_files || [];
            batch.cleaned_files_1 = batch.cleaned_files_1 || [];
            batch.cleaned_files_2 = batch.cleaned_files_2 || [];
            batch.id = batch.id || Date.now(); // 临时ID避免undefined
            batch.timestamp = batch.timestamp || new Date().toISOString();

            const batchElement = createBatchElement(batch);
            batchesList.appendChild(batchElement);
        });
    }

    // 创建单个批次的DOM元素
    function createBatchElement(batch) {
        const batchDiv = document.createElement('div');
        batchDiv.className = 'border rounded-lg mb-6 overflow-hidden';
        batchDiv.dataset.batchId = batch.id;

        // 格式化日期显示
        const formattedDate = new Date(batch.timestamp).toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });

        // 生成批次HTML
        batchDiv.innerHTML = `
            <div class="bg-gray-50 px-4 py-3 border-b flex justify-between items-center">
                <div>
                    <h3 class="font-medium text-gray-900">批次 #${batch.id}</h3>
                    <p class="text-sm text-gray-500">创建时间: ${formattedDate}</p>
                    ${batch.description ? `<p class="text-sm text-gray-600 mt-1">描述: ${batch.description}</p>` : ''}
                </div>
                <button class="viewBatchDetails px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
                        data-batch-id="${batch.id}">
                    查看详情
                </button>
            </div>
            <div class="batchDetails hidden p-4">
                <!-- 原始文件区域 -->
                <div class="mb-6">
                    <h4 class="font-medium text-gray-800 mb-2">原始文件 (${batch.original_files.length})</h4>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-2 originalFiles">
                        ${batch.original_files.map(file => createFileElement(file, 'original')).join('')}
                    </div>
                </div>

                <!-- 初次清洗文件区域 -->
                <div class="mb-6">
                    <h4 class="font-medium text-gray-800 mb-2">初次清洗文件 (${batch.cleaned_files_1.length})</h4>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-2 cleanedFiles1">
                        ${batch.cleaned_files_1.map(file => createFileElement(file, 'cleaned1')).join('')}
                    </div>
                </div>

                <!-- 二次清洗文件区域 -->
                <div class="mb-4">
                    <div class="flex justify-between items-center mb-2">
                        <h4 class="font-medium text-gray-800">二次清洗文件 (${batch.cleaned_files_2.length})</h4>
                        ${batch.cleaned_files_1.length > 0 && batch.cleaned_files_2.length === 0 ? `
                            <button class="performClean2 px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700"
                                    data-batch-id="${batch.id}">
                                执行二次清洗
                            </button>
                        ` : ''}
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-2 cleanedFiles2">
                        ${batch.cleaned_files_2.map(file => createFileElement(file, 'cleaned2')).join('')}
                    </div>
                </div>

                <!-- 关键词匹配区域 -->
                ${batch.cleaned_files_2.length > 0 ? `
                    <div class="mt-4">
                        <button class="performKeywordCheck px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 text-sm"
                                data-batch-id="${batch.id}">
                            <i class="fa fa-search mr-1"></i> 执行关键词检查
                        </button>
                    </div>
                ` : ''}
            </div>
        `;

        // 绑定"查看详情"按钮事件
        batchDiv.querySelector('.viewBatchDetails').addEventListener('click', function () {
            const detailsDiv = batchDiv.querySelector('.batchDetails');
            detailsDiv.classList.toggle('hidden');
        });

        // 绑定"执行二次清洗"按钮事件
        const clean2Btn = batchDiv.querySelector('.performClean2');
        if (clean2Btn) {
            clean2Btn.addEventListener('click', async function () {
                const batchId = this.dataset.batchId;
                await performClean2(batchId);
            });
        }

        // 绑定"执行关键词检查"按钮事件
        const keywordCheckBtn = batchDiv.querySelector('.performKeywordCheck');
        if (keywordCheckBtn) {
            keywordCheckBtn.addEventListener('click', async function () {
                const batchId = this.dataset.batchId;
                await performKeywordCheck(batchId, batchDiv);
            });
        }

        return batchDiv;
    }

    // 创建单个文件的DOM元素
    function createFileElement(file, fileType) {
        // 为不同文件类型添加额外操作按钮
        let extraActions = '';
        if (fileType === 'cleaned2') {
            extraActions = `
                <button class="viewKeywordMatches ml-2 px-2 py-0 text-xs bg-purple-100 text-purple-800 rounded hover:bg-purple-200"
                        data-file-id="${file.id}"
                        data-batch-id="${file.batch_id || file.batchId}">
                    关键词匹配
                </button>
            `;
        }

        return `
            <div class="flex justify-between items-center p-2 border rounded bg-gray-50">
                <span class="text-sm truncate max-w-[60%]">${file.filename}</span>
                <div>
                    <button class="viewFileContent text-blue-600 hover:text-blue-800 text-sm"
                            data-file-id="${file.id}"
                            data-file-type="${fileType}"
                            data-file-name="${file.filename}">
                        <i class="fa fa-eye mr-1"></i> 查看
                    </button>
                    ${extraActions}
                </div>
            </div>
        `;
    }

    // 查看文件内容
    async function viewFileContent(fileId, fileType, fileName) {
        try {
            const response = await fetch(`/api/files/${fileType}/${fileId}/content`);
            if (!response.ok) {
                throw new Error('获取文件内容失败');
            }

            // 更新模态框标题
            modalTitle.textContent = `文件内容: ${fileName}`;

            // 处理不同类型文件的展示
            if (fileType === 'cleaned2' && fileName.endsWith('.json')) {
                try {
                    // 二次清洗的JSON文件特殊格式化展示
                    const jsonData = await response.json();
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

            // 显示模态框
            fileContentModal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';

        } catch (error) {
            console.error('获取文件内容错误:', error);
            alert('获取文件内容失败，请重试');
        }
    }

    // 执行二次清洗
    async function performClean2(batchId) {
        if (!confirm('确定要执行二次清洗吗？这将处理所有初次清洗后的文件。')) {
            return;
        }

        try {
            const response = await fetch(`/api/batches/${batchId}/clean2`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error('二次清洗失败');
            }

            // 刷新批次列表
            loadBatches();
            alert('二次清洗已完成');

        } catch (error) {
            console.error('二次清洗错误:', error);
            alert(`二次清洗失败: ${error.message}`);
        }
    }

    // 执行关键词检查
    async function performKeywordCheck(batchId, batchElement) {
        try {
            // 1. 获取该批次的二次清洗文件
            const batchResponse = await fetch(`/api/batches/${batchId}`);
            if (!batchResponse.ok) {
                throw new Error('获取批次信息失败');
            }
            const batch = await batchResponse.json();
            const cleanedFileIds = batch.cleaned_files_2.map(file => file.id);

            if (cleanedFileIds.length === 0) {
                alert('该批次没有二次清洗文件，请先执行二次清洗');
                return;
            }

            const keywordSetsResponse = await fetch('/api/keywords/sets/');
            if (!keywordSetsResponse.ok) {
                throw new Error('获取关键词组失败');
            }
            const keywordSets = await keywordSetsResponse.json();

            if (keywordSets.length === 0) {
                alert('没有可用的关键词组，请先创建关键词组');
                return;
            }

            // 3. 创建关键词组选择弹窗（不变）
            const selectModal = document.createElement('div');
            selectModal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4';
            selectModal.innerHTML = `
            <div class="bg-white rounded-lg shadow-xl max-w-md w-full">
                <div class="p-4 border-b">
                    <h3 class="text-lg font-semibold text-gray-800">选择关键词组</h3>
                </div>
                <div class="p-4">
                    <p class="mb-3 text-sm text-gray-600">请选择用于检查的关键词组：</p>
                    <select id="keywordSetSelect" class="w-full px-3 py-2 border border-gray-300 rounded-md">
                        ${keywordSets.map(set => `
                            <option value="${set.id}">${set.name} (${set.keywords.length}个关键词)</option>
                        `).join('')}
                    </select>
                </div>
                <div class="p-4 border-t flex justify-end gap-2">
                    <button class="cancelSelect px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">
                        取消
                    </button>
                    <button class="confirmSelect px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
                        确认检查（将检测该批次所有二次清洗文件）
                    </button>
                </div>
            </div>
        `;
            document.body.appendChild(selectModal);
            document.body.style.overflow = 'hidden';

            // 4. 绑定弹窗按钮事件
            const cancelBtn = selectModal.querySelector('.cancelSelect');
            const confirmBtn = selectModal.querySelector('.confirmSelect');

            cancelBtn.addEventListener('click', () => {
                document.body.removeChild(selectModal);
                document.body.style.overflow = '';
            });

            confirmBtn.addEventListener('click', async () => {
                const keywordSetId = selectModal.querySelector('#keywordSetSelect').value;
                document.body.removeChild(selectModal);
                document.body.style.overflow = '';

                    // 执行关键词检查（参数放在请求体中，而非查询参数）
    const response = await fetch('/api/keywords/match/', {  // 移除URL中的查询参数
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',  // 明确JSON格式
        },
        // 关键：在body中传递参数（JSON字符串）
        body: JSON.stringify({
            batch_id: parseInt(batchId),  // 批次ID（数字类型）
            keyword_set_id: parseInt(keywordSetId)  // 关键词组ID（数字类型）
        })
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        const errorMessage = errorData?.detail || await response.text() || '未知错误';
        throw new Error(errorMessage);
    }

    loadBatches();
    alert('关键词检查已完成');
            });

        } catch (error) {
            console.error('关键词检查错误:', error);
            alert(`关键词检查失败: ${error.message}`);
        }
    }

    // 查看关键词匹配结果
    async function viewKeywordMatches(batchId, fileId) {
        try {
            // 获取该批次的所有匹配结果
            const resultsResponse = await fetch(`/api/keywords/match/batch/${batchId}`);
            if (!resultsResponse.ok) {
                throw new Error('获取匹配结果失败');
            }
            const results = await resultsResponse.json();

            // 筛选当前文件的结果
            const fileResults = results.filter(res => res.file_id === parseInt(fileId));
            if (fileResults.length === 0) {
                alert('没有找到该文件的关键词匹配结果');
                return;
            }

            // 获取对应的关键词组信息
            const result = fileResults[0];
            const keywordSetResponse = await fetch(`/api/keywords/sets/${result.keyword_set_id}`);
            if (!keywordSetResponse.ok) {
                throw new Error('获取关键词组信息失败');
            }
            const keywordSet = await keywordSetResponse.json();

            // 生成结果HTML
            let resultHtml = `
                <div class="mb-4">
                    <h3 class="text-lg font-semibold text-gray-800">${keywordSet.name}</h3>
                    <p class="text-sm text-gray-500">
                        匹配时间: ${new Date(result.created_at).toLocaleString()} |
                        设备厂商: ${result.match_data.vendor || '未知'}
                    </p>
                </div>
            `;

            // 按章节展示匹配结果
            const sections = Object.keys(result.match_data.matches);
            if (sections.length === 0) {
                resultHtml += '<p class="text-gray-600">没有找到匹配的关键词</p>';
            } else {
                sections.forEach(section => {
                    resultHtml += `
                        <div class="mb-4 p-3 bg-gray-50 rounded-md">
                            <h4 class="font-medium text-gray-800 mb-2">${section}</h4>
                            <ul class="space-y-2 text-sm">
                                ${result.match_data.matches[section].map(match => `
                                    <li class="flex">
                                        <span class="text-gray-500 w-16">行 ${match.line}:</span>
                                        <span><strong class="text-purple-600">${match.keyword}</strong> - ${escapeHtml(match.content)}</span>
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                    `;
                });
            }

            // 创建结果弹窗
            const resultModal = document.createElement('div');
            resultModal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4';
            resultModal.innerHTML = `
                <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] flex flex-col">
                    <div class="p-4 border-b flex justify-between items-center">
                        <h3 class="text-lg font-semibold text-gray-800">关键词匹配详情</h3>
                        <button class="closeResultModal text-gray-500 hover:text-gray-700">
                            <i class="fa fa-times text-xl"></i>
                        </button>
                    </div>
                    <div class="p-4 flex-grow overflow-auto">
                        ${resultHtml}
                    </div>
                    <div class="p-4 border-t flex justify-end">
                        <button class="closeResultBtn px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">
                            关闭
                        </button>
                    </div>
                </div>
            `;
            document.body.appendChild(resultModal);
            document.body.style.overflow = 'hidden';

            // 绑定关闭按钮事件
            resultModal.querySelectorAll('.closeResultModal, .closeResultBtn').forEach(btn => {
                btn.addEventListener('click', () => {
                    document.body.removeChild(resultModal);
                    document.body.style.overflow = '';
                });
            });

        } catch (error) {
            console.error('查看关键词匹配结果错误:', error);
            alert(`获取匹配结果失败: ${error.message}`);
        }
    }

    // 辅助函数：显示错误信息
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('hidden');
    }

    // 辅助函数：隐藏错误信息
    function hideError() {
        errorMessage.classList.add('hidden');
    }

    // 辅助函数：格式化JSON为HTML（带高亮）
    function formatJson(data, indent = 0) {
        const spaces = '  '.repeat(indent);
        let result = '';

        if (typeof data === 'object' && data !== null) {
            const isArray = Array.isArray(data);
            result += isArray ? '[' : '{';
            result += '<br>';

            const entries = isArray ? Array.from(data.entries()) : Object.entries(data);
            const total = entries.length;
            let index = 0;

            for (const [key, value] of entries) {
                const isLast = index === total - 1;
                const keyPart = isArray ? '' : `<span class="json-key">"${escapeHtml(key)}": </span>`;

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

    // 辅助函数：HTML转义（防止XSS攻击）
    function escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // 全局事件委托：查看文件内容
    document.addEventListener('click', (e) => {
        const viewBtn = e.target.closest('.viewFileContent');
        if (viewBtn) {
            const fileId = viewBtn.dataset.fileId;
            const fileType = viewBtn.dataset.fileType;
            const fileName = viewBtn.dataset.fileName;
            viewFileContent(fileId, fileType, fileName);
        }
    });

    // 全局事件委托：查看关键词匹配结果
    document.addEventListener('click', (e) => {
        const matchBtn = e.target.closest('.viewKeywordMatches');
        if (matchBtn) {
            const fileId = matchBtn.dataset.fileId;
            const batchId = matchBtn.dataset.batchId;
            viewKeywordMatches(batchId, fileId);
        }
    });

    // 关闭文件内容模态框
    closeModal.addEventListener('click', () => {
        fileContentModal.classList.add('hidden');
        document.body.style.overflow = '';
    });

    // 点击模态框外部关闭
    fileContentModal.addEventListener('click', (e) => {
        if (e.target === fileContentModal) {
            fileContentModal.classList.add('hidden');
            document.body.style.overflow = '';
        }
    });
});