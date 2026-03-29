// toast-messages.js
// Django消息框架的Toast弹窗组件

class ToastMessages {
    constructor() {
        this.toastContainer = null;
        this.init();
    }
    
    // 初始化
    init() {
        this.createToastContainer();
        this.autoShowMessages();
    }
    
    // 创建Toast容器
    createToastContainer() {
        // 如果已存在，直接使用
        this.toastContainer = document.getElementById('message-toast');
        if (this.toastContainer) {
            return;
        }
        
        // 创建新的Toast容器
        this.toastContainer = document.createElement('div');
        this.toastContainer.id = 'message-toast';
        this.toastContainer.className = 'toast-container';
        
        // 添加样式
        const style = document.createElement('style');
        style.textContent = `
            .toast-container {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1055;
                min-width: 300px;
                max-width: 500px;
            }
            
            .toast {
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                border-radius: 8px;
                overflow: hidden;
                margin-bottom: 10px;
            }
            
            .toast-header {
                padding: 10px 15px;
                border-bottom: 1px solid rgba(0,0,0,0.1);
            }
            
            .toast-body {
                padding: 15px;
                background-color: white;
            }
            
            .bg-warning.text-dark .btn-close {
                filter: brightness(0) invert(0);
            }
        `;
        
        document.head.appendChild(style);
        document.body.appendChild(this.toastContainer);
    }
    
    // 自动显示Django消息
    autoShowMessages() {
        // 检查是否有Django消息
        const messages = window.djangoMessages || [];
        messages.forEach(message => {
            this.show(message.type, message.message);
        });
    }
    
    // 显示Toast
    show(type, message, options = {}) {
        const config = {
            title: options.title || this.getTitle(type),
            duration: options.duration || 5000,
            icon: options.icon || this.getIcon(type),
            position: options.position || 'top-right',
            ...options
        };
        
        const toastId = 'toast-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        const bgClass = this.getBgClass(type);
        const textClass = this.getTextClass(type);
        
        // 创建Toast HTML
        const toastHtml = `
            <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="${config.duration}">
                <div class="toast-header ${bgClass} ${textClass}">
                    <i class="bi ${config.icon} me-2"></i>
                    <strong class="me-auto">${config.title}</strong>
                    <button type="button" class="btn-close ${textClass.includes('text-white') ? 'btn-close-white' : ''}" 
                            data-bs-dismiss="toast" aria-label="关闭"></button>
                </div>
                <div class="toast-body">
                    ${this.escapeHtml(message)}
                </div>
            </div>
        `;
        
        this.toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        const toastElement = document.getElementById(toastId);
        
        // 初始化Bootstrap Toast
        const toast = new bootstrap.Toast(toastElement, {
            autohide: true,
            delay: config.duration
        });
        
        toast.show();
        
        // Toast隐藏后移除元素
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
        
        return toast;
    }
    
    // 成功消息
    success(message, options = {}) {
        return this.show('success', message, options);
    }
    
    // 错误消息
    error(message, options = {}) {
        return this.show('error', message, options);
    }
    
    // 警告消息
    warning(message, options = {}) {
        return this.show('warning', message, options);
    }
    
    // 信息消息
    info(message, options = {}) {
        return this.show('info', message, options);
    }
    
    // 清空所有Toast
    clear() {
        this.toastContainer.innerHTML = '';
    }
    
    // 获取背景颜色类
    getBgClass(type) {
        switch(type) {
            case 'success': return 'bg-success';
            case 'error': return 'bg-danger';
            case 'warning': return 'bg-warning';
            case 'info': return 'bg-primary';
            default: return 'bg-info';
        }
    }
    
    // 获取文本颜色类
    getTextClass(type) {
        switch(type) {
            case 'warning': return 'text-dark';
            default: return 'text-white';
        }
    }
    
    // 获取图标
    getIcon(type) {
        switch(type) {
            case 'success': return 'bi-check-circle-fill';
            case 'error': return 'bi-x-circle-fill';
            case 'warning': return 'bi-exclamation-triangle-fill';
            case 'info': return 'bi-info-circle-fill';
            default: return 'bi-chat-fill';
        }
    }
    
    // 获取标题
    getTitle(type) {
        switch(type) {
            case 'success': return '成功';
            case 'error': return '错误';
            case 'warning': return '警告';
            case 'info': return '提示';
            default: return '消息';
        }
    }
    
    // 转义HTML，防止XSS
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // AJAX错误处理
    handleAjaxError(xhr, status, error) {
        let message = '请求失败，请稍后重试';
        
        if (xhr.responseJSON && xhr.responseJSON.message) {
            message = xhr.responseJSON.message;
        } else if (xhr.status === 0) {
            message = '网络连接失败，请检查网络';
        } else if (xhr.status === 404) {
            message = '请求的资源不存在';
        } else if (xhr.status === 500) {
            message = '服务器内部错误';
        } else if (error) {
            message = error;
        }
        
        this.error(message);
    }
}

// 创建全局实例
let toastMessages = null;

// 初始化函数
function initToastMessages() {
    if (!toastMessages && typeof bootstrap !== 'undefined') {
        toastMessages = new ToastMessages();
    }
    return toastMessages;
}

// 全局便捷函数
window.showToast = function(type, message, options) {
    const toast = initToastMessages();
    if (toast) {
        return toast.show(type, message, options);
    }
};

window.showSuccess = function(message, options) {
    return showToast('success', message, options);
};

window.showError = function(message, options) {
    return showToast('error', message, options);
};

window.showWarning = function(message, options) {
    return showToast('warning', message, options);
};

window.showInfo = function(message, options) {
    return showToast('info', message, options);
};

// 处理AJAX错误
window.handleAjaxError = function(xhr, status, error) {
    const toast = initToastMessages();
    if (toast) {
        toast.handleAjaxError(xhr, status, error);
    }
};

// DOM加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 确保Bootstrap已加载
    if (typeof bootstrap !== 'undefined') {
        initToastMessages();
    }
    
    // 为所有带有data-toast属性的元素添加点击事件
    document.querySelectorAll('[data-toast-type]').forEach(element => {
        element.addEventListener('click', function(e) {
            e.preventDefault();
            const type = this.dataset.toastType;
            const message = this.dataset.toastMessage || this.title || this.textContent;
            
            if (message && showToast) {
                showToast(type, message);
            }
    });
    });
});