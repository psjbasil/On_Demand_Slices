/**
 * Network Slice Management Frontend Script
 * Handles UI interactions and communication with backend API
 */

// Global variables to store active slices and their colors
let activeSlices = {};
const sliceColors = {
    'production_control': '#FF6B6B',    // Red
    'monitoring_maintenance': '#4ECDC4', // Cyan
    'office_access': '#9B59B6',         // Purple
    'emergency_response': '#F1C40F'      // Yellow
};

/**
 * Initialize the application when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', () => {
    fetchTopology();
    fetchSlices();
    initializeSliceState();
});

/**
 * Fetch network topology data from backend
 */
async function fetchTopology() {
    try {
        const response = await fetch('/api/topology');
        const topology = await response.json();
        displayTopology(topology);
    } catch (error) {
        console.error('Error fetching topology:', error);
    }
}

/**
 * Fetch slice configurations from backend
 */
async function fetchSlices() {
    try {
        const response = await fetch('/api/slices');
        const slices = await response.json();
        updateSlicesControl(slices);
    } catch (error) {
        console.error('Error fetching slices:', error);
    }
}

/**
 * Update the slice control interface
 * @param {Object} slices - Slice configurations
 */
function updateSlicesControl(slices) {
    const slicesList = document.getElementById('slices-list');
    slicesList.innerHTML = '';

    // Display slices in order of bandwidth percentage
    const sliceOrder = [
        'production_control',    // 50%
        'emergency_response',    // 40%
        'monitoring_maintenance',// 30%
        'office_access'         // 20%
    ];

    // Generate slice list based on predefined order
    sliceOrder.forEach(sliceName => {
        if (slices[sliceName]) {
            const slice = slices[sliceName];
            const li = document.createElement('li');
            li.className = 'slice-item';
            
            // Format slice name for display
            const displayName = sliceName.split('_')
                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                .join(' ');
            
            li.innerHTML = `
                <div class="slice-info">
                    <h3>${displayName}</h3>
                    <p>Bandwidth: ${slice.bandwidth_percentage}%</p>
                    <p>Priority: ${slice.priority}</p>
                    <p>Hosts: ${slice.hosts.join(', ')}</p>
                    <p class="slice-description">${slice.description || ''}</p>
                    <div class="slice-controls">
                        <button onclick="handleActivateSlice('${sliceName}')" class="activate-btn">Activate</button>
                        <button onclick="handleDeactivateSlice('${sliceName}')" class="deactivate-btn">Deactivate</button>
                    </div>
                </div>
            `;
            
            slicesList.appendChild(li);
        }
    });
}

/**
 * Handle slice activation
 * @param {string} sliceName - Name of the slice to activate
 */
async function handleActivateSlice(sliceName) {
    try {
        const button = event.target;
        button.disabled = true;
        
        const response = await fetch(`/api/slices/${sliceName}/activate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            alert(result.error);
            return;
        }
        
        // Update active slices state
        const sliceInfo = await fetch('/api/slices').then(r => r.json());
        activeSlices[sliceName] = {
            active: true,
            hosts: sliceInfo[sliceName].hosts
        };
        
        // Update host colors in topology
        updateHostColors();
        
        alert(result.message);
        await fetchSlices();
        
    } catch (error) {
        console.error('Error activating slice:', error);
        alert('Failed to activate slice');
    } finally {
        button.disabled = false;
    }
}

/**
 * Handle slice deactivation
 * @param {string} sliceName - Name of the slice to deactivate
 */
async function handleDeactivateSlice(sliceName) {
    try {
        const button = event.target;
        button.disabled = true;
        
        const response = await fetch(`/api/slices/${sliceName}/deactivate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            alert(result.error);
            return;
        }
        
        // Update active slices state
        delete activeSlices[sliceName];
        
        // Update host colors in topology
        updateHostColors();
        
        alert(result.message);
        await fetchSlices();
        
    } catch (error) {
        console.error('Error deactivating slice:', error);
        alert('Failed to deactivate slice');
    } finally {
        button.disabled = false;
    }
}

/**
 * Draw network topology visualization
 * @param {Object} topology - Network topology data
 */
