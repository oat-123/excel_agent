// Patch for enhancing Thought Stream: increase history, add insert buttons, and require selected rows when appending
(function(){
    // Enhance addStreamLine by wrapping existing one if present
    const orig = window.addStreamLine;
    function patchedAddStreamLine(text, type='info', save=true){
        const container = document.getElementById('data-stream');
        if (!container) return;
        const line = document.createElement('div');
        let color = 'rgba(0, 242, 255, 0.7)';
        let prefix = `[${new Date().toLocaleTimeString()}] `;
        if (type === 'bot') { color = '#ffcc00'; prefix = 'J.A.R.V.I.S >> '; line.style.fontWeight = 'bold'; }
        else if (type === 'error') color = '#ff4d4d';
        line.style.cssText = `padding: 6px 8px; border-bottom: 1px solid rgba(0,242,255,0.05); font-size: 11px; color: ${color}; display:flex; justify-content:space-between; gap:8px; align-items:center;`;

        const msg = document.createElement('span');
        msg.style.flex = '1';
        msg.textContent = `${prefix}${text}`;
        line.appendChild(msg);

        const insertBtn = document.createElement('button');
        insertBtn.className = 'insert-log-btn';
        insertBtn.title = 'Insert into input';
        insertBtn.innerHTML = '<i class="fas fa-angle-right"></i>';
        insertBtn.onclick = (e) => { e.stopPropagation(); const input = document.getElementById('neural-cmd') || document.getElementById('neural-input'); if (input){ input.value = text; input.focus(); } };
        line.appendChild(insertBtn);

        container.prepend(line);
        // Keep larger history
        if (container.children.length > 500) container.removeChild(container.lastChild);

        if (save) {
            try{
                const logs = JSON.parse(localStorage.getItem('jarvis_neural_logs') || '[]');
                logs.unshift({ text, type, time: new Date().toLocaleTimeString() });
                localStorage.setItem('jarvis_neural_logs', JSON.stringify(logs.slice(0, 500)));
            }catch(e){}
        }
    }

    // Replace or set
    window.addStreamLine = patchedAddStreamLine;

    // Load persistent logs on start (if original loadPersistentLogs exists, call it, otherwise implement)
    const load = window.loadPersistentLogs;
    window.loadPersistentLogs = function(){
        const container = document.getElementById('data-stream');
        if (!container) return;
        try{
            const logs = JSON.parse(localStorage.getItem('jarvis_neural_logs') || '[]');
            // logs stored newest first; replay oldest → newest
            logs.slice(0,500).reverse().forEach(l => { window.addStreamLine(l.text, l.type, false); });
        }catch(e){ if (typeof load === 'function') load(); }
    };

    // When appending rows via hologram, only allow append of selected rows
    // Intercept the append button if present in the UI (create one)
    document.addEventListener('DOMContentLoaded', ()=>{
        // Create "Append Selected" small button near hologram footer if hologram exists
        const modal = document.getElementById('hologram-modal');
        if (!modal) return;
        let appendBtn = document.createElement('button');
        appendBtn.textContent = 'Append Selected';
        appendBtn.title = 'Append only checked profiles to Excel (requires selection)';
        appendBtn.style.position = 'absolute';
        appendBtn.style.left = '14px';
        appendBtn.style.bottom = '14px';
        appendBtn.style.padding = '6px 10px';
        appendBtn.style.borderRadius = '6px';
        appendBtn.style.background = 'rgba(0,242,255,0.06)';
        appendBtn.style.border = '1px solid rgba(0,242,255,0.12)';
        appendBtn.style.color = 'var(--primary)';
        appendBtn.style.cursor = 'pointer';
        appendBtn.onclick = async () => {
            // Gather selected rows
            const sel = window.hologramSelectedRows ? Array.from(window.hologramSelectedRows) : [];
            if (!sel.length){ window.addStreamLine('No rows selected. Please check entries first.', 'error'); return; }
            // Map selected IDs back to hologramRows
            const rows = (window.hologramRows || []).filter(r => {
                const id = String(r['ลำดับ'] || r['ชื่อ'] || '');
                return sel.includes(id);
            });
            if (!rows.length){ window.addStreamLine('Selected rows not found in current cache.', 'error'); return; }

            // Ask backend to append via API; use currently selected filename or fallback
            const filename = window.lastAppendTargetFile || (window.LAST_USED_FILE || 'students.xlsx');
            try{
                const res = await fetch('/api/append_rows', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ file: filename, rows })
                });
                const data = await res.json();
                if (data.status === 'success'){
                    window.addStreamLine(`Appended ${rows.length} selected rows to ${filename}`, 'bot');
                } else {
                    window.addStreamLine(`Append failed: ${data.message || JSON.stringify(data)}`, 'error');
                }
            }catch(e){ window.addStreamLine(`Network error: ${e.message}`, 'error'); }
        };

        // Append button inside hologram card
        const card = modal.querySelector('.hologram-card');
        if (card) card.appendChild(appendBtn);
    });
})();
