const state = {
  currentProject: null,
  graphData: null,
  fileTreeData: null,
  fileTreeFilter: "",
  selectedGraphNodeId: null,
  selectedFilePath: null,
  gitTimeline: [],
  selectedCommitHash: null,
  graphScale: 1,
  graphPanX: 0,
  graphPanY: 0,
  graphViewportWidth: 520,
  graphViewportHeight: 320,
  graphDrag: null,
  graphSuppressClick: false,
};

const elements = {
  projectPath: document.querySelector("#project-path"),
  openProject: document.querySelector("#open-project"),
  rescanProject: document.querySelector("#rescan-project"),
  shutdownApp: document.querySelector("#shutdown-app"),
  refreshTree: document.querySelector("#refresh-tree"),
  fileTreeFilter: document.querySelector("#file-tree-filter"),
  clearTreeFilter: document.querySelector("#clear-tree-filter"),
  refreshTimeline: document.querySelector("#refresh-timeline"),
  detailPath: document.querySelector("#detail-path"),
  loadDetail: document.querySelector("#load-detail"),
  diffHash: document.querySelector("#diff-hash"),
  loadDiff: document.querySelector("#load-diff"),
  serverStatus: document.querySelector("#server-status"),
  notice: document.querySelector("#notice"),
  statusProject: document.querySelector("#status-project"),
  statusCache: document.querySelector("#status-cache"),
  statusGit: document.querySelector("#status-git"),
  fileTreeView: document.querySelector("#file-tree-view"),
  fileTree: document.querySelector("#file-tree"),
  graphZoomOut: document.querySelector("#graph-zoom-out"),
  graphZoomIn: document.querySelector("#graph-zoom-in"),
  graphPanLeft: document.querySelector("#graph-pan-left"),
  graphPanUp: document.querySelector("#graph-pan-up"),
  graphPanDown: document.querySelector("#graph-pan-down"),
  graphPanRight: document.querySelector("#graph-pan-right"),
  graphResetView: document.querySelector("#graph-reset-view"),
  graphCanvas: document.querySelector("#graph-canvas"),
  graphEmpty: document.querySelector("#graph-empty"),
  graphSelected: document.querySelector("#graph-selected"),
  graphView: document.querySelector("#graph-view"),
  fileDetail: document.querySelector("#file-detail"),
  gitTimelineList: document.querySelector("#git-timeline-list"),
  gitSelectedState: document.querySelector("#git-selected-state"),
  gitTimeline: document.querySelector("#git-timeline"),
  gitDiffSummary: document.querySelector("#git-diff-summary"),
  gitDiffHunks: document.querySelector("#git-diff-hunks"),
  gitDiffView: document.querySelector("#git-diff-view"),
  gitDiff: document.querySelector("#git-diff"),
};

function showNotice(message) {
  elements.notice.textContent = message;
}

function renderJson(target, value) {
  target.textContent = JSON.stringify(value, null, 2);
}

async function requestJson(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!payload.ok) {
    const message = payload.error?.message || `Request failed: ${response.status}`;
    throw new Error(message);
  }
  return payload.data;
}

async function optionalJson(path, target, emptyMessage) {
  try {
    const data = await requestJson(path);
    renderJson(target, data ?? {});
  } catch (error) {
    target.textContent = emptyMessage;
  }
}

function setEmpty(target, message) {
  target.replaceChildren();
  target.textContent = message;
}

