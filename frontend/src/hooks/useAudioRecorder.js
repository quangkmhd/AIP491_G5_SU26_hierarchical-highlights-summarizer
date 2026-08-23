import { useState, useRef, useEffect, useCallback } from 'react';
import { sendAudioChunk } from '../services/api';

export function useAudioRecorder(activeSessionId) {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);

  const mediaStreamRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const timerIntervalRef = useRef(null);
  const isRecordingRef = useRef(false);

  // Start continuous 3.5s chunk recording loop
  const startChunkLoop = useCallback((stream) => {
    if (!isRecordingRef.current) return;

    try {
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      const chunks = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          chunks.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunks, { type: mediaRecorder.mimeType });
        if (blob.size > 0 && activeSessionId && isRecordingRef.current) {
          await sendAudioChunk(activeSessionId, blob, 'live_stream_chunk.wav');
        }

        // Loop next chunk if still recording
        if (isRecordingRef.current) {
          startChunkLoop(stream);
        }
      };

      mediaRecorder.start();

      // Stop slice after 3.5 seconds
      setTimeout(() => {
        if (mediaRecorder.state === 'recording') {
          mediaRecorder.stop();
        }
      }, 3500);
    } catch (err) {
      console.error('Failed to start MediaRecorder slice:', err);
    }
  }, [activeSessionId]);

  const startRecording = async () => {
    if (!activeSessionId) {
      alert('Please select or create a session first.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      isRecordingRef.current = true;
      setIsRecording(true);
      setRecordingTime(0);

      // Start timer
      timerIntervalRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);

      // Start audio chunk streaming loop
      startChunkLoop(stream);
    } catch (err) {
      console.error('Microphone access denied or error:', err);
      alert(`Microphone Error: ${err.message}`);
    }
  };

  const stopRecording = () => {
    isRecordingRef.current = false;
    setIsRecording(false);

    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop();
      } catch (e) {}
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      stopRecording();
    };
  }, []);

  return {
    isRecording,
    recordingTime,
    startRecording,
    stopRecording,
  };
}
