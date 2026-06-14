import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, Loader2 } from 'lucide-react';
import TopNav from '../components/TopNav';
import Sidebar from '../components/Sidebar';
import { useCamera } from '../hooks/useCamera';
import { registerFace } from '../services/employeeService';
import { useToast } from '../components/Toast';
import './FaceRegister.css';

const STEPS = [
  'Nhìn thẳng vào camera',
  'Giữ nguyên vị trí',
  'Xoay nhẹ đầu sang phải',
  'Hoàn tất',
];

export default function FaceRegister() {
  const { videoRef, ready, error: cameraError, captureFrame } = useCamera();
  const [step, setStep]         = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone]         = useState(false);
  const { showToast }           = useToast();
  const navigate                = useNavigate();

  const handleConfirm = async () => {
    if (!ready) {
      showToast('Camera chưa sẵn sàng.', 'error');
      return;
    }
    setSubmitting(true);
    // Animate through steps
    setStep(1);
    await new Promise((r) => setTimeout(r, 500));
    setStep(2);
    await new Promise((r) => setTimeout(r, 500));
    setStep(3);
    try {
      const blob = await captureFrame();
      if (!blob) throw new Error('no-frame');
      const file = new File([blob], 'face-register.jpg', { type: 'image/jpeg' });
      await registerFace(file);
      setDone(true);
      showToast('Đăng ký khuôn mặt thành công! Bạn có thể điểm danh ngay.', 'success');
      setTimeout(() => navigate('/diem-danh'), 1600);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const message = Array.isArray(detail)
        ? detail.map((d) => d.msg).join(', ')
        : detail || 'Đăng ký khuôn mặt thất bại. Vui lòng thử lại.';
      showToast(message, 'error');
      setStep(0);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page">
      <TopNav />
      <div className="page__body">
        <Sidebar />
        <main className="fr">
          <div className="fr__center">
            <h1 className="fr__title">Đăng ký khuôn mặt</h1>
            <p className="fr__subtitle">
              Nhìn thẳng vào camera và giữ khuôn mặt trong khung hình.
              Khuôn mặt sẽ được kích hoạt ngay sau khi đăng ký.
            </p>

            <div className="fr__frame-wrap">
              <div className={`fr__frame ${done ? 'fr__frame--done' : ''}`}>
                {cameraError ? (
                  <div className="fr__camera-error">{cameraError}</div>
                ) : (
                  <video ref={videoRef} className="fr__video" muted playsInline />
                )}
              </div>
              <div className="fr__dots">
                {STEPS.map((_, i) => (
                  <span key={i} className={`fr__dot ${i <= step ? 'fr__dot--active' : ''}`} />
                ))}
              </div>
            </div>

            <div className="fr__status">
              <div className="fr__status-icon">{done ? <CheckCircle2 size={18} /> : '🙂'}</div>
              <div>
                <div className="fr__status-label">TRẠNG THÁI</div>
                <div className="fr__status-value">{done ? 'Đã đăng ký thành công' : STEPS[step]}</div>
              </div>
            </div>

            {done && (
              <div className="fr__success-note">
                <CheckCircle2 size={16} strokeWidth={2.2} />
                Khuôn mặt đã được kích hoạt. Bạn có thể sử dụng điểm danh ngay!
              </div>
            )}

            <button className="fr__confirm" onClick={handleConfirm} disabled={submitting || done}>
              {submitting ? (
                <><Loader2 size={18} className="fr__spin" /> Đang xử lý...</>
              ) : done ? (
                <><CheckCircle2 size={18} /> Đã đăng ký</>
              ) : (
                <><CheckCircle2 size={18} /> Xác nhận đăng ký khuôn mặt</>
              )}
            </button>
          </div>
        </main>
      </div>
    </div>
  );
}