"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { TownSelector } from "./TownSelector";
import { useParcelStore } from "@/store/parcel-store";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ResearchStatus {
  parcelsFound: number;
  hasZoningData: boolean;
}

export function PropertyResearch() {
  const { selectedTown } = useParcelStore();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState<ResearchStatus | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Reset messages when town changes
  useEffect(() => {
    setMessages([]);
    setStatus(null);
  }, [selectedTown]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !selectedTown || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await fetch("/api/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: userMessage,
          state: "Connecticut",
          municipality: selectedTown,
          conversationHistory: messages,
        }),
      });

      const data = await response.json();

      if (data.success && data.data) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.data.answer },
        ]);
        setStatus({
          parcelsFound: data.data.parcelsFound,
          hasZoningData: data.data.hasZoningData,
        });
      } else {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.error || "Failed to get response" },
        ]);
      }
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Error: ${error instanceof Error ? error.message : "Unknown error"}`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setMessages([]);
    setStatus(null);
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium mb-2">Property Research</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Ask questions about properties and zoning regulations. The system will search
          both the zoning PDF and property database to provide comprehensive answers.
        </p>
      </div>

      <TownSelector />

      {!selectedTown ? (
        <Alert>
          <AlertDescription>
            Select a town to start researching properties and zoning regulations.
          </AlertDescription>
        </Alert>
      ) : (
        <>
          {/* Status bar */}
          {status && (
            <div className="flex gap-4 text-sm text-muted-foreground">
              <span>
                {status.hasZoningData ? "✓ Zoning data available" : "⚠ No zoning data"}
              </span>
              <span>
                {status.parcelsFound > 0
                  ? `✓ ${status.parcelsFound} properties matched`
                  : "⚠ No properties matched"}
              </span>
            </div>
          )}

          {/* Chat messages */}
          <div className="space-y-4 max-h-[500px] overflow-y-auto">
            {messages.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                <p className="mb-4">Start by asking a question about {selectedTown}.</p>
                <div className="text-sm space-y-2">
                  <p>Try:</p>
                  <p className="italic">&quot;What are the setback requirements for residential zones?&quot;</p>
                  <p className="italic">&quot;Show me properties with more than 1 acre&quot;</p>
                  <p className="italic">&quot;Can I build a commercial building on a residential lot?&quot;</p>
                </div>
              </div>
            )}

            {messages.map((message, index) => (
              <Card
                key={index}
                className={
                  message.role === "user"
                    ? "bg-blue-50 border-blue-200 ml-8"
                    : "bg-white mr-8"
                }
              >
                <CardContent className="py-3">
                  <div className="text-xs font-medium text-muted-foreground mb-1">
                    {message.role === "user" ? "You" : "Research Assistant"}
                  </div>
                  <div className="prose prose-sm max-w-none dark:prose-invert">
                    {message.role === "assistant" ? (
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                      </ReactMarkdown>
                    ) : (
                      <p>{message.content}</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}

            {isLoading && (
              <Card className="mr-8">
                <CardContent className="py-3">
                  <div className="text-xs font-medium text-muted-foreground mb-2">
                    Research Assistant
                  </div>
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-4 w-1/2" />
                  </div>
                </CardContent>
              </Card>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input form */}
          <form onSubmit={handleSubmit} className="space-y-3">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`Ask about properties or zoning in ${selectedTown}...`}
              className="min-h-[80px]"
              disabled={isLoading}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
            />
            <div className="flex gap-2">
              <Button type="submit" disabled={isLoading || !input.trim()}>
                {isLoading ? "Researching..." : "Send"}
              </Button>
              {messages.length > 0 && (
                <Button type="button" variant="outline" onClick={handleClear}>
                  Clear Chat
                </Button>
              )}
            </div>
          </form>
        </>
      )}
    </div>
  );
}
