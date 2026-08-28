// Graffiti Wars - client-side helpers backed by the real /api endpoints

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text == null ? "" : String(text);
  return div.innerHTML;
}

function initInfiniteList(options) {
  const {
    container,
    scrollParent = document.querySelector(".app-content"),
    fetchPage,
    renderItem,
    pageSize = 10,
    emptyMessage = "",
  } = options;

  let offset = 0;
  let loading = false;
  let exhausted = false;
  let firstLoad = true;
  let destroyed = false;

  const spinner = document.createElement("div");
  spinner.className = "infinite-scroll-spinner";
  spinner.innerHTML = '<div class="infinite-scroll-spinner-icon"></div>';
  spinner.style.display = "none";
  container.insertAdjacentElement("afterend", spinner);

  function currentScrollMetrics() {
    if (scrollParent) {
      return { top: scrollParent.scrollTop, height: scrollParent.scrollHeight, client: scrollParent.clientHeight };
    }
    return {
      top: window.scrollY,
      height: document.documentElement.scrollHeight,
      client: window.innerHeight,
    };
  }

  function loadNext() {
    if (loading || exhausted || destroyed) return;
    loading = true;
    spinner.style.display = "flex";

    fetchPage(offset, pageSize)
      .then((items) => {
        loading = false;
        spinner.style.display = "none";
        if (destroyed) return;

        if (firstLoad) {
          container.innerHTML = "";
          firstLoad = false;
        }

        if (!items || !items.length) {
          exhausted = true;
          if (offset === 0 && emptyMessage) {
            const empty = document.createElement("p");
            empty.className = "text-muted";
            empty.textContent = emptyMessage;
            container.appendChild(empty);
          }
          return;
        }

        items.forEach((item) => container.appendChild(renderItem(item)));
        offset += items.length;
        if (items.length < pageSize) exhausted = true;

        // If the page loaded fewer items than fit the viewport, immediately try the next page.
        requestAnimationFrame(checkScroll);
      })
      .catch(() => {
        loading = false;
        spinner.style.display = "none";
        exhausted = true;
      });
  }

  function checkScroll() {
    const { top, height, client } = currentScrollMetrics();
    if (top + client >= height - 200) {
      loadNext();
    }
  }

  const scrollTarget = scrollParent || window;
  scrollTarget.addEventListener("scroll", checkScroll);
  loadNext();

  return {
    reload: () => {
      offset = 0;
      exhausted = false;
      firstLoad = true;
      loadNext();
    },
    destroy: () => {
      destroyed = true;
      scrollTarget.removeEventListener("scroll", checkScroll);
      spinner.remove();
    },
  };
}

function initBottomSheet(handleEl, sheetEl, backdropEl, onToggle) {
  if (!handleEl || !sheetEl) return null;

  function setOpen(open) {
    sheetEl.classList.toggle("open", open);
    handleEl.classList.toggle("open", open);
    if (backdropEl) backdropEl.classList.toggle("open", open);
    if (onToggle) onToggle(open);
  }

  handleEl.addEventListener("click", () => {
    setOpen(!sheetEl.classList.contains("open"));
  });

  if (backdropEl) {
    backdropEl.addEventListener("click", () => setOpen(false));
  }

  return { setOpen, isOpen: () => sheetEl.classList.contains("open") };
}

function bandPinIcon(color) {
  const svg = `
    <svg width="17" height="22" viewBox="0 0 26 34" xmlns="http://www.w3.org/2000/svg">
      <ellipse cx="13" cy="32" rx="6" ry="1.6" fill="#000" opacity="0.35"/>
      <rect x="10" y="0" width="6" height="3.5" rx="1.2" fill="#e8e6ee"/>
      <rect x="8" y="3" width="10" height="4" rx="1.5" fill="#3a3a46"/>
      <rect x="5" y="7" width="16" height="23" rx="4" fill="${color}" stroke="#fff" stroke-width="1.6"/>
      <rect x="5" y="15" width="16" height="5" fill="#fff" opacity="0.22"/>
    </svg>
  `;
  return L.divIcon({
    html: svg,
    className: "band-pin-icon",
    iconSize: [17, 22],
    iconAnchor: [8, 21],
    popupAnchor: [0, -19],
  });
}

