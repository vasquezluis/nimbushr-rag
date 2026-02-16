"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send, Square } from "lucide-react";
import { ChatInputProps } from "@/types/chat";

export function ChatInput({
  onSendMessage,
  isLoading,
  onCancel,
}: ChatInputProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if (!input.trim() || isLoading) return;

    onSendMessage(input.trim());
    setInput("");

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  return (
    <div className="max-w-4xl mx-auto w-full px-6 py-6">
      <div className="relative flex items-end gap-3">
        {/* Input Container */}
        <div className="flex-1 relative">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your documents..."
            disabled={isLoading}
            className="
              min-h-14 max-h-50 resize-none
              bg-white/5 border-white/10 
              hover:bg-white/8 hover:border-white/15
              focus:bg-white/10 focus:border-white/20
              text-white/90 placeholder:text-white/30
              rounded-2xl px-5 py-4 pr-14
              transition-all duration-200
              focus-visible:ring-0 focus-visible:ring-offset-0
            "
            rows={1}
          />

          {/* Character Count */}
          <div className="absolute bottom-2 right-3 text-xs text-white/20">
            {input.length}
          </div>
        </div>

        {/* Send/Stop Button */}
        {isLoading ? (
          <Button
            onClick={onCancel}
            size="icon"
            className="
              h-14 w-14 rounded-2xl shrink-0
              bg-red-500/20 hover:bg-red-500/30
              border border-red-500/30 hover:border-red-500/40
              transition-all duration-200
            "
          >
            <Square className="h-5 w-5 text-red-400" fill="currentColor" />
          </Button>
        ) : (
          <Button
            onClick={handleSubmit}
            disabled={!input.trim()}
            size="icon"
            className="
              h-14 w-14 rounded-2xl shrink-0
              bg-linear-to-br from-blue-500/20 to-purple-500/20
              hover:from-blue-500/30 hover:to-purple-500/30
              border border-blue-500/30 hover:border-blue-500/40
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-all duration-200
              group
            "
          >
            <Send className="h-5 w-5 text-blue-400 group-hover:text-blue-300 transition-colors" />
          </Button>
        )}
      </div>

      {/* Helper Text */}
      <div className="mt-3 flex items-center justify-between px-1">
        <p className="text-xs text-white/30">
          Press{" "}
          <kbd className="px-1.5 py-0.5 bg-white/10 rounded text-white/40 font-mono">
            Enter
          </kbd>{" "}
          to send,{" "}
          <kbd className="px-1.5 py-0.5 bg-white/10 rounded text-white/40 font-mono">
            Shift + Enter
          </kbd>{" "}
          for new line
        </p>
      </div>
    </div>
  );
}
