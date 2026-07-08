"""高德地图 — P0-7；支持安全密钥 + Folium 离线兜底。"""

from __future__ import annotations

import json
import math
import os

import streamlit as st
import streamlit.components.v1 as components

from utils.data_loader import get_heatmap_hotspots, load_cities

AMAP_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
__SECURITY_CONFIG__
<script src="https://webapi.amap.com/maps?v=2.0&key=__AMAP_KEY__"></script>
<style>
  html, body { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden;
    font-family: 'Noto Sans SC', sans-serif; background: #0b1020; }
  #map { width: 100%; height: 580px; min-height: 580px; min-width: 200px; }
  #err { color: #ff6b4a; padding: 12px; font-size: 14px; display: none; line-height: 1.6; }
  .info-win { padding: 8px; max-width: 240px; }
  .info-win h4 { margin: 0 0 6px; }
  .info-win p { margin: 2px 0; font-size: 13px; color: #666; }
</style>
</head>
<body>
<div id="err"></div>
<div id="map"></div>
<script>
(function() {
  var errEl = document.getElementById('err');
  var mapEl = document.getElementById('map');
  var map = null;
  var markers = [];
  var path = [];

  function showErr(msg, hint) {
    errEl.style.display = 'block';
    errEl.innerHTML = '⚠️ 地图加载失败：' + msg +
      '<br><small>' + (hint || '若反复出现：刷新页面并先点开「地图」Tab，或改用离线地图。') + '</small>';
  }

  function isValidCoord(lng, lat) {
    return typeof lng === 'number' && typeof lat === 'number' &&
      isFinite(lng) && isFinite(lat) &&
      lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180;
  }

  function waitForVisibleContainer(cb, attempt) {
    attempt = attempt || 0;
    var w = mapEl.offsetWidth;
    var h = mapEl.offsetHeight;
    var visible = mapEl.getClientRects().length > 0;
    if (w > 0 && h > 0 && visible) {
      cb();
      return;
    }
    if (attempt >= 80) {
      mapEl.style.width = '100%';
      mapEl.style.height = '580px';
      setTimeout(cb, 150);
      return;
    }
    requestAnimationFrame(function() { waitForVisibleContainer(cb, attempt + 1); });
  }

  function safeFitView() {
    if (!map || path.length === 0) return;
    try {
      map.resize();
      if (path.length === 1) {
        map.setZoomAndCenter(14, path[0]);
        return;
      }
      map.setFitView(markers, false, [50, 50, 50, 50], 14);
    } catch (e) {
      try { map.setZoomAndCenter(12, path[0]); } catch (_) {}
    }
  }

  function bindVisibilityResize() {
    if (typeof IntersectionObserver === 'undefined') return;
    var obs = new IntersectionObserver(function(entries) {
      if (!map || !entries[0].isIntersecting) return;
      setTimeout(function() {
        try {
          map.resize();
          safeFitView();
        } catch (_) {}
      }, 120);
    }, { threshold: 0.05 });
    obs.observe(mapEl);
    window.addEventListener('resize', function() {
      if (map) { try { map.resize(); } catch (_) {} }
    });
  }

  function initMap() {
    try {
      if (typeof AMap === 'undefined') {
        showErr('AMap SDK 未加载', '请检查 Key、安全密钥、白名单(localhost;127.0.0.1)');
        return;
      }

      var attractions = __ATTRACTIONS__;
      var center = __CENTER__;
      var heatmapData = __HEATMAP__;
      var showHeat = __SHOW_HEAT__;

      if (!isValidCoord(center[0], center[1])) {
        center = [114.3055, 30.5928];
      }

      attractions = (attractions || []).filter(function(a) {
        return isValidCoord(a.lng, a.lat);
      });

      if (attractions.length === 0) {
        showErr('没有有效的经纬度坐标', '请确认行程数据含 lat/lng 字段');
        return;
      }

      map = new AMap.Map('map', {
        zoom: 12,
        center: center,
        viewMode: '2D',
        resizeEnable: true,
        animateEnable: false,
      });

      attractions.forEach(function(a, idx) {
        var pos = [a.lng, a.lat];
        path.push(pos);
        var marker = new AMap.Marker({
          position: pos,
          title: a.name,
          anchor: 'bottom-center',
        });
        var costStr = a.cost === 0 ? '免费' : '¥' + a.cost;
        var infoWindow = new AMap.InfoWindow({
          content: '<div class="info-win"><h4>' + a.emoji + ' ' + a.name +
            '</h4><p>' + (a.description || '') + '</p><p>🕐 ' + a.time +
            ' | 门票: ' + costStr + '</p></div>'
        });
        marker.on('click', function() { infoWindow.open(map, pos); });
        map.add(marker);
        markers.push(marker);
      });

      if (path.length > 1) {
        map.add(new AMap.Polyline({
          path: path,
          strokeColor: '#4cc9f0',
          strokeWeight: 5,
          strokeStyle: 'dashed',
        }));
      }

      map.on('complete', function() {
        try {
          map.resize();
          markers.forEach(function(marker, idx) {
            marker.setLabel({
              content: '<div style="background:#ff6b4a;color:#fff;border-radius:50%;'
                + 'width:22px;height:22px;line-height:22px;text-align:center;'
                + 'font-size:12px;font-weight:bold;">' + (idx + 1) + '</div>',
              direction: 'top',
              offset: new AMap.Pixel(0, -4),
            });
          });
          safeFitView();
        } catch (e) {
          showErr(e.message, '地图容器尺寸异常，请切换到地图 Tab 后刷新');
        }

        if (showHeat && heatmapData.length > 0) {
          map.plugin(['AMap.HeatMap'], function() {
            var heatmap = new AMap.HeatMap(map, { radius: 35, opacity: [0, 0.8] });
            heatmap.setDataSet({ data: heatmapData, max: 100 });
          });
        }
      });

      bindVisibilityResize();
      setTimeout(function() { if (map) { try { map.resize(); safeFitView(); } catch (_) {} } }, 400);
    } catch (e) {
      showErr(e.message);
    }
  }

  waitForVisibleContainer(initMap);
})();
</script>
</body>
</html>
"""


def _as_float(value) -> float | None:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(num):
        return None
    return num


def _valid_coord(lat, lng) -> bool:
    lat_f, lng_f = _as_float(lat), _as_float(lng)
    if lat_f is None or lng_f is None:
        return False
    return -90 <= lat_f <= 90 and -180 <= lng_f <= 180


def _collect_map_points(plan: dict) -> list[dict]:
    points = []
    seen: set[tuple[float, float, str]] = set()
    for day in plan.get("days", []):
        for item in day.get("items", []):
            lat, lng = _as_float(item.get("lat")), _as_float(item.get("lng"))
            if lat is None or lng is None or not _valid_coord(lat, lng):
                continue
            key = (round(lat, 5), round(lng, 5), item.get("name", ""))
            if key in seen:
                continue
            seen.add(key)
            points.append({
                "name": item.get("name", ""),
                "lat": lat,
                "lng": lng,
                "cost": item.get("cost", 0),
                "description": item.get("description", ""),
                "emoji": item.get("emoji", "📍"),
                "time": item.get("time", ""),
            })
    return points


def _city_center(plan: dict) -> list[float]:
    city = plan.get("trip_summary", {}).get("city", "武汉")
    for c in load_cities():
        if c["name"] == city:
            lng, lat = _as_float(c.get("lng")), _as_float(c.get("lat"))
            if lng is not None and lat is not None:
                return [lng, lat]
    points = _collect_map_points(plan)
    if points:
        return [points[0]["lng"], points[0]["lat"]]
    return [114.3055, 30.5928]


def _render_folium_fallback(plan: dict, points: list[dict]) -> None:
    """高德失败时的离线兜底地图。"""
    try:
        import folium
        from streamlit_folium import st_folium

        center = _city_center(plan)
        m = folium.Map(location=[center[1], center[0]], zoom_start=12, tiles="OpenStreetMap")
        coords = []
        for idx, p in enumerate(points, 1):
            folium.Marker(
                [p["lat"], p["lng"]],
                popup=f"{idx}. {p['name']}",
                tooltip=p["name"],
                icon=folium.DivIcon(html=f'<div style="font-weight:bold;color:#4cc9f0;">{idx}</div>'),
            ).add_to(m)
            coords.append([p["lat"], p["lng"]])
        if len(coords) > 1:
            folium.PolyLine(coords, color="#4cc9f0", weight=4, dash_array="8").add_to(m)
        st_folium(m, width=None, height=580)
        st.caption("⚠️ 高德地图未加载，已切换 OpenStreetMap 兜底显示")
    except Exception as e:
        st.error(f"地图加载失败：{e}")


def render_map(plan: dict, show_heatmap: bool = False) -> None:
    if st.session_state.get("map_use_folium"):
        points = _collect_map_points(plan)
        if points:
            _render_folium_fallback(plan, points)
        else:
            st.info("暂无地图坐标数据。")
        return

    points = _collect_map_points(plan)
    if not points:
        st.info("暂无地图坐标数据。")
        return

    amap_key = os.getenv("AMAP_JS_API_KEY", "").strip()
    security_code = os.getenv("AMAP_SECURITY_JS_CODE", "").strip()

    if not amap_key:
        st.warning("未配置 AMAP_JS_API_KEY，使用离线地图。")
        _render_folium_fallback(plan, points)
        return

    if not security_code:
        st.warning(
            "未配置 **AMAP_SECURITY_JS_CODE**（高德控制台「安全密钥」）。"
            "JS API 2.0 通常需要 Key + 安全密钥才能显示瓦片。"
        )

    security_block = ""
    if security_code:
        security_block = (
            f"<script>window._AMapSecurityConfig={{securityJsCode:'{security_code}'}};</script>"
        )

    city = plan.get("trip_summary", {}).get("city", "武汉")
    heat_raw = get_heatmap_hotspots(city) if show_heatmap else []
    heat_data = []
    for h in heat_raw:
        lng, lat = _as_float(h.get("lng")), _as_float(h.get("lat"))
        if lng is None or lat is None:
            continue
        density = _as_float(h.get("density")) or 50
        heat_data.append({"lng": lng, "lat": lat, "count": density})

    html_content = AMAP_HTML.replace("__SECURITY_CONFIG__", security_block)
    html_content = html_content.replace("__AMAP_KEY__", amap_key)
    html_content = html_content.replace("__ATTRACTIONS__", json.dumps(points, ensure_ascii=False))
    html_content = html_content.replace("__CENTER__", json.dumps(_city_center(plan)))
    html_content = html_content.replace("__HEATMAP__", json.dumps(heat_data, ensure_ascii=False))
    html_content = html_content.replace("__SHOW_HEAT__", "true" if show_heatmap else "false")

    components.html(html_content, height=600, scrolling=False)

    with st.expander("地图加载不稳定？点这里排查"):
        st.markdown(
            """
            **常见原因（不一定 Key 有问题）：**

            1. **Tab 未激活时初始化**：Streamlit 地图在隐藏 Tab 里，容器宽高为 0 会导致 `Pixel(NaN, NaN)`  
               → 先点开 **「地图」** Tab，再 **刷新页面（F5）**
            2. **白名单**：填 `localhost;127.0.0.1`（英文分号），访问地址与白名单一致  
               → 建议固定用 http://127.0.0.1:8501
            3. **安全密钥**：`.env` 中 `AMAP_SECURITY_JS_CODE=` 与控制台一致，改完需 **重启 Streamlit**
            4. 仍失败可点下方按钮切换 **OpenStreetMap 离线地图**
            """
        )
        if st.button("改用离线地图（OpenStreetMap）", key="map_folium_btn"):
            st.session_state["map_use_folium"] = True
            st.rerun()

    cap = f"共 {len(points)} 个点位 · 虚线为游览顺序"
    if show_heatmap:
        cap += " · 热力图层已开启"
    st.caption(cap)