function displayTopology(topology) {
    const width = 800;
    const height = 600;
    
    // Clear existing SVG
    d3.select("#network-topology svg").remove();

    const svg = d3.select("#network-topology").append("svg")
        .attr("width", width)
        .attr("height", height);

    // Create force-directed graph
    const simulation = d3.forceSimulation(topology.nodes)
        .force("link", d3.forceLink(topology.links).id(d => d.id))
        .force("charge", d3.forceManyBody().strength(-300))
        .force("center", d3.forceCenter(width / 2, height / 2));

    // Draw links
    const link = svg.append("g")
        .selectAll("line")
        .data(topology.links)
        .enter().append("line")
        .attr("class", "link")
        .style("stroke", "#999")
        .style("stroke-width", 1);

    // Create node groups
    const node = svg.append("g")
        .selectAll(".node")
        .data(topology.nodes)
        .enter().append("g")
        .attr("class", "node")
        .call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));

    // Draw different shapes based on node type with increased size
    node.each(function(d) {
        const element = d3.select(this);
        if (d.id.startsWith('h')) {  // Host nodes
            element.append("rect")
                .attr("width", 30)    // Increased to 1.5x (was 20)
                .attr("height", 30)   // Increased to 1.5x (was 20)
                .attr("x", -15)       // Adjust center position
                .attr("y", -15)       // Adjust center position
                .style("fill", "#6baed6")
                .style("stroke", "#4292c6")
                .style("stroke-width", 2);
        } else {  // Switch nodes
            element.append("circle")
                .attr("r", 15)        // Increased to 1.5x (was 10)
                .style("fill", "#6baed6")
                .style("stroke", "#4292c6")
                .style("stroke-width", 2);
        }
        
        // Adjust label position for larger icons
        element.append("text")
            .attr("dx", 18)           // Increased offset for larger icons
            .attr("dy", 4)
            .style("font-size", "12px")
            .text(d => d.id);
    });

    // Update force layout
    simulation.on("tick", () => {
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        node
            .attr("transform", d => `translate(${d.x},${d.y})`);
    });

    // Drag functions
    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
}

/**
 * Update host colors based on active slices
 */
function updateHostColors() {
    // Get all host nodes
    const hostNodes = d3.selectAll('.node').filter(d => d.id.startsWith('h'));
    
    hostNodes.each(function(d) {
        const node = d3.select(this);
        const rect = node.select('rect');
        const hostId = d.id;
        
        // Find all active slices that this host belongs to
        const belongingSlices = Object.entries(activeSlices)
            .filter(([sliceName, sliceInfo]) => 
                sliceInfo.active && sliceInfo.hosts.includes(hostId))
            .map(([sliceName]) => sliceName);
        
        if (belongingSlices.length === 0) {
            // Use default color if host doesn't belong to any active slice
            rect.style('fill', '#6baed6');
        } else if (belongingSlices.length === 1) {
            // Use slice color if host belongs to one slice
            rect.style('fill', sliceColors[belongingSlices[0]]);
        } else {
            // Create gradient for hosts belonging to multiple slices
            const gradientId = `gradient-${hostId}`;
            
            // Create or update gradient definition
            let gradient = d3.select(`#${gradientId}`);
            if (gradient.empty()) {
                gradient = d3.select('svg').append('defs')
                    .append('linearGradient')
                    .attr('id', gradientId)
                    .attr('x1', '0%')
                    .attr('y1', '0%')
                    .attr('x2', '100%')
                    .attr('y2', '0%');
            } else {
                gradient.selectAll('*').remove();
            }
            
            // Add gradient stops
            belongingSlices.forEach((sliceName, index) => {
                const offset = (index / (belongingSlices.length - 1)) * 100;
                gradient.append('stop')
                    .attr('offset', `${offset}%`)
                    .attr('stop-color', sliceColors[sliceName]);
            });
            
            // Apply gradient
            rect.style('fill', `url(#${gradientId})`);
        }
    });
}

// Initialize slice state
async function initializeSliceState() {
    try {
        const response = await fetch('/api/slices');
        const slices = await response.json();
        activeSlices = {};
        updateHostColors();
    } catch (error) {
        console.error('Error initializing slice state:', error);
    }
}

// Display message with type (info/error)
function showMessage(message, type = 'info') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.textContent = message;
    
    // Remove existing message
    const existingMessage = document.querySelector('.message');
    if (existingMessage) {
        existingMessage.remove();
    }
    
    document.body.appendChild(messageDiv);
    setTimeout(() => messageDiv.remove(), 3000);
}

// Display error message
function showErrorMessage(message) {
    showMessage(message, 'error');
}