function formatDate(value) {
  if (!value) {
    return "unknown date";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString();
}

function shortCommitHash(value) {
  return value ? String(value).slice(0, 12) : "unknown";
}

function renderFileTreeData(data) {
  state.fileTreeData = data ?? {};
  renderJson(elements.fileTree, data ?? {});
  renderFilteredFileTree();
}

function normalizeFilter(value) {
  return String(value || "").trim().toLowerCase();
}

function fileTreeMatchText(item) {
  return [item?.name, item?.path, item?.type].filter(Boolean).join(" ").toLowerCase();
}

function filterTreeItem(item, query) {
  if (!query) {
    return item;
  }

  const children = Array.isArray(item?.children) ? item.children.map((child) => filterTreeItem(child, query)).filter(Boolean) : [];
  if (fileTreeMatchText(item).includes(query)) {
    return item;
  }
  if (children.length) {
    return { ...item, children };
  }
  return null;
}

function renderFilteredFileTree() {
  const data = state.fileTreeData ?? {};
  const root = data?.root;
  if (!root) {
    setEmpty(elements.fileTreeView, "Open a project to load the file tree.");
    return;
  }

  const query = normalizeFilter(state.fileTreeFilter);
  const visibleRoot = filterTreeItem(root, query);
  if (!visibleRoot) {
    setEmpty(elements.fileTreeView, `No files match "${state.fileTreeFilter}".`);
    return;
  }

  elements.fileTreeView.replaceChildren(buildTreeList([visibleRoot], true, Boolean(query)));
}

function buildTreeList(items, isRoot = false, isFiltered = false) {
  const list = document.createElement("ul");
  if (isRoot) {
    list.className = "tree-root";
  }
  items.forEach((item) => list.append(buildTreeItem(item, isFiltered)));
  return list;
}

function buildTreeItem(item, isFiltered = false) {
  const treeItem = document.createElement("li");
  treeItem.className = "tree-item";
  const row = document.createElement("button");
  row.type = "button";
  row.className = "tree-row";

  const icon = document.createElement("span");
  icon.className = "tree-icon";
  const label = document.createElement("span");
  label.className = "tree-name";
  label.textContent = item.name || item.path || ".";
  row.append(icon, label);
  treeItem.append(row);

  if (item.type === "folder") {
    const children = Array.isArray(item.children) ? item.children : [];
    icon.textContent = children.length ? "v" : "-";
    row.title = item.path || ".";
    if (children.length) {
      const childList = buildTreeList(children, false, isFiltered);
      childList.className = "tree-children";
      treeItem.append(childList);
      row.addEventListener("click", () => {
        const nextHidden = !childList.hidden;
        childList.hidden = nextHidden;
        icon.textContent = nextHidden ? ">" : "v";
      });
    }
    return treeItem;
  }

  icon.textContent = "*";
  row.title = item.path || item.name || "";
  if (item.path && item.path === state.selectedFilePath) {
    row.classList.add("is-selected");
  }
  row.addEventListener("click", async () => {
    state.selectedFilePath = item.path;
    elements.detailPath.value = item.path || "";
    elements.fileTreeView.querySelectorAll(".tree-row.is-selected").forEach((node) => node.classList.remove("is-selected"));
    row.classList.add("is-selected");
    await loadFileDetail();
  });
  return treeItem;
}

async function optionalFileTree(path, emptyMessage) {
  try {
    const data = await requestJson(path);
    renderFileTreeData(data ?? {});
  } catch (error) {
    state.fileTreeData = null;
    elements.fileTree.textContent = emptyMessage;
    setEmpty(elements.fileTreeView, emptyMessage);
  }
}

function normalizeGraphData(data) {
  return {
    ...data,
    nodes: Array.isArray(data?.nodes) ? data.nodes : [],
    edges: Array.isArray(data?.edges) ? data.edges : [],
  };
}

function nodeKind(node) {
  if (node?.kind === "folder" || String(node?.id || "").startsWith("folder:")) {
    return "folder";
  }
  return "file";
}

function nodePath(node) {
  const path = node?.path;
  if (path === "") {
    return ".";
  }
  return path || String(node?.id || "unknown");
}

function nodeLabel(node) {
  const path = nodePath(node);
  if (path === ".") {
    return ".";
  }
  return path.split("/").filter(Boolean).pop() || path;
}

function createSvgElement(tagName, attributes = {}) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", tagName);
  Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value)));
  return element;
}

function clampGraphScale(value) {
  return Math.max(0.6, Math.min(2.4, value));
}

function graphViewSize(scale = state.graphScale) {
  const safeScale = clampGraphScale(scale);
  return {
    width: state.graphViewportWidth / safeScale,
    height: state.graphViewportHeight / safeScale,
  };
}

function graphPointFromEvent(event) {
  const rect = elements.graphCanvas.getBoundingClientRect();
  if (rect.width <= 0 || rect.height <= 0) {
    return null;
  }
  const viewSize = graphViewSize();
  const relativeX = Math.max(0, Math.min(event.clientX - rect.left, rect.width));
  const relativeY = Math.max(0, Math.min(event.clientY - rect.top, rect.height));
  return {
    graphX: state.graphPanX + (relativeX / rect.width) * viewSize.width,
    graphY: state.graphPanY + (relativeY / rect.height) * viewSize.height,
    relativeX,
    relativeY,
    rect,
  };
}

