const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8080';

export async function fetchSessions() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/sessions`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.sessions || [];
  } catch (err) {
    console.error('Failed to fetch sessions:', err);
    return [];
  }
}

export async function createSession(title, meetingType = 'online_live', file = null) {
  try {
    const formData = new FormData();
    if (title) formData.append('title', title);
    formData.append('meeting_type', meetingType);
    if (file) formData.append('file', file);

    const res = await fetch(`${BACKEND_URL}/api/v1/sessions`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.session;
  } catch (err) {
    console.error('Failed to create session:', err);
    throw err;
  }
}

export async function getSessionDetails(sessionId) {
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/sessions/${sessionId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`Failed to fetch details for session ${sessionId}:`, err);
    return null;
  }
}

export async function sendAudioChunk(sessionId, audioBlob, filename = 'live_stream_chunk.wav') {
  try {
    const formData = new FormData();
    formData.append('file', audioBlob, filename);

    const res = await fetch(`${BACKEND_URL}/api/v1/sessions/${sessionId}/audio`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`Failed to send audio chunk for session ${sessionId}:`, err);
    return null;
  }
}

export async function deleteSession(sessionId) {
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/sessions/${sessionId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`Failed to delete session ${sessionId}:`, err);
    throw err;
  }
}

export async function renameSession(sessionId, newTitle) {
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/sessions/${sessionId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: newTitle }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`Failed to rename session ${sessionId}:`, err);
    throw err;
  }
}
