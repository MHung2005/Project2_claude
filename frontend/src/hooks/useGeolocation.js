import { useEffect, useState } from 'react';

export function useGeolocation() {
  const [position, setPosition] = useState(null);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('locating'); // 'locating' | 'matched' | 'unmatched' | 'error'

  useEffect(() => {
    if (!navigator.geolocation) {
      setError('Thiết bị không hỗ trợ định vị GPS.');
      setStatus('error');
      return;
    }

    const watcher = navigator.geolocation.watchPosition(
      (pos) => {
        setPosition({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        });
        setStatus('matched');
      },
      () => {
        setError('Không thể lấy vị trí GPS. Vui lòng cấp quyền truy cập vị trí.');
        setStatus('error');
      },
      { enableHighAccuracy: true, maximumAge: 10000, timeout: 15000 }
    );

    return () => navigator.geolocation.clearWatch(watcher);
  }, []);

  return { position, error, status };
}
