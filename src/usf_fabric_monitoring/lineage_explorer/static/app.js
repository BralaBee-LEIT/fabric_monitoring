/**
 * Fabric Lineage Explorer - Enhanced Application v2.0
 * 
 * A modern, immersive visualization of Microsoft Fabric lineage data
 * featuring animated particles, multiple layouts, minimap, and advanced interactions.
 */

// =============================================================================
// State Management
// =============================================================================

const state = {
    graph: null,
    stats: null,
    filteredGraph: null,
    
    filters: {
        search: '',
        workspaces: new Set(),
        itemTypes: new Set(),
        sourceTypes: new Set()
    },
    
    selectedNode: null,
    hoveredNode: null,
    sidebarOpen: true,
    particlesEnabled: true,
    labelsVisible: true,
    activeDetailTab: 'overview',
    currentLayout: 'force',
    
    simulation: null,
    svg: null,
    zoom: null,
    particleTimer: null,
    minimapSvg: null
};

// =============================================================================
// API Functions
// =============================================================================

async function fetchGraph() {
    const response = await fetch('/api/graph');
    if (!response.ok) throw new Error('Failed to load graph');
    return response.json();
}

async function fetchStats() {
    const response = await fetch('/api/stats');
    if (!response.ok) throw new Error('Failed to load stats');
    return response.json();
}

async function refreshData() {
    const response = await fetch('/api/refresh', { method: 'POST' });
    if (!response.ok) throw new Error('Failed to refresh');
    return response.json();
}

// =============================================================================
// Graph Processing
// =============================================================================

function processGraphData(data) {
    const workspacesById = new Map(data.workspaces.map(w => [w.id, w]));
    const itemsById = new Map(data.items.map(i => [i.id, i]));
    const sourcesById = new Map(data.external_sources.map(s => [s.id, s]));
    
    const nodes = [];
    
    data.workspaces.forEach(ws => {
        nodes.push({ id: ws.id, type: 'workspace', label: ws.name, data: ws });
    });
    
    data.items.forEach(item => {
        nodes.push({
            id: item.id, type: 'item', label: item.name,
            itemType: item.item_type, workspaceId: item.workspace_id, data: item
        });
    });
    
    data.external_sources.forEach(source => {
        nodes.push({
            id: source.id, type: 'source', label: source.display_name,
            sourceType: source.source_type, data: source
        });
    });
    
    const links = data.edges.map(edge => ({
        id: edge.id, source: edge.source_id, target: edge.target_id,
        edgeType: edge.edge_type, metadata: edge.metadata
    }));
    
    return { nodes, links, workspacesById, itemsById, sourcesById };
}

function applyFilters(graph) {
    if (!graph) return null;
    
    const { search, workspaces, itemTypes, sourceTypes } = state.filters;
    const searchLower = search.toLowerCase();
    
    let filteredNodes = graph.nodes.filter(node => {
        if (searchLower && !node.label.toLowerCase().includes(searchLower)) return false;
        
        if (node.type === 'workspace') {
            return workspaces.size === 0 || workspaces.has(node.id);
        }
        if (node.type === 'item') {
            const wsMatch = workspaces.size === 0 || workspaces.has(node.workspaceId);
            const typeMatch = itemTypes.size === 0 || itemTypes.has(node.itemType);
            return wsMatch && typeMatch;
        }
        if (node.type === 'source') {
            return sourceTypes.size === 0 || sourceTypes.has(node.sourceType);
        }
        return true;
    });
    
    const visibleIds = new Set(filteredNodes.map(n => n.id));
    const filteredLinks = graph.links.filter(link => {
        const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
        const targetId = typeof link.target === 'object' ? link.target.id : link.target;
        return visibleIds.has(sourceId) && visibleIds.has(targetId);
    });
    
    return { nodes: filteredNodes, links: filteredLinks,
        workspacesById: graph.workspacesById, itemsById: graph.itemsById, sourcesById: graph.sourcesById };
}

// =============================================================================
// D3 Graph Visualization
// =============================================================================

