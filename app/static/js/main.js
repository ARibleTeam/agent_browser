// Список доступных моделей (будет загружен с сервера)
let MODELS = [];

let currentModel = null;
let currentConfig = {};
let modelSchema = {};
let requiredParams = [];
let isConfigured = false;
let isVerified = false;  // Флаг проверки модели
let isAgentRunning = false;  // Флаг выполнения агента
let currentReader = null;  // Текущий SSE reader для возможности отмены

// Системный промпт: значение по умолчанию и текущее для выбранной модели
let systemPromptDefault = 'Всегда используй поисковую систему Яндекс.';

// Переключение layout: только чат (без боковых колонок)
function enterTaskLayout() {
    document.querySelector('.container')?.classList.add('layout-task-running');
}
function exitTaskLayout() {
    document.querySelector('.container')?.classList.remove('layout-task-running');
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    loadAvailableModels();
    initChatInterface();
});

// Загрузка доступных моделей
async function loadAvailableModels() {
    try {
        const response = await fetch('/api/models');
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                MODELS = data.models || [];
                initModelList();
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки моделей:', error);
    }
}

// Инициализация списка моделей
function initModelList() {
    const modelList = document.getElementById('modelList');
    modelList.innerHTML = '';
    
    MODELS.forEach(model => {
        const li = document.createElement('li');
        const icon = document.createElement('span');
        icon.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>';
        icon.style.display = 'flex';
        icon.style.alignItems = 'center';
        const text = document.createTextNode(model);
        li.appendChild(icon);
        li.appendChild(text);
        li.onclick = () => selectModel(model);
        modelList.appendChild(li);
    });
}

// Инициализация интерфейса чата
function initChatInterface() {
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendButton');
    
    // Отправка по Enter
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!isAgentRunning) {
                sendMessage();
            }
        }
    });
}

// Выбор модели
async function selectModel(modelName) {
    // Если переключаемся на другую модель, остановить текущий процесс
    if (isAgentRunning && currentModel !== modelName) {
        await stopAgent();
    }
    
    currentModel = modelName;
    
    // Очистка чата при переключении модели
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.innerHTML = `
            <div class="welcome-card" id="welcomeMessage">
                <div class="welcome-icon">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                    </svg>
                </div>
                <h3>Готов к работе</h3>
                <p>Выберите модель слева и настройте её справа для начала работы</p>
            </div>
        `;
    }
    
    // Обновление заголовка чата
    const chatHeader = document.getElementById('currentModelTitle');
    if (chatHeader) {
        chatHeader.textContent = modelName;
    }
    
    // Обновление активного элемента в списке
    document.querySelectorAll('#modelList li').forEach(li => {
        li.classList.remove('active');
        // Сравниваем текст без иконки
        const liText = Array.from(li.childNodes)
            .filter(node => node.nodeType === Node.TEXT_NODE)
            .map(node => node.textContent.trim())
            .join('');
        if (liText === modelName) {
            li.classList.add('active');
        }
    });
    
    // Показать сообщение о загрузке
    const container = document.getElementById('settingsContainer');
    container.innerHTML = `
        <div class="settings-card light">
            <div class="status-message info">Загрузка настроек...</div>
        </div>
    `;
    
    // Загрузка схемы и конфигурации модели
    await loadModelSchema(modelName);
    await loadModelConfig(modelName);
    
    // Генерация формы настроек
    generateSettingsForm(modelName);
    
    // Проверка конфигурации (с учётом флага проверки)
    // Вызываем после генерации формы, чтобы конфигурация точно загружена
    // Используем setTimeout, чтобы дать время DOM обновиться
    setTimeout(() => {
        checkConfiguration();
    }, 50);
}

// Загрузка схемы модели
async function loadModelSchema(modelName) {
    try {
        const response = await fetch(`/api/models/${modelName}/schema`);
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                modelSchema = data.schema || {};
                requiredParams = data.required || [];
            } else {
                modelSchema = {};
                requiredParams = [];
            }
        } else {
            modelSchema = {};
            requiredParams = [];
        }
    } catch (error) {
        modelSchema = {};
        requiredParams = [];
    }
}