function graphLayout(nodes) {
  const columns = Math.max(1, Math.min(6, Math.ceil(Math.sqrt(nodes.length || 1))));
  const xGap = 160;
  const yGap = 96;
  const margin = 48;
  const positions = new Map();

  nodes.forEach((node, index) => {
    positions.set(node.id, {
      x: margin + (index % columns) * xGap,
      y: margin + Math.floor(index / columns) * yGap,
    });
  });

  return {
    positions,
    width: margin * 2 + (columns - 1) * xGap,
    height: margin * 2 + Math.max(0, Math.ceil(nodes.length / columns) - 1) * yGap,
  };
}

function applyGraphViewport() {
  const scale = clampGraphScale(state.graphScale);
  state.graphScale = scale;
  const { width: viewWidth, height: viewHeight } = graphViewSize(scale);
  const maxX = Math.max(0, state.graphViewportWidth - viewWidth);
  const maxY = Math.max(0, state.graphViewportHeight - viewHeight);
  state.graphPanX = Math.max(0, Math.min(state.graphPanX, maxX));
  state.graphPanY = Math.max(0, Math.min(state.graphPanY, maxY));
  elements.graphCanvas.setAttribute("viewBox", `${state.graphPanX} ${state.graphPanY} ${viewWidth} ${viewHeight}`);
}

function adjustGraphZoom(delta) {
  state.graphScale += delta;
  applyGraphViewport();
}

function zoomGraphAt(scale, anchor) {
  const nextScale = clampGraphScale(scale);
  if (nextScale === state.graphScale) {
    return;
  }

  if (anchor) {
    const nextViewSize = graphViewSize(nextScale);
    state.graphPanX = anchor.graphX - (anchor.relativeX / anchor.rect.width) * nextViewSize.width;
    state.graphPanY = anchor.graphY - (anchor.relativeY / anchor.rect.height) * nextViewSize.height;
  }
  state.graphScale = nextScale;
  applyGraphViewport();
}

function handleGraphWheel(event) {
  if (elements.graphEmpty.hidden === false) {
    return;
  }
  event.preventDefault();
  const anchor = graphPointFromEvent(event);
  const direction = event.deltaY < 0 ? 1 : -1;
  zoomGraphAt(state.graphScale + direction * 0.16, anchor);
}

function panGraph(dx, dy) {
  const step = 60 / state.graphScale;
  state.graphPanX += dx * step;
  state.graphPanY += dy * step;
  applyGraphViewport();
}

function resetGraphViewport() {
  state.graphScale = 1;
  state.graphPanX = 0;
  state.graphPanY = 0;
  applyGraphViewport();
}

function startGraphDrag(event) {
  if (event.button !== 0 || elements.graphEmpty.hidden === false) {
    return;
  }
  const rect = elements.graphCanvas.getBoundingClientRect();
  if (rect.width <= 0 || rect.height <= 0) {
    return;
  }
  state.graphDrag = {
    pointerId: event.pointerId,
    startClientX: event.clientX,
    startClientY: event.clientY,
    previousClientX: event.clientX,
    previousClientY: event.clientY,
    moved: false,
  };
  elements.graphCanvas.setPointerCapture(event.pointerId);
  elements.graphCanvas.classList.add("is-dragging");
}

function moveGraphDrag(event) {
  const drag = state.graphDrag;
  if (!drag || drag.pointerId !== event.pointerId) {
    return;
  }
  const rect = elements.graphCanvas.getBoundingClientRect();
  if (rect.width <= 0 || rect.height <= 0) {
    return;
  }
  const viewSize = graphViewSize();
  const deltaX = event.clientX - drag.previousClientX;
  const deltaY = event.clientY - drag.previousClientY;
  state.graphPanX -= (deltaX / rect.width) * viewSize.width;
  state.graphPanY -= (deltaY / rect.height) * viewSize.height;
  drag.previousClientX = event.clientX;
  drag.previousClientY = event.clientY;
  drag.moved = drag.moved || Math.hypot(event.clientX - drag.startClientX, event.clientY - drag.startClientY) > 3;
  if (drag.moved) {
    event.preventDefault();
  }
  applyGraphViewport();
}