function initGraph() {
    const container = document.getElementById('graph');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    d3.select('#graph').selectAll('*').remove();
    
    state.svg = d3.select('#graph')
        .append('svg')
        .attr('width', '100%')
        .attr('height', '100%')
        .attr('viewBox', [0, 0, width, height]);
    
    const defs = state.svg.append('defs');
    
    defs.append('marker')
        .attr('id', 'arrow')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 20).attr('refY', 0)
        .attr('markerWidth', 6).attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path').attr('class', 'arrow-marker').attr('d', 'M0,-5L10,0L0,5');
    
    defs.append('marker')
        .attr('id', 'arrow-highlighted')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 20).attr('refY', 0)
        .attr('markerWidth', 6).attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path').attr('class', 'arrow-marker highlighted').attr('d', 'M0,-5L10,0L0,5');
    
    state.zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => {
            state.svg.select('g.main').attr('transform', event.transform);
            updateMinimap();
        });
    
    state.svg.call(state.zoom);
    state.svg.on('click', (event) => { if (event.target.tagName === 'svg') deselectNode(); });
    state.svg.append('g').attr('class', 'main');
    
    initMinimap();
}

function renderGraph(data) {
    if (!data || !data.nodes.length) { showEmptyState(); return; }
    hideEmptyState();
    
    const container = document.getElementById('graph');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    const mainGroup = state.svg.select('g.main');
    mainGroup.selectAll('*').remove();
    
    const linkGroup = mainGroup.append('g').attr('class', 'links');
    mainGroup.append('g').attr('class', 'particles');
    const nodeGroup = mainGroup.append('g').attr('class', 'nodes');
    
    createSimulation(data, width, height);
    
    const links = linkGroup.selectAll('path')
        .data(data.links).join('path')
        .attr('class', 'link').attr('marker-end', 'url(#arrow)').attr('fill', 'none');
    
    const nodes = nodeGroup.selectAll('g')
        .data(data.nodes).join('g')
        .attr('class', d => `node ${state.labelsVisible ? '' : 'labels-hidden'}`)
        .call(drag(state.simulation))
        .on('click', (event, d) => { event.stopPropagation(); selectNode(d); })
        .on('mouseenter', (event, d) => { highlightConnections(d); showTooltip(event, d); })
        .on('mouseleave', () => { clearHighlight(); hideTooltip(); });
    
    nodes.each(function(d) {
        const node = d3.select(this);
        const color = getNodeColor(d);
        const colorRaw = getNodeColorRaw(d);
        
        if (d.type === 'workspace') {
            node.append('rect').attr('class', 'node-glow')
                .attr('width', 32).attr('height', 32).attr('x', -16).attr('y', -16)
                .attr('rx', 6).attr('fill', colorRaw).attr('filter', 'blur(8px)');
            node.append('rect').attr('class', 'node-shape')
                .attr('width', 24).attr('height', 24).attr('x', -12).attr('y', -12)
                .attr('rx', 4).attr('fill', color);
        } else if (d.type === 'item') {
            node.append('circle').attr('class', 'node-glow')
                .attr('r', 16).attr('fill', colorRaw).attr('filter', 'blur(8px)');
            node.append('circle').attr('class', 'node-shape').attr('r', 10).attr('fill', color);
        } else {
            node.append('rect').attr('class', 'node-glow')
                .attr('width', 22).attr('height', 22).attr('x', -11).attr('y', -11)
                .attr('transform', 'rotate(45)').attr('fill', colorRaw).attr('filter', 'blur(8px)');
            node.append('rect').attr('class', 'node-shape')
                .attr('width', 16).attr('height', 16).attr('x', -8).attr('y', -8)
                .attr('transform', 'rotate(45)').attr('fill', color);
        }
        node.append('text').attr('dy', d.type === 'workspace' ? 24 : 20).text(truncate(d.label, 18));
    });
    
    state.simulation.on('tick', () => {
        links.attr('d', d => `M${d.source.x},${d.source.y}L${d.target.x},${d.target.y}`);
        nodes.attr('transform', d => `translate(${d.x},${d.y})`);
        updateMinimap();
    });
    
    if (state.particlesEnabled) startParticles();
}

function createSimulation(data, width, height) {
    if (state.simulation) state.simulation.stop();
    
    if (state.currentLayout === 'radial') {
        createRadialLayout(data, width, height);
    } else if (state.currentLayout === 'tree') {
        createTreeLayout(data, width, height);
    } else {
        state.simulation = d3.forceSimulation(data.nodes)
            .force('link', d3.forceLink(data.links).id(d => d.id).distance(100).strength(0.4))
            .force('charge', d3.forceManyBody().strength(-400).distanceMax(500))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(45))
            .force('x', d3.forceX(width / 2).strength(0.05))
            .force('y', d3.forceY(height / 2).strength(0.05));
    }
}

