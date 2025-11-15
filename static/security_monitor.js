/**
 * グローバルセキュリティ監視システム
 * すべてのページで使用される共通セキュリティ機能
 */

(function() {
    'use strict';
    
    let securityViolations = {
        f12: 0,
        contextmenu: 0,
        refresh: 0,
        lastReset: Date.now()
    };

    const MAX_F12 = 1;           // F12は1回でアウト
    const MAX_CONTEXTMENU = 2;   // 右クリックは2回でアウト
    const MAX_REFRESH = 3;       // 更新は3回でアウト
    const RESET_INTERVAL = 60000; // 1分でリセット

    // 1分ごとにカウンターをリセット
    setInterval(function() {
        const now = Date.now();
        if (now - securityViolations.lastReset > RESET_INTERVAL) {
            securityViolations = {
                f12: 0,
                contextmenu: 0,
                refresh: 0,
                lastReset: now
            };
        }
    }, 1000);

    // 違反をサーバーに報告
    async function reportViolation(action) {
        try {
            const response = await fetch('/api/security/log', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ action: action })
            });
            
            const data = await response.json();
            if (data.redirect && data.url) {
                window.location.href = data.url;
            }
        } catch (error) {
            // エラーは無視
        }
    }

    // ウイルス画面へリダイレクト
    function redirectToVirus() {
        window.location.href = '/virus';
    }

    // F12キー無効化（1回でアウト）
    document.addEventListener('keydown', function(e) {
        if (e.key === 'F12' || (e.ctrlKey && e.shiftKey && e.key === 'I') || 
            (e.ctrlKey && e.shiftKey && e.key === 'J') || (e.ctrlKey && e.key === 'u')) {
            e.preventDefault();
            e.stopPropagation();
            
            securityViolations.f12++;
            reportViolation('f12');
            
            if (securityViolations.f12 >= MAX_F12) {
                redirectToVirus();
            }
            
            return false;
        }
        
        // 更新ボタン監視（3回でアウト）
        if ((e.ctrlKey && e.key === 'r') || e.key === 'F5') {
            securityViolations.refresh++;
            reportViolation('refresh');
            
            if (securityViolations.refresh >= MAX_REFRESH) {
                e.preventDefault();
                e.stopPropagation();
                redirectToVirus();
                return false;
            }
        }
    }, true);

    // 右クリック無効化（2回でアウト）
    document.addEventListener('contextmenu', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        securityViolations.contextmenu++;
        reportViolation('contextmenu');
        
        if (securityViolations.contextmenu >= MAX_CONTEXTMENU) {
            redirectToVirus();
        }
        
        return false;
    }, true);

    // ページ離脱時の警告（ウイルス画面以外）
    if (!window.location.pathname.includes('/virus')) {
        window.addEventListener('beforeunload', function(e) {
            if (securityViolations.f12 > 0 || securityViolations.contextmenu > 0) {
                e.preventDefault();
                e.returnValue = '';
            }
        });
    }
})();

