import React, { useState } from 'react';
import { API_BASE_URL } from './config';  // ✅ config.js에서 가져오기

const DenoisePage = () => {
  const [file, setFile] = useState(null);
  const [originalUrl, setOriginalUrl] = useState(null);
  const [denoisedUrl, setDenoisedUrl] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleDenoise = async () => {
    if (!file) {
      alert('Please select a file first.');
      return;
    }

    const formData = new FormData();
    formData.append('noisy_file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/api/denoise-upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.error) {
        console.error('Server error:', result.error);
        alert(`Server error: ${result.error}`);
        return;
      }

      setOriginalUrl(`${API_BASE_URL}${result.originalFile}`);
      setDenoisedUrl(`${API_BASE_URL}${result.denoisedFile}`);
    } catch (error) {
      console.error('Denoise failed:', error);
      alert('Denoise request failed. Check console for details.');
    }
  };

  return (
    <div className="denoise-form" style={{ marginTop: '20px' }}>
      <h2>Noise Removal Upload</h2>
      <input type="file" onChange={handleFileChange} accept="audio/wav" />
      <button onClick={handleDenoise}>Upload and Denoise</button>

      <div className="audio-section" style={{ marginTop: '20px' }}>
        {originalUrl && (
          <div>
            <p>Original File:</p>
            <audio controls src={originalUrl}></audio>
          </div>
        )}
        {denoisedUrl && (
          <div>
            <p>Denoised File:</p>
            <audio controls src={denoisedUrl}></audio>
          </div>
        )}
      </div>
    </div>
  );
};

export default DenoisePage;
