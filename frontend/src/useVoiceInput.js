import { useState, useRef, useCallback } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

/**
 * Server-side transcription via MediaRecorder + upload, replacing the
 * browser SpeechRecognition approach (unreliable across Brave/Firefox/
 * Chrome). Records locally, uploads once you stop recording, gets text
 * back from the backend (which uses Gemini). Same hook API as before
 * (isSupported, isListening, error, startListening, stopListening) so
 * ChatInput.jsx needs no changes - plus a new isTranscribing flag for
 * the upload-in-progress moment.
 */
export function useVoiceInput() {
  const [isListening, setIsListening] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [error, setError] = useState(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const onResultRef = useRef(null);

  const isSupported =
    typeof navigator !== 'undefined' &&
    !!navigator.mediaDevices &&
    typeof MediaRecorder !== 'undefined';

  const startListening = useCallback(async (onResult) => {
    if (!isSupported || isListening) return;
    setError(null);
    onResultRef.current = onResult;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        setIsTranscribing(true);

        try {
          const formData = new FormData();
          formData.append('file', blob, 'voice-input.webm');

          const res = await fetch(`${API_BASE_URL}/voice/transcribe`, {
            method: 'POST',
            body: formData,
          });

          if (!res.ok) {
            const payload = await res.json().catch(() => null);
            throw new Error(payload?.detail || 'Could not transcribe your voice input.');
          }

          const { transcript } = await res.json();
          if (onResultRef.current) onResultRef.current(transcript);
        } catch (err) {
          setError(err.message || 'Voice input failed. Please try typing instead.');
        } finally {
          setIsTranscribing(false);
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsListening(true);
    } catch {
      setError('Microphone access was denied. Enable it in your browser settings to use voice input.');
      setIsListening(false);
    }
  }, [isSupported, isListening]);

  const stopListening = useCallback(() => {
    if (mediaRecorderRef.current && isListening) {
      mediaRecorderRef.current.stop();
      setIsListening(false);
    }
  }, [isListening]);

  return { isSupported, isListening, isTranscribing, error, startListening, stopListening };
}
