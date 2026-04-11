async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load ${url}: ${response.status}`);
  }
  return response.json();
}

function setText(id, value) {
  const node = document.getElementById(id);
  if (node) node.textContent = value;
}

function renderMatrix(items) {
  const body = document.getElementById("matrixBody");
  body.innerHTML = "";

  for (const item of items) {
    const tr = document.createElement("tr");
    const gaps = item.gaps && item.gaps.length ? item.gaps.join(" | ") : "none";

    tr.innerHTML = `
      <td>${item.track}</td>
      <td>${item.component}</td>
      <td class="status status-${item.status}">${item.status}</td>
      <td>${item.severity}</td>
      <td>${gaps}</td>
    `;
    body.appendChild(tr);
  }
}

function renderRiskList(items) {
  const riskList = document.getElementById("riskList");
  riskList.innerHTML = "";

  const risky = items.filter((item) => item.severity === "critical" || item.severity === "high");
  if (!risky.length) {
    const li = document.createElement("li");
    li.textContent = "No critical/high verification gaps currently open.";
    riskList.appendChild(li);
    return;
  }

  for (const item of risky) {
    const li = document.createElement("li");
    li.textContent = `${item.component}: ${item.gaps.join("; ")}`;
    riskList.appendChild(li);
  }
}

function formatPct(value) {
  return `${(value * 100).toFixed(2)}%`;
}

async function loadTerminal() {
  try {
    const [audit, tests, slo] = await Promise.all([
      fetchJson("/implementation/audit"),
      fetchJson("/implementation/test-results"),
      fetchJson("/slo/status"),
    ]);

    setText("implementedCount", audit.counts.implemented ?? "0");
    setText("partialCount", audit.counts.partial ?? "0");
    setText("criticalCount", audit.severity_counts.critical ?? "0");
    setText("highCount", audit.severity_counts.high ?? "0");
    setText("generatedAt", `Audit timestamp: ${audit.generated_at}`);

    setText("availabilityVal", formatPct(slo.availability));
    setText("latencyVal", `${slo.p95_latency_ms.toFixed(1)} ms`);
    setText("windowVal", `${slo.window_minutes} min`);

    setText("unitResult", tests.unit.trim());
    setText("realResult", tests.realdata.trim());

    renderMatrix(audit.items || []);
    renderRiskList(audit.items || []);
  } catch (error) {
    console.error(error);
    setText("unitResult", `UI load failed: ${error.message}`);
    setText("realResult", "Unable to load real-data verification output.");
  }
}

loadTerminal();
