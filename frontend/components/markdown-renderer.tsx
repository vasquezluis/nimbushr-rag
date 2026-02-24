import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import type { MarkdownRendererProps } from "@/types/chat";

export function MarkdownRenderer({
  content,
  className,
}: MarkdownRendererProps) {
  return (
    <div className={cn("markdown-content", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Headings
          h1: ({ node, ...props }) => (
            <h1
              className="text-xl font-bold text-white/95 mt-6 mb-4 first:mt-0"
              {...props}
            />
          ),
          h2: ({ node, ...props }) => (
            <h2
              className="text-lg font-bold text-white/95 mt-8 mb-3 first:mt-0 border-b border-white/10 pb-1"
              {...props}
            />
          ),

          h3: ({ node, ...props }) => (
            <h3
              className="text-base font-semibold text-white/90 mt-6 mb-2 first:mt-0 tracking-wide"
              {...props}
            />
          ),
          h4: ({ node, ...props }) => (
            <h4
              className="text-sm font-semibold text-white/85 mt-3 mb-2 first:mt-0"
              {...props}
            />
          ),

          // Paragraphs
          p: ({ node, ...props }) => (
            <p
              className="text-white/90 leading-relaxed mb-3 last:mb-0"
              {...props}
            />
          ),

          // Lists - Fixed to prevent numbers appearing above content
          ul: ({ node, ...props }) => (
            <ul
              className="list-disc mb-3 pl-6 space-y-1 marker:text-white/50"
              {...props}
            />
          ),
          ol: ({ node, ...props }) => (
            <ol
              className="list-decimal mb-3 pl-6 space-y-1 marker:text-white/60 marker:font-medium"
              {...props}
            />
          ),
          li: ({ node, ...props }) => (
            <li className="text-white/90 leading-relaxed pl-1.5" {...props} />
          ),

          // Code blocks
          // biome-ignore lint/suspicious/noExplicitAny: Change type to anything else someday
          code: ({ inline, className, children, ...props }: any) => {
            if (inline) {
              return (
                <code
                  className="px-1.5 py-0.5 rounded bg-white/10 text-blue-300 font-mono text-[0.85rem] border border-white/15"
                  {...props}
                >
                  {children}
                </code>
              );
            }

            return (
              <code
                className={cn(
                  "block font-mono text-[0.85rem] leading-relaxed text-green-300",
                  className,
                )}
                {...props}
              >
                {children}
              </code>
            );
          },

          pre: ({ ...props }) => (
            <pre
              className="my-4 rounded-xl bg-black/50 border border-white/10 shadow-inner overflow-x-auto"
              {...props}
            />
          ),

          // Blockquotes
          blockquote: ({ node, ...props }) => (
            <blockquote
              className="border-l-4 border-blue-500/50 pl-4 py-2 my-4 italic text-white/80 bg-white/5 rounded-r"
              {...props}
            />
          ),

          // Links
          a: ({ node, ...props }) => (
            <a
              className="text-blue-400 hover:text-blue-300 underline underline-offset-2 transition-colors"
              target="_blank"
              rel="noopener noreferrer"
              {...props}
            />
          ),

          // Tables
          table: ({ node, ...props }) => (
            <div className="overflow-x-auto my-4">
              <table
                className="min-w-full divide-y divide-white/10 border border-white/10 rounded-lg overflow-hidden"
                {...props}
              />
            </div>
          ),
          thead: ({ node, ...props }) => (
            <thead className="bg-white/5" {...props} />
          ),
          tbody: ({ node, ...props }) => (
            <tbody className="divide-y divide-white/10" {...props} />
          ),
          tr: ({ node, ...props }) => (
            <tr className="hover:bg-white/5 transition-colors" {...props} />
          ),
          th: ({ node, ...props }) => (
            <th
              className="px-4 py-2 text-left text-xs font-semibold text-white/80 uppercase tracking-wider"
              {...props}
            />
          ),
          td: ({ node, ...props }) => (
            <td className="px-4 py-2 text-sm text-white/90" {...props} />
          ),

          // Horizontal rule
          hr: ({ ...props }) => (
            <hr
              className="my-8 border-0 h-px bg-linear-to-r from-transparent via-white/20 to-transparent"
              {...props}
            />
          ),

          // Strong/Bold
          strong: ({ node, ...props }) => (
            <strong className="font-bold text-white/95" {...props} />
          ),

          // Emphasis/Italic
          em: ({ node, ...props }) => (
            <em className="italic text-white/90" {...props} />
          ),

          // Delete/Strikethrough
          del: ({ node, ...props }) => (
            <del className="line-through text-white/70" {...props} />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