function createRadialLayout(data, width, height) {
    const centerX = width / 2, centerY = height / 2;
    const radius = Math.min(width, height) / 3;
    
    const workspaces = data.nodes.filter(n => n.type === 'workspace');
    const items = data.nodes.filter(n => n.type === 'item');
    const sources = data.nodes.filter(n => n.type === 'source');
    
    workspaces.forEach((node, i) => {
        const angle = (i / workspaces.length) * 2 * Math.PI - Math.PI / 2;
        node.fx = centerX + radius * 0.4 * Math.cos(angle);
        node.fy = centerY + radius * 0.4 * Math.sin(angle);
    });
    items.forEach((node, i) => {
        const angle = (i / items.length) * 2 * Math.PI - Math.PI / 2;
        node.fx = centerX + radius * 0.75 * Math.cos(angle);
        node.fy = centerY + radius * 0.75 * Math.sin(angle);
    });
    sources.forEach((node, i) => {
        const angle = (i / sources.length) * 2 * Math.PI - Math.PI / 2;
        node.fx = centerX + radius * Math.cos(angle);
        node.fy = centerY + radius * Math.sin(angle);
    });
    
    state.simulation = d3.forceSimulation(data.nodes)
        .force('link', d3.forceLink(data.links).id(d => d.id).strength(0)).alphaDecay(0.1);
}

function createTreeLayout(data, width, height) {
    const root = { id: 'root', children: [] };
    const workspaces = data.nodes.filter(n => n.type === 'workspace');
    
    workspaces.forEach(ws => {
        const wsNode = { ...ws, children: [] };
        data.nodes.filter(n => n.type === 'item' && n.workspaceId === ws.id)
            .forEach(item => wsNode.children.push({ ...item, children: [] }));
        root.children.push(wsNode);
    });
    
    data.nodes.filter(n => n.type === 'source' || (n.type === 'item' && !n.workspaceId))
        .forEach(node => root.children.push({ ...node, children: [] }));
    
    const hierarchy = d3.hierarchy(root);
    d3.tree().size([width - 200, height - 200])(hierarchy);
    
    hierarchy.descendants().forEach(d => {
        const node = data.nodes.find(n => n.id === d.data.id);
        if (node) { node.fx = d.x + 100; node.fy = d.y + 100; }
    });
    
    state.simulation = d3.forceSimulation(data.nodes)
        .force('link', d3.forceLink(data.links).id(d => d.id).strength(0)).alphaDecay(0.1);
}

function drag(simulation) {
    return d3.drag()
        .on('start', (event) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        })
        .on('drag', (event) => {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        })
        .on('end', (event) => {
            if (!event.active) simulation.alphaTarget(0);
            if (state.currentLayout === 'force') {
                event.subject.fx = null;
                event.subject.fy = null;
            }
        });
}

// =============================================================================
// Particles
// =============================================================================

function startParticles() {
    stopParticles();
    if (!state.particlesEnabled || !state.filteredGraph?.links.length) return;
    
    const particleGroup = state.svg.select('g.particles');
    
    state.particleTimer = setInterval(() => {
        if (!state.filteredGraph?.links.length) return;
        const numParticles = Math.min(3, state.filteredGraph.links.length);
        for (let i = 0; i < numParticles; i++) {
            const link = state.filteredGraph.links[Math.floor(Math.random() * state.filteredGraph.links.length)];
            if (link.source.x !== undefined) {
                particleGroup.append('circle')
                    .attr('class', 'particle').attr('r', 3)
                    .attr('cx', link.source.x).attr('cy', link.source.y)
                    .transition().duration(1500 + Math.random() * 1000).ease(d3.easeLinear)
                    .attr('cx', link.target.x).attr('cy', link.target.y).remove();
            }
        }
    }, 800);
}

function stopParticles() {
    if (state.particleTimer) { clearInterval(state.particleTimer); state.particleTimer = null; }
    state.svg?.select('g.particles').selectAll('*').remove();
}

function toggleParticles() {
    state.particlesEnabled = !state.particlesEnabled;
    const btn = document.getElementById('btn-toggle-particles');
    if (state.particlesEnabled) { btn?.classList.add('active'); startParticles(); }
    else { btn?.classList.remove('active'); stopParticles(); }
}

// =============================================================================
// Minimap
// =============================================================================

