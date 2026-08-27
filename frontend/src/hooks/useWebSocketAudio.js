import { useState, useRef, useEffect, useCallback } from 'react';

const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8080';
const TARGET_SAMPLE_RATE = 16000;
// const STREAM_FRAME_SAMPLES = 40000; // 2.5s per frame at 16kHz (40,000 samples)
const STREAM_FRAME_SAMPLES = 8000; // 500ms per frame at 16kHz (8,000 samples)

function writeString(view, offset, string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

function encodeWavBlob(samples, sampleRate = 16000) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  // RIFF chunk descriptor
  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(view, 8, 'WAVE');

  // fmt sub-chunk
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM format
  view.setUint16(22, 1, true); // Mono channel
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true); // 16-bit

  // data sub-chunk
  writeString(view, 36, 'data');
  view.setUint32(40, samples.length * 2, true);

  // Write Int16 PCM samples
  let offset = 44;
  for (let i = 0; i < samples.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }

  return new Blob([view], { type: 'audio/wav' });
}

function resampleTo16k(audioBuffer, origSampleRate) {
  if (origSampleRate === TARGET_SAMPLE_RATE) {
    return audioBuffer;
  }
  const ratio = origSampleRate / TARGET_SAMPLE_RATE;
  const newLength = Math.round(audioBuffer.length / ratio);
  const result = new Float32Array(newLength);
  for (let i = 0; i < newLength; i++) {
    const origIndex = i * ratio;
    const index = Math.floor(origIndex);
    const fraction = origIndex - index;
    const nextIndex = Math.min(index + 1, audioBuffer.length - 1);
    result[i] = audioBuffer[index] * (1 - fraction) + audioBuffer[nextIndex] * fraction;
  }
  return result;
}

async function getAudioStream() {
  if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    return await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: TARGET_SAMPLE_RATE,
        echoCancellation: true,
        noiseSuppression: false,
        autoGainControl: false,
      },
    });
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
  const audioContextRef = useRef(null);
  const processorNodeRef = useRef(null);
  const sourceNodeRef = useRef(null);
  const timerIntervalRef = useRef(null);
  const isRecordingRef = useRef(false);
  const sampleBufferRef = useRef([]);

  // Stop current recording session
  const stopRecording = useCallback(() => {
    isRecordingRef.current = false;
    setIsRecording(false);

    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }

    // Flush any remaining accumulated audio samples (>100ms)
    if (sampleBufferRef.current.length > 1600 && socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      const remainingSamples = new Float32Array(sampleBufferRef.current);
      sampleBufferRef.current = [];
      const wavBlob = encodeWavBlob(remainingSamples, TARGET_SAMPLE_RATE);
      try {
        socketRef.current.send(wavBlob);
      } catch (e) { }
    }

    // Disconnect Web Audio nodes
    if (processorNodeRef.current) {
      try {
        processorNodeRef.current.disconnect();
      } catch (e) { }
      processorNodeRef.current = null;
    }

    if (sourceNodeRef.current) {
      try {
        sourceNodeRef.current.disconnect();
      } catch (e) { }
      sourceNodeRef.current = null;
    }

    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      try {
        audioContextRef.current.close();
      } catch (e) { }
      audioContextRef.current = null;
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      try {
        socketRef.current.send(JSON.stringify({ type: 'finish' }));
      } catch (e) { }
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
        console.log('WebSocket connected for continuous audio stream:', wsUrl);
        try {
          isRecordingRef.current = true;
          setIsRecording(true);
          setRecordingTime(0);
          sampleBufferRef.current = [];

          timerIntervalRef.current = setInterval(() => {
            setRecordingTime((prev) => prev + 1);
          }, 1000);

          // 2. Initialize Web Audio API continuous PCM stream
          const AudioContextClass = window.AudioContext || window.webkitAudioContext;
          const audioCtx = new AudioContextClass({ sampleRate: TARGET_SAMPLE_RATE });
          audioContextRef.current = audioCtx;

          const source = audioCtx.createMediaStreamSource(stream);
          sourceNodeRef.current = source;

          // 4096 buffer size = ~256ms per buffer at 16kHz
          const processor = audioCtx.createScriptProcessor(4096, 1, 1);
          processorNodeRef.current = processor;

          processor.onaudioprocess = (e) => {
            if (!isRecordingRef.current) return;
            const inputChannel = e.inputBuffer.getChannelData(0);
            const resampled = resampleTo16k(inputChannel, audioCtx.sampleRate);

            // Accumulate samples
            for (let i = 0; i < resampled.length; i++) {
              sampleBufferRef.current.push(resampled[i]);
            }

            // Once we have 500ms (8000 samples), send a clean WAV frame
            while (sampleBufferRef.current.length >= STREAM_FRAME_SAMPLES) {
              const frameSamples = new Float32Array(
                sampleBufferRef.current.splice(0, STREAM_FRAME_SAMPLES)
              );

              if (socket.readyState === WebSocket.OPEN && isRecordingRef.current) {
                const wavBlob = encodeWavBlob(frameSamples, TARGET_SAMPLE_RATE);
                socket.send(wavBlob);
              }
            }
          };

          source.connect(processor);
          processor.connect(audioCtx.destination);
        } catch (err) {
          console.error('Continuous Audio Stream Error:', err);
          alert(`Microphone Stream Error: ${err.message}`);
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
        console.log('WebSocket stream connection closed.');
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
