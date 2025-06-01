import base64
import numpy as np
import io
import soundfile as sf
import torch
import librosa
from pydub import AudioSegment
from demucs.pretrained import get_model
from demucs.apply import apply_model

device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = None

def load_demucs_model():
    global model
    if model is None:
        try:
            model_wrapper = get_model('htdemucs').to(device)
            # 이 경로를 Colab에서 모델 파일을 저장한 실제 경로로 변경해야 합니다.
            # 예: 'models/noise_reduction/epoch_30_data_200.th'
            model_path = 'models/noise_reduction/epoch_30_data_200.th'
            
            state_dict = torch.load(model_path, map_location=device)
            model_wrapper.models[0].load_state_dict(state_dict)
            model = model_wrapper.models[0].eval()
            print(f"Demucs 모델이 {device}에 로드되었습니다.")
        except Exception as e:
            print(f"Demucs 모델 로드 중 오류 발생: {e}")
            raise

def clean_noise_from_base64(audio_b64: str) -> str:
    """
    base64로 인코딩된 오디오(wav/mp3) 데이터를 받아 노이즈 제거 후 base64로 반환
    """
    global model
    if model is None:
        load_demucs_model()

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
        audio_np = np.mean(audio_np, axis=1) # 모노로 변환

    # 48kHz로 리샘플링 (Demucs 모델 요구)
    if sr != 48000:
        audio_np = librosa.resample(audio_np, orig_sr=sr, target_sr=48000)
        sr = 48000

    # Demucs는 스테레오 입력을 선호합니다. 모노인 경우 스테레오로 변환합니다.
    if audio_np.ndim == 1:
        audio_np = np.stack([audio_np, audio_np], axis=0) # (2, samples) 형태로 변환
    elif audio_np.ndim > 1 and audio_np.shape[1] == 2: # 이미 스테레오인 경우
        audio_np = audio_np.T # (samples, channels) -> (channels, samples)
    else: # 기타 다채널인 경우
        audio_np = audio_np[:, :2].T # (samples, channels) -> (channels, samples)

    # NumPy 배열을 PyTorch 텐서로 변환 (Demucs apply_model은 (channels, samples)를 기대)
    if audio_np.ndim == 1:
        audio_tensor = torch.from_numpy(audio_np).float().unsqueeze(0) # (1, samples)
    else: # 스테레오 이상
        audio_tensor = torch.from_numpy(audio_np.T).float() # (channels, samples)

    # Demucs의 apply_model을 사용하여 노이즈 제거
    # apply_model 함수가 내부적으로 device 이동, chunking, padding 등을 처리
    # (model, mix, samplerate)
    processed_tensor = apply_model(model, audio_tensor.unsqueeze(0).to(device), sr) # (batch, channels, samples)

    # 출력 텐서 처리: Demucs 모델의 출력은 (batch, channels, samples) 형태
    # processed_tensor는 (1, num_sources, channels, samples) 형태일 수 있음.
    # 우리의 경우 'noise removal'이므로, 'noise' 소스를 제외한 다른 소스를 합치거나
    # 'vocals'와 같은 'clean' 소스만 남기는 로직이 필요할 수 있습니다.
    # 팀원의 모델 훈련 목표에 따라 이 로직이 달라질 수 있습니다.
    # 현재는 전체 신호를 복원하는 방식으로 진행합니다.
    
    # htdemucs 모델은 (batch, sources, channels, samples) 형태를 반환.
    # sources: ['bass', 'drums', 'other', 'vocals']
    # 여기서는 'other' (음악 외 잡음) 소스를 제거하고 나머지 소스를 합친다고 가정합니다.
    # 만약 팀원 모델이 'noise'라는 특정 소스를 분리하도록 훈련되었다면,
    # 해당 소스를 제외하고 합칩니다.
    # 일단은 기존 로직대로 모든 소스를 합치는 방식을 유지하되,
    # apply_model의 출력 형태에 맞춰 수정합니다.
    
    # apply_model의 출력은 (batch, channels, samples) 형태이거나
    # (batch, sources, channels, samples) 형태일 수 있습니다.
    # Demucs는 sources를 분리하므로, 우리가 필요로 하는 '깨끗한' 소스를 선택해야 합니다.
    # 여기서는 팀원의 원본 코드를 기반으로, 모든 소스를 합친 최종 결과가 아닌,
    # 분리된 소스 중 '음악' 관련 소스들을 합쳐서 최종 출력으로 가정합니다.
    # 만약 'noise' 소스를 분리했다면, 해당 소스 인덱스를 제외하고 합칩니다.
    
    # apply_model은 (batch, channels, samples) 형태를 반환합니다.
    processed = processed_tensor.squeeze(0).cpu().numpy() # (channels, samples)

    # 처리된 오디오가 단일 채널이라면 다시 1차원 배열로 변환
    if processed.shape[0] == 1:
        processed = processed.squeeze(0) # (samples,)
    elif processed.shape[0] == 2: # 스테레오인 경우 (channels, samples) -> (samples, channels)
        processed = processed.T

    # 메모리에서 wav로 저장
    buf = io.BytesIO()
    sf.write(buf, processed, sr, format='WAV')
    buf.seek(0)
    b64_cleaned = base64.b64encode(buf.read()).decode('utf-8')
    return f'data:audio/wav;base64,{b64_cleaned}' 