function endGraphDrag(event) {
  const drag = state.graphDrag;
  if (!drag || drag.pointerId !== event.pointerId) {
    return;
  }
  state.graphSuppressClick = drag.moved;
  state.graphDrag = null;
  elements.graphCanvas.classList.remove("is-dragging");
  if (elements.graphCanvas.hasPointerCapture(event.pointerId)) {
    elements.graphCanvas.releasePointerCapture(event.pointerId);
  }
  if (state.graphSuppressClick) {
    window.setTimeout(() => {
      state.graphSuppressClick = false;
    }, 0);
  }
}

function renderSelectedNode(node) {
  if (!node) {
    elements.graphSelected.textContent = "Select a node to inspect it.";
    return;
  }

  const fields = [
    ["Kind", nodeKind(node)],
    ["Path", nodePath(node)],
    ["ID", node.id || "unknown"],
    ["Language", node.language],
    ["Role", node.role],
    ["Children", node.child_count],
    ["Issues", node.issue_count],
    ["Degree", node.degree],
  ];
  elements.graphSelected.textContent = fields
    .filter(([, value]) => value !== undefined && value !== null && value !== "")
    .map(([label, value]) => `${label}: ${value}`)
    .join("\n");
}

function selectGraphNode(nodeId) {
  state.selectedGraphNodeId = nodeId;
  renderGraphVisualization(state.graphData);
}

function renderGraphVisualization(data) {
  const graph = normalizeGraphData(data);
  const nodes = graph.nodes.filter((node) => node && node.id);
  const nodeIds = new Set(nodes.map((node) => node.id));
  const edges = graph.edges.filter((edge) => nodeIds.has(edge?.source) && nodeIds.has(edge?.target));
  const selectedNode = nodes.find((node) => node.id === state.selectedGraphNodeId) || null;

  elements.graphCanvas.replaceChildren();
  elements.graphEmpty.hidden = nodes.length > 0;
  renderSelectedNode(selectedNode);

  if (nodes.length === 0) {
    state.selectedGraphNodeId = null;
    elements.graphCanvas.removeAttribute("viewBox");
    elements.graphCanvas.style.minWidth = "";
    elements.graphCanvas.style.height = "";
    return;
  }

  if (!selectedNode) {
    state.selectedGraphNodeId = null;
  }

  const orderedNodes = [...nodes].sort((left, right) => {
    const kindSort = nodeKind(left).localeCompare(nodeKind(right));
    return kindSort || nodePath(left).localeCompare(nodePath(right));
  });
  const { positions, width, height } = graphLayout(orderedNodes);
  const canvasWidth = Math.max(width, 520);
  const canvasHeight = Math.max(height + 48, 320);
  state.graphViewportWidth = canvasWidth;
  state.graphViewportHeight = canvasHeight;
  elements.graphCanvas.style.minWidth = `${canvasWidth}px`;
  elements.graphCanvas.style.height = `${canvasHeight}px`;

  const edgeLayer = createSvgElement("g", { class: "graph-edges" });
  edges.forEach((edge) => {
    const source = positions.get(edge.source);
    const target = positions.get(edge.target);
    if (!source || !target) {
      return;
    }
    const isSelected = edge.source === state.selectedGraphNodeId || edge.target === state.selectedGraphNodeId;
    edgeLayer.append(
      createSvgElement("line", {
        class: `graph-edge${isSelected ? " is-selected" : ""}`,
        x1: source.x,
        y1: source.y,
        x2: target.x,
        y2: target.y,
      }),
    );
  });
  elements.graphCanvas.append(edgeLayer);

  const nodeLayer = createSvgElement("g", { class: "graph-nodes" });
  orderedNodes.forEach((node) => {
    const position = positions.get(node.id);
    const kind = nodeKind(node);
    const isSelected = node.id === state.selectedGraphNodeId;
    const group = createSvgElement("g", {
      class: `graph-node graph-node-${kind}${isSelected ? " is-selected" : ""}`,
      tabindex: "0",
      role: "button",
      "aria-label": `${kind} ${nodePath(node)}`,
    });
    group.addEventListener("click", (event) => {
      if (state.graphSuppressClick) {
        event.preventDefault();
        return;
      }
      selectGraphNode(node.id);
    });
    group.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectGraphNode(node.id);
      }
    });

    if (kind === "folder") {
      group.append(createSvgElement("rect", { x: position.x - 34, y: position.y - 21, width: 68, height: 42, rx: 6 }));
    } else {
      group.append(createSvgElement("circle", { cx: position.x, cy: position.y, r: 23 }));
    }
    const text = createSvgElement("text", { x: position.x, y: position.y + 39, "text-anchor": "middle" });
    text.textContent = nodeLabel(node).slice(0, 22);
    group.append(text);
    nodeLayer.append(group);
  });
  elements.graphCanvas.append(nodeLayer);
  applyGraphViewport();
}