function initMinimap() {
    const container = document.querySelector('.minimap-svg');
    if (!container) return;
    state.minimapSvg = d3.select(container).append('svg').attr('width', '100%').attr('height', '100%');
}

function updateMinimap() {
    if (!state.minimapSvg || !state.filteredGraph?.nodes.length) return;
    
    const mainContainer = document.getElementById('graph');
    const mainWidth = mainContainer.clientWidth, mainHeight = mainContainer.clientHeight;
    const miniWidth = 160, miniHeight = 85;
    
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    state.filteredGraph.nodes.forEach(node => {
        if (node.x !== undefined) {
            if (node.x < minX) minX = node.x; if (node.x > maxX) maxX = node.x;
            if (node.y < minY) minY = node.y; if (node.y > maxY) maxY = node.y;
        }
    });
    if (minX === Infinity) return;
    
    const padding = 20;
    const graphWidth = maxX - minX + padding * 2, graphHeight = maxY - minY + padding * 2;
    const scale = Math.min(miniWidth / graphWidth, miniHeight / graphHeight);
    
    state.minimapSvg.selectAll('*').remove();
    const g = state.minimapSvg.append('g')
        .attr('transform', `translate(${(miniWidth - graphWidth * scale) / 2}, ${(miniHeight - graphHeight * scale) / 2})`);
    
    g.selectAll('line').data(state.filteredGraph.links).join('line')
        .attr('stroke', 'rgba(75, 85, 99, 0.5)').attr('stroke-width', 0.5)
        .attr('x1', d => (d.source.x - minX + padding) * scale)
        .attr('y1', d => (d.source.y - minY + padding) * scale)
        .attr('x2', d => (d.target.x - minX + padding) * scale)
        .attr('y2', d => (d.target.y - minY + padding) * scale);
    
    g.selectAll('circle').data(state.filteredGraph.nodes).join('circle')
        .attr('r', 2).attr('fill', d => getNodeColorRaw(d))
        .attr('cx', d => (d.x - minX + padding) * scale)
        .attr('cy', d => (d.y - minY + padding) * scale);
    
    const transform = d3.zoomTransform(state.svg.node());
    g.append('rect').attr('class', 'minimap-viewport')
        .attr('x', (-transform.x / transform.k - minX + padding) * scale)
        .attr('y', (-transform.y / transform.k - minY + padding) * scale)
        .attr('width', (mainWidth / transform.k) * scale)
        .attr('height', (mainHeight / transform.k) * scale)
        .attr('fill', 'rgba(59, 130, 246, 0.1)')
        .attr('stroke', 'var(--accent-blue)').attr('stroke-width', 1);
}

// =============================================================================
// Node Selection & Highlighting
// =============================================================================

function selectNode(node) {
    state.selectedNode = node;
    state.svg.selectAll('.node').classed('selected', d => d.id === node.id);
    showNodeDetail(node);
    document.getElementById('detail-panel').classList.add('open');
}

function deselectNode() {
    state.selectedNode = null;
    state.svg?.selectAll('.node').classed('selected', false);
    document.getElementById('detail-panel')?.classList.remove('open');
}

function highlightConnections(node) {
    state.hoveredNode = node;
    const connectedIds = new Set([node.id]);
    state.filteredGraph?.links.forEach(link => {
        const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
        const targetId = typeof link.target === 'object' ? link.target.id : link.target;
        if (sourceId === node.id) connectedIds.add(targetId);
        if (targetId === node.id) connectedIds.add(sourceId);
    });
    
    state.svg.selectAll('.node')
        .classed('dimmed', d => !connectedIds.has(d.id))
        .classed('highlighted', d => connectedIds.has(d.id));
    
    state.svg.selectAll('.link')
        .classed('highlighted', d => {
            const sId = typeof d.source === 'object' ? d.source.id : d.source;
            const tId = typeof d.target === 'object' ? d.target.id : d.target;
            return sId === node.id || tId === node.id;
        })
        .classed('dimmed', d => {
            const sId = typeof d.source === 'object' ? d.source.id : d.source;
            const tId = typeof d.target === 'object' ? d.target.id : d.target;
            return sId !== node.id && tId !== node.id;
        })
        .attr('marker-end', d => {
            const sId = typeof d.source === 'object' ? d.source.id : d.source;
            const tId = typeof d.target === 'object' ? d.target.id : d.target;
            return (sId === node.id || tId === node.id) ? 'url(#arrow-highlighted)' : 'url(#arrow)';
        });
}

