import type { ChatRequest, StreamEvent } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export class TravelPlannerAPI {
  private sessionId: string | null = null;
  private currentReader: ReadableStreamDefaultReader<Uint8Array> | null = null;
  private abortController: AbortController | null = null;

  /**
   * Abort current streaming request
   */
  abortStream(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
    if (this.currentReader) {
      this.currentReader.cancel();
      this.currentReader = null;
    }
  }

  /**
   * Create a streaming connection to the chat endpoint
   */
  async streamChat(
    message: string,
    onEvent: (event: StreamEvent) => void,
    onError: (error: Error) => void,
    onComplete: () => void
  ): Promise<void> {
    // Abort any existing stream
    this.abortStream();

    // Create new AbortController for this request
    this.abortController = new AbortController();

    const request: ChatRequest = {
      message,
      session_id: this.sessionId || undefined,
    };

    try {
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
        signal: this.abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error("Response body is null");
      }

      this.currentReader = reader;

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          this.currentReader = null;
          this.abortController = null;
          onComplete();
          break;
        }

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6)) as StreamEvent;

              // Store session ID from first event
              if (data.session_id && !this.sessionId) {
                this.sessionId = data.session_id;
              }

              onEvent(data);
            } catch (e) {
              console.warn("Failed to parse SSE data:", line, e);
            }
          }
        }
      }
    } catch (error) {
      // Clean up on error
      this.currentReader = null;
      this.abortController = null;

      // Don't report error if it was an intentional abort
      if ((error as Error).name !== "AbortError") {
        onError(error as Error);
      }
    }
  }

  /**
   * Get current session info
   */
  async getSession(sessionId: string): Promise<StreamEvent> {
    const response = await fetch(`${API_BASE_URL}/session/${sessionId}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  }

  /**
   * Delete current session
   */
  async deleteSession(sessionId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/session/${sessionId}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    this.sessionId = null;
  }

  /**
   * Reset session ID
   */
  resetSession(): void {
    this.sessionId = null;
  }

  /**
   * Get current session ID
   */
  getSessionId(): string | null {
    return this.sessionId;
  }
}

export const apiClient = new TravelPlannerAPI();
