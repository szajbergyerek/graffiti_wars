// Graffiti Wars - client-side helpers backed by the real /api endpoints

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text == null ? "" : String(text);
  return div.innerHTML;
}

function toggleModal(id) {
  const el = document.getElementById(id);
  if (el) {
    el.classList.toggle("open");
  }
}

function autoHideFlashes() {
  document.querySelectorAll(".flash").forEach((el) => {
    setTimeout(() => {
      el.classList.add("flash-hide");
      setTimeout(() => el.remove(), 500);
    }, 4000);
  });
}

function styleTerritoryFeature(feature) {
  return {
    color: feature.properties.color,
    weight: 2,
    fillColor: feature.properties.color,
    fillOpacity: 0.28,
  };
}

function filterFeatures(featureCollection, bandId) {
  if (!bandId) return featureCollection;
  return {
    type: "FeatureCollection",
    features: featureCollection.features.filter((f) => f.properties.band_id === bandId),
  };
}

function initLiveMap(elementId, options = {}) {
  const el = document.getElementById(elementId);
  if (!el || typeof L === "undefined") return null;

  const map = L.map(elementId, {
    zoomControl: options.interactive !== false,
    scrollWheelZoom: options.interactive !== false,
    dragging: options.interactive !== false,
    doubleClickZoom: options.interactive !== false,
    boxZoom: options.interactive !== false,
    keyboard: options.interactive !== false,
  }).setView(options.center || [47.4979, 19.0402], options.zoom || 13);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 19,
  }).addTo(map);

  let tagsLayer = null;

  function currentBboxParam() {
    const bounds = map.getBounds();
    return [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()].join(",");
  }

  function loadTags() {
    let url = "/api/tags.geojson";
    if (options.viewportFiltered) {
      url += `?bbox=${encodeURIComponent(currentBboxParam())}`;
    }
    fetch(url)
      .then((r) => r.json())
      .then((data) => {
        const filtered = filterFeatures(data, options.bandFilter);

        if (tagsLayer) {
          map.removeLayer(tagsLayer);
        }
        tagsLayer = L.geoJSON(filtered, {
          pointToLayer: (feature, latlng) =>
            L.circleMarker(latlng, {
              radius: 6,
              color: "#fff",
              weight: 2,
              fillColor: feature.properties.color,
              fillOpacity: 0.95,
            }),
          onEachFeature: (feature, featureLayer) => {
            featureLayer.bindPopup(
              `<strong>${escapeHtml(feature.properties.band_name)}</strong><br/>` +
                `<img src="${escapeHtml(feature.properties.photo_url)}" style="width:120px;border-radius:6px;margin-top:6px" />`
            );
          },
        }).addTo(map);

        if (options.onTagsUpdate) {
          const visibleBandIds = new Set(filtered.features.map((f) => f.properties.band_id));
          options.onTagsUpdate(visibleBandIds);
        }
      });
  }

  fetch("/api/territories.geojson")
    .then((r) => r.json())
    .then((data) => {
      const filtered = filterFeatures(data, options.bandFilter);
      const layer = L.geoJSON(filtered, {
        style: styleTerritoryFeature,
        onEachFeature: (feature, featureLayer) => {
          featureLayer.bindPopup(
            `<strong>${escapeHtml(feature.properties.band_name)}</strong><br/>${feature.properties.area_km2} km2`
          );
        },
      }).addTo(map);

      if (options.bandFilter && filtered.features.length && layer.getBounds().isValid()) {
        map.fitBounds(layer.getBounds(), { padding: [30, 30] });
      }

      if (options.onTerritoriesLoaded) {
        options.onTerritoriesLoaded(filtered.features.map((f) => f.properties));
      }
    });

  if (options.showTags !== false) {
    loadTags();
    if (options.viewportFiltered) {
      map.on("moveend", loadTags);
    }
  }

  return map;
}

function initLocationPicker(mapElementId, latInputId, lonInputId, onSet) {
  const map = initLiveMap(mapElementId, { interactive: true, zoom: 14, showTags: false });
  if (!map) return;

  const latInput = document.getElementById(latInputId);
  const lonInput = document.getElementById(lonInputId);
  let marker = null;

  function setLocation(lat, lon) {
    latInput.value = lat.toFixed(6);
    lonInput.value = lon.toFixed(6);
    if (marker) {
      marker.setLatLng([lat, lon]);
    } else {
      marker = L.marker([lat, lon]).addTo(map);
    }
    if (onSet) onSet(lat, lon);
  }

  map.on("click", (e) => setLocation(e.latlng.lat, e.latlng.lng));

  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition((pos) => {
      map.setView([pos.coords.latitude, pos.coords.longitude], 16);
      setLocation(pos.coords.latitude, pos.coords.longitude);
    });
  }
}

function appendChatMessage(container, message) {
  const bubble = document.createElement("div");
  bubble.className = "chat-bubble" + (message.is_own ? " own" : "");
  bubble.dataset.messageId = message.id;

  const meta = document.createElement("div");
  meta.className = "meta";
  meta.textContent = `${message.sender} - ${message.created_at}`;

  const body = document.createElement("div");
  body.textContent = message.body;

  bubble.appendChild(meta);
  bubble.appendChild(body);
  container.appendChild(bubble);
}

function initChatPolling(conversationId, sendUrl, messagesUrl) {
  const container = document.getElementById("chatMessages");
  const form = document.getElementById("chatForm");
  const input = document.getElementById("chatInput");
  if (!container || !form || !input) return;

  function lastMessageId() {
    let max = 0;
    container.querySelectorAll("[data-message-id]").forEach((bubble) => {
      const id = parseInt(bubble.dataset.messageId, 10);
      if (id > max) max = id;
    });
    return max;
  }

  function scrollToBottom() {
    container.scrollTop = container.scrollHeight;
  }

  function poll() {
    fetch(`${messagesUrl}?after=${lastMessageId()}`)
      .then((r) => r.json())
      .then((messages) => {
        if (!messages.length) return;
        const emptyNotice = container.querySelector("p");
        if (emptyNotice) emptyNotice.remove();
        messages.forEach((message) => appendChatMessage(container, message));
        scrollToBottom();
      });
  }

  scrollToBottom();
  const pollInterval = setInterval(poll, 3000);
  window.addEventListener("beforeunload", () => clearInterval(pollInterval));

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const body = input.value.trim();
    if (!body) return;
    input.value = "";
    fetch(sendUrl, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: `body=${encodeURIComponent(body)}`,
    }).then(poll);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  autoHideFlashes();

  const navToggle = document.getElementById("navToggle");
  const navLinks = document.getElementById("navLinks");
  if (navToggle && navLinks) {
    navToggle.addEventListener("click", () => {
      navLinks.classList.toggle("open");
      navToggle.classList.toggle("open");
    });
    navLinks.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        navLinks.classList.remove("open");
        navToggle.classList.remove("open");
      });
    });
  }

  document.querySelectorAll("[data-init-map]").forEach((el) => {
    initLiveMap(el.id, {
      interactive: el.dataset.interactive !== "false",
      zoom: el.dataset.zoom ? parseInt(el.dataset.zoom, 10) : 13,
      bandFilter: el.dataset.bandFilter ? parseInt(el.dataset.bandFilter, 10) : null,
    });
  });
});
