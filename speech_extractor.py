import librosa
import numpy as np
import re
import os
import av
from faster_whisper import WhisperModel
from audio_processor import AudioProcessor


def _load_waveform(audio_path):
    try:
        return librosa.load(audio_path, sr=None)
    except Exception:
        with av.open(audio_path) as container:
            audio_stream = next((stream for stream in container.streams if stream.type == "audio"), None)
            if audio_stream is None:
                raise ValueError("The uploaded video does not contain an audio track")
            samples = []
            sample_rate = audio_stream.rate or 16000
            for frame in container.decode(audio_stream):
                data = frame.to_ndarray()
                if data.ndim == 2:
                    data = data.mean(axis=0)
                samples.append(data.astype(np.float32) / 32768.0)
        if not samples:
            raise ValueError("The audio track contains no decodable samples")
        return np.concatenate(samples), sample_rate


class SpeakingSkillsAnalyzer:
    def __init__(self, whisper_size="tiny", audio_processor=None):
        self.audio_processor = audio_processor or AudioProcessor()
        # Use a cached model when available; a missing model must not block grading.
        allow_download = os.getenv("ALLOW_WHISPER_DOWNLOAD", "0") == "1"
        try:
            self.transcribe_model = WhisperModel(
                whisper_size,
                device="cpu",
                compute_type="int8",
                local_files_only=not allow_download,
            )
        except Exception:
            self.transcribe_model = None

    def extract_audio_features(self, audio_path):
        # Transcription enriches the report, but waveform metrics remain usable without it.
        transcript = ""
        duration_sec = 1.0
        avg_word_prob = 0.0
        processed_audio = None
        try:
            processed_audio, trimmed_duration = self.audio_processor.prepare(audio_path)
            if self.transcribe_model is not None:
                segments, info = self.transcribe_model.transcribe(str(processed_audio), beam_size=1)
                segments = list(segments)
                transcript = " ".join([segment.text for segment in segments]).strip()
                probabilities = [float(segment.avg_logprob) for segment in segments if hasattr(segment, "avg_logprob")]
                if probabilities:
                    avg_word_prob = float(np.exp(np.mean(probabilities)))
                duration_sec = info.duration if info.duration > 0 else trimmed_duration
            else:
                duration_sec = trimmed_duration

            y, sr = librosa.load(processed_audio, sr=None, mono=True)
        finally:
            if processed_audio is not None:
                self.audio_processor.cleanup(processed_audio)

        # 1. Words Per Minute (Pace Calculation)
        words = re.findall(r'\b\w+\b', transcript.lower())
        word_count = len(words)
        # Load the waveform before deriving duration when Whisper is unavailable.
        wpm = (word_count / duration_sec) * 60

        # 2. Filler Word Counter
        filler_list = ["um", "uh", "like", "you know", "actually", "basically", "so"]
        filler_count = sum(len(re.findall(rf'\b{f}\b', transcript.lower())) for f in filler_list)

        # 3. Pitch & Pitch Variation (Monotone Detection) using Librosa
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        pitch_per_frame = []
        pitch_semitones_per_frame = []
        for frame_index in range(pitches.shape[1]):
            frame_magnitudes = magnitudes[:, frame_index]
            if not np.any(frame_magnitudes):
                continue
            pitch_index = int(np.argmax(frame_magnitudes))
            pitch_value = float(pitches[pitch_index, frame_index])
            if 60 <= pitch_value <= 500:
                pitch_per_frame.append(pitch_value)
                pitch_semitones_per_frame.append(float(12 * np.log2(pitch_value)))
        pitch_std = float(np.std(pitch_per_frame)) if pitch_per_frame else 0.0
        pitch_variation_semitones = (
            float(np.std(pitch_semitones_per_frame)) if pitch_semitones_per_frame else 0.0
        )

        # 4. Silence / Long Pause Detection
        intervals = librosa.effects.split(y, top_db=30) # Detect vocal activity
        vocal_time = sum([(end - start)/sr for start, end in intervals])
        duration_sec = len(y) / sr
        vocal_time = min(vocal_time, duration_sec)
        pause_time = max(0.0, duration_sec - vocal_time)
        speech_ratio = min(1.0, vocal_time / max(duration_sec, 1))
        rms = librosa.feature.rms(y=y)[0]
        energy_variation = float(np.std(rms) / max(np.mean(rms), 1e-6)) if len(rms) else 0.0

        return {
            "transcript": transcript,
            "duration_sec": round(duration_sec, 2),
            "word_count": word_count,
            "wpm": round(wpm, 1),
            "filler_count": filler_count,
            "pitch_variation": round(pitch_std, 2),
            "pitch_variation_semitones": round(pitch_variation_semitones, 3),
            "pause_seconds": round(pause_time, 2),
            "speech_ratio": round(speech_ratio, 3),
            "energy_variation": round(energy_variation, 3),
            "avg_word_prob": round(avg_word_prob, 4),
        }