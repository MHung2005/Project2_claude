"""
backend/app/services/ai/embeddings.py

Sử dụng InsightFace để sinh embedding khuôn mặt.
Kiểm tra chất lượng khuôn mặt trước khi embedding:
  1. det_score  : độ tin cậy phát hiện khuôn mặt (>= 0.70)
  2. pose (yaw) : góc xoay ngang không vượt quá ±30°
  3. kps spread : 5 keypoint phải phân bố đủ rộng — phát hiện che mặt
"""

import numpy as np
from insightface.app import FaceAnalysis

# ── Ngưỡng chất lượng ──────────────────────────────────────────────────────
DET_SCORE_THRESHOLD  = 0.70   # độ tin cậy tối thiểu khi detect khuôn mặt
MAX_YAW_DEGREE       = 30.0   # góc xoay ngang tối đa (°), vượt qua → bị che/nghiêng
MIN_KPS_SPREAD_RATIO = 0.10   # tỉ lệ spread keypoint tối thiểu so với chiều cao bbox

_instance = None


class FaceEmbeddingService:
    def __new__(cls, *args, **kwargs):
        global _instance
        if _instance is None:
            _instance = super().__new__(cls)
            _instance._initialized = False
        return _instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self.app = FaceAnalysis(name='buffalo_l')
        self.app.prepare(ctx_id=-1, det_size=(640, 640))
        self._initialized = True

    def embedding_img(self, img):
        faces = self.app.get(img)

        if not faces:
            print("Không tìm thấy khuôn mặt nào")
            return None

        best_face = max(faces, key=lambda x: x.det_score)

        # ── Kiểm tra 1: độ tin cậy phát hiện ──────────────────────────────
        det_score = float(best_face.det_score)
        if det_score < DET_SCORE_THRESHOLD:
            print(f"[REJECT] det_score quá thấp: {det_score:.3f} < {DET_SCORE_THRESHOLD}")
            return None

        # ── Kiểm tra 2: số keypoint ────────────────────────────────────────
        kps = best_face.kps
        if kps is None or len(kps) < 5:
            print(f"[REJECT] Keypoint không đủ: {len(kps) if kps is not None else 0}/5")
            return None

        # ── Kiểm tra 3: góc xoay mặt (yaw) ─────────────────────────────────
        if best_face.pose is not None:
            yaw = float(best_face.pose[1])
            if abs(yaw) > MAX_YAW_DEGREE:
                print(f"[REJECT] Góc mặt quá nghiêng: yaw={yaw:.1f}° (tối đa ±{MAX_YAW_DEGREE}°)")
                return None

        # ── Kiểm tra 4: phân bố keypoint — phát hiện che mũi/miệng ─────────
        # 0: mắt trái | 1: mắt phải | 2: mũi | 3: khóe miệng trái | 4: khóe miệng phải
        kps = np.array(kps)

        eye_y   = (kps[0][1] + kps[1][1]) / 2.0
        mouth_y = (kps[3][1] + kps[4][1]) / 2.0
        spread_y = abs(mouth_y - eye_y)

        bbox   = best_face.bbox
        bbox_h = float(bbox[3] - bbox[1])

        if bbox_h > 0:
            spread_ratio = spread_y / bbox_h
            if spread_ratio < MIN_KPS_SPREAD_RATIO:
                print(
                    f"[REJECT] Keypoint tụm lại (spread={spread_ratio:.3f} "
                    f"< {MIN_KPS_SPREAD_RATIO}): khuôn mặt có thể bị che"
                )
                return None

        # ── Tất cả kiểm tra qua → embedding ──────────────────────────────
        return best_face.embedding
