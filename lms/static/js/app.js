// LinguaVoice App JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Theme toggle
    const themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
        themeBtn.addEventListener('click', function() {
            document.body.classList.toggle('light-mode');
            const isLight = document.body.classList.contains('light-mode');
            themeBtn.innerHTML = isLight ? '<i class="fa-solid fa-moon"></i>' : '<i class="fa-solid fa-sun"></i>';
            localStorage.setItem('theme', isLight ? 'light' : 'dark');
        });

        // Load saved theme
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'light') {
            document.body.classList.add('light-mode');
            themeBtn.innerHTML = '<i class="fa-solid fa-moon"></i>';
        }
    }

    // Toast notifications
    window.showToast = function(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 5000);
    };

    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const inputs = form.querySelectorAll('input[required]');
            let isValid = true;

            inputs.forEach(input => {
                if (!input.value.trim()) {
                    input.classList.add('error');
                    isValid = false;
                } else {
                    input.classList.remove('error');
                }
            });

            if (!isValid) {
                e.preventDefault();
                showToast('Please fill in all required fields', 'error');
            }
        });
    });

    // Tab switching
    window.switchTab = function(tabId) {
        const tabs = document.querySelectorAll('.tab-btn');
        const sections = document.querySelectorAll('.vocab-section');

        tabs.forEach(tab => tab.classList.remove('active'));
        sections.forEach(section => section.classList.remove('active'));

        document.querySelector(`[onclick="switchTab('${tabId}')"]`).classList.add('active');
        document.getElementById(tabId).classList.add('active');
    };

    // Language selection
    window.setLanguage = function(lang) {
        const buttons = document.querySelectorAll('.lang-btn');
        buttons.forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');

        fetch('/api/set_language', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ language: lang })
        }).then(() => {
            showToast(`Language set to ${lang.toUpperCase()}`, 'success');
        });
    };

    // Transcription controls
    let isRecording = false;
    window.toggleRecording = function() {
        const micBtn = document.getElementById('mic-btn');
        const micIcon = document.getElementById('mic-icon');
        const micText = document.getElementById('mic-text');

        if (!isRecording) {
            // Start recording
            fetch('/api/start_recording', { method: 'POST' })
                .then(() => {
                    isRecording = true;
                    micBtn.classList.add('recording');
                    micIcon.innerHTML = '<i class="fa-solid fa-stop"></i>';
                    micText.textContent = 'Stop Recording';
                    showToast('Recording started', 'success');
                });
        } else {
            // Stop recording
            isRecording = false;
            micBtn.classList.remove('recording');
            micIcon.innerHTML = '<i class="fa-solid fa-microphone"></i>';
            micText.textContent = 'Start Recording';
            showToast('Recording stopped', 'info');
        }
    };

    // Save transcript
    window.saveTranscript = function() {
        const text = document.getElementById('transcript-text').textContent;
        if (!text.trim()) {
            showToast('No transcript to save', 'warning');
            return;
        }

        fetch('/api/save_transcript', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text, language: 'en' }) // TODO: get current language
        }).then(() => {
            showToast('Transcript saved', 'success');
        });
    };

    // Clear transcript
    window.clearTranscript = function() {
        document.getElementById('transcript-text').textContent = 'Click "Start Recording" to begin transcription...';
        showToast('Transcript cleared', 'info');
    };

    // Load dashboard data
    if (document.getElementById('total-xp')) {
        fetch('/api/stats')
            .then(res => res.json())
            .then(data => {
                const stats = data.stats || {};
                document.getElementById('total-xp').textContent = (stats.total_xp || 1240).toLocaleString();
                document.getElementById('streak').textContent = stats.current_streak || 12;
            });
    }

    // Load vocabulary
    if (document.getElementById('my-vocab-grid')) {
        fetch('/api/get_vocabulary_bank_full')
            .then(res => res.json())
            .then(words => {
                renderVocabulary(words);
            });
    }

    function renderVocabulary(words) {
        const grid = document.getElementById('my-vocab-grid');
        if (!grid) return;

        grid.innerHTML = words.map(word => `
            <div class="word-card">
                <div class="word-header">
                    <div class="word-title">${word.word}</div>
                    <div class="word-lang">${word.language}</div>
                </div>
                <div class="word-meaning">${word.meaning || 'Learning in progress...'}</div>
                <div class="word-footer">
                    Added ${new Date(word.first_seen * 1000).toLocaleDateString()}
                </div>
            </div>
        `).join('');
    }

    // Quiz functionality
    window.selectQuizOption = function(option) {
        const options = document.querySelectorAll('.quiz-option');
        options.forEach(opt => opt.classList.remove('selected'));
        option.classList.add('selected');
    };

    // Chat functionality for AI Tutor
    window.sendMessage = function() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();
        if (!message) return;

        // Add user message
        addChatMessage(message, 'user');
        input.value = '';

        // Send to API
        fetch('/api/ai_tutor_chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message, base_language: 'en', target_language: 'es' })
        })
        .then(res => res.json())
        .then(data => {
            addChatMessage(data.reply, 'bot');
        });
    };

    function addChatMessage(text, sender) {
        const chat = document.querySelector('.tutor-chat');
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message message-${sender}`;
        messageDiv.innerHTML = `<div class="message-bubble">${text}</div>`;
        chat.appendChild(messageDiv);
        chat.scrollTop = chat.scrollHeight;
    }

    // Enter key for chat
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }

    // Live transcript updates
    if (document.getElementById('transcript-text')) {
        setInterval(() => {
            fetch('/api/get_live_transcripts')
                .then(res => res.json())
                .then(data => {
                    if (data.transcripts.length > 0) {
                        const latest = data.transcripts[data.transcripts.length - 1];
                        document.getElementById('transcript-text').textContent = latest.text;
                    }
                });
        }, 1000);
    }
});