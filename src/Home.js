import React, { useState, useRef } from 'react';
import './App.css';
import { API_BASE_URL } from './config';

function Home() {
  const [recording, setRecording] = useState(false);
  const [recognizedText, setRecognizedText] = useState('');
  const [translatedText, setTranslatedText] = useState('');
  const [sourceLang, setSourceLang] = useState('ko');
  const [targetLang, setTargetLang] = useState('en');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isTranslating, setIsTranslating] = useState(false);
  const [cleanedAudio, setCleanedAudio] = useState(null);
  const [originalAudioUrl, setOriginalAudioUrl] = useState(null);
  const [denoisedAudioUrl, setDenoisedAudioUrl] = useState(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef   = useRef([]);
  const silenceTimerRef  = useRef(null);
  const audioCtxRef      = useRef(null);
  const analyserRef      = useRef(null);

  // 2초 무음 감지 → 자동 정지
  const detectSilence = stream => {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    const ctx = new AudioCtx();
    audioCtxRef.current = ctx;
    const src = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyserRef.current = analyser;
    src.connect(analyser);
    const data = new Uint8Array(analyser.fftSize);

    const check = () => {
      analyser.getByteTimeDomainData(data);
      const silent = data.every(v => Math.abs(v - 128) < 2);
      if (silent && !silenceTimerRef.current) {
        silenceTimerRef.current = setTimeout(() => {
          if (mediaRecorderRef.current?.state === 'recording') {
            mediaRecorderRef.current.stop();
          }
        }, 2000);
      } else if (!silent && silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
        silenceTimerRef.current = null;
      }
      if (mediaRecorderRef.current?.state === 'recording') {
        requestAnimationFrame(check);
      }
    };
    check();
  };

  // 1) 마이크 녹음 → 자동 정지 → STT → 번역 → 브라우저 TTS
  const handleRecord = async () => {
    setError('');
    if (!recording) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mr = new MediaRecorder(stream);
        mediaRecorderRef.current = mr;
        audioChunksRef.current = [];

        mr.ondataavailable = e => {
          if (e.data.size) audioChunksRef.current.push(e.data);
        };

        mr.onstop = async () => {
          setLoading(true);
          setIsTranslating(true);
          const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          const reader = new FileReader();
          reader.onloadend = async () => {
            try {
              const base64 = reader.result;

              // STT
              const sttRes = await fetch(`${API_BASE_URL}/api/stt`, {
                method: 'POST',
                body: new URLSearchParams({
                  audio_data: base64,
                  source_lang: sourceLang
                })
              });
              const { recognizedText, cleanedAudio, originalFileUrl, denoisedFileUrl } = await sttRes.json();
              setRecognizedText(recognizedText);
              setCleanedAudio(cleanedAudio);
              setOriginalAudioUrl(`${API_BASE_URL}${originalFileUrl}`);
              setDenoisedAudioUrl(`${API_BASE_URL}${denoisedFileUrl}`);

              // 번역
              const trRes = await fetch(`${API_BASE_URL}/api/translate-text`, {
                method: 'POST',
                body: new URLSearchParams({
                  text: recognizedText,
                  source_lang: sourceLang,
                  target_lang: targetLang
                })
              });
              const { translatedText } = await trRes.json();
              setTranslatedText(translatedText);

              // 브라우저 TTS는 이제 버튼을 눌러야 재생되므로 여기서 제거
              // const utter = new SpeechSynthesisUtterance(translatedText);
              // utter.lang = targetLang;
              // window.speechSynthesis.speak(utter);
            } catch (err) {
              console.error(err);
              setError('음성 번역 중 오류가 발생했습니다.');
            } finally {
              setLoading(false);
              setIsTranslating(false);
              stream.getTracks().forEach(t => t.stop());
              audioCtxRef.current?.close();
              setRecording(false);
            }
          };
          reader.readAsDataURL(blob);
        };

        mr.start();
        setRecording(true);
        detectSilence(stream);
      } catch (err) {
        console.error(err);
        setError('마이크를 사용할 수 없습니다.');
      }
    } else {
      mediaRecorderRef.current.stop();
    }
  };

  // 파일 업로드 핸들러 수정
  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = async (e) => {
        const base64 = e.target.result;
        try {
          setIsTranslating(true);
          setError("");

          // STT 및 노이즈 제거 (이제 /api/stt가 파일 저장 및 URL 반환)
          const sttRes = await fetch(`${API_BASE_URL}/api/stt`, {
            method: 'POST',
            body: new URLSearchParams({
              audio_data: base64,
              source_lang: sourceLang
            })
          });
          const { recognizedText, cleanedAudio, originalFileUrl, denoisedFileUrl } = await sttRes.json();
          setRecognizedText(recognizedText);
          setCleanedAudio(cleanedAudio); // Base64는 계속 받되, UI에서는 URL 사용
          setOriginalAudioUrl(`${API_BASE_URL}${originalFileUrl}`);
          setDenoisedAudioUrl(`${API_BASE_URL}${denoisedFileUrl}`);

          // 번역
          const trRes = await fetch(`${API_BASE_URL}/api/translate-text`, {
            method: 'POST',
            body: new URLSearchParams({
              text: recognizedText,
              source_lang: sourceLang,
              target_lang: targetLang
            })
          });
          const { translatedText } = await trRes.json();
          setTranslatedText(translatedText);

          // 브라우저 TTS 자동 재생 제거
          // window.speechSynthesis.cancel();
          // const utter = new window.SpeechSynthesisUtterance(translatedText);
          // utter.lang = targetLang;
          // utter.rate = 1;
          // utter.pitch = 1;
          // utter.volume = 1;
          // window.speechSynthesis.speak(utter);
        } catch (err) {
          console.error(err);
          setError('파일 업로드 중 오류가 발생했습니다.');
        } finally {
          setIsTranslating(false);
        }
      };
      reader.readAsDataURL(file);
    }
  };

  // 번역 결과 재생 함수 추가
  const playTranslatedAudio = () => {
    if (translatedText) {
      window.speechSynthesis.cancel();
      const utter = new window.SpeechSynthesisUtterance(translatedText);
      utter.lang = targetLang;
      utter.rate = 1;
      utter.pitch = 1;
      utter.volume = 1;
      window.speechSynthesis.speak(utter);
    } else {
      alert("번역된 텍스트가 없습니다.");
    }
  };

  return (
    <div className="App">
      <header><h1>Mindy</h1></header>

      <div className="control-panel">
        <button
          className={`mic-button ${recording ? 'recording' : ''}`}
          onClick={handleRecord}
          disabled={loading}
        >
          {recording ? '■' : '🎤'}
        </button>
        <input
          type="file"
          accept="audio/mp3,audio/mpeg,audio/wav,audio/x-wav,audio/webm"
          style={{ display: 'none' }}
          id="audio-upload"
          onChange={handleFileUpload}
          disabled={loading || recording}
        />
        <label htmlFor="audio-upload" className="attach-button" style={{ marginLeft: 10, cursor: 'pointer' }}>
          📎
        </label>
        <div className="lang-selectors">
          <label>
            STT 언어:
            <select
              value={sourceLang}
              onChange={e => { setSourceLang(e.target.value); }}
              disabled={loading || recording}
            >
              <option value="ko">한국어</option>
              <option value="en">English</option>
              <option value="ja">日本語</option>
              <option value="zh">中文</option>
              <option value="es">Español</option>
            </select>
          </label>
          <label>
            번역 언어:
            <select
              value={targetLang}
              onChange={e => { setTargetLang(e.target.value); }}
              disabled={loading || recording}
            >
              <option value="en">English</option>
              <option value="ko">한국어</option>
              <option value="ja">日本語</option>
              <option value="zh">中文</option>
              <option value="es">Español</option>
            </select>
          </label>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="boxes horizontal">
        <div className="box">
          <h2>인식된 텍스트 ({sourceLang}):</h2>
          <textarea readOnly value={recognizedText} placeholder="STT 결과" />

          {originalAudioUrl && (
            <div style={{ marginTop: 12 }}>
              <p>원본 음성:</p>
              <audio controls src={originalAudioUrl}></audio>
            </div>
          )}

          {denoisedAudioUrl && (
            <div style={{ marginTop: 12 }}>
              <p>노이즈 제거 음성:</p>
              <audio controls src={denoisedAudioUrl}></audio>
            </div>
          )}
        </div>
        <div className="box">
          <h2>번역된 텍스트 ({targetLang}):</h2>
          {isTranslating ? (
            <div className="loading-indicator">
              <div className="spinner"></div>
              번역 및 음성 처리 중입니다...
            </div>
          ) : (
            <>
              <textarea readOnly value={translatedText} placeholder="번역 결과" />
              {translatedText && (
                <button className="play-translated-audio" onClick={playTranslatedAudio} style={{marginTop: 12}}>
                  번역 결과 듣기
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default Home;
