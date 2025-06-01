import base64
import numpy as np
import io
import soundfile as sf
import torch
import librosa
from df.enhance import enhance, init_df
from pydub import AudioSegment

def clean_noise_from_base64(audio_b64: str) -> str:
    """
    base64로 인코딩된 오디오(wav/mp3) 데이터를 받아 노이즈 제거 후 base64로 반환
    """
    # base64 디코딩
    if ',' in audio_b64:
        _, audio_b64 = audio_b64.split(',', 1)
    audio_bytes = base64.b64decode(audio_b64)

    try:
        # pydub를 사용하여 WebM (또는 다른 형식)을 로드하고 WAV로 변환
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
        wav_buffer = io.BytesIO()
        audio_segment.export(wav_buffer, format="wav")
        wav_buffer.seek(0)
        audio_np, sr = sf.read(wav_buffer)
    except Exception as e:
        raise RuntimeError(f"오디오 형식 변환 또는 로드 오류: {e}") from e

    if audio_np.ndim > 1:
        audio_np = np.mean(audio_np, axis=1)  # 모노로 변환
    # 48kHz로 리샘플링 (DF 모델 요구)
    if sr != 48000:
        audio_np = librosa.resample(audio_np, orig_sr=sr, target_sr=48000)
        sr = 48000
    # DF 모델로 노이즈 제거
    model, df_state, _ = init_df()
    audio_tensor = torch.from_numpy(audio_np).float().unsqueeze(0)
    processed_tensor = enhance(model, df_state, audio_tensor, atten_lim_db=75.0)
    processed = processed_tensor.squeeze(0).cpu().numpy()
    # 메모리에서 wav로 저장
    buf = io.BytesIO()
    sf.write(buf, processed, sr, format='WAV')
    buf.seek(0)
    b64_cleaned = base64.b64encode(buf.read()).decode('utf-8')
    return f'data:audio/wav;base64,{b64_cleaned}' 