// Загрузка конфигурации модели
async function loadModelConfig(modelName) {
    try {
        const response = await fetch(`/api/models/${modelName}/config`);
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                currentConfig = data.config || {};
                isVerified = data.verified || false;  // Получить флаг проверки
                // Обновить дефолтный системный промпт, если сервер его вернул
                if (data.system_prompt_default) {
                    systemPromptDefault = data.system_prompt_default;
                }
                // Если модель проверена, считаем её настроенной
                if (isVerified) {
                    isConfigured = true;
                }
            } else {
                currentConfig = {};
                isVerified = false;
                isConfigured = false;
            }
        } else {
            currentConfig = {};
            isVerified = false;
            isConfigured = false;
        }
    } catch (error) {
        console.error('Ошибка загрузки конфигурации:', error);
        currentConfig = {};
        isVerified = false;
        isConfigured = false;
    }
}

// Генерация формы настроек
function generateSettingsForm(modelName) {
    const container = document.getElementById('settingsContainer');
    
    // Проверка наличия схемы
    if (!modelSchema || Object.keys(modelSchema).length === 0) {
        container.innerHTML = `
            <div class="settings-card light">
                <div class="status-message info">Загрузка схемы модели...</div>
            </div>
        `;
        return;
    }
    
    // Группировка параметров в карточки (как блоки APY в референсе)
    let html = '';
    
    // Генерация полей для каждого параметра схемы
    let hasFields = false;
    const params = [];
    
    for (const [paramName, paramInfo] of Object.entries(modelSchema)) {
        // Пропустить внутренние параметры
        if (paramName.startsWith('_')) {
            continue;
        }
        
        hasFields = true;
        params.push({ name: paramName, info: paramInfo });
    }
    
    if (!hasFields) {
        container.innerHTML = `
            <div class="settings-card light">
                <div class="status-message info">Нет доступных параметров для настройки</div>
            </div>
        `;
        return;
    }
    
    // Создаем карточку для каждого параметра (или группируем в одну карточку)
    // Используем темную карточку в стиле блоков APY из референса
    html += '<div class="settings-card">';
    html += `<div class="settings-title">${modelName}</div>`;
    html += '<div class="settings-form">';

    const currentSystemPrompt = currentConfig['system_prompt'] || systemPromptDefault || '';
    html += '<div class="form-group">';
    html += '<label>system_prompt</label>';
    html += '<small class="param-description">Системный промпт агента. Он всегда добавляется к задаче перед запуском. Можно изменить или сбросить к значению по умолчанию.</small>';
    html += `<textarea id="param_system_prompt" rows="3" placeholder="${systemPromptDefault}" oninput="onConfigChanged()">${currentSystemPrompt}</textarea>`;
    html += '<div class="button-group">';
    html += '<button type="button" class="btn btn-secondary" onclick="resetSystemPrompt()">Сбросить системный промпт</button>';
    html += '</div>';
    html += '</div>';
    
    params.forEach(({ name: paramName, info: paramInfo }) => {
        const isRequired = requiredParams.includes(paramName);
        let currentValue = currentConfig[paramName];
        if (currentValue === undefined || currentValue === null) {
            currentValue = '';
        }
        const formType = paramInfo.form_type || 'text';
        
        html += '<div class="form-group">';
        html += `<label>${paramName}${isRequired ? ' <span class="required">*</span>' : ''}</label>`;
        
        // Добавить описание параметра, если есть
        if (paramInfo.description) {
            html += `<small class="param-description">${paramInfo.description}</small>`;
        }
        
        // Добавить обработчик изменения для отслеживания изменений
        const onChangeHandler = `oninput="onConfigChanged()"`;
        
        if (formType === 'checkbox') {
            html += `<input type="checkbox" id="param_${paramName}" ${currentValue ? 'checked' : ''} onchange="onConfigChanged()">`;
        } else if (formType === 'number') {
            html += `<input type="number" id="param_${paramName}" value="${currentValue}" step="any" ${onChangeHandler}>`;
        } else {
            const placeholder = paramInfo.default !== null && paramInfo.default !== undefined ? String(paramInfo.default) : '';
            html += `<input type="text" id="param_${paramName}" value="${currentValue}" placeholder="${placeholder}" ${onChangeHandler}>`;
        }
        
        html += '</div>';
    });

    html += '<button class="btn-action" onclick="saveAndTestConfig()">Сохранить и проверить</button>';
    html += '<div id="statusMessage"></div>';
    html += '</div>';
    html += '</div>';
    
    container.innerHTML = html;
}