function renderGraphData(data) {
  const graph = normalizeGraphData(data);
  state.graphData = graph;
  if (!graph.nodes.some((node) => node?.id === state.selectedGraphNodeId)) {
    state.selectedGraphNodeId = null;
  }
  renderJson(elements.graphView, data ?? {});
  renderGraphVisualization(graph);
}

async function optionalGraph(path, emptyMessage) {
  try {
    const data = await requestJson(path);
    renderGraphData(data ?? {});
  } catch (error) {
    elements.graphView.textContent = emptyMessage;
    state.graphData = normalizeGraphData({});
    state.selectedGraphNodeId = null;
    renderGraphVisualization(state.graphData);
  }
}

function renderTimelineData(data) {
  const commits = Array.isArray(data) ? data : [];
  state.gitTimeline = commits;
  renderJson(elements.gitTimeline, data ?? []);
  updateTimelineSelection();
  if (commits.length === 0) {
    setEmpty(elements.gitTimelineList, "Git timeline data will appear here.");
    return;
  }

  elements.gitTimelineList.replaceChildren();
  commits.forEach((commit) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = `timeline-item${commit.commit_hash === state.selectedCommitHash ? " is-selected" : ""}`;
    item.title = commit.commit_hash || "";
    if (commit.commit_hash === state.selectedCommitHash) {
      item.setAttribute("aria-current", "true");
    }

    const title = document.createElement("span");
    title.className = "timeline-title";
    title.textContent = `${commit.short_hash || "commit"} ${commit.message || "(no message)"}`;

    const selectedLabel = document.createElement("span");
    selectedLabel.className = "timeline-selected-label";
    selectedLabel.textContent = "Selected";
    selectedLabel.hidden = commit.commit_hash !== state.selectedCommitHash;

    const meta = document.createElement("span");
    meta.className = "timeline-meta";
    meta.textContent = `${formatDate(commit.date)} | ${commit.author || "unknown author"} | ${commit.changed_files_count ?? 0} file(s)`;

    item.append(title, selectedLabel, meta);
    item.addEventListener("click", async () => {
      state.selectedCommitHash = commit.commit_hash;
      elements.diffHash.value = commit.commit_hash || "";
      updateTimelineSelection();
      await loadDiff();
    });
    elements.gitTimelineList.append(item);
  });
  updateTimelineSelection();
}

function updateTimelineSelection() {
  const selected = state.gitTimeline.find((commit) => commit.commit_hash === state.selectedCommitHash);
  if (!state.selectedCommitHash) {
    elements.gitSelectedState.textContent = "No commit selected.";
  } else if (selected) {
    elements.gitSelectedState.textContent = `Selected ${selected.short_hash || shortCommitHash(selected.commit_hash)}: ${selected.message || "(no message)"}`;
  } else {
    elements.gitSelectedState.textContent = `Selected ${shortCommitHash(state.selectedCommitHash)}.`;
  }

  elements.gitTimelineList.querySelectorAll(".timeline-item").forEach((item) => {
    const isSelected = item.title === state.selectedCommitHash;
    item.classList.toggle("is-selected", isSelected);
    if (isSelected) {
      item.setAttribute("aria-current", "true");
    } else {
      item.removeAttribute("aria-current");
    }
    const selectedLabel = item.querySelector(".timeline-selected-label");
    if (selectedLabel) {
      selectedLabel.hidden = !isSelected;
    }
  });
}

