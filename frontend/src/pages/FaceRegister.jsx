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
  'Xoay nhẹ đầu',
  'Hoàn tất',
];

export default function FaceRegister() {
  const { videoRef, ready, error: cameraError, captureFrame } = useCamera();
  const [step, setStep] = useState(2); // matches mockup state "Xoay nhẹ đầu"
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const { showToast } = useToast();
  const navigate = useNavigate();

  const handleConfirm = async () => {
    if (!ready) {
      showToast('Camera chưa sẵn sàng.', 'error');
      return;
    }
    setSubmitting(true);
    try {
      const blob = await captureFrame();
      if (!blob) throw new Error('no-frame');
      const file = new File([blob], 'face-register.jpg', { type: 'image/jpeg' });
      await registerFace(file);
      setDone(true);
      setStep(3);
      showToast('Đăng ký khuôn mặt thành công', 'success');
      setTimeout(() => navigate('/trang-chu'), 1400);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const message = Array.isArray(detail)
        ? detail.map((d) => d.msg).join(', ')
        : detail || 'Đăng ký khuôn mặt thất bại. Vui lòng thử lại.';
      showToast(message, 'error');
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
              Vui lòng làm theo hướng dẫn để thiết lập bảo mật sinh trắc học của bạn.
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
                <div className="fr__status-label">TRẠNG THÁI HIỆN TẠI</div>
                <div className="fr__status-value">{done ? 'Hoàn tất' : STEPS[step]}</div>
              </div>
            </div>

            <button className="fr__confirm" onClick={handleConfirm} disabled={submitting || done}>
              {submitting ? (
                <>
                  <Loader2 size={18} className="fr__spin" /> Đang xử lý...
                </>
              ) : done ? (
                <>
                  <CheckCircle2 size={18} /> Đã đăng ký
                </>
              ) : (
                <>
                  <CheckCircle2 size={18} /> Xác nhận mẫu khuôn mặt
                </>
              )}
            </button>
          </div>
        </main>
      </div>
    </div>
  );
}
