document.addEventListener('DOMContentLoaded', () => {
    fetchTopology();
    fetchSlices();
});

async function fetchTopology() {
    try {
        const response = await fetch('/api/topology');
        const topology = await response.json();
        displayTopology(topology);
    } catch (error) {
        console.error('Error fetching topology:', error);
    }
}

function displayTopology(topology) {
    const width = 800;
    const height = 600;

    const svg = d3.select("#network-topology").append("svg")
        .attr("width", width)
        .attr("height", height);

    // 创建一个映射来存储节点 ID 和对应的索引
    const nodeMap = {};
    topology.nodes.forEach((node, i) => {
        nodeMap[node.id] = i;
    });

    // 将 source 和 target 替换为对应的索引
    const links = topology.links.map(link => ({
        source: nodeMap[link.source],
        target: nodeMap[link.target]
    }));

    // 初始化节点位置
    topology.nodes.forEach(node => {
        node.x = Math.random() * width; // 随机初始 x 坐标
        node.y = Math.random() * height; // 随机初始 y 坐标
    });

    const simulation = d3.forceSimulation(topology.nodes)
        .force("charge", d3.forceManyBody().strength(-400))
        .force("link", d3.forceLink(links).distance(100))
        .force("center", d3.forceCenter(width / 2, height / 2)); // 添加中心力

    const link = svg.selectAll(".link")
        .data(links)
        .enter().append("line")
        .attr("class", "link");

    const node = svg.selectAll(".node")
        .data(topology.nodes)
        .enter().append("g")
        .attr("class", "node")
        .call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));

    node.append("circle")
        .attr("r", 8);

    node.append("text")
        .attr("dx", 12)
        .attr("dy", ".35em")
        .text(d => d.id);

    simulation.on("tick", () => {
        link.attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        node.attr("transform", d => `translate(${d.x},${d.y})`);
    });

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

async function fetchSlices() {
    try {
        const response = await fetch('/api/slices');
        const slices = await response.json();
        displaySlices(slices);
    } catch (error) {
        console.error('Error fetching slices:', error);
    }
}

function displaySlices(slices) {
    const slicesList = document.getElementById('slices-list');
    slicesList.innerHTML = '';
    for (const [sliceName, hosts] of Object.entries(slices)) {
        const li = document.createElement('li');
        li.textContent = `${sliceName}: ${hosts.join(', ')}`;

        const activateButton = document.createElement('button');
        activateButton.textContent = 'Activate';
        activateButton.onclick = () => handleActivateSlice(sliceName);
        li.appendChild(activateButton);

        const deactivateButton = document.createElement('button');
        deactivateButton.textContent = 'Deactivate';
        deactivateButton.onclick = () => handleDeactivateSlice(sliceName);
        li.appendChild(deactivateButton);

        slicesList.appendChild(li);
    }
}

async function handleActivateSlice(sliceName) {
    try {
        const response = await fetch(`/api/slices/${sliceName}/activate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ slice_name: sliceName })
        });
        if (!response.ok) {
            throw new Error(await response.text());
        }
        const message = await response.json();
        alert(message.message);
        fetchSlices();
    } catch (error) {
        console.error('Error activating slice:', error);
        alert(`Error activating slice: ${error.message}`);
    }
}

async function handleDeactivateSlice(sliceName) {
    try {
        const response = await fetch(`/api/slices/${sliceName}/deactivate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ slice_name: sliceName })
        });
        if (!response.ok) {
            throw new Error(await response.text());
        }
        const message = await response.json();
        alert(message.message);
        fetchSlices();
    } catch (error) {
        console.error('Error deactivating slice:', error);
        alert(`Error deactivating slice: ${error.message}`);
    }
}
