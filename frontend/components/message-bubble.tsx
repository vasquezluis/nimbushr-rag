"use client";

import { format } from "date-fns";
import { User, Bot, FileText, Table, Image, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { MessageBubbleProps } from "@/types/chat";

export function MessageBubble({ message, isLatest }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex gap-4 ${isUser ? "flex-row-reverse" : "flex-row"} group animate-in fade-in slide-in-from-bottom-4 duration-500`}
    >
      {/* Avatar */}
      <div
        className={`
        w-8 h-8 rounded-full flex items-center justify-center -shrink-0
        ${
          isUser
            ? "bg-linear-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/30"
            : "bg-linear-to-br from-white/10 to-white/5 border border-white/10"
        }
      `}
      >
        {isUser ? (
          <User className="h-4 w-4 text-blue-400" />
        ) : (
          <Bot className="h-4 w-4 text-white/60" />
        )}
      </div>

      {/* Message Content */}
      <div
        className={`flex-1 space-y-2 ${isUser ? "items-end" : "items-start"} flex flex-col max-w-2xl`}
      >
        {/* Message Bubble */}
        <div
          className={`
          rounded-2xl px-5 py-3.5 relative
          ${
            isUser
              ? "bg-linear-to-br from-blue-500/10 to-purple-500/10 border border-blue-500/20 ml-auto"
              : "bg-white/5 border border-white/10 backdrop-blur-sm"
          }
        `}
        >
          <p className="text-white/90 text-[15px] leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>

          {/* Streaming Indicator */}
          {message.isStreaming && (
            <div className="mt-2 flex items-center gap-1">
              <div className="w-1.5 h-1.5 bg-white/40 rounded-full animate-pulse" />
              <div
                className="w-1.5 h-1.5 bg-white/40 rounded-full animate-pulse"
                style={{ animationDelay: "0.2s" }}
              />
              <div
                className="w-1.5 h-1.5 bg-white/40 rounded-full animate-pulse"
                style={{ animationDelay: "0.4s" }}
              />
            </div>
          )}
        </div>

        {/* Sources */}
        {message.sources && message.sources.length > 0 && (
          <div className="space-y-2 w-full">
            <p className="text-xs text-white/40 font-medium px-1">Sources:</p>
            <div className="space-y-1.5">
              {message.sources.map((source, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-2 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 hover:bg-white/8 hover:border-white/15 transition-all duration-200 group/source"
                >
                  <FileText className="h-3.5 w-3.5 text-white/40 shrink-0" />
                  <span className="text-xs text-white/60 font-mono flex-1 truncate">
                    {source.file}
                  </span>
                  <span className="text-xs text-white/30">
                    #{source.chunk_index}
                  </span>
                  <div className="flex gap-1">
                    {source.ai_summarized && (
                      <Badge
                        variant="outline"
                        className="h-5 px-1.5 text-[10px] bg-purple-500/10 border-purple-500/30 text-purple-300 hover:bg-purple-500/20"
                      >
                        <Sparkles className="h-2.5 w-2.5 mr-0.5" />
                        AI
                      </Badge>
                    )}
                    {source.has_tables && (
                      <Badge
                        variant="outline"
                        className="h-5 px-1.5 text-[10px] bg-green-500/10 border-green-500/30 text-green-300"
                      >
                        <Table className="h-2.5 w-2.5 mr-0.5" />
                      </Badge>
                    )}
                    {source.has_images && (
                      <Badge
                        variant="outline"
                        className="h-5 px-1.5 text-[10px] bg-blue-500/10 border-blue-500/30 text-blue-300"
                      >
                        <Image className="h-2.5 w-2.5 mr-0.5" />
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Timestamp */}
        <p className="text-xs text-white/30 px-1">
          {format(message.timestamp, "HH:mm")}
        </p>
      </div>
    </div>
  );
}
