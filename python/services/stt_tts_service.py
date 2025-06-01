import whisper
from gtts import gTTS
import base64
import os
import tempfile

class STT_TTSService:
    """
    STT (Speech-to-Text) and TTS (Text-to-Speech) 기능만을 담당하는 서비스입니다.
    """
    def __init__(self):
        # Whisper 모델 로드
        self.model = whisper.load_model("large")
        # 지원 언어 목록
        self.supported_languages = {"ko", "en", "ja", "zh", "es"}

    async def speech_to_text(self, audio_data: str, source_lang: str) -> str:
        """
        Base64로 인코딩된 오디오 데이터를 받아 지정된 언어로 STT 처리를 수행하고
        인식된 텍스트를 반환합니다.
        """
        if source_lang not in self.supported_languages:
            raise ValueError(f"Unsupported source language: {source_lang}")
        try:
            # Data URL 형식일 경우, 쉼표 이후 순수 base64 데이터만 분리
            if "," in audio_data:
                _, audio_data = audio_data.split(",", 1)
            audio_bytes = base64.b64decode(audio_data)

            # 임시 WAV 파일 생성 후 Whisper로 음성 인식
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                temp_path = tmp.name

            result = self.model.transcribe(temp_path, language=source_lang)
            os.unlink(temp_path)

            return result.get("text", "").strip()
        except Exception as e:
            raise RuntimeError(f"Speech recognition error: {e}")

    async def text_to_speech(self, text: str, target_lang: str) -> str:
        """
        텍스트와 대상 언어 코드를 받아 gTTS로 TTS 처리 후
        Base64 인코딩된 MP3 데이터 URL 문자열로 반환합니다.
        """
        if not text:
            return ""
        if target_lang not in self.supported_languages:
            raise ValueError(f"Unsupported target language: {target_lang}")
        try:
            tts = gTTS(text=text, lang=target_lang)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tts.save(tmp.name)
                with open(tmp.name, "rb") as f:
                    audio_bytes = f.read()
                os.unlink(tmp.name)

            b64_audio = base64.b64encode(audio_bytes).decode('utf-8')
            return f"data:audio/mp3;base64,{b64_audio}"
        except Exception as e:
            raise RuntimeError(f"Text to speech error: {e}")

    def is_language_supported(self, lang_code: str) -> bool:
        """
        언어 지원 여부 확인
        """
        return lang_code.lower() in self.supported_languages