function clearHighlight() {
    state.hoveredNode = null;
    state.svg?.selectAll('.node').classed('dimmed', false).classed('highlighted', false);
    state.svg?.selectAll('.link').classed('highlighted', false).classed('dimmed', false).attr('marker-end', 'url(#arrow)');
}

// =============================================================================
// Tooltip
// =============================================================================

function showTooltip(event, node) {
    const tooltip = document.getElementById('tooltip');
    tooltip.querySelector('.tooltip-title').textContent = node.label;
    tooltip.querySelector('.tooltip-subtitle').textContent = node.type === 'item' 
        ? node.itemType : node.type.charAt(0).toUpperCase() + node.type.slice(1);
    tooltip.classList.add('visible');
    tooltip.style.left = `${event.pageX + 15}px`;
    tooltip.style.top = `${event.pageY + 15}px`;
}

function hideTooltip() { document.getElementById('tooltip')?.classList.remove('visible'); }

// =============================================================================
// Detail Panel
// =============================================================================

function showNodeDetail(node) {
    const typeBadge = document.getElementById('detail-type-badge');
    const title = document.getElementById('detail-title');
    typeBadge.textContent = node.type === 'item' ? node.itemType : node.type;
    typeBadge.className = `detail-type-badge ${node.type}`;
    title.textContent = node.label;
    updateDetailTab('overview');
}

function updateDetailTab(tab) {
    state.activeDetailTab = tab;
    const node = state.selectedNode;
    if (!node) return;
    
    document.querySelectorAll('.detail-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
    const content = document.getElementById('detail-content');
    
    if (tab === 'overview') content.innerHTML = renderOverviewTab(node);
    else if (tab === 'connections') content.innerHTML = renderConnectionsTab(node);
    else if (tab === 'metadata') content.innerHTML = renderMetadataTab(node);
}

function renderOverviewTab(node) {
    let html = `<div class="detail-field"><div class="label">Type</div><div class="value">${node.type === 'item' ? node.itemType : node.type}</div></div>`;
    html += `<div class="detail-field"><div class="label">ID</div><div class="value mono">${node.id}</div></div>`;
    
    if (node.type === 'item') {
        const ws = state.graph?.workspacesById.get(node.workspaceId);
        if (ws) html += `<div class="detail-field"><div class="label">Workspace</div><div class="value">${ws.name}</div></div>`;
    }
    if (node.type === 'source') {
        html += `<div class="detail-field"><div class="label">Source Type</div><div class="value">${node.sourceType || 'Unknown'}</div></div>`;
    }
    
    const conn = getNodeConnections(node);
    html += `<div class="detail-field"><div class="label">Connections</div><div class="value">${conn.incoming.length} incoming, ${conn.outgoing.length} outgoing</div></div>`;
    return html;
}

function renderConnectionsTab(node) {
    const conn = getNodeConnections(node);
    let html = '';
    
    if (conn.incoming.length) {
        html += `<div class="detail-field"><div class="label">Incoming (${conn.incoming.length})</div></div><div class="connections-list">`;
        conn.incoming.forEach(c => {
            html += `<div class="connection-item" onclick="focusNode('${c.id}')"><span class="icon" style="background:${getNodeColorRaw(c)}"></span><span class="name">${c.label}</span><span class="direction incoming">← source</span></div>`;
        });
        html += '</div>';
    }
    if (conn.outgoing.length) {
        html += `<div class="detail-field" style="margin-top:1rem;"><div class="label">Outgoing (${conn.outgoing.length})</div></div><div class="connections-list">`;
        conn.outgoing.forEach(c => {
            html += `<div class="connection-item" onclick="focusNode('${c.id}')"><span class="icon" style="background:${getNodeColorRaw(c)}"></span><span class="name">${c.label}</span><span class="direction outgoing">→ target</span></div>`;
        });
        html += '</div>';
    }
    return html || '<div class="detail-placeholder"><p>No connections</p></div>';
}

function renderMetadataTab(node) {
    return node.data 
        ? `<div class="detail-field"><div class="label">Raw Data</div><div class="value mono">${JSON.stringify(node.data, null, 2)}</div></div>`
        : '<div class="detail-placeholder"><p>No metadata available</p></div>';
}

function getNodeConnections(node) {
    const incoming = [], outgoing = [];
    if (!state.filteredGraph) return { incoming, outgoing };
    const nodesById = new Map(state.filteredGraph.nodes.map(n => [n.id, n]));
    
    state.filteredGraph.links.forEach(link => {
        const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
        const targetId = typeof link.target === 'object' ? link.target.id : link.target;
        if (targetId === node.id && nodesById.has(sourceId)) incoming.push(nodesById.get(sourceId));
        if (sourceId === node.id && nodesById.has(targetId)) outgoing.push(nodesById.get(targetId));
    });
    return { incoming, outgoing };
}

function focusNode(nodeId) {
    const node = state.filteredGraph?.nodes.find(n => n.id === nodeId);
    if (node && node.x !== undefined) {
        selectNode(node);
        const transform = d3.zoomIdentity
            .translate(state.svg.node().clientWidth / 2, state.svg.node().clientHeight / 2)
            .scale(1.5).translate(-node.x, -node.y);
        state.svg.transition().duration(500).call(state.zoom.transform, transform);
    }
}

// =============================================================================
// Search
// =============================================================================

function initSearch() {
    const input = document.getElementById('search-input');
    const clearBtn = document.getElementById('search-clear');
    const results = document.getElementById('search-results');
    
    input?.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        state.filters.search = query;
        clearBtn.classList.toggle('hidden', !query);
        if (query.length >= 2) showSearchResults(query);
        else { results.classList.add('hidden'); updateGraph(); }
    });
    
    input?.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            input.value = ''; state.filters.search = '';
            clearBtn.classList.add('hidden'); results.classList.add('hidden');
            updateGraph();
        }
    });
    
    clearBtn?.addEventListener('click', () => {
        input.value = ''; state.filters.search = '';
        clearBtn.classList.add('hidden'); results.classList.add('hidden');
        updateGraph();
    });
}