function resetDiffPresentation(message = "No diff selected.") {
  elements.gitDiffSummary.textContent = message;
  elements.gitDiffHunks.replaceChildren();
  elements.gitDiffHunks.hidden = true;
  elements.gitDiffView.classList.remove("is-truncated");
}

async function optionalTimeline(path, emptyMessage) {
  try {
    const data = await requestJson(path);
    renderTimelineData(data ?? []);
  } catch (error) {
    elements.gitTimeline.textContent = emptyMessage;
    setEmpty(elements.gitTimelineList, emptyMessage);
  }
}

function renderDiffData(data) {
  renderJson(elements.gitDiff, data ?? {});
  const diffText = data?.diff_text;
  resetDiffPresentation();
  if (!diffText) {
    setEmpty(elements.gitDiffView, "Diff API data will appear here.");
    return;
  }

  elements.gitDiffView.replaceChildren();
  const lines = diffText.split("\n");
  const hunkButtons = [];
  elements.gitDiffView.classList.toggle("is-truncated", Boolean(data.truncated));
  elements.gitDiffSummary.textContent = `${lines.length} diff line(s) for ${shortCommitHash(data.commit_hash || state.selectedCommitHash)}${data.truncated ? `, truncated at ${data.max_bytes} bytes` : ""}.`;

  if (data.truncated) {
    const banner = document.createElement("div");
    banner.className = "diff-truncated-banner";
    banner.textContent = `Truncated diff: showing the first ${data.max_bytes} bytes.`;
    elements.gitDiffView.append(banner);
  }

  lines.forEach((line, index) => {
    const row = document.createElement("span");
    row.className = "diff-line";
    if (line.startsWith("+++") || line.startsWith("---") || line.startsWith("diff --git")) {
      row.classList.add("diff-line-header");
    } else if (line.startsWith("@@")) {
      row.classList.add("diff-line-hunk");
      row.id = `diff-hunk-${hunkButtons.length + 1}`;
      row.textContent = line || " ";
      const button = document.createElement("button");
      button.type = "button";
      button.className = "diff-hunk-button";
      button.textContent = `Hunk ${hunkButtons.length + 1}`;
      button.title = line;
      button.addEventListener("click", () => row.scrollIntoView({ block: "nearest" }));
      hunkButtons.push(button);
    } else if (line.startsWith("+")) {
      row.classList.add("diff-line-added");
    } else if (line.startsWith("-")) {
      row.classList.add("diff-line-removed");
    }
    if (!row.textContent) {
      row.textContent = line || " ";
    }
    row.setAttribute("data-line-number", String(index + 1));
    elements.gitDiffView.append(row);
  });

  if (hunkButtons.length) {
    elements.gitDiffHunks.hidden = false;
    elements.gitDiffHunks.append(...hunkButtons);
  }

  if (data.truncated) {
    const note = document.createElement("span");
    note.className = "diff-line diff-line-truncated";
    note.textContent = `Diff truncated at ${data.max_bytes} bytes.`;
    elements.gitDiffView.append(note);
  }
}

async function optionalDiff(path, emptyMessage) {
  try {
    const data = await requestJson(path);
    renderDiffData(data ?? {});
  } catch (error) {
    elements.gitDiff.textContent = emptyMessage;
    resetDiffPresentation(emptyMessage);
    setEmpty(elements.gitDiffView, emptyMessage);
  }
}

function renderProjectStatus(data) {
  state.currentProject = data?.project || null;
  if (!state.currentProject) {
    elements.statusProject.textContent = "No project open";
    elements.statusCache.textContent = "Unavailable";
    elements.statusGit.textContent = "Unknown";
    return;
  }

  elements.statusProject.textContent = `${state.currentProject.display_name} (${state.currentProject.path})`;
  elements.statusCache.textContent = data.cache?.project_dir || "Unavailable";
  elements.statusGit.textContent = state.currentProject.is_git_repo ? "Git repository" : "Not a Git repository";
}

async function refreshStatus() {
  try {
    await requestJson("/api/app/status");
    elements.serverStatus.textContent = "Online";
    const current = await requestJson("/api/project/current");
    renderProjectStatus(current);
  } catch (error) {
    elements.serverStatus.textContent = "Offline";
    showNotice(error.message);
  }
}

