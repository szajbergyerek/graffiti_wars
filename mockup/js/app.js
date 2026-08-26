// Graffiti Wars - shared UI helpers for the static mockup (no real backend calls here)

function toggleModal(id) {
  const el = document.getElementById(id);
  if (el) {
    el.classList.toggle("open");
  }
}

function switchTab(groupName, tabName) {
  document.querySelectorAll(`[data-tab-group="${groupName}"]`).forEach((el) => {
    el.classList.toggle("active", el.dataset.tab === tabName);
  });
  document.querySelectorAll(`[data-tab-panel-group="${groupName}"]`).forEach((el) => {
    el.style.display = el.dataset.tabPanel === tabName ? "block" : "none";
  });
}

// Mock band territories around a sample city center, used on map.html and index.html preview.
// In the real app these polygons come from the grid-based influence field computed server-side.
const MOCK_CENTER = [47.4979, 19.0402];

const MOCK_TERRITORIES = [
  {
    band: "Nitro Kings",
    color: "#ff2e6c",
    points: [
      [47.5010, 19.0350], [47.5025, 19.0400], [47.5005, 19.0440],
      [47.4980, 19.0420], [47.4985, 19.0365],
    ],
  },
  {
    band: "Cyan Ghosts",
    color: "#00e0d1",
    points: [
      [47.4950, 19.0470], [47.4965, 19.0520], [47.4935, 19.0545],
      [47.4915, 19.0500],
    ],
  },
  {
    band: "Yellow Vandals",
    color: "#ffcc00",
    points: [
      [47.5040, 19.0470], [47.5060, 19.0510], [47.5030, 19.0530],
      [47.5015, 19.0495],
    ],
  },
  {
    band: "Purple Reign",
    color: "#8c52ff",
    points: [
      [47.4940, 19.0330], [47.4955, 19.0360], [47.4930, 19.0390],
      [47.4910, 19.0355],
    ],
  },
];

const MOCK_TAG_POINTS = [
  { lat: 47.5000, lon: 19.0390, band: "Nitro Kings" },
  { lat: 47.4990, lon: 19.0410, band: "Nitro Kings" },
  { lat: 47.4945, lon: 19.0510, band: "Cyan Ghosts" },
  { lat: 47.5045, lon: 19.0500, band: "Yellow Vandals" },
  { lat: 47.4935, lon: 19.0360, band: "Purple Reign" },
];

function initMockMap(elementId, options = {}) {
  const el = document.getElementById(elementId);
  if (!el || typeof L === "undefined") return;

  const map = L.map(elementId, {
    zoomControl: options.zoomControl !== false,
    scrollWheelZoom: options.interactive !== false,
    dragging: options.interactive !== false,
    doubleClickZoom: options.interactive !== false,
    boxZoom: options.interactive !== false,
    keyboard: options.interactive !== false,
  }).setView(MOCK_CENTER, options.zoom || 14);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    className: "map-tiles-dark",
  }).addTo(map);

  MOCK_TERRITORIES.forEach((t) => {
    L.polygon(t.points, {
      color: t.color,
      weight: 2,
      fillColor: t.color,
      fillOpacity: 0.28,
    })
      .addTo(map)
      .bindPopup(`<strong>${t.band}</strong> territoriuma`);
  });

  MOCK_TAG_POINTS.forEach((p) => {
    L.circleMarker([p.lat, p.lon], {
      radius: 6,
      color: "#fff",
      weight: 2,
      fillColor: "#fff",
      fillOpacity: 0.9,
    })
      .addTo(map)
      .bindPopup(`Hitelesitett tag - ${p.band}`);
  });

  return map;
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-init-map]").forEach((el) => {
    initMockMap(el.id, {
      interactive: el.dataset.interactive !== "false",
      zoom: el.dataset.zoom ? parseInt(el.dataset.zoom, 10) : 14,
    });
  });
});
