import { useEffect, useState } from 'react';
import { ScanFace, Loader2, CheckCircle2, XCircle, MapPin } from 'lucide-react';
import TopNav from '../components/TopNav';
import Sidebar from '../components/Sidebar';
import { useCamera } from '../hooks/useCamera';
import { useGeolocation } from '../hooks/useGeolocation';
import { checkin, checkout } from '../services/employeeService';
import './CheckIn.css';

const WEEKDAYS = ['Chủ Nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'];

function formatClock(date) {
  return date.toLocaleTimeString('vi-VN', { hour12: false });
}

function formatDate(date) {
  return `${WEEKDAYS[date.getDay()]}, ${date.getDate()} tháng ${date.getMonth() + 1}, ${date.getFullYear()}`;
}

export default function CheckIn() {
  const [now, setNow]           = useState(new Date());
  const [mode, setMode]         = useState('checkin'); // 'checkin' | 'checkout'
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult]     = useState(null); // { type: 'success' | 'error', message }

  const { videoRef, ready, error: cameraError, captureFrame } = useCamera();
  const { position, error: gpsError, status: gpsStatus }      = useGeolocation();

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const handleSubmit = async () => {
    setResult(null);
    if (!ready) {
      setResult({ type: 'error', message: 'Camera chưa sẵn sàng. Vui lòng đợi trong giây lát.' });
      return;
    }
    setSubmitting(true);
    try {
      const blob = await captureFrame();
      if (!blob) throw new Error('no-frame');
      const file   = new File([blob], `${mode}.jpg`, { type: 'image/jpeg' });
      const lat    = position?.lat ?? null;
      const lng    = position?.lng ?? null;
      const apiCall = mode === 'checkin' ? checkin : checkout;

      const { data: payload } = await apiCall(file, lat, lng);
      // Backend: { success, message, data: { name, department, position, timestamp, checkin_status } }
      // or checkout: { success, message, data: { checkout_time } }
      const message = payload?.message ||
        (mode === 'checkin' ? 'Chấm công vào ca thành công!' : 'Chấm công ra ca thành công!');
      setResult({ type: 'success', message });
    } catch (err) {
      // Backend error: { success: false, message: "...", data: null }
      const payload = err?.response?.data;
      const detail  = payload?.message || payload?.detail;
      let message;
      if (Array.isArray(detail)) {
        message = detail.map((d) => d.msg).join(', ');
      } else if (typeof detail === 'string') {
        message = detail;
      } else {
        message = 'Chấm công thất bại. Vui lòng kiểm tra khuôn mặt và vị trí GPS.';
      }
      setResult({ type: 'error', message });
    } finally {
      setSubmitting(false);
    }
  };

  const gpsLabel =
    gpsStatus === 'matched' ? 'Đã khớp GPS' :
    gpsStatus === 'error'   ? 'Lỗi GPS'     : 'Đang định vị...';

  const locationName = position
    ? `${position.lat.toFixed(5)}, ${position.lng.toFixed(5)}`
    : 'Chưa xác định vị trí';

  return (
    <div className="page">
      <TopNav />
      <div className="page__body">
        <Sidebar />
        <main className="ci">
          <div className="ci__center">
            <div className="ci__clock">{formatClock(now)}</div>
            <div className="ci__date">{formatDate(now)}</div>

            <div className="ci__map">
              <div className="ci__map-bg">
                <div className="ci__map-ping">
                  <span className="ci__map-pulse" />
                  <span className="ci__map-dot" />
                </div>
              </div>
              <div className="ci__map-info">
                <div>
                  <div className="ci__map-label">Vị trí hiện tại</div>
                  <div className="ci__map-value">{locationName}</div>
                </div>
                <div className={`ci__gps-badge ${gpsStatus === 'error' ? 'ci__gps-badge--error' : ''}`}>
                  <MapPin size={14} strokeWidth={2.2} />
                  {gpsLabel}
                </div>
              </div>
            </div>

            <div className="ci__camera-wrap">
              <div className="ci__camera">
                {cameraError ? (
                  <div className="ci__camera-error">{cameraError}</div>
                ) : (
                  <video ref={videoRef} className="ci__video" muted playsInline />
                )}
              </div>
              <div className="ci__camera-caption">Căn chỉnh khuôn mặt vào giữa khung hình</div>
            </div>

            <div className="ci__mode-switch">
              <button
                className={`ci__mode-btn ${mode === 'checkin' ? 'ci__mode-btn--active' : ''}`}
                onClick={() => { setMode('checkin'); setResult(null); }}
              >
                Vào ca
              </button>
              <button
                className={`ci__mode-btn ${mode === 'checkout' ? 'ci__mode-btn--active' : ''}`}
                onClick={() => { setMode('checkout'); setResult(null); }}
              >
                Ra ca
              </button>
            </div>

            {result && (
              <div className={`ci__result ci__result--${result.type}`}>
                {result.type === 'success'
                  ? <CheckCircle2 size={18} strokeWidth={2.2} />
                  : <XCircle     size={18} strokeWidth={2.2} />}
                <span>{result.message}</span>
              </div>
            )}

            {gpsError && (
              <div className="ci__result ci__result--error">
                <XCircle size={18} strokeWidth={2.2} />
                <span>{gpsError}</span>
              </div>
            )}

            <button className="ci__submit" onClick={handleSubmit} disabled={submitting}>
              {submitting ? (
                <><Loader2 size={20} className="ci__spin" /> Đang xử lý...</>
              ) : (
                <><ScanFace size={20} strokeWidth={2} /> Chấm công bằng nhận diện khuôn mặt</>
              )}
            </button>
          </div>
        </main>
      </div>
    </div>
  );
}