function showSearchResults(query) {
    const results = document.getElementById('search-results');
    const queryLower = query.toLowerCase();
    const matches = state.graph?.nodes.filter(n => n.label.toLowerCase().includes(queryLower)).slice(0, 10) || [];
    
    if (!matches.length) {
        results.innerHTML = '<div class="search-result-item"><span class="name">No results found</span></div>';
    } else {
        results.innerHTML = matches.map(node => {
            const idx = node.label.toLowerCase().indexOf(queryLower);
            const highlighted = node.label.slice(0, idx) + '<strong>' + node.label.slice(idx, idx + query.length) + '</strong>' + node.label.slice(idx + query.length);
            return `<div class="search-result-item" onclick="focusNode('${node.id}')"><span class="dot" style="background:${getNodeColorRaw(node)}"></span><span class="name">${highlighted}</span><span class="type">${node.type}</span></div>`;
        }).join('');
    }
    results.classList.remove('hidden');
}

// =============================================================================
// Filters
// =============================================================================

function initFilters() {
    if (!state.graph) return;
    
    const workspaces = state.graph.nodes.filter(n => n.type === 'workspace');
    const itemTypes = [...new Set(state.graph.nodes.filter(n => n.type === 'item').map(n => n.itemType))];
    const sourceTypes = [...new Set(state.graph.nodes.filter(n => n.type === 'source').map(n => n.sourceType))];
    
    const wsContainer = document.getElementById('filter-workspaces');
    wsContainer.innerHTML = workspaces.map(ws => {
        const count = state.graph.nodes.filter(n => n.type === 'item' && n.workspaceId === ws.id).length;
        return `<span class="chip active" data-id="${ws.id}">${truncate(ws.label, 18)} <span class="count">(${count})</span></span>`;
    }).join('');
    workspaces.forEach(ws => state.filters.workspaces.add(ws.id));
    
    const itemContainer = document.getElementById('filter-item-types');
    itemContainer.innerHTML = itemTypes.sort().map(type => {
        const count = state.graph.nodes.filter(n => n.type === 'item' && n.itemType === type).length;
        return `<span class="chip active" data-type="${type}">${type} <span class="count">(${count})</span></span>`;
    }).join('');
    itemTypes.forEach(t => state.filters.itemTypes.add(t));
    
    const sourceContainer = document.getElementById('filter-source-types');
    sourceContainer.innerHTML = sourceTypes.sort().map(type => {
        const count = state.graph.nodes.filter(n => n.type === 'source' && n.sourceType === type).length;
        return `<span class="chip active" data-source-type="${type}">${type} <span class="count">(${count})</span></span>`;
    }).join('');
    sourceTypes.forEach(t => state.filters.sourceTypes.add(t));
    
    setupFilterListeners();
}

