"use client";

import { useState, useRef, useEffect } from "react";
import { MessageList } from "@/components/message-list";
import { ChatInput } from "@/components/chat-input";
import { useStreamingQuery } from "@/hooks/use-streaming-query";
import { Message } from "@/types/chat";

export function ChatArea() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content:
        "Hello! I'm your NimusHR Assistant. I can help you find information from your documents. Ask me anything about employee benefits, policies, or procedures.",
      timestamp: new Date(),
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const {
    sendStreamingQuery,
    cancel,
    isStreaming,
    error,
    streamingAnswer,
    sources,
    status,
  } = useStreamingQuery();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingAnswer]);

  // Update streaming message in real-time
  useEffect(() => {
    if (isStreaming && streamingAnswer) {
      setMessages((prev) => {
        const lastMessage = prev[prev.length - 1];

        // If last message is assistant and streaming, update it
        if (lastMessage?.role === "assistant" && lastMessage?.isStreaming) {
          return [
            ...prev.slice(0, -1),
            {
              ...lastMessage,
              content: streamingAnswer,
              sources: sources.length > 0 ? sources : lastMessage.sources,
            },
          ];
        }

        // Otherwise, create new streaming message
        return [
          ...prev,
          {
            id: Date.now().toString(),
            role: "assistant",
            content: streamingAnswer,
            timestamp: new Date(),
            sources: sources.length > 0 ? sources : undefined,
            isStreaming: true,
          },
        ];
      });
    }
  }, [isStreaming, streamingAnswer, sources]);

  // Finalize message when streaming completes
  useEffect(() => {
    if (!isStreaming && streamingAnswer) {
      setMessages((prev) => {
        const lastMessage = prev[prev.length - 1];
        if (lastMessage?.isStreaming) {
          return [
            ...prev.slice(0, -1),
            {
              ...lastMessage,
              isStreaming: false,
            },
          ];
        }
        return prev;
      });
    }
  }, [isStreaming, streamingAnswer]);

  // Handle errors
  useEffect(() => {
    if (error) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: "assistant",
          content: `Error: ${error}`,
          timestamp: new Date(),
        },
      ]);
    }
  }, [error]);

  const handleSendMessage = async (content: string) => {
    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);

    // Start streaming
    await sendStreamingQuery(content);
  };

  const handleCancelStreaming = () => {
    cancel();
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-[#0A0A0A]">
      {/* Messages Area */}
      <div className="flex-1 overflow-hidden">
        <MessageList
          messages={messages}
          isLoading={isStreaming}
          messagesEndRef={messagesEndRef as React.RefObject<HTMLDivElement>}
          status={status}
        />
      </div>

      {/* Input Area */}
      <div className="border-t border-white/5 bg-[#0A0A0A]">
        <ChatInput
          onSendMessage={handleSendMessage}
          isLoading={isStreaming}
          onCancel={handleCancelStreaming}
        />
      </div>
    </div>
  );
}
