"use client";

import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "@/components/message-bubble";
import { Loader2 } from "lucide-react";
import { MessageListProps } from "@/types/chat";

export function MessageList({
  messages,
  isLoading,
  messagesEndRef,
  status,
}: MessageListProps) {
  return (
    <ScrollArea className="h-full">
      <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        {messages.map((message, index) => (
          <MessageBubble
            key={message.id}
            message={message}
            isLatest={index === messages.length - 1}
          />
        ))}

        {isLoading && status && (
          <div className="flex items-start gap-4 animate-in fade-in slide-in-from-bottom-4 duration-300">
            <div className="w-8 h-8 rounded-full bg-linear-to-br from-white/10 to-white/5 flex items-center justify-center border border-white/10">
              <Loader2 className="h-4 w-4 text-white/60 animate-spin" />
            </div>
            <div className="flex-1 space-y-3 mt-1">
              <p className="text-sm text-white/60">{status}</p>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </ScrollArea>
  );
}