// Сохранение и тестирование конфигурации
async function saveAndTestConfig() {
    const statusDiv = document.getElementById('statusMessage');
    statusDiv.innerHTML = '<div class="status-message info">Проверка подключения...</div>';
    
    // Сбор данных формы
    const config = {};
    for (const paramName of Object.keys(modelSchema)) {
        // Пропустить внутренние параметры
        if (paramName.startsWith('_')) {
            continue;
        }
        
        const input = document.getElementById(`param_${paramName}`);
        if (input) {
            if (input.type === 'checkbox') {
                config[paramName] = input.checked;
            } else if (input.type === 'number') {
                const value = input.value;
                if (value === '') {
                    // Не добавлять пустые числовые значения
                    continue;
                }
                config[paramName] = value.includes('.') ? parseFloat(value) : parseInt(value);
            } else {
                const value = input.value.trim();
                if (value === '') {
                    // Не добавлять пустые строковые значения
                    continue;
                }
                config[paramName] = value;
            }
        }
    }

    // Системный промпт сохраняем отдельно: пустое значение означает "использовать дефолт"
    const systemPromptEl = document.getElementById('param_system_prompt');
    if (systemPromptEl) {
        const value = systemPromptEl.value.trim();
        if (value !== '') {
            config['system_prompt'] = value;
        }
    }

    // Валидация обязательных полей
    const missing = requiredParams.filter(param => !config[param] || config[param] === '');
    if (missing.length > 0) {
        statusDiv.innerHTML = `<div class="status-message error">Заполните обязательные поля: ${missing.join(', ')}</div>`;
        return;
    }
    
    // Проверка, изменилась ли конфигурация (сравниваем только значимые параметры, без служебных)
    const currentConfigClean = Object.fromEntries(
        Object.entries(currentConfig).filter(([k]) => !k.startsWith('_'))
    );
    const configChanged = JSON.stringify(config) !== JSON.stringify(currentConfigClean);
    
    // Если конфигурация не изменилась и модель уже проверена - не проверять снова
    if (!configChanged && isVerified) {
        statusDiv.innerHTML = `<div class="status-message success">Настройки не изменились. Модель уже проверена и готова к работе.</div>`;
        return;
    }
    
    // Тестирование подключения
    try {
        const response = await fetch(`/api/models/${currentModel}/test`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        const data = await response.json();
        
        if (data.success) {
            statusDiv.innerHTML = `<div class="status-message success">${data.message || 'Подключение успешно установлено!'}</div>`;
            currentConfig = config;
            isConfigured = true;
            isVerified = true;  // Модель проверена
            checkConfiguration();
        } else {
            statusDiv.innerHTML = `<div class="status-message error">Ошибка: ${data.error || 'Неизвестная ошибка'}</div>`;
            isConfigured = false;
            isVerified = false;  // Сбросить флаг при ошибке
        }
    } catch (error) {
        statusDiv.innerHTML = `<div class="status-message error">Ошибка: ${error.message}</div>`;
        isConfigured = false;
        isVerified = false;  // Сбросить флаг при ошибке
    }
}

// Обработчик изменения конфигурации (глобальная функция для вызова из HTML)
window.onConfigChanged = function() {
    // При изменении параметров сбрасываем флаг проверки
    isVerified = false;
    isConfigured = false;
    checkConfiguration();
};

// Сброс системного промпта к значению по умолчанию
window.resetSystemPrompt = function() {
    const el = document.getElementById('param_system_prompt');
    if (!el) return;
    el.value = systemPromptDefault || '';
    window.onConfigChanged();
};

// Проверка конфигурации и обновление интерфейса
function checkConfiguration() {
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendButton');
    const chatMessages = document.getElementById('chatMessages');
    const welcomeMessage = document.getElementById('welcomeMessage');
    
    // Проверка наличия всех обязательных параметров
    const allRequiredFilled = requiredParams.every(param => {
        const value = currentConfig[param];
        return value !== undefined && value !== null && value !== '';
    });

    // Если модель была проверена и все обязательные поля заполнены - разблокировать чат
    if (allRequiredFilled && isVerified) {
        // Конфигурация готова и проверена
        chatInput.disabled = false;
        sendButton.disabled = false;
        if (welcomeMessage) {
            welcomeMessage.querySelector('h3').textContent = 'Готов к работе';
            welcomeMessage.querySelector('p').textContent = 'Модель настроена и проверена. Введите задачу для агента.';
        }
    } else if (allRequiredFilled && isConfigured) {
        // Конфигурация готова, но не проверена (для обратной совместимости)
        chatInput.disabled = false;
        sendButton.disabled = false;
        if (welcomeMessage) {
            welcomeMessage.querySelector('h3').textContent = 'Готов к работе';
            welcomeMessage.querySelector('p').textContent = 'Модель настроена. Введите задачу для агента.';
        }
    } else {
        // Конфигурация не готова
        chatInput.disabled = true;
        sendButton.disabled = true;
        if (welcomeMessage) {
            const missing = requiredParams.filter(param => !currentConfig[param] || currentConfig[param] === '');
            if (missing.length > 0) {
                welcomeMessage.querySelector('h3').textContent = 'Требуется настройка';
                welcomeMessage.querySelector('p').textContent = `Заполните обязательные параметры: ${missing.join(', ')}`;
            } else if (!isVerified && !isConfigured) {
                welcomeMessage.querySelector('h3').textContent = 'Требуется проверка';
                welcomeMessage.querySelector('p').textContent = 'Нажмите "Сохранить и проверить" для активации модели';
            } else {
                welcomeMessage.querySelector('h3').textContent = 'Требуется настройка';
                welcomeMessage.querySelector('p').textContent = 'Проверьте настройки модели';
            }
        }
    }
}

// Остановка агента
async function stopAgent() {
    if (!isAgentRunning) {
        return;
    }
    
    try {
        // Отправить запрос на остановку
        const response = await fetch('/api/chat/stop', {
            method: 'POST'
        });
        
        // Прервать чтение SSE потока
        if (currentReader) {
            try {
                await currentReader.cancel();
            } catch (e) {
                console.error('Ошибка при отмене чтения:', e);
            }
        }
        
        exitTaskLayout();
        updateSendButton(false);
        isAgentRunning = false;
        currentReader = null;

        addMessageToChat('ai', '⏹️ Выполнение остановлено пользователем');
    } catch (error) {
        console.error('Ошибка остановки агента:', error);
    }
}

// Обновление кнопки отправки/остановки
function updateSendButton(running) {
    const sendButton = document.getElementById('sendButton');
    const chatInput = document.getElementById('chatInput');
    
    if (running) {
        sendButton.innerHTML = '<span class="spinner"></span>';
        sendButton.onclick = stopAgent;
        sendButton.className = 'btn-send btn-stop';
        chatInput.disabled = true;
    } else {
        sendButton.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>';
        sendButton.onclick = sendMessage;
        sendButton.className = 'btn-send';
        chatInput.disabled = false;
    }
}

// Отправка сообщения
async function sendMessage() {
    const chatInput = document.getElementById('chatInput');
    const message = chatInput.value.trim();
    
    if (!message || !currentModel || isAgentRunning) {
        return;
    }
    
    // Добавить сообщение пользователя в чат
    addMessageToChat('user', message);
    chatInput.value = '';
    
    // Обновить UI: кнопка остановки и полноэкранный режим (чат + браузер)
    isAgentRunning = true;
    updateSendButton(true);
    enterTaskLayout();

    // Отправить запрос через SSE
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: currentModel,
                message: message
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Читать SSE поток
        const reader = response.body.getReader();
        currentReader = reader;
        const decoder = new TextDecoder();
        let buffer = '';
        
        // Переменные для группировки логов по типам
        let currentStepMessage = null;
        let currentEvalMessage = null;
        let currentMemoryMessage = null;
        let currentGoalMessage = null;
        let currentActionMessage = null;
        let currentToolMessage = null;
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // Оставить неполную строку в буфере
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (!data || typeof data !== 'object') continue;

                        if (data.type === 'result' && data.success !== undefined) {
                            // Финальный результат — возврат к обычному виду
                            isAgentRunning = false;
                            updateSendButton(false);
                            currentReader = null;
                            exitTaskLayout();

                            if (data.success) {
                                // Успешное завершение - показываем с зеленой галочкой
                                const successText = `✅ ${data.response || data.message || 'Задача выполнена'}`;
                                addMessageToChat('ai', successText, null, 'log-result-success');
                            } else {
                                const errorText = `❌ Ошибка: ${data.error || data.message || 'Неизвестная ошибка'}`;
                                addMessageToChat('ai', errorText, null, 'log-result-error');
                            }
                            return; // Завершить чтение
                        }
                        
                        // Обработка разных типов логов как отдельных сообщений
                        const chatMessages = document.getElementById('chatMessages');
                        const msgText = (data.message != null) ? String(data.message) : '';

                        if (data.type === 'step') {
                            // Новый шаг - новое сообщение
                            currentStepMessage = addMessageToChat('ai', msgText, null, 'log-step');
                            currentEvalMessage = null;
                            currentMemoryMessage = null;
                            currentGoalMessage = null;
                        } else if (data.type === 'eval') {
                            if (currentStepMessage) {
                                const evalDiv = document.createElement('div');
                                evalDiv.className = 'log-eval' + (msgText.includes('⚠️') ? ' log-eval-warning' : '');
                                evalDiv.textContent = msgText;
                                currentStepMessage.querySelector('.message-content').appendChild(evalDiv);
                            } else {
                                currentEvalMessage = addMessageToChat('ai', msgText, null, 'log-eval');
                            }
                        } else if (data.type === 'memory') {
                            currentMemoryMessage = addMessageToChat('ai', msgText, null, 'log-memory');
                        } else if (data.type === 'goal') {
                            currentGoalMessage = addMessageToChat('ai', msgText, null, 'log-goal');
                        } else if (data.type === 'judge') {
                            addMessageToChat('ai', msgText, null, 'log-judge');
                        } else if (data.type === 'action') {
                            currentActionMessage = addMessageToChat('ai', msgText, null, 'log-action');
                        } else if (data.type === 'tool') {
                            if (currentActionMessage) {
                                const toolDiv = document.createElement('div');
                                toolDiv.className = 'log-tool';
                                toolDiv.textContent = msgText;
                                currentActionMessage.querySelector('.message-content').appendChild(toolDiv);
                            } else {
                                currentToolMessage = addMessageToChat('ai', msgText, null, 'log-tool');
                            }
                        } else if (data.type === 'error') {
                            addMessageToChat('ai', msgText, null, 'log-error');
                        } else if (data.type === 'log') {
                            addMessageToChat('ai', msgText, null, 'log-line');
                        }
                        
                        // Прокрутка вниз
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    } catch (e) {
                        console.error('Ошибка парсинга SSE:', e);
                    }
                }
            }
        }
        
        // Если поток завершился без результата
        isAgentRunning = false;
        updateSendButton(false);
        currentReader = null;
        exitTaskLayout();

    } catch (error) {
        isAgentRunning = false;
        updateSendButton(false);
        currentReader = null;
        exitTaskLayout();

        // Обработка сетевых ошибок
        let errorText = '❌ Ошибка подключения';
        if (error.message) {
            errorText += `: ${error.message}`;
        }
        addMessageToChat('ai', errorText, null, 'log-result-error');
        console.error('Ошибка отправки сообщения:', error);
    }
}

