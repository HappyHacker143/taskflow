(function() {
    'use strict';

    const POLL_INTERVAL_MS = 10000;
    let lastSync = new Date().toISOString();

    async function syncTaskStatuses() {
        try {
            const response = await fetch(`/tasks/live/?updated_after=${encodeURIComponent(lastSync)}`, {
                headers: { 'Accept': 'application/json' }
            });
            if (!response.ok) return;
            const data = await response.json();
            if (!data.success) return;
            lastSync = data.server_time || new Date().toISOString();

            data.tasks.forEach((task) => {
                const card = document.querySelector(`[data-task-id='${task.id}']`);
                const targetColumn = document.querySelector(`[data-status='${task.status}'] .kanban-cards`);
                if (card && targetColumn && card.parentElement !== targetColumn) {
                    targetColumn.appendChild(card);
                }
            });
        } catch (error) {
            // Silent polling failure: the next interval will retry.
        }
    }

    if (document.querySelector('.kanban-board')) {
        window.setInterval(syncTaskStatuses, POLL_INTERVAL_MS);
    }
})();
