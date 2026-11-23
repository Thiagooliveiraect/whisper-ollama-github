"""Whisper audio transcription and Ollama key-point extraction application."""
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import requests
from faster_whisper import WhisperModel

OLLAMA_API = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"
WHISPER_MODEL = "base"
SUPPORTED_EXTENSIONS = {".wav", ".mp3"}


def transcribe_audio(audio_path: Path) -> str:
    """Transcribe an audio file in Portuguese using faster-whisper."""
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(audio_path), language="pt")
    text = " ".join(segment.text.strip() for segment in segments).strip()
    if not text:
        raise ValueError("Nenhuma fala foi identificada no áudio.")
    return text


def summarize_with_ollama(transcript: str) -> str:
    """Send the transcript to Ollama and return summary and key points."""
    prompt = f"""Analise a transcrição em português abaixo. Não invente informações.
Organize a resposta em: 1) Resumo breve; 2) de 5 a 10 pontos-chave;
3) Conclusão curta.

TRANSCRIÇÃO:
{transcript}
"""
    response = requests.post(
        OLLAMA_API,
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=600,
    )
    response.raise_for_status()
    result = response.json().get("response", "").strip()
    if not result:
        raise ValueError("O Ollama retornou uma resposta vazia.")
    return result


def save_result(audio_path: Path, transcript: str, summary: str) -> Path:
    """Save transcript and generated summary beside the input audio."""
    output = audio_path.with_name(f"{audio_path.stem}_resultado.txt")
    output.write_text(
        "TRANSCRIÇÃO DO ÁUDIO\n====================\n\n"
        f"{transcript}\n\nRESUMO E PONTOS-CHAVE (OLLAMA)\n"
        "==============================\n\n"
        f"{summary}\n",
        encoding="utf-8",
    )
    return output


class AudioSummaryApp:
    def __init__(self, window: tk.Tk):
        self.window = window
        window.title("Whisper + Ollama | Transcrição de Áudio")
        window.geometry("600x320")
        window.resizable(False, False)
        tk.Label(window, text="Transcrição de Áudio e Pontos-Chave",
                 font=("Segoe UI", 16, "bold")).pack(pady=(25, 10))
        tk.Label(window,
                 text="Selecione um arquivo .wav ou .mp3.\n"
                      "O Whisper transcreve e o Ollama gera um resumo.",
                 font=("Segoe UI", 10), justify="center").pack(pady=8)
        self.button = tk.Button(window, text="Selecionar áudio e processar",
                               command=self.select_audio, padx=16, pady=9)
        self.button.pack(pady=18)
        self.status = tk.StringVar(value="Pronto para iniciar.")
        tk.Label(window, textvariable=self.status, wraplength=540).pack(pady=8)
        tk.Label(window, text=f"Whisper: {WHISPER_MODEL} | Ollama: {OLLAMA_MODEL}",
                 fg="gray").pack(side="bottom", pady=14)

    def select_audio(self):
        filename = filedialog.askopenfilename(
            title="Selecione um arquivo de áudio",
            filetypes=[("Áudios", "*.wav *.mp3"), ("Todos os arquivos", "*.*")],
        )
        if not filename:
            return
        audio = Path(filename)
        if audio.suffix.lower() not in SUPPORTED_EXTENSIONS:
            messagebox.showerror("Formato inválido", "Escolha um arquivo .wav ou .mp3.")
            return
        self.button.config(state="disabled")
        self.status.set("Processando áudio... Aguarde.")
        threading.Thread(target=self.process_audio, args=(audio,), daemon=True).start()

    def process_audio(self, audio: Path):
        try:
            self.window.after(0, lambda: self.status.set("Etapa 1/3: transcrição Whisper..."))
            transcript = transcribe_audio(audio)
            self.window.after(0, lambda: self.status.set("Etapa 2/3: resumo Ollama..."))
            summary = summarize_with_ollama(transcript)
            self.window.after(0, lambda: self.status.set("Etapa 3/3: salvando resultado..."))
            output = save_result(audio, transcript, summary)
            self.window.after(0, lambda: self.status.set("Processamento concluído!"))
            self.window.after(0, lambda: messagebox.showinfo(
                "Concluído", f"Transcrição e resumo salvos em:\n{output}"))
        except requests.exceptions.ConnectionError:
            self.window.after(0, lambda: messagebox.showerror(
                "Ollama não encontrado",
                f"Abra o Ollama e confirme que o modelo está instalado:\nollama pull {OLLAMA_MODEL}"))
            self.window.after(0, lambda: self.status.set("Erro de conexão com Ollama."))
        except Exception as error:
            message = str(error)
            self.window.after(0, lambda: messagebox.showerror("Erro", message))
            self.window.after(0, lambda: self.status.set("O processamento apresentou um erro."))
        finally:
            self.window.after(0, lambda: self.button.config(state="normal"))


if __name__ == "__main__":
    root = tk.Tk()
    AudioSummaryApp(root)
    root.mainloop()