function setupFilterListeners() {
    document.getElementById('filter-workspaces')?.addEventListener('click', (e) => {
        const chip = e.target.closest('.chip'); if (!chip) return;
        const id = chip.dataset.id;
        chip.classList.toggle('active');
        if (state.filters.workspaces.has(id)) state.filters.workspaces.delete(id);
        else state.filters.workspaces.add(id);
        updateGraph();
    });
    
    document.getElementById('filter-item-types')?.addEventListener('click', (e) => {
        const chip = e.target.closest('.chip'); if (!chip) return;
        const type = chip.dataset.type;
        chip.classList.toggle('active');
        if (state.filters.itemTypes.has(type)) state.filters.itemTypes.delete(type);
        else state.filters.itemTypes.add(type);
        updateGraph();
    });
    
    document.getElementById('filter-source-types')?.addEventListener('click', (e) => {
        const chip = e.target.closest('.chip'); if (!chip) return;
        const type = chip.dataset.sourceType;
        chip.classList.toggle('active');
        if (state.filters.sourceTypes.has(type)) state.filters.sourceTypes.delete(type);
        else state.filters.sourceTypes.add(type);
        updateGraph();
    });
    
    document.getElementById('btn-reset-filters')?.addEventListener('click', resetFilters);
}

function resetFilters() {
    document.querySelectorAll('#filter-workspaces .chip, #filter-item-types .chip, #filter-source-types .chip')
        .forEach(chip => chip.classList.add('active'));
    
    state.filters.workspaces.clear();
    state.filters.itemTypes.clear();
    state.filters.sourceTypes.clear();
    
    state.graph?.nodes.forEach(n => {
        if (n.type === 'workspace') state.filters.workspaces.add(n.id);
        if (n.type === 'item' && n.itemType) state.filters.itemTypes.add(n.itemType);
        if (n.type === 'source' && n.sourceType) state.filters.sourceTypes.add(n.sourceType);
    });
    
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.value = ''; state.filters.search = '';
        document.getElementById('search-clear')?.classList.add('hidden');
        document.getElementById('search-results')?.classList.add('hidden');
    }
    updateGraph();
}

// =============================================================================
// Stats & Controls
// =============================================================================

function updateStats() {
    if (!state.stats) return;
    document.getElementById('stat-workspaces').textContent = state.stats.workspace_count;
    document.getElementById('stat-items').textContent = state.stats.item_count;
    document.getElementById('stat-connections').textContent = state.stats.edge_count;
}

function setupControls() {
    document.getElementById('btn-zoom-in')?.addEventListener('click', () => state.svg.transition().duration(300).call(state.zoom.scaleBy, 1.5));
    document.getElementById('btn-zoom-out')?.addEventListener('click', () => state.svg.transition().duration(300).call(state.zoom.scaleBy, 0.67));
    document.getElementById('btn-fit')?.addEventListener('click', fitGraphToView);
    
    document.querySelectorAll('.layout-switcher .btn-icon').forEach(btn => {
        btn.addEventListener('click', () => {
            const layout = btn.dataset.layout;
            if (layout && layout !== state.currentLayout) setLayout(layout);
        });
    });
    
    document.getElementById('btn-refresh')?.addEventListener('click', async () => {
        showLoading();
        try { await refreshData(); await loadData(); } catch (e) { console.error('Refresh failed:', e); }
        hideLoading();
    });
    
    document.getElementById('btn-toggle-particles')?.addEventListener('click', toggleParticles);
    document.getElementById('btn-toggle-labels')?.addEventListener('click', () => {
        state.labelsVisible = !state.labelsVisible;
        state.svg?.selectAll('.node').classed('labels-hidden', !state.labelsVisible);
    });
    document.getElementById('btn-toggle-sidebar')?.addEventListener('click', () => {
        state.sidebarOpen = !state.sidebarOpen;
        document.getElementById('sidebar')?.classList.toggle('open', state.sidebarOpen);
    });
    document.getElementById('btn-close-detail')?.addEventListener('click', deselectNode);
    
    document.querySelectorAll('.detail-tab').forEach(tab => {
        tab.addEventListener('click', () => updateDetailTab(tab.dataset.tab));
    });
    
    document.addEventListener('keydown', (event) => {
        if (event.target.tagName === 'INPUT') return;
        if (event.key === 'Escape') deselectNode();
        else if (event.key === 'f' || event.key === 'F') fitGraphToView();
        else if (event.key === '+' || event.key === '=') state.svg.transition().duration(200).call(state.zoom.scaleBy, 1.3);
        else if (event.key === '-') state.svg.transition().duration(200).call(state.zoom.scaleBy, 0.77);
        else if (event.key === '/') { event.preventDefault(); document.getElementById('search-input')?.focus(); }
    });
}

