function $(id) {
    return document.getElementById(id);
}

function showError(msg) {
    const box = $("errorBox");
    box.textContent = msg;
    box.style.display = "block";
    $("okBox").style.display = "none";
}

function showOk(msg) {
    const box = $("okBox");
    box.textContent = msg;
    box.style.display = "block";
    $("errorBox").style.display = "none";
}

function setStatus(text) {
    const pill = $("statusPill");
    if (!text) {
        pill.style.display = "none";
        pill.textContent = "";
        return;
    }
    pill.style.display = "inline-block";
    pill.textContent = text;
}

function clearMessages() {
    $("errorBox").style.display = "none";
    $("okBox").style.display = "none";
    setStatus("");
}

async function fetchJson(url) {
    const resp = await fetch(url, {headers: {"Accept": "application/json"}});
    let body = null;
    try {
        body = await resp.json();
    } catch (e) {
        body = null;
    }

    if (!resp.ok) {
        const detail = body && body.detail ? body.detail : `HTTP ${resp.status}`;
        throw new Error(detail);
    }
    return body;
}

function renderGeocodeResults(results) {
    const root = $("geocodeResults");
    root.innerHTML = "";

    if (!results || results.length === 0) {
        root.innerHTML = `<div class="muted">No results</div>`;
        return;
    }

    const wrap = document.createElement("div");
    wrap.className = "radio-list";

    results.forEach((p, idx) => {
        const item = document.createElement("div");
        item.className = "radio-item";

        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = "geocodeCandidate";
        radio.value = String(idx);

        const label = document.createElement("label");
        label.style.margin = "0";
        label.style.cursor = "pointer";
        label.innerHTML = `<div><strong>${p.display_name}</strong></div>
      <div class="muted">lat=${p.lat}, lon=${p.lon}${p.country ? `, ${p.country}` : ""}</div>`;

        radio.addEventListener("change", () => {
            $("lat").value = String(p.lat);
            $("lon").value = String(p.lon);
            showOk("Coordinates filled from place search");
        });

        item.appendChild(radio);
        item.appendChild(label);
        wrap.appendChild(item);
    });

    root.appendChild(wrap);
}

function renderForecast(data) {
    const out = $("forecastOut");
    out.innerHTML = "";

    const loc = data.location || {};
    const days = data.days || [];

    const locHtml = `
    <div class="card">
      <h3 style="margin:0 0 8px; font-size: 15px;">Location used</h3>
      <div><strong>lat</strong>: ${loc.lat}, <strong>lon</strong>: ${loc.lon}</div>
      <div><strong>tz</strong>: ${loc.timezone}, <strong>at</strong>: ${loc.target_time}</div>
      ${loc.place_name ? `<div style="margin-top:6px;"><strong>place</strong>: ${loc.place_name}</div>` : ""}
      ${(loc.city || loc.country) ? `<div class="muted">${loc.city ? loc.city : ""}${loc.city && loc.country ? ", " : ""}${loc.country ? loc.country : ""}</div>` : ""}
    </div>
  `;

    let tableHtml = "";
    if (days.length === 0) {
        tableHtml = `<div class="muted">No forecast points available</div>`;
    } else {
        const rows = days.map(d => `
      <tr>
        <td>${d.date}</td>
        <td>${d.time}</td>
        <td>${d.temperature_c}</td>
      </tr>
    `).join("");

        tableHtml = `
      <div class="card">
        <h3 style="margin:0 0 8px; font-size: 15px;">Forecast</h3>
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Local time</th>
              <th>Temp (C)</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
    }

    out.innerHTML = locHtml + tableHtml;
}

async function onSearch() {
    clearMessages();
    const q = $("place").value.trim();
    if (q.length < 2) {
        showError("Place query must be at least 2 characters");
        return;
    }

    setStatus("Searching...");
    try {
        const url = `/v1/geocode?q=${encodeURIComponent(q)}&limit=5`;
        const data = await fetchJson(url);
        renderGeocodeResults(data.results || []);
        showOk("Select a candidate to fill coordinates");
    } catch (e) {
        showError(`Geocode failed: ${e.message}`);
    } finally {
        setStatus("");
    }
}

async function onForecast() {
    clearMessages();

    const tz = $("tz").value.trim() || "Europe/Belgrade";
    const at = $("at").value.trim() || "14:00";
    const includePlace = $("includePlace").checked;

    const lat = $("lat").value.trim();
    const lon = $("lon").value.trim();

    const params = new URLSearchParams();
    params.set("tz", tz);
    params.set("at", at);
    params.set("include_place", includePlace ? "true" : "false");

    if (lat && lon) {
        params.set("lat", lat);
        params.set("lon", lon);
    }

    setStatus("Loading forecast...");
    try {
        const data = await fetchJson(`/v1/forecast?${params.toString()}`);
        renderForecast(data);
        showOk("Done");
    } catch (e) {
        showError(`Forecast failed: ${e.message}`);
    } finally {
        setStatus("");
    }
}

function onClearPlace() {
    $("place").value = "";
    $("geocodeResults").innerHTML = "";
    clearMessages();
}

document.addEventListener("DOMContentLoaded", () => {
    $("btnSearch").addEventListener("click", onSearch);
    $("btnForecast").addEventListener("click", onForecast);
    $("btnClearPlace").addEventListener("click", onClearPlace);
});
