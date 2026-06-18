import { useEffect, useRef, useState } from 'react';
import { MapPin, Save, Loader2, CheckCircle2, Navigation, Radio, Target, AlertTriangle } from 'lucide-react';
import TopNav from '../components/TopNav';
import Sidebar from '../components/Sidebar';
import { getLocationConfig, setLocationConfig } from '../services/managerService';
import { useToast } from '../components/Toast';
import './LocationConfig.css';

const DEFAULT_RADIUS = 200;

// Haversine distance (metres) — dùng để hiển thị preview khoảng cách
function haversine(lat1, lng1, lat2, lng2) {
  const R = 6371000;
  const toRad = (d) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export default function LocationConfig() {
  const { showToast } = useToast();

  // Form state
  const [lat, setLat]         = useState('');
  const [lng, setLng]         = useState('');
  const [radius, setRadius]   = useState(String(DEFAULT_RADIUS));

  // UI state
  const [loading, setLoading]         = useState(true);
  const [saving, setSaving]           = useState(false);
  const [locating, setLocating]       = useState(false);
  const [currentPos, setCurrentPos]   = useState(null);  // device GPS
  const [errorMsg, setErrorMsg]       = useState('');
  const [saved, setSaved]             = useState(false);

  // Load hiện tại từ backend
  useEffect(() => {
    setLoading(true);
    getLocationConfig()
      .then(({ data: payload }) => {
        const d = payload?.data;
        if (d?.lat != null) {
          setLat(String(d.lat));
          setLng(String(d.lng));
          setRadius(String(d.radius ?? DEFAULT_RADIUS));
        }
      })
      .catch(() => setErrorMsg('Không thể tải cấu hình vị trí. Vui lòng thử lại.'))
      .finally(() => setLoading(false));
  }, []);

  // Lấy vị trí thiết bị hiện tại để hỗ trợ điền nhanh
  const handleLocateMe = () => {
    if (!navigator.geolocation) {
      showToast('Thiết bị không hỗ trợ định vị GPS.', 'error');
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const userLat = pos.coords.latitude.toFixed(6);
        const userLng = pos.coords.longitude.toFixed(6);
        setCurrentPos({ lat: parseFloat(userLat), lng: parseFloat(userLng) });
        setLat(userLat);
        setLng(userLng);
        setLocating(false);
        showToast('Đã lấy vị trí thiết bị của bạn.', 'success');
      },
      () => {
        setLocating(false);
        showToast('Không thể lấy vị trí. Vui lòng kiểm tra quyền truy cập GPS.', 'error');
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const handleSave = async () => {
    const latNum = parseFloat(lat);
    const lngNum = parseFloat(lng);
    const radNum = parseInt(radius, 10);

    if (isNaN(latNum) || isNaN(lngNum)) {
      showToast('Vui lòng nhập tọa độ hợp lệ.', 'error');
      return;
    }
    if (latNum < -90 || latNum > 90) {
      showToast('Vĩ độ phải nằm trong khoảng -90 đến 90.', 'error');
      return;
    }
    if (lngNum < -180 || lngNum > 180) {
      showToast('Kinh độ phải nằm trong khoảng -180 đến 180.', 'error');
      return;
    }
    if (isNaN(radNum) || radNum < 50 || radNum > 5000) {
      showToast('Bán kính phải từ 50m đến 5000m.', 'error');
      return;
    }

    setSaving(true);
    setSaved(false);
    try {
      await setLocationConfig(latNum, lngNum, radNum);
      setSaved(true);
      showToast('Cập nhật vị trí điểm danh thành công!', 'success');
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      const msg = err?.response?.data?.message || 'Lưu cấu hình thất bại.';
      showToast(msg, 'error');
    } finally {
      setSaving(false);
    }
  };

  // Tính khoảng cách từ thiết bị đến điểm đã cấu hình (nếu có)
  const distanceFromDevice =
    currentPos && lat && lng
      ? haversine(currentPos.lat, currentPos.lng, parseFloat(lat), parseFloat(lng))
      : null;

  const radiusNum = parseInt(radius, 10) || DEFAULT_RADIUS;
  const isWithin =
    distanceFromDevice !== null ? distanceFromDevice <= radiusNum : null;

  return (
    <div className="page">
      <TopNav />
      <div className="page__body">
        <Sidebar statusLabel="Đang hoạt động" />
        <main className="lc">
          {/* Header */}
          <div className="lc__header">
            <div className="lc__header-icon">
              <MapPin size={26} strokeWidth={1.8} />
            </div>
            <div>
              <h1 className="lc__title">Cấu hình vị trí điểm danh</h1>
              <p className="lc__subtitle">
                Đặt tọa độ GPS và bán kính cho phép nhân viên chấm công.
              </p>
            </div>
          </div>

          {errorMsg && <div className="lc__alert">{errorMsg}</div>}

          <div className="lc__body">
            {/* LEFT — form */}
            <div className="lc__form-col">
              <div className="lc__card">
                <div className="lc__card-title">
                  <Target size={16} strokeWidth={2} />
                  Tọa độ trung tâm
                </div>

                <button
                  className="lc__locate-btn"
                  onClick={handleLocateMe}
                  disabled={locating}
                  type="button"
                >
                  {locating ? (
                    <Loader2 size={15} className="lc__spin" />
                  ) : (
                    <Navigation size={15} strokeWidth={2} />
                  )}
                  {locating ? 'Đang định vị...' : 'Dùng vị trí thiết bị của tôi'}
                </button>

                <div className="lc__divider-row">
                  <span className="lc__divider-text">hoặc nhập thủ công</span>
                </div>

                <div className="lc__field-group">
                  <div className="lc__field">
                    <label className="lc__label">Vĩ độ (Latitude)</label>
                    <input
                      className="lc__input"
                      type="number"
                      step="any"
                      placeholder="Ví dụ: 21.027763"
                      value={lat}
                      onChange={(e) => setLat(e.target.value)}
                      disabled={loading}
                    />
                    <span className="lc__hint">-90 đến 90</span>
                  </div>
                  <div className="lc__field">
                    <label className="lc__label">Kinh độ (Longitude)</label>
                    <input
                      className="lc__input"
                      type="number"
                      step="any"
                      placeholder="Ví dụ: 105.834160"
                      value={lng}
                      onChange={(e) => setLng(e.target.value)}
                      disabled={loading}
                    />
                    <span className="lc__hint">-180 đến 180</span>
                  </div>
                </div>

                <div className="lc__card-title lc__card-title--mt">
                  <Radio size={16} strokeWidth={2} />
                  Bán kính cho phép (mét)
                </div>

                <div className="lc__radius-wrap">
                  <input
                    className="lc__input lc__input--radius"
                    type="number"
                    min={50}
                    max={5000}
                    step={10}
                    value={radius}
                    onChange={(e) => setRadius(e.target.value)}
                    disabled={loading}
                  />
                  <div className="lc__radius-presets">
                    {[100, 200, 500, 1000].map((r) => (
                      <button
                        key={r}
                        type="button"
                        className={`lc__preset ${parseInt(radius) === r ? 'lc__preset--active' : ''}`}
                        onClick={() => setRadius(String(r))}
                      >
                        {r}m
                      </button>
                    ))}
                  </div>
                </div>

                {/* Slider bán kính */}
                <input
                  className="lc__slider"
                  type="range"
                  min={50}
                  max={2000}
                  step={10}
                  value={Math.min(parseInt(radius) || DEFAULT_RADIUS, 2000)}
                  onChange={(e) => setRadius(e.target.value)}
                  disabled={loading}
                />
                <div className="lc__slider-labels">
                  <span>50m</span>
                  <span>2000m</span>
                </div>

                <button
                  className="lc__save-btn"
                  onClick={handleSave}
                  disabled={saving || loading}
                  type="button"
                >
                  {saving ? (
                    <><Loader2 size={18} className="lc__spin" /> Đang lưu...</>
                  ) : saved ? (
                    <><CheckCircle2 size={18} /> Đã lưu!</>
                  ) : (
                    <><Save size={18} strokeWidth={2} /> Lưu cấu hình</>
                  )}
                </button>
              </div>
            </div>

            {/* RIGHT — preview & info */}
            <div className="lc__preview-col">
              {/* Map visual */}
              <div className="lc__map-card">
                <div className="lc__map-visual">
                  <MapVisual lat={lat} lng={lng} radius={radiusNum} />
                </div>
                <div className="lc__map-footer">
                  <div className="lc__map-stat">
                    <span className="lc__map-stat-label">Tọa độ</span>
                    <span className="lc__map-stat-value">
                      {lat && lng
                        ? `${parseFloat(lat).toFixed(5)}, ${parseFloat(lng).toFixed(5)}`
                        : '—'}
                    </span>
                  </div>
                  <div className="lc__map-divider" />
                  <div className="lc__map-stat">
                    <span className="lc__map-stat-label">Bán kính</span>
                    <span className="lc__map-stat-value">{radiusNum}m</span>
                  </div>
                </div>
              </div>

              {/* Device distance check */}
              {distanceFromDevice !== null && (
                <div className={`lc__distance-card ${isWithin ? 'lc__distance-card--ok' : 'lc__distance-card--warn'}`}>
                  <div className="lc__distance-icon">
                    {isWithin
                      ? <CheckCircle2 size={20} strokeWidth={2} />
                      : <AlertTriangle size={20} strokeWidth={2} />}
                  </div>
                  <div>
                    <div className="lc__distance-title">
                      {isWithin ? 'Thiết bị nằm trong vùng cho phép' : 'Thiết bị nằm ngoài vùng cho phép'}
                    </div>
                    <div className="lc__distance-sub">
                      Khoảng cách từ thiết bị đến tâm: <strong>{Math.round(distanceFromDevice)}m</strong>
                    </div>
                  </div>
                </div>
              )}

              {/* Info box */}
              <div className="lc__info-card">
                <div className="lc__info-title">Hướng dẫn</div>
                <ul className="lc__info-list">
                  <li>Nhân viên chỉ được chấm công khi thiết bị nằm trong bán kính đã cấu hình.</li>
                  <li>Nếu chưa cấu hình vị trí, hệ thống sẽ cho phép chấm công từ mọi nơi.</li>
                  <li>Dùng nút <strong>"Vị trí thiết bị"</strong> để điền tọa độ văn phòng nhanh.</li>
                  <li>Bán kính tối thiểu 50m, tối đa 5000m. Khuyến nghị 200m.</li>
                </ul>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

// SVG map visual — animated pulse + radius ring
function MapVisual({ lat, lng, radius }) {
  const hasCoords = lat && lng;

  // Tính tỉ lệ vòng tròn dựa trên bán kính (tương đối, chỉ để visualize)
  const maxRadius = 2000;
  const ringRatio = Math.min((parseInt(radius) || 200) / maxRadius, 1);
  const ringR = 30 + ringRatio * 55; // 30 → 85px

  return (
    <div className="lc__map-bg">
      {/* Grid */}
      <svg className="lc__map-grid" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="grid" width="36" height="36" patternUnits="userSpaceOnUse">
            <path d="M 36 0 L 0 0 0 36" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="1"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
      </svg>

      {hasCoords ? (
        <div className="lc__map-center">
          {/* Radius ring */}
          <div
            className="lc__map-ring"
            style={{ width: ringR * 2, height: ringR * 2, borderRadius: '50%' }}
          />
          {/* Pulse */}
          <div className="lc__map-pulse" />
          {/* Dot */}
          <div className="lc__map-dot">
            <div className="lc__map-dot-inner" />
          </div>
          {/* Radius label */}
          <div className="lc__map-ring-label" style={{ top: `calc(50% - ${ringR}px - 20px)` }}>
            ←{parseInt(radius) || 200}m→
          </div>
        </div>
      ) : (
        <div className="lc__map-empty">
          <MapPin size={28} strokeWidth={1.5} />
          <span>Chưa có tọa độ</span>
        </div>
      )}
    </div>
  );
}