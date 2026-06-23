import type { SummaryMethod, SummaryResponse, SummaryStreamEvent } from "./types";

interface SummaryRequest {
  transcript: string;
  method: SummaryMethod;
  input_name: string;
}

export async function summarizeMeeting(request: SummaryRequest): Promise<SummaryResponse> {
  const response = await fetch("/api/summarize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request)
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Summary request failed");
  }
  return payload as SummaryResponse;
}

export async function streamSummaryMeeting(
  request: SummaryRequest,
  onEvent: (event: SummaryStreamEvent) => void
): Promise<SummaryResponse> {
  const response = await fetch("/api/summarize/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request)
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }
  if (!response.body) {
    throw new Error("Summary stream did not include a response body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResponse: SummaryResponse | null = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      const event = parseStreamEvent(line);
      if (!event) {
        continue;
      }
      onEvent(event);
      if (event.event === "completed") {
        finalResponse = event.data;
      }
      if (event.event === "error") {
        throw new Error(event.data.detail || "Summary stream failed");
      }
    }
  }

  buffer += decoder.decode();
  const finalEvent = parseStreamEvent(buffer);
  if (finalEvent) {
    onEvent(finalEvent);
    if (finalEvent.event === "completed") {
      finalResponse = finalEvent.data;
    }
    if (finalEvent.event === "error") {
      throw new Error(finalEvent.data.detail || "Summary stream failed");
    }
  }

  if (!finalResponse) {
    throw new Error("Summary stream ended before sending a completed event");
  }
  return finalResponse;
}

function parseStreamEvent(line: string): SummaryStreamEvent | null {
  const trimmed = line.trim();
  if (!trimmed) {
    return null;
  }
  return JSON.parse(trimmed) as SummaryStreamEvent;
}

async function getErrorMessage(response: Response): Promise<string> {
  try {
    const payload = await response.clone().json();
    return payload.detail || "Summary request failed";
  } catch {
    return (await response.text()) || "Summary request failed";
  }
}
