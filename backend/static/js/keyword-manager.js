document.addEventListener('DOMContentLoaded', () => {
    const keywordSetForm = document.getElementById('keywordSetForm');
    const keywordSetsList = document.getElementById('keywordSetsList');

    // 加载关键词组列表
    loadKeywordSets();

    // 表单提交
    keywordSetForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        // 关键修复：按换行分割关键词，过滤空行
        const keywordsText = document.getElementById('keywords').value;
        const keywords = keywordsText
            .split('\n')  // 按换行分割
            .map(k => k.trim())  // 去除前后空格
            .filter(k => k !== '');  // 过滤空字符串

        const formData = {
            name: document.getElementById('setName').value,
            description: document.getElementById('setDescription').value,
            keywords: keywords  // 确保是字符串数组
        };

        try {
            const response = await fetch('/api/keywords/sets/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            // if (!response.ok) {
            //     throw new Error('创建关键词组失败');
            // }

            // 重置表单并刷新列表
            keywordSetForm.reset();
            loadKeywordSets();

            // 显示成功提示
            alert('关键词组创建成功');

        } catch (error) {
            console.error('创建关键词组错误:', error);
            alert('创建关键词组失败: ' + error.message);
        }
    });

    // 加载关键词组
    async function loadKeywordSets() {
        try {
            const response = await fetch('/api/keywords/sets/');
            if (!response.ok) {
                throw new Error('获取关键词组失败');
            }

            const sets = await response.json();
            displayKeywordSets(sets);

        } catch (error) {
            console.error('加载关键词组错误:', error);
            keywordSetsList.innerHTML = `<div class="text-red-500">加载关键词组失败: ${error.message}</div>`;
        }
    }

    // 显示关键词组
    function displayKeywordSets(sets) {
        if (sets.length === 0) {
            keywordSetsList.innerHTML = `<div class="text-gray-500 italic">暂无关键词组，请创建新的关键词组</div>`;
            return;
        }

        keywordSetsList.innerHTML = sets.map(set => `
            <div class="border rounded-lg p-4 hover:shadow-md transition-shadow">
                <div class="flex justify-between items-start">
                    <div>
                        <h3 class="font-medium text-lg text-gray-900">${set.name}</h3>
                        ${set.description ? `<p class="text-sm text-gray-600 mt-1">${set.description}</p>` : ''}
                        <p class="text-sm text-gray-500 mt-2">
                            <i class="fa fa-tag mr-1"></i> 关键词数量: ${set.keywords.length}
                        </p>
                        <p class="text-xs text-gray-400 mt-1">
                            创建时间: ${new Date(set.created_at).toLocaleString()}
                        </p>
                    </div>
                    <button class="viewKeywordsBtn px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
                            data-set-id="${set.id}"
                            data-set-name="${set.name}"
                            data-description="${set.description || ''}"
                            data-keywords='${JSON.stringify(set.keywords)}'>
                        查看关键词
                    </button>
                </div>
            </div>
        `).join('');

        // 添加查看关键词事件
        document.querySelectorAll('.viewKeywordsBtn').forEach(btn => {
            btn.addEventListener('click', function () {
                const setName = this.dataset.setName;
                const description = this.dataset.description;
                const keywords = JSON.parse(this.dataset.keywords);

                // 填充模态框内容
                document.getElementById('modalSetTitle').textContent = `关键词组: ${setName}`;
                document.getElementById('modalSetDescription').textContent = description || '无描述';
                document.getElementById('keywordCount').textContent = `(${keywords.length}个关键词)`;

                // 生成关键词列表（按列展示）
                const keywordsList = document.getElementById('modalKeywordsList');
                keywordsList.innerHTML = keywords.map(keyword => `
                <div class="px-3 py-2 bg-gray-50 rounded border flex items-center">
                    <span class="text-sm text-gray-800">${keyword}</span>
                </div>
            `).join('');

                // 显示模态框
                document.getElementById('keywordSetModal').classList.remove('hidden');
                document.body.style.overflow = 'hidden';
            });
        });
    }

    // 绑定模态框关闭事件
    document.getElementById('closeSetModal').addEventListener('click', closeKeywordModal);
    document.getElementById('closeSetModalBtn').addEventListener('click', closeKeywordModal);

    // 点击模态框外部关闭
    document.getElementById('keywordSetModal').addEventListener('click', (e) => {
        if (e.target === document.getElementById('keywordSetModal')) {
            closeKeywordModal();
        }
    });

    // 关闭模态框函数
    function closeKeywordModal() {
        document.getElementById('keywordSetModal').classList.add('hidden');
        document.body.style.overflow = '';
    }
});