function setLayout(layout) {
    state.currentLayout = layout;
    document.querySelectorAll('.layout-switcher .btn-icon').forEach(btn => btn.classList.toggle('active', btn.dataset.layout === layout));
    if (layout === 'force') state.filteredGraph?.nodes.forEach(node => { node.fx = null; node.fy = null; });
    updateGraph();
}

function fitGraphToView() {
    if (!state.filteredGraph?.nodes.length) return;
    const container = document.getElementById('graph');
    const width = container.clientWidth, height = container.clientHeight;
    
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    state.filteredGraph.nodes.forEach(node => {
        if (node.x !== undefined) {
            if (node.x < minX) minX = node.x; if (node.x > maxX) maxX = node.x;
            if (node.y < minY) minY = node.y; if (node.y > maxY) maxY = node.y;
        }
    });
    if (minX === Infinity) return;
    
    const graphWidth = maxX - minX + 100, graphHeight = maxY - minY + 100;
    const scale = Math.min(width / graphWidth, height / graphHeight, 2) * 0.85;
    const transform = d3.zoomIdentity
        .translate(width / 2, height / 2).scale(scale)
        .translate(-(minX + maxX) / 2, -(minY + maxY) / 2);
    state.svg.transition().duration(500).call(state.zoom.transform, transform);
}

// =============================================================================
// Utilities
// =============================================================================

function showEmptyState() { document.getElementById('empty-state')?.classList.remove('hidden'); }
function hideEmptyState() { document.getElementById('empty-state')?.classList.add('hidden'); }
function showLoading() { document.getElementById('loading-overlay')?.classList.remove('hidden'); }
function hideLoading() { document.getElementById('loading-overlay')?.classList.add('hidden'); }

function getNodeColor(node) {
    switch (node.type) {
        case 'workspace': return 'var(--node-workspace)';
        case 'item': return 'var(--node-item)';
        case 'source': return 'var(--node-source)';
        default: return 'var(--text-muted)';
    }
}

function getNodeColorRaw(node) {
    switch (node.type) {
        case 'workspace': return '#3b82f6';
        case 'item': return '#10b981';
        case 'source': return '#f59e0b';
        default: return '#6b7280';
    }
}

function truncate(str, length) {
    return !str ? '' : str.length > length ? str.slice(0, length) + '…' : str;
}

// =============================================================================
// Main
// =============================================================================

function updateGraph() {
    state.filteredGraph = applyFilters(state.graph);
    renderGraph(state.filteredGraph);
    setTimeout(fitGraphToView, 800);
}

async function loadData() {
    const [graphData, statsData] = await Promise.all([fetchGraph(), fetchStats()]);
    state.graph = processGraphData(graphData);
    state.stats = statsData;
    initFilters();
    updateStats();
    updateGraph();
}

async function init() {
    showLoading();
    try {
        initGraph();
        initSearch();
        setupControls();
        document.getElementById('sidebar')?.classList.add('open');
        await loadData();
    } catch (error) {
        console.error('Initialization failed:', error);
        const loading = document.getElementById('loading-overlay');
        if (loading) {
            loading.innerHTML = `<div class="loading-content">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--accent-red)" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                <p class="loading-text" style="color:var(--accent-red);">Failed to load data</p>
                <p class="loading-subtext">${error.message}</p>
                <button class="btn btn-primary" style="margin-top:1rem;" onclick="location.reload()">Retry</button>
            </div>`;
        }
        return;
    }
    hideLoading();
}

document.addEventListener('DOMContentLoaded', init);

let resizeTimeout;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        if (state.svg) {
            const container = document.getElementById('graph');
            state.svg.attr('viewBox', [0, 0, container.clientWidth, container.clientHeight]);
            updateMinimap();
        }
    }, 100);
});

window.focusNode = focusNode;