async function openProject() {
  const path = elements.projectPath.value.trim();
  if (!path) {
    showNotice("Enter a project path first.");
    return;
  }

  elements.openProject.disabled = true;
  try {
    const data = await requestJson("/api/project/open", {
      method: "POST",
      body: JSON.stringify({ path }),
    });
    renderProjectStatus(data);
    showNotice("Project opened.");
    await refreshDataViews();
  } catch (error) {
    showNotice(error.message);
  } finally {
    elements.openProject.disabled = false;
  }
}

async function rescanProject() {
  elements.rescanProject.disabled = true;
  try {
    const data = await requestJson("/api/project/rescan", { method: "POST", body: "{}" });
    showNotice("Rescan complete.");
    if (data?.graph_data) {
      renderGraphData(data.graph_data);
    }
    await refreshDataViews();
  } catch (error) {
    showNotice(`Rescan unavailable: ${error.message}`);
  } finally {
    elements.rescanProject.disabled = false;
  }
}

async function shutdownApp() {
  elements.shutdownApp.disabled = true;
  try {
    await requestJson("/api/app/shutdown", { method: "POST", body: "{}" });
    elements.serverStatus.textContent = "Shutting down";
    showNotice("Server shutdown requested.");
  } catch (error) {
    showNotice(error.message);
    elements.shutdownApp.disabled = false;
  }
}

async function refreshDataViews() {
  await Promise.all([
    optionalFileTree("/api/files/tree", "File tree API is not available yet."),
    optionalGraph("/api/graph/data", "Graph data API is not available yet."),
    optionalTimeline("/api/git/timeline", "Git timeline API is not available yet."),
  ]);
}

async function loadFileDetail() {
  const path = elements.detailPath.value.trim();
  if (!path) {
    showNotice("Enter a project-relative file path.");
    return;
  }
  await optionalJson(`/api/files/detail?path=${encodeURIComponent(path)}`, elements.fileDetail, "File detail API is not available yet.");
}

async function loadDiff() {
  const hash = elements.diffHash.value.trim();
  if (!hash) {
    showNotice("Enter a commit hash.");
    return;
  }
  state.selectedCommitHash = hash;
  updateTimelineSelection();
  await optionalDiff(`/api/git/diff?hash=${encodeURIComponent(hash)}`, "Diff API is not available yet.");
}

elements.openProject.addEventListener("click", openProject);
elements.rescanProject.addEventListener("click", rescanProject);
elements.shutdownApp.addEventListener("click", shutdownApp);
elements.refreshTree.addEventListener("click", () => optionalFileTree("/api/files/tree", "File tree API is not available yet."));
elements.fileTreeFilter.addEventListener("input", () => {
  state.fileTreeFilter = elements.fileTreeFilter.value;
  renderFilteredFileTree();
});
elements.clearTreeFilter.addEventListener("click", () => {
  state.fileTreeFilter = "";
  elements.fileTreeFilter.value = "";
  renderFilteredFileTree();
});
elements.refreshTimeline.addEventListener("click", () => optionalTimeline("/api/git/timeline", "Git timeline API is not available yet."));
elements.loadDetail.addEventListener("click", loadFileDetail);
elements.loadDiff.addEventListener("click", loadDiff);
elements.graphZoomOut.addEventListener("click", () => adjustGraphZoom(-0.2));
elements.graphZoomIn.addEventListener("click", () => adjustGraphZoom(0.2));
elements.graphPanLeft.addEventListener("click", () => panGraph(-1, 0));
elements.graphPanUp.addEventListener("click", () => panGraph(0, -1));
elements.graphPanDown.addEventListener("click", () => panGraph(0, 1));
elements.graphPanRight.addEventListener("click", () => panGraph(1, 0));
elements.graphResetView.addEventListener("click", resetGraphViewport);
elements.graphCanvas.addEventListener("wheel", handleGraphWheel, { passive: false });
elements.graphCanvas.addEventListener("pointerdown", startGraphDrag);
elements.graphCanvas.addEventListener("pointermove", moveGraphDrag);
elements.graphCanvas.addEventListener("pointerup", endGraphDrag);
elements.graphCanvas.addEventListener("pointercancel", endGraphDrag);

refreshStatus();
refreshDataViews();
