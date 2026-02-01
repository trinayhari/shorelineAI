"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface QuestionInputProps {
  onSubmit: (question: string) => void;
  disabled?: boolean;
  placeholder?: string;
  isLoading?: boolean;
}

export function QuestionInput({
  onSubmit,
  disabled = false,
  placeholder = "Ask a question...",
  isLoading = false,
}: QuestionInputProps) {
  const [question, setQuestion] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim() && !disabled && !isLoading) {
      onSubmit(question.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <Input
        type="text"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder={placeholder}
        disabled={disabled || isLoading}
        className="flex-1"
      />
      <Button type="submit" disabled={disabled || isLoading || !question.trim()}>
        {isLoading ? "Searching..." : "Search"}
      </Button>
    </form>
  );
}
