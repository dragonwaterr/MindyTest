import os
import shutil
import torch
import torchaudio
import uvicorn, nest_asyncio
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from tempfile import TemporaryDirectory
from demucs.pretrained import get_model

from services.stt_tts_service import STT_TTSService
from services.translation_service import TranslationService
from services.ocr_service import OCRService
from services.cleanNoise import clean_noise_from_base64

nest_asyncio.apply()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === 절대경로 고정 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 서비스 인스턴스
stt_tts = STT_TTSService()
translator = TranslationService()
ocr_service = OCRService()

# Demucs 모델 준비
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model_wrapper = get_model('htdemucs').to(device)
model = model_wrapper.models[0].to(device)
model.load_state_dict(torch.load(os.path.join(BASE_DIR, 'outputs', 'epoch_30_data_200.th'), map_location=device))
model.eval()

@app.post("/api/clean-noise")
async def clean_noise(audio_data: str = Form(...)):
    try:
        cleaned_b64 = clean_noise_from_base64(audio_data)
        return {"cleanedAudio": cleaned_b64}
    except Exception as e:
        print(f"[ERROR /api/clean-noise] {str(e)}")
        return {"error": str(e)}

@app.post("/api/stt")
async def stt(audio_data: str = Form(...), source_lang: str = Form(...)):
    try:
        cleaned = clean_noise_from_base64(audio_data)
        text = await stt_tts.speech_to_text(cleaned, source_lang)
        return {"recognizedText": text, "cleanedAudio": cleaned}
    except Exception as e:
        print(f"[ERROR /api/stt] {str(e)}")
        return {"error": str(e)}

@app.post("/api/translate-text")
async def translate_text(text: str = Form(...), source_lang: str = Form(...), target_lang: str = Form(...)):
    try:
        translated = await translator.translate(text, source_lang, target_lang)
        return {"translatedText": translated}
    except Exception as e:
        print(f"[ERROR /api/translate-text] {str(e)}")
        return {"error": str(e)}

@app.post("/api/tts")
async def tts(text: str = Form(...), target_lang: str = Form(...)):
    try:
        audio_b64 = await stt_tts.text_to_speech(text, target_lang)
        return {"audioData": audio_b64}
    except Exception as e:
        print(f"[ERROR /api/tts] {str(e)}")
        return {"error": str(e)}

@app.post("/api/ocr-translate")
async def ocr_translate(file: UploadFile = File(...), source_lang: str = Form(...), target_lang: str = Form(...)):
    try:
        ocr_text = await ocr_service.extract_text(file)
        translated = await translator.translate(ocr_text, source_lang, target_lang)
        return {"ocrText": ocr_text, "translation": translated}
    except Exception as e:
        print(f"[ERROR /api/ocr-translate] {str(e)}")
        return {"error": str(e)}

@app.post("/api/denoise-upload")
async def denoise_upload(noisy_file: UploadFile = File(...)):
    try:
        with TemporaryDirectory() as tmpdir:
            noisy_path = os.path.join(STATIC_DIR, noisy_file.filename)
            output_path = os.path.join(STATIC_DIR, f"denoised_{noisy_file.filename}")

            with open(noisy_path, 'wb') as f:
                shutil.copyfileobj(noisy_file.file, f)

            noisy, sr = torchaudio.load(noisy_path)

            if noisy.shape[0] == 1:
                noisy = noisy.repeat(2, 1)

            noisy_input = noisy.unsqueeze(0).to(device)

            with torch.no_grad():
                estimate = model(noisy_input).cpu()

            if estimate.dim() == 4:
                estimate_to_save = estimate[0].sum(dim=0)
            elif estimate.dim() == 3:
                estimate_to_save = estimate[0]
            else:
                estimate_to_save = estimate

            torchaudio.save(output_path, estimate_to_save, sr)

            print(f"[INFO] Saved original: {noisy_path}")
            print(f"[INFO] Saved denoised: {output_path}")

            return {
                "originalFile": f"/static/{noisy_file.filename}",
                "denoisedFile": f"/static/denoised_{noisy_file.filename}"
            }
    except Exception as e:
        print(f"[ERROR /api/denoise-upload] {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    try:
        from pyngrok import ngrok
        public_url = ngrok.connect(8000, "http")
        print(f"[NGROK URL] {public_url.public_url}")
    except Exception as e:
        print("[NGROK ERROR]", e)
    uvicorn.run(app, host="0.0.0.0", port=8000)