// Добавление сообщения в чат
function addMessageToChat(type, text, messageId = null, additionalClass = '') {
    const chatMessages = document.getElementById('chatMessages');
    const welcomeMessage = document.getElementById('welcomeMessage');
    
    if (welcomeMessage) {
        welcomeMessage.remove();
    }
    
    if (!messageId) {
        messageId = 'msg-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    }
    
    // Добавляем log-result-success ко всем AI сообщениям (кроме ошибок)
    if (type === 'ai') {
        if (additionalClass && !additionalClass.includes('log-result-error')) {
            // Если есть дополнительный класс и это не ошибка, добавляем log-result-success
            if (!additionalClass.includes('log-result-success')) {
                additionalClass += ' log-result-success';
            }
        } else if (!additionalClass) {
            // Если нет дополнительного класса, добавляем log-result-success
            additionalClass = 'log-result-success';
        }
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.id = messageId;
    messageDiv.className = `message ${type} ${additionalClass}`.trim();
    
    // Создать контейнер для содержимого
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = text;
    messageDiv.appendChild(contentDiv);
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageDiv;
}

// Удаление сообщения из чата
function removeMessage(messageId) {
    const message = document.getElementById(messageId);
    if (message) {
        message.remove();
    }
}

// Функции для потока скриншотов и CDP удалены, так как браузерный просмотр больше не используется.
