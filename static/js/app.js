document.addEventListener('DOMContentLoaded', () => {
    // --- State ---
    let isConnected = false;
    let liveMode = false;
    let currentGroup = 1;
    let eventSource = null;
    let sparklineData = {};
    let dashRefreshTimer = null;

    // Cached data for export
    let lastDTCs = [];
    let lastMeasurements = {};
    let ecuInfoCache = {};

    // --- DOM Elements ---
    const portSelect = document.getElementById('portSelect');
    const refreshPortsBtn = document.getElementById('refreshPortsBtn');
    const connectBtn = document.getElementById('connectBtn');
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    const mainContent = document.getElementById('mainContent');
    
    const ecuPartNum = document.getElementById('ecuPartNum');
    const ecuExtra = document.getElementById('ecuExtra');
    
    const dtcContainer = document.getElementById('dtcContainer');
    const readDTCBtn = document.getElementById('readDTCBtn');
    const clearDTCBtn = document.getElementById('clearDTCBtn');
    const exportDTCBtn = document.getElementById('exportDTCBtn');
    
    const groupPills = document.getElementById('groupPills');
    const customGroupInput = document.getElementById('customGroupInput');
    const readGroupBtn = document.getElementById('readGroupBtn');
    const groupNameLabel = document.getElementById('groupNameLabel');
    const measContainer = document.getElementById('measContainer');
    const liveModeToggle = document.getElementById('liveModeToggle');
    const exportMeasBtn = document.getElementById('exportMeasBtn');
    
    const toggleLogBtn = document.getElementById('toggleLogBtn');
    const logContainer = document.getElementById('logContainer');
    
    const confirmModal = document.getElementById('confirmModal');
    const cancelModalBtn = document.getElementById('cancelModalBtn');
    const confirmClearBtn = document.getElementById('confirmClearBtn');

    const dashLiveToggle = document.getElementById('dashLiveToggle');
    const exportAllBtn = document.getElementById('exportAllBtn');

    // --- Initialization ---
    initGroupPills();
    fetchPorts();
    
    // --- Event Listeners ---
    refreshPortsBtn.addEventListener('click', fetchPorts);
    
    connectBtn.addEventListener('click', () => {
        if (isConnected) {
            disconnect();
        } else {
            connect();
        }
    });

    readDTCBtn.addEventListener('click', fetchDTCs);
    
    clearDTCBtn.addEventListener('click', () => {
        confirmModal.classList.remove('hidden');
    });
    
    cancelModalBtn.addEventListener('click', () => {
        confirmModal.classList.add('hidden');
    });
    
    confirmClearBtn.addEventListener('click', () => {
        confirmModal.classList.add('hidden');
        clearDTCs();
    });

    readGroupBtn.addEventListener('click', () => {
        let group = customGroupInput.value ? parseInt(customGroupInput.value) : currentGroup;
        if (liveModeToggle.checked) {
            startLiveMode(group);
        } else {
            fetchMeasGroup(group);
        }
    });

    liveModeToggle.addEventListener('change', (e) => {
        if (e.target.checked) {
            startLiveMode(currentGroup);
        } else {
            stopLiveMode();
        }
    });

    toggleLogBtn.addEventListener('click', () => {
        logContainer.classList.toggle('collapsed');
        toggleLogBtn.textContent = logContainer.classList.contains('collapsed') ? '▼' : '▲';
    });

    // Dashboard auto-refresh toggle
    dashLiveToggle.addEventListener('change', (e) => {
        if (e.target.checked) {
            startDashboardRefresh();
        } else {
            stopDashboardRefresh();
        }
    });

    // Export buttons
    exportDTCBtn.addEventListener('click', exportDTCsToFile);
    exportMeasBtn.addEventListener('click', exportMeasToFile);
    exportAllBtn.addEventListener('click', exportFullReport);

    // --- Gauge Drawing ---
    function drawGauge(canvasId, value, min, max, color = '#00d4ff', warnThresh = null, dangerThresh = null) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;
        const cx = w / 2;
        const cy = h / 2 + 10;
        const r = Math.min(w, h) / 2 - 15;

        ctx.clearRect(0, 0, w, h);

        // Angle range: from 220° to -40° (sweeping 260°)
        const startAngle = (220 * Math.PI) / 180;
        const endAngle = (-40 * Math.PI) / 180;
        const totalAngle = startAngle - endAngle;

        // Background arc
        ctx.beginPath();
        ctx.arc(cx, cy, r, endAngle, startAngle, false);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
        ctx.lineWidth = 10;
        ctx.lineCap = 'round';
        ctx.stroke();

        // Value arc
        if (typeof value === 'number' && !isNaN(value)) {
            const clamped = Math.max(min, Math.min(max, value));
            const pct = (clamped - min) / (max - min);
            const valAngle = startAngle - pct * totalAngle;

            // Determine color based on thresholds
            let arcColor = color;
            if (dangerThresh !== null && value >= dangerThresh) {
                arcColor = '#ff3366';
            } else if (warnThresh !== null && value >= warnThresh) {
                arcColor = '#ffa502';
            }

            ctx.beginPath();
            ctx.arc(cx, cy, r, startAngle, valAngle, true);
            ctx.strokeStyle = arcColor;
            ctx.lineWidth = 10;
            ctx.lineCap = 'round';
            ctx.stroke();

            // Glow effect
            ctx.beginPath();
            ctx.arc(cx, cy, r, startAngle, valAngle, true);
            ctx.strokeStyle = arcColor;
            ctx.lineWidth = 10;
            ctx.lineCap = 'round';
            ctx.shadowColor = arcColor;
            ctx.shadowBlur = 12;
            ctx.stroke();
            ctx.shadowBlur = 0;

            // Min/Max labels
            ctx.font = '10px Outfit, sans-serif';
            ctx.fillStyle = 'rgba(255,255,255,0.3)';
            ctx.textAlign = 'center';
            
            const minLabelX = cx + (r + 12) * Math.cos(startAngle);
            const minLabelY = cy + (r + 12) * Math.sin(startAngle);
            ctx.fillText(min, minLabelX, minLabelY);

            const maxLabelX = cx + (r + 12) * Math.cos(endAngle);
            const maxLabelY = cy + (r + 12) * Math.sin(endAngle);
            ctx.fillText(max, maxLabelX, maxLabelY);
        }
    }

    function updateGauges(group, measurements) {
        if (!measurements || measurements.length < 1) return;

        if (group === 1) {
            // Group 1: Compressor & Blower Status
            // Field 0: Compressor Shut-off Code
            if (measurements[0]) {
                const compCode = measurements[0].value;
                const compRing = document.querySelector('.compressor-ring');
                const compValEl = document.getElementById('gaugeValCompressor');
                
                // Compressor is typically ON if shut-off code is 0
                const isOn = (compCode === 0);
                compRing.className = `compressor-ring ${isOn ? 'on' : 'off'}`;
                compValEl.textContent = isOn ? 'ON' : 'OFF';
                compValEl.style.color = isOn ? 'var(--accent-green)' : 'var(--text-muted)';
            }
            // Field 1: Target Blower Voltage
            if (measurements[1]) {
                const blowerVal = measurements[1].value;
                document.getElementById('gaugeValBlower').textContent = typeof blowerVal === 'number' ? blowerVal.toFixed(1) : blowerVal;
                drawGauge('gaugeCanvasBlower', blowerVal, 0, 15, '#00d4ff');
            }
            // Field 2: System Voltage
            if (measurements[2]) {
                const sysV = measurements[2].value;
                document.getElementById('gaugeValSysV').textContent = typeof sysV === 'number' ? sysV.toFixed(1) : sysV;
                drawGauge('gaugeCanvasSysV', sysV, 10, 16, '#00e676', null, null);
            }
        }

        if (group === 2) {
            // Group 2: Temperature Sensors (Raw)
            // Field 0: Interior Sensor (G56)
            if (measurements[0]) {
                const intTemp = measurements[0].value;
                document.getElementById('gaugeValInterior').textContent = typeof intTemp === 'number' ? intTemp.toFixed(1) : intTemp;
                // Using generic 0-255 range for ADC counts since we don't have the exact formula mapping yet
                drawGauge('gaugeCanvasInterior', intTemp, 0, 255, '#00d4ff', 200, 240);
            }
        }

        if (group === 3) {
            // Group 3: External Sensors (Raw)
            // Field 0: Outside Air Sensor (G17)
            if (measurements[0]) {
                const outTemp = measurements[0].value;
                document.getElementById('gaugeValOutside').textContent = typeof outTemp === 'number' ? outTemp.toFixed(1) : outTemp;
                drawGauge('gaugeCanvasOutside', outTemp, 0, 255, '#00d4ff', 200, 240);
            }
            // Field 1: Evaporator Sensor (G263)
            if (measurements[1]) {
                const evapTemp = measurements[1].value;
                document.getElementById('gaugeValEvap').textContent = typeof evapTemp === 'number' ? evapTemp.toFixed(1) : evapTemp;
                drawGauge('gaugeCanvasEvap', evapTemp, 0, 255, '#33ddff', 200, 240);
            }
        }
    }

    // --- Car Diagram Updates ---
    function updateDiagram(group, measurements) {
        if (!measurements || measurements.length < 1) return;

        if (group === 2) {
            // Group 2: Interior Sensor (G56) ADC, Dash Sensor (G86) ADC, Fresh Air Sensor (G89) ADC, Set Temperature
            updateSensorDot('sensorG56', measurements[0], 'diag_G56', '°C');
            updateSensorDot('sensorG86', measurements[1], 'diag_G86', '°C');
            updateSensorDot('sensorG89', measurements[2], 'diag_G89', '°C');
        }

        if (group === 3) {
            // Group 3: Outside Air (G17) ADC, Evaporator (G263) ADC, Coolant Temp ADC, Sunlight (G107) ADC
            updateSensorDot('sensorG17', measurements[0], 'diag_G17', '°C');
            updateSensorDot('sensorG263', measurements[1], 'diag_G263', '°C');
            updateSensorDot('sensorCoolant', measurements[2], 'diag_Coolant', '°C');
            if (measurements[3]) {
                updateSensorDot('sensorG107', measurements[3], 'diag_G107', '');
            }
        }

        if (group === 8) {
            // Group 8: Sensor Voltages - Field 0 is G65 High Pressure
            if (measurements[0]) {
                updateSensorDot('sensorG65', measurements[0], 'diag_G65', ' V');
            }
        }
    }

    function updateSensorDot(groupId, meas, textId, suffix) {
        if (!meas) return;

        const textEl = document.getElementById(textId);
        const groupEl = document.getElementById(groupId);
        if (!textEl || !groupEl) return;

        const val = meas.value;
        const displayVal = typeof val === 'number' ? val.toFixed(1) : val;
        textEl.textContent = `${displayVal}${suffix}`;

        // Determine sensor health from value
        const circles = groupEl.querySelectorAll('circle');
        const outerCircle = circles[0];
        const innerCircle = circles[1];
        const rect = groupEl.querySelector('rect');

        if (typeof val === 'number') {
            if (val <= -40 || val >= 220) {
                // Fault / Open circuit
                setSensorColor(outerCircle, innerCircle, rect, '#ff3366', 'glow-fault');
                outerCircle.style.animation = 'sensor-pulse-fault 1.5s ease-in-out infinite';
            } else if (val >= 100 || val <= -20) {
                // Warning range
                setSensorColor(outerCircle, innerCircle, rect, '#ffa502', 'glow-ok');
                outerCircle.style.animation = '';
            } else {
                // Normal
                setSensorColor(outerCircle, innerCircle, rect, '#00d4ff', 'glow-ok');
                outerCircle.style.animation = '';
            }
        }
    }

    function setSensorColor(outerCircle, innerCircle, rect, color, filterName) {
        const colorMap = {
            '#ff3366': { fill: 'rgba(255,51,102,0.15)', stroke: 'rgba(255,51,102,0.3)' },
            '#ffa502': { fill: 'rgba(255,165,2,0.15)', stroke: 'rgba(255,165,2,0.3)' },
            '#00d4ff': { fill: 'rgba(0,212,255,0.15)', stroke: 'rgba(0,212,255,0.3)' },
            '#00e676': { fill: 'rgba(0,230,118,0.15)', stroke: 'rgba(0,230,118,0.3)' }
        };
        const mapped = colorMap[color] || { fill: 'rgba(0,212,255,0.15)', stroke: 'rgba(0,212,255,0.3)' };

        outerCircle.setAttribute('stroke', color);
        outerCircle.setAttribute('fill', mapped.fill);
        innerCircle.setAttribute('fill', color);
        outerCircle.setAttribute('filter', `url(#${filterName})`);
        if (rect) {
            rect.setAttribute('stroke', mapped.stroke);
        }
    }

    // Dashboard auto-refresh: cycles through groups 1, 2, 3, 8 to populate gauges + diagram
    let dashGroupCycle = [1, 2, 3, 8];
    let dashCycleIdx = 0;

    function startDashboardRefresh() {
        if (dashRefreshTimer) clearInterval(dashRefreshTimer);
        dashCycleIdx = 0;
        addLog('Dashboard auto-refresh started.', 'system');
        
        // Immediately fetch first group
        fetchDashGroup();

        dashRefreshTimer = setInterval(() => {
            if (!isConnected) {
                stopDashboardRefresh();
                return;
            }
            fetchDashGroup();
        }, 2000);
    }

    function stopDashboardRefresh() {
        if (dashRefreshTimer) {
            clearInterval(dashRefreshTimer);
            dashRefreshTimer = null;
        }
        addLog('Dashboard auto-refresh stopped.', 'system');
    }

    async function fetchDashGroup() {
        const group = dashGroupCycle[dashCycleIdx % dashGroupCycle.length];
        dashCycleIdx++;

        try {
            const res = await fetch(`/api/meas/${group}`);
            const data = await res.json();
            if (data.success) {
                updateGauges(group, data.measurements);
                updateDiagram(group, data.measurements);
                // Cache for export
                lastMeasurements[group] = {
                    name: data.name,
                    group: group,
                    measurements: data.measurements,
                    timestamp: new Date().toISOString()
                };
            }
        } catch (e) {
            // Silently fail on dash refresh
        }
    }

    // --- Export Functions ---
    function exportDTCsToFile() {
        if (lastDTCs.length === 0) {
            alert('No fault codes to export. Read faults first.');
            return;
        }
        const report = {
            export_type: 'Fault Codes',
            vehicle: 'Audi A4 B5 (8D2)',
            module: '08 - Auto HVAC',
            ecu_info: ecuInfoCache,
            timestamp: new Date().toISOString(),
            fault_codes: lastDTCs
        };
        downloadJSON(report, `audi_hvac_dtcs_${dateStamp()}.json`);
        addLog(`Exported ${lastDTCs.length} fault codes.`, 'data');
    }

    function exportMeasToFile() {
        if (Object.keys(lastMeasurements).length === 0) {
            alert('No measurement data to export. Read some groups first.');
            return;
        }
        const report = {
            export_type: 'Measurement Blocks',
            vehicle: 'Audi A4 B5 (8D2)',
            module: '08 - Auto HVAC',
            ecu_info: ecuInfoCache,
            timestamp: new Date().toISOString(),
            measurement_blocks: lastMeasurements
        };
        downloadJSON(report, `audi_hvac_meas_${dateStamp()}.json`);
        addLog('Exported measurement blocks.', 'data');
    }

    async function exportFullReport() {
        addLog('Generating full diagnostic report...', 'system');
        
        // Read fresh DTCs
        try {
            const dtcRes = await fetch('/api/dtcs');
            const dtcData = await dtcRes.json();
            if (dtcData.success) {
                lastDTCs = dtcData.dtcs;
                renderDTCs(lastDTCs);
            }
        } catch (e) {}

        // Read all 8 known groups
        for (let g = 1; g <= 8; g++) {
            try {
                const res = await fetch(`/api/meas/${g}`);
                const data = await res.json();
                if (data.success) {
                    lastMeasurements[g] = {
                        name: data.name,
                        group: g,
                        measurements: data.measurements,
                        timestamp: new Date().toISOString()
                    };
                    updateGauges(g, data.measurements);
                    updateDiagram(g, data.measurements);
                }
            } catch (e) {}
        }

        const report = {
            export_type: 'Full Diagnostic Report',
            vehicle: 'Audi A4 B5 (8D2)',
            module: '08 - Auto HVAC',
            ecu_info: ecuInfoCache,
            generated_at: new Date().toISOString(),
            fault_codes: lastDTCs,
            measurement_blocks: lastMeasurements,
            analysis_prompt: 'Please analyze this Audi A4 B5 HVAC diagnostic data. Identify potential issues based on the fault codes and measurement values. Check for out-of-range sensor readings, abnormal temperatures, compressor issues, and any correlations between fault codes and measurement data.'
        };

        downloadJSON(report, `audi_hvac_full_report_${dateStamp()}.json`);
        addLog('Full diagnostic report exported.', 'data');
    }

    function downloadJSON(obj, filename) {
        const blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    function dateStamp() {
        const d = new Date();
        return `${d.getFullYear()}${(d.getMonth()+1).toString().padStart(2,'0')}${d.getDate().toString().padStart(2,'0')}_${d.getHours().toString().padStart(2,'0')}${d.getMinutes().toString().padStart(2,'0')}`;
    }

    // --- API Functions ---
    async function fetchPorts() {
        try {
            portSelect.innerHTML = '<option value="">Scanning...</option>';
            const res = await fetch('/api/ports');
            const data = await res.json();
            
            portSelect.innerHTML = '';
            if (data.ports.length === 0) {
                portSelect.innerHTML = '<option value="">No ports found</option>';
            } else {
                data.ports.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p.device;
                    opt.textContent = `${p.device} ${p.is_likely ? '(KKL)' : ''}`;
                    portSelect.appendChild(opt);
                });
                if (data.auto) {
                    portSelect.value = data.auto;
                }
            }
        } catch (e) {
            addLog(`Error fetching ports: ${e}`, 'error');
        }
    }

    async function connect() {
        const port = portSelect.value;
        if (!port) {
            alert('Please select a port');
            return;
        }

        connectBtn.textContent = 'Connecting...';
        connectBtn.disabled = true;
        addLog(`Connecting to ${port} (Address 0x08)...`, 'system');

        try {
            const res = await fetch('/api/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ port })
            });
            const data = await res.json();

            if (data.success) {
                isConnected = true;
                connectBtn.textContent = 'Disconnect';
                connectBtn.disabled = false;
                connectBtn.classList.replace('btn-primary', 'btn-danger');
                statusDot.classList.replace('disconnected', 'connected');
                statusText.textContent = 'Connected (0x08)';
                
                ecuInfoCache = data.ecu_info;
                ecuPartNum.textContent = data.ecu_info.part_number || 'Unknown';
                ecuExtra.textContent = data.ecu_info.extra.join(', ') || 'N/A';
                
                mainContent.classList.remove('hidden');
                addLog(`Connected successfully. ECU: ${data.ecu_info.part_number}`, 'data');
                
                // Auto-read faults and group 1
                fetchDTCs();
                fetchMeasGroup(1);
            } else {
                throw new Error(data.error);
            }
        } catch (e) {
            connectBtn.textContent = 'Connect';
            connectBtn.disabled = false;
            addLog(`Connection failed: ${e.message}`, 'error');
            alert(`Connection failed: ${e.message}`);
        }
    }

    async function disconnect() {
        if (liveModeToggle.checked) {
            liveModeToggle.click();
        }
        stopDashboardRefresh();
        dashLiveToggle.checked = false;
        
        try {
            await fetch('/api/disconnect', { method: 'POST' });
        } catch(e) {}

        isConnected = false;
        connectBtn.textContent = 'Connect';
        connectBtn.classList.replace('btn-danger', 'btn-primary');
        statusDot.classList.replace('connected', 'disconnected');
        statusText.textContent = 'Disconnected';
        mainContent.classList.add('hidden');
        addLog('Disconnected.', 'system');
    }

    async function fetchDTCs() {
        if (!isConnected) return;
        readDTCBtn.disabled = true;
        readDTCBtn.textContent = 'Reading...';
        addLog('Requesting Fault Codes...', 'system');
        
        try {
            const res = await fetch('/api/dtcs');
            const data = await res.json();
            
            if (data.success) {
                lastDTCs = data.dtcs;
                renderDTCs(data.dtcs);
                addLog(`Read ${data.dtcs.length} faults.`, 'data');
            } else {
                throw new Error(data.error);
            }
        } catch (e) {
            addLog(`Error reading DTCs: ${e.message}`, 'error');
        } finally {
            readDTCBtn.disabled = false;
            readDTCBtn.textContent = 'Read Faults';
        }
    }

    async function clearDTCs() {
        if (!isConnected) return;
        clearDTCBtn.disabled = true;
        addLog('Sending clear faults command...', 'system');
        
        try {
            const res = await fetch('/api/dtcs/clear', { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                addLog('Faults cleared successfully.', 'data');
                setTimeout(fetchDTCs, 1000);
            } else {
                throw new Error(data.error);
            }
        } catch (e) {
            addLog(`Error clearing DTCs: ${e.message}`, 'error');
        } finally {
            clearDTCBtn.disabled = false;
        }
    }

    async function fetchMeasGroup(group) {
        if (!isConnected) return;
        addLog(`Requesting Measurement Group ${group}...`, 'system');
        
        try {
            const res = await fetch(`/api/meas/${group}`);
            const data = await res.json();
            if (data.success) {
                renderMeasurements(data);
                updateGauges(group, data.measurements);
                updateDiagram(group, data.measurements);
                // Cache for export
                lastMeasurements[group] = {
                    name: data.name,
                    group: group,
                    measurements: data.measurements,
                    timestamp: new Date().toISOString()
                };
                addLog(`Group ${group} read success.`, 'data');
            } else {
                 throw new Error(data.error);
            }
        } catch (e) {
             addLog(`Error reading group ${group}: ${e.message}`, 'error');
        }
    }

    // --- Live Mode (SSE) ---
    function startLiveMode(group) {
        if (eventSource) {
            eventSource.close();
        }
        
        addLog(`Starting Live Monitor for Group ${group}...`, 'system');
        eventSource = new EventSource(`/api/meas/live/${group}`);
        
        eventSource.onmessage = (e) => {
            const data = JSON.parse(e.data);
            renderMeasurements(data, true);
            updateGauges(group, data.measurements);
            updateDiagram(group, data.measurements);
        };
        
        eventSource.onerror = (e) => {
            addLog('Live monitor connection error.', 'error');
            stopLiveMode();
            liveModeToggle.checked = false;
        };
    }
    
    async function stopLiveMode() {
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
        try {
            await fetch('/api/meas/live/stop', { method: 'POST' });
        } catch(e) {}
        addLog('Stopped live monitor.', 'system');
    }

    // --- UI Rendering ---
    function renderDTCs(dtcs) {
        dtcContainer.innerHTML = '';
        
        if (dtcs.length === 0) {
            dtcContainer.innerHTML = `
                <div class="empty-state success">
                    <div class="icon">✓</div>
                    <p>No fault codes stored in module.</p>
                </div>
            `;
            return;
        }
        
        dtcs.forEach(dtc => {
            const card = document.createElement('div');
            card.className = 'dtc-card';
            
            const badgeClass = dtc.status.toLowerCase();
            
            card.innerHTML = `
                <div class="dtc-header">
                    <span class="dtc-code">${dtc.code}</span>
                    <span class="dtc-badge ${badgeClass}">${dtc.status}</span>
                </div>
                <div class="dtc-desc">${dtc.description}</div>
                <div class="dtc-details">Elaboration: ${dtc.details} (${dtc.elaboration_hex})</div>
            `;
            dtcContainer.appendChild(card);
        });
    }

    function initGroupPills() {
        for(let i=1; i<=8; i++) {
            const pill = document.createElement('div');
            pill.className = `pill ${i === 1 ? 'active' : ''}`;
            pill.textContent = i;
            pill.dataset.group = i;
            
            pill.addEventListener('click', () => {
                document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
                pill.classList.add('active');
                currentGroup = i;
                customGroupInput.value = '';
                
                if (liveModeToggle.checked) {
                    startLiveMode(i);
                } else {
                    fetchMeasGroup(i);
                }
            });
            groupPills.appendChild(pill);
        }
        
        customGroupInput.addEventListener('change', (e) => {
            const val = parseInt(e.target.value);
            if (val > 0 && val <= 255) {
                document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
                currentGroup = val;
            }
        });
    }

    function renderMeasurements(data, isLive = false) {
        if (!data.measurements) return;
        
        groupNameLabel.textContent = data.name || `Group ${data.group}`;
        
        if (!isLive || measContainer.children.length !== 4) {
            measContainer.innerHTML = '';
            sparklineData = {};
            
            for(let i=0; i<4; i++) {
                const card = document.createElement('div');
                card.className = 'meas-card';
                card.id = `measCard_${i}`;
                
                const canvas = document.createElement('canvas');
                canvas.className = 'meas-sparkline';
                canvas.id = `sparkline_${i}`;
                
                card.innerHTML = `
                    <div class="meas-label" id="measLabel_${i}">---</div>
                    <div class="meas-value-area">
                        <span class="meas-val" id="measVal_${i}">--</span>
                        <span class="meas-unit" id="measUnit_${i}"></span>
                    </div>
                `;
                card.appendChild(canvas);
                measContainer.appendChild(card);
                sparklineData[i] = [];
            }
        }
        
        data.measurements.forEach((meas, i) => {
            if (i >= 4) return;
            
            const card = document.getElementById(`measCard_${i}`);
            const valEl = document.getElementById(`measVal_${i}`);
            
            document.getElementById(`measLabel_${i}`).textContent = meas.label;
            document.getElementById(`measUnit_${i}`).textContent = meas.unit;
            
            if (valEl.textContent != meas.value) {
                valEl.textContent = meas.value;
                card.classList.add('updated');
                setTimeout(() => card.classList.remove('updated'), 200);
            }
            
            if (isLive && typeof meas.value === 'number') {
                updateSparkline(i, meas.value);
            }
        });
    }

    function updateSparkline(idx, val) {
        const arr = sparklineData[idx];
        arr.push(val);
        if (arr.length > 30) arr.shift();
        
        const canvas = document.getElementById(`sparkline_${idx}`);
        if (!canvas) return;
        
        canvas.width = canvas.parentElement.clientWidth;
        canvas.height = 40;
        
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;
        
        ctx.clearRect(0, 0, w, h);
        
        if (arr.length < 2) return;
        
        const max = Math.max(...arr);
        const min = Math.min(...arr);
        const range = (max - min) || 1;
        
        const step = w / (30 - 1);
        
        ctx.beginPath();
        ctx.moveTo(0, h - ((arr[0] - min) / range) * (h - 5) - 2);
        
        for (let i = 1; i < arr.length; i++) {
            const x = i * step;
            const y = h - ((arr[i] - min) / range) * (h - 5) - 2;
            ctx.lineTo(x, y);
        }
        
        ctx.strokeStyle = '#00d4ff';
        ctx.lineWidth = 2;
        ctx.stroke();
        
        ctx.lineTo(w, h);
        ctx.lineTo(0, h);
        ctx.closePath();
        
        const gradient = ctx.createLinearGradient(0, 0, 0, h);
        gradient.addColorStop(0, 'rgba(0, 212, 255, 0.2)');
        gradient.addColorStop(1, 'rgba(0, 212, 255, 0)');
        
        ctx.fillStyle = gradient;
        ctx.fill();
    }

    function addLog(msg, type = 'system') {
        const line = document.createElement('div');
        line.className = `log-line ${type}`;
        
        const now = new Date();
        const time = `${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}:${now.getSeconds().toString().padStart(2,'0')}`;
        
        line.textContent = `[${time}] ${msg}`;
        logContainer.appendChild(line);
        
        if (logContainer.children.length > 100) {
            logContainer.removeChild(logContainer.children[0]);
        }
        
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    // Draw initial empty gauges
    drawGauge('gaugeCanvasInterior', null, -10, 60, '#00d4ff');
    drawGauge('gaugeCanvasOutside', null, -30, 60, '#00d4ff');
    drawGauge('gaugeCanvasEvap', null, -10, 50, '#33ddff');
    drawGauge('gaugeCanvasBlower', null, 0, 14, '#00d4ff');
    drawGauge('gaugeCanvasSysV', null, 10, 16, '#00e676');
});
