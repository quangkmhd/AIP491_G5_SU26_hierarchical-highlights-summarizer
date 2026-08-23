import { useState, useRef, useEffect, useCallback } from 'react';

const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8080';

async function getAudioStream() {
  if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    return await navigator.mediaDevices.getUserMedia({ audio: true });
  }

  const legacyGetUserMedia =
    navigator.getUserMedia ||
    navigator.webkitGetUserMedia ||
    navigator.mozGetUserMedia ||
    navigator.msGetUserMedia;

  if (legacyGetUserMedia) {
    return new Promise((resolve, reject) => {
      legacyGetUserMedia.call(navigator, { audio: true }, resolve, reject);
    });
  }

  throw new Error(
    'Microphone access requires a Secure Context. Please open the app at http://localhost:8501 (or http://127.0.0.1:8501) instead of an IP/domain.'
  );
}

export function useWebSocketAudio(activeSessionId, onUtteranceReceived, onSummaryReceived) {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);

  const socketRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const timerIntervalRef = useRef(null);
  const isRecordingRef = useRef(false);

  // Stop current recording session
  const stopRecording = useCallback(() => {
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

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      try {
        socketRef.current.send(JSON.stringify({ type: 'finish' }));
      } catch (e) {}
    }
  }, []);

  // Start real-time audio recording & WebSocket stream
  const startRecording = useCallback(async () => {
    if (!activeSessionId) {
      alert('Please select or create a session first.');
      return;
    }

    try {
      // 1. Acquire mic stream first before establishing WebSocket
      const stream = await getAudioStream();
      mediaStreamRef.current = stream;

      const wsUrl = `${WS_BASE_URL}/ws/sessions/${activeSessionId}/stream`;
      const socket = new WebSocket(wsUrl);
      socketRef.current = socket;

      socket.onopen = () => {
        console.log('WebSocket connected:', wsUrl);
        try {
          isRecordingRef.current = true;
          setIsRecording(true);
          setRecordingTime(0);

          timerIntervalRef.current = setInterval(() => {
            setRecordingTime((prev) => prev + 1);
          }, 1000);

          function recordNextChunk() {
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

              mediaRecorder.onstop = () => {
                const blob = new Blob(chunks, { type: mediaRecorder.mimeType });
                if (blob.size > 0 && socket.readyState === WebSocket.OPEN && isRecordingRef.current) {
                  socket.send(blob);
                }

                if (isRecordingRef.current) {
                  recordNextChunk();
                }
              };

              mediaRecorder.start();

              setTimeout(() => {
                if (mediaRecorder.state === 'recording') {
                  mediaRecorder.stop();
                }
              }, 2500);
            } catch (err) {
              console.error('Error in MediaRecorder slice:', err);
            }
          }

          recordNextChunk();
        } catch (err) {
          console.error('Microphone error:', err);
          alert(`Microphone Error: ${err.message}`);
          stopRecording();
        }
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'utterance-emitted' && data.utterance) {
            onUtteranceReceived?.(data.utterance);
          } else if (data.type === 'session-completed' && data.result) {
            if (data.result.summary) {
              onSummaryReceived?.(data.result.summary);
            }
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      socket.onerror = (err) => {
        console.error('WebSocket Error:', err);
      };

      socket.onclose = () => {
        console.log('WebSocket connection closed.');
      };
    } catch (err) {
      console.error('Failed to initiate recording:', err);
      alert(`Microphone Error: ${err.message}`);
    }
  }, [activeSessionId, onUtteranceReceived, onSummaryReceived, stopRecording]);

  useEffect(() => {
    return () => {
      stopRecording();
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [stopRecording]);

  return {
    isRecording,
    recordingTime,
    startRecording,
    stopRecording,
  };
}