function initNationalityPreview(selectId, previewId) {
  const select = document.getElementById(selectId);
  const preview = document.getElementById(previewId);
  if (!select || !preview) return;

  function update() {
    const option = select.selectedOptions[0];
    const iconUrl = option ? option.dataset.flagIcon || "" : "";
    preview.innerHTML = iconUrl ? `<img class="flag-icon" src="${iconUrl}" alt="" />` : "";
  }

  select.addEventListener("change", update);
  update();
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
    zoomControl: options.zoomControl !== undefined ? options.zoomControl : options.interactive !== false,
    scrollWheelZoom: options.interactive !== false,
    dragging: options.interactive !== false,
    doubleClickZoom: options.interactive !== false,
    boxZoom: options.interactive !== false,
    keyboard: options.interactive !== false,
  }).setView(options.center || [47.4979, 19.0402], options.zoom || 13);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 19,
    className: "map-tiles-dark",
  }).addTo(map);

  const tagsLayerGroup = L.layerGroup().addTo(map);
  const tagMarkersById = new Map();
  let loadTagsDebounce = null;

  function currentBboxParam() {
    const bounds = map.getBounds();
    return [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()].join(",");
  }

  function makeTagMarker(feature) {
    const p = feature.properties;
    const [lon, lat] = feature.geometry.coordinates;
    const marker = L.marker([lat, lon], { icon: bandPinIcon(p.color) });
    const logLabel = (window.mapUiLabels && window.mapUiLabels.logButton) || "Log";
    marker.bindPopup(
      `<a href="/users/${encodeURIComponent(p.submitted_by)}" style="font-weight:700; display:block">${escapeHtml(p.submitted_by)}</a>` +
        `<a href="/bands/${p.band_id}" style="color:${escapeHtml(p.color)}; display:block; font-size:12px">${escapeHtml(p.band_name)}</a>` +
        `<a href="/tags/${p.id}"><img src="${escapeHtml(p.photo_url)}" style="width:190px;border-radius:6px;margin-top:6px" /></a>` +
        `<a href="/tags/${p.id}/log" class="btn btn-secondary btn-sm btn-block" style="margin-top:8px">${escapeHtml(logLabel)}</a>`
    );
    return marker;
  }

  // Fetches only the current viewport's tags and reconciles them against
  // what's already on the map, instead of tearing down and rebuilding every
  // marker on each pan/zoom - the previous approach visibly stuttered once
  // the dataset grew into the thousands of points.
  function loadTagsNow() {
    const params = new URLSearchParams();
    if (options.viewportFiltered) params.set("bbox", currentBboxParam());
    if (options.bandFilter) params.set("band_id", options.bandFilter);
    const url = `/api/tags.geojson${params.toString() ? `?${params}` : ""}`;
    fetch(url)
      .then((r) => r.json())
      .then((data) => {
        const filtered = filterFeatures(data, options.bandFilter);
        const seenIds = new Set();

        filtered.features.forEach((feature) => {
          const id = feature.properties.id;
          seenIds.add(id);
          if (!tagMarkersById.has(id)) {
            const marker = makeTagMarker(feature);
            marker.addTo(tagsLayerGroup);
            tagMarkersById.set(id, marker);
          }
        });

        tagMarkersById.forEach((marker, id) => {
          if (!seenIds.has(id)) {
            tagsLayerGroup.removeLayer(marker);
            tagMarkersById.delete(id);
          }
        });

        if (options.onTagsUpdate) {
          const visibleBandIds = new Set(filtered.features.map((f) => f.properties.band_id));
          options.onTagsUpdate(visibleBandIds);
        }
      });
  }

  function loadTags() {
    clearTimeout(loadTagsDebounce);
    loadTagsDebounce = setTimeout(loadTagsNow, 250);
  }

  fetch(options.bandFilter ? `/api/territories.geojson?band_id=${options.bandFilter}` : "/api/territories.geojson")
    .then((r) => r.json())
    .then((data) => {
      const filtered = filterFeatures(data, options.bandFilter);
      const territoriesInteractive = options.territoriesInteractive !== false;
      const layer = L.geoJSON(filtered, {
        style: styleTerritoryFeature,
        interactive: territoriesInteractive,
        onEachFeature: (feature, featureLayer) => {
          if (!territoriesInteractive) return;
          featureLayer.bindPopup(
            `<a href="/bands/${feature.properties.band_id}" style="font-weight:700; color:${escapeHtml(feature.properties.color)}">${escapeHtml(feature.properties.band_name)}</a><br/>${feature.properties.area_km2} km2`
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
    loadTagsNow();
    if (options.viewportFiltered) {
      map.on("moveend", loadTags);
    }
  }

  return map;
}

function initLocationPicker(mapElementId, latInputId, lonInputId, onSet) {
  const map = initLiveMap(mapElementId, { interactive: true, zoom: 14, showTags: false, territoriesInteractive: false });
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

function renderPollWidget(poll) {
  const labels = window.chatUiLabels || {};
  const box = document.createElement("div");
  box.className = "poll-widget";
  box.dataset.pollId = poll.id;

  const question = document.createElement("div");
  question.className = "poll-question";
  question.textContent = poll.question;
  box.appendChild(question);

  const total = poll.options.reduce((sum, o) => sum + o.count, 0);

  poll.options.forEach((option) => {
    const pct = total > 0 ? Math.round((option.count / total) * 100) : 0;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "poll-option" + (poll.my_vote_option_id === option.id ? " voted" : "");
    btn.innerHTML = `
      <div class="poll-option-fill" style="width:${pct}%"></div>
      <span class="poll-option-label">${escapeHtml(option.text)}</span>
      <span class="poll-option-count">${option.count} ${escapeHtml(labels.votes || "votes")}</span>
    `;
    btn.addEventListener("click", () => {
      fetch(`/api/chat/polls/${poll.id}/vote`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `option_id=${option.id}`,
      })
        .then((r) => r.json())
        .then((updatedPoll) => box.replaceWith(renderPollWidget(updatedPoll)));
    });
    box.appendChild(btn);
  });

  return box;
}

function buildChatBubbleBody(message) {
  const labels = window.chatUiLabels || {};
  const wrap = document.createElement("div");

  if (message.message_type === "image" && message.image_url) {
    const img = document.createElement("img");
    img.src = message.image_url;
    img.style.cssText = "max-width:220px;max-height:280px;border-radius:10px;display:block;object-fit:cover";
    wrap.appendChild(img);
  } else if (message.message_type === "location" && message.lat != null) {
    const link = document.createElement("a");
    link.href = `https://www.openstreetmap.org/?mlat=${message.lat}&mlon=${message.lon}#map=16/${message.lat}/${message.lon}`;
    link.target = "_blank";
    link.rel = "noopener";
    link.style.fontWeight = "700";
    link.textContent = `\u{1F4CD} ${labels.viewOnMap || "View on map"}`;
    wrap.appendChild(link);
  } else if (message.message_type === "poll" && message.poll) {
    wrap.appendChild(renderPollWidget(message.poll));
  } else if (message.message_type === "tag_added" && message.tag_id) {
    const text = document.createElement("div");
    text.textContent = message.body;
    text.style.marginBottom = "6px";
    wrap.appendChild(text);

    const link = document.createElement("a");
    link.href = `/tags/${message.tag_id}`;
    link.style.display = "flex";
    link.style.alignItems = "center";
    link.style.gap = "8px";
    link.style.fontWeight = "700";
    if (message.tag_photo_url) {
      const thumb = document.createElement("img");
      thumb.src = message.tag_photo_url;
      thumb.style.cssText = "width:40px;height:40px;border-radius:8px;object-fit:cover;flex-shrink:0";
      link.appendChild(thumb);
    }
    const label = document.createElement("span");
    label.textContent = labels.viewTag || "View tag";
    link.appendChild(label);
    wrap.appendChild(link);
  } else {
    wrap.textContent = message.body;
  }

  return wrap;
}

function appendChatMessage(container, message) {
  const bubble = document.createElement("div");
  bubble.className = "chat-bubble" + (message.is_own ? " own" : "");
  bubble.dataset.messageId = message.id;

  const meta = document.createElement("div");
  meta.className = "meta";
  meta.textContent = `${message.sender} - ${message.created_at}`;

  bubble.appendChild(meta);
  bubble.appendChild(buildChatBubbleBody(message));
  container.appendChild(bubble);
}

function prependChatMessage(container, message) {
  const bubble = document.createElement("div");
  bubble.className = "chat-bubble" + (message.is_own ? " own" : "");
  bubble.dataset.messageId = message.id;

  const meta = document.createElement("div");
  meta.className = "meta";
  meta.textContent = `${message.sender} - ${message.created_at}`;

  bubble.appendChild(meta);
  bubble.appendChild(buildChatBubbleBody(message));
  container.insertBefore(bubble, container.firstChild);
}

function initChatHistoryLoader(container, historyUrl) {
  let loading = false;
  let exhausted = false;

  function oldestMessageId() {
    let min = null;
    container.querySelectorAll("[data-message-id]").forEach((bubble) => {
      const id = parseInt(bubble.dataset.messageId, 10);
      if (min === null || id < min) min = id;
    });
    return min;
  }

  function loadOlder() {
    if (loading || exhausted) return;
    const beforeId = oldestMessageId();
    if (!beforeId) return;

    loading = true;
    fetch(`${historyUrl}?before=${beforeId}&limit=10`)
      .then((r) => r.json())
      .then((messages) => {
        loading = false;
        if (!messages.length) {
          exhausted = true;
          return;
        }
        const previousHeight = container.scrollHeight;
        const previousTop = container.scrollTop;
        for (let i = messages.length - 1; i >= 0; i -= 1) {
          prependChatMessage(container, messages[i]);
        }
        container.scrollTop = container.scrollHeight - previousHeight + previousTop;
        if (messages.length < 10) exhausted = true;
      })
      .catch(() => {
        loading = false;
        exhausted = true;
      });
  }

  container.addEventListener("scroll", () => {
    if (container.scrollTop < 100) loadOlder();
  });
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

  function refreshPolls() {
    container.querySelectorAll(".poll-widget").forEach((widget) => {
      const pollId = widget.dataset.pollId;
      fetch(`/api/chat/polls/${pollId}`)
        .then((r) => (r.ok ? r.json() : null))
        .then((updatedPoll) => {
          if (updatedPoll) widget.replaceWith(renderPollWidget(updatedPoll));
        });
    });
  }

  function poll() {
    fetch(`${messagesUrl}?after=${lastMessageId()}`)
      .then((r) => r.json())
      .then((messages) => {
        refreshPolls();
        if (!messages.length) return;
        const emptyNotice = container.querySelector("p");
        if (emptyNotice) emptyNotice.remove();
        messages.forEach((message) => appendChatMessage(container, message));
        scrollToBottom();
      });
  }

  scrollToBottom();

  // Pause polling while the tab is hidden - a chat left open in a
  // background tab shouldn't keep hitting the server every 3 seconds.
  let pollInterval = null;
  const startPolling = () => {
    if (pollInterval) return;
    poll();
    pollInterval = setInterval(poll, 3000);
  };
  const stopPolling = () => {
    clearInterval(pollInterval);
    pollInterval = null;
  };
  if (document.visibilityState === "visible") startPolling();
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") startPolling();
    else stopPolling();
  });
  window.addEventListener("beforeunload", stopPolling);

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

  document.querySelectorAll("[data-init-map]").forEach((el) => {
    initLiveMap(el.id, {
      interactive: el.dataset.interactive !== "false",
      zoom: el.dataset.zoom ? parseInt(el.dataset.zoom, 10) : 13,
      bandFilter: el.dataset.bandFilter ? parseInt(el.dataset.bandFilter, 10) : null,
    });
  });

  document.querySelectorAll('.dropzone input[type="file"]').forEach((input) => {
    const dropzone = input.closest(".dropzone");
    const filenameEl = dropzone.querySelector(".dropzone-filename");
    input.addEventListener("change", () => {
      if (filenameEl) filenameEl.textContent = input.files[0] ? input.files[0].name : "";
    });
  });
});
