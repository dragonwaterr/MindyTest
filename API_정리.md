# Mindy 프로젝트 API 상세 정리

본 문서는 Mindy 프로젝트에서 사용되는 모든 주요 API의 호출 흐름과 각 API의 역할, 입력/출력, 내부 처리 과정을 상세히 설명합니다.

---

## 1. 전체 프로그램 진행 흐름 및 API 호출 순서

### (A) 음성(STT) 기반 번역/합성 흐름
1. **마이크 녹음/음성파일 첨부** → 프론트엔드에서 base64 인코딩
2. **/api/stt** (음성 인식 + 노이즈 제거)
    - 내부적으로 **clean_noise_from_base64**(DeepFilterNet) 호출
3. **/api/translate-text** (텍스트 번역)
4. **/api/tts** (번역된 텍스트를 음성으로 합성, 필요시)

### (B) 이미지/문서 기반 번역 흐름
1. **이미지/PDF/문서 파일 업로드**
2. **/api/ocr-translate** (OCR + 번역)

### (C) 노이즈 제거만 별도로 테스트할 경우
1. **/api/clean-noise** (base64 오디오 → 노이즈 제거 base64 오디오)

---

## 2. 각 API 상세 설명

### 2.1 /api/clean-noise
- **역할:**
  - 입력된 base64 오디오(webm/wav/mp3 등) 데이터에서 DeepFilterNet(DF)으로 노이즈를 제거
- **입력:**
  - `audio_data` (Form, base64 인코딩된 오디오)
- **출력:**
  - `cleanedAudio` (base64 인코딩된 노이즈 제거된 wav)
- **내부 처리:**
  1. base64 → 바이트 디코딩
  2. **pydub를 사용하여 오디오 로드 및 WAV 형식으로 변환 (WebM 등 다양한 형식 지원)**
  3. 48kHz로 리샘플링 (librosa)
  4. DeepFilterNet으로 노이즈 제거
  5. 메모리에서 wav로 저장 후 base64 인코딩

### 2.2 /api/stt
- **역할:**
  - 입력된 base64 오디오에서 노이즈를 제거한 뒤 Whisper로 STT(음성 인식) 수행
- **입력:**
  - `audio_data` (Form, base64 인코딩된 오디오)
  - `source_lang` (Form, 언어코드)
- **출력:**
  - `recognizedText` (STT 결과 텍스트)
  - `cleanedAudio` (노이즈 제거된 base64 오디오)
- **내부 처리:**
  1. **clean_noise_from_base64** 함수로 노이즈 제거
  2. Whisper로 STT 수행

### 2.3 /api/translate-text
- **역할:**
  - 입력 텍스트를 source_lang → target_lang으로 번역
- **입력:**
  - `text` (Form, 번역할 텍스트)
  - `source_lang` (Form, 원본 언어코드)
  - `target_lang` (Form, 번역 언어코드)
- **출력:**
  - `translatedText` (번역 결과)
- **내부 처리:**
  1. googletrans 라이브러리로 번역 수행

### 2.4 /api/tts
- **역할:**
  - 입력 텍스트를 gTTS로 음성(mp3, base64)로 변환
- **입력:**
  - `text` (Form, 음성으로 변환할 텍스트)
  - `target_lang` (Form, 언어코드)
- **출력:**
  - `audioData` (base64 인코딩된 mp3)
- **내부 처리:**
  1. gTTS로 mp3 생성
  2. base64로 인코딩하여 반환

### 2.5 /api/ocr-translate
- **역할:**
  - 업로드된 파일(이미지, PDF, TXT, DOCX 등)에서 텍스트를 추출(OCR)하고 번역
- **입력:**
  - `file` (Form, 업로드 파일)
  - `source_lang` (Form, 원본 언어코드)
  - `target_lang` (Form, 번역 언어코드)
- **출력:**
  - `ocrText` (OCR로 추출된 텍스트)
  - `translation` (번역 결과)
- **내부 처리:**
  1. 파일 확장자에 따라 OCR/텍스트 추출
  2. 추출된 텍스트를 번역

---

## 3. 참고: 내부 주요 함수/서비스

- **clean_noise_from_base64** (services/cleanNoise.py)
  - base64 오디오 → **pydub를 통한 WAV 변환 및 DeepFilterNet으로 노이즈 제거** → base64 오디오 반환
- **speech_to_text** (services/stt_tts_service.py)
  - base64 오디오 → Whisper로 STT
- **translate** (services/translation_service.py)
  - 텍스트 번역
- **text_to_speech** (services/stt_tts_service.py)
  - 텍스트 → gTTS로 음성(mp3, base64)
- **extract_text** (services/ocr_service.py)
  - 파일에서 텍스트 추출(OCR)

---

이 문서는 Mindy 프로젝트의 API 구조와 데이터 흐름을 팀원/개발자/운영자 모두가 쉽게 이해할 수 있도록 작성되었습